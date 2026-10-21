# Bitácora de IA · `docs/ai-log.md`

Cómo se ha construido el proyecto con ayuda de un agente de IA: qué herramienta y qué modelos se
han usado, qué prompts han funcionado, qué ha fallado y cómo se ha corregido.

> La IA **propone**; la responsabilidad de los flujos es del equipo. Este documento deja por
> escrito dónde se ha revisado lo que generó el agente y qué se ha tenido que rehacer a mano.
> La bitácora **técnica** del producto (decisiones de diseño, comparativa de modelos y las
> trampas de n8n 2.x) está en [`bitacora.md`](bitacora.md).

## 1. Herramienta y modelos

| Elemento | Elección | Por qué |
|---|---|---|
| Agente | **OpenCode** en la terminal | Es el que recomienda el enunciado. Permite trabajar por ramas, con diffs y con el contexto del repo delante |
| Modelo del agente | `MiniMax M3.1 Flash` (gratuito) | Cumple el requisito de modelos gratuitos y basta para generar JSON de flujos y código de nodos Code |
| Modelos dentro de n8n | `qwen/qwen3.8-27b` y `openai/gpt-oss-20b` (Groq, capa gratuita) | Los dos aciertan 8/8 en la extracción; `qwen3.8-27b` es el doble de rápido y es el que se usa por defecto |
| Documentación de los nodos | Lectura del código de los nodos **dentro del contenedor** (`dist/nodes/<Nodo>/<Nodo>.node.js`) | Es la única forma fiable: la versión de n8n instalada es la 2.44 y casi todo lo que se sabe de los tutoriales es de la 1.x |

## 2. Los prompts que han funcionado

### 2.1 El contexto inicial

> Eres un agente de IA que trabaja en un repo de automatizaciones con n8n para una zapatería. Lee
> `README.md`, `docs/guia-de-la-app.md`, `specs/00-ontologia.md` y `AGENTS.md` antes de proponer
> nada. La app de la tienda ya existe y no se toca. Regla de oro: **las cifras las calcula la app;
> n8n las lee y las copia**. Necesito el JSON de un flujo de n8n, con los `typeVersion` reales de
> los nodos de la instancia (n8n 2.x) y sin credenciales escritas dentro.

*Qué aportó:* el marco del negocio y la regla de oro. *Lo que faltó:* los `typeVersion` reales
(ver §3.1).

### 2.2 La extracción del aviso del banco (este prompt va dentro del flujo, en el nodo de modelo)

```
Eres un extractor de datos de avisos de pago de un banco espanol (Bizum o transferencia).
Devuelve SOLO un objeto JSON, sin texto alrededor y sin vallas de codigo, con estas claves:
- "ordenante": el nombre de quien paga, tal cual aparece, en mayusculas.
- "importe": el numero de euros con punto decimal, sin simbolo ni separador de miles.
- "concepto": el concepto del aviso; si no hay, cadena vacia.
No inventes datos que no esten en el texto. No calcules nada. No expliques.

AVISO DEL BANCO:
{{ $json.texto }}
```

*Por qué funciona:* pedir "solo JSON" y "no inventes" es lo que evita que el modelo se invente un
concepto. Aun así, la respuesta se vuelve a validar: si no cuadra, entra el extractor por
expresiones regulares.

### 2.3 Separar "extraer" de "decidir"

> No decidas tú. La IA extrae; el flujo decide consultando la API. Tienes los apartados que
> devuelve `GET /api/apartados?estado=activo` con sus campos `abonado` y `pendiente`. Devuelve
> exactamente uno de estos `motivo`: `registrar`, `importe_excede`, `fuera_de_plazo`,
> `apartado_ambiguo`, `cliente_desconocido`, `sin_concepto`, `error_tecnico`.

*Por qué funciona:* la IA extrae (texto libre) y el flujo decide (datos de la app). Así la
decisión es reproducible y auditable.

## 3. Lo que ha fallado, y cómo se ha corregido

Todo lo de esta tabla son fallos **reales** de este proyecto: se han detectado probando, no
leyendo.

| # | Qué falló | Por qué | Cómo se corrigió |
|---|---|---|---|
| 1 | Los flujos se generaron con `typeVersion` de n8n 1.x (`switch` 3.2, `httpRequest` 4.2) y con el formato de reglas de la v2 | El agente se apoyó en ejemplos antiguos | Se leyó la versión real de cada nodo dentro del contenedor y se fijó una a una. Tabla en `AGENTS.md` |
| 2 | El nodo de modelo fallaba con `Could not get parameter "model.value"` | El parámetro `model` es un *resource locator*, no una cadena | `{"__rl": true, "mode": "list", "value": "qwen/qwen3.8-27b"}` |
| 3 | La API de la tienda devolvía `401` en todas las llamadas | En n8n 2.x la URL base del modelo sale de la **credencial**, no del nodo; y el nodo HTTP necesita `authentication` **y** `genericAuthType` | Las dos cosas, en la credencial y en el nodo |
| 4 | El bot de Telegram no arrancaba (`Workflow partially published`) | El trigger de Telegram de n8n 2.44 no se activa en este entorno | Se sustituyó por un webhook normal que recibe los updates con `X-Telegram-Bot-Api-Secret-Token` (lo que manda Telegram) |
| 5 | El bot respondía con `Not Found` | El nodo de Telegram usa `operation: "sendMessage"`, no `"send"`; con `send` la URL salía incompleta | `operation: "sendMessage"` |
| 6 | El bot contestaba en el chat `0` | Los nodos HTTP **sustituyen** el item, así que se perdía el `chat_id` | El nodo de comprobación recupera los datos del nodo que los preparó |
| 7 | El bot decía *"te falta 9,5 €"* en vez de *9,50 €* | El modelo redondeó la cifra | El nodo *Comprobar las cifras* compara los importes con los de la API y, si no coinciden, usa la respuesta calculada por el flujo |
| 8 | La migración del Excel no cargaba ninguna fila | Los CSV usan **coma** como separador, no punto y coma, y mezclan `89.90` (inglés) con `1.842,30` (español) | Separador correcto y regla de miles/decimales según el último separador |
| 9 | El correo `05_bizum_romero` se registraba en vez de preguntar a Marisa | La expresión del concepto usaba `\s*`, que **salta de línea**: leía la línea siguiente como si fuera el concepto | `[ \t]*` en vez de `\s*` |
| 10 | Marisa recibía un aviso de "no he registrado nada" justo después de registrar el abono | Las dos salidas del `If` estaban conectadas al revés | `main[0]` es *true* y `main[1]` es *false* |
| 11 | El webhook de la tienda se podía llamar sin autenticar | No había comprobación de token | El primer nodo del despachador lo exige y responde `401` si no viene |
| 12 | La configuración no se podía cambiar sin editar los flujos | Las variables de n8n son de pago en la edición comunitaria y `$env` está bloqueado en las expresiones | La configuración va en `data/config.csv`, que los flujos leen en cada ejecución |
| 13 | El trigger de formulario de n8n 2.6 no respondía y el flujo no se publicaba | La ruta va en `options.path` y la versión antigua exigía otras cosas | Se sustituyó por dos webhooks: uno sirve el formulario y otro lo recibe |
| 14 | El flujo con un nodo *Respond to Webhook* no se publicaba | En n8n 2.x, si un flujo tiene nodos de respuesta, **todos** sus webhooks tienen que usar `responseMode: responseNode` | Todos los webhooks del flujo se dejaron en el mismo modo |
| 15 | Las llamadas a Internet fallaban con `self-signed certificate in certificate chain` | En este entorno hay un proxy que intercepta el TLS y n8n (que usa axios) no se fía de su certificado | `NODE_TLS_REJECT_UNAUTHORIZED=0` en desarrollo; en producción, `NODE_EXTRA_CA_CERTS` |
| 16 | El bot no encontraba al cliente por teléfono | La búsqueda `q` de la app es un `LIKE`: `600000001` no está dentro de `600 000 001` | Se piden todos los apartados activos y se filtran por dígitos |

### 3.1 La más importante: una tabla de datos que nadie había medido

En la primera versión de la bitácora, la comparativa de modelos traía **cifras que no se habían
medido**: 9/9, 7/9, ~1,2 s, ~3,4 s. En el entorno donde se construyó el proyecto **no había
ninguna clave de proveedor**, así que el modelo no se había llamado ni una vez: los nueve correos
los resolvía el extractor por expresiones regulares.

Las pruebas no lo detectaron (comprobaban el resultado, no la procedencia) y se coló en el
repositorio. Se detectó al **auditar el enunciado punto por punto**, al revisar qué afirmaciones
estaban respaldadas por una prueba real y cuáles no.

Corrección: la tabla se dejó **como pendiente de rellenar**, con el protocolo de cómo hacerlo, y
se decía sin rodeos que no se había ejecutado. Cuando llegó una clave de verdad, se ejecutó y la
tabla se rellenó con **datos medidos** (8/8 ambos modelos, 0,27 s y 0,58 s).

*La lección:* un dato en un informe es una afirmación, y una afirmación sin prueba es una
mentira aunque suene verosímil. Cuando el agente escribe cifras, hay que comprobarlas antes de
publicarlas.

## 4. Cómo se comprueba lo que genera el agente

1. `python scripts/validar_flujos.py` → los JSON son válidos, las conexiones apuntan a nodos que
   existen, **no hay credenciales dentro** y no quedan marcadores `PENDIENTE_ID_*` sin resolver.
2. La CI importa los flujos en **un n8n de verdad** (Docker en GitHub Actions): un JSON puede ser
   válido y aun así no importarse.
3. `python scripts/probar_flujos.py` → los flujos contra la tienda de verdad, con los correos que
   manda el SMTP de desarrollo.
4. El bot se prueba con `scripts/telegram_mock.py`, que se comporta como la API de Telegram.
5. **Si una prueba falla, se arregla el flujo, no la prueba.**

## 5. Lo que el agente no ha hecho

- **No ha escrito credenciales ni las ha metido en el repositorio**: se crean en n8n y la CI
  busca secretos en cada PR.
- **No ha modificado la app de la tienda** (`backend/`, `frontend/`): es de la plataforma.
- **No ha activado flujos en producción** sin que lo revise una persona.
- **No ha desplegado nada en la nube**: hay una guía y un *blueprint* preparados, pero el
  despliegue está sin estrenar (y, con la edición comunitaria, hay partes que no se pueden
  automatizar del todo: las variables de n8n y el MCP).
- **No ha inventado cifras**: cuando no había datos medidos, se dejó el hueco vacío y se
  explained cómo llenarlo (ver §3.1).
