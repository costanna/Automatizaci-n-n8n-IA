"""La interfaz es un conjunto de archivos que el servidor entrega tal cual."""


def test_las_paginas_se_entregan(anonimo):
    for ruta in ["/", "/apartados/nuevo", "/apartados/3", "/ventas"]:
        r = anonimo.get(ruta)
        assert r.status_code == 200 and "text/html" in r.headers["content-type"], ruta


def test_estilos_y_scripts(anonimo):
    assert anonimo.get("/static/css/styles.css").status_code == 200
    assert anonimo.get("/static/js/api.js").status_code == 200


def test_config_js_lleva_la_clave_para_la_interfaz(anonimo):
    r = anonimo.get("/config.js")
    assert r.status_code == 200 and 'apiKey: "test"' in r.text
