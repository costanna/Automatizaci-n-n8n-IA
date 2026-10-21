"""RUTAS · Vales: qué URL llega a qué función del controlador."""

from fastapi import APIRouter, Depends

from controllers import vales
from middleware.seguridad import exigir_clave
from schemas.vale import ValeOut

router = APIRouter(prefix="/api/vales", tags=["consultas"], dependencies=[Depends(exigir_clave)])

router.get("", response_model=list[ValeOut], summary="Vales de compra generados")(vales.listar)
