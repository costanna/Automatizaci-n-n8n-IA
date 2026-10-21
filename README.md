# 👟 Automatizaciones con n8n · Zapatería Paso Firme

Proyecto de automatizaciones para **Paso Firme**, una zapatería de barrio con un sistema de
apartados (apartar zapatos pagando poco a poco). La tienda ya tiene una app propia
(`backend/` + `frontend/`) que sustituye a la libreta de los apartados; este repositorio contiene
la capa de **automatización con n8n** que hay alrededor: avisos a clientes, control de vencimientos,
cierres de caja, informes y la lectura automática de los avisos del banco.

> Este repositorio es **nuestro**: el código de la app viene de la plataforma y a partir de aquí
> todo lo que hay es trabajo del equipo.

## 📌 Índice

- [Arquitectura](#-arquitectura)
- [Puesta en marcha](#-puesta-en-marcha)
- [Cómo se trabaja en este repo (Git Flow)](#-cómo-se-trabaja-en-este-repo-git-flow)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Flujos de n8n](#-flujos-de-n8n)
- [Credenciales y variables](#-credenciales-y-variables)
- [Documentación](#-documentación)

---

## 🏗️ Arquitectura

```
  ┌──────────────┐   POST /webhook/tienda   ┌────────────────────┐
  │  App tienda  │ ────────────────────────▶ │        n8n         │
  │  (FastAPI)   │                          │  (flujos y subflujos)│
  └──────┬───────┘                          └─────────┬──────────┘
         │                                              │
         │  GET/POST /api/...  (X-API-Key)            │  Gmail / Telegram
         └──────────────────────────────────────────────┘
```

- **App → n8n**: la app manda un `POST` a `http://n8n:5678/webhook/tienda` cada vez que se crea
  un apartado, se abona, se vende algo o se vence un apartado. El cuerpo siempre es
  `{"evento": "...", "datos": {...}}`.
- **n8n → App**: n8n usa la API REST de la tienda (`http://tienda:8000/api/...`) con la cabecera
  `X-API-Key`. **Las reglas del negocio las aplica la app**: n8n no recalcula `pendiente` ni
  `abonado`, los lee.

Detalle completo en [`docs/guia-de-la-app.md`](docs/guia-de-la-app.md).

---

## 🚀 Puesta en marcha

Requisitos: [Docker](https://docs.docker.com/get-docker/) y Docker Desktop abierto.

```bash
cp .env.example .env
# edita API_KEY en .env con una clave vuestra
docker compose up -d
```

| Servicio | URL | Para qué |
|---|---|---|
| App de la tienda | http://localhost:8000 | Registrar apartados, abonos y ventas |
| Documentación de la API | http://localhost:8000/docs | Probar los endpoints (Swagger) |
| n8n | http://localhost:5678 | Construir y ejecutar los flujos |

La primera vez, la app se llena sola con datos de ejemplo (24 apartados y ~250 ventas, con fechas
relativas a hoy) para poder probar: hay apartados que vencen en 7 días, en 1 día y otros ya fuera
de plazo. Para empezar de cero: `SEED=0` en el `.env`.

Para parar: `docker compose down`. Para borrar también los datos: `docker compose down -v`.

---

## 🌿 Cómo se trabaja en este repo (Git Flow)

| Rama | Para qué | Se mergea en |
|---|---|---|
| `main` | Lo que está **en producción**. Siempre estable. | — |
| `develop` | Integración. Aquí vive lo que se está construyendo. | `main` (vía `release/`) |
| `feature/<nombre>` | Una automatización o documento. Nace de `develop`. | `develop` |
| `release/<version>` | Preparación de una entrega. Nace de `develop`. | `main` y `develop` |
| `hotfix/<nombre>` | Arreglo urgente en producción. Nace de `main`. | `main` y `develop` |

Reglas del equipo:

1. **Una automatización = una rama = una PR.** No se mezcla trabajo de dos flujos en la misma rama.
2. **Rama corta y viva**: si tarda más de un día, se parte en tareas más pequeñas.
3. **Commits pequeños y con mensaje**: `tipo(scope): descripción` (`feat`, `fix`, `docs`, `test`, `chore`, `refactor`).
4. **El JSON de los flujos va versionado**: cada flujo se exporta a `workflows/` y se sube en el
   mismo commit que lo cambia.
5. **Nunca se suben credenciales**: las claves viven en n8n y en el `.env`, nunca en el JSON ni en
   el repositorio.
6. **`main` solo se toca por `release/` o `hotfix/`**, nunca con un merge directo desde `develop`.

Convenciones de nombres:

- Flujos: `NN · Nombre legible` (p. ej. `03 · Abonos a distancia`).
- Archivos de flujo: `workflows/NN-nombre-del-flujo.json`.
- Specs: `specs/NN-nombre-del-flujo.md`.
- Ramas: `feature/flujo-NN-nombre-corto`, `feature/docs-nombre-corto`, `hotfix/descripcion-corta`.

```bash
# flujo nuevo
git switch develop
git switch -c feature/flujo-03-abonos-distancia
# ... trabajo ...
git add . && git commit -m "feat(flujo-03): extrae el pago del correo y registra el abono"
git push -u origin feature/flujo-03-abonos-distancia
# PR -> develop
```

---

## 📁 Estructura del proyecto

```
.
├── backend/                 # App de la tienda (FastAPI + SQLite) — viene de la plataforma
├── frontend/                # Pantallas de la tienda
├── data/                    # Datos de partida: Excel de Marisa y avisos del banco
│   ├── excel_actual_apartados.csv
│   ├── excel_actual_ventas.csv
│   └── correos/             # Los 9 correos de prueba del flujo 3
├── docs/                    # Documentación del proyecto
├── workflows/               # Flujos de n8n exportados en JSON (versionados)
├── specs/                   # Specs (SDD) de cada automatización + ontología del dominio
├── scripts/                 # Utilidades (datos de demo, validación de flujos)
├── tests/                   # Datos de prueba y resultados esperados de cada flujo
├── AGENTS.md                # Contexto que se le da al agente de IA
├── docker-compose.yml
└── .env.example
```

---

## ⚙️ Flujos de n8n

Los flujos están exportados en `workflows/` y se importan desde n8n
(*Workflows → Import from File*). Las instrucciones paso a paso están en
[`docs/como-importar-flujos.md`](docs/como-importar-flujos.md).

---

## 🔑 Credenciales y variables

En n8n, las claves se guardan en **Credentials** (nunca en el JSON del flujo). La lista completa
está en [`docs/credenciales.md`](docs/credenciales.md).

---

## 📚 Documentación

| Documento | Para qué |
|---|---|
| [`docs/guia-de-la-app.md`](docs/guia-de-la-app.md) | Cómo funciona la app, la API y el webhook |
| [`docs/mapa-proceso.md`](docs/mapa-proceso.md) | Mapa del proceso de apartado: hoy vs. automatizado |
| [`docs/credenciales.md`](docs/credenciales.md) | Credenciales y variables que necesita cada flujo |
| [`docs/kanban.md`](docs/kanban.md) | Tablero con las historias de usuario |
| [`docs/ai-log.md`](docs/ai-log.md) | Bitácora de IA: prompts, errores y correcciones |
| [`docs/retrospectiva.md`](docs/retrospectiva.md) | Retrospectiva del equipo |
| [`AGENTS.md`](AGENTS.md) | Contexto y reglas para el agente de IA |
| [`specs/`](specs/) | Specs de cada automatización y ontología del dominio |
