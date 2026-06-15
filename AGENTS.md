# AGENTS.md — Link Seguro (Detector de Phishing para DMs de Instagram)

## Inicio rápido

```bash
cd src
.venv/bin/python database/init_db.py              # crear tablas
.venv/bin/python scripts/setup_usuarios.py          # crear usuarios (idempotente)
.venv/bin/uvicorn app.main:app --reload --port 8000 # servidor dev
```

Todos los comandos se ejecutan desde `src/`. El virtual env está en `src/.venv`.

## Comandos clave

| Comando | Propósito |
|---------|-----------|
| `.venv/bin/pytest -v` | Ejecutar tests |
| `.venv/bin/python scripts/import_conversations.py --dir data/conversations/<dir>` | Importar JSONs históricos |
| `.venv/bin/python scripts/update_blacklist.py` | Actualizar CSV de PhishTank |
| `.venv/bin/python export_conversations.py --token ... --ig-user-id ...` | Exportar desde Graph API |

## Arquitectura

- **Entrypoint**: `app/main.py` — FastAPI con dos routers y mount de `src/static/` en `/static` (logo, assets estáticos).
- **Webhook** (`app/webhook/router.py`): `GET /webhook` (verificación Meta), `POST /webhook` (recepción de mensajes). Usa `BackgroundTasks` — siempre responde 200 en menos de 200ms. Tras `save_message()`, agenda `update_username_if_missing()` en background para resolver el username de Instagram via Graph API.
- **Dashboard** (`app/dashboard/router.py`): HTML via **Jinja2 templates** (`src/templates/base.html`, `login.html`, `dashboard.html`). Estilizado con **Tailwind CDN** + Inter + JetBrains Mono. Paleta de colores clara extraída de `chamba.css`. Logo en `/static/logo.png` aparece en login y header. Autenticación con bcrypt + cookies firmadas con itsdangerous (8h de expiración). Los usuarios `es_admin=1` ven `[contenido protegido]` en lugar del texto de los mensajes en el timeline. En vista admin, la columna "Usuario" muestra `↳ @cuenta` indicando a qué cuenta monitoreada pertenece cada conversación.
- **Pipeline de análisis** (`app/analysis/orchestrator.py`): Análisis de URLs + texto en paralelo con `asyncio.gather`. Si el score de URL > 0.3, consulta URLhaus API async. Luego llama a UM Cloud AI (cliente compatible con OpenAI) para clasificar.
- **Base de datos**: SQLite en `src/data/phishing_detector.db`. Sin ORM — SQL directo con `aiosqlite`. Schema en `database/schema.sql`. `update_username_if_missing()` resuelve usernames de IG vía Graph API con timeout 3s, falla silenciosamente.

## Detalles importantes

- **Trabajar dentro de `src/`**: Todos los imports asumen `src/` como raíz. Siempre hacer `cd src` primero.
- **`.env`**: Debe estar en `src/.env`, lo carga `pydantic-settings` en `app/config.py`.
- **Dos stubs viejos**: `app/utils.py` y `app/models.py` son obsoletos. Usar `app/utils/logger.py` y `app/models/schemas.py` en su lugar.
- **Supabase descartado** (decisión del tutor 2026-05-08). Las claves existen en `.env.example` como comentarios pero son código muerto.
- **Verificación HMAC** (`app/webhook/validator.py`) está implementada pero NO conectada al router. Hay que agregarla explícitamente si se necesita.
- **UM Cloud AI**: Requiere `UM_API_KEY` en `.env`. Usa endpoint `https://ai.cloud.um.edu.ar/api/v1`, modelo `gemma4-26b`. Falla silenciosamente si no está configurada.
- **ID de conversación**: Usa `sha256(sorted([sender, recipient])[:16])`. Fue corregido — ahora los IDs son bidireccionales.
- **Usuarios del dashboard**: `admin/admin123` (ve todo), `flia_test/link2024`, `benja/link2024`, `hernesto/link2024`. El badge de ADMIN solo se muestra si `es_admin=1`. Los admin ven `[contenido protegido]` en el timeline de mensajes (privacidad de contenido).
- **Assets estáticos**: `src/static/` servido en `/static`. El logo oficial está en `src/static/logo.png`.
- **Blacklist de PhishTank** en `data/blacklist/phishtank.csv`, con fallback a `data/blacklist.txt`. Ejecutar `python scripts/update_blacklist.py` para actualizar.

## Tests

- Framework: pytest + pytest-asyncio.
- Dataset de prueba: `tests/dataset_evaluacion.json` (8 casos de phishing).
- No existen tests unitarios para módulos específicos — solo el JSON de dataset y `__init__.py`.
- No hay configuración de cobertura, lint (ruff) ni typecheck (mypy) en el repo.

## Estado conocido (de notas de sesión)

- ~2440+ mensajes, 16+ conversaciones en SQLite.
- Las importaciones históricas tienen un problema conocido: los mensajes anteriores a la corrección del ID bidireccional pueden estar divididos en varias filas.
- El `SESSION_SECRET` por defecto es `link_seguro_secret_2024` — cambiarlo antes de producción.
- El usuario hernesto tiene 0 DMs (aún no hay tráfico de webhook hacia ese ID).
