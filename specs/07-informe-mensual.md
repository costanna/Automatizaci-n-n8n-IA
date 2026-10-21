# Spec · 07 Informe mensual

| | |
|---|---|
| **Flujo** | `workflows/07-informe-mensual.json` |
| **Historia** | HU-08 (medio) |
| **Nivel** | 🟡 Medio |
| **Disparador** | Programado: el **día 1 de cada mes** a las 09:00 |

## Objetivo

Que Marisa reciba a principios de mes un informe con lo recaudado y lo que le deben, sin hacer
cuentas.

## Entradas

Ninguna: el flujo calcula el mes anterior y consulta la API.

## Salidas

Informe (email a Marisa, con tabla HTML y resumen) con:

- Recaudación del mes anterior: **ventas directas** y **abonos**, por separado.
- Total pendiente de cobro (suma de lo que falta de todos los apartados activos).
- Apartados **nuevos** del mes, **liquidados** del mes y **vencidos** del mes.
- Número de apartados por estado.

## Pasos

1. **Schedule Trigger** (día 1 de mes, 09:00).
2. **Rango del mes** (Code): calcula `desde` = primer día del mes anterior y `hasta` = último día
   del mes anterior, en `AAAA-MM-DD`.
3. **Ventas del mes** (HTTP Request `GET /api/ventas?desde=&hasta=`).
4. **Abonos del mes** (HTTP Request `GET /api/abonos?desde=&hasta=`).
5. **Todos los apartados** (HTTP Request `GET /api/apartados`).
6. **Apartados del mes** (HTTP Request `GET /api/abonos?desde=&hasta=`): a partir de los abonos se
   sabe qué apartados han tenido movimiento; para "nuevos" se usa la fecha de creación.
7. **Calcular el informe** (Code): una sola salida con todas las cifras.
8. **Montar el informe** (Code): texto + tabla HTML.
9. **Enviar** a Marisa (email). Opcionalmente guardar una copia en el histórico.

## Reglas

- "Pendiente de cobro" = suma de `pendiente` de los apartados en estado `activo`. Los importes
  vienen de la API; el flujo solo los suma.
- La recaudación del mes separa **ventas directas** y **abonos** (los abonos iniciales cuentan
  como abono del mes en que se crearon).
- R-A1: ninguna cifra se calcula a mano en el texto del modelo; sale de la API.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Mes sin movimientos | El informe lo dice (todo a cero) |
| Fallo al pedir datos a la API | El flujo falla → Error Workflow (flujo 08) |
| Un apartado no tiene fecha de creación utilizable | Se cuenta en "nuevos" si su primer abono es del mes |

## Criterios de aceptación

- [ ] El día 1 llega un informe con lo recaudado el mes anterior (ventas directas y abonos por separado).
- [ ] Incluye el total pendiente de cobro, y los apartados nuevos, liquidados y vencidos del mes.
- [ ] Los importes coinciden con los de la app.

## Datos de prueba

`tests/flujo-07/entradas.json` — mes con datos y mes vacío.
