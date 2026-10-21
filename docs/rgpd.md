# Datos personales y RGPD

Qué datos maneja el proyecto, cuáles salen de nuestra máquina y con qué criterio se avisa a
alguien. Es la documentación de la historia **HU-14** (datos personales protegidos).

## 1. De dónde salen los datos

Todos los datos de clientes vienen de la **app de la tienda**, que es la base de datos:

| Dato | Dónde está | Para qué se usa |
|---|---|---|
| Nombre, teléfono, correo | `Apartado` | Avisar al cliente y buscarlo |
| Producto, talla, precio | `Apartado` | Los mensajes |
| Abonado, pendiente, fecha límite | `Apartado` (los calcula la app) | Los mensajes y las cifras |
| Fecha de vencimiento, código e importe del vale | `Vale` | El aviso del vale |

**No hay una tabla de clientes**: los datos de la persona viven dentro de su apartado. Tampoco
hay un campo de "consentimiento": se explica en el punto 4.

## 2. Qué sale de nuestra máquina

### Al modelo de lenguaje (fuera de nuestra máquina)

| Flujo | Qué se le manda | Qué **no** se le manda |
|---|---|---|
| `03 · Abonos a distancia` | **Solo el texto del aviso del banco** (asunto y cuerpo, sin el pie del banco) | Datos de clientes, apartados, claves, cualquier dato de la tienda |
| `14 · Asistente de Telegram` (cliente) | La pregunta del cliente y **sus propios** apartados (producto, precio, abonado, pendiente, fecha límite) | Los apartados de otros clientes, los datos de la tienda, las claves |
| `14 · Asistente de Telegram` (tienda) | La pregunta y las cifras agregadas de la tienda | Datos personales de los clientes |
| `06 · Recordatorios` | El texto del aviso con las cifras del cliente | Nada más |

En ningún caso se manda al modelo un **número de teléfono, un correo, una clave de la API ni el
histórico de la tienda**.

Y aunque se le manden datos, el modelo **no decide nada**: extrae (flujo 3) o redacta el tono
(flujos 6 y 14). Las cifras las pone la API, y hay un nodo que lo comprueba
(*Comprobar las cifras*): si el modelo cambia un importe, se usa el texto original.

### A los proveedores de correo y Telegram

| Destinatario | Qué recibe |
|---|---|
| El cliente | Su nombre, su producto, su precio, lo abonado, lo pendiente y su fecha límite |
| La tienda (Marisa) | Lo mismo, más el teléfono cuando hace falta (por ejemplo, para avisar de que el cliente no tiene correo) |

Un cliente **no** recibe nunca datos de otro, ni el listado de apartados de la tienda, ni las
cifras del negocio.

### Al banco (IMAP)

El flujo 3 **solo lee** el buzón donde el banco manda los avisos. No escribe nada al banco ni
comparte datos con él.

## 3. Dónde se guardan los datos que no están en la app

| Dato | Dónde | Cuánto tiempo |
|---|---|---|
| Solicitudes de apartado desde casa | *Static data* del flujo `11` | Hasta que se confirman (el flujo marca `confirmada`) |
| Cobros ya importados del datáfono | *Static data* del flujo `13` | Los 2.000 últimos |
| Recordatorios ya enviados | *Static data* del flujo `06` | Todos (son pocas claves) |
| Teléfono apuntado a un chat de Telegram | *Static data* del flujo `14` | Hasta que se borren los *static data* del flujo |
| Correos enviados en desarrollo | `data/envios/` (ignorado por git) | Los que se borren a mano |

Ninguno de estos ficheros sale de la máquina: viven en el volumen de n8n.

## 4. Consentimiento

La app no tiene un campo de consentimiento, así que el criterio es el siguiente:

| Canal | Consentimiento |
|---|---|
| **Correo al cliente** | Solo se escribe a quien ha dejado una dirección de correo en su apartado. Se considera que al dejar su correo para un aviso de apartado ha aceptado ese aviso. Si no hay correo, **no se le escribe**: se avisa a la tienda (criterio de HU-01) |
| **Telegram** | Es explícito: el cliente escribe al bot y apunta su teléfono. Además solo ve sus propios apartados |
| **Avisos a la tienda** | La tienda es la dueña de los datos: sin consentimiento |

**El flujo 1 nunca escribe a un apartado sin correo**: si el cliente no lo tiene, la Confirmación
va a la tienda con el aviso de que no se ha podido enviar. Lo mismo con el recibo de abono
(flujo 2) y con el aviso del vale.

## 5. Seguridad de los avisos

| Medida | Dónde |
|---|---|
| El webhook de la tienda exige un token | `00 · Despachador de eventos`: sin `WEBHOOK_TOKEN` (query o cabecera `X-Webhook-Token`) responde **401** y no ejecuta nada |
| La API de la tienda exige `X-API-Key` | La credencial *Header Auth* `Tienda - API`; la clave no está en ningún JSON |
| El bot solo habla con quien está apuntado | `14 · Asistente de Telegram`: cada chat queda apuntado a un teléfono y solo se filtran los apartados de ese teléfono |
| Solo la tienda pregunta por el negocio | `14 · Asistente de Telegram`: `TELEGRAM_ADMIN_ID` en `data/config.csv` |
| El aviso de error no lleva claves | `08 · Avisos de error`: el mensaje se limpia de tokens y claves antes de enviarlo |
| Las credenciales no están en el repositorio | `.env` y las credenciales de n8n están en el `.gitignore`; la CI busca secretos en cada PR |

## 6. Lo que falta para el RGPD completo

- La app no tiene campo de consentimiento: si el negocio lo pide, habría que añadirlo (o un
  fichero de consentimientos) y que los flujos lo consulten antes de escribir.
- No hay cifrado en reposo de los *static data* de n8n (los lleva el volumen de n8n).
- No hay política de conservación: los *static data* se borran a mano desde la interfaz de n8n
  (*Workflows → ⋮ → Settings → Static Data*).
