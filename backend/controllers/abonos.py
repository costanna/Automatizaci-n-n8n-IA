"""CONTROLADOR · Abonos: consulta de abonos entre dos fechas. La URL está en routes/abonos.py."""

from datetime import date

from models import abono


def listar(desde: date | None = None, hasta: date | None = None):
    return abono.listar(desde, hasta)
