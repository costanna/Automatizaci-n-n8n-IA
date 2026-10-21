"""MIDDLEWARE · Seguridad: comprobar la clave de la API (cabecera X-API-Key) antes de llegar al controlador.

Las rutas de la API la piden con `dependencies=[Depends(exigir_clave)]`; las páginas no.
"""

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

import config

# Declarar la cabecera como esquema de seguridad es lo que hace aparecer el botón Authorize en /docs.
cabecera_clave = APIKeyHeader(name="X-API-Key", auto_error=False)


def exigir_clave(clave: str | None = Depends(cabecera_clave)):
    if not config.API_KEY or clave != config.API_KEY:
        raise HTTPException(401, "Falta la cabecera X-API-Key o no es válida")
