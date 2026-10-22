# Spec · 03 Abonos a distancia (Bizum / transferencia)

| | |
|---|---|
| **Flujo** | `workflows/03-abonos-distancia.json` |
| **Historia** | HU-03 (esencial) |
| **Nivel** | 🟢 Esencial |
| **Disparador** | Correo nuevo (IMAP o Gmail Trigger) con el aviso del banco |

## Objetivo

Que los pagos que llegan por Bizum o transferencia se registren solos en el apartado correcto, y
que **nada** se registre cuando hay dudas: en ese caso se pregunta a Marisa.

## Entradas

El correo del banco: asunto y cuerpo. Ejemplo (`data/correos/01_bizum_carmen.eml`):

```
Subject: Has recibido un Bizum de 10,00 €
Importe: 10,00 EUR
Ordenante: CARMEN RUIZ GARCIA
Concepto: zuecos
```

## Salidas

| Tipo | Condición |
|---|---|
| Abono registrado | Hay **un** apartado claro, el importe cabe y está en plazo |
| Recibo al cliente | Se ha registrado el abono (invoca el flujo 02) |
| Aviso a Marisa | Dudoso, importa de más, fuera de plazo o error técnico. **No se registra nada** |
| Silencio | El correo no es un aviso de pago (publicidad del banco) |

## Pasos

1. **Normalizar correo** (Code): junta asunto + cuerpo, quita el texto citado (`>`) y el pie del
   banco. Deja `asunto`, `cuerpo` y `texto`.
2. **¿Es un aviso de pago?** (If): busca marcas de pago (`bizum`, `transferencia`, `importe`,
   `ordenante`, `abonado`) y descarta las de publicidad (`ofertas`, `domicilias`, `condiciones`).
   - No → **terminar en silencio** (nada de avisos: R-A4).
3. **Extraer los datos** (Basic LLM Chain + modelo de lenguaje): el modelo **solo extrae**
   `ordenante`, `importe` y `concepto`, y devuelve JSON. El modelo **no decide** nada.
4. **Interpretar la respuesta** (Code): saca el JSON de la respuesta del modelo (quitando vallas
   ```` ``` ````), lo normaliza a mayúsculas sin acentos y valida el formato.
   Si el modelo no está disponible o no devuelve algo usable → **extractor determinista** por
   expresiones regulares (mismo contrato de salida, `origen: "regex"`).
5. **Buscar el apartado** (HTTP Request `GET /api/apartados?estado=activo&q=<ordenante>`).
6. **Elegir el apartado** (Code):
   - Normaliza nombres (mayúsculas, sin acentos, quitando tildes y comparando palabra a palabra).
   - Coincidencia **exacta** de nombre y/o teléfono → candidato único.
   - Si el concepto trae un nº de apartado (`apartado 2`), ese número manda.
   - 0 candidatos → `motivo: cliente_desconocido`.
   - >1 candidatos → `motivo: apartado_ambiguo`.
7. **Decidir** (Code), con los datos de la API:
   - `importe > pendiente` → `motivo: importe_excede`.
   - `fecha_limite < hoy` → `motivo: fuera_de_plazo`.
   - `importe <= 0` → `motivo: error_tecnico`.
   - Si no → `accion: registrar`.
8. **Registrar** (HTTP Request `POST /api/apartados/{id}/abonos` con `importe` y
   `forma_pago: bizum|transferencia`… ⚠️ **la app solo admite `efectivo`, `tarjeta` y `bizum`**:
   las transferencias se registran como `bizum`, que es el equivalente del banco en esta tienda).
9. **¿Se registró?** (If): sí → **invocar el flujo 02** (recibo) ; no → **avisar a Marisa** con el
   `motivo` y el detalle.

## Reglas

- **La entrada manual (`POST /webhook/abonos-distancia`) va protegida**: pide la cabecera
  `X-Webhook-Token` (credencial `Webhooks - Tienda`). Sin ella, n8n responde 403 y no registra
  nada: si no, cualquiera podría mandar un aviso del banco falso.
- R-A1: el importe que se registra es el que dice el aviso; el pendiente es el de la API.
- R-A2: si hay dudas → **no se registra nada** y se pregunta.
- R-A3: si el importe supera lo pendiente o el apartado está fuera de plazo → **no se registra
  nada** y se avisa a Marisa con el motivo.
- R-A4: un correo que no es un pago se ignora en silencio.
- R-A7: al modelo solo se le manda el texto del correo (asunto + cuerpo). **No** se le mandan datos
  de clientes ni de la base de datos.

## Casos de error

| Caso | Comportamiento |
|---|---|
| El modelo no está configurado o falla | El extractor determinista toma el relevo; el flujo sigue |
| La API devuelve 401 (clave mal puesta) | Se avisa a Marisa: "no se pudo registrar, credenciales de la API" |
| La API devuelve 422 (regla del negocio) | Se avisa a Marisa con el `detail` de la API |
| El nombre coincide con varios apartados | No se registra; se pregunta a Marisa con la lista |

## Criterios de aceptación

- [ ] Los correos que no son un pago (como la publicidad del banco) se ignoran.
- [ ] De cada pago se extraen ordenante, importe y concepto, y se busca el apartado por API.
- [ ] Si hay un único apartado claro, se registra el abono y el cliente recibe su recibo (HU-02).
- [ ] Si el pago es dudoso (varios apartados posibles, sin concepto o cliente desconocido), no se registra nada y se pregunta a Marisa.
- [ ] Si el importe supera lo pendiente o el apartado está fuera de plazo, no se registra nada y se avisa a Marisa con el motivo.
- [ ] El flujo resuelve bien los correos de `data/correos/`.

## Comportamiento esperado con los 9 correos de prueba

| Correo | Resultado esperado |
|---|---|
| `01_bizum_carmen` | Cliente con un único apartado activo → **se registra** |
| `02_bizum_jorge` | Nombre abreviado, pero el concepto trae el nº de apartado → **se registra** |
| `03_transferencia_lucia` | Paga justo lo que falta → **se registra** y el apartado queda **liquidado** |
| `04_bizum_laura` | Paga de más → **no se registra**, aviso a Marisa (`importe_excede`) |
| `05_bizum_romero` | Solo apellido e inicial, sin concepto → **no se registra**, aviso a Marisa (`sin_concepto` / `apartado_ambiguo`) |
| `06_bizum_paula` | Apartado fuera de plazo → **no se registra**, aviso a Marisa (`fuera_de_plazo`) |
| `07_transferencia_desconocido` | No coincide con nadie → **no se registra**, aviso a Marisa (`cliente_desconocido`) |
| `08_publicidad_banco` | No es un pago → **se ignora en silencio** |
| `09_bizum_silvia` | Nombre único → **se registra** |

## Datos de prueba

`tests/flujo-03/casos.json` — un caso por correo, con el resultado esperado.

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Tienda - API` | Header Auth (`X-API-Key`) | Buscar y registrar abonos |
| `Banco - IMAP` | IMAP | Leer los avisos del banco |
| `Modelo - Groq` | OpenAI compatible | Extraer ordenante, importe y concepto |
| `Gmail - Paso Firme` / `Telegram - Paso Firme` | | Avisar a Marisa y enviar el recibo |
