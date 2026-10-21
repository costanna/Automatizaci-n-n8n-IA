"""SCHEMAS · Venta: la forma de los datos que entran y salen por la API."""

from datetime import date

from pydantic import BaseModel


class VentaIn(BaseModel):
    concepto: str
    importe: float
    forma_pago: str = "efectivo"
    fecha: date | None = None


class VentaOut(BaseModel):
    id: int
    fecha: date
    concepto: str
    importe: float
    forma_pago: str
