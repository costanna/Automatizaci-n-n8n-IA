"""MODELO · Vale: el crédito que recibe el cliente cuando un apartado vence."""

import database


def del_apartado(apartado_id):
    encontrados = database.consultar("SELECT * FROM vales WHERE apartado_id = ?", apartado_id)
    return encontrados[0] if encontrados else None


def listar():
    return database.consultar("SELECT * FROM vales ORDER BY fecha")
