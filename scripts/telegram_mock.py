#!/usr/bin/env python
"""Mock de la API de Telegram para probar el bot.

Implementa lo que necesita el bot (flujo `14 · Asistente de Telegram`):

* n8n recibe los updates por un webhook propio (`/webhook/telegram`) con la cabecera
  `X-Telegram-Bot-Api-Secret-Token`; el mock la pone.
* Cuando el bot responde, n8n llama a `sendMessage` al `baseUrl` de la credencial; el
  mock lo guarda.

Para usarlo:
    python scripts/telegram_mock.py --puerto 8081 \
        --url http://localhost:5678/webhook/telegram \
        --secreto paso-firme-token-bot-2026

Endpoints:
* `POST /_inyectar`  {"chat_id":"111111","text":"¿cuánto me falta?","first_name":"Ana"}
* `GET  /_enviados`  los mensajes que el bot ha enviado
* `GET  /_config`    la configuracion con la que se ha arrancado
* `POST /_vaciar`    limpia la lista de enviados
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ESTADO = {"enviados": [], "url": None, "secreto": None}
CANDADO = threading.Lock()


class Manejador(BaseHTTPRequestHandler):
    server_version = "TelegramMock/1.0"

    def log_message(self, formato, *args):
        # Cada peticion se apunta: asi se ve a donde va el bot de verdad.
        print(f"[telegram-mock] {self.command} {self.path}", flush=True)

    def _json(self, codigo: int, datos) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _cuerpo(self):
        largo = int(self.headers.get("Content-Length") or 0)
        if not largo:
            return {}
        try:
            return json.loads(self.rfile.read(largo).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        if self.path.startswith("/_enviados"):
            with CANDADO:
                return self._json(200, {"ok": True, "result": list(ESTADO["enviados"])})
        if self.path.startswith("/_config"):
            with CANDADO:
                return self._json(200, {"ok": True, "result": {"url": ESTADO["url"], "secreto": ESTADO["secreto"]}})
        if re.match(r"^/bot[^/]+/getMe", self.path):
            return self._json(200, {"ok": True, "result": {"id": 1234567890, "is_bot": True,
                                                              "first_name": "Paso Firme", "username": "pasofirme_bot"}})
        return self._json(404, {"ok": False, "error_code": 404, "description": "Not Found"})

    def do_POST(self):
        if self.path.startswith("/_inyectar"):
            return self._entregar(self._cuerpo())
        if self.path.startswith("/_vaciar"):
            with CANDADO:
                ESTADO["enviados"].clear()
            return self._json(200, {"ok": True})
        if re.match(r"^/bot[^/]+/setWebhook", self.path):
            datos = self._cuerpo()
            with CANDADO:
                ESTADO["url"] = datos.get("url")
                ESTADO["secreto"] = datos.get("secret_token")
            print(f"[telegram-mock] n8n quiere los updates en {datos.get('url')}", flush=True)
            return self._json(200, {"ok": True, "result": True})
        if re.match(r"^/bot[^/]+/deleteWebhook", self.path):
            return self._json(200, {"ok": True, "result": True})
        if re.match(r"^/bot[^/]+/sendMessage", self.path):
            datos = self._cuerpo()
            mensaje = {
                "message_id": len(ESTADO["enviados"]) + 1,
                "from": {"id": 1, "is_bot": True, "first_name": "Paso Firme", "username": "pasofirme_bot"},
                "chat": {"id": int(datos.get("chat_id") or 0), "type": "private"},
                "date": int(time.time()),
                "text": datos.get("text", ""),
            }
            with CANDADO:
                ESTADO["enviados"].append(mensaje)
            print(f"[telegram-mock] enviado al chat {datos.get('chat_id')}: {datos.get('text', '')[:100]}", flush=True)
            return self._json(200, {"ok": True, "result": mensaje})
        return self._json(404, {"ok": False, "error_code": 404, "description": "Not Found"})

    def _entregar(self, datos: dict) -> None:
        """Manda el update al webhook de n8n, igual que haria Telegram."""
        with CANDADO:
            url = ESTADO["url"]
            secreto = ESTADO["secreto"]
        if not url:
            return self._json(400, {"ok": False, "error_code": 400,
                                    "description": "falta --url (donde recibe n8n los updates)"})

        ahora = int(time.time())
        update = {
            "update_id": ahora % 1000000,
            "message": {
                "message_id": ahora % 100000,
                "from": {
                    "id": int(datos.get("chat_id") or 0),
                    "is_bot": False,
                    "first_name": datos.get("first_name", "Cliente"),
                    "username": datos.get("username", "cliente"),
                },
                "chat": {
                    "id": int(datos.get("chat_id") or 0),
                    "type": "private",
                    "first_name": datos.get("first_name", "Cliente"),
                },
                "date": ahora,
                "text": datos.get("text", ""),
            },
        }

        peticion = urllib.request.Request(
            url, json.dumps(update).encode("utf-8"), {"Content-Type": "application/json"}, method="POST")
        if secreto:
            peticion.add_header("X-Telegram-Bot-Api-Secret-Token", secreto)
        try:
            with urllib.request.urlopen(peticion, timeout=30) as r:
                estado = r.status
        except urllib.error.HTTPError as e:
            estado = e.code
        except Exception as e:
            estado = str(e)[:80]
        print(f"[telegram-mock] update entregado a {url} -> {estado}", flush=True)
        return self._json(200, {"ok": True, "entregado": estado})


def main() -> int:
    ap = argparse.ArgumentParser(description="Mock de la API de Telegram para pruebas")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--puerto", type=int, default=8081)
    ap.add_argument("--url", default="http://localhost:5678/webhook/telegram",
                    help="donde recibe n8n los updates de Telegram")
    ap.add_argument("--secreto", default="paso-firme-token-bot-2026",
                    help="valor de la cabecera X-Telegram-Bot-Api-Secret-Token")
    args = ap.parse_args()

    ESTADO["url"] = args.url
    ESTADO["secreto"] = args.secreto

    servidor = ThreadingHTTPServer((args.host, args.puerto), Manejador)
    print(f"[telegram-mock] escuchando en http://{args.host}:{args.puerto}", flush=True)
    print(f"[telegram-mock] entrega los updates en {args.url}", flush=True)
    print('[telegram-mock] para encolar un mensaje: POST /_inyectar {"chat_id":1,"text":"hola"}', flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[telegram-mock] parando", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
