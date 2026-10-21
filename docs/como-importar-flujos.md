# Cómo importar y probar los flujos

## 1. Requisitos

- Docker Desktop abierto.
- La app y n8n levantados: `docker compose up -d`.
- Las credenciales de n8n creadas ([`credenciales.md`](credenciales.md)).

## 2. Importar los flujos

Hay dos formas. La recomendada es la primera, porque además **enlaza** los subflujos.

### Opción A · Con el script (recomendada)

```bash
cp .env.example .env          # edita API_KEY
docker compose up -d

# Importa los 14 flujos, sustituye los ids de los subflujos y los de las credenciales
python scripts/enlazar_flujos.py --url http://localhost:5678
```

El script:

1. Importa los JSON de `workflows/` en n8n.
2. Pregunta a n8n los ids que ha asignado a cada flujo.
3. Sustituye en los JSON los marcadores `PENDIENTE_ID_*` por el id real del subflujo destino.
4. Sustituye los ids de las credenciales por los de tu instancia.
5. Vuelve a subir los flujos ya enlazados.

> Los marcadores existen porque el id de un flujo es distinto en cada instancia: en tu n8n
> serán otros. El script se encarga; si prefieres hacerlo a mano, en cada nodo *Execute
> Workflow* eliges el subflujo en el desplegable.

### Opción B · A mano desde el editor

1. En n8n: *Workflows → ⋮ (arriba a la derecha) → Import from File*.
2. Sube el JSON de `workflows/`.
3. **Importa primero los subflujos** (`sub-notificar`, `sub-buscar-apartado`, `sub-avisar-vale`),
   luego los flujos que los usan.
4. En cada nodo *Execute Workflow*, elige el subflujo en el desplegable (viene con el id de
   ejemplo, que no existe en tu instancia).

## 3. Configurar las credenciales

Después de importar, en cada nodo que muestre "credential not found" hay que elegir la
credencial:

| Nodo | Credencial |
|---|---|
| `Buscar apartados activos`, `Registrar abono`, `Ventas del dia`, `Apartados activos`, `Vencer apartado`, `Ventas del mes`, `Abonos del mes`, `Apartados`, `Vales`, `Crear apartado`, `Crear abono`, `Ver el estado de la tienda`, `Buscar apartados existentes` | `Tienda - API` (Header Auth) |
| `Enviar email` | `SMTP - Paso Firme` |
| `Enviar Telegram` | `Telegram - Paso Firme` |
| `Correo del banco` | `Banco - IMAP` |
| `Modelo de lenguaje` | `Modelo - Groq` |

## 4. Publicar los flujos

En n8n 2.x, un flujo con webhook **no recibe nada hasta que se publica** (botón *Publish*):

| Flujo | Publicar | Por qué |
|---|---|---|
| `00 · Despachador de eventos` | Sí | Es el webhook que usa la app (`/webhook/tienda`) |
| `01`, `02`, `04` | Sí | Son subflujos: se ejecutan desde el despachador |
| `03 · Abonos a distancia` | Sí | Tiene webhook de prueba y trigger de IMAP |
| `11 · Apartados desde casa` | Sí | El formulario está en `/webhook/apartar-zapatos` |
| `13 · Ventas del datáfono` | Sí | Importa cada noche a las 02:00; también se puede lanzar a mano con `POST /webhook/datxfono` |
| `14 · Asistente de Telegram` | Sí | Necesita un bot de Telegram (ver más abajo) |
| `05`, `06`, `07` | Sí | Programados: sin publicar no se ejecutan |
| `08 · Avisos de error` | Sí | Y además hay que marcarlo como *Error Workflow* en los demás |
| `sub-notificar`, `sub-buscar-apartado`, `sub-avisar-vale` | Sí | Los usan los demás flujos |
| `10 · Migración del Excel`, `90 · Datos de demo` | No | Se ejecutan a mano desde el editor |

**Orden**: primero los subflujos, luego los que los usan. n8n no deja publicar un flujo que
llama a otro que no esté publicado.

### El Error Workflow

1. Publica `08 · Avisos de error`.
2. En cada flujo que deba avisar: *Settings → Error Workflow → 08 · Avisos de error*.

## 4 bis. El bot de Telegram (flujo 14)

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram y crea un bot: te da un token
   (parecido a `123456789:AAH...`).
2. En n8n, edita la credencial `Telegram - Paso Firme` y pega ese token.
3. En `data/config.csv`, pon tu chat id en `TELEGRAM_ADMIN_ID` (solo tú debes poder preguntar
   por las cifras de la tienda). Para saber tu chat id, escribe cualquier cosa al bot y míralo en
   *Executions* → el nodo *Telegram Trigger* → `message.chat.id`.
4. Publica el flujo y habla con el bot.

Sin la credencial, el flujo se publica pero no recibe mensajes; el resto de flujos no se ven
afectados.

## 5. Probar

### Con el servidor SMTP de desarrollo

Para ver los correos que se envían, sin tener que configurar un SMTP de verdad:

```bash
python scripts/smtp_desarrollo.py
```

Guarda cada correo en `data/envios/` (el `.eml` original y un `.txt` con el texto plano).

### La batería de pruebas

```bash
python scripts/probar_flujos.py            # todas
python scripts/probar_flujos.py --flujo 3  # solo el de abonos a distancia
python scripts/probar_flujos.py --caso 05_bizum_romero.eml
```

La prueba **reinicia la tienda** (borra la base de datos y la vuelve a levantar con los datos de
ejemplo) para que los resultados sean los mismos siempre. Con `--sin-reset` no lo hace.

Comprueba:

| Flujo | Qué comprueba |
|---|---|
| 1 | Al crear un apartado, el cliente recibe la confirmación con los importes correctos |
| 2 | Al abonar, el cliente recibe el recibo con lo que queda pendiente |
| 3 | Los 9 correos de `data/correos/` se resuelven como dice la tabla del enunciado |
| 4 | Una venta por debajo del umbral no avisa; una por encima, sí |

### Probar a mano los flujos programados

Los flujos 5, 6 y 7 están programados (23:00, 08:30 y día 1 a las 09:00). Para verlos funcionar
sin esperar, se puede hacer una copia con un webhook delante:

1. En n8n, duplica el flujo.
2. Borra el nodo *Schedule Trigger* y pon un *Webhook* (POST) con un path libre.
3. Publícalo y llama a `http://localhost:5678/webhook/<tu-path>`.
4. Revisa el correo que le llega a Marisa.

### Probar el Error Workflow

1. Crea un flujo de prueba con un *Webhook* y un nodo *Code* que lance un error:
   `throw new Error('prueba');`
2. En *Settings → Error Workflow*, elige `08 · Avisos de error`.
3. Publícalo y llácalo: a Marisa le llega el aviso con el flujo, el paso y el error.

## 6. Comprobar que los JSON siguen siendo válidos

```bash
python scripts/validar_flujos.py
```

Comprueba que cada flujo tiene la forma mínima de n8n, que las conexiones apuntan a nodos que
existen, que **no hay credenciales escritas dentro** y que no queda ningún marcador
`PENDIENTE_ID_*` sin resolver. Es lo que corre la CI (`.github/workflows/validar-flujos.yml`).

## 7. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| La app avisa y en n8n no aparece nada | El flujo no está publicado | Botón *Publish* en el despachador |
| `404` en el webhook | El flujo está en modo *test* | Publicar: la app usa la *Production URL* |
| `401` en las llamadas a la API | La credencial `Tienda - API` no está enlazada o el `API_KEY` no coincide | Comprobar el `Name` (exactamente `X-API-Key`) y el valor |
| El flujo 3 no extrae los datos | Falta la credencial `Modelo - Groq` | No es un error: entra el extractor por regex. Si quieres el modelo, crea la credencial |
| El flujo 3 se para en el nodo del modelo | Sin credencial el nodo falla | Está en *On Error → Continue*; el flujo sigue con el extractor por regex |
| No llegan los correos | SMTP mal configurado | Probar con `scripts/smtp_desarrollo.py` y mirar `data/envios/` |
| `Access to the file is not allowed` | n8n 2.x restringe la lectura de ficheros | `N8N_RESTRICT_FILE_ACCESS_TO` (ya viene en el `docker-compose.yml`) |
| Los Flows no se ven en el editor | Se importaron con otro `typeVersion` | En n8n 2.x se actualizan solos; si no, recrear el nodo |
