# Spec · 04 Aviso de venta grande

| | |
|---|---|
| **Flujo** | `workflows/04-venta-grande.json` |
| **Historia** | HU-09 (medio) |
| **Nivel** | 🟡 Medio |
| **Disparador** | Subflujo invocado por el despachador con `evento = venta.registrada` |

## Objetivo

Que Marisa se entere de las ventas grandes aunque no esté en la tienda.

## Entradas

```json
{ "evento": "venta.registrada",
  "datos": { "id": 257, "fecha": "2026-10-20", "concepto": "Bota montaña T41",
             "importe": 79.9, "forma_pago": "efectivo" } }
```

## Salidas

| Tipo | Condición |
|---|---|
| Aviso a Marisa | `importe >= UMBRAL_VENTA_GRANDE` |
| Nada | Por debajo del umbral: el flujo termina sin molestar |

## Pasos

1. **Comprobar el umbral** (If): compara `datos.importe` con la variable de n8n
   `$vars.UMBRAL_VENTA_GRANDE` (por defecto **200 €**). Cambiar el umbral se hace en
   *Settings → Variables*, **sin tocar el flujo** (criterio de HU-09).
2. **Preparar aviso** (Code): mensaje con el concepto, el importe, la forma de pago y la fecha.
3. **Enviar a Marisa** (email; opcionalmente Telegram).

## Reglas

- El umbral vive en una **variable de n8n**, no en el JSON del flujo.
- El importe es el de la API, no se recalcula.
- R-A7: el aviso no incluye datos de otros clientes.

## Casos de error

| Caso | Comportamiento |
|---|---|
| La variable no existe | Se usa 200 € por defecto (`$vars.UMBRAL_VENTA_GRANDE \|\| 200`) |
| Fallo al enviar el aviso | Se captura con *On Error → Continue*; lo reporta el Error Workflow si el flujo está configurado con él |

## Criterios de aceptación

- [ ] Las ventas por encima de un importe configurable generan un aviso a Marisa.
- [ ] Cambiar el importe no obliga a editar el flujo (se guarda en una variable).

## Datos de prueba

`tests/flujo-04/entradas.json` — venta de 79,90 € (no avisa) y venta de 250 € (avisa).
