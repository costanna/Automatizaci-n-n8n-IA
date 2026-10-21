"""Zapatería Paso Firme: apartados, abonos y ventas.

Estructura (MVC):
  models/       MODELO      los datos y las reglas del negocio (abono mínimo, plazo de 90 días...)
  schemas/                  la forma de los datos que entran y salen por la API (Pydantic)
  routes/                   qué URL llega a qué función del controlador
  controllers/  CONTROLADOR la lógica de cada petición: llama a los modelos y devuelve la respuesta
  middleware/               lo que se ejecuta antes o alrededor: comprobar la clave, convertir errores en respuestas
  ../frontend/  VISTA       la interfaz (HTML, CSS y JavaScript), que usa la API como cualquier otro cliente

Este archivo solo junta las piezas. Las automatizaciones (avisos, recordatorios, cierres, informes) son
trabajo de n8n, que usa la API (documentada en /docs) y recibe eventos por webhook.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import config
import database
import seed
from middleware import errores
from routes import abonos, apartados, paginas, utilidades, vales, ventas

app = FastAPI(title="Zapatería Paso Firme", description="API para integrar n8n con la tienda.")

errores.registrar(app)
for modulo in (apartados, abonos, ventas, vales, utilidades, paginas):
    app.include_router(modulo.router)
app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="frontend")

database.crear_tablas()
if config.SEED and database.esta_vacia():
    seed.cargar()
