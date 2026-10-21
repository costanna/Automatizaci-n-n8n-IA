# Bitácora técnica · `docs/bitacora.md`

Decisiones técnicas del proyecto y registro de los fallos encontrados al construir y probar los
flujos. Se escribe porque las decisiones no se ven en el código y los errores conviene
recordarlos: volver a tropezar con ellos cuesta media hora cada vez.

## 1. El modelo de lenguaje: solo en un sitio

De las diez automatizaciones, **una** usa un modelo de lenguaje: el flujo `03 · Abonos a distancia`,
que tiene que leer el aviso del banco y sacar tres datos (ordenante, importe y concepto) de un
texto libre.

| Pieza | Decisión |
|---|---|
| Modelo | `llama-3.3-70b-versatile` (Groq, capa gratuita), con `gpt-4o-mini` de OpenRouter como alternativa |
| Proveedor | Groq, mediante el nodo *OpenAI Chat Model* de n8n, que habla con cualquier API compatible con OpenAI |
| URL base | `https://api.groq.com/openai/v1` (se cambia en el propio nodo) |
| Modelo | `llama-3.3-70b-versatile` (se cambia en el propio nodo) |
| Temperatura | `0`: queremos extracción, no redacción |

**Por qué el modelo solo extrae y no decide.** El texto del aviso es corto y su forma es conocida
(«Importe:», «Ordenante:», «Concepto:»), pero los nombres vienen escritos como los escribe el
cliente («CARMEN RUIZ GARCIA» frente a «Carmen Ruiz») y los importes mezclan formatos («89.90» y
«1.842,30»). Un modelo de lenguaje resuelve esas dos cosas bien; decidir a qué apartado pertenece
un pago es otra historia: depende del estado real del apartado en la app, y eso lo sabe la API,
no el modelo. Por eso el flujo se reparte en dos:

```
Correo -> Normalizar -> ¿es un pago? -> Extraer (modelo) -> Interpretar -> Buscar apartado (API)
                                                                    -> Decidir (reglas) -> Registrar
```

**El flujo no depende del modelo.** Si la credencial no está, o el proveedor falla, o la
respuesta no es un JSON utilizable, entra un extractor por expresiones regulares con el mismo
contrato de salida (`ordenante`, `importe`, `concepto`) y el flujo sigue. La salida del extractor
lleva `origen: "modelo"` o `origen: "regex"`, así que se puede ver en la ejecución cuál de los dos
ha acted.

### Comparativa de los dos modelos gratuitos probados

Misma tarea (extraer los tres datos de los 9 correos de `data/correos/`), mismo *prompt*:

| Modelo | Aciertos (9) | Velocidad media | Errores |
|---|---|---|---|
| `llama-3.3-70b-versatile` (Groq, free) | 9/9 | ~1,2 s | Ninguno con el *prompt* de `specs/03` |
| `gemma-3-27b-it` (OpenRouter, free) | 7/9 | ~3,4 s | En `05_bizum_romero` se inventa un concepto; en `02_bizum_jorge` omite el número de apartado |

Se queda Groq por defecto, pero el extractor de respaldo hace que la elección no sea crítica.

### El *prompt* del flujo

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

Pedir «solo JSON» y «no inventes» es lo que evita que el modelo se invente un concepto cuando el
aviso no lo trae. Aun así, la respuesta se vuelve a validar: si no cuadra, entra el extractor por
expresiones regulares.

### Lo que se le manda al modelo y lo que no

Al modelo solo se le manda **el texto del correo** (asunto + cuerpo, sin el pie del banco). No se
le mandan datos de clientes, ni de apartados, ni claves. Es la regla `A7` de la ontología, y la
razón es práctica: si el aviso trae un nombre y un importe, no hace falta nada más.

## 2. Fallos encontrados al construir y probar los flujos

Todos se encontraron probando contra la app, no leyendo el código. La columna de cómo se
detectó dice qué mirar la próxima vez.

| # | Qué pasaba | Por qué | Cómo se detectó | Arreglo |
|---|---|---|---|---|
| 1 | Las peticiones a la API de la tienda salían **sin la cabecera** y la app respondía `401` | En n8n 2.x el nodo *HTTP Request* necesita `authentication: "genericCredentialType"` **y** `genericAuthType: "httpHeaderAuth"`; con la credencial puesta pero sin los dos parámetros, la petición sale sin autenticar | El flujo «funcionaba» y no hacía nada: el `401` se ve solo en los datos de la ejecución | Añadir los dos parámetros en todos los nodos HTTP con credencial |
| 2 | La segunda petición HTTP de una cadena se lanzaba **una vez por item** de la primera, con expresiones ya caducadas | El nodo HTTP procesa todos los items que le llegan | El flujo de cierre pedía las ventas con la fecha vacía | Un nodo Code que devuelve **un** item antes de cada petición |
| 3 | El flujo de cierre y el de informe no llegaban a calcular nada | Consecuencia del anterior | El correo de cierre salía con importes a cero | Lo mismo |
| 4 | La migración del Excel no cargaba **ninguna** fila | Los CSV usan **coma** como separador, no punto y coma, y los importes mezclan `89.90` (formato inglés) y `1.842,30` (formato español) | El informe decía «0 apartados cargados» | Separador correcto y regla de miles/ decimales según el último separador |
| 5 | El correo `05_bizum_romero` (apellido e inicial, sin concepto) se registraba en vez de preguntar a Marisa | La expresión regular del concepto usaba `\s*`, que **salta de línea**: leía la línea siguiente («El importe ya está disponible…») como si fuera el concepto | La prueba comparada con la tabla del enunciado | `[ \t]*` en vez de `\s*` en las expresiones del extractor |
| 6 | Marisa recibía un aviso de «no he registrado nada» justo después de registrar el abono | Las dos salidas del nodo `If` estaban conectadas al revés | Los correos de la prueba | La salida 0 es *true* y la 1 es *false* |
| 7 | La migración se ejecutaba dos veces y no cargaba nada la segunda | Se comparaba contra un fichero de histórico que, en n8n 2.x, se guarda en disco y el nodo Code no puede leer | El informe decía «0 cargados» en la segunda vez | Comparar contra **la propia app**: si ya existe un apartado con el mismo cliente, producto y fecha, no se crea |
| 8 | El historial de recordatorios enviados no se podía leer (y se repetían los avisos) | Igual que el anterior: el binario en disco | Se veían dos correos seguidos al mismo cliente | Los *static data* del flujo (`$getWorkflowStaticData`): la memoria de n8n entre ejecuciones |
| 9 | El aviso de error decía «Error desconocido» | El nodo *Error Trigger* mete el error dentro de `execution.error`, no en `error` | El correo de la prueba | Leer de `execution.error` |
| 10 | El nodo de escribir ficheros fallaba con `EACCES` | `writeBinaryFile` resuelve la ruta contra el almacén de n8n, no contra una ruta libre | El error en la ejecución | Históricos en los *static data* del flujo |
| 11 | Los ficheros del CSV no se podían leer | n8n 2.x restringe la lectura a `~/.n8n-files` | «Access to the file is not allowed» | `N8N_RESTRICT_FILE_ACCESS_TO` en el `docker-compose.yml` y el nodo *Spreadsheet File* para el CSV |
| 12 | Los nodos de la rama de éxito y de error del flujo 3 salían cruzados | Al añadir el nodo de comprobación se olvidó una conexión | El aviso a Marisa salía en el caso bueno | Revisar `connections` nodo a nodo |
| 13 | Ni `$vars` ni `$env` sirven para configurar un flujo | En la edición comunitaria de n8n las variables no existen (`feat:variables` es de pago) y n8n 2.x bloquea `$env` en las expresiones (`access to env vars denied`) | El umbral de la venta grande no se podía cambiar | La configuración va en `data/config.csv`, que los flujos leen en cada ejecución |
| 14 | El CSV de configuración no se leía | `DIAS_AVISO_VENCIMIENTO,"7,1"` sin comillas rompe el CSV, y un fichero guardado con BOM añade un carácter invisible al nombre de la primera clave | El umbral salía siempre con el valor por defecto | Comillas en los valores con coma y guardar el fichero **sin BOM** |

La lista completa de trampas de n8n 2.x está en [`AGENTS.md`](../AGENTS.md), que es donde se
quedan para que no haya que volver a descubrirlas.

## 3. Cómo se comprueba

```bash
python scripts/validar_flujos.py     # los JSON son válidos y no hay claves dentro
python scripts/probar_flujos.py      # los flujos contra la tienda de verdad
```

La batería de pruebas cubre los flujos 1, 2, 3 y 4 (24 comprobaciones, incluidos los 9 correos
del enunciado). Los flujos 5, 6, 7, 8 y 10 se han ejecutado a mano contra la app; las capturas
están en [`docs/evidencias/`](evidencias/).

**Si una prueba falla, se arregla el flujo, no la prueba.**
