# Spec · 08 Error Workflow (avisos de error)

| | |
|---|---|
| **Flujo** | `workflows/08-error-workflow.json` |
| **Historia** | HU-05 (esencial) |
| **Nivel** | 🟢 Esencial |
| **Disparador** | **Error Trigger**: se activa cuando **otro** flujo falla |

## Objetivo

Que Marisa se entere en cuanto una automatización deja de funcionar, en vez de descubrirlo
semanas después.

## Entradas

El propio n8n: `workflow`, `execution`, `error` (mensaje, descripción, nodo y traza).

## Salidas

Aviso a la tienda con:

- El **nombre del flujo** que ha fallado.
- El **paso** (nodo) donde ha fallado.
- El **mensaje del error**.
- La fecha y la hora.

## Pasos

1. **Error Trigger**.
2. **Preparar aviso** (Code): extrae el nombre del flujo, el nodo, el mensaje y la hora; limpia
   el mensaje de cualquier cosa que parezca una credencial.
3. **Enviar a la tienda** (email a Marisa + opcionalmente Telegram).

## Reglas

- R-A7: **el aviso no incluye contraseñas ni claves**. El nodo de limpieza sustituye cualquier
  cosa que parezca una clave (`api_key`, `apikey`, `password`, `token`, `secret`, `Bearer ...`)
  por `***`.
- El aviso identifica siempre al flujo y al nodo: sin eso no se puede arreglar nada.

## Casos de error

| Caso | Comportamiento |
|---|---|
| El aviso a la tienda también falla | Se detiene el flujo; el error queda en *Executions* de n8n |
| El error contiene datos sensibles | Se limpian antes de enviar |

## Criterios de aceptación

- [ ] Cualquier flujo que falle envía un aviso con el nombre del flujo, el paso y el error.
- [ ] El aviso no incluye contraseñas ni claves.

## Cómo se conecta

Este flujo **no** se activa solo: hay que activarlo como *Error Workflow*.

1. Importar este flujo y **publicarlo** (Publish).
2. En cada flujo que deba avisar: *Settings → Error Workflow → 08 · Avisos de error*.
3. Comprobarlo: en cualquier flujo, *Execute workflow* con un nodo que falle a propósito
   (p. ej. `Code` con `throw new Error('prueba')`) y mirar si a Marisa le llega el aviso.

## Datos de prueba

`tests/flujo-08/entradas.json` — un error simulado con un texto que contiene un token falso, para
comprobar que se limpia.
