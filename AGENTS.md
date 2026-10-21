# AGENTS.md · Contexto del proyecto

Este archivo es el **contexto de trabajo** de la automatización: qué es el negocio, qué reglas
se aplican, cómo se habla con la app y qué no se debe tocar. Está pensado para que lo lea
cualquiera que vaya a tocar el proyecto (persona o herramienta) antes de proponer nada: sin este
contexto se inventan conceptos, se recalculan cifras que ya calcula la app y se meten
credenciales en los flujos.

---

## 1. Qué es este proyecto

**Zapatería Paso Firme**: una tienda de barrio con una sola dependienta y su dueña, Marisa. El
servicio estrella es el **sistema de apartados**: el cliente elige unos zapatos, deja un abono
inicial y los va pagando poco a poco hasta llevárselos.

- La **app de la tienda** (`backend/`, `frontend/`) ya existe: sustituye a la libreta. **No se
  modifica**. Su documentación está en [`docs/guia-de-la-app.md`](docs/guia-de-la-app.md).
- Este repositorio contiene la **capa de automatización con n8n**: los flujos (`workflows/`), sus
  specs (`specs/`), los datos de prueba (`tests/`) y la documentación.

## 2. Reglas del negocio (no las inventes)

| Regla | Detalle |
|---|---|
| Abono inicial | Mínimo **5 €** |
| Plazo | Máximo **3 meses (90 días)** desde la fecha del apartado |
| Abonos | Los que se quieran, de cualquier importe, sin superar lo que falta |
| Liquidación | Cuando lo que falta llega a 0 €, el apartado queda `liquidado` y el cliente puede recoger |
| Vencimiento | Pasados los 90 días sin liquidar, el apartado queda `vencido`: los zapatos vuelven a la venta y lo abonado se convierte en **vale de compra** (no se devuelve en efectivo) |
| Un apartado = un par | Un producto (modelo + talla) por apartado |
| Formas de pago | `efectivo`, `tarjeta`, `bizum` |

Cifras que necesita Marisa:

- **Ventas del día** = ventas directas + abonos cobrados ese día (los abonos iniciales también cuentan).
- **Recaudación mensual** = todo lo cobrado en el mes, separando ventas directas y abonos.
- **Total pendiente de cobro** = suma de lo que falta en todos los apartados activos.

## 3. Servicios y direcciones

| Servicio | Desde el host | Desde dentro de n8n |
|---|---|---|
| App de la tienda | `http://localhost:8000` | `http://tienda:8000` |
| API de la tienda | `http://localhost:8000/api/...` | `http://tienda:8000/api/...` |
| n8n | `http://localhost:5678` | `http://n8n:5678` |

> ⚠️ **La trampa del `localhost`**: dentro de n8n, `localhost` es el propio n8n. Usa siempre
> `http://tienda:8000` en los nodos HTTP Request y `http://n8n:5678` en el `.env` de la tienda.

**La API de la tienda exige la cabecera `X-API-Key`** (el valor de `API_KEY` del `.env`). En n8n se
gestiona con una credencial **Header Auth** con Name `X-API-Key`. Nunca escribas la clave en el
JSON del flujo.

## 4. Cómo habla la app con n8n

- La app manda `POST` a `http://n8n:5678/webhook/tienda` con `{"evento": "...", "datos": {...}}`.
- En n8n el cuerpo llega en **`$json.body`**, no en `$json`.
- Eventos: `apartado.creado`, `abono.registrado`, `venta.registrada`, `apartado.vencido`.
- El estado va en `datos.estado` y es el estado **después** de la acción.
- **El aviso se manda una sola vez, sin reintentos.** Los flujos programados (cierre, recordatorios)
  **no dependen del webhook**: consultan la API.

## 5. La regla de oro de este proyecto

> **Las cifras las calcula la app. n8n las lee, las copia y las suma. El modelo redacta el texto,
> nunca calcula dinero.**

- `abonado` y `pendiente` **nunca** se recalculan en n8n: se copian de la API.
- En los mensajes, el importe va tal cual lo devuelve la API.
- Lo único que el flujo puede hacer con las cifras es **sumarlas** (cierre diario, informe
  mensual, total pendiente).
- Un modelo **no** recibe cifras para que las interprete: recibe el texto ya compuesto, o
  solo el texto del correo en el flujo 3.

## 6. Convenciones de este repo

### Ramas (Git Flow)

```
main        producción (solo release/ y hotfix/)
develop     integración
feature/*   una automatización o documento por rama
release/*   preparación de entrega
hotfix/*    arreglo urgente (nace de main)
```

- Una automatización = una rama = una PR.
- Commits: `tipo(scope): descripción` → `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.
- El JSON exportado del flujo se sube **en el mismo commit** que lo cambia.

### Nombres

| Qué | Patrón | Ejemplo |
|---|---|---|
| Flujo (en n8n) | `NN · Nombre legible` | `03 · Abonos a distancia` |
| Archivo de flujo | `workflows/NN-nombre.json` | `workflows/03-abonos-distancia.json` |
| Spec | `specs/NN-nombre.md` | `specs/03-abonos-distancia.md` |
| Rama | `feature/flujo-NN-nombre-corto` | `feature/flujo-03-abonos-distancia` |
| Test | `tests/flujo-NN/` | `tests/flujo-03/casos.json` |

### Nodos

- Nombres de nodo en español y legibles: `Webhook eventos`, `Switch evento`, `Preparar recibo`.
- Expresiones `{{ ... }}` siempre en español en los textos, y **con `toFixed(2)`** para los euros.
- Comentarios `//` en el código de los nodos Code explicando el porqué, no el qué.

## 7. Importar y exportar flujos

```bash
# Exportar (desde n8n: ⋮ → Download o la CLI dentro del contenedor)
docker compose exec n8n n8n export:workflow --id=<id> --output=/tmp/flujo.json

# Importar
docker cp flujo.json <contenedor>:/tmp/flujo.json
docker compose exec n8n n8n import:workflow --input=/tmp/flujo.json
```

- El JSON que vive en `workflows/` es **el exportado por n8n**, no escrito a mano: así siempre
  corresponde a un flujo que n8n puede abrir.
- Un flujo con `Execute Workflow` **no se puede probar en isolation** sin sus subflujos importados
  y publicados. Importa primero los subflujos.
- Los flujos con webhook necesitan estar **publicados** (Publish) para que funcione la
  *Production URL* (`/webhook/tienda`), que es la que usa la app.

## 8. Credenciales y variables

**Nunca** escribas credenciales ni valores secretos en el JSON de un flujo, en los textos de los
mensajes ni en los logs. Las credenciales viven en n8n:

| Credencial | Tipo | Para qué |
|---|---|---|
| `Tienda - API` | Header Auth (`X-API-Key`) | Llamar a la API de la tienda |
| `Gmail - Paso Firme` | Gmail OAuth2 | Enviar correos |
| `Banco - IMAP` | IMAP | Leer los avisos del banco |
| `Telegram - Paso Firme` | Telegram API | Avisos a Marisa y a clientes |
| `Modelo - Groq` | OpenAI compatible | Extraer datos del correo (flujo 3) |
| `Histórico - Sheets` | Google Sheets | Histórico de cierres y avisos |

**Configuración** (`data/config.csv`), que los flujos leen en cada ejecución:

| Variable | Por defecto | Para qué |
|---|---|---|
| `UMBRAL_VENTA_GRANDE` | `200` | Aviso de venta grande (HU-09) |
| `EMAIL_MARISA` | `marisa@pasofirme.example` | A quién se avisa a la tienda |
| `DIAS_AVISO_VENCIMIENTO` | `7,1` | Cuántos días antes se avisa (HU-06) |

> La configuración está en [`data/config.csv`](data/config.csv), **no** en los flujos: se cambia
> editando el fichero, sin tocar el JSON ni republicar nada. No se usan las variables de n8n
> (`$vars`) porque en la edición comunitaria no existen, ni `$env`, porque n8n 2.x lo bloquea en
> las expresiones.

## 9. Qué **no** se debe hacer

1. **No** modificar `backend/` ni `frontend/`: la app es de la plataforma.
2. **No** escribir claves, tokens ni contraseñas en ningún fichero.
3. **No** activar flujos en producción sin que lo revise una persona.
4. **No** recalcular `abonado` ni `pendiente` en n8n.
5. **No** enviar datos personales a un modelo externo que no sean imprescindibles (en el flujo 3
   solo va el texto del correo).
6. **No** borrar datos ni borrar flujos que no hayas creado tú.
7. **No** cambiar el contrato de la API (URL, cabeceras, nombres de campos) sin actualizar la spec.

## 9 bis. n8n 2.x: las trampas que ya nos han mordido

Este proyecto se ha probado con **n8n 2.44**. Estas son las cosas que fallan en silencio:

| Trampa | Qué pasa | Cómo se hace bien |
|---|---|---|
| Nodo HTTP Request con credencial | Si faltan `authentication: "genericCredentialType"` **y** `genericAuthType: "httpHeaderAuth"`, la petición sale **sin la cabecera** y la API responde `401` sin avisar | Poner los dos parámetros |
| `localhost` dentro de n8n | Es el propio n8n, no la tienda | `http://tienda:8000` |
| Peticiones HTTP encadenadas | La segunda se lanza **una vez por item** de la primera, con expresiones que ya no valen | Meter un nodo Code que devuelva **un** item antes de cada petición |
| Nodo Code con `runOnceForAllItems` | Recibe todos los items de una vez, pero devuelve un solo item | Si necesitas un item por fila, usa `runOnceForEachItem` o `return` un array |
| Leer un fichero | En n8n 2.x el binario se guarda en disco: el nodo Code **no** puede leerlo | Nodo *Spreadsheet File* para CSV, o `$getWorkflowStaticData('global')` para recordar cosas entre ejecuciones |
| Escribir un fichero | `writeBinaryFile` resuelve la ruta contra el almacén de n8n y falla con `EACCES` | Usa los *static data* del flujo (la memoria de n8n entre ejecuciones) |
| Ficheros fuera de `~/.n8n-files` | `Access to the file is not allowed` | `N8N_RESTRICT_FILE_ACCESS_TO` en el `docker-compose.yml` |
| Un nodo con dos ramas | Solo hay una salida: las dos ramas van en `main[0]` | `{"main": [[{"node": "A"}, {"node": "B"}]]}` |
| Referencia a un nodo que no se ha ejecutado | `An expression references this node, but the node is unexecuted` | `$(('X').isExecuted ? ... : ...)` |
| `typeVersion` inventado | El nodo no hace lo que se espera o no se importa | Mirar el nodo real: `dist/nodes/<Nodo>/<Nodo>.node.js` en el contenedor |
| Un `If` con la salida puesta al revés | Se ejecuta la rama contraria | Revisar `connections`: la salida 0 es *true* y la 1 es *false* |
| Publicar un flujo que llama a otro | `Cannot publish workflow: ... references workflow ... which is not published` | Publicar primero los subflujos |
| Un webhook con `Respond to Webhook` | Si un flujo tiene nodos *Respond to Webhook*, **todos** sus webhooks tienen que usar `responseMode: responseNode` | Si no: `Unused Respond to Webhook node found in the workflow` |
| La URL de un webhook | Los webhooks normales viven en `/webhook/<ruta>` | `http://localhost:5678/webhook/tienda` |
| Un `If` con dos salidas y un nodo de respuesta | La rama que no lleva el nodo de respuesta se queda colgada | Un nodo *Respond to Webhook* por rama |
| Un nodo Code que devuelve una lista | Devuelve **un item por elemento** si el nodo siguiente es HTTP | Si no, hace una sola petición |
| Buscar por teléfono | La búsqueda `q` de la app es un `LIKE`: `600000001` no está en `600 000 001` | Pedir todos los apartados y filtrar por dígitos en un nodo Code |
| El trigger de formulario de n8n 2.6 | No se deja publicar si el flujo tiene otra cosa mal | Se sustituyó por un webhook GET que sirve el formulario y otro POST que lo recibe |
| La query de un webhook | Los nodos HTTP **sustituyen** el item, así que la query se pierde | Léela del nodo que la guardó (`$('Preparar').first().json.query`) |
| El trigger de Telegram de n8n 2.44 | No se activa: la tarea de activación falla y el flujo queda a medias | Se sustituyó por un webhook normal con `authentication: headerAuth` y el token en la cabecera `X-Telegram-Bot-Api-Secret-Token` (que es lo que manda Telegram) |
| La URL base de un modelo de lenguaje | En n8n 2.x **no** se pone en el nodo: sale de la credencial (`url`) | `Modelo - Groq` → `url: https://api.groq.com/openai/v1` |
| El parámetro `model` del nodo de modelo | Es un *resource locator*, no una cadena | `{"__rl": true, "mode": "list", "value": "qwen/qwen3.8-27b"}` |
| El nodo de Telegram | Su `operation` es `sendMessage`, no `send` | Con `send` la URL sale incompleta y Telegram devuelve 404 |
| Un proxy que intercepta el TLS | n8n (que usa axios) no se fía y falla con `self-signed certificate in certificate chain` | `NODE_TLS_REJECT_UNAUTHORIZED=0` (solo desarrollo) o `NODE_EXTRA_CA_CERTS` |
| Las credenciales por tipo | Hay dos `httpHeaderAuth` (la de la API y la del token del bot) y el tipo no basta | El enlazador mira el nodo **y** el tipo |
| `const` usado antes de declararse | En el nodo Code da `Cannot access 'x' before initialization` | Decláralo al principio del código |

## 10. Cómo se trabaja: Spec-Driven Development

1. **Primero la spec** (`specs/`): disparador, entradas, salidas, casos de error y criterios de
   aceptación, apoyada en la ontología (`specs/00-ontologia.md`).
2. **Después el flujo**, con la spec al lado. Si el flujo hace algo que no está en la spec, se
   actualiza la spec (o se cambia el flujo).
3. **Después el test** (`tests/flujo-NN/`): datos de entrada y resultado esperado.
4. **Revisión humana**: se importa, se ejecuta con los datos de prueba y se revisa en la PR.
5. **Si una prueba falla, se arregla el flujo, no se cambia la prueba.**

## 11. Comandos útiles

```bash
docker compose up -d --build          # levantar app + n8n
docker compose logs -f tienda         # ver los avisos que envía la app
docker compose ps                     # estado

# API de la tienda
curl "http://localhost:8000/api/apartados?estado=activo" -H "X-API-Key: $API_KEY"

# Validar que los JSON de workflows/ son JSON válidos y tienen lo mínimo
python scripts/validar_flujos.py
```

## 12. Resumen en una línea

> La tienda apunta con los datos; n8n avisa, recuerda, cierra caja e informa; el modelo solo extrae
> datos y redacta; **las cifras y las reglas son de la app**.
