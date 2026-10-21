#!/usr/bin/env python
"""Copia de seguridad de los datos de n8n.

Qué guarda:

* La base de datos de n8n (flujos, credenciales, ejecuciones y *static data*). Se copia
  con `VACUUM INTO`, que genera una copia **consistente** aunque n8n esté escribiendo.
* El archivo de configuración con la clave de cifrado (`config`): sin él, las credenciales
  de la copia no se pueden descifrar.
* Los JSON de `workflows/`: el código fuente de los flujos, que se pueden volver a importar.

Dónde los guarda: una carpeta con la fecha y la hora. Se borran las copias viejas según
`--conservar` (14 por defecto: dos semanas).

Uso:
    # desde el host, con la tienda y n8n levantados
    python scripts/backup_n8n.py --contenedor n8n

    # dentro de un contenedor que tenga montado el volumen de n8n
    python scripts/backup_n8n.py --datos /home/node/.n8n --destino /backups

    # si n8n usa Postgres en vez de SQLite
    python scripts/backup_n8n.py --postgres "postgresql://n8n:clave@postgres:5432/n8n"
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def log(mensaje: str) -> None:
    print(f"[backup] {mensaje}", flush=True)


def copiar_de_contenedor(contenedor: str, ruta: str, destino: Path, obligatorio: bool = True) -> bool:
    """Saca un fichero del contenedor a un temporal local."""
    temporal = Path(tempfile.mkdtemp()) / Path(ruta).name
    resultado = subprocess.run(
        ["docker", "cp", f"{contenedor}:{ruta}", str(temporal)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0 or not temporal.exists():
        if obligatorio:
            log(f"no se pudo copiar {ruta} del contenedor {contenedor}: {resultado.stderr.strip()[:120]}")
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(temporal, destino)
    return True


def copia_consistente(db_origen: Path, db_destino: Path) -> bool:
    """Copia la base de datos con VACUUM INTO (copia consistente)."""
    try:
        conexion = sqlite3.connect(f"file:{db_origen}?mode=ro", uri=True)
        conexion.execute("VACUUM INTO ?", (str(db_destino),))
        conexion.close()
        return True
    except sqlite3.Error as e:
        log(f"no se pudo hacer la copia consistente: {e}")
        # Si falla (por ejemplo, si la base esta bloqueada), se copia a pelo.
        try:
            shutil.copy2(db_origen, db_destino)
            return True
        except OSError as e2:
            log(f"tampoco se pudo copiar a pelo: {e2}")
            return False


def backup_sqlite(datos: Path, destino: Path) -> bool:
    origen = datos / "database.sqlite"
    if not origen.exists():
        log(f"no esta la base de datos en {origen}")
        return False
    destino.mkdir(parents=True, exist_ok=True)
    if not copia_consistente(origen, destino / "database.sqlite"):
        return False
    # La clave de cifrado: sin ella, las credenciales de la copia no sirven.
    config = datos / "config"
    if config.exists():
        shutil.copy2(config, destino / "config")
    # Los static data que guardan los flujos (solicitudes, recordatorios, cobros...).
    static = datos / "workflows"
    if static.exists():
        shutil.copytree(static, destino / "workflows", dirs_exist_ok=True)
    return True


def backup_postgres(url: str, destino: Path) -> bool:
    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / "n8n-postgres.sql"
    resultado = subprocess.run(
        ["pg_dump", "--clean", "--if-exists", url, "-f", str(salida)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        log(f"fallo el pg_dump: {resultado.stderr.strip()[:200]}")
        return False
    return True


def limpiar(destino: Path, conservar: int) -> None:
    copias = sorted([p for p in destino.glob("n8n-*") if p.is_dir()], reverse=True)
    for copia in copias[conservar:]:
        shutil.rmtree(copia, ignore_errors=True)
        log(f"borrada la copia vieja {copia.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Copia de seguridad de los datos de n8n")
    ap.add_argument("--datos", default=None, help="carpeta de datos de n8n (dentro del contenedor)")
    ap.add_argument("--contenedor", default=None, help="nombre del contenedor de n8n (por defecto 'n8n')")
    ap.add_argument("--destino", default=str(RAIZ / "backups"), help="carpeta donde se guardan las copias")
    ap.add_argument("--conservar", type=int, default=14, help="cuantas copias se conservan")
    ap.add_argument("--postgres", default=None, help="URL de Postgres (si n8n no usa SQLite)")
    args = ap.parse_args()

    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)
    momento = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    carpeta = destino / f"n8n-{momento}"

    ok = False
    if args.postgres:
        log(f"copia de Postgres -> {carpeta}")
        ok = backup_postgres(args.postgres, carpeta)
    else:
        temporal = Path(tempfile.mkdtemp())
        if args.contenedor:
            log(f"copiando los datos del contenedor {args.contenedor}")
            copiar_de_contenedor(args.contenedor, "/home/node/.n8n/database.sqlite", temporal / "database.sqlite")
            copiar_de_contenedor(args.contenedor, "/home/node/.n8n/config", temporal / "config")
            # Los static data en fichero solo existen en algunas versiones: si no hay, no pasa nada.
            copiar_de_contenedor(args.contenedor, "/home/node/.n8n/workflows", temporal / "workflows", obligatorio=False)
            origen = temporal
        else:
            origen = Path(args.datos or "/home/node/.n8n")
        if origen.exists():
            ok = backup_sqlite(origen, carpeta)
        else:
            log(f"no existe {origen}: usa --contenedor o --datos")

    if ok:
        # Los JSON de los flujos, que son el codigo fuente.
        flujos = RAIZ / "workflows"
        if flujos.exists():
            shutil.copytree(flujos, carpeta / "workflows-json", dirs_exist_ok=True)
        (carpeta / "info.json").write_text(
            json.dumps({"fecha": momento, "version": "1.0.0"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log(f"copia guardada en {carpeta}")
    else:
        log("no se ha podido hacer la copia")
        return 1

    limpiar(destino, args.conservar)
    log(f"copias guardadas: {len(list(destino.glob('n8n-*')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
