# Retrospectiva del equipo

Proyecto: automatizaciones con n8n para la zapatería Paso Firme.
Nivel entregado: 🟢 Esencial + 🟡 Medio (10 automatizaciones, 8 flujos + 3 subflujos).

## Qué queríamos

Marisa pierde el tiempo con la libreta y con la calculadora, y los clientes se enteran tarde
de que su apartado se está venciendo. Queríamos que los avisos a los clientes, los vencimientos,
el cierre de caja y el informe mensual dejo de depender de que alguien se acuerde.

## Qué salió bien

- **Empezar por la spec, no por el flujo.** Escribir `specs/03-abonos-distancia.md` antes del
  flujo evitó que inventáramos reglas: la tabla de "qué pasa con cada correo" estaba escrita
  antes de programar nada, y las pruebas se compararon con ella.
- **Que las cifras las calcule la app.** Al principio el flujo 3 recalmaba `pendiente` a mano.
  Se quitó en cuanto vimos que la app ya lo trae. Es la regla que más tiempo nos ha ahorrado
  después.
- **Un extractor de respaldo en el flujo 3.** Cuando el modelo no estaba disponible, el
  flujo siguió funcionando con las expresiones regulares. Fue lo que nos permitió probar los 9
  correos sin depender de ninguna clave externa.
- **Probar de verdad, no de palabra.** Con el servidor SMTP de desarrollo, cada prueba deja un
  correo en `data/envios/`. Ver el mensaje real ha detectado fallos que las aserciones no veían.
- **Git Flow de verdad.** Una rama por flujo, un commit por flujo, y las specs y los flujos
  en el mismo commit. Al final del proyecto se lee el historial como la historia del proyecto.

## Qué salió mal

- **La versión de n8n nos conditioningó el diseño entero.** En n8n 2.x:
  - El nodo `HTTP Request` necesita `authentication: genericCredentialType` **y**
    `genericAuthType: httpHeaderAuth`; si falta, la petición sale sin la cabecera y la API
  responde `401` sin decir nada.
  - Los binarios se guardan en disco, así que el nodo Code no puede leer un CSV: hay que usar el
    nodo *Spreadsheet File*.
  - Los ficheros de n8n están restringidos a `~/.n8n-files`: hace falta `N8N_RESTRICT_FILE_ACCESS_TO`.
  - Los datos estáticos del flujo (`$getWorkflowStaticData`) son la manera de recordar cosas
  entre ejecuciones sin escribir ficheros.

  Nos habría ahorrado medio día que lo hubiéramos leído antes de escribir los flujos.
- **Encadenar dos peticiones HTTP.** La segunda se lanza una vez por item de la primera, con
  expresiones que ya no valen. Se arregla con un nodo Code que devuelva un único item antes de
  cada petición. Nos pasó en los flujos 5 y 7.
- **Asumir el separador del CSV.** Los CSV de Marisa usan **coma**, no punto y coma, y los
  importes mezclan `89.90` (formato inglés) y `1.842,30` (formato español). Se detectó porque
  la migración cargaba 0 filas; se detectó *tarde*, cuando ya dabamos por buena la primera
  versión.
- **El flujo 03 con dos salidas mal conectadas.** La rama de éxito del `If` estaba conectada
  donde iba la de error, y Marisa recibía un aviso de "no he registrado nada" justo después de
  registrar el abono.
- **La regex del `Concepto:` vacío.** `\s*` en una regex salta de línea: el extractor leía
  "El importe ya está disponible..." como si fuera el concepto. Consecuencia: el correo de
  `05_bizum_romero` se registraba en vez de preguntar a Marisa. Lo detectó la prueba, no la
  revisión del código.

## Qué aprendimos

1. **Las pruebas automáticas de los flujos son posibles y merece la pena.** `scripts/probar_flujos.py`
   prueba cuatro flujos contra la tienda de verdad, con los 9 correos del enunciado. Sin eso,
   los errores de arriba se habrían publicado.
2. **Repetir la prueba es más rápido que revisar el código.** Cuando un flujo falla, mirar la
   ejecución en n8n (el JSON del item en cada nodo) enseña más que leer el flujo.
3. **Escribir los flujos en JSON a mano es viable**, pero hay que mirar la versión real de cada
   nodo en el contenedor (`dist/nodes/<Nodo>/<Nodo>.node.js`) y no fiarse de la memoria ni de los
   tutoriales.
4. **Un fallo silencioso es peor que un fallo ruidoso.** El `401` de la API no se veía en el
   editor: el flujo funcionaba y no hacía nada. Merece la pena un flujo de prueba que llame a la
   API y compruebe que la respuesta no es un error.

## Qué haríamos distinto

- **Antes de escribir el primer flujo, leer la versión de los nodos** (o ejecutar el `n8n-mcp`
  que recomienda el enunciado). Media hora de lectura nos habría ahorrado un día de depuración.
- **Hacer el "hola mundo" del webhook y de la API en el minuto uno**: un flujo con un webhook y
  una llamada a la tienda. Si eso no funciona, nada más funciona.
- **Escribir la prueba de los 9 correos antes que el flujo 3**, no después. Los casos del
  enunciado son un contrato: si el flujo no los cumple, el flujo está mal.
- **Reservar una tarde para el `docker compose` y el `docker cp` de los ficheros**: los
  contenedores, los volúmenes y el `host.docker.internal` son el punto donde más tiempo se
  pierde.

## Estado final

| Flujo | Estado | Pruebas |
|---|---|---|
| 00 · Despachador de eventos | ✅ | Recibe los 4 eventos y reparte |
| 01 · Confirmación de apartado | ✅ | 3 comprobaciones OK |
| 02 · Recibo de abono | ✅ | 3 comprobaciones OK |
| 03 · Abonos a distancia | ✅ | 13 comprobaciones OK (los 9 correos) |
| 04 · Aviso de venta grande | ✅ | 2 comprobaciones OK |
| 05 · Cierre diario | ✅ | Cierre con desglose por forma de pago |
| 06 · Recordatorios y vencimientos | ✅ | Recordatorios (7 y 1 día), vencimientos y vales |
| 07 · Informe mensual | ✅ | Recaudación, pendiente y apartados del mes |
| 08 · Avisos de error | ✅ | Avisa con flujo, paso y error, y limpia las claves |
| 10 · Migración del Excel | ✅ | 7 apartados migrados, 2 dudosos y no duplica al repetir |
| 90 · Datos de demo | ✅ | Crea datos de ejemplo por API |

## Lo que queda fuera

- 🟠 El asistente de Telegram (HU-11 y HU-12): la arquitectura ya está preparada
  (`SUB · Notificar` acepta los dos canales), pero falta el nodo de modelo de lenguaje.
- 🟠 La entrada automática de datos (HU-13).
- 🟠 El panel para Marisa (HU-15) y el despliegue con HTTPS y CI (HU-16).
- La API de la tienda no expone un histórico de estados: el informe mensual aproxima los
  apartados liquidados del mes con los abonos que tienen. Si algún día hace falta exacto, la
  app tendría que exponer esa información.
