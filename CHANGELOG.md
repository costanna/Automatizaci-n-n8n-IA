# Changelog

Todas las novedades del proyecto. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es
[SemVer](https://semver.org/lang/es/).

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
  IA y con un extractor de respaldo), busca el apartado por API y registra el abono. Si hay
  dudas, paga de más o está fuera de plazo, no registra nada y pregunta a Marisa.
- `04 · Aviso de venta grande`: avisa de las ventas por encima de `$vars.UMBRAL_VENTA_GRANDE`.
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
- `AGENTS.md`: el contexto que se le da al agente de IA, con las trampas de n8n 2.x.
- `docs/`: mapa del proceso (antes y después), kanban, credenciales, guía de importación,
  bitácora de IA y retrospectiva.
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
