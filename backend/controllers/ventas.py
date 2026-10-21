"""CONTROLADOR · Ventas: consultar y registrar ventas directas. Las URL están en routes/ventas.py."""

from datetime import date

from fastapi import BackgroundTasks, Response

from models import venta
from schemas.venta import VentaIn
from services import n8n


def listar(response: Response, desde: date | None = None, hasta: date | None = None, orden: str = "asc",
           pagina: int | None = None, por_pagina: int = 25):
    """Sin `pagina` devuelve todas. `orden=desc` muestra primero las más recientes."""
    limite = por_pagina if pagina else None
    ventas, total = venta.listar(desde, hasta, orden == "desc", limite, (max(pagina or 1, 1) - 1) * por_pagina)
    response.headers["X-Total-Count"] = str(total)
    return ventas


def registrar(datos: VentaIn, tareas: BackgroundTasks):
    nueva = venta.registrar(**datos.model_dump())
    tareas.add_task(n8n.avisar, "venta.registrada", nueva)
    return nueva
