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

Este flujo **no** se activa solo: los demás flujos tienen que tenerlo como *Error Workflow*.

1. Importar este flujo y **publicarlo** (Publish).
2. Todos los demás flujos lo llevan en sus ajustes (`settings.errorWorkflow` en el JSON, que en
   el editor es *Settings → Error Workflow → 08 · Avisos de error*). En otra instancia de n8n,
   `scripts/enlazar_flujos.py` lo vuelve a apuntar al id que tenga allí el 08.
3. n8n **solo** lo dispara en ejecuciones de producción (un webhook o un programado), no al
   pulsar *Execute workflow* en el editor.

## Datos de prueba

`tests/flujo-08/entradas.json` — un error simulado con un texto que contiene un token falso, para
comprobar que se limpia.

`python scripts/probar_flujos.py --flujo 8` provoca un fallo de verdad: para la tienda, abre el
panel (que no puede consultar la API) y comprueba que a Marisa le llega el aviso con el flujo, el
paso, la fecha y la hora, y sin la clave de la API. Después vuelve a arrancar la tienda.
