"""RUTAS · Páginas: qué dirección del navegador muestra qué archivo de `frontend/`. No aparecen en /docs."""

from fastapi import APIRouter

from controllers import paginas

router = APIRouter(include_in_schema=False)

router.get("/")(paginas.apartados)
router.get("/apartados/nuevo")(paginas.nuevo_apartado)
router.get("/apartados/{apartado_id}")(paginas.ver_apartado)
router.get("/ventas")(paginas.ventas)
router.get("/config.js")(paginas.configuracion)
