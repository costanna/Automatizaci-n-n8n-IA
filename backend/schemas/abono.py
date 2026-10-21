"""SCHEMAS · Abono: la forma de los datos que entran y salen por la API."""

from datetime import date

from pydantic import BaseModel


class AbonoIn(BaseModel):
    importe: float
    forma_pago: str = "efectivo"
    fecha: date | None = None


class AbonoOut(BaseModel):
    id: int
    apartado_id: int
    fecha: date
    importe: float
    forma_pago: str
