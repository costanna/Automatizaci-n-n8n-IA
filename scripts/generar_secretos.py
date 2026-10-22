#!/usr/bin/env python
"""Genera los secretos de la automatizacion en el `.env` (que no se sube a GitHub).

Que hace:
1. Crea en `.env` los secretos que falten (o todos, con --rotar): API_KEY, WEBHOOK_TOKEN,
   TELEGRAM_SECRET_TOKEN, PANEL_USUARIO y PANEL_CLAVE. El token del webhook tambien va en
   N8N_WEBHOOK_URL (`?token=...`), que es como lo manda la app.
2. Escribe en `data/config.csv` el hash SHA-256 del token (WEBHOOK_TOKEN_SHA256): el
   despachador compara hashes, asi que el token no esta en el repositorio.
3. Dice que credencial de n8n hay que rellenar con cada valor. Los valores no se imprimen:
   se copian del `.env`.

Uso:
    python scripts/generar_secretos.py           # crea los que falten
    python scripts/generar_secretos.py --rotar   # los cambia todos (si se han filtrado)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENV = RAIZ / ".env"
CONFIG = RAIZ / "data" / "config.csv"

# Telegram solo admite A-Z, a-z, 0-9, _ y - en el token secreto: token_urlsafe cumple.
SECRETOS = {
    "API_KEY": lambda: secrets.token_urlsafe(32),
    "WEBHOOK_TOKEN": lambda: secrets.token_urlsafe(32),
    "TELEGRAM_SECRET_TOKEN": lambda: secrets.token_urlsafe(32),
    "PANEL_USUARIO": lambda: "marisa",
    "PANEL_CLAVE": lambda: secrets.token_urlsafe(18),
}
# Valores de ejemplo de .env.example: si siguen ahi, se cambian aunque no se pida --rotar.
DE_EJEMPLO = {"", "cambia-esta-clave", "cambia-este-token"}

CREDENCIALES = [
    ("Tienda - API", "Header Auth", "Name: X-API-Key", "Value: API_KEY"),
    ("Webhooks - Tienda (nueva)", "Header Auth", "Name: X-Webhook-Token", "Value: WEBHOOK_TOKEN"),
    ("Telegram - Token del bot", "Header Auth", "Name: X-Telegram-Bot-Api-Secret-Token",
     "Value: TELEGRAM_SECRET_TOKEN"),
    ("Panel - Marisa (nueva)", "Basic Auth", "User: PANEL_USUARIO", "Password: PANEL_CLAVE"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera los secretos en el .env")
    ap.add_argument("--rotar", action="store_true", help="cambiar todos los secretos")
    args = ap.parse_args()

    if not ENV.exists():
        print("No hay .env: copia antes .env.example (cp .env.example .env)")
        return 1

    lineas = ENV.read_text(encoding="utf-8").splitlines()
    actuales = {l.split("=", 1)[0]: l.split("=", 1)[1] for l in lineas if "=" in l and not l.startswith("#")}
    valores, cambiados = {}, []
    for clave, generar in SECRETOS.items():
        actual = actuales.get(clave, "").strip()
        if args.rotar or actual in DE_EJEMPLO:
            valores[clave] = generar()
            cambiados.append(clave)
        else:
            valores[clave] = actual

    salida, puestas = [], set()
    for linea in lineas:
        clave = linea.split("=", 1)[0]
        if clave in valores and not linea.startswith("#"):
            linea = f"{clave}={valores[clave]}"
            puestas.add(clave)
        elif clave == "N8N_WEBHOOK_URL" and "token=" in linea:
            linea = re.sub(r"token=[^&\s]*", "token=" + valores["WEBHOOK_TOKEN"], linea)
        salida.append(linea)
    faltan = [k for k in SECRETOS if k not in puestas]
    if faltan:
        salida += ["", "# Secretos (no se suben a GitHub): los mismos valores van en las credenciales de n8n"]
        salida += [f"{k}={valores[k]}" for k in faltan]
    ENV.write_text("\n".join(salida) + "\n", encoding="utf-8")

    huella = hashlib.sha256(valores["WEBHOOK_TOKEN"].encode("utf-8")).hexdigest()
    config = [l for l in CONFIG.read_text(encoding="utf-8").splitlines()
              if not l.startswith(("WEBHOOK_TOKEN,", "WEBHOOK_TOKEN_SHA256,", "TELEGRAM_SECRET_TOKEN,"))]
    config.append(f"WEBHOOK_TOKEN_SHA256,{huella}")
    CONFIG.write_text("\n".join(config) + "\n", encoding="utf-8")

    print("Secretos nuevos en .env:", ", ".join(cambiados) or "ninguno (ya estaban)")
    print("Hash del token del webhook en data/config.csv (WEBHOOK_TOKEN_SHA256)")
    if not any(re.match(r"N8N_WEBHOOK_URL=.*token=", l) for l in salida):
        print("\nOjo: N8N_WEBHOOK_URL no lleva ?token=. Ponla asi:")
        print("  N8N_WEBHOOK_URL=http://n8n:5678/webhook/tienda?token=<el WEBHOOK_TOKEN del .env>")
    print("\nAhora, en n8n (Overview -> Credentials), copia los valores del .env:")
    for nombre, tipo, campo1, campo2 in CREDENCIALES:
        print(f"  - {nombre} [{tipo}]  {campo1}  ·  {campo2}")
    print("\nY reinicia para que la tienda y n8n lean lo nuevo:")
    print("  docker compose up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
