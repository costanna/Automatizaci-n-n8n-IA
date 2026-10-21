---
description: Genera la spec (SDD) de una automatización a partir de su idea
agent: opencode
---

Genera la especificación de una automatización nueva para la zapatería Paso Firme, siguiendo el
plantón de `specs/README.md` y las reglas de `AGENTS.md`.

**Pide antes de empezar** (si no está en el mensaje):

1. Qué hace la automatización y qué dispara.
2. Quién recibe el resultado (cliente, tienda o las dos) y por qué canal.

**Pasos**:

1. Lee `AGENTS.md` (reglas del negocio y trampas de n8n 2.x) y `specs/00-ontologia.md`
   (vocabulario). No inventes entidades: usa las que hay.
2. Escribe la spec en `specs/NN-nombre.md` con esta estructura:
   - **Objetivo**, **Disparador**, **Entradas** (con un ejemplo real de payload),
     **Salidas** (tabla tipo → condición → contenido), **Pasos** (con el nodo de n8n de cada uno),
     **Reglas** (citando las de la ontología), **Casos de error** (tabla),
     **Criterios de aceptación** (los de la historia de usuario, en check-list),
     **Datos de prueba** y **Credenciales**.
3. Comprueba que los criterios de aceptación son verificables: cada uno tiene un "cómo se
   comprueba" (un endpoint, un correo, una línea del log).
4. Si la automatización va a tocar la API de la tienda, apunta a
   `docs/guia-de-la-app.md` y **no cambies el contrato de la API**: si hace falta un dato nuevo,
   dilo en la spec en lugar de inventarlo.
5. Al final, escribe un resumen de 5 líneas: qué has especificado, qué dudas quedan y qué
   flujos de `workflows/` habría que tocar.

**No hagas**:

- Escribir el JSON del flujo (eso es otro paso).
- Poner credenciales ni valores secretos.
- Salirte de la ontología del dominio.
