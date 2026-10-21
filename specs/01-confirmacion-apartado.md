# Spec · 01 Confirmación de apartado

| | |
|---|---|
| **Flujo** | `workflows/01-confirmacion-apartado.json` |
| **Historia** | HU-01 (esencial) |
| **Nivel** | 🟢 Esencial |
| **Disparador** | Subflujo invocado por el despachador de eventos con `evento = apartado.creado` |

## Objetivo

Que el cliente reciba, en menos de un minuto, un mensaje con lo que ha apartado, cuánto ha
abonado, cuánto le falta y hasta cuándo.

## Entradas

Llega del despachador (`workflows/00-despachador-eventos.json`):

```json
{ "evento": "apartado.creado",
  "datos": { "id": 25, "fecha": "2026-10-20", "cliente": "Carmen Ruiz",
             "telefono": "612 345 001", "email": "carmen@example.com",
             "producto": "Botín piel marrón", "talla": "38", "precio": 89.9,
             "fecha_limite": "2027-01-18", "estado": "activo",
             "abonado": 10.0, "pendiente": 79.9 } }
```

## Salidas

| Tipo | Condición | Contenido |
|---|---|---|
| Mensaje al cliente | El cliente tiene email o teléfono | Modelo, talla, precio, abonado, pendiente, fecha límite |
| Aviso a la tienda | El cliente **no** tiene email ni teléfono | "No se pudo avisar al cliente del apartado 25: falta email y teléfono" |

## Pasos

1. **Preparar mensaje** (Code): monta el texto con los importes **tal cual vienen** de la API.
   No recalcula nada. Formatea euros con `toFixed(2)` y coma decimal.
2. **¿Tiene email?** (If)
   - Sí → **Enviar email** (Gmail) → *fin*.
   - No → **¿Tiene teléfono?** (If)
     - Sí → **Enviar Telegram** → *fin*.
     - No → **Avisar a la tienda** (email a Marisa) → *fin*.
3. Si el envío falla, el nodo de envío está en *On Error → Continue* y el flujo **no falla**:
   cae en la rama de "no se pudo enviar" y avisa a la tienda.

## Reglas

- R-A1: los importes del mensaje son los de la API (`precio`, `abonado`, `pendiente`).
- R-A5: la falta de email **no** hace fallar el flujo.
- R-A7: el mensaje no incluye claves ni datos de otros clientes.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Cliente sin email ni teléfono | Avisa a la tienda, el flujo termina bien |
| Error del servidor de correo | Se captura y se avisa a la tienda |
| Falta algún campo del payload | Se avisa a la tienda con el error; no se manda un mensaje a medias |

## Criterios de aceptación

- [ ] Al crear un apartado en la app, el cliente recibe un mensaje en menos de un minuto.
- [ ] El mensaje incluye modelo, talla, precio, abonado, pendiente y fecha límite, con los importes que da la app.
- [ ] Si el cliente no tiene correo, el flujo no falla: avisa a la tienda de que no se pudo enviar.

## Datos de prueba

`tests/flujo-01/entradas.json` · resultado esperado en `tests/flujo-01/resultado-esperado.json`

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Tienda - API` | Header Auth (`X-API-Key`) | — (este flujo no llama a la API) |
| `Gmail - Paso Firme` | Gmail OAuth2 | Enviar email |
| `Telegram - Paso Firme` | Telegram API | Enviar Telegram |
