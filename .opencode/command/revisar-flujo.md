---
description: Revisa un flujo de n8n antes de subirlo (seguridad, reglas y cifras)
agent: opencode
---

Revisa un flujo de `workflows/` como si fueras el revisor de la Pull Request: busca los fallos
que ya nos han mordido y los que todavía no hemos visto.

**Pasos**:

1. Lee el flujo (`workflows/*.json`) y su spec (`specs/`). Si no hay spec, dilo: el flujo va
   primero por el papel.
2. Comprueba, en este orden:
   - **Cifras**: ¿el flujo recalcula `abonado` o `pendiente`? Tiene que copiarlos de la API.
     ¿Hay sumas que no son de la API?
   - **Credenciales**: ¿hay alguna clave escrita dentro del JSON, en los mensajes o en los logs?
     ¿El `X-API-Key` va por la credencial *Header Auth* (con `authentication` y `genericAuthType`)?
   - **Reglas del negocio**: abono mínimo 5 €, plazo 90 días, no abonar de más, no abonar fuera
     de plazo, `liquidado` y `vencido` son finales.
   - **n8n 2.x**: peticiones HTTP encadenadas (falta un nodo Code que devuelva un item),
     referencias a nodos que pueden no haberse ejecutado (`isExecuted`), ficheros (usa
     *Spreadsheet File* o *static data*), `typeVersion` y formato de `connections`.
   - **Errores**: ¿qué pasa si la API devuelve 401 o 422? ¿El flujo avisa a la tienda?
   - **Privacidad**: ¿se manda a un modelo externo más datos de los necesarios? ¿Se avisa a
     alguien que no ha dado su consentimiento?
3. Devuelve una lista de hallazgos, cada uno con: **severidad** (bloqueante / importante / menor),
   **nodo**, **qué pasa** y **cómo se arregla**. Si no hay nada, dilo.
4. No modifiques nada: esto es una revisión.

Al final, resume en 3 líneas: cuántos bloqueantes, cuántos importantes y si el flujo se puede
publicar tal como está.
