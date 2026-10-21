"""CONTROLADOR · Utilidades: descargar los datos en Excel. La URL está en routes/utilidades.py."""

import io
from datetime import date

from fastapi.responses import StreamingResponse
from openpyxl import Workbook

import database
from models import apartado

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def excel():
    hojas = {
        "Apartados": (["id", "fecha", "cliente", "telefono", "email", "producto", "talla", "precio", "abonado",
                       "pendiente", "fecha_limite", "estado"], apartado.listar()[0]),
        "Abonos": (["id", "apartado_id", "fecha", "importe", "forma_pago"],
                   database.consultar("SELECT * FROM abonos ORDER BY fecha, id")),
        "Ventas": (["id", "fecha", "concepto", "importe", "forma_pago"],
                   database.consultar("SELECT * FROM ventas ORDER BY fecha, id")),
        "Vales": (["id", "codigo", "apartado_id", "fecha", "importe", "usado"],
                  database.consultar("SELECT * FROM vales ORDER BY fecha, id")),
    }
    libro = Workbook()
    libro.remove(libro.active)
    for nombre, (columnas, filas) in hojas.items():
        hoja = libro.create_sheet(nombre)
        hoja.append(columnas)
        for fila in filas:
            hoja.append([fila[c] for c in columnas])
    memoria = io.BytesIO()
    libro.save(memoria)
    memoria.seek(0)
    return StreamingResponse(memoria, media_type=XLSX,
                             headers={"Content-Disposition": f'attachment; filename="paso-firme-{date.today()}.xlsx"'})
