"""RUTAS · Utilidades: qué URL llega a qué función del controlador."""

from fastapi import APIRouter, Depends

from controllers import utilidades
from middleware.seguridad import exigir_clave

router = APIRouter(prefix="/api", tags=["utilidades"], dependencies=[Depends(exigir_clave)])

router.get("/excel", summary="Descargar todos los datos en un Excel (una hoja por tabla)")(utilidades.excel)
