# Despliegue en la nube

Cómo dejar el proyecto **funcionando siempre** (HU-16): en la nube, con HTTPS, con copias de
seguridad automáticas y con la CI vigilando que los flujos siguen siendo válidos.

## 1. Qué hay preparado en el repositorio

| Fichero | Para qué |
|---|---|
| `deploy/render.yaml` | Blueprint de Render: n8n (web con HTTPS), Postgres y el cron de las copias |
| `deploy/Dockerfile.n8n` | Imagen de n8n con los flujos dentro y el arranque que los importa si hace falta |
| `deploy/Dockerfile.backup` | Imagen del cron que hace la copia de seguridad |
| `deploy/arrancar_con_flujos.sh` | Arranque de n8n en la nube |
| `scripts/backup_n8n.py` | La copia de seguridad (base de datos, clave de cifrado y flujos) |
| `scripts/enlazar_flujos.py` | Importa los flujos en la instancia y resuelve los ids de los subflujos |
| `docker-compose.yml` | Servicios de `backup` (copia cada 24 h) y `postgres` (perfil opcional) |

## 2. Desplegar en Render (recomendado: HTTPS sin tocar nada)

Render emite el certificado TLS automáticamente: la URL del servicio ya es
`https://paso-firme-n8n.onrender.com`.

1. Sube el repositorio a GitHub y crea un **Blueprint** en Render apuntando al repositorio
   (`deploy/render.yaml`).
2. Render crea tres cosas:
   - `paso-firme-n8n`: el servicio web con n8n (disco de 1 GB para los datos).
   - `paso-firme-db`: Postgres 16.
   - `paso-firme-backup`: el cron diario (3:17 de la mañana) que hace la copia.
3. Pon `WEBHOOK_URL` = `https://paso-firme-n8n.onrender.com` (Render te lo pide al
   crear el servicio: es el valor que Render usa para los webhooks y para el editor).
4. **Copia la clave de cifrado** (`N8N_ENCRYPTION_KEY`) del servicio web al cron de
   backup: sin ella, las credenciales de la copia no se pueden descifrar.
5. La app de la tienda también tiene que llegar a n8n: en el `.env` de la tienda,
   `N8N_WEBHOOK_URL=https://paso-firme-n8n.onrender.com/webhook/tienda?token=<token>`.

### Railway, un VPS o Google Cloud

La idea es la misma: n8n detrás de un proxy con TLS (Caddy, Traefik, nginx o el que
resuelva la plataforma) y las variables `WEBHOOK_URL`, `N8N_PROTOCOL=https` y
`N8N_HOST` apuntando al dominio público.

En un VPS, con Docker:

```bash
git clone <tu-repo> && cd <tu-repo>
cp .env.example .env          # API_KEY, N8N_WEBHOOK_URL, WEBHOOK_URL
docker compose up -d          # n8n, la tienda y el servicio de copias
# el proxy delante: caddy o nginx con el certificado de Let's Encrypt
```

## 3. Las copias de seguridad

### En local (Docker)

El servicio `backup` del `docker-compose.yml` ya las hace: cada 24 horas copia la base de
datos de n8n, el `config` con la clave de cifrado y los JSON de los flujos en `backups/`,
y borra las copias viejas (se conservan 14).

```bash
# ver las copias
ls -la backups/
# forzar una copia ahora
docker compose exec backup python /app/scripts/backup_n8n.py --datos /datos --destino /backups
```

### En la nube

El cron de Render hace lo mismo, pero **el destino tiene que ser un disco o un bucket**: un
disco de Render se puede montar en el cron, y si lo que quieres es no depender del
proveedor, un bucket S3 (o el `pg_dump` a un Postgres de otro sitio).

### Cómo se restaura

```bash
# 1. parar n8n
docker compose stop n8n
# 2. devolver la base de datos (y el config con la clave de cifrado)
cp backups/n8n-20261021-031700/database.sqlite n8n_data/database.sqlite
cp backups/n8n-20261021-031700/config n8n_data/config
# 3. arrancar
docker compose start n8n
```

> La copia de la **clave de cifrado** es la importante: sin ella, las credenciales de la copia
> son un montón de bytes inútiles.

### Qué NO se copia

Las credenciales de los proveedores externos (el SMTP, el bot de Telegram, la clave del
modelo) están en el `.env` de cada máquina, no en n8n. Copia también el `.env` (a otro sitio,
con contraseña) si quieres poder restaurarlo todo.

## 4. La CI: ningún cambio llega a producción sin validarse

`.github/workflows/validar-flujos.yml` corre en cada PR y en cada push a `main` y `develop`:

| Trabajo | Qué comprueba |
|---|---|
| Validar los flujos | Que los 20 JSON de `workflows/` son válidos, que las conexiones apuntan a nodos que existen, que **no hay credenciales dentro** y que no quedan marcadores `PENDIENTE_ID_*` sin resolver |
| Specs y flujos | Que cada flujo tiene su spec en `specs/` |
| Sin secretos | Que en todo el repositorio no hay claves (patrones de API, tokens, JWT) |
| Importar en n8n | Levanta n8n en Docker, **importa los flujos de verdad** y comprueba que se importan sin errores |

Ese último trabajo es el que de verdad protege: un JSON puede ser válido y aun así no
importarse.

## 5. Lo que falta para el despliegue automático

- **El `.env` no se versiona** (bien), así que en la nube hay que poner las variables a mano
  o usar los *secretos* del proveedor (Render los tiene).
- **La app de la tienda también hay que desplegarla** (es un servicio más): en `render.yaml`
  está solo n8n. La app se puede desplegar igual, con su propio servicio y su propio disco.
- **El dominio propio**: con `WEBHOOK_URL` apuntando a un dominio propio hay que poner el
  certificado a mano (Caddy lo hace solo).
- **El MCP Server Trigger** (exponer los flujos como servidor MCP para que otros agentes
  consulten la tienda) **no está disponible en la versión de n8n que se usa aquí**: el nodo no
  existe en el paquete instalado. Habría que actualizar n8n o esperar a que lo traiga.
