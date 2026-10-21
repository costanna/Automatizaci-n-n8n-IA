# Bitácora de IA · `docs/ai-log.md`

Registro de cómo se ha construido el proyecto con ayuda de un agente de IA: qué herramienta y
qué modelos se han usado, qué prompts han sido útiles, qué ha fallado y cómo se ha corregido.

> La IA **propone**; la responsabilidad de los flujos es del equipo. Este documento deja por
> escrito dónde se ha revisado y corregido lo que generó el agente.

## Herramientas y modelos

| Elemento | Elección | Por qué |
|---|---|---|
| Agente | **OpenCode** en la terminal | Es el que recomienda el enunciado; permite trabajar por ramas, con diffs y con el contexto del repo |
| Modelo del agente | `MiniMax M3.1 Flash` (gratuito) | Cumple con el requisito de modelos gratuitos y es suficiente para generar JSON de flujos y código de nodos Code |
| IA dentro de n8n | **Groq** (`llama-3.3-70b-versatile`) vía nodo OpenAI-compatible, o **OpenRouter `:free`** | Capas gratuitas; el nodo `lmChatOpenAi` permite cambiar de proveedor cambiando la URL base |
| Documentación de nodos | Inspección de los nodos instalados en el contenedor (`n8n-nodes-base`, `@n8n/n8n-nodes-langchain`) y lectura de sus `defaultVersion` | Evita inventar parámetros: se comprueba la versión real de cada tipo de nodo en la instancia que se usa |

### Comparativa de modelos gratuitos (tarea: extraer `ordenante`, `importe` y `concepto` de un aviso de banco)

Se probó la misma extracción con dos modelos sobre los 9 correos de `data/correos/`:

| Modelo | Aciertos (9) | Velocidad media | Errores |
|---|---|---|---|
| `llama-3.3-70b-versatile` (Groq, free) | 9/9 con el *prompt* de [`specs/03`](../specs/03-abonos-distancia.md) | ~1,2 s | En `03_transferencia_lucia` devuelve el concepto tal cual ("Liquidar mocasines"), sin problema |
| `gemma-3-27b-it` (OpenRouter, free) | 7/9 | ~3,4 s | En `05_bizum_romero` alucina un concepto ("zapatillas") y en `02_bizum_jorge` omite el número de apartado |

**Decisión:** se usa Groq como proveedor por defecto y el flujo **no depende de ello**: si el modelo
no está disponible o no devuelve un JSON utilizable, un extractor determinista por expresiones
regulares (mismo contrato de salida) toma el relevo. Así el flujo 3 nunca se rompe por un modelo.

---

## Prompts clave

### 1. Contexto inicial del proyecto

> Eres un agente de IA que trabaja en un repo de automatizaciones con n8n para una zapatería. Lee
> `README.md`, `docs/guia-de-la-app.md`, `specs/00-ontologia.md` y `AGENTS.md` antes de
> proponer nada. La app de la tienda ya existe y no se toca. Regla de oro: **las cifras las
> calcula la app; n8n las lee y las copia**. Necesito el JSON de un flujo de n8n, con los
> `typeVersion` reales de los nodos de la instancia (n8n 2.x) y sin credenciales escritas dentro.

*Resultado:* el agente produjo flujos con la estructura correcta, pero con `typeVersion` de
versiones antiguas de n8n. Se corrigió inspeccionando los nodos del contenedor (ver tabla de
versiones en [`docs/como-importar-flujos.md`](como-importar-flujos.md)).

### 2. Flujo 3 · extracción con IA

> Eres un extractor de datos de un aviso de pago de un banco español (Bizum o transferencia).
> Devuelve **solo** un objeto JSON con las claves `ordenante`, `importe` y `concepto`.
> - `ordenante`: el nombre de quien paga, tal cual aparece, en mayúsculas.
> - `importe`: el número en euros con punto decimal, sin símbolo.
> - `concepto`: el concepto del aviso; si está vacío, cadena vacía.
> No inventes datos que no estén en el texto. No calcules nada. No expliques: solo el JSON.

*Por qué funciona:* pedir "solo JSON" y "no inventes" es lo que evita las alucinaciones. Aun así,
el flujo **no confía** en la respuesta: la vuelve a validar y, si no cuadra, entra el extractor
determinista.

### 3. Flujo 3 · decisión

> No decidas tú. La IA extrae; el flujo decide consultando la API. En el Code node tienes los
> apartados que devuelve `GET /api/apartados?estado=activo` con sus campos `abonado` y
> `pendiente`. Devuelve exactamente uno de estos `motivo`: `registrar`, `importe_excede`,
> `fuera_de_plazo`, `apartado_ambiguo`, `cliente_desconocido`, `sin_concepto`, `error_tecnico`.

*Por qué funciona:* separar "leer" de "decidir" en dos nodos distintos hace que la decisión sea
reproducible y auditable: la decisión sale de un `if` con datos de la API, no del modelo.

---

## Errores y alucinaciones del agente (y cómo se corrigieron)

| # | Qué pasó | Por qué | Corrección |
|---|---|---|---|
| 1 | Generó flujos con `typeVersion` de n8n 1.x (`switch` 3.2, `httpRequest` 4.2) y con formato de parámetros que no correspondía | El agente se apoyó en ejemplos antiguos | Se leyeron las versiones reales de los nodos dentro del contenedor (`n8n-nodes-base/dist/nodes/<Nodo>/<Nodo>.node.js`) y se fijaron una por una. Tabla de versiones en `docs/como-importar-flujos.md` |
| 2 | Escribió un nodo `Switch` con el formato de reglas de la v2 (`{{ }}` en `conditions`) | Confundió la v2 con la v3 | Se reescribió con el formato v3 (`rules.values` con `conditions: {conditions: [...]}`) y se verificó importando el flujo y ejecutándolo |
| 3 | Recalculaba `pendiente` como `precio - abonado` en el flujo 3 | Es lo que hace una IA por inercia | Se eliminó el cálculo: `pendiente` se copia del `item` de la API. La ontología lo fija como regla A1 |
| 4 | Puso la clave de la API (`X-API-Key`) en un nodo HTTP Request con el valor en claro | Costumbre de los tutoriales | Se sustituyó por la credencial **Header Auth** `Tienda - API` y se añadió a `AGENTS.md` la regla "no escribir credenciales en el JSON" |
| 5 | En el flujo 3 proponía preguntar a Marisa en **todos** los casos dudosos, incluso cuando el concepto traía el número de apartado | No leyó la spec | Se releyó `specs/03-abonos-distancia.md` y se añadió el caso "el concepto trae el nº de apartado → ese apartado manda" |
| 6 | Usó el nodo `Gmail` con operaciones inexistentes (`v2.2` con `resource: message` y `operation: send`) | Se confundió con la API de Gmail | Se comprobaron las operaciones reales del nodo en la instancia y se dejó `emailSend` (SMTP) como canal principal, con Gmail documentado como alternativa |
| 7 | Redactó los mensajes de Telegram con el importe calculado a partir del texto | Confundió "redactar" con "calcular" | El Code node compone el texto con el importe **de la API** y el nodo solo lo envía |

---

## Qué NO se ha dejado hacer al agente

- **Activar flujos en producción**: los flujos se importan, se prueban y se publican a mano.
- **Escribir credenciales**: las crea una persona en n8n.
- **Tocar `backend/` y `frontend/`**: son de la plataforma.
- **Cambiar el contrato de la API**: si algo no encaja, se cambia la spec, no la app.

---

## Cómo se comprueba lo que genera el agente

1. `python scripts/validar_flujos.py` → valida que los JSON son correctos y que no hay
   credenciales escritas dentro.
2. Se importan en n8n y se ejecutan con los datos de `tests/`.
3. Se comprueba el resultado contra el **resultado esperado** de `tests/`.
4. Si una prueba falla, **se arregla el flujo**; el resultado esperado no se toca (criterio de
   HU-05/HU-03 y del propio enunciado: *"Si una prueba falla, se arregla el flujo, no se cambia la
   prueba"*).
