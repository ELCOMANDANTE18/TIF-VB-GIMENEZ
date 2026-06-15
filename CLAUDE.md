# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> A more detailed companion document exists at `AGENTS.md` (root). Keep both in sync when changing workflow or architecture facts.

## Project

**Link Seguro** — phishing detector for Instagram DMs. A FastAPI service receives Meta webhook events, runs a multi-stage analysis pipeline (URL + text heuristics + generative-AI classification), persists everything to SQLite, and exposes a web dashboard for reviewing conversations and risk.

## Working directory

**All commands run from `src/`.** Every import assumes `src/` is the project root. The virtualenv lives at `src/.venv` — there is no system-wide install, so invoke tools as `.venv/bin/<tool>` (or activate it first). The `.env` must live at `src/.env`; `pydantic-settings` loads it in `app/config.py` and the app **fails to boot** if the required Meta keys are missing.

## Commands

```bash
cd src
.venv/bin/python database/init_db.py                 # create SQLite tables (schema.sql)
.venv/bin/python scripts/setup_usuarios.py           # seed dashboard users (idempotent)
.venv/bin/uvicorn app.main:app --reload --port 8000  # dev server
ngrok http 8000                                      # public tunnel for Meta webhook

.venv/bin/pytest -v                                  # run tests
.venv/bin/pytest tests/test_file.py::test_name       # run a single test
.venv/bin/python scripts/import_conversations.py --dir data/conversations/<dir>  # import historical JSONs
.venv/bin/python scripts/update_blacklist.py         # refresh PhishTank CSV
```

Health/inspection endpoints: `/health`, `/docs`, ngrok inspector at `http://127.0.0.1:4040`.

No lint (ruff), typecheck (mypy), or coverage tooling is configured. Tests use pytest + pytest-asyncio; there are no per-module unit tests yet — only `tests/dataset_evaluacion.json` (8 labeled phishing cases) for end-to-end evaluation.

## Architecture

**Entrypoint** `app/main.py` mounts two routers plus `/health`. Also mounts `src/static/` at `/static` (logo, assets) via `StaticFiles` — the directory is optional so the app boots even if it doesn't exist.

**Webhook** (`app/webhook/router.py`, prefix `/webhook`):
- `GET /webhook` — Meta verification handshake (`hub.challenge`/`hub.verify_token`).
- `POST /webhook` — parses `entry[].messaging[]`, skips echoes/empty text, saves the message, then **schedules analysis via `BackgroundTasks`**. It always returns `{"status":"ok"}` immediately; the heavy analysis runs after the response so Meta never times out. After `save_message()`, also schedules `update_username_if_missing()` in background to resolve the sender's Instagram username via Graph API.
- HMAC signature verification (`app/webhook/validator.py::verify_signature`) is implemented but **NOT wired into the router** — add it explicitly if needed.

**Analysis pipeline** (`app/analysis/orchestrator.py::PhishingOrchestrator.analyze`):
1. Loads prior conversation state (`get_conversation_info`).
2. Runs `URLAnalyzer` and `TextAnalyzer` concurrently via `asyncio.gather` + `asyncio.to_thread` (they are sync).
3. If `url_result.score > 0.3` and URLs were found, queries the **URLhaus** API async; a confirmed-online hit bumps the URL score to ~1.0.
4. Combines into a heuristic score: `url*URL_WEIGHT + text*TEXT_WEIGHT` (0.6/0.4), mapped to LOW/MEDIUM/HIGH via `RISK_THRESHOLD_*` (0.4/0.7).
5. Calls **UM Cloud AI** (`app/ai/groq_client.py`) with the current message + history for richer classification (MITRE technique, Cialdini principles, scam category, lifecycle stage, recommended action, user/analyst explanations). The AI severity is converted back to the heuristic scale and combined with `max(...)` so a confident "LOW" doesn't inflate the score; AI can only *raise* the risk level.
6. Persists the result (`save_analysis_result`) and triggers `conversation_observer.observe` for holistic, conversation-level analysis.
- The AI step is wrapped in try/except and **fails silently** (logs a warning) if `UM_API_KEY` is unset or the call errors.

**AI client** (`app/ai/groq_client.py` + `app/ai/prompts.py`): despite the `groq` filename, it talks to **UM Cloud** via the OpenAI-compatible SDK (`UM_BASE_URL=https://ai.cloud.um.edu.ar/api/v1`, `UM_MODEL=gemma4-26b`).

**Persistence** (`app/db/sqlite_client.py`): SQLite at `src/data/phishing_detector.db`, **no ORM** — raw SQL via `aiosqlite`. Schema in `database/schema.sql`.
- **Conversation ID** = `sha256` of the sorted `[sender, recipient]` pair (truncated to 16 chars), making IDs bidirectional. Messages imported before this fix may be split across rows.
- `update_username_if_missing(id_conversacion, participante_id, token)`: called as a background task after each webhook message. Queries `GET graph.instagram.com/v25.0/{id}?fields=username,name` with 3s timeout; updates `participante_username` in the DB if empty. Fails silently — returns `...{id[-8:]}` fallback on any error.
- `app/db/supabase_client.py` and the Supabase env keys are **dead code** — Supabase was dropped by tutor decision (2026-05-08). Use SQLite only.

**Dashboard** (`app/dashboard/router.py`, `app/dashboard/auth.py`): HTML rendered via **Jinja2 templates** (`src/templates/` — `base.html`, `login.html`, `dashboard.html`). Styled with **Tailwind CDN** + Inter + JetBrains Mono fonts; color palette from `chamba.css` (light theme: `#ECEAE3` background, white cards, `#1B1D1C` ink, sage `#6E8F73`, danger `#C2554B`, butter `#B59628`). Logo PNG served from `/static/logo.png` appears in the login card and the header. `router.py` contains only DB helpers + routes (~420 lines); presentation logic lives in the templates.
- Auth uses bcrypt password hashes + `itsdangerous`-signed cookies (8h expiry). Seeded users: `admin/admin123` (sees everything, `es_admin=1` shows the ADMIN badge), plus `flia_test`, `benja`, `hernesto` (all `link2024`). Change `SESSION_SECRET` (default `link_seguro_secret_2024`) before any real deployment.
- **Admin message privacy**: when `es_admin=1`, the message timeline in the detail panel shows `[contenido protegido — solo visible para el operador]` instead of the actual text. Regular users see the full content.
- **Admin owner column**: in the "Usuario" cell, admin users see a secondary line `↳ @cuenta` identifying which monitored account each conversation belongs to. Requires a JOIN with `usuario_sistema` via `cuenta_monitoreada`.
- **Automatic DM template** (`app/notifications/messenger.py::_build_alert_message`): sends a structured warning with the attack category, safety advice, and "Link Seguro · Mensaje automático" footer.

## Gotchas

- **Obsolete stubs:** `app/utils.py` and `app/models.py` are dead. Use `app/utils/logger.py` and `app/models/schemas.py` (the package versions).
- **Blacklist:** PhishTank data at `data/blacklist/phishtank.csv`, with fallback to `data/blacklist.txt`.
- Config weights/thresholds (`URL_WEIGHT`, `TEXT_WEIGHT`, `RISK_THRESHOLD_*`) live in `app/config.py::Settings` and can be overridden via `.env`.
