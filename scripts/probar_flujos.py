#!/usr/bin/env python
"""Pruebas de los flujos de n8n contra la tienda de verdad.

Comprueba el comportamiento que piden las historias de usuario:

  * Flujo 1: al crear un apartado, el cliente recibe la confirmacion.
  * Flujo 2: al abonar, el cliente recibe el recibo (y si se liquida, otro mensaje).
  * Flujo 3: los 9 correos de `data/correos/` se resuelven como dice la tabla del README.
  * Flujo 4: la venta grande avisa a Marisa y la pequena no.
  * Flujo 11: el apartado desde casa se solicita y se confirma.
  * Flujo 13: las ventas del datafono se importan y no se duplican.

Para las pruebas hace falta:
  - la tienda y n8n levantados (`docker compose up -d`);
  - el servidor SMTP de desarrollo, para ver los correos que se envian:
        python scripts/smtp_desarrollo.py
  - el webhook de la app apuntando a n8n (el `.env` lo trae de serie).

Uso:
    python scripts/probar_flujos.py                 # todas las pruebas
    python scripts/probar_flujos.py --flujo 3       # solo el flujo 3
    python scripts/probar_flujos.py --listar        # ver los casos
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = os.getenv("API_URL", "http://localhost:8000")
N8N = os.getenv("N8N_URL", "http://localhost:5678")
CLAVE = os.getenv("API_KEY", "paso-firme-dev-key")
CARPETA_CORREOS = RAIZ / "data" / "correos"
CARPETA_ENVIOS = RAIZ / "data" / "envios"
ESPERA = float(os.getenv("ESPERA", "9"))


# ---------------------------------------------------------------- utilidades

def api(metodo: str, ruta: str, cuerpo=None):
    peticion = urllib.request.Request(API + ruta, method=metodo)
    peticion.add_header("X-API-Key", CLAVE)
    if cuerpo is not None:
        peticion.data = json.dumps(cuerpo).encode("utf-8")
        peticion.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def reiniciar_tienda() -> bool:
    """Borra la base de datos de la tienda y la vuelve a levantar con los datos de ejemplo.

    Las pruebas necesitan un estado conocido: si la app ya tiene abonos de pruebas
    anteriores, el caso 'paga de mas' puede dejar de cumplirse.
    """
    import subprocess

    print("Reiniciando la tienda (datos de ejemplo limpios)...")
    try:
        subprocess.run(
            ["docker", "compose", "exec", "-T", "tienda", "sh", "-c", "rm -f /data/tienda.db"],
            cwd=RAIZ, check=True, capture_output=True, timeout=120,
        )
        subprocess.run(
            ["docker", "compose", "restart", "tienda"],
            cwd=RAIZ, check=True, capture_output=True, timeout=180,
        )
    except Exception as e:
        print("  no se ha podido reiniciar la tienda:", e)
        return False
    for _ in range(40):
        time.sleep(1)
        try:
            api("GET", "/api/apartados/resumen")
            print("  la tienda esta lista")
            return True
        except Exception:
            continue
    print("  la tienda no responde")
    return False


def n8n_webhook(ruta: str, cuerpo: dict):
    peticion = urllib.request.Request(
        N8N + ruta,
        json.dumps(cuerpo).encode("utf-8"),
        {"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def apartados() -> list[dict]:
    _, datos = api("GET", "/api/apartados")
    return datos if isinstance(datos, list) else []


def por_cliente(cliente: str):
    objetivo = cliente.strip().lower()
    for a in apartados():
        if a["cliente"].strip().lower() == objetivo:
            return a
    return None


def correos_enviados() -> list[dict]:
    """Lee los correos que ha guardado el servidor SMTP de desarrollo.

    El servidor SMTP escribe dos ficheros por correo: el `.eml` original (el que se
    puede abrir en cualquier cliente de correo) y un `.txt` con los datos y el texto
    plano, que es lo que se comprueba aquí.
    """
    if not CARPETA_ENVIOS.exists():
        return []
    salida = []
    for ruta in sorted(CARPETA_ENVIOS.glob("*.txt")):
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        cabecera, _, cuerpo = texto.partition("-" * 60)
        datos = {}
        for linea in cabecera.splitlines():
            if ":" in linea:
                clave, _, valor = linea.partition(":")
                datos[clave.strip().lower()] = valor.strip()
        salida.append({
            "fichero": ruta.name,
            "destinatario": datos.get("destinatarios", ""),
            "remitente": datos.get("remitente", ""),
            "asunto": datos.get("asunto", ""),
            "texto": cuerpo,
        })
    return salida


def n8n_webhook(ruta: str, cuerpo: dict):
    """Llama a un webhook de n8n y devuelve (codigo, cuerpo de la respuesta)."""
    peticion = urllib.request.Request(
        N8N + ruta,
        json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
        {"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return r.status, r.read().decode("utf-8")[:200]
    except urllib.error.HTTPError as e:
        return e.code, ""


def leer_correo(ruta: Path) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo en texto plano) de un .eml, descodificados."""
    import email
    import email.header

    mensaje = email.message_from_string(ruta.read_text(encoding="utf-8", errors="replace"))
    asunto = str(email.header.make_header(email.header.decode_header(mensaje.get("Subject", ""))))
    cuerpo = ""
    for parte in mensaje.walk():
        if parte.get_content_type() == "text/plain":
            try:
                cuerpo = parte.get_payload(decode=True).decode(parte.get_content_charset() or "utf-8", "replace")
            except Exception:
                cuerpo = str(parte.get_payload())
            break
    if not cuerpo:
        cuerpo = mensaje.get_payload()
        if not isinstance(cuerpo, str):
            cuerpo = ""
    return asunto, cuerpo


class Resultado:
    def __init__(self):
        self.ok = 0
        self.fallos: list[str] = []

    def comprobar(self, condicion: bool, mensaje: str):
        if condicion:
            self.ok += 1
            print(f"  OK   {mensaje}")
        else:
            self.fallos.append(mensaje)
            print(f"  FALLA {mensaje}")
        return condicion

    def resumen(self, titulo: str) -> bool:
        print()
        if self.fallos:
            print(f"{titulo}: {self.ok} correctos, {len(self.fallos)} con fallos")
            for f in self.fallos:
                print(f"   - {f}")
            return False
        print(f"{titulo}: {self.ok} comprobaciones correctas")
        return True


# ------------------------------------------------------------------- pruebas

def probar_flujo_1(r: Resultado):
    """HU-01: al crear un apartado, el cliente recibe la confirmacion."""
    print("\n== Flujo 1 · Confirmacion de apartado ==")
    antes = len(correos_enviados())
    st, creado = api("POST", "/api/apartados", {
        "cliente": "Cliente Prueba Confirmacion",
        "email": "prueba.confirmacion@example.com",
        "producto": "Botín piel marrón",
        "talla": "38",
        "precio": 89.9,
        "abono_inicial": 10,
        "forma_pago": "bizum",
    })
    if not r.comprobar(st == 201, f"se crea el apartado por API (respuesta {st})"):
        return
    time.sleep(ESPERA)
    nuevos = correos_enviados()[antes:]
    hubo = any("prueba.confirmacion@example.com" in c["destinatario"] for c in nuevos)
    r.comprobar(hubo, "el cliente recibe el mensaje de confirmacion")
    if hubo:
        cuerpo = [c for c in nuevos if "prueba.confirmacion@example.com" in c["destinatario"]][0]["texto"]
        r.comprobar("89,90" in cuerpo and "10,00" in cuerpo and "79,90" in cuerpo,
                    "el mensaje lleva precio, abonado y pendiente")
    return creado


def probar_flujo_2(r: Resultado, apartado: dict | None):
    """HU-02: al abonar, el cliente recibe el recibo; si liquida, el mensaje cambia."""
    print("\n== Flujo 2 · Recibo de abono ==")
    if not apartado:
        st, creado = api("POST", "/api/apartados", {
            "cliente": "Cliente Prueba Recibo",
            "email": "prueba.recibo@example.com",
            "producto": "Sandalia tacón negra",
            "talla": "37",
            "precio": 40,
            "abono_inicial": 10,
            "forma_pago": "efectivo",
        })
        if not r.comprobar(st == 201, f"se crea el apartado de prueba (respuesta {st})"):
            return
        apartado = creado
        time.sleep(ESPERA)

    email_cliente = apartado.get("email") or ""
    antes = len(correos_enviados())
    st, _ = api("POST", f"/api/apartados/{apartado['id']}/abonos", {"importe": 15, "forma_pago": "efectivo"})
    r.comprobar(st == 201, f"se registra el abono (respuesta {st})")
    time.sleep(ESPERA)
    nuevos = correos_enviados()[antes:]
    hubo = any(email_cliente in c["destinatario"] for c in nuevos) if email_cliente else False
    r.comprobar(hubo, "el cliente recibe el recibo del abono")
    if hubo:
        cuerpo = [c for c in nuevos if email_cliente in c["destinatario"]][0]["texto"]
        r.comprobar("15,00" in cuerpo, "el recibo lleva el importe del abono")
        r.comprobar("queda por pagar" in cuerpo.lower() or "Pendiente" in cuerpo,
                    "el recibo dice lo que queda pendiente")


def probar_flujo_4(r: Resultado):
    """HU-09: la venta grande avisa a Marisa; la pequena no."""
    print("\n== Flujo 4 · Aviso de venta grande ==")
    antes = len(correos_enviados())
    api("POST", "/api/ventas", {"concepto": "Venta pequena de prueba", "importe": 9.9, "forma_pago": "efectivo"})
    time.sleep(ESPERA)
    nuevos = correos_enviados()[antes:]
    r.comprobar(not any("Venta grande" in c["asunto"] for c in nuevos),
                "una venta por debajo del umbral no avisa")

    antes = len(correos_enviados())
    api("POST", "/api/ventas", {"concepto": "Venta grande de prueba", "importe": 250, "forma_pago": "tarjeta"})
    time.sleep(ESPERA)
    nuevos = correos_enviados()[antes:]
    r.comprobar(any("Venta grande" in c["asunto"] for c in nuevos),
                "una venta por encima del umbral avisa a Marisa")


CASOS_FLUJO_3 = [
    {"fichero": "01_bizum_carmen.eml", "cliente": "Carmen Ruiz", "registra": True,
     "detalle": "nombre unico -> se registra"},
    {"fichero": "02_bizum_jorge.eml", "cliente": "Jorge Martín", "registra": True,
     "detalle": "el concepto trae el numero de apartado -> se registra"},
    {"fichero": "03_transferencia_lucia.eml", "cliente": "Lucía Gómez", "registra": True, "liquidado": True,
     "detalle": "paga justo lo que falta -> se registra y liquida"},
    {"fichero": "04_bizum_laura.eml", "cliente": "Laura Ortega", "registra": False,
     "detalle": "paga de mas -> no se registra, se avisa a Marisa"},
    {"fichero": "05_bizum_romero.eml", "cliente": "David Romero", "registra": False,
     "detalle": "apellido e inicial sin concepto -> no se registra, se pregunta a Marisa"},
    {"fichero": "06_bizum_paula.eml", "cliente": "Paula Ramos", "registra": False,
     "detalle": "fuera de plazo -> no se registra, se avisa a Marisa"},
    {"fichero": "07_transferencia_desconocido.eml", "cliente": None, "registra": False,
     "detalle": "cliente desconocido -> no se registra, se pregunta a Marisa"},
    {"fichero": "08_publicidad_banco.eml", "cliente": None, "registra": False, "silencio": True,
     "detalle": "no es un pago -> se ignora en silencio"},
    {"fichero": "09_bizum_silvia.eml", "cliente": "Silvia Cortés", "registra": True,
     "detalle": "nombre unico -> se registra"},
]


def probar_flujo_3(r: Resultado, solo: str | None = None):
    """HU-03: los 9 correos de `data/correos/`."""
    print("\n== Flujo 3 · Abonos a distancia ==")
    casos = CASOS_FLUJO_3
    if solo:
        casos = [c for c in casos if solo in c["fichero"]]

    for caso in casos:
        ruta = CARPETA_CORREOS / caso["fichero"]
        if not ruta.exists():
            r.comprobar(False, f"{caso['fichero']}: no se encuentra el fichero")
            continue

        antes_correos = len(correos_enviados())
        abonado_antes = {}
        pendientes_antes = {}
        for cliente in {c["cliente"] for c in casos if c["cliente"]}:
            a = por_cliente(cliente)
            if a:
                abonado_antes[cliente] = a["abonado"]
                pendientes_antes[cliente] = a["pendiente"]

        asunto, cuerpo = leer_correo(ruta)
        n8n_webhook("/webhook/abonos-distancia", {"texto": cuerpo, "asunto": asunto})
        time.sleep(ESPERA)

        nuevos = correos_enviados()[antes_correos:]
        cambio = {}
        for cliente, valor in abonado_antes.items():
            a = por_cliente(cliente)
            cambio[cliente] = (a["abonado"] if a else 0) - valor

        if caso["registra"]:
            cliente = caso["cliente"]
            r.comprobar(cambio.get(cliente, 0) > 0,
                        f"{caso['fichero']}: se ha registrado el abono ({caso['detalle']})")
            if caso.get("liquidado"):
                a = por_cliente(cliente)
                r.comprobar(bool(a) and a["estado"] == "liquidado",
                            f"{caso['fichero']}: el apartado queda liquidado")
        elif caso.get("silencio"):
            r.comprobar(not nuevos, f"{caso['fichero']}: se ignora en silencio (no se avisa a nadie)")
        else:
            total = sum(cambio.values())
            r.comprobar(total == 0, f"{caso['fichero']}: no se registra nada ({caso['detalle']})")
            r.comprobar(len(nuevos) > 0, f"{caso['fichero']}: se avisa a Marisa")


def probar_flujo_11(r: Resultado):
    """HU-13: apartado desde casa (formulario -> solicitud -> confirmacion)."""
    print("\n== Flujo 11 · Apartados desde casa ==")
    antes = len(correos_enviados())
    st, _ = n8n_webhook("/webhook/apartar-zapatos", {
        "cliente": "Cliente Casa Demo",
        "telefono": "600 555 111",
        "email": "casa.demo@example.com",
        "producto": "Botin piel marron",
        "talla": "39",
        "precio": "89.90",
        "forma_pago": "bizum",
    })
    r.comprobar(st == 200, f"el cliente envia la solicitud (respuesta {st})")
    time.sleep(ESPERA)
    nuevos = correos_enviados()[antes:]
    r.comprobar(any("Casa Demo" in c["texto"] for c in nuevos),
                "la tienda recibe el aviso de la solicitud")

    # El codigo de la solicitud lo genera el flujo: se busca en el aviso.
    codigo = ""
    for c in nuevos:
        m = re.search(r"SOL-\d{4}", c["texto"])
        if m:
            codigo = m.group(0)
            break
    r.comprobar(bool(codigo), f"el aviso lleva el codigo de la solicitud ({codigo or 'no aparece'})")
    if not codigo:
        return

    st, _ = n8n_webhook("/webhook/confirmar-solicitud", {"codigo": codigo, "importe": 10})
    r.comprobar(st == 200, f"la tienda confirma la solicitud (respuesta {st})")
    time.sleep(ESPERA)

    apartado = None
    for a in api("GET", "/api/apartados")[1]:
        if a.get("cliente") == "Cliente Casa Demo":
            apartado = a
            break
    r.comprobar(apartado is not None, "el apartado se crea en la app")
    if apartado:
        r.comprobar(abs(apartado["abonado"] - 10) < 0.01, "el abono inicial son 10 EUR")
        r.comprobar(abs(apartado["pendiente"] - 79.9) < 0.01, "el pendiente son 79,90 EUR")


def probar_flujo_13(r: Resultado):
    """HU-13: las ventas del datafono se importan una sola vez."""
    print("\n== Flujo 13 · Ventas del datafono ==")
    conceptos = {"Bota montana T41", "Zapatilla casa T38", "Calcetines pack 3",
                 "Botin piel negro T40", "Crema calzado", "Zapatilla running azul T43",
                 "Plantillas gel"}

    def ventas_datafono():
        return [v for v in api("GET", "/api/ventas")[1]
                if v.get("fecha") in ("2026-10-19", "2026-10-20")
                and v.get("forma_pago") == "tarjeta"
                and v.get("concepto") in conceptos]

    antes = len(ventas_datafono())
    r.comprobar(n8n_webhook("/webhook/datxfono", {})[0] == 200, "se lanza la importacion")
    time.sleep(ESPERA)
    despues = len(ventas_datafono())
    r.comprobar(despues > antes, f"se importan cobros nuevos ({antes} -> {despues})")

    r.comprobar(n8n_webhook("/webhook/datxfono", {})[0] == 200, "se lanza la importacion otra vez")
    time.sleep(ESPERA)
    final = len(ventas_datafono())
    r.comprobar(final == despues, f"la segunda vez no se duplica nada ({despues} -> {final})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pruebas de los flujos de n8n")
    ap.add_argument("--flujo", type=int, default=None, help="probar solo un flujo (1, 2, 3 o 4)")
    ap.add_argument("--caso", default=None, help="probar solo un caso del flujo 3 (nombre del fichero)")
    ap.add_argument("--listar", action="store_true", help="listar los casos del flujo 3")
    ap.add_argument("--sin-reset", action="store_true",
                    help="no reiniciar la tienda antes de las pruebas")
    args = ap.parse_args()

    if args.listar:
        for caso in CASOS_FLUJO_3:
            print(f"{caso['fichero']}: {caso['detalle']}")
        return 0

    try:
        api("GET", "/api/apartados/resumen")
    except Exception as e:
        print("No se puede falar con la API de la tienda:", e)
        print("Levantala con: docker compose up -d")
        return 2

    r = Resultado()
    if not args.sin_reset:
        reiniciar_tienda()
    todo = args.flujo is None
    if todo or args.flujo == 1:
        apartado = probar_flujo_1(r)
    if todo or args.flujo == 2:
        probar_flujo_2(r, apartado if todo or args.flujo == 2 else None)
    if todo or args.flujo == 3:
        probar_flujo_3(r, args.caso)
    if todo or args.flujo == 4:
        probar_flujo_4(r)
    if args.flujo == 11:
        probar_flujo_11(r)
    if args.flujo == 13:
        probar_flujo_13(r)

    print()
    print(f"Correos enviados durante las pruebas: {len(correos_enviados())} (en {CARPETA_ENVIOS})")
    return 0 if not r.fallos else 1


if __name__ == "__main__":
    sys.exit(main())
