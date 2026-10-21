"""SCHEMAS · Vale."""

from datetime import date

from pydantic import BaseModel


class ValeOut(BaseModel):
    id: int
    codigo: str
    apartado_id: int
    fecha: date
    importe: float
    usado: int
