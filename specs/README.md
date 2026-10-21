# Specs · Spec-Driven Development

Cada automatización se define aquí **antes** de programarla: disparador, entradas, salidas, casos
de error y criterios de aceptación. Todo el equipo (y quien automate sobre este código) comparte
este vocabulario para no inventar conceptos.

## Onde está cada cosa

| Documento | Contenido |
|---|---|
| [`00-ontologia.md`](00-ontologia.md) | **Ontología del dominio**: `Cliente`, `Apartado`, `Abono`, `Venta`, `Vale`, `CierreDiario`, `PagoRemoto`, `Notificacion`, `Incidencia` y las reglas R1-R8 (las de la app) y A1-A7 (las de n8n) |
| [`00-despachador-eventos.md`](00-despachador-eventos.md) | Webhook único + Switch que reparte los eventos |
| [`01-confirmacion-apartado.md`](01-confirmacion-apartado.md) | HU-01 · Confirmación al apartar |
| [`02-recibo-abono.md`](02-recibo-abono.md) | HU-02 · Recibo de cada abono |
| [`03-abonos-distancia.md`](03-abonos-distancia.md) | HU-03 · Abonos por Bizum o transferencia |
| [`04-venta-grande.md`](04-venta-grande.md) | HU-09 · Aviso de ventas grandes |
| [`05-cierre-diario.md`](05-cierre-diario.md) | HU-04 · Cierre de caja automático |
| [`06-recordatorios-vencimientos.md`](06-recordatorios-vencimientos.md) | HU-06 y HU-07 · Recordatorios y vencimientos |
| [`07-informe-mensual.md`](07-informe-mensual.md) | HU-08 · Informe mensual |
| [`08-error-workflow.md`](08-error-workflow.md) | HU-05 · Avisos de errores |
| [`10-migracion-excel.md`](10-migracion-excel.md) | HU-10 · Migración del Excel antiguo |
| [`11-apartados-desde-casa.md`](11-apartados-desde-casa.md) | HU-13 · Apartados desde casa |
| [`13-ventas-datxfono.md`](13-ventas-datxfono.md) | HU-13 · Ventas del datáfono |
| [`14-asistente-telegram.md`](14-asistente-telegram.md) | HU-11 y HU-12 · Asistente de Telegram |

## Plantilla de una spec

```markdown
# Spec · NN Nombre

| | |
|---|---|
| **Flujo** | workflows/NN-nombre.json |
| **Historia** | HU-XX (nivel) |
| **Disparador** | Qué lo arranca |

## Objetivo
## Entradas   (payload de ejemplo)
## Salidas    (tabla: tipo → condición → contenido)
## Pasos      (1..n, con el nodo n8n de cada uno)
## Reglas     (R-Ax de la ontología)
## Casos de error
## Criterios de aceptación   (checklist, los mismos de la HU)
## Datos de prueba
## Credenciales
```

## Trazabilidad historia ↔ spec ↔ flujo ↔ test

| HU | Spec | Flujo | Test |
|---|---|---|---|
| HU-01 | 01 | `01-confirmacion-apartado.json` | `tests/flujo-01/` |
| HU-02 | 02 | `02-recibo-abono.json` | `tests/flujo-02/` |
| HU-03 | 03 | `03-abonos-distancia.json` | `tests/flujo-03/` |
| HU-04 | 05 | `05-cierre-diario.json` | `tests/flujo-05/` |
| HU-05 | 08 | `08-error-workflow.json` | `tests/flujo-08/` |
| HU-06 | 06 | `06-recordatorios-vencimientos.json` | `tests/flujo-06/` |
| HU-07 | 06 | `06-recordatorios-vencimientos.json` | `tests/flujo-06/` |
| HU-08 | 07 | `07-informe-mensual.json` | `tests/flujo-07/` |
| HU-09 | 04 | `04-venta-grande.json` | `tests/flujo-04/` |
| HU-10 | 10 | `10-migracion-excel.json` | `tests/flujo-10/` |
| HU-11 | 14 | `14-asistente-telegram.json` + `sub-tool-saldo-cliente.json` | `tests/flujo-14/` |
| HU-12 | 14 | `14-asistente-telegram.json` + `sub-tool-cifras-tienda.json` | `tests/flujo-14/` |
| HU-13 | 11 y 13 | `11-apartados-desde-casa.json`, `13-ventas-datxfono.json` | `tests/flujo-11/`, `tests/flujo-13/` |
| HU-14 | 00 y 14 | `00-despachador-eventos.json` (token), `14-asistente-telegram.json` | `docs/rgpd.md` |
