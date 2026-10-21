from datetime import date, timedelta

NUEVO = {"cliente": "Carmen Ruiz", "producto": "Botín piel marrón", "talla": "38", "precio": 89.9, "abono_inicial": 10}


def test_la_api_exige_clave(anonimo):
    assert anonimo.get("/api/apartados").status_code == 401


def test_swagger_muestra_authorize(anonimo):
    esquemas = anonimo.get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(e["type"] == "apiKey" and e["name"] == "X-API-Key" for e in esquemas.values())


def test_ciclo_completo_hasta_liquidar(cliente):
    a = cliente.post("/api/apartados", json=NUEVO).json()
    assert a["pendiente"] == 79.9 and a["estado"] == "activo"
    assert a["fecha_limite"] == (date.today() + timedelta(days=90)).isoformat()
    assert cliente.post(f"/api/apartados/{a['id']}/abonos", json={"importe": 100}).status_code == 422  # pagar de más
    a = cliente.post(f"/api/apartados/{a['id']}/abonos", json={"importe": 79.9}).json()
    assert a["pendiente"] == 0 and a["estado"] == "liquidado"
    assert cliente.post(f"/api/apartados/{a['id']}/abonos", json={"importe": 1}).status_code == 422


def test_abono_inicial_minimo(cliente):
    r = cliente.post("/api/apartados", json=NUEVO | {"abono_inicial": 4})
    assert r.status_code == 422 and "mínimo" in r.json()["detail"]


def test_apartado_inexistente(cliente):
    assert cliente.get("/api/apartados/99999").status_code == 404


def test_vencimiento_genera_vale(cliente):
    viejo = (date.today() - timedelta(days=100)).isoformat()
    a = cliente.post("/api/apartados", json=NUEVO | {"fecha": viejo}).json()
    nuevo = cliente.post("/api/apartados", json=NUEVO).json()
    assert cliente.post(f"/api/apartados/{nuevo['id']}/vencer").status_code == 422  # aún en plazo
    r = cliente.post(f"/api/apartados/{a['id']}/vencer").json()
    assert r["apartado"]["estado"] == "vencido" and r["vale"]["importe"] == 10
    assert cliente.get(f"/api/apartados/{a['id']}").json()["vale"]["codigo"] == f"VALE-{a['id']:05d}"
    assert any(v["apartado_id"] == a["id"] for v in cliente.get("/api/vales").json())


def test_lista_con_filtros_y_paginacion(cliente):
    for i in range(3):
        cliente.post("/api/apartados", json=NUEVO | {"cliente": f"Cliente {i}"})
    todos = cliente.get("/api/apartados")
    assert isinstance(todos.json(), list) and int(todos.headers["X-Total-Count"]) == len(todos.json())  # n8n recibe una lista
    pagina = cliente.get("/api/apartados?pagina=1&por_pagina=2")
    assert len(pagina.json()) == 2 and int(pagina.headers["X-Total-Count"]) >= 3
    assert len(cliente.get("/api/apartados?q=Cliente 1").json()) == 1
    resumen = cliente.get("/api/apartados/resumen").json()
    assert resumen["total"] == resumen["activo"] + resumen["liquidado"] + resumen["vencido"]


def test_ventas_por_fecha_y_abonos(cliente):
    cliente.post("/api/ventas", json={"concepto": "Crema calzado", "importe": 4.5})
    hoy = date.today().isoformat()
    ventas = cliente.get(f"/api/ventas?desde={hoy}&hasta={hoy}")
    assert len(ventas.json()) == 1 and ventas.headers["X-Total-Count"] == "1"
    assert cliente.get(f"/api/abonos?desde={hoy}&hasta={hoy}").json()
    desc = cliente.get("/api/ventas?orden=desc&pagina=1&por_pagina=1")
    assert len(desc.json()) == 1


def test_excel_es_un_xlsx(cliente):
    assert cliente.get("/api/excel").content[:2] == b"PK"  # un xlsx es un zip
