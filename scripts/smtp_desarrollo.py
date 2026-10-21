#!/usr/bin/env python
"""Servidor SMTP mínimo para desarrollo: guarda los correos que envía n8n.

No es un servidor de correo: solo habla SMTP suficiente para que el nodo `emailSend` de n8n
entregue el mensaje, y lo escribe en `data/envios/` (asunto, destinatario y cuerpo).

Uso:
    python scripts/smtp_desarrollo.py [--port 1025] [--salida data/envios]

Para que n8n (que corre en Docker) lo alcance, el contenedor usa el host:
    host: host.docker.internal   puerto: 1025
"""

from __future__ import annotations

import argparse
import email
import os
import re
import socket
import socketserver
import threading
from datetime import datetime, timezone

BANNER = "SMTP de desarrollo · Paso Firme"


def sanitize(nombre: str) -> str:
    """Convierte el nombre del fichero en algo seguro para Windows."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", nombre).strip("-") or "mensaje"


class Handler(socketserver.StreamRequestHandler):
    def _send(self, linea: str) -> None:
        self.wfile.write((linea + "\r\n").encode("utf-8"))
        self.wfile.flush()

    def handle(self) -> None:
        self._send(f"220 {BANNER}")
        remitente = ""
        destinatarios: list[str] = []
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            linea = raw.decode("utf-8", "replace").strip()
            if not linea:
                continue
            comando = linea.split(" ")[0].upper()

            if comando in ("HELO", "EHLO"):
                self._send("250-OK")
                self._send("250 SIZE 10485760")
            elif comando == "MAIL":
                m = re.search(r"FROM:\s*<([^>]*)>", linea, re.I)
                remitente = m.group(1) if m else ""
                self._send("250 OK")
            elif comando == "RCPT":
                m = re.search(r"TO:\s*<([^>]*)>", linea, re.I)
                if m:
                    destinatarios.append(m.group(1))
                self._send("250 OK")
            elif comando == "DATA":
                self._send("354 End data with <CR><LF>.<CR><LF>")
                lineas = []
                while True:
                    buf = self.rfile.readline()
                    if not buf or buf in (b".\r\n", b".\n"):
                        break
                    lineas.append(buf.decode("utf-8", "replace"))
                cuerpo = "".join(lineas)
                self.guardar(remitente, destinatarios, cuerpo)
                self._send("250 OK: mensaje guardado")
            elif comando == "RSET":
                remitente, destinatarios = "", []
                self._send("250 OK")
            elif comando == "NOOP":
                self._send("250 OK")
            elif comando == "QUIT":
                self._send("221 Bye")
                return
            else:
                self._send("250 OK")

    def guardar(self, remitente: str, destinatarios: list[str], cuerpo: str) -> None:
        msg = email.message_from_string(cuerpo)
        # El asunto llega codificado (MIME); se decodifica para poder leerlo.
        asunto = str(email.header.make_header(email.header.decode_header(msg.get("Subject", "(sin asunto)"))))
        destino = ", ".join(destinatarios) or "(sin destinatario)"
        ahora = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        nombre = sanitize(f"{ahora}-{destinatarios[0] if destinatarios else 'sin-destinatario'}.eml")
        ruta = os.path.join(self.server.salida, nombre)

        # Se guarda tambien el texto plano descodificado, que es lo que se lee en las pruebas.
        texto_plano = ""
        for parte in msg.walk():
            if parte.get_content_type() == "text/plain":
                try:
                    texto_plano = parte.get_payload(decode=True).decode(parte.get_content_charset() or "utf-8", "replace")
                except Exception:
                    texto_plano = str(parte.get_payload())
                break

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(cuerpo)
        # Ademas se escribe un .txt con los datos y el texto plano descodificados:
        # es lo que leen las pruebas y lo que se lee a pelo en una demo.
        with open(ruta[:-4] + ".txt", "w", encoding="utf-8") as f:
            f.write(f"Remitente: {remitente}\n")
            f.write(f"Destinatarios: {destino}\n")
            f.write(f"Fecha: {ahora}\n")
            f.write(f"Asunto: {asunto}\n")
            f.write("-" * 60 + "\n")
            f.write(texto_plano)
            f.write("\n")
        self.server.enviados.append((nombre, asunto, destino))
        print(f"[smtp] guardado {nombre} | para {destino} | {asunto}", flush=True)


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr, salida: str):
        super().__init__(addr, Handler)
        self.salida = salida
        self.enviados: list[tuple[str, str, str]] = []


def main() -> None:
    ap = argparse.ArgumentParser(description="Servidor SMTP de desarrollo para n8n")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=1025)
    ap.add_argument("--salida", default=os.path.join("data", "envios"))
    args = ap.parse_args()

    os.makedirs(args.salida, exist_ok=True)
    servidor = Servidor((args.host, args.port), args.salida)
    print(f"[smtp] escuchando en {args.host}:{args.port} -> {args.salida}", flush=True)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n[smtp] parando", flush=True)
        servidor.shutdown()


if __name__ == "__main__":
    main()
