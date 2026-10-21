"""MODELO · Venta: las ventas directas del mostrador (sin apartado)."""

from datetime import date

import config
import database
from models.errores import ReglaDeNegocio


def listar(desde=None, hasta=None, descendente=False, limite=None, desplazamiento=0):
    """Devuelve (ventas, total) entre dos fechas (incluidas)."""
    args = [str(desde or "0000-01-01"), str(hasta or "9999-12-31")]
    total = database.consultar("SELECT COUNT(*) AS n FROM ventas WHERE fecha BETWEEN ? AND ?", *args)[0]["n"]
    sentido = "DESC" if descendente else "ASC"
    sql = f"SELECT * FROM ventas WHERE fecha BETWEEN ? AND ? ORDER BY fecha {sentido}, id {sentido}"
    if limite:
        sql += " LIMIT ? OFFSET ?"
        args += [limite, desplazamiento]
    return database.consultar(sql, *args), total


def registrar(concepto, importe, forma_pago, fecha=None):
    fecha = fecha or date.today()
    if importe <= 0:
        raise ReglaDeNegocio("El importe debe ser mayor que 0")
    if forma_pago not in config.FORMAS_PAGO:
        raise ReglaDeNegocio(f"Forma de pago no válida: {forma_pago}")
    with database.conectar() as con:
        cur = con.execute("INSERT INTO ventas (fecha, concepto, importe, forma_pago) VALUES (?, ?, ?, ?)",
                          (fecha.isoformat(), concepto.strip(), importe, forma_pago))
    return database.consultar("SELECT * FROM ventas WHERE id = ?", cur.lastrowid)[0]
