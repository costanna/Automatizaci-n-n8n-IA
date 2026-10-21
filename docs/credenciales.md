# Credenciales y variables

> **Ninguna credencial vive en este repositorio.** Las claves se crean en n8n
> (*Credentials → New*) y la configuración de los flujos está en
> [`data/config.csv`](../data/config.csv). Ni en los JSON de los flujos ni en los mensajes ni en
> los logs hay claves.

## 1. Credenciales que necesita cada flujo

| Credencial | Tipo en n8n | Qué guarda | Dónde se usa |
|---|---|---|---|
| `Tienda - API` | **Header Auth** | Name: `X-API-Key` · Value: el `API_KEY` de tu `.env` | `sub-buscar-apartado`, `03`, `05`, `06`, `07`, `10`, `90` |
| `SMTP - Paso Firme` | **SMTP** | Host, puerto, usuario y contraseña del correo saliente | `sub-notificar` (envío de todos los mensajes) |
| `Banco - IMAP` | **IMAP** | Host, puerto, usuario y contraseña del buzón del banco | `03 · Abonos a distancia` (leer los avisos) |
| `Telegram - Paso Firme` | **Telegram API** | El token del bot | `sub-notificar` (canal opcional) |
| `Modelo - Groq` | **OpenAI compatible** | La clave del proveedor (Groq, OpenRouter, Gemini…) y la URL base | `03 · Abonos a distancia` (extraer los datos del aviso) |
| `Gmail - Paso Firme` | **Gmail OAuth2** | La cuenta de Gmail de la tienda | Alternativa al SMTP para enviar |

> **Ningún flujo necesita una credencial de Google Sheets.** El histórico de cierres y el de
> recordatorios se guarda en los *static data* de cada flujo (la memoria de n8n entre
> ejecuciones), que es lo que hace `06 · Recordatorios y vencimientos` para no avisar dos veces al
> mismo cliente. Si algún día se quiere el histórico en una hoja de cálculo, se añade el nodo
> *Google Sheets* en `05 · Cierre diario` y la credencial `Histórico - Sheets` en esta tabla.

### Cómo se crea cada una

**`Tienda - API` (Header Auth)**

| Campo | Valor |
|---|---|
| Name | `X-API-Key` (en mayúsculas, tal cual) |
| Value | el valor de `API_KEY` de tu `.env` |

**`SMTP - Paso Firme`**

| Campo | Valor |
|---|---|
| Host | `smtp.tu-proveedor.com` |
| Port | `587` (o `465` si es SSL) |
| User / Password | los de la cuenta de la tienda |
| SSL/TLS | según el proveedor |

> Para desarrollo, `scripts/smtp_desarrollo.py` levanta un servidor SMTP en el puerto 1025 del
> ordenador: el contenedor lo alcanza con el host `host.docker.internal`, puerto `1025`, sin
> usuario ni contraseña, y guarda cada correo en `data/envios/`. Es lo que se usa en las pruebas.

**`Banco - IMAP`**

| Campo | Valor |
|---|---|
| Host | `imap.tu-banco.com` |
| Port | `993` (o `143`) |
| User / Password | los del buzón donde llegan los avisos |
| Mailbox | `INBOX` |

**`Modelo - Groq` (OpenAI compatible)**

| Campo | Valor |
|---|---|
| API Key | la clave del proveedor elegido |
| Base URL | `https://api.groq.com/openai/v1` (Groq) o `https://openrouter.ai/api/v1` (OpenRouter) |

> El nodo `OpenAI Chat Model` de n8n habla con cualquier API compatible con OpenAI, así que
> Groq, OpenRouter o Gemini sirven. **El flujo 3 no depende del modelo**: si no está configurado,
> un extractor por expresiones regulares hace el relevo (ver `specs/03-abonos-distancia.md`).

## 2. Configuración de los flujos

La configuración (a quién se avisa, el umbral de la venta grande, los días de aviso) **no está en
los flujos**: está en [`data/config.csv`](../data/config.csv), un fichero de dos columnas
(`clave,valor`) que los flujos leen en cada ejecución.

| Clave | Valor por defecto | Para qué | Quién la usa |
|---|---|---|---|
| `EMAIL_MARISA` | `marisa@pasofirme.example` | A quién se avisa a la tienda | Todos los flujos |
| `EMAIL_TIENDA` | `tienda@pasofirme.example` | Remitente de los correos | `sub-notificar` |
| `UMBRAL_VENTA_GRANDE` | `200` | A partir de qué importe se avisa de una venta | `04 · Aviso de venta grande` |
| `DIAS_AVISO_VENCIMIENTO` | `7,1` | Cuántos días antes se avisa del vencimiento | `06 · Recordatorios y vencimientos` |

> **Por qué un fichero y no las variables de n8n.** En la edición comunitaria de n8n, *Settings →
> Variables* no existe (es una función de pago: `Your license does not allow for
> feat:variables`) y el acceso a `$env` está bloqueado en las expresiones
> (`access to env vars denied`). Un fichero montado en el contenedor funciona en cualquier
> edición, no necesita credenciales y **se cambia sin tocar ningún flujo**: es el criterio de
> aceptación de HU-09.

Para cambiar algo:

```bash
# editar data/config.csv y ya está: los flujos leen el fichero en cada ejecución
notepad data/config.csv
```

> Ojo con el formato: es un CSV, así que un valor con coma va entre comillas
> (`DIAS_AVISO_VENCIMIENTO,"7,1"`) y el fichero se guarda **sin BOM**.

## 3. Variables de entorno (fuera de n8n)

Van en el `.env` de la raíz del proyecto, que **nunca** se sube al repositorio.

| Variable | Para qué | Dónde la lee |
|---|---|---|
| `API_KEY` | La clave que la app exige en la cabecera `X-API-Key` | La app (y la credencial `Tienda - API` de n8n) |
| `N8N_WEBHOOK_URL` | A dónde avisa la app: `http://n8n:5678/webhook/tienda` | La app |
| `SEED` | `1` carga los datos de ejemplo, `0` arranca vacía | La app |
| `TZ` / `GENERIC_TIMEZONE` | `Europe/Madrid` | Los dos contenedores |

## 4. Lo que nunca debe pasar

- Escribir una clave en el JSON de un flujo → `scripts/validar_flujos.py` lo busca y falla.
- Mandar una clave en un correo a un cliente → el flujo 8 limpia el mensaje de error antes de enviarlo.
- Subir el `.env` → está en el `.gitignore` desde el primer commit.
- Dejar la clave de la API en el historial de git → si pasa, se cambia la clave y se limpia el
  historial antes de publicar.
