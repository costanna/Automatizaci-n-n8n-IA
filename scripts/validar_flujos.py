#!/usr/bin/env python
"""Valida los flujos de `workflows/` antes de importarlos en n8n.

Comprueba:
  - que cada JSON es válido y tiene la forma mínima de un flujo de n8n;
  - que todas las conexiones apuntan a nodos que existen;
  - que no hay credenciales escritas dentro de los flujos;
  - que las URLs de la tienda usan el nombre del servicio (`http://tienda:8000`), no `localhost`;
  - que no queda ningún marcador `PENDIENTE_ID_*` sin resolver.

Uso:
    python scripts/validar_flujos.py
    python scripts/validar_flujos.py --carpeta workflows
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Cosas que NO deben aparecer dentro de un flujo.
PATRONES_SECRETOS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "una clave de modelo (sk-...)"),
    (re.compile(r"(?i)(api[_-]?key|apikey|clave_api)\s*[:=]\s*['\"][^'\"]{6,}['\"]"), "una clave de API en claro"),
    (re.compile(r"(?i)(password|passwd|contrasena|contraseña)\s*[:=]\s*['\"][^'\"]{4,}['\"]"), "una contraseña en claro"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"), "un token bearer"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."), "un JWT"),
]

NODOS_OBLIGATORIOS = ("id", "name", "type", "typeVersion", "position")


def texto_del_flujo(flujo: dict) -> str:
    return json.dumps(flujo, ensure_ascii=False)


def validar(ruta: Path) -> list[str]:
    errores: list[str] = []
    try:
        flujo = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{ruta.name}: JSON invalido ({e})"]

    for clave in ("name", "nodes", "connections"):
        if clave not in flujo:
            errores.append(f"{ruta.name}: falta la clave '{clave}'")

    nodos = flujo.get("nodes", [])
    if not nodos:
        errores.append(f"{ruta.name}: el flujo no tiene nodos")

    nombres: set[str] = set()
    ids: set[str] = set()
    for nodo in nodos:
        for clave in NODOS_OBLIGATORIOS:
            if clave not in nodo:
                errores.append(f"{ruta.name}: el nodo {nodo.get('id', '?')} no tiene '{clave}'")
        nombre = nodo.get("name")
        if nombre:
            if nombre in nombres:
                errores.append(f"{ruta.name}: hay dos nodos con el nombre '{nombre}'")
            nombres.add(nombre)
        identificador = nodo.get("id")
        if identificador in ids:
            errores.append(f"{ruta.name}: hay dos nodos con el id '{identificador}'")
        ids.add(identificador)

    for origen, conexiones in (flujo.get("connections") or {}).items():
        if origen not in nombres:
            errores.append(f"{ruta.name}: la conexion '{origen}' no viene de ningun nodo")
        for tipo, ramas in (conexiones or {}).items():
            for rama in ramas or []:
                for destino in rama or []:
                    if destino.get("node") not in nombres:
                        errores.append(
                            f"{ruta.name}: la conexion '{origen}' -> '{destino.get('node')}' no apunta a ningun nodo"
                        )

    texto = texto_del_flujo(flujo)
    for patron, descripcion in PATRONES_SECRETOS:
        if patron.search(texto):
            errores.append(f"{ruta.name}: parece que hay {descripcion} dentro del flujo")

    if "localhost:8000" in texto:
        errores.append(
            f"{ruta.name}: usa 'localhost:8000'. Dentro de n8n hay que poner 'http://tienda:8000'"
        )

    for marcador in set(re.findall(r"PENDIENTE_ID_[A-Z0-9_]+", texto)):
        errores.append(
            f"{ruta.name}: queda sin resolver el marcador {marcador} "
            "(ejecuta scripts/enlazar_flujos.py)"
        )

    return errores


def main() -> int:
    ap = argparse.ArgumentParser(description="Valida los flujos de n8n del repositorio")
    ap.add_argument("--carpeta", default=str(RAIZ / "workflows"))
    args = ap.parse_args()

    carpeta = Path(args.carpeta)
    rutas = sorted(carpeta.glob("*.json"))
    if not rutas:
        print(f"No hay flujos en {carpeta}")
        return 1

    total = 0
    for ruta in rutas:
        errores = validar(ruta)
        if errores:
            total += len(errores)
            print(f"FAIL {ruta.name}")
            for e in errores:
                print(f"     - {e}")
        else:
            print(f"OK   {ruta.name}")

    print()
    if total:
        print(f"{total} problema(s) encontrados en {len(rutas)} flujo(s).")
        return 1
    print(f"{len(rutas)} flujo(s) correctos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
