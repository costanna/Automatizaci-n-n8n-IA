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
- [Los flujos](#-los-flujos)
- [Importarlos y probarlos](#-importarlos-y-probarlos)
- [Cómo se trabaja en este repo (Git Flow)](#-cómo-se-trabaja-en-este-repo-git-flow)
- [Estructura del proyecto](#-estructura-del-proyecto)
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
         │  GET/POST /api/...  (X-API-Key)            │  Gmail / SMTP / Telegram
         └──────────────────────────────────────────────┘
```

- **App → n8n**: la app manda un `POST` a `http://n8n:5678/webhook/tienda` cada vez que se crea
  un apartado, se abona, se vende algo o se vence un apartado. El cuerpo siempre es
  `{"evento": "...", "datos": {...}}`.
- **n8n → App**: n8n usa la API REST de la tienda (`http://tienda:8000/api/...`) con la cabecera
  `X-API-Key`. **Las reglas del negocio las aplica la app**: n8n no recalcula `pendiente` ni
  `abonado`, los lee.

> **La regla de oro**: *las cifras las calcula la app; n8n las lee y las copia. El modelo redacta el
> texto, nunca calcula dinero.*

Detalle completo en [`docs/guia-de-la-app.md`](docs/guia-de-la-app.md) y en la
[ontología del dominio](specs/00-ontologia.md).

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

## ⚙️ Los flujos

| # | Flujo | Disparador | Qué hace | Historia |
|---|---|---|---|---|
| 00 | `00 · Despachador de eventos` | Webhook `POST /tienda` | Reparte los 4 eventos de la app con un nodo **Switch** | — |
| 01 | `01 · Confirmación de apartado` | Evento `apartado.creado` | Manda al cliente qué ha apartado, cuánto falta y hasta cuándo | HU-01 |
| 02 | `02 · Recibo de abono` | Evento `abono.registrado` | Manda el recibo y avisa si el apartado queda liquidado | HU-02 |
| 03 | `03 · Abonos a distancia` | Correo del banco (IMAP) | Extrae el pago con un modelo de lenguaje, busca el apartado por API y registra el abono | HU-03 |
| 04 | `04 · Aviso de venta grande` | Evento `venta.registrada` | Avisa a Marisa de las ventas por encima del umbral | HU-09 |
| 05 | `05 · Cierre diario` | Programado (23:00) | Cierra la caja: ventas, abonos y total por forma de pago | HU-04 |
| 06 | `06 · Recordatorios y vencimientos` | Programado (08:30) | Recuerda los vencimientos, vence los fuera de plazo y avisa del vale | HU-06, HU-07 |
| 07 | `07 · Informe mensual` | Programado (día 1, 09:00) | Recaudación del mes, pendiente de cobro y apartados del mes | HU-08 |
| 08 | `08 · Avisos de error` | Error Trigger | Avisa del flujo, el paso y el error (sin claves) | HU-05 |
| 10 | `10 · Migración del Excel` | Manual | Migra el Excel antiguo, limpia los datos e informa de los dudosos | HU-10 |
| 11 | `11 · Apartados desde casa` | Webhook | El cliente pide apartar unos zapatos; la tienda confirma cuando llega el abono | HU-13 |
| 13 | `13 · Ventas del datáfono` | Programado (02:00) | Importa el CSV de cobros con tarjeta como ventas, sin duplicar | HU-13 |
| 14 | `14 · Asistente de Telegram` | Telegram | El cliente pregunta cuánto le falta; la tienda pregunta por las cifras | HU-11, HU-12 |
| 15 | `15 · Panel de Marisa` | Webhook | Una pantalla con las cifras y los apartados que vencen | HU-15 |
| 90 | `90 · Datos de demo` | Manual | Crea datos de ejemplo por API para la demo | — |

Y tres **subflujos** reutilizables:

| Subflujo | Para qué |
|---|---|
| `SUB · Notificar` | Envía el mensaje por el canal que le pidan (correo o Telegram) y dice si ha salido |
| `SUB · Buscar apartado` | Busca a qué apartado pertenece un pago remoto |
| `SUB · Avisar vale` | Avisa al cliente del vale y a la tienda de los zapatos que vuelven a la venta |
| `SUB · Tool saldo del cliente` | La herramienta del bot: los apartados de un cliente, por teléfono |
| `SUB · Tool cifras de la tienda` | La herramienta del bot: la recaudación y lo pendiente de cobro |

Las specs de cada uno (qué hace, casos de error y criterios de aceptación) están en
[`specs/`](specs/).

---

## 🔧 Importarlos y probarlos

```bash
# Importa los 14 flujos en n8n y los enlaza (ids de subflujos y de credenciales)
python scripts/enlazar_flujos.py

# Comprueba que los JSON son válidos y que no hay credenciales dentro
python scripts/validar_flujos.py

# Para ver los correos que se envían, sin configurar un SMTP de verdad
python scripts/smtp_desarrollo.py

# La batería de pruebas, contra la tienda de verdad
python scripts/probar_flujos.py
```

Las instrucciones paso a paso (credenciales, publicar los flujos, errores frecuentes) están en
[`docs/como-importar-flujos.md`](docs/como-importar-flujos.md).

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
│   ├── correos/             # Los 9 correos de prueba del flujo 3
│   └── envios/              # Correos que ha enviado el SMTP de desarrollo
├── docs/                    # Documentación del proyecto
│   ├── guia-de-la-app.md        # Cómo funciona la app, la API y el webhook
│   ├── mapa-proceso.md          # El proceso de apartado, antes y después
│   ├── kanban.md                # Tablero con las historias de usuario
│   ├── credenciales.md          # Credenciales y variables que necesita cada flujo
│   ├── como-importar-flujos.md  # Cómo importarlos, configurarlos y probarlos
│   ├── bitacora.md              # Bitácora técnica: decisiones, modelos y fallos corregidos
│   └── retrospectiva.md         # Retrospectiva del equipo
├── workflows/               # Flujos de n8n exportados en JSON (versionados)
├── specs/                   # Specs (SDD) de cada automatización + ontología del dominio
├── scripts/                 # Utilidades (importar y enlazar, validar, SMTP, pruebas)
├── tests/                   # Datos de prueba y resultados esperados de cada flujo
├── .github/workflows/        # CI que valida los JSON de los flujos en cada PR
├── AGENTS.md                # Contexto del proyecto: reglas, convenciones y trampas de n8n
├── docker-compose.yml
└── .env.example
```

---

## 🔑 Credenciales y variables

En n8n, las claves se guardan en **Credentials** (nunca en el JSON del flujo) y los valores de
configuración, en **Variables**. La lista completa está en
[`docs/credenciales.md`](docs/credenciales.md).

| Variable | Por defecto | Para qué |
|---|---|---|
| `EMAIL_MARISA` | `marisa@pasofirme.example` | A quién se avisa a la tienda |
| `UMBRAL_VENTA_GRANDE` | `200` | Aviso de venta grande (HU-09) |
| `DIAS_AVISO_VENCIMIENTO` | `7,1` | Cuántos días antes se avisa del vencimiento (HU-06) |

---

## 📚 Documentación

| Documento | Para qué |
|---|---|
| [`docs/guia-de-la-app.md`](docs/guia-de-la-app.md) | Cómo funciona la app, la API y el webhook |
| [`docs/mapa-proceso.md`](docs/mapa-proceso.md) | El proceso de apartado: hoy y automatizado (con diagrama) |
| [`docs/kanban.md`](docs/kanban.md) | Tablero con las historias de usuario y quién hace cada una |
| [`docs/credenciales.md`](docs/credenciales.md) | Credenciales y variables que necesita cada flujo |
| [`docs/como-importar-flujos.md`](docs/como-importar-flujos.md) | Cómo importarlos, configurarlos y probarlos |
| [`docs/bitacora.md`](docs/bitacora.md) | Bitácora técnica: decisiones, modelos y fallos corregidos |
| [`docs/retrospectiva.md`](docs/retrospectiva.md) | Retrospectiva del equipo |
| [`docs/despliegue.md`](docs/despliegue.md) | Despliegue en la nube con HTTPS y copias de seguridad |
| [`AGENTS.md`](AGENTS.md) | Contexto del proyecto: reglas del negocio y trampas de n8n |
| [`specs/`](specs/) | Specs de cada automatización y ontología del dominio |
