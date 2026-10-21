# Spec · 02 Recibo de abono

| | |
|---|---|
| **Flujo** | `workflows/02-recibo-abono.json` |
| **Historia** | HU-02 (esencial) |
| **Nivel** | 🟢 Esencial |
| **Disparador** | Subflujo invocado por el despachador con `evento = abono.registrado`; también lo invoca el flujo 3 tras registrar un abono remoto |

## Objetivo

Que cada abono se reciba con un recibo que diga cuánto se ha pagado y cuánto queda, y que el
cliente sepa de inmediato si ya puede recoger sus zapatos.

## Entradas

```json
{ "evento": "abono.registrado",
  "datos": { "id": 25, "cliente": "Carmen Ruiz", "email": "carmen@example.com",
             "producto": "Botín piel marrón", "talla": "38", "precio": 89.9,
             "fecha_limite": "2027-01-18", "estado": "liquidado",
             "abonado": 89.9, "pendiente": 0.0, "importe": 20.0 } }
```

`datos.importe` es **el importe de este abono** (lo añade la app al aviso). `datos.estado` es el
estado **después** del abono.

## Salidas

| Tipo | Condición |
|---|---|
| Recibo "aún debes" | `estado = activo` → importe pagado, pendiente y fecha límite |
| Recibo "puedes recoger" | `estado = liquidado` → importe pagado, pendiente 0 y aviso de recogida |
| Aviso a la tienda | El cliente no tiene email ni teléfono, o el envío falla |

## Pasos

1. **Preparar recibo** (Code): arma el texto y calcula `mensaje` según `datos.estado`.
2. **¿Liquidado?** (If sobre `datos.estado`)
   - `liquidado` → texto de recogida, con un párrafo extra.
   - otro → texto normal con el pendiente.
3. **Enviar** (Gmail / Telegram) con *On Error → Continue*.
4. **¿Se pudo enviar?** (If): si no, **avisar a la tienda**.

## Reglas

- R-A1: el importe pagado y el pendiente son los de la API. El `importe` del abono también.
- El mensaje de liquidación **cambia** de texto, no es el mismo con otro valor.
- R-A5: sin email ni teléfono, avisa a la tienda.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Cliente sin email/teléfono | Aviso a la tienda, sin fallo |
| Servidor de correo caído | Se captura y se avisa a la tienda |
| `importe` ausente en el payload | Se avisa a la tienda indicando qué falta |

## Criterios de aceptación

- [ ] Cada abono registrado genera un recibo con el importe pagado y lo que queda pendiente.
- [ ] Si el apartado queda liquidado, el mensaje cambia: avisa de que ya puede recoger sus zapatos.

## Datos de prueba

`tests/flujo-02/entradas.json` (dos casos: abono parcial y abono que liquida)

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Gmail - Paso Firme` | Gmail OAuth2 | Enviar email |
| `Telegram - Paso Firme` | Telegram API | Enviar Telegram |
