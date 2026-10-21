# Changelog

Todas las novedades del proyecto. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es
[SemVer](https://semver.org/lang/es/).

## [1.2.0] - 2026-10-21

### Añadido

- `14 · Asistente de Telegram` (HU-11 y HU-12): un bot al que el cliente pregunta cuánto le
  falta por pagar y la tienda pregunta por la recaudación y los vencimientos. El bot apunta
  cada chat a un teléfono y **solo enseña los apartados de ese teléfono**.
- `SUB · Tool saldo del cliente` y `SUB · Tool cifras de la tienda`: las dos herramientas que
  usa el bot, que van a la API de la tienda.
- `11 · Apartados desde casa` (HU-13): un formulario web para pedir un apartado desde casa. La
  tienda recibe la solicitud con un código y el apartado se confirma cuando llega el abono inicial.
- `13 · Ventas del datáfono` (HU-13): cada noche se importa el CSV de los cobros con tarjeta
  como ventas, sin duplicar los cobros ya importados.
- `docs/rgpd.md`: qué datos se guardan, qué sale de nuestra máquina y con qué criterio se avisa
  a alguien (HU-14).
- `.opencode/command/`: dos comandos de OpenCode para las tareas repetitivas
  (`/generar-spec` y `/revisar-flujo`).

### Corregido

- **El webhook de la tienda va protegido** (HU-14): sin el token correcto responde `401` y no
  ejecuta nada. El token va en `data/config.csv` (`WEBHOOK_TOKEN`) y en la URL del webhook del
  `.env` de la tienda.
- Los recordatorios los redacta ahora el modelo con un tono más cercano, y un nodo comprueba
  que **no ha cambiado ninguna cifra**: si las ha cambiado, se usa el texto original.
- La búsqueda de apartados por teléfono se hace por dígitos (la búsqueda `q` de la app es un
  `LIKE` y no encontraba `600000001` dentro de `600 000 001`).
- El importador del datáfono registra **una venta por cobro** (antes registraba solo el
  primero) y no importa dos veces el mismo cobro.

## [1.1.0] - 2026-10-21


### Añadido

- `data/config.csv`: la configuración de los flujos (a quién se avisa, el umbral de la venta
  grande, los días de aviso) sale de aquí. Los flujos lo leen en cada ejecución, así que se
  cambia **sin tocar ningún flujo** ni republicar nada (criterio de HU-09).
- `docs/bitacora.md`: la bitácora técnica del proyecto, con las decisiones, la comparativa de
  modelos y los doce fallos encontrados al construir y probar los flujos.

### Corregido

- La configuración ya no dependía de las variables de n8n (`$vars`), que en la edición
  comunitaria no existen, ni de `$env`, que n8n 2.x bloquea en las expresiones
  (`access to env vars denied`). Ahora se lee de `data/config.csv`.
- El valor `DIAS_AVISO_VENCIMIENTO` va entre comillas en el CSV: `7,1` sin comillas rompía la
  lectura del fichero.
- La configuración se lee **sin BOM**: un fichero guardado con BOM añadía un carácter invisible
  al nombre de la primera clave.
- El flujo 06 vuelve a leer los apartados del nodo que los pide a la API (la configuración va
  por delante en la cadena).
- Los nodos del flujo 03 se llaman «Extraer los datos» y «Modelo de lenguaje», en vez de
  nombres con siglas.

## [1.0.1] - 2026-10-21

### Corregido

- `docs/credenciales.md`: la lista de credenciales incluía `Histórico - Sheets`, que ningún flujo
  usa. El histórico de cierres y de recordatorios se guarda en los *static data* de cada flujo.

## [1.0.0] - 2026-10-21

Primera entrega: **nivel 🟢 Esencial + 🟡 Medio**. Ocho automatizaciones, tres subflujos
reutilizables, sus specs, sus pruebas y la documentación.

### Añadido

**Flujos**

- `00 · Despachador de eventos`: un único webhook (`POST /tienda`) que reparte los cuatro
  eventos de la app con un nodo Switch.
- `01 · Confirmación de apartado`: el cliente recibe qué ha apartado, cuánto ha abonado, cuánto
  le falta y hasta cuándo. Sin correo, avisa a la tienda y el flujo no falla.
- `02 · Recibo de abono`: recibo con el importe pagado y lo pendiente; si el apartado queda
  liquidado, el mensaje cambia y avisa de que puede recoger los zapatos.
- `03 · Abonos a distancia`: lee los avisos del banco, extrae ordenante, importe y concepto (con
  un modelo de lenguaje y con un extractor de respaldo), busca el apartado por API y registra el abono. Si hay
  dudas, paga de más o está fuera de plazo, no registra nada y pregunta a Marisa.
- `04 · Aviso de venta grande`: avisa de las ventas por encima de `$env.UMBRAL_VENTA_GRANDE`.
- `05 · Cierre diario`: cada noche, ventas, abonos y total desglosados por forma de pago.
- `06 · Recordatorios y vencimientos`: recuerda los vencimientos (7 y 1 días), vence por API los
  apartados fuera de plazo, avisa del vale y manda a la tienda la lista de zapatos que vuelven.
- `07 · Informe mensual`: el día 1, recaudación del mes (ventas y abonos por separado), total
  pendiente de cobro y apartados nuevos, liquidados y vencidos.
- `08 · Avisos de error`: error workflow que avisa del flujo, el paso y el error, limpiando
  cualquier clave que se haya colado en el mensaje.
- `10 · Migración del Excel`: limpia los CSV de `data/`, migra apartados y abonos con su fecha
  original, no duplica al ejecutarlo dos veces e informa de los casos dudosos.
- `90 · Datos de demo`: crea datos de ejemplo por API para las demos.

**Subflujos reutilizables**

- `SUB · Notificar`: envía por correo o Telegram y dice si ha salido.
- `SUB · Buscar apartado`: decide a qué apartado pertenece un pago remoto.
- `SUB · Avisar vale`: avisa al cliente del vale y a la tienda de los zapatos que vuelven.

**Documentación y herramientas**

- `specs/`: la ontología del dominio y la especificación de cada automatización, con sus
  criterios de aceptación.
- `AGENTS.md`: el contexto del proyecto, con las reglas del negocio y las trampas de n8n 2.x.
- `docs/`: mapa del proceso (antes y después), kanban, credenciales, guía de importación,
  bitácora técnica y retrospectiva.
- `scripts/enlazar_flujos.py`: importa los flujos en n8n y resuelve los ids de subflujos y
  credenciales de la instancia.
- `scripts/validar_flujos.py`: valida los JSON y busca credenciales escritas dentro.
- `scripts/smtp_desarrollo.py`: servidor SMTP de desarrollo para ver los correos que se envían.
- `scripts/probar_flujos.py`: batería de pruebas contra la tienda de verdad.
- `tests/`: datos de prueba y resultados esperados de cada flujo.
- CI en GitHub Actions que valida los JSON en cada PR.

### Verificado

Los flujos 1, 2, 3 y 4 se prueban automáticamente contra la app (`scripts/probar_flujos.py`):
24 comprobaciones, todas en verde, incluidos los nueve correos de `data/correos/`. Los flujos 5,
6, 7, 8 y 10 se han ejecutado a mano contra la app (ver `docs/evidencias/`).

[1.0.0]: https://github.com/Factoria-F5-madrid/AI-project-automatizaciones-n8n
