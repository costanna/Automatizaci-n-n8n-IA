"""SCHEMAS · Apartado: la forma de los datos que entran y salen por la API."""

from datetime import date

from pydantic import BaseModel, Field

from schemas.abono import AbonoOut
from schemas.vale import ValeOut


class ApartadoIn(BaseModel):
    cliente: str
    telefono: str | None = None
    email: str | None = None
    producto: str
    talla: str | None = None
    precio: float = Field(gt=0)
    abono_inicial: float
    forma_pago: str = "efectivo"
    fecha: date | None = Field(None, description="Solo para migrar datos antiguos. Por defecto, hoy.")


class ApartadoOut(BaseModel):
    id: int
    fecha: date
    cliente: str
    telefono: str | None
    email: str | None
    producto: str
    talla: str | None
    precio: float
    fecha_limite: date
    estado: str
    abonado: float
    pendiente: float


class ApartadoDetalle(ApartadoOut):
    abonos: list[AbonoOut]
    vale: ValeOut | None


class Vencimiento(BaseModel):
    apartado: ApartadoOut
    vale: ValeOut


class Resumen(BaseModel):
    activo: int
    liquidado: int
    vencido: int
    total: int
