# Spec · 10 Migración del Excel antiguo

| | |
|---|---|
| **Flujo** | `workflows/10-migracion-excel.json` |
| **Historia** | HU-10 (medio) |
| **Nivel** | 🟡 Medio |
| **Disparador** | Manual (Manual Trigger): se ejecuta una vez, con un flag de "modo simulación" para revisar antes de cargar |

## Objetivo

Pasar el Excel de Marisa a la app sin perder el histórico y sin mantener dos sistemas, sin
duplicar datos si se ejecuta dos veces, y dejando a Marisa los casos dudosos en un informe.

## Entradas

Los CSV de `data/`:

- `excel_actual_apartados.csv`: apartados y abonos **mezclados en la misma hoja**.
- `excel_actual_ventas.csv`: ventas del día y el total mensual **sumado a mano**.

## Salidas

| Tipo | Contenido |
|---|---|
| Apartados creados | Uno por fila de apartado, con su fecha original |
| Abonos creados | Uno por fila de abono, con su fecha original |
| Ventas creadas | Una por fila de venta, con su fecha original |
| Informe de dudosos | Filas que **no** se han cargado, con el motivo |
| Resumen | Cuántas filas se han cargado, cuántas se han omitido y por qué |

## Pasos

1. **Manual Trigger** + **leer los CSV** (nodo Code con los datos embebidos o *Read Binary File*
   + *Spreadsheet File*).
2. **Limpiar** (Code), por fila:
   - **Fechas**: `02/09/2026`, `7/9/26`, `2026-09-02` → todas a `AAAA-MM-DD`.
   - **Importes**: `89.90`, `1.842,30`, `15€` → número con punto decimal.
   - **Nombres**: `carmen ruiz` → `Carmen Ruiz` (primera letra en mayúscula por palabra).
   - **Teléfonos**: `612345002` → `612 345 002`.
   - **Filas que no son apartados**: las que tienen un abono sin producto/precio (el CSV mezcla
     apartados y abonos: las filas con `notas` "abono" y sin `modelo` nuevo son abonos).
3. **Decidir qué se carga** (Code), con las reglas de la app:
   - Abono inicial < 5 € → **no se carga**, va al informe de dudosos.
   - Fecha ilegible o importe no numérico → **no se carga**.
   - Fila duplicada (mismo cliente + producto + fecha + importe) → se salta y se cuenta como
     duplicada.
4. **Crear en la app** (HTTP Request `POST /api/apartados` y `POST /api/apartados/{id}/abonos`,
   con `fecha` original).
5. **Registrar lo cargado** (Code) en una hoja de histórico (`migrados`) con una clave
   `cliente|producto|fecha` para **no duplicar** en una segunda ejecución.
6. **Informe de dudosos** (Code + envío a Marisa): tabla con `fecha`, `cliente`, `producto`,
   `importe` y `motivo` (`abono_inicial_bajo_minimo`, `fecha_ilegible`, `importe_ilegible`,
   `duplicado`).

## Reglas

- Los importes y los pendientes **no se calculan**: los devuelve la API.
- Las fechas originales se conservan (`fecha` en el `POST`).
- Ejecutarlo dos veces **no duplica**: se comprueba el histórico antes de crear.
- Un abono inicial por debajo de 5 € **no se carga** y sale en el informe (criterio explícito de
  HU-10).

## Casos de error

| Caso | Comportamiento |
|---|---|
| La API rechaza una fila (422) | Se anota en el informe de dudosos con el `detail` y se sigue |
| La API rechaza la llamada (401) | Se detiene el flujo (credencial mal puesta) → Error Workflow |
| CSV con separador `;` o BOM | El limpiador lo detecta y lo normaliza |
| La fila "TOTAL SEPTIEMBRE (a mano)" | Se detecta y se ignora (no es una venta) |

## Criterios de aceptación

- [ ] Los CSV de `data/` se leen y se limpian (fechas, nombres, importes con €).
- [ ] Los apartados y abonos se crean en la app por API conservando su fecha original.
- [ ] Ejecutarlo dos veces no duplica los datos.
- [ ] Los casos dudosos (por ejemplo, un abono inicial menor de 5 €) no se cargan y salen en un informe para que Marisa decida.

## Datos de prueba

`tests/flujo-10/entradas.json` — el CSV tal cual, con la fila de total manual incluida.
