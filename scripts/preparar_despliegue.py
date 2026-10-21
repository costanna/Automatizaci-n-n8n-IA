#!/usr/bin/env python
"""Prepara el despliegue en la nube: exporta lo que hace falta y avisa de lo que falta.

Qué hace:

1. Exporta las **credenciales** de n8n a `deploy/credenciales/` (una por fichero, **en claro**).
   Sin esto, la instancia de la nube se queda sin credenciales: los flujos no pueden llamar a la
   API de la tienda, ni enviar correos, ni hablar con el modelo.
2. Exporta los **flujos** a `deploy/flujos/`, por si se quieren subir a mano.
3. Escribe `deploy/ENTORNO.txt` con las variables que hay que poner en la nube.
4. Avisa de lo que falta: si no hay credencial de Telegram, de SMTP o del modelo, el despliegue
   no va a funcionar entero.

Ojo: `deploy/credenciales/` contiene **secretos en texto plano** y está en el `.gitignore`.
No lo subas a ningún repositorio ni lo mandes por correo: al importar la instancia en la nube
bórralo.

Uso:
    python scripts/preparar_despliegue.py
    python scripts/preparar_despliegue.py --contenedor n8n
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO_CRED = RAIZ / "deploy" / "credenciales"
DESTINO_FLUJOS = RAIZ / "deploy" / "flujos"

CREDENCIALES_NECESARIAS = {
    "Tienda - API": "Sin ella, ningún flujo puede llamar a la API de la tienda.",
    "SMTP - Paso Firme": "Sin ella, no se manda ningún correo.",
    "Telegram - Paso Firme": "Sin ella, el bot no responde.",
    "Telegram - Token del bot": "Sin ella, el webhook del bot rechaza los updates con un 403.",
    "Modelo - Groq": "Opcional: sin ella, el flujo 3 usa el extractor por expresiones regulares.",
    "Banco - IMAP": "Opcional: sin ella, el flujo 3 solo lee los correos por el webhook de prueba.",
}

VARIABLES = """# Variables de entorno para la instancia de n8n en la nube
# (en Render: Environment; en otro sitio, el equivalente).

# La URL publica con la que se llega a n8n. Render te la da al crear el servicio.
WEBHOOK_URL=https://<tu-servicio>.onrender.com
N8N_WEBHOOK_URL=https://<tu-servicio>.onrender.com/

# La clave con la que se cifran las credenciales. La misma en el servicio web y en el
# cron de copias: sin ella, las copias de seguridad no se pueden descifrar.
N8N_ENCRYPTION_KEY=<generala-y-no-la-cambies>

# Zona horaria
GENERIC_TIMEZONE=Europe/Madrid
TZ=Europe/Madrid

# Base de datos (si usas el perfil de Postgres del docker-compose)
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=<la-que- pongas>

# Si hay un proxy que intercepta el TLS, anade su certificado en vez de esto:
# NODE_EXTRA_CA_CERTS=/ruta/ca.crt
"""


def log(mensaje: str) -> None:
    print(f"[despliegue] {mensaje}", flush=True)


def en_contenedor(contenedor: str, argumentos: list[str]) -> tuple[int, str]:
    resultado = subprocess.run(
        ["docker", "exec", contenedor, "n8n", *argumentos],
        capture_output=True, text=True,
    )
    return resultado.returncode, (resultado.stdout + resultado.stderr)


def preparar_carpeta(contenedor: str, ruta: str) -> None:
    """Crea la carpeta dentro del contenedor: la CLI no la crea, y si el nombre existe
    como fichero se lia."""
    subprocess.run(
        ["docker", "exec", contenedor, "sh", "-c", f"rm -rf {ruta} && mkdir -p {ruta}"],
        capture_output=True, text=True,
    )


def traer_carpeta(contenedor: str, ruta: str, destino: Path) -> int:
    """Se trae la carpeta del contenedor. Devuelve cuantos ficheros JSON hay."""
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)
    resultado = subprocess.run(
        ["docker", "cp", f"{contenedor}:{ruta}/.", str(destino)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        log(f"no se pudo traer {ruta}: {resultado.stderr.strip()[:160]}")
        return 0
    return len(list(destino.glob("*.json")))


def exportar_credenciales(contenedor: str) -> list[str]:
    # --decrypted: la instancia de la nube tendra otra clave de cifrado, asi que las
    # credenciales tienen que viajar en claro (por eso la carpeta esta en el .gitignore).
    preparar_carpeta(contenedor, "/tmp/credenciales")
    codigo, salida = en_contenedor(
        contenedor,
        ["export:credentials", "--backup", "--decrypted", "--output", "/tmp/credenciales"],
    )
    if codigo != 0:
        log(f"no se pudieron exportar las credenciales: {salida.strip()[:200]}")
        return []
    total = traer_carpeta(contenedor, "/tmp/credenciales", DESTINO_CRED)
    log(f"credenciales exportadas: {total}")
    return [p.name for p in DESTINO_CRED.glob("*.json")]


def exportar_flujos(contenedor: str) -> int:
    preparar_carpeta(contenedor, "/tmp/flujos")
    codigo, salida = en_contenedor(
        contenedor, ["export:workflow", "--all", "--separate", "--output", "/tmp/flujos"])
    if codigo != 0:
        log(f"no se pudieron exportar los flujos: {salida.strip()[:200]}")
        return 0
    total = traer_carpeta(contenedor, "/tmp/flujos", DESTINO_FLUJOS)
    log(f"flujos exportados: {total}")
    return total


def comprobar_credenciales() -> None:
    if not DESTINO_CRED.exists():
        return
    encontradas = []
    for ruta in DESTINO_CRED.glob("*.json"):
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(datos, dict):
            encontradas.append(datos.get("name", "?"))
    print()
    print("Credenciales exportadas:")
    for nombre, aviso in CREDENCIALES_NECESARIAS.items():
        marca = "OK   " if nombre in encontradas else "FALTA"
        print(f"  {marca} {nombre}: {aviso}")
    faltan = [n for n in CREDENCIALES_NECESARIAS if n not in encontradas]
    if faltan:
        print()
        print("  Las que faltan hay que crearlas a mano en la nube (Credentials -> New):")
        for nombre in faltan:
            print(f"    - {nombre}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepara el despliegue en la nube")
    ap.add_argument("--contenedor", default="n8n", help="nombre del contenedor de n8n")
    args = ap.parse_args()

    print()
    print("OJO: deploy/credenciales/ tiene las claves EN CLARO. Esta en el .gitignore:")
    print("      no lo subas a ningun repositorio ni lo mandes por correo.")
    print("      Cuando importes las credenciales en la nube, borra esa carpeta.")
    print()

    ficheros = exportar_credenciales(args.contenedor)
    exportar_flujos(args.contenedor)

    (RAIZ / "deploy" / "ENTORNO.txt").write_text(VARIABLES, encoding="utf-8")
    log("variables de entorno escritas en deploy/ENTORNO.txt")

    comprobar_credenciales()

    print()
    print("Pasos siguientes (en docs/despliegue.md):")
    print("  1. Crea el servicio en Render con deploy/render.yaml")
    print("  2. Pon las variables de deploy/ENTORNO.txt en el servicio")
    print("  3. Importa las credenciales (por el shell del servicio):")
    print("       n8n import:credentials --separate --input=/ruta/a/las/credenciales")
    print("  4. Publica los flujos (en el editor o con scripts/enlazar_flujos.py)")
    print("  5. Comprueba el HTTPS: curl -I https://<tu-servicio>.onrender.com/healthz")
    if not ficheros:
        print()
        print("  No se ha exportado ninguna credencial: comprueba que el contenedor se llama "
              f"'{args.contenedor}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
