# Spec · 11 Apartados desde casa

| | |
|---|---|
| **Flujo** | `workflows/11-apartados-desde-casa.json` |
| **Historia** | HU-13 · Entrada automática de datos 🟠 |
| **Disparador** | Webhook `GET /webhook/apartar-zapatos` (el formulario) y `POST /webhook/apartar-zapatos` (la solicitud) |
| **Configuración** | El webhook de la tienda va protegido con `WEBHOOK_TOKEN` (ver `00 · Despachador de eventos`) |

## Objetivo

Que un cliente pueda pedir un apartado desde casa y que la tienda reciba la solicitud con
todo lo necesario para confirmarla en cuanto llegue el abono inicial.

## Entradas

**Del cliente** (`POST /webhook/apartar-zapatos`):

```json
{
  "cliente": "Cliente Casa Demo",
  "telefono": "600 555 111",
  "email": "casa.demo@example.com",
  "producto": "Botín piel marrón",
  "talla": "39",
  "precio": "89.90",
  "forma_pago": "bizum"
}
```

**De la tienda** (`POST /webhook/confirmar-solicitud`):

```json
{ "codigo": "SOL-0001", "importe": 10 }
```

## Salidas

| Tipo | Condición | Contenido |
|---|---|---|
| Formulario (HTML) | `GET /webhook/apartar-zapatos` | La página con los campos; envía el JSON por `fetch` |
| Confirmación al cliente | El cliente ha enviado la solicitud | "Gracias, hemos recibido tu solicitud" |
| Aviso a la tienda | El cliente ha enviado la solicitud | La solicitud con su **código** y cómo confirmarla |
| Apartado creado | La tienda confirma la solicitud | El apartado en la app, con su fecha y el abono inicial |
| Aviso al cliente | Apartado creado | Qué se ha apartado, lo abonado y lo que falta |
| Aviso a la tienda | Apartado creado | El código de la solicitud y el abono inicial |

## Pasos

1. **Enrutar el formulario** (Code): el `GET` siempre es el formulario.
2. **Enrutar** (Code): el `POST` con `codigo` es una confirmación; si no, es una solicitud.
3. **¿Es el formulario?** (If): sí → **Mostrar el formulario** (Respond to Webhook con HTML).
4. **¿Es una confirmación?** (If):
   - sí → **Buscar la solicitud** (Code, en los *static data* del flujo) → **¿Está pendiente?** (If)
     - sí → **Preparar el apartado** → **Crear el apartado** (API) → **Avisos de la confirmación**
       → **Avisar al cliente** → **Responder confirmado**.
     - no → **Aviso de solicitud no válida** → **Avisar a la tienda** → **Responder no válida**.
   - no → **Preparar la solicitud** (Code: valida, crea el código `SOL-XXXX` y la guarda) →
     **Avisar a la tienda** → **Responder gracias**.

## Reglas

- **El formulario es público; la confirmación no.** `GET/POST /webhook/apartar-zapatos` lo usa
  cualquier cliente, pero `POST /webhook/confirmar-solicitud` crea el apartado en la app: pide la
  cabecera `X-Webhook-Token` (credencial `Webhooks - Tienda`), y sin ella n8n responde 403.
- **El apartado no se crea hasta que llega el abono inicial.** La primera vez solo se crea la
  *solicitud*: la app exige un abono de al menos 5 € al crear el apartado, y no se puede
  inventar ese dinero.
- La solicitud se guarda en los *static data* del flujo (la memoria de n8n entre ejecuciones),
  con un código `SOL-XXXX` que la tienda usa para confirmarla.
- El precio lo pone el cliente, pero lo que manda es la app: si el precio no es válido, la API
  lo rechaza y el aviso a la tienda lo dice.
- R-A7: al modelo externo no se le manda nada en este flujo.

## Casos de error

| Caso | Comportamiento |
|---|---|
| Faltan datos del cliente | La solicitud se crea igual, vacía; la tienda lo ve y lo corrige |
| El precio no es un número | La API responde 422 y el aviso a la tienda lleva el error |
| El código de confirmación no existe | Se avisa a la tienda: "no existe ninguna solicitud con ese código" |
| La solicitud ya estaba confirmada | Se avisa a la tienda: "ya estaba confirmada" (no se crea el apartado dos veces) |
| El abono inicial es menor de 5 € | La API lo rechaza (regla de la tienda) y se avisa a la tienda |

## Criterios de aceptación

- [ ] El cliente pide apartar unos zapatos desde casa y la tienda recibe la solicitud con un código.
- [ ] El apartado se confirma cuando llega el abono inicial, con la fecha de la solicitud.
- [ ] El cliente recibe la confirmación del apartado y lo que le queda por pagar.

## Datos de prueba

```bash
# 1. el cliente pide el apartado
curl -X POST http://localhost:5678/webhook/apartar-zapatos \
  -H "Content-Type: application/json" \
  -d '{"cliente":"Cliente Casa Demo","telefono":"600 555 111","email":"casa.demo@example.com","producto":"Botín piel marrón","talla":"39","precio":"89.90","forma_pago":"bizum"}'

# 2. la tienda confirma cuando llega el abono
curl -X POST http://localhost:5678/webhook/confirmar-solicitud \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: <el WEBHOOK_TOKEN del .env>" \
  -d '{"codigo":"SOL-0001","importe":10}'
```

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Tienda - API` | Header Auth | Crear el apartado |
| `SMTP - Paso Firme` | SMTP | Avisar a la tienda y al cliente (vía `SUB · Notificar`) |
