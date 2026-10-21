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
| 00 · Despachador de eventos | ✅ | Recibe los 4 eventos, reparte y **rechaza sin token** (401) |
| 01 · Confirmación de apartado | ✅ | 3 comprobaciones OK |
| 02 · Recibo de abono | ✅ | 3 comprobaciones OK |
| 03 · Abonos a distancia | ✅ | 13 comprobaciones OK (los 9 correos) |
| 04 · Aviso de venta grande | ✅ | 2 comprobaciones OK, con el umbral configurable |
| 05 · Cierre diario | ✅ | Cierre con desglose por forma de pago |
| 06 · Recordatorios y vencimientos | ✅ | Recordatorios (7 y 1 día), vencimientos, vales y redacción con IA |
| 07 · Informe mensual | ✅ | Recaudación, pendiente y apartados del mes |
| 08 · Avisos de error | ✅ | Avisa con flujo, paso y error, y limpia las claves |
| 10 · Migración del Excel | ✅ | 7 apartados migrados, 2 dudosos y no duplica al repetir |
| 11 · Apartados desde casa | ✅ | 7 comprobaciones OK (solicitud, aviso y confirmación) |
| 13 · Ventas del datáfono | ✅ | 3 comprobaciones OK (importa y no duplica) |
| 14 · Asistente de Telegram | ✅ | Cliente pide el teléfono y recibe su saldo; la tienda recibe las cifras |
| 90 · Datos de demo | ✅ | Crea datos de ejemplo por API |

**Nivel entregado: 🟢 Esencial + 🟡 Medio + 🟠 Avanzado** (14 historias de usuario). Las
comprobaciones automáticas son 40 (24 de los flujos de siempre + 7 del flujo 11 + 3 del 13 + 6 del
asistente, que se prueban con un webhook que simula el mensaje de Telegram).

## Lo que aprendimos en el nivel avanzado

- **Proteger el webhook obliga a tocar la app, y la app es de la plataforma.** La solución ha
  sido poner el token en la URL (`?token=...`), que es lo único que la app puede cambiar sin
  tocar su código. El token se compara en el primer nodo del despachador y, si no coincide, se
  responde 401 sin ejecutar nada.
- **Un bot que "reconoce" a un cliente sin guardar datos personales nuevos**: el chat se apunta a
  un teléfono la primera vez y a partir de ahí solo se le enseñan los apartados de ese teléfono,
  comparando los dígitos. Dos clientes parecidos no se ven entre sí.
- **Que el modelo redacte, pero no decida, se puede comprobar.** En los dos sitios donde entra un
  modelo (el bot y los recordatorios) hay un nodo que compara las cifras de su respuesta con
  las que salieron de la API y, si no coinciden, usa el texto original. Así el tono es del modelo
  y las cifras son de la tienda.
- **El nodo de formulario de n8n 2.6 dio más guerra que el bot entero**: al final se sustituyó
  por dos webhooks (uno que sirve el formulario y otro que lo recibe), que además se pueden
  probar con un `curl`.
- **La configuración fuera de n8n era la única opción**: en la edición comunitaria no hay
  variables y `$env` está bloqueado. Un `config.csv` montado en el contenedor lo resuelve y no
  necesita licencia ni credenciales.

## Lo que queda fuera

- 🔴 El panel para Marisa (HU-15) y el despliegue en la nube con HTTPS, copias de seguridad
  automáticas de n8n y CI completa (HU-16). La CI de validación de JSON sí está.
- La API de la tienda no expone un histórico de estados: el informe mensual aproxima los
  apartados liquidados del mes con los abonos que tienen. Si algún día hace falta exacto, la
  app tendría que exponer esa información.
- La app no tiene campo de consentimiento: el criterio es "solo se escribe a quien ha dejado
  una dirección de correo" (ver [`docs/rgpd.md`](rgpd.md)).
