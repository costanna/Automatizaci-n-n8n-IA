# Ontología del dominio · Paso Firme

Vocabulario compartido entre el negocio, la app y los flujos de n8n. Los flujos no inventan
conceptos: usan los que están aquí, con estos nombres exactos.

## Entidades

### `Cliente`
Persona que compra en la tienda.

| Atributo | Tipo | Notas |
|---|---|---|
| `id` | int | Id interno de la app (no se usa fuera de la API) |
| `nombre` | str | Nombre completo tal y como lo escribe la dependienta. **No está normalizado**: "Carmen Ruiz" y "carmen ruiz" son la misma persona |
| `telefono` | str? | Puede faltar (obligatorio para avisar por Telegram, opcional para correo) |
| `email` | str? | Puede faltar. Si falta, el flujo **no falla**: avisa a la tienda |
| `consentimiento` | bool | Derivado: hay email o teléfono. Un cliente sin ninguno de los dos no es notificable |

> La app **no tiene entidad `Cliente`**: los datos del cliente viven dentro del `Apartado`.
> Por eso la búsqueda de clientes es una búsqueda sobre apartados.

### `Producto`
Lo que se aparta. No tiene tabla propia: se denormaliza en el `Apartado` como
`producto` + `talla` + `precio`.

| Atributo | Tipo | Notas |
|---|---|---|
| `nombre` | str | "Botín piel marrón" |
| `talla` | str? | "38" (string, no número: hay tallas con letras) |
| `precio` | float | Precio total en euros, > 0 |

> Regla: **un apartado = un par**. Un producto tiene exactamente una talla por apartado.

### `Apartado`
Reserva de un producto por parte de un cliente, pagada a plazos.

| Atributo | Tipo | Notas |
|---|---|---|
| `id` | int | Número de apartado. Aparece en los conceptos de los pagos ("apartado 2") |
| `fecha` | date | Fecha de creación (o fecha original al migrar) |
| `cliente` | str | Ver `Cliente.nombre` |
| `telefono` | str? | |
| `email` | str? | |
| `producto` | str | Ver `Producto.nombre` |
| `talla` | str? | |
| `precio` | float | |
| `fecha_limite` | date | `fecha + 90 días`. La app la calcula |
| `estado` | enum | `activo` \| `liquidado` \| `vencido` |
| `abonado` | float | **Lo calcula la app** a partir de los abonos |
| `pendiente` | float | **Lo calcula la app**: `precio - abonado` |

**Estados y transiciones**

```
                  el abono deja lo pendiente en 0 €
   ┌─────────┐ ───────────────────────────────────▶ ┌────────────┐
   │ activo  │                                       │ liquidado  │  (puede recoger sus zapatos)
   └─────────┘ ───────────────────────┐              └────────────┘
                                      │ POST /api/apartados/{id}/vencer
                                      │ (solo si hoy > fecha_limite)
                                      ▼
                                ┌───────────┐
                                │  vencido  │  (se genera un Vale con lo abonado)
                                └───────────┘
```

- `liquidado` lo pone **la app sola** en cuanto un abono deja el pendiente en 0.
- `vencido` **no lo pone la app sola**: sigue `activo` hasta que n8n llame a `POST /vencer`.
- `liquidado` y `vencido` son finales: no admiten más abonos.

### `Abono`
Pago parcial (o inicial) sobre un `Apartado`.

| Atributo | Tipo | Notas |
|---|---|---|
| `id` | int | |
| `apartado_id` | int | Relación con `Apartado` |
| `fecha` | date | |
| `importe` | float | > 0 y ≤ pendiente del apartado en ese momento |
| `forma_pago` | enum | `efectivo` \| `tarjeta` \| `bizum` |

Reglas: abono inicial mínimo **5 €**; nunca se puede abonar más de lo que queda pendiente;
no se puede abonar un apartado `liquidado` o `vencido`; no se puede abonar con fecha posterior a
`fecha_limite`.

### `Venta`
Venta directa en la tienda (no es un apartado).

| Atributo | Tipo | Notas |
|---|---|---|
| `id` | int | |
| `fecha` | date | |
| `concepto` | str | "Botín piel negro T40" |
| `importe` | float | |
| `forma_pigo` → `forma_pago` | enum | `efectivo` \| `tarjeta` \| `bizum` |

### `Vale`
Vale de compra generado al vencer un apartado. **No es dinero**: no se devuelve en efectivo.

| Atributo | Tipo | Notas |
|---|---|---|
| `id` | int | |
| `codigo` | str | `VALE-00016` (patrón `VALE-{id:05d}`) |
| `apartado_id` | int | Apartado que lo originó |
| `fecha` | date | Fecha de vencimiento |
| `importe` | float | Lo que el cliente había abonado |
| `usado` | float | 0 mientras no se canjea |

### `CierreDiario`
Resumen de un día de caja. **No está en la app**: lo calcula n8n y lo guarda en un histórico
(Google Sheets / n8n Data Tables / Postgres).

| Atributo | Tipo | Notas |
|---|---|---|
| `fecha` | date | El día cerrado |
| `ventas_directas` | float | Suma de las ventas del día |
| `abonos` | float | Suma de los abonos del día (incluidos los iniciales) |
| `total` | float | `ventas_directas + abonos` |
| `por_forma_pago` | map | `{efectivo, tarjeta, bizum}` con el desglose |

> "Ventas del día" = ventas directas **+** abonos cobrados ese día. Los abonos iniciales también
> cuentan, porque nacen como un abono dentro de un apartado creado ese día.

### `PagoRemoto`
Pago recibido por Bizum o transferencia, **antes** de saber a qué apartado pertenece.

| Atributo | Tipo | Notas |
|---|---|---|
| `ordenante` | str | Lo que dice el aviso del banco |
| `importe` | float | |
| `concepto` | str | Puede venir vacío |
| `canal` | enum | `bizum` \| `transferencia` |
| `apartado_id` | int? | Se rellena **solo** si se resolvió sin dudas |

Es un concepto **temporal**: existe entre que llega el aviso y que se decide a qué apartado
pertenece. Si la decisión no es unívoca, el pago queda **sin asignar** y se pregunta a Marisa.

### `Notificacion`
Mensaje que sale hacia un cliente o hacia la tienda.

| Atributo | Tipo | Notas |
|---|---|---|
| `destinatario` | str | Email o `chat_id` de Telegram |
| `canal` | enum | `email` \| `telegram` |
| `asunto` | str | |
| `cuerpo` | str | **Los importes salen de la API, nunca se recalculan** |
| `motivo` | str? | En las notificaciones a la tienda: por qué se avisa |

### `Incidencia`
Aviso a Marisa de que algo no se ha podido hacer automáticamente.

| Atributo | Tipo | Notas |
|---|---|---|
| `motivo` | enum | `importe_excede` \| `fuera_de_plazo` \| `apartado_ambiguo` \| `cliente_desconocido` \| `sin_concepto` \| `error_tecnico` |
| `detalle` | str | Texto legible con el contexto (importe, apartado, ordenante) |
| `pago` | `PagoRemoto`? | El pago que no se pudo asignar |

## Reglas del negocio (las aplica la app, no n8n)

| # | Regla | Dónde se aplica |
|---|---|---|
| R1 | El abono inicial mínimo es **5 €** | `POST /api/apartados` → 422 |
| R2 | El plazo máximo es de **90 días** desde la fecha del apartado | `fecha_limite` |
| R3 | Un abono nunca supera lo pendiente | `POST /api/apartados/{id}/abonos` → 422 |
| R4 | No se abona un apartado `liquidado` ni `vencido` | idem → 422 |
| R5 | No se abona con fecha posterior a `fecha_limite` | idem → 422 |
| R6 | `forma_pago` ∈ {`efectivo`, `tarjeta`, `bizum`} | idem → 422 |
| R7 | Solo se vence un apartado `activo` y ya fuera de plazo | `POST /api/apartados/{id}/vencer` → 422 |
| R8 | Un abono que deja el pendiente en 0 liquidada el apartado | Automático en la app |

## Reglas de automatización (las aplica n8n)

| # | Regla |
|---|---|
| A1 | Los importes de un mensaje salen **siempre** de la API. El modelo redacta el texto pero no calcula cifras |
| A2 | Un pago remoto **no se registra** si hay dudas: se pregunta a Marisa |
| A3 | Un pago remoto **no se registra** si el importe supera el pendiente o el apartado está fuera de plazo: se avisa a Marisa con el motivo |
| A4 | Un correo que no es un aviso de pago se ignora en silencio (no genera notificación) |
| A5 | Un cliente sin email ni teléfono no hace fallar ningún flujo: se avisa a la tienda |
| A6 | Los avisos de vencimiento se mandan **una sola vez** por cliente y fecha límite |
| A7 | Ninguna credencial ni clave aparece en los mensajes, en los logs ni en el JSON de los flujos |
