"""RUTAS · Abonos: qué URL llega a qué función del controlador."""

from fastapi import APIRouter, Depends

from controllers import abonos
from middleware.seguridad import exigir_clave
from schemas.abono import AbonoOut

router = APIRouter(prefix="/api/abonos", tags=["consultas"], dependencies=[Depends(exigir_clave)])

router.get("", response_model=list[AbonoOut], summary="Abonos entre dos fechas (incluidas)")(abonos.listar)
