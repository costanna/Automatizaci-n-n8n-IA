# Spec · 05 Cierre diario de caja

| | |
|---|---|
| **Flujo** | `workflows/05-cierre-diario.json` |
| **Historia** | HU-04 (esencial) |
| **Nivel** | 🟢 Esencial |
| **Disparador** | Programado: todos los días a las **23:00** (Europe/Madrid) |

## Objetivo

Que Marisa reciba cada noche el resumen de lo cobrado, separado por forma de pago, y no tenga que
sumar nada con la calculadora.

## Entradas

Ninguna: el flujo pregunta a la API por las ventas y los abonos del día.

## Salidas

| Tipo | Contenido |
|---|---|
| Resumen a Marisa | Ventas directas, abonos y total, desglosados por `efectivo` / `tarjeta` / `bizum` |
| Histórico | Una fila por día con el cierre (Google Sheets / Data Table / Postgres) |
| Aviso "sin movimientos" | Si ese día no hubo nada, el resumen lo dice en vez de fallar |

## Pasos

1. **Schedule Trigger** (23:00, todos los días).
2. **Fecha de hoy** (Code): calcula `hoy` y `ayer` en formato `AAAA-MM-DD` con la zona horaria de
   la tienda.
3. **Ventas del día** (HTTP Request `GET /api/ventas?desde=<hoy>&hasta=<hoy>`).
4. **Abonos del día** (HTTP Request `GET /api/abonos?desde=<hoy>&hasta=<hoy>`).
5. **Calcular el cierre** (Code): suma por forma de pago, sin redondeos intermedios (redondea
   **al final** a dos decimales). Devuelve un único item con el cierre.
6. **¿Ha habido movimientos?** (If): si no → mensaje "Hoy no ha habido movimientos".
7. **Guardar el histórico** (Google Sheets / Data Table): una fila por día, con la fecha como
   clave para no duplicar.
8. **Enviar el resumen** a Marisa (email, con tabla HTML en el cuerpo).

## Reglas

- **Un cierre con ceros no se manda nunca por un error.** Las peticiones a la API llevan
  *neverError*: si alguna devuelve un error, *Calcular el cierre* para el flujo y el Error Workflow
  avisa a la tienda. (Antes, las ventas se pedian sin fechas, la API respondia 422 y el cierre
  salia con 0 ventas sin que nadie se enterara.)
- "Ventas del día" = ventas directas **+** abonos cobrados ese día (los abonos iniciales también
  cuentan: nacen como abono dentro de un apartado creado ese día).
- Los importes del resumen son los de la API; el flujo solo **suma**.
- Si no hubo movimientos, el flujo **no falla**: lo dice.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Día sin ventas ni abonos | Se envía "hoy no ha habido movimientos" |
| Fallo al pedir los datos a la API | El flujo falla y lo recoge el Error Workflow (flujo 08) |
| Fallo al guardar el histórico | Se avisa a Marisa y se sigue con el envío |
| Histórico ya existente para ese día | Se actualiza la fila, no se duplica |

## Criterios de aceptación

- [ ] Cada noche llega un resumen con ventas directas, abonos y el total, separados por forma de pago (efectivo, tarjeta y Bizum).
- [ ] Los importes coinciden con los de la app.
- [ ] Si ese día no hubo movimientos, el resumen lo dice en vez de fallar.

## Datos de prueba

`tests/flujo-05/entradas.json` — día con movimientos, día vacío y la API caída. Se prueba con
`python scripts/probar_flujos.py --flujo 5`, que registra una venta en efectivo, otra por Bizum y
un abono con tarjeta, lanza el cierre y compara cada línea con la API.
