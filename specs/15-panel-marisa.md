# Spec · 15 Panel de Marisa

| | |
|---|---|
| **Flujo** | `workflows/15-panel-marisa.json` |
| **Historia** | HU-15 · Panel para Marisa 🔴 |
| **Disparador** | Webhook `GET /webhook/panel` |

## Objetivo

Que Marisa vea en una sola pantalla, y sin abrir hojas ni correos, cómo va el negocio: lo que se
ha cobrado hoy, lo recaudado este mes, lo que queda por cobrar y qué apartados se están
quedando sin pagar.

## Entradas

Ninguna: el panel consulta la API de la tienda cada vez que se abre.

## Salidas

| Tipo | Condición | Contenido |
|---|---|---|
| Panel (HTML) | `GET /webhook/panel` | La página con las cifras y los apartados que vencen |
| Panel (JSON) | `GET /webhook/panel?formato=json` | Los mismos datos en JSON (para otras herramientas) |

## Lo que muestra

| Bloque | Dato | De dónde sale |
|---|---|---|
| Cobrado hoy | Ventas + abonos de hoy, con el total y el número de operaciones | `GET /api/ventas` y `GET /api/abonos` (hoy) |
| Recaudado este mes | Ventas + abonos del mes natural | Los mismos endpoints, filtrados por mes |
| Pendiente de cobro | Suma de lo que falta de los apartados activos | `GET /api/apartados` |
| Apartados | Activos, liquidados y vencidos | `GET /api/apartados/resumen` |
| Se vencen en 30 días | Cliente, producto, pendiente, fecha límite y días que quedan | `GET /api/apartados` |

## Pasos

1. **Ver el panel** (Webhook GET `/panel`).
2. **Preparar** (Code): la fecha de hoy y la de hace 30 días (y guarda la query, para poder
   pedir el panel en JSON).
3. **Ventas del periodo** (HTTP Request): los últimos 30 días.
4. **Abonos del periodo** (HTTP Request): los últimos 30 días.
5. **Apartados** (HTTP Request): todos.
6. **Resumen de la tienda** (HTTP Request): cuántos hay de cada tipo.
7. **Construir el panel** (Code): separa lo de hoy de lo del mes, calcula el pendiente y monta
   el HTML (o el JSON).
8. **¿Lo piden en JSON?** (If) → **Responder JSON** o **Mostrar el panel** (Respond to Webhook).

## Reglas

- **La clave de la API no sale nunca al navegador**: n8n consulta la tienda y devuelve solo los
  datos del panel. El navegador no ve la `X-API-Key`.
- Las cifras las calcula la app; el panel solo las suma y las pinta.
- La página se **actualiza sola** cada minuto (`<meta http-equiv="refresh">`), así que Marisa
  puede tenerla abierta en el móvil.
- **Tema claro y oscuro**: el panel arranca con el tema que tenga el sistema
  (`prefers-color-scheme`) y hay un interruptor en la cabecera para cambiarlo a mano. La
  elección se guarda en el navegador (`localStorage`) y se aplica **antes de pintar la
  página**, para que no haya destellos.
- R-A7: el panel no se lleva a ningún modelo ni a ningún servicio externo.

## Casos de error

| Caso | Comportamiento |
|---|---|
| La API no responde | El panel sale con las cifras a cero y el flujo sigue (los nodos HTTP no paran el flujo) |
| Un apartado sin fecha límite | No aparece en la lista de los que vencen |
| Se pide el panel en JSON | Se devuelve el JSON con los mismos datos |

## Criterios de aceptación

- [ ] El panel muestra los datos de la app actualizados.
- [ ] Se entiende sin explicación y se ve bien en el móvil.

## Datos de prueba

```bash
# en el navegador
http://localhost:5678/webhook/panel

# los datos en JSON (para otras herramientas)
curl "http://localhost:5678/webhook/panel?formato=json"
```

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Tienda - API` | Header Auth | Las cuatro consultas a la tienda |

> **Ninguna**: el panel es público para quien tenga la URL. Si hay que protegerlo, la opción
> es comprobar un token en el primer nodo (como hace el despachador de la tienda) y poner la
> URL en la lista de permitidos de la tienda.
