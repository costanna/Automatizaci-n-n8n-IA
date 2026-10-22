# Spec · 14 Asistente de Telegram

| | |
|---|---|
| **Flujo** | `workflows/14-asistente-telegram.json` |
| **Herramientas** | `SUB · Tool saldo del cliente`, `SUB · Tool cifras de la tienda` |
| **Historias** | HU-11 y HU-12 🟠 |
| **Disparador** | Webhook `POST /webhook/telegram` con la cabecera `X-Telegram-Bot-Api-Secret-Token`: es lo que Telegram manda (el trigger de Telegram de n8n 2.44 no se activa en este entorno) |
| **Configuración** | `TELEGRAM_ADMIN_ID` en `data/config.csv`: el chat de la tienda |

## Objetivo

Que un cliente pregunte por Telegram cuánto le falta por pagar y lo sepa sin llamar, y que la
tienda pueda preguntar por Telegram cómo va el negocio.

## Entradas

Un mensaje de Telegram:

```json
{
  "message": {
    "chat": { "id": "111111" },
    "from": { "first_name": "Ana" },
    "text": "¿cuánto me falta por pagar?"
  }
}
```

## Salidas

| Tipo | Condición | Contenido |
|---|---|---|
| Pide el teléfono | El chat no está apuntado a ningún teléfono | "Necesito el teléfono con el que hiciste el apartado (9 dígitos)" |
| Saldo del cliente | El chat está apuntado | Sus apartados, lo que le falta y la fecha límite |
| Cifras de la tienda | El chat es el de la tienda | Recaudación, pendiente de cobro y apartados que vencen este mes |
| Mensaje al modelo | Siempre que se redacte | La pregunta del cliente y **sus** datos |

## Pasos

1. **Telegram Trigger** (webhook con token): recibe el update de Telegram.
2. **Leer configuración** + **Parsear configuración** (`data/config.csv`).
3. **Normalizar el mensaje** (Code): chat, texto y nombre; si el chat es `TELEGRAM_ADMIN_ID` es
   la tienda. Mira si el chat ya está apuntado a un teléfono (en los *static data* del flujo) y,
   si el cliente escribe 9 dígitos, lo apunta.
4. **¿Es la tienda?** (If):
   - sí → **Cifras de la tienda** (`SUB · Tool cifras de la tienda`) → **Preparar respuesta de la
     tienda** → **Responder en Telegram**.
   - no → **Datos del cliente** → **¿Tiene teléfono?** (If)
     - sí → **Saldo del cliente** (`SUB · Tool saldo del cliente`) → **Preparar respuesta del
       cliente** → **Redactar con IA** (AI Agent con la API de la tienda como herramienta) →
       **Comprobar las cifras** → **Responder en Telegram**.
     - no → **Pedir el teléfono** → **Responder en Telegram**.

## Reglas

- **Un cliente solo ve sus apartados.** El chat se apunta a un teléfono y la herramienta filtra
  **por dígitos exactos**: dos clientes con nombres parecidos no se ven entre sí.
- **Solo la tienda pregunta por el negocio**: el chat tiene que ser `TELEGRAM_ADMIN_ID`.
- **Las cifras las pone la tienda, no el modelo.** El agente redacta el tono; el nodo
  *Comprobar las cifras* compara sus importes con los que han salido de la API y, si no
  coinciden, **usa la respuesta calculada por el flujo**.
- **Al modelo solo se le manda lo justo**: la pregunta del cliente y sus propios apartados. Ni
  datos de otros clientes, ni claves, ni el resto de la tienda (ver
  [`docs/rgpd.md`](../docs/rgpd.md)).
- El periodo de las cifras de la tienda se deduce de la pregunta, con la fecha de Madrid:
  "hoy" → hoy; "esta semana" → los últimos 7 días; "este mes" (o sin periodo) → del día 1 a
  hoy; "el mes pasado" o "el mes anterior" → el mes natural anterior.

## Casos de error

| Caso | Comportamiento |
|---|---|
| El chat no está apuntado | Se pide el teléfono; al enviarlo, se apunta y se responde |
| El teléfono no está en la app | Se responde que no hay ningún apartado con ese teléfono y se ofrece pasar por la tienda. Siempre con la respuesta del flujo: sin cifras que comprobar, el modelo no redacta |
| El modelo no está disponible | Se usa la respuesta calculada por el flujo (el nodo del agente está en *On Error → Continue*) |
| El modelo cambia una cifra | El nodo *Comprobar las cifras* lo detecta y usa la respuesta original |
| `TELEGRAM_ADMIN_ID` no está configurado | Nadie es la tienda: todas las preguntas se tratan como de cliente |

## Criterios de aceptación

- [ ] El asistente identifica al cliente y solo le muestra sus apartados, nunca los de otro.
- [ ] Responde con el saldo y la fecha límite que da la app, nunca con cifras calculadas por el modelo.
- [ ] Si no entiende la pregunta o no encuentra al cliente, lo dice y ofrece hablar con la tienda.
- [ ] Solo responde a la tienda (usuario autorizado) las preguntas del negocio.
- [ ] Las respuestas salen de consultas a la API de la tienda.

## Datos de prueba

Los casos y el resultado esperado están en `tests/flujo-14/entradas.json`. Se prueban con el
mock de Telegram, que manda los mensajes al webhook `/webhook/telegram` con la cabecera
`X-Telegram-Bot-Api-Secret-Token`, igual que Telegram:

```bash
python scripts/telegram_mock.py --puerto 8081 \
    --url http://localhost:5678/webhook/telegram --secreto <TELEGRAM_SECRET_TOKEN>
python scripts/probar_flujos.py --flujo 14
```

> Si se escribe a mano al mock desde Git Bash con `curl`, los acentos y la `¿` no llegan en
> UTF-8 y el mock recibe un mensaje vacío: es mejor usar `probar_flujos.py`.

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Telegram - Paso Firme` | Telegram API | Recibir los mensajes y responder |
| `Tienda - API` | Header Auth | La API de la tienda como herramienta del agente |
| `Modelo - Groq` | OpenAI compatible | Redactar el tono (opcional: si no está, responde el flujo) |
