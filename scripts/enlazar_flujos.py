#!/usr/bin/env python
"""Importa los flujos de `workflows/` en n8n y los deja enlazados.

Qué hace, en este orden:

1. Importa todos los JSON de `workflows/` en la instancia de n8n.
2. Consulta los ids que n8n ha asignado a cada flujo.
3. Sustituye en los JSON locales los marcadores `PENDIENTE_ID_*` por el id real del flujo
   destino y los ids de credenciales por los de la instancia.
4. Vuelve a subir los flujos ya enlazados.

Sin este paso, los nodos *Execute Workflow* apuntan a un id que no existe en tu n8n
y hay que elegir el subflujo a mano en cada nodo.

Uso:
    python scripts/enlazar_flujos.py                     # importa y enlaza
    python scripts/enlazar_flujos.py --url http://localhost:5678
    python scripts/enlazar_flujos.py --solo-enlazar       # no importa, solo arregla ids
    python scripts/enlazar_flujos.py --dry-run           # no toca nada, solo informa

Variables de entorno opcionales:
    N8N_EMAIL / N8N_PASSWORD  credenciales de la cuenta de n8n (si no, se pregunta)
    N8N_API_KEY               si se prefiere usar una API key en vez de iniciar sesion
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request
from getpass import getpass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_FLUJOS = RAIZ / "workflows"

# Marcador -> nombre del flujo destino en n8n.
DESTINOS = {
    "PENDIENTE_ID_01": "01 · Confirmación de apartado",
    "PENDIENTE_ID_02": "02 · Recibo de abono",
    "PENDIENTE_ID_03": "03 · Abonos a distancia",
    "PENDIENTE_ID_04": "04 · Aviso de venta grande",
    "PENDIENTE_ID_05": "05 · Cierre diario",
    "PENDIENTE_ID_06": "06 · Recordatorios y vencimientos",
    "PENDIENTE_ID_07": "07 · Informe mensual",
    "PENDIENTE_ID_08": "08 · Avisos de error",
    "PENDIENTE_ID_10": "10 · Migración del Excel",
    "PENDIENTE_ID_SUB_NOTIFICAR": "SUB · Notificar",
    "PENDIENTE_ID_SUB_BUSCAR_APARTADO": "SUB · Buscar apartado",
    "PENDIENTE_ID_SUB_AVISAR_VALE": "SUB · Avisar vale",
    "PENDIENTE_ID_SUB_TOOL_SALDO": "SUB · Tool saldo del cliente",
    "PENDIENTE_ID_SUB_TOOL_CIFRAS": "SUB · Tool cifras de la tienda",
}

# Credenciales que usan los flujos -> nombre que deben tener en n8n.
CREDENCIALES = {
    "httpHeaderAuth": "Tienda - API",
    "smtp": "SMTP - Paso Firme",
    "gmail": "Gmail - Paso Firme",
    "telegramApi": "Telegram - Paso Firme",
    "imap": "Banco - IMAP",
    "openAiApi": "Modelo - Groq",
    "googleSheets": "Histórico - Sheets",
}


class ClienteN8n:
    def __init__(self, url: str, email: str | None, password: str | None, api_key: str | None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.token = None
        if not api_key:
            if not email or not password:
                email = input("Usuario de n8n: ").strip()
                password = getpass("Contrasena de n8n: ")
            self.token = self._login(email, password)

    def _login(self, email: str, password: str) -> str:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        cuerpo = json.dumps({"emailOrLdapLoginId": email, "password": password}).encode()
        peticion = urllib.request.Request(
            self.url + "/rest/login", cuerpo, {"Content-Type": "application/json"}
        )
        opener.open(peticion, timeout=30)
        for c in cj:
            if c.name == "n8n-auth":
                return c.value
        raise RuntimeError("n8n no ha devuelto la cookie de sesion")

    def _peticion(self, metodo: str, ruta: str, cuerpo=None):
        peticion = urllib.request.Request(self.url + ruta, method=metodo)
        peticion.add_header("Content-Type", "application/json")
        if self.api_key:
            peticion.add_header("X-N8N-API-KEY", self.api_key)
        elif self.token:
            peticion.add_header("Cookie", f"n8n-auth={self.token}")
        if cuerpo is not None:
            peticion.data = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        try:
            with urllib.request.urlopen(peticion, timeout=120) as r:
                datos = r.read().decode("utf-8")
                return r.status, (json.loads(datos) if datos else None)
        except urllib.error.HTTPError as e:
            datos = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(datos)
            except Exception:
                return e.code, datos

    def listar(self):
        estado, datos = self._peticion("GET", "/api/v1/workflows?limit=200")
        if estado != 200:
            raise RuntimeError(f"no se pudieron listar los flujos: {estado} {datos}")
        return datos.get("data", [])

    def crear(self, flujo):
        # 'active' es de solo lectura en la API: se quita antes de crear.
        cuerpo = {k: v for k, v in flujo.items() if k != "active"}
        estado, datos = self._peticion("POST", "/api/v1/workflows", cuerpo)
        if estado not in (200, 201):
            raise RuntimeError(f"no se pudo importar '{flujo.get('name')}': {estado} {datos}")
        return datos.get("id") or datos.get("data", {}).get("id")

    def actualizar(self, flujo_id, flujo):
        cuerpo = {
            "name": flujo["name"],
            "nodes": flujo["nodes"],
            "connections": flujo["connections"],
            "settings": flujo.get("settings", {}),
            "pinData": flujo.get("pinData", {}),
        }
        estado, datos = self._peticion("PUT", f"/api/v1/workflows/{flujo_id}", cuerpo)
        if estado not in (200, 204):
            raise RuntimeError(f"no se pudo actualizar '{flujo['name']}': {estado} {datos}")

    def credenciales(self):
        estado, datos = self._peticion("GET", "/api/v1/credentials?limit=100")
        if estado != 200:
            return {}
        return {c["name"]: c["id"] for c in datos.get("data", [])}


def leer_flujos():
    flujos = []
    for ruta in sorted(CARPETA_FLUJOS.glob("*.json")):
        with open(ruta, encoding="utf-8") as f:
            flujos.append((ruta, json.load(f)))
    return flujos


def sustituir_texto(texto: str, ids_flujos: dict[str, str]) -> str:
    for marcador, nombre in DESTINOS.items():
        real = ids_flujos.get(nombre)
        if real:
            texto = texto.replace(marcador, real)
    return texto


def enlazar(flujo: dict, ids_flujos: dict[str, str], ids_cred: dict[str, str]) -> bool:
    """Sustituye marcadores e ids de credenciales. Devuelve True si ha cambiado algo."""
    cambios = False
    for nodo in flujo.get("nodes", []):
        params = nodo.get("parameters", {})
        ref = params.get("workflowId")
        if isinstance(ref, dict) and str(ref.get("value", "")).startswith("PENDIENTE_ID_"):
            texto = json.dumps(flujo, ensure_ascii=False)
            texto = sustituir_texto(texto, ids_flujos)
            flujo.clear()
            flujo.update(json.loads(texto))
            cambios = True
            break
    for nodo in flujo.get("nodes", []):
        for tipo, cred in (nodo.get("credentials") or {}).items():
            if tipo in CREDENCIALES:
                nombre = CREDENCIALES[tipo]
                real = ids_cred.get(nombre)
                if real and cred.get("id") != real:
                    nodo["credentials"][tipo] = {"id": real, "name": nombre}
                    cambios = True
    return cambios


def main() -> int:
    ap = argparse.ArgumentParser(description="Importa y enlaza los flujos de workflows/ en n8n")
    ap.add_argument("--url", default=os.getenv("N8N_URL", "http://localhost:5678"))
    ap.add_argument("--email", default=os.getenv("N8N_EMAIL"))
    ap.add_argument("--password", default=os.getenv("N8N_PASSWORD"))
    ap.add_argument("--api-key", default=os.getenv("N8N_API_KEY"))
    ap.add_argument("--solo-enlazar", action="store_true", help="no importa, solo arregla los ids")
    ap.add_argument("--dry-run", action="store_true", help="no modifica nada")
    args = ap.parse_args()

    cliente = ClienteN8n(args.url, args.email, args.password, args.api_key)
    flujos = leer_flujos()
    if not flujos:
        print("No hay flujos en", CARPETA_FLUJOS)
        return 1

    print(f"{len(flujos)} flujos en {CARPETA_FLUJOS}")

    # 1. Importar (si toca) para que n8n asigne ids.
    if not args.solo_enlazar and not args.dry_run:
        existentes = {w["name"]: w["id"] for w in cliente.listar()}
        for ruta, flujo in flujos:
            if flujo["name"] in existentes:
                print(f"  · ya existe: {flujo['name']} ({existentes[flujo['name']]})")
                continue
            nuevo_id = cliente.crear(flujo)
            print(f"  + importado: {flujo['name']} -> {nuevo_id}")

    # 2. Resolver ids.
    ids_flujos = {w["name"]: w["id"] for w in cliente.listar()}
    ids_cred = cliente.credenciales()
    print("Credenciales en n8n:", ", ".join(sorted(ids_cred)) or "(ninguna)")

    # 3. Enlazar y volver a subir.
    for ruta, flujo in flujos:
        cambio = enlazar(flujo, ids_flujos, ids_cred)
        if cambio:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(flujo, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"  ~ enlazado: {ruta.name}")
        else:
            print(f"  = ids ya resueltos: {ruta.name}")
        # El flujo local siempre se sube: asi los cambios de nodos tambien llegan a n8n.
        if not args.dry_run and flujo["name"] in ids_flujos:
            cliente.actualizar(ids_flujos[flujo["name"]], flujo)

    if args.dry_run:
        print("\n--dry-run: no se ha modificado nada")
    else:
        print("\nListo. Ya puedes publicar los flujos desde n8n (boton Publish).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
