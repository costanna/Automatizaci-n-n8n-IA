# Tablero Kanban · Paso Firme

Una tarjeta por historia de usuario, con sus criterios de aceptación como lista de
comprobación. Las historias que llevan etiqueta de nivel **solo** se hacen si se llega a ese nivel.

## 🗂️ Tablero

| Por hacer | En curso | En revisión | Hecho |
|---|---|---|---|
| | | | HU-01 · Confirmación al apartar 🟢 |
| HU-16 · Funcionar siempre 🔴 | | | HU-02 · Recibo de cada abono 🟢 |
| | | | HU-03 · Abonos por Bizum o transferencia 🟢 |
| | | | HU-04 · Cierre de caja automático 🟢 |
| | | | HU-05 · Avisos de errores 🟢 |
| | | | HU-06 · Recordatorios de vencimiento 🟡 |
| | | | HU-07 · Apartados vencidos con su vale 🟡 |
| | | | HU-08 · Informe mensual 🟡 |
| | | | HU-09 · Aviso de ventas grandes 🟡 |
| | | | HU-10 · Migración del Excel 🟡 |
| | | | HU-11 · Preguntar saldo por Telegram 🟠 |
| | | | HU-12 · Marisa pregunta a su negocio 🟠 |
| | | | HU-13 · Entrada automática de datos 🟠 |
| | | | HU-14 · Datos personales protegidos 🟠 |
| | | | HU-15 · Panel para Marisa 🔴 |
| | | | HU-16 · Funcionar siempre 🔴 |

## 📋 Tarjetas

### HU-01 · Confirmación al apartar 🟢

> Como **cliente**, quiero recibir un mensaje al apartar unos zapatos, para tener claro qué he
> apartado, cuánto he pagado, cuánto me falta y hasta cuándo.

- [x] Al crear un apartado en la app, el cliente recibe un mensaje en menos de un minuto.
- [x] El mensaje incluye modelo, talla, precio, abonado, pendiente y fecha límite, con los importes que da la app.
- [x] Si el cliente no tiene correo, el flujo no falla: avisa a la tienda de que no se pudo enviar.

**Flujo:** `01 · Confirmación de apartado` · **Spec:** `specs/01-confirmacion-apartado.md`
**Prueba:** `scripts/probar_flujos.py --flujo 1`

### HU-02 · Recibo de cada abono 🟢

> Como **cliente**, quiero un recibo cada vez que pago un abono, para saber cuánto me queda por pagar.

- [x] Cada abono registrado genera un recibo con el importe pagado y lo que queda pendiente.
- [x] Si el apartado queda liquidado, el mensaje cambia: avisa de que ya puede recoger sus zapatos.

**Flujo:** `02 · Recibo de abono` · **Spec:** `specs/02-recibo-abono.md`
**Prueba:** `scripts/probar_flujos.py --flujo 2`

### HU-03 · Abonos por Bizum o transferencia sin apuntar nada a mano 🟢

> Como **Marisa**, quiero que los pagos que me llegan por Bizum o transferencia se registren solos
> en el apartado correcto, para dejar de revisar los avisos del banco y apuntarlos a mano.

- [x] Los correos que no son un pago (como la publicidad del banco) se ignoran.
- [x] De cada pago se extraen ordenante, importe y concepto, y se busca el apartado por API.
- [x] Si hay un único apartado claro, se registra el abono y el cliente recibe su recibo (HU-02).
- [x] Si el pago es dudoso (varios apartados posibles, sin concepto o cliente desconocido), no se registra nada y se pregunta a Marisa.
- [x] Si el importe supera lo pendiente o el apartado está fuera de plazo, no se registra nada y se avisa a Marisa con el motivo.
- [x] El flujo resuelve bien los correos de `data/correos/`.

**Flujo:** `03 · Abonos a distancia` + `SUB · Buscar apartado` · **Spec:** `specs/03-abonos-distancia.md`
**Prueba:** `scripts/probar_flujos.py --flujo 3` (los 9 correos)

### HU-04 · Cierre de caja automático 🟢

> Como **Marisa**, quiero recibir cada noche el resumen de lo cobrado en el día, para cerrar la caja
> sin sumar con calculadora.

- [x] Cada noche llega un resumen con ventas directas, abonos y el total, separados por forma de pago (efectivo, tarjeta y Bizum).
- [x] Los importes coinciden con los de la app.
- [x] Si ese día no hubo movimientos, el resumen lo dice en vez de fallar.

**Flujo:** `05 · Cierre diario` · **Spec:** `specs/05-cierre-diario.md`

### HU-05 · Avisos de errores 🟢

> Como **Marisa**, quiero que me avisen si una automatización falla, para no descubrir semanas
> después que algo dejó de funcionar.

- [x] Cualquier flujo que falle envía un aviso con el nombre del flujo, el paso y el error.
- [x] El aviso no incluye contraseñas ni claves.

**Flujo:** `08 · Avisos de error` · **Spec:** `specs/08-error-workflow.md`
**Prueba:** flujo de prueba que falla a propósito (`docs/como-importar-flujos.md`)

### HU-06 · Recordatorios de vencimiento 🟡

> Como **cliente**, quiero que me avisen antes de que se acabe el plazo de mi apartado, para no
> perder mis zapatos ni lo que ya he pagado.

- [x] Cada mañana se avisa a los clientes cuyo plazo vence en 7 días y en 1 día.
- [x] Cada cliente recibe cada aviso una sola vez.
- [x] El mensaje incluye lo que falta por pagar y la fecha límite.
- [x] El aviso está redactado con un tono más cercano (lo redacta el modelo, y un nodo comprueba que las cifras no han cambiado).

**Flujo:** `06 · Recordatorios y vencimientos` · **Spec:** `specs/06-recordatorios-vencimientos.md`

### HU-07 · Apartados vencidos con su vale 🟡

> Como **Marisa**, quiero que los apartados que se pasan de plazo se cierren solos y el cliente
> reciba un vale, para recuperar los zapatos y no tener que gestionarlo uno a uno.

- [x] Los apartados fuera de plazo se vencen por API y la app genera el vale.
- [x] El cliente recibe un mensaje con el código y el importe de su vale.
- [x] Marisa recibe la lista de zapatos que vuelven a la venta.

**Flujo:** `06 · Recordatorios y vencimientos` + `SUB · Avisar vale`

### HU-08 · Informe mensual 🟡

> Como **Marisa**, quiero un informe a principios de mes con lo recaudado y lo que me deben, para
> saber cómo va el negocio sin hacer cuentas.

- [x] El día 1 llega un informe con lo recaudado el mes anterior (ventas directas y abonos por separado).
- [x] Incluye el total pendiente de cobro, y los apartados nuevos, liquidados y vencidos del mes.
- [x] Los importes coinciden con los de la app.

**Flujo:** `07 · Informe mensual` · **Spec:** `specs/07-informe-mensual.md`

### HU-09 · Aviso de ventas grandes 🟡

> Como **Marisa**, quiero que me avisen de las ventas grandes, para enterarme aunque no esté en la tienda.

- [x] Las ventas por encima de un importe configurable generan un aviso a Marisa.
- [x] Cambiar el importe no obliga a editar el flujo (está en `data/config.csv`).

**Flujo:** `04 · Aviso de venta grande` · **Configuración:** `UMBRAL_VENTA_GRANDE`

### HU-10 · Migración del Excel antiguo 🟡

> Como **Marisa**, quiero pasar los datos de mi Excel a la app, para no perder el histórico ni
> mantener dos sistemas.

- [x] Los CSV de `data/` se leen y se limpian (fechas, nombres, importes con €).
- [x] Los apartados y abonos se crean en la app por API conservando su fecha original.
- [x] Ejecutarlo dos veces no duplica los datos.
- [x] Los casos dudosos (por ejemplo, un abono inicial menor de 5 €) no se cargan y salen en un informe para que Marisa decida.

**Flujo:** `10 · Migración del Excel` · **Spec:** `specs/10-migracion-excel.md`

### HU-11 · Preguntar saldo por Telegram 🟠

> Como **cliente**, quiero preguntar por Telegram cuánto me falta por pagar, para no tener que llamar o pasar por la tienda.

- [x] El asistente identifica al cliente y solo le muestra sus apartados, nunca los de otro.
- [x] Responde con el saldo y la fecha límite que da la app, nunca con cifras calculadas por el modelo.
- [x] Si no entiende la pregunta o no encuentra al cliente, lo dice y ofrece hablar con la tienda.

**Flujo:** `14 · Asistente de Telegram` + `SUB · Tool saldo del cliente`
**Spec:** `specs/14-asistente-telegram.md`

### HU-12 · Marisa pregunta a su negocio 🟠

> Como **Marisa**, quiero preguntar por Telegram *"¿cuánto se recaudó esta semana?"* o *"¿qué apartados vencen este mes?"*, para tener las cifras al momento.

- [x] Solo responde a Marisa (usuario autorizado).
- [x] Las respuestas salen de consultas a la API de la tienda.

**Flujo:** `14 · Asistente de Telegram` + `SUB · Tool cifras de la tienda`
**Configuración:** `TELEGRAM_ADMIN_ID`

### HU-13 · Entrada automática de datos 🟠

> Como **dependienta**, quiero que ciertos datos entren solos, para dedicarme a atender a los clientes.

- [x] *Apartados desde casa:* el cliente pide apartar unos zapatos con el formulario, n8n crea la solicitud, avisa a la tienda y el apartado se confirma cuando llega el abono inicial.
- [x] *Datáfono:* cada noche se importa el CSV de cobros con tarjeta como ventas, sin duplicar las ya registradas.

**Flujos:** `11 · Apartados desde casa` y `13 · Ventas del datáfono`
**Specs:** `specs/11-apartados-desde-casa.md`, `specs/13-ventas-datxfono.md`
**Pruebas:** `scripts/probar_flujos.py --flujo 11` y `--flujo 13`

### HU-14 · Datos personales protegidos 🟠

> Como **cliente**, quiero que mis datos se traten con cuidado, para que no se compartan con más de lo necesario.

- [x] El webhook de n8n exige autenticación y rechaza peticiones sin ella (401).
- [x] A los modelos de IA solo se envía lo imprescindible y está documentado qué datos salen.
- [x] Solo se envían mensajes a clientes que han dado su consentimiento.

**Flujos:** `00 · Despachador de eventos` (token), `14 · Asistente de Telegram` (consentimiento y filtrado)
**Doc:** [`docs/rgpd.md`](rgpd.md)

### HU-15 · Panel para Marisa 🔴

> Como **Marisa**, quiero ver en una pantalla las ventas, la recaudación, lo pendiente de cobro y los
> apartados que van a vencer, para decidir sin abrir hojas ni correos.

- [x] El panel muestra los datos de la app actualizados (n8n los consulta en cada visita).
- [x] Se entiende sin explicación y se ve bien en el móvil (diseño responsive, se actualiza solo).

**Flujo:** `15 · Panel de Marisa` · **Spec:** `specs/15-panel-marisa.md`
**Prueba:** `http://localhost:5678/webhook/panel` (y `?formato=json`)

### HU-16 · Funcionar siempre 🔴

> Como **Marisa**, quiero que las automatizaciones sigan funcionando aunque se reinicie el
> ordenador, para no depender de que alguien las encienda.

- [x] Despliegue en la nube con HTTPS preparado (`deploy/render.yaml`, `deploy/Dockerfile.n8n` y la guía [`docs/despliegue.md`](despliegue.md)).
- [x] Copias de seguridad automáticas de los datos de n8n (servicio `backup` del compose, cron en la nube y `scripts/backup_n8n.py`).
- [x] Un cambio en los flujos pasa por CI (validación de los JSON, importándolos de verdad en n8n) antes de mergear.

**CI:** `.github/workflows/validar-flujos.yml` · **Backups:** `scripts/backup_n8n.py`

## 👥 Reparto (pareja)

| Persona | Tarea |
|---|---|
| Persona 1 | Flujos 1, 2, 8, 11 y 14 (avisos al cliente y entrada de solicitudes) |
| Persona 2 | Flujos 3, 5, 6, 7, 10 y 13 (caja, vencimientos, informes y datos) |
| Las dos | El asistente de Telegram (flujo 14) y la revisión cruzada de cada PR |

Ninguna pareja toca dos ramas a la vez: el tablero marca una tarjeta en curso por persona.
