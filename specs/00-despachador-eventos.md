# Spec · 00 Despachador de eventos (webhook único)

| | |
|---|---|
| **Flujo** | `workflows/00-despachador-eventos.json` |
| **Nivel** | 🟢 Esencial (requisito: *un único webhook que reparta los eventos con un nodo Switch*) |

## Objetivo

Un solo punto de entrada para todo lo que avisa la app. La app hace `POST` a
`http://n8n:5678/webhook/tienda` y este flujo decide a qué subflujo va cada evento.

## Entradas

```json
{ "evento": "apartado.creado", "datos": { ... } }
```

Eventos posibles: `apartado.creado`, `abono.registrado`, `venta.registrada`, `apartado.vencido`.

## Salidas

| Evento | Subflujo invocado |
|---|---|
| `apartado.creado` | `01 · Confirmación de apartado` |
| `abono.registrado` | `02 · Recibo de abono` |
| `venta.registrada` | `04 · Aviso de venta grande` |
| `apartado.vencido` | `06 · Aviso de vale al cliente` (parte del flujo 06) |
| Cualquier otro | Se ignora (y se avisa a la tienda por si es un error de la app) |

## Pasos

1. **Webhook** (POST, path `tienda`, respuesta 200 inmediata).
   - Ojo: en n8n el cuerpo llega en `$json.body`, no en `$json`.
2. **Normalizar** (Code): extrae `evento` y `datos` de `$json.body` y deja el item con la forma
   `{ "evento": ..., "datos": { ... } }` para que los subflujos reciben siempre lo mismo.
3. **Switch** (por el campo `evento`): cuatro ramas + rama por defecto.
4. Cada rama llama a su subflujo con **Execute Workflow**, pasándole `{ evento, datos }`.
5. La rama por defecto avisa a la tienda: "evento desconocido recibido".

## Reglas

- Un solo webhook para toda la app (requisito del enunciado).
- La respuesta al webhook es inmediata: n8n contesta `200` en cuanto acepta el evento, sin esperar
  a los subflujos. Para eso, el nodo Webhook usa **Respond Immediately** y el trabajo real se
  hace en ramas aparte.
- R-A7: el webhook **exige autenticación**: el token `WEBHOOK_TOKEN` del `.env`, en la query
  (`?token=...`, que es como lo manda la app, porque no puede poner cabeceras propias) o en la
  cabecera `X-Webhook-Token`. En `data/config.csv` no está el token sino su hash
  (`WEBHOOK_TOKEN_SHA256`): *Comprobar el token* calcula el SHA-256 de lo recibido y lo compara en
  tiempo constante. Sin token válido, responde `401` y no se ejecuta nada.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Evento desconocido | Se avisa a la tienda; no se rompe nada |
| La app manda el aviso y n8n está caído | **El aviso se pierde**: la app no reintenta. Por eso los flujos programados (cierre, vencimientos) consultan la API y no dependen del webhook |
| Un subflujo falla | Lo recoge el Error Workflow (flujo 08) |

## Criterios de aceptación

- [ ] Un único webhook reparte los cuatro eventos con un nodo Switch.
- [ ] La app y n8n conversan en los dos sentidos: webhook y API REST.

## Criterio de "publicado"

El `.env` de la tienda apunta a la **Production URL** (`/webhook/tienda`). Si el flujo no está
**publicado**, n8n responde `404` y el aviso se pierde. Ver `docs/como-importar-flujos.md`.
