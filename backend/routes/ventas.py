"""RUTAS · Ventas: qué URL llega a qué función del controlador."""

from fastapi import APIRouter, Depends

from controllers import ventas
from middleware.seguridad import exigir_clave
from schemas.venta import VentaOut

router = APIRouter(prefix="/api/ventas", tags=["consultas"], dependencies=[Depends(exigir_clave)])

router.get("", response_model=list[VentaOut], summary="Ventas entre dos fechas (incluidas)")(ventas.listar)
router.post("", response_model=VentaOut, status_code=201, summary="Registrar una venta")(ventas.registrar)
