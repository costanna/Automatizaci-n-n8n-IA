from datetime import date, timedelta

import config
import database
import seed


def test_los_datos_de_ejemplo_cuadran_con_los_correos(cliente, monkeypatch, tmp_path):
    """data/correos/ cuenta con estos apartados concretos."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "seed.db"))
    database.crear_tablas()
    seed.cargar()
    hoy = date.today()
    activos = cliente.get("/api/apartados?estado=activo").json()
    limites = {date.fromisoformat(a["fecha_limite"]) - hoy for a in activos}
    assert {timedelta(days=7), timedelta(days=1)} <= limites  # recordatorios
    assert any(d < timedelta(0) for d in limites)  # fuera de plazo pendientes de vencer
    assert cliente.get("/api/apartados?estado=liquidado").json() and cliente.get("/api/vales").json()
    assert cliente.get(f"/api/ventas?desde={hoy}&hasta={hoy}").json() or hoy.weekday() == 6
    por_id = {a["id"]: a for a in cliente.get("/api/apartados").json()}
    dias = lambda a: (date.fromisoformat(a["fecha_limite"]) - hoy).days  # noqa: E731
    assert por_id[1]["cliente"] == "Carmen Ruiz" and por_id[1]["pendiente"] >= 10
    assert por_id[3]["cliente"] == "Lucía Gómez" and por_id[3]["pendiente"] == 12  # liquida
    assert por_id[12]["cliente"] == "Laura Ortega" and por_id[12]["pendiente"] < 15  # paga de más
    assert por_id[16]["cliente"] == "Paula Ramos" and dias(por_id[16]) < 0  # fuera de plazo
    assert por_id[24]["cliente"] == "Silvia Cortés" and por_id[24]["pendiente"] >= 5
