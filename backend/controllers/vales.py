"""CONTROLADOR · Vales de compra generados al vencer un apartado. La URL está en routes/vales.py."""

from models import vale


def listar():
    return vale.listar()
