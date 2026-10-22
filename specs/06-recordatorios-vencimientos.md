# Spec · 06 Recordatorios de vencimiento y apartados vencidos

| | |
|---|---|
| **Flujo** | `workflows/06-recordatorios-vencimientos.json` |
| **Historias** | HU-06 y HU-07 (medio) |
| **Nivel** | 🟡 Medio |
| **Disparador** | Programado: todos los días a las **08:30** (Europe/Madrid) |

## Objetivo

Avisar a los clientes antes de que se acabe el plazo, cerrar los apartados que ya lo han pasado
(generando su vale) y avisar a la tienda de los zapatos que vuelven a la venta.

## Entradas

Ninguna: el flujo consulta la API.

## Salidas

| Tipo | Condición |
|---|---|
| Recordatorio "7 días" | `fecha_limite = hoy + 7` |
| Recordatorio "1 día" | `fecha_limite = mañana` |
| Aviso con el vale | Apartado vencido por la API: el cliente recibe el código y el importe del vale |
| Lista para la tienda | Los zapatos que vuelven a la venta (producto, talla, cliente, importe del vale) |

## Pasos

1. **Schedule Trigger** (08:30, todos los días).
2. **Apartados activos** (HTTP Request `GET /api/apartados?estado=activo`).
3. **Clasificar** (Code): para cada apartado activo calcula los días que faltan para
   `fecha_limite` y lo marca como `recordatorio_7`, `recordatorio_1` o `vencer`.
4. **¿Hay recordatorios?** (If): si no → el flujo termina sin hacer nada.
5. **Enviar recordatorios** (email/Telegram a cada cliente), uno por item, con lo que falta por
   pagar y la fecha límite (los datos de la API).
6. **Vencer** (HTTP Request `POST /api/apartados/{id}/vencer`) con cada apartado marcado
   `vencer`. La API genera el vale.
7. **¿Vencido?** (If): si sí → avisar al cliente con el **código y el importe del vale** (de la
   respuesta de la API) y a la tienda con la lista de zapatos que vuelven.
8. La app manda el evento `apartado.vencido` por el webhook, que el despachador puede usar para
   el aviso al cliente; este flujo lo hace en la misma ejecución para no depender del aviso
   (R: los flujos programados **no dependen de haber recibido el aviso**).

## Reglas

- R-A6: **cada cliente recibe cada aviso una sola vez**. Se controla con la clave
  `apartado_id:días` en los datos estáticos del flujo (`$getWorkflowStaticData`): si ya se
  avisó de ese apartado para esos días, no se vuelve a avisar. n8n solo guarda esos datos en
  las ejecuciones de producción, no en las manuales.
- El modelo redacta cada recordatorio por separado y *Comprobar las cifras* revisa **cada uno**
  (modo *Run Once for Each Item*). El nodo del modelo solo devuelve su texto: el correo, el
  asunto y las cifras se recuperan del recordatorio preparado con el mismo índice.
- R-A1: el importe del vale y el pendiente son los de la API.
- La app **no** vence los apartados sola: lo hace este flujo.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Cliente sin email ni teléfono | Se registra en la lista de "no avisados" y se avisa a la tienda |
| La API rechaza el vencimiento (todavía en plazo) | Se ignora ese apartado y se anota en el aviso a la tienda |
| Fallo al enviar un recordatorio | *On Error → Continue*: los demás clientes se siguen avisando |
| Un apartado ya se avisó | Se salta (no se repite el aviso) |

## Criterios de aceptación

- [ ] Cada mañana se avisa a los clientes cuyo plazo vence en 7 días y en 1 día.
- [ ] Cada cliente recibe cada aviso una sola vez.
- [ ] El mensaje incluye lo que falta por pagar y la fecha límite.
- [ ] Los apartados fuera de plazo se vencen por API y la app genera el vale.
- [ ] El cliente recibe un mensaje con el código y el importe de su vale.
- [ ] Marisa recibe la lista de zapatos que vuelven a la venta.

## Datos de prueba

`tests/flujo-06/entradas.json` — apartados que vencen en 7 días, en 1 día, dentro de 30 días y
fuera de plazo. Se prueba con `python scripts/probar_flujos.py --flujo 6`, que crea esos
apartados y lanza el flujo como el botón *Execute workflow* (hace falta `N8N_EMAIL` y
`N8N_PASSWORD`). "Una sola vez" se comprueba en producción (ver el JSON de la prueba).
