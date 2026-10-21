"""MODELO · Abono: los pagos parciales de un apartado y las reglas para registrarlos."""

from datetime import date

import config
import database
from models import apartado
from models.errores import ReglaDeNegocio


def de_apartado(apartado_id):
    return database.consultar("SELECT * FROM abonos WHERE apartado_id = ? ORDER BY fecha, id", apartado_id)


def listar(desde=None, hasta=None):
    return database.consultar("SELECT * FROM abonos WHERE fecha BETWEEN ? AND ? ORDER BY fecha, id",
                              str(desde or "0000-01-01"), str(hasta or "9999-12-31"))


def registrar(apartado_id, importe, forma_pago, fecha=None):
    fecha = fecha or date.today()
    actual = apartado.obtener(apartado_id)
    if actual["estado"] != "activo":
        raise ReglaDeNegocio(f"El apartado está {actual['estado']} y no admite abonos")
    if fecha.isoformat() > actual["fecha_limite"]:
        raise ReglaDeNegocio("El plazo del apartado ha vencido")
    if importe <= 0:
        raise ReglaDeNegocio("El importe debe ser mayor que 0")
    if importe > actual["pendiente"]:
        raise ReglaDeNegocio(f"El importe supera lo pendiente ({actual['pendiente']} €)")
    if forma_pago not in config.FORMAS_PAGO:
        raise ReglaDeNegocio(f"Forma de pago no válida: {forma_pago}")
    with database.conectar() as con:
        con.execute("INSERT INTO abonos (apartado_id, fecha, importe, forma_pago) VALUES (?, ?, ?, ?)",
                    (apartado_id, fecha.isoformat(), importe, forma_pago))
        if round(actual["pendiente"] - importe, 2) == 0:
            con.execute("UPDATE apartados SET estado = 'liquidado' WHERE id = ?", (apartado_id,))
    return apartado.obtener(apartado_id)
