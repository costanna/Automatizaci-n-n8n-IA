#!/usr/bin/env python
"""Pruebas de los flujos de n8n contra la tienda de verdad.

Comprueba el comportamiento que piden las historias de usuario:

  * Flujo 1: al crear un apartado, el cliente recibe la confirmacion.
  * Flujo 2: al abonar, el cliente recibe el recibo (y si se liquida, otro mensaje).
  * Flujo 3: los 9 correos de `data/correos/` se resuelven como dice la tabla del README.
  * Flujo 4: la venta grande avisa a Marisa y la pequena no.
  * Flujo 6: recordatorios a 7 y 1 dias, y los fuera de plazo se vencen con su vale.
  * Flujo 7: el informe mensual trae las cifras de la API.
  * Flujo 8: si un flujo falla (la tienda parada), la tienda recibe el aviso del error.
  * Flujo 11: el apartado desde casa se solicita y se confirma.
  * Flujo 13: las ventas del datafono se importan y no se duplican.
  * Flujo 14: el asistente de Telegram (cliente y tienda).
  * Flujo 15: el panel de Marisa trae las cifras de la API.
  * Seguridad (--seguridad): sin credenciales, los webhooks que escriben y el panel se rechazan.

Para las pruebas hace falta:
  - la tienda y n8n levantados (`docker compose up -d`);
  - el servidor SMTP de desarrollo, para ver los correos que se envian:
        python scripts/smtp_desarrollo.py
  - el webhook de la app apuntando a n8n (el `.env` lo trae de serie).
  - para los flujos 6 y 7 (programados): la cuenta de n8n en N8N_EMAIL y N8N_PASSWORD.
    Se lanzan como el boton "Execute workflow" del editor, sin esperar a su hora.
  - para el flujo 14: el mock de Telegram (`scripts/telegram_mock.py`, ver su ayuda).

Uso:
    python scripts/probar_flujos.py                 # flujos 1 a 4
    python scripts/probar_flujos.py --flujo 3       # solo el flujo 3
    python scripts/probar_flujos.py --flujo 6       # los flujos 6, 7, 8, 11, 13, 14 y 15 van de uno en uno
    python scripts/probar_flujos.py --listar        # ver los casos
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = os.getenv("API_URL", "http://localhost:8000")
N8N = os.getenv("N8N_URL", "http://localhost:5678")


def _del_env(nombre: str, defecto: str = "") -> str:
    """Una variable del entorno o, si no esta, la del .env del proyecto."""
    if os.getenv(nombre):
        return os.getenv(nombre)
    env = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith(nombre + "="):
                return linea.split("=", 1)[1].strip()
    return defecto


def _clave_api() -> str:
    """La clave de la API: la del entorno o, si no, la del .env del proyecto."""
    # Sin .env: la clave de desarrollo por defecto (la de .env.example).
    return _del_env("API_KEY", "cambia-esta-clave")


CLAVE = _clave_api()
# Los webhooks que escriben en la tienda piden X-Webhook-Token; el panel, usuario y contraseña.
WEBHOOK_TOKEN = _del_env("WEBHOOK_TOKEN")
PANEL = (_del_env("PANEL_USUARIO"), _del_env("PANEL_CLAVE"))
CARPETA_CORREOS = RAIZ / "data" / "correos"
CARPETA_ENVIOS = RAIZ / "data" / "envios"
ESPERA = float(os.getenv("ESPERA", "9"))
TELEGRAM_MOCK = os.getenv("TELEGRAM_MOCK", "http://localhost:8081")
# El chat de la tienda (TELEGRAM_ADMIN_ID en data/config.csv)
CHAT_TIENDA = "999999"


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


def n8n_webhook(ruta: str, cuerpo: dict, token: str | None = None):
    """Llama a un webhook de n8n y devuelve (codigo, cuerpo de la respuesta).

    Lleva la cabecera X-Webhook-Token con el WEBHOOK_TOKEN del .env (token="" la quita).
    """
    cabeceras = {"Content-Type": "application/json"}
    token = WEBHOOK_TOKEN if token is None else token
    if token:
        cabeceras["X-Webhook-Token"] = token
    peticion = urllib.request.Request(
        N8N + ruta,
        json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
        cabeceras,
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return r.status, r.read().decode("utf-8")[:200]
    except urllib.error.HTTPError as e:
        return e.code, ""


def abrir_panel(ruta: str = "", credenciales: tuple[str, str] | None = None):
    """Abre el panel con usuario y contraseña (Basic Auth); por defecto, los del .env."""
    import base64

    usuario, clave = PANEL if credenciales is None else credenciales
    peticion = urllib.request.Request(N8N + "/webhook/panel" + ruta)
    if usuario or clave:
        par = base64.b64encode(f"{usuario}:{clave}".encode("utf-8")).decode("ascii")
        peticion.add_header("Authorization", "Basic " + par)
    return urllib.request.urlopen(peticion, timeout=60)


def codigo_http(funcion) -> int:
    """El codigo HTTP de una llamada (tambien si es un error)."""
    try:
        with funcion() as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


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


def hoy_madrid():
    """La fecha de hoy en Madrid, que es la que usan los flujos."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Europe/Madrid")).date()


def euros(n) -> str:
    """Los importes como los escriben los flujos: 1234,50 EUR."""
    return f"{float(n):.2f}".replace(".", ",") + " EUR"


def fecha_es(iso: str) -> str:
    """Las fechas de los mensajes van como dia/mes/año: 2026-10-22 -> 22/10/2026."""
    anio, mes, dia = str(iso)[:10].split("-")
    return f"{dia}/{mes}/{anio}"


def con_fecha(texto: str, iso: str) -> bool:
    """La fecha sale en el texto como DD/MM/AAAA."""
    return fecha_es(iso) in texto


def ejecutar_programado(nombre: str) -> str:
    """Lanza un flujo programado ya, como el boton "Execute workflow" del editor.

    Los flujos con Schedule Trigger no tienen webhook y `n8n execute` solo arranca
    flujos con Execute Workflow Trigger, asi que se usa la API del editor con la
    sesion de la cuenta de n8n. Devuelve el estado de la ejecucion.
    """
    import http.cookiejar

    email, password = os.getenv("N8N_EMAIL"), os.getenv("N8N_PASSWORD")
    if not email or not password:
        return "faltan N8N_EMAIL y N8N_PASSWORD"
    cabeceras = {"Content-Type": "application/json", "browser-id": "probar-flujos"}

    def rest(metodo, ruta, cuerpo=None):
        peticion = urllib.request.Request(
            N8N + ruta, method=metodo, headers=cabeceras,
            data=json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None)
        with abridor.open(peticion, timeout=120) as r:
            return json.loads(r.read() or b"{}").get("data")

    galletas = http.cookiejar.CookieJar()
    abridor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(galletas))
    rest("POST", "/rest/login", {"emailOrLdapLoginId": email, "password": password})
    # La cookie de n8n es Secure y por http no se reenvia sola: se manda a mano.
    cabeceras["Cookie"] = "n8n-auth=" + next(c.value for c in galletas if c.name == "n8n-auth")

    flujo = next((f for f in rest("GET", "/rest/workflows") if f["name"] == nombre), None)
    if not flujo:
        return f"no existe el flujo '{nombre}' en n8n"
    flujo = rest("GET", f"/rest/workflows/{flujo['id']}")
    disparador = next(n["name"] for n in flujo["nodes"] if n["type"].endswith("scheduleTrigger"))
    ejecucion = rest("POST", f"/rest/workflows/{flujo['id']}/run",
                     {"workflowData": flujo, "triggerToStartFrom": {"name": disparador}})["executionId"]
    for _ in range(90):
        time.sleep(2)
        datos = rest("GET", f"/rest/executions/{ejecucion}") or {}
        if datos.get("status") in ("success", "error", "crashed", "canceled"):
            return datos["status"]
    return "no ha terminado en 3 minutos"


def telegram(chat: str, texto: str, nombre: str = "Cliente") -> list[str]:
    """Escribe al bot por el mock de Telegram y devuelve lo que contesta a ese chat."""
    def llamar(ruta, cuerpo=None):
        peticion = urllib.request.Request(
            TELEGRAM_MOCK + ruta, method="POST" if cuerpo is not None else "GET",
            data=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8") if cuerpo is not None else None,
            headers={"Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return json.loads(r.read())

    antes = len(llamar("/_enviados")["result"])
    llamar("/_inyectar", {"chat_id": chat, "text": texto, "first_name": nombre})
    time.sleep(ESPERA + 3)  # el modelo tarda un poco en redactar
    return [m["text"] for m in llamar("/_enviados")["result"][antes:] if str(m["chat"]["id"]) == chat]


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
        r.comprobar(con_fecha(cuerpo, creado["fecha_limite"]),
                    f"y la fecha limite en dia/mes/año ({fecha_es(creado['fecha_limite'])})")
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
        r.comprobar(con_fecha(cuerpo, apartado["fecha_limite"]), "el recibo lleva la fecha limite en dia/mes/año")


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
    grandes = [c for c in nuevos if "Venta grande" in c["asunto"]]
    r.comprobar(bool(grandes), "una venta por encima del umbral avisa a Marisa")
    if grandes:
        r.comprobar(con_fecha(grandes[0]["texto"], hoy_madrid().isoformat()), "el aviso lleva la fecha en dia/mes/año")


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


def probar_flujo_6(r: Resultado):
    """HU-06 y HU-07: recordatorios a 7 y 1 dias, y los fuera de plazo se vencen con su vale."""
    from datetime import timedelta

    print("\n== Flujo 6 · Recordatorios y vencimientos ==")
    hoy = hoy_madrid()
    # El plazo son 90 dias desde la fecha del apartado: con la fecha se elige cuantos faltan.
    casos = {
        "siete": 7,     # recordatorio "dentro de 7 dias"
        "uno": 1,       # recordatorio "mañana"
        "lejos": 30,    # no toca avisar
        "vencido": -5,  # fuera de plazo: se vence y se genera el vale
    }
    creados = {}
    for nombre, dias in casos.items():
        st, a = api("POST", "/api/apartados", {
            "cliente": f"Cliente Plazo {nombre.capitalize()}",
            "email": f"prueba.plazo.{nombre}@example.com",
            "producto": "Mocasín ante azul", "talla": "41", "precio": 60,
            "abono_inicial": 10, "forma_pago": "efectivo",
            "fecha": (hoy + timedelta(days=dias - 90)).isoformat(),
        })
        if not r.comprobar(st == 201, f"se crea el apartado que vence en {dias} dias (respuesta {st})"):
            return
        creados[nombre] = a
    time.sleep(ESPERA)

    antes = len(correos_enviados())
    estado = ejecutar_programado("06 · Recordatorios y vencimientos")
    if not r.comprobar(estado == "success", f"el flujo se ejecuta ({estado})"):
        return
    time.sleep(ESPERA)
    nuevos = correos_enviados()[antes:]
    para = lambda nombre: [c for c in nuevos if f"prueba.plazo.{nombre}@" in c["destinatario"]]

    for nombre, cuando in (("siete", "7 días"), ("uno", "mañana")):
        a, correos = creados[nombre], para(nombre)
        r.comprobar(len(correos) == 1, f"el cliente cuyo plazo vence en {cuando} recibe un recordatorio ({len(correos)})")
        if correos:
            texto = correos[0]["texto"]
            r.comprobar(euros(a["pendiente"]) in texto, f"el recordatorio ({cuando}) lleva lo que falta: {euros(a['pendiente'])}")
            r.comprobar(con_fecha(texto, a["fecha_limite"]), f"el recordatorio ({cuando}) lleva la fecha limite")
    r.comprobar(not para("lejos"), "a quien le quedan 30 dias no se le avisa")

    _, vencido = api("GET", f"/api/apartados/{creados['vencido']['id']}")
    vale = (vencido or {}).get("vale") or {}
    r.comprobar(vencido.get("estado") == "vencido", "el apartado fuera de plazo queda vencido por API")
    r.comprobar(bool(vale.get("codigo")), f"la app genera el vale ({vale.get('codigo', 'sin vale')})")
    correos = para("vencido")
    r.comprobar(len(correos) == 1, f"el cliente recibe un solo aviso del vale ({len(correos)})")
    if correos and vale:
        texto = correos[0]["texto"]
        r.comprobar(vale["codigo"] in texto and euros(vale["importe"]) in texto,
                    "el aviso lleva el codigo y el importe del vale")
    r.comprobar(any(f"#{vencido.get('id')}" in c["texto"] and "vuelve" in c["texto"] for c in nuevos
                    if "marisa@" in c["destinatario"] or "tienda@" in c["destinatario"]),
                "la tienda recibe el par que vuelve a la venta")
    # "Cada aviso una sola vez" se guarda en los datos estaticos del flujo, y n8n no los
    # guarda en las ejecuciones manuales: se comprueba en produccion (tests/flujo-06/).


def probar_flujo_7(r: Resultado):
    """HU-08: el informe mensual trae las cifras de la API del mes anterior."""
    from datetime import timedelta

    print("\n== Flujo 7 · Informe mensual ==")
    hoy = hoy_madrid()
    hasta = hoy.replace(day=1) - timedelta(days=1)
    desde = hasta.replace(day=1)
    rango = f"desde={desde.isoformat()}&hasta={hasta.isoformat()}"
    ventas = api("GET", f"/api/ventas?{rango}")[1]
    abonos = api("GET", f"/api/abonos?{rango}")[1]
    todos = apartados()
    esperado = {
        "Ventas directas": round(sum(v["importe"] for v in ventas), 2),
        "Abonos de apartados": round(sum(a["importe"] for a in abonos), 2),
        "Total recaudado": round(sum(v["importe"] for v in ventas) + sum(a["importe"] for a in abonos), 2),
        "Total por cobrar": round(sum(a["pendiente"] for a in todos if a["estado"] == "activo"), 2),
    }
    nuevos_mes = sum(1 for a in todos if desde.isoformat() <= a["fecha"] <= hasta.isoformat())

    antes = len(correos_enviados())
    estado = ejecutar_programado("07 · Informe mensual")
    if not r.comprobar(estado == "success", f"el flujo se ejecuta ({estado})"):
        return
    time.sleep(3)
    informes = [c for c in correos_enviados()[antes:] if "Informe mensual" in c["asunto"]]
    if not r.comprobar(len(informes) == 1 and "marisa@" in informes[0]["destinatario"],
                       "Marisa recibe un informe"):
        return
    texto = informes[0]["texto"]
    rango_es = f"{fecha_es(desde.isoformat())} a {fecha_es(hasta.isoformat())}"
    r.comprobar(rango_es in texto, f"el informe es del mes anterior ({rango_es})")
    for etiqueta, importe in esperado.items():
        r.comprobar(f"{etiqueta}: {euros(importe)}" in texto, f"{etiqueta}: {euros(importe)} (lo que da la API)")
    r.comprobar(f"Nuevos: {nuevos_mes}" in texto, f"apartados nuevos del mes: {nuevos_mes}")
    r.comprobar("Liquidados:" in texto and "Vencidos:" in texto, "trae los liquidados y los vencidos del mes")


def probar_flujo_14(r: Resultado):
    """HU-11 y HU-12: el asistente de Telegram, para el cliente y para la tienda."""
    from datetime import timedelta

    print("\n== Flujo 14 · Asistente de Telegram ==")
    try:
        urllib.request.urlopen(TELEGRAM_MOCK + "/_config", timeout=5)
    except Exception:
        r.comprobar(False, f"el mock de Telegram no responde en {TELEGRAM_MOCK}")
        return

    activos = [a for a in apartados() if a["estado"] == "activo" and a.get("telefono")]
    cliente = activos[0]
    otros = {a["cliente"] for a in activos if a["telefono"] != cliente["telefono"]}
    # Un chat nuevo en cada prueba: el flujo recuerda el telefono de cada chat.
    chat = str(int(time.time()) % 1000000 + 100000)

    respuesta = " ".join(telegram(chat, "¿cuánto me falta?"))
    r.comprobar("teléfono" in respuesta, "a un chat sin apuntar le pide el telefono")

    # El modelo puede escribir "59,50 €" en vez de "59,50 EUR": lo que el flujo garantiza
    # es el importe de la app, no la unidad.
    importe = euros(cliente["pendiente"]).replace(" EUR", "")
    respuesta = " ".join(telegram(chat, cliente["telefono"]))
    r.comprobar(importe in respuesta, f"con el telefono, le dice lo que le falta: {importe}")
    r.comprobar(con_fecha(respuesta, cliente["fecha_limite"]), "y su fecha limite")
    r.comprobar(not any(nombre in respuesta for nombre in otros), "no le enseña apartados de otros clientes")

    respuesta = " ".join(telegram(chat, "¿cuánto me falta por pagar?"))
    r.comprobar(importe in respuesta and "teléfono" not in respuesta, "la siguiente vez ya no le pide el telefono")

    r.comprobar("sent automatically with" not in respuesta, "los mensajes no llevan el pie de n8n")

    respuesta = " ".join(telegram(chat, "¿cuánto se recaudó esta semana?"))
    r.comprobar("Recaudado" not in respuesta and "Ventas directas" not in respuesta,
                "a un cliente no le da las cifras de la tienda")

    otro_chat = str(int(chat) + 1)
    telegram(otro_chat, "¿cuánto me falta?")
    respuesta = " ".join(telegram(otro_chat, "600 999 999"))
    r.comprobar("EUR" not in respuesta and "no he encontrado" in respuesta.lower()
                and "tienda" in respuesta.lower(),
                "si no encuentra el telefono, lo dice, no da cifras y ofrece hablar con la tienda")

    hoy = hoy_madrid()
    pendiente = sum(a["pendiente"] for a in apartados() if a["estado"] == "activo")
    fin_mes_pasado = hoy.replace(day=1) - timedelta(days=1)
    for pregunta, desde, hasta in (
            ("¿cuánto se recaudó esta semana?", hoy - timedelta(days=6), hoy),
            ("¿cuánto se recaudó este mes?", hoy.replace(day=1), hoy),
            ("¿cuánto se recaudó el mes pasado?", fin_mes_pasado.replace(day=1), fin_mes_pasado)):
        rango = f"desde={desde.isoformat()}&hasta={hasta.isoformat()}"
        recaudado = (sum(v["importe"] for v in api("GET", f"/api/ventas?{rango}")[1])
                     + sum(a["importe"] for a in api("GET", f"/api/abonos?{rango}")[1]))
        respuesta = " ".join(telegram(CHAT_TIENDA, pregunta, "Marisa"))
        r.comprobar(f"Recaudado: {euros(recaudado)}" in respuesta,
                    f"la tienda pregunta '{pregunta}': {euros(recaudado)} ({desde.isoformat()} a {hasta.isoformat()})")
        r.comprobar(f"Pendiente de cobro: {euros(pendiente)}" in respuesta,
                    f"y el pendiente de cobro: {euros(pendiente)}")


def probar_flujo_8(r: Resultado):
    """HU-05: si un flujo falla, la tienda recibe el aviso con el flujo, el paso y el error."""
    import subprocess

    print("\n== Flujo 8 · Avisos de error ==")
    # Un fallo de verdad: con la tienda parada, el panel no puede consultar la API.
    # (El Error Workflow solo salta en ejecuciones de produccion, no en las manuales.)
    antes = len(correos_enviados())
    subprocess.run(["docker", "compose", "stop", "tienda"], cwd=RAIZ, capture_output=True, timeout=120)
    try:
        try:
            abrir_panel()
        except Exception:
            pass
        time.sleep(ESPERA)
    finally:
        subprocess.run(["docker", "compose", "start", "tienda"], cwd=RAIZ, capture_output=True, timeout=120)
    avisos = [c for c in correos_enviados()[antes:] if "marisa@" in c["destinatario"]]
    if not r.comprobar(len(avisos) == 1, f"la tienda recibe un aviso del error ({len(avisos)})"):
        return
    texto = avisos[0]["asunto"] + "\n" + avisos[0]["texto"]
    r.comprobar("15 · Panel de Marisa" in texto, "el aviso dice que flujo ha fallado")
    r.comprobar("Ventas del periodo" in texto, "el aviso dice en que paso (Ventas del periodo)")
    r.comprobar(CLAVE not in texto, "el aviso no lleva la clave de la API")
    r.comprobar(bool(re.search(r"Cuando: \d{2}/\d{2}/\d{4},? \d{2}:\d{2}", texto)),
                "el aviso lleva la fecha y la hora (dia/mes/año hh:mm)")
    for _ in range(40):
        try:
            api("GET", "/api/apartados/resumen")
            break
        except Exception:
            time.sleep(1)


def probar_seguridad(r: Resultado):
    """HU-14: sin credenciales, los webhooks que escriben en la tienda y el panel se rechazan."""
    print("\n== Seguridad de los webhooks ==")
    rechazo = (401, 403)

    st, _ = n8n_webhook("/webhook/tienda", {"evento": "prueba.seguridad", "datos": {}}, token="")
    r.comprobar(st == 401, f"el webhook de la tienda sin token responde 401 ({st})")
    st, _ = n8n_webhook("/webhook/tienda", {"evento": "prueba.seguridad", "datos": {}}, token="no-es-el-token")
    r.comprobar(st == 401, f"el webhook de la tienda con un token falso responde 401 ({st})")

    carmen = por_cliente("Carmen Ruiz")
    asunto, cuerpo = leer_correo(CARPETA_CORREOS / "01_bizum_carmen.eml")
    st, _ = n8n_webhook("/webhook/abonos-distancia", {"texto": cuerpo, "asunto": asunto}, token="")
    r.comprobar(st in rechazo, f"un aviso del banco sin token se rechaza ({st})")
    time.sleep(ESPERA)
    despues = por_cliente("Carmen Ruiz")
    r.comprobar(bool(carmen) and bool(despues) and despues["abonado"] == carmen["abonado"],
                "y no se registra ningun abono")

    st, _ = n8n_webhook("/webhook/confirmar-solicitud", {"codigo": "SOL-0001", "importe": 10}, token="")
    r.comprobar(st in rechazo, f"confirmar una solicitud sin token se rechaza ({st})")
    st, _ = n8n_webhook("/webhook/datxfono", {}, token="")
    r.comprobar(st in rechazo, f"lanzar la importacion del datafono sin token se rechaza ({st})")

    st = codigo_http(lambda: abrir_panel(credenciales=("", "")))
    r.comprobar(st == 401, f"el panel sin usuario ni contraseña responde 401 ({st})")
    st = codigo_http(lambda: abrir_panel(credenciales=(PANEL[0], "no-es-la-clave")))
    r.comprobar(st in rechazo, f"el panel con una contraseña falsa se rechaza ({st})")
    st = codigo_http(lambda: abrir_panel("?formato=json", credenciales=("", "")))
    r.comprobar(st == 401, f"los datos del panel en JSON tampoco salen sin contraseña ({st})")

    st = codigo_http(lambda: urllib.request.urlopen(N8N + "/webhook/apartar-zapatos", timeout=60))
    r.comprobar(st == 200, f"el formulario de los clientes sigue abierto ({st})")


def probar_flujo_15(r: Resultado):
    """HU-15: el panel de Marisa trae las cifras de la API."""
    print("\n== Flujo 15 · Panel de Marisa ==")
    hoy = hoy_madrid().isoformat()
    try:
        with abrir_panel("?formato=json") as resp:
            panel = json.loads(resp.read())
    except Exception as e:
        r.comprobar(False, f"el panel responde en JSON ({e})")
        return
    r.comprobar(panel.get("fecha") == hoy, f"el panel es de hoy ({panel.get('fecha')})")

    todos = apartados()
    activos = [a for a in todos if a["estado"] == "activo"]
    resumen = api("GET", "/api/apartados/resumen")[1]
    cobrado_hoy = (sum(v["importe"] for v in api("GET", f"/api/ventas?desde={hoy}&hasta={hoy}")[1])
                   + sum(a["importe"] for a in api("GET", f"/api/abonos?desde={hoy}&hasta={hoy}")[1]))
    mes = f"desde={hoy[:8]}01&hasta={hoy}"
    del_mes = (sum(v["importe"] for v in api("GET", f"/api/ventas?{mes}")[1])
               + sum(a["importe"] for a in api("GET", f"/api/abonos?{mes}")[1]))
    pendiente = sum(a["pendiente"] for a in activos)

    r.comprobar(abs(panel["hoy"]["total"] - cobrado_hoy) < 0.01, f"cobrado hoy: {euros(cobrado_hoy)}")
    r.comprobar(abs(panel["mes"]["recaudacion"] - del_mes) < 0.01, f"recaudado este mes: {euros(del_mes)}")
    r.comprobar(abs(panel["pendiente_cobro"] - pendiente) < 0.01, f"pendiente de cobro: {euros(pendiente)}")
    r.comprobar(panel["apartados"]["activos"] == len(activos)
                and panel["apartados"]["liquidados"] == resumen.get("liquidado")
                and panel["apartados"]["vencidos"] == resumen.get("vencido"),
                "apartados activos, liquidados y vencidos como en la app")
    from datetime import date
    esperados = sorted((a for a in activos
                        if 0 <= (date.fromisoformat(a["fecha_limite"]) - date.fromisoformat(hoy)).days <= 30),
                       key=lambda a: a["fecha_limite"])
    r.comprobar([x["id"] for x in panel["por_vencer"]] == [a["id"] for a in esperados],
                f"los que vencen en 30 dias, del mas cercano al mas lejano ({len(esperados)})")

    with abrir_panel("?tema=oscuro") as resp:
        html = resp.read().decode("utf-8")
        r.comprobar("text/html" in resp.headers.get("Content-Type", ""), "el panel se sirve como pagina web")
    r.comprobar(euros(pendiente) in html, "la pagina pinta el pendiente de cobro")
    r.comprobar('data-tema="oscuro"' in html, "con ?tema=oscuro la pagina sale en oscuro")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pruebas de los flujos de n8n")
    ap.add_argument("--flujo", type=int, default=None,
                    help="probar solo un flujo (1, 2, 3, 4, 6, 7, 8, 11, 13, 14 o 15)")
    ap.add_argument("--caso", default=None, help="probar solo un caso del flujo 3 (nombre del fichero)")
    ap.add_argument("--listar", action="store_true", help="listar los casos del flujo 3")
    ap.add_argument("--seguridad", action="store_true",
                    help="comprobar que sin credenciales los webhooks y el panel se rechazan")
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
    if args.seguridad:
        probar_seguridad(r)
        return 0 if not r.fallos else 1
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
    if args.flujo == 6:
        probar_flujo_6(r)
    if args.flujo == 8:
        probar_flujo_8(r)
    if args.flujo == 7:
        probar_flujo_7(r)
    if args.flujo == 14:
        probar_flujo_14(r)
    if args.flujo == 15:
        probar_flujo_15(r)

    print()
    print(f"Correos enviados durante las pruebas: {len(correos_enviados())} (en {CARPETA_ENVIOS})")
    return 0 if not r.fallos else 1


if __name__ == "__main__":
    sys.exit(main())
