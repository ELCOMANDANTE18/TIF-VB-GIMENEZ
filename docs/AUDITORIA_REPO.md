# Auditoría del Repositorio — Link Seguro

**Fecha de auditoría:** 2026-06-14  
**Versión analizada:** ~v0.5.0 (branch `main`, commit `c512253`)  
**Alcance:** Solo lectura. Ningún archivo fue modificado.

---

## PARTE 1 — Estructura del repositorio

### 1.1 Archivos Python (`src/**/*.py`)

```
src/app/ai/__init__.py
src/app/ai/groq_client.py
src/app/ai/prompts.py
src/app/analysis/__init__.py
src/app/analysis/conversation_observer.py
src/app/analysis/orchestrator.py
src/app/analysis/text_analyzer.py
src/app/analysis/url_analyzer.py
src/app/config.py
src/app/dashboard/__init__.py
src/app/dashboard/auth.py
src/app/dashboard/router.py
src/app/db/__init__.py
src/app/db/sqlite_client.py
src/app/db/supabase_client.py          ← dead code (ver Parte 2)
src/app/__init__.py
src/app/main.py
src/app/models/__init__.py
src/app/models/schemas.py
src/app/notifications/__init__.py
src/app/notifications/email_notifier.py
src/app/notifications/messenger.py
src/app/utils/__init__.py
src/app/utils/logger.py
src/app/webhook/__init__.py
src/app/webhook/router.py
src/app/webhook/validator.py
src/database/init_db.py
src/export_conversations.py            ← fuera de lugar (ver Parte 2)
src/scripts/backup_db.py
src/scripts/evaluar_dataset.py
src/scripts/import_conversations.py
src/scripts/migrate_conv_ids.py
src/scripts/reset_analisis.py
src/scripts/restore_db.py
src/scripts/setup_usuarios.py
src/scripts/test_email.py
src/scripts/update_blacklist.py
src/tests/__init__.py
```

**Total: 39 archivos Python** (sin `__pycache__` ni `.venv`)

### 1.2 Archivos de documentación / datos / configuración

```
AGENTS.md                              ← .gitignored
CLAUDE.md                              ← .gitignored
DEMO_TUTOR.md                          ← .gitignored
ESTADO_PROYECTO.txt                    ← .gitignored
ESTADO_SESION.md                       ← untracked (no está en .gitignore)
README.md
RETOMAR.md                             ← .gitignored
docs/arquitectura.md                   ← duplicado (ver nota)
docs/integracion-meta.md               ← duplicado
docs/tecnologias.md                    ← duplicado
research/algo.txt
src/.env-example
src/algo.txt
src/data/backups/backup_20260605_183518.json
src/data/conversations/*.json          ← .gitignored (datos reales)
src/database/schema.sql
src/docs/arquitectura.md
src/docs/BASE_DE_DATOS.md
src/docs/base-de-datos.md             ← duplicado (mismo contenido, distinto nombre)
src/docs/DECISIONES_ARQUITECTURA.md
src/docs/ia-generativa.md
src/docs/INSTALACION.md
src/docs/integracion-meta.md
src/docs/PROMPT_SUSTENTO.md
src/docs/README_TECNICO.md
src/docs/tecnologias.md
src/requirements.txt
src/tests/dataset_evaluacion.json
```

### 1.3 Directorios principales

```
ls -la raíz:
  docs/           32 KB  ← 3 archivos (duplicados de src/docs/)
  src/app/       392 KB  ← código fuente de la aplicación
  src/data/       18 MB  ← BD SQLite + conversaciones exportadas + backups
  logo2.png     1.6 MB   ← binario grande en raíz del repo (ver Parte 2)
```

### 1.4 `.gitignore` — observaciones

- `notas.md`, `estructura.md`, `instruccion.md`, `hu.md` están al inicio del `.gitignore` como líneas sueltas (sin sección ni comentario) — probablemente añadidas manualmente antes del bloque principal.
- `CLAUDE.md` y `AGENTS.md` están en `.gitignore`, por lo que no van al repositorio GitHub. El tutor no puede leerlos directamente.
- `ESTADO_SESION.md` (raíz) es **untracked** pero no está en `.gitignore` — es un archivo de trabajo que podría subirse accidentalmente.

---

## PARTE 2 — Archivos posiblemente no utilizados

Metodología: se buscaron importaciones de cada módulo con `grep -rn "from app\." src/` y se verificó manualmente si los scripts están documentados como ejecución manual.

| Archivo | Importado por | Estado |
|---|---|---|
| `app/ai/__init__.py` | `from app.ai import groq_client` (observer, orchestrator) | USADO |
| `app/ai/groq_client.py` | orchestrator, conversation_observer, evaluar_dataset | USADO |
| `app/ai/prompts.py` | groq_client.py | USADO |
| `app/analysis/__init__.py` | `from app.analysis import conversation_observer` | USADO |
| `app/analysis/conversation_observer.py` | orchestrator.py | USADO |
| `app/analysis/orchestrator.py` | webhook/router.py | USADO |
| `app/analysis/text_analyzer.py` | orchestrator.py, evaluar_dataset.py | USADO |
| `app/analysis/url_analyzer.py` | orchestrator.py, evaluar_dataset.py | USADO |
| `app/config.py` | groq_client, orchestrator, dashboard, webhook, db | USADO |
| `app/dashboard/auth.py` | dashboard/router.py | USADO |
| `app/dashboard/router.py` | app/main.py | USADO |
| `app/db/sqlite_client.py` | orchestrator, webhook/router, conversation_observer, scripts | USADO |
| **`app/db/supabase_client.py`** | **ninguno** | **NO USADO — DEAD CODE** |
| `app/main.py` | entrypoint uvicorn | SCRIPT PRINCIPAL |
| `app/models/schemas.py` | analysis modules, webhook/router | USADO |
| `app/notifications/email_notifier.py` | orchestrator, dashboard/router, test_email | USADO |
| `app/notifications/messenger.py` | orchestrator, dashboard/router | USADO |
| `app/utils/logger.py` | casi todos los módulos | USADO |
| `app/webhook/router.py` | app/main.py | USADO |
| `app/webhook/validator.py` | webhook/router.py (importado, no invocado) | **PARCIAL — ver Parte 4** |
| `database/init_db.py` | ninguno | SCRIPT MANUAL |
| **`export_conversations.py`** | ninguno | **SCRIPT MANUAL — fuera de lugar** |
| `scripts/backup_db.py` | ninguno | SCRIPT MANUAL |
| `scripts/evaluar_dataset.py` | ninguno | SCRIPT MANUAL (documentado en CLAUDE.md) |
| `scripts/import_conversations.py` | ninguno | SCRIPT MANUAL (documentado en CLAUDE.md) |
| **`scripts/migrate_conv_ids.py`** | ninguno | **SCRIPT MANUAL — probablemente ya ejecutado** |
| `scripts/reset_analisis.py` | ninguno | SCRIPT MANUAL |
| `scripts/restore_db.py` | ninguno | SCRIPT MANUAL |
| `scripts/setup_usuarios.py` | ninguno | SCRIPT MANUAL (documentado en CLAUDE.md) |
| `scripts/test_email.py` | ninguno | SCRIPT MANUAL |
| `scripts/update_blacklist.py` | ninguno | SCRIPT MANUAL (documentado en CLAUDE.md) |
| `tests/__init__.py` | pytest | MARCADOR DE PAQUETE |
| `logo2.png` (raíz) | ninguno | **BINARIO GRANDE EN RAÍZ — ver nota** |

### Notas adicionales

- **`app/db/supabase_client.py`**: Supabase fue descartado por decisión del tutor (2026-05-08). El archivo existe, compila (importa `supabase`), pero `supabase` no está en `requirements.txt` — fallaría si se ejecutase. Es dead code confirmado.
- **`export_conversations.py`**: Ubicado en `src/` raíz en lugar de `src/scripts/`. Es un script standalone con 6842 líneas que exporta conversaciones vía Instagram Graph API. Documentado dentro de sí mismo pero no en CLAUDE.md.
- **`scripts/migrate_conv_ids.py`**: Script de migración one-time para corregir el cálculo de `conversation_id` (de `sha256(sender+recipient)` a `sha256(sorted([sender,recipient]))`). Según la descripción, este cambio ya está en producción — el script probablemente ya se ejecutó.
- **`logo2.png` (raíz, 1.6 MB)**: Binario grande commiteado en la raíz. Git no tiene LFS configurado. El asset estático real debería vivir en `src/static/`.
- **`src/app/notifications/email_notifier.py::send_welcome_email`**: La función existe (línea 255) pero solo es llamada desde `scripts/test_email.py`. No está integrada en el flujo principal del sistema.
- **Duplicados en `docs/`**: La carpeta raíz `docs/` contiene 3 archivos (`arquitectura.md`, `integracion-meta.md`, `tecnologias.md`) que son versiones anteriores/distintas de los equivalentes en `src/docs/`. Son redundantes.
- **`src/docs/base-de-datos.md` vs `src/docs/BASE_DE_DATOS.md`**: Dos archivos sobre la misma temática con nombres distintos (245 y 230 líneas respectivamente). No se pudo verificar si tienen contenido idéntico sin leerlos completos.

---

## PARTE 3 — Cobertura de documentación

### 3.1 Conteo de docstrings por módulo

| Módulo | Archivo | Líneas con `"""` | Funciones/métodos | Promedio |
|---|---|---|---|---|
| ai | groq_client.py | 0 | 3 | 0% |
| ai | prompts.py | 0 | 0 (solo constante) | n/a |
| analysis | orchestrator.py | 0 | 2 | 0% |
| analysis | text_analyzer.py | 0 | 1 | 0% |
| analysis | url_analyzer.py | 0 | 4 | 0% |
| analysis | conversation_observer.py | 2 | 2 | ~50% |
| dashboard | router.py | 16 | 14 | ~30%* |
| dashboard | auth.py | 2 | 5 | ~20% |
| db | sqlite_client.py | 21 | 11 | ~60%* |
| notifications | email_notifier.py | 6 | 4 | ~50%* |
| notifications | messenger.py | 4 | 2 | ~50%* |
| webhook | router.py | 0 | 3 | 0% |
| webhook | validator.py | 0 | 1 | 0% |

*Nota: en `dashboard/router.py` y `db/sqlite_client.py`, muchas líneas con `"""` son strings dentro de HTML embebido (queries SQL inline), no necesariamente docstrings de función. El porcentaje real de docstrings útiles es menor.

### 3.2 Cobertura en `src/docs/`

| Módulo | Archivo(s) en src/docs/ | Cobertura | Qué falta |
|---|---|---|---|
| `app/ai/` | `ia-generativa.md`, `PROMPT_SUSTENTO.md` | Buena | Documentar parámetros de `analyze_conversation()`, manejo de errores |
| `app/analysis/` | `README_TECNICO.md`, `arquitectura.md` | Parcial | `conversation_observer` mencionado brevemente; `text_analyzer` y `url_analyzer` sin doc propia |
| `app/dashboard/` | `README_TECNICO.md` (1 párrafo) | Escasa | No existe doc dedicada al dashboard; autenticación, rutas y lógica de vistas sin documentar |
| `app/db/` | `BASE_DE_DATOS.md`, `base-de-datos.md` | Buena | Aclarar cuál de los dos es la versión vigente |
| `app/notifications/` | `README_TECNICO.md` (mención) | Escasa | `email_notifier.py` no tiene doc propia; `send_welcome_email` no documentada |
| `app/webhook/` | `integracion-meta.md` | Buena | HMAC sin documentar como "pendiente de implementar" |
| `app/config.py` | `INSTALACION.md` (parcial) | Parcial | Las variables `ENABLE_*` y los pesos no están explicados en ningún doc |

---

## PARTE 4 — Estado de funcionalidades

### 4.1 HMAC webhook (verify_signature)

**Estado: IMPORTADO pero NO CONECTADO**

```python
# webhook/router.py — línea 10
from app.webhook.validator import verify_signature

# El POST handler (línea 67) NO llama a verify_signature en ningún momento.
# La función existe y es correcta en validator.py, pero nunca se invoca.
```

La validación de firma criptográfica está implementada en `validator.py` pero no protege el endpoint `POST /webhook`. Cualquier cliente puede enviar payloads falsos.

### 4.2 ENABLE_AUTO_RESPONSE

**Estado: SÍ está implementado y activo por defecto**

```python
# orchestrator.py — línea 165
if (
    risk_level == RiskLevel.HIGH
    and settings.ENABLE_AUTO_RESPONSE      # ← se lee aquí
    and id_analisis is not None
):
```

Valor por defecto en `config.py`: `ENABLE_AUTO_RESPONSE: bool = True`.  
Documentado en `src/.env-example` como `ENABLE_AUTO_RESPONSE=true`.

### 4.3 RISK_THRESHOLD_MEDIUM

**Valor actual:** `0.4` (tanto en `config.py` como en `src/.env-example`)

```python
# config.py — línea 8
RISK_THRESHOLD_MEDIUM: float = 0.4
RISK_THRESHOLD_HIGH: float = 0.7
```

El archivo `.env.example` en la raíz del repositorio NO incluye estas variables (solo tiene llaves Meta vacías). El archivo completo es `src/.env-example`.

### 4.4 UM Cloud AI — manejo de errores

**Estado: manejo robusto en dos capas**

**Capa 1 — `groq_client.py`** (función `analyze_conversation`):
```python
except json.JSONDecodeError:
    logger.warning("UM Cloud devolvió respuesta no-JSON — análisis omitido")
    return {}
except Exception as exc:
    logger.warning("UM Cloud análisis omitido: %s", exc)
    return {}
```

**Capa 2 — `orchestrator.py`** (líneas 87-131):
```python
try:
    ai_result = await groq_client.analyze_conversation(...)
    if ai_result:
        # ...procesa resultado
except Exception as exc:
    logger.warning("UM Cloud integration skipped: %s", exc)
    mensajes_analizados = 1
```

Si `UM_API_KEY` está vacío, `groq_client.analyze_conversation` retorna `{}` inmediatamente (línea 34: `if not settings.UM_API_KEY: return {}`). El sistema continúa con el score heurístico puro.

### 4.5 Script de evaluación del dataset

**Estado: SÍ existe en `src/scripts/evaluar_dataset.py`**

El script:
- Lee los 8 casos de `src/tests/dataset_evaluacion.json`
- Corre `URLAnalyzer` + `TextAnalyzer` + UM Cloud AI sobre cada caso
- Compara `expected_severity` vs `final_risk` (combinación heurística + IA)
- Reporta PASS/FAIL por caso y porcentaje global

**Lo que NO calcula:** precision, recall, F1, ni matriz de confusión formal. El score es simplemente `casos_correctos / total_casos`. Para el informe académico sería necesario añadir estas métricas.

Invocación:
```bash
cd src && .venv/bin/python scripts/evaluar_dataset.py
```

---

## PARTE 5 — Tareas pendientes para el informe

### Limpieza de repo

- [ ] **Eliminar `src/app/db/supabase_client.py`** — dead code, Supabase descartado por el tutor. No importado en ningún módulo activo.
- [ ] **Mover `src/export_conversations.py` → `src/scripts/`** — script standalone en ubicación inconsistente con el resto.
- [ ] **Evaluar `src/scripts/migrate_conv_ids.py`** — si la migración ya se ejecutó, archivar o eliminar para no confundir.
- [ ] **Mover `logo2.png` (raíz) → `src/static/logo.png`** o eliminar si es idéntico al que ya existe en `src/static/`. Es un binario de 1.6 MB commiteado directamente.
- [ ] **Consolidar `docs/` raíz con `src/docs/`** — la carpeta raíz tiene 3 archivos que duplican versiones de `src/docs/`. Elegir una ubicación canónica.
- [ ] **Resolver `src/docs/BASE_DE_DATOS.md` vs `src/docs/base-de-datos.md`** — dos archivos sobre el mismo tema con nombres distintos.
- [ ] **Agregar `ESTADO_SESION.md` al `.gitignore` raíz** — archivo de trabajo untracked que podría subirse por accidente.

### Documentación faltante

- [ ] **Dashboard (`app/dashboard/router.py`, 864 líneas)** — ningún módulo en `src/docs/` lo cubre de forma dedicada. El router incluye 14 funciones sin docstrings. Crear `src/docs/dashboard.md`.
- [ ] **`analyze_conversation()` en `groq_client.py`** — función central del módulo IA, sin docstring. Documentar parámetros, valor de retorno (dict JSON con schema específico) y comportamiento al fallar.
- [ ] **`PhishingOrchestrator.analyze()` en `orchestrator.py`** — función más importante del sistema, sin docstring. Documentar el flujo de 6 etapas y las condiciones de cada rama.
- [ ] **`app/webhook/validator.py`** — debe documentarse explícitamente que `verify_signature()` existe pero no está conectada al router (es una tarea pendiente, no un olvido).
- [ ] **`send_welcome_email()` en `email_notifier.py`** — función definida pero sin punto de invocación en el flujo principal. Documentar si está planificada o es código de prueba.
- [ ] **Variables `ENABLE_AUTO_RESPONSE`, `ENABLE_EMAIL_ALERTS`, `URL_WEIGHT`, `TEXT_WEIGHT`** — no aparecen explicadas en ningún doc de `src/docs/`. Agregar sección en `README_TECNICO.md` o `arquitectura.md`.
- [ ] **`evaluar_dataset.py`**: añadir cálculo de precision/recall para el informe académico.

### Funcionalidades a implementar para el viernes

#### RAG (Retrieval-Augmented Generation)

El objetivo sería aumentar el prompt enviado a UM Cloud con fragmentos relevantes recuperados de una base de conocimiento (ej: descripción de técnicas MITRE, patrones de scams conocidos, etc.).

**Archivos nuevos necesarios:**
```
src/app/rag/
    __init__.py
    embedder.py          # genera embeddings de texto
    vector_store.py      # interfaz con ChromaDB o FAISS
    retriever.py         # dado un texto, devuelve chunks relevantes
src/data/knowledge_base/
    mitre_techniques.json   # corpus de técnicas ATT&CK
    scam_patterns.md        # descripciones de categorías de scam
src/scripts/build_rag_index.py  # script one-time para indexar el corpus
```

**Archivos existentes a modificar:**
- `src/app/ai/groq_client.py` — añadir parámetro `retrieved_context: str` a `analyze_conversation()`, incluirlo en el `user_prompt`
- `src/app/ai/prompts.py` — actualizar `SYSTEM_PROMPT` para instruir al modelo a usar el contexto recuperado
- `src/app/analysis/orchestrator.py` — llamar al retriever antes de `groq_client.analyze_conversation()` y pasar el contexto

**Dependencias nuevas:**
```
chromadb>=0.5          # vector store local (sin servidor)
sentence-transformers  # o usar endpoint de embeddings de UM Cloud si disponible
```

**Estimación de complejidad: COMPLEJO**  
Razones: requiere diseño del corpus de conocimiento, evaluación de la calidad de retrieval, riesgo de aumentar la latencia del pipeline, y posible incompatibilidad con los límites de contexto del modelo `gemma4-26b`.

---

#### Exportar análisis a PDF

**Librería recomendada: `weasyprint`**

Justificación: el dashboard ya genera HTML complejo con CSS (Tailwind inline + chamba.css). WeasyPrint convierte HTML→PDF manteniendo el layout, por lo que se pueden reutilizar las mismas estructuras HTML que ya existen. ReportLab requeriría reconstruir todo el layout desde cero con su API imperativa. fpdf2 tiene soporte CSS limitado. WeasyPrint es la opción con menor duplicación de código.

Nota: WeasyPrint requiere librerías del sistema (`libpango`, `libcairo`, `libgdk-pixbuf`). En producción o entorno de Docker, esto implica añadir dependencias del SO.

**Endpoint nuevo:**
```
GET /dashboard/conversacion/{id_conversacion}/pdf
    → descarga directa del PDF (Content-Disposition: attachment)
    → requiere sesión activa (misma auth que el dashboard)
```

**Información del análisis que debería incluir el PDF y que el dashboard actual no muestra o muestra parcialmente:**
- Historial completo de mensajes (el dashboard muestra una vista resumida en el panel lateral)
- Explicación completa del analista (`explicacion_analista`) — en el dashboard este campo aparece colapsado o truncado
- Desglose numérico de sub-scores: `score_urls`, `score_texto`, `score_ia`, `score_final` con los pesos aplicados
- Lista completa de indicadores heurísticos detectados (`patterns_matched`, `url_reasons`)
- Lista de URLs sospechosas identificadas por la IA (`ai_suspicious_urls`)
- Principios de Cialdini detectados (`principios_cialdini`) — no visible en el dashboard actual
- Técnica MITRE y etapa del lifecycle — visibles en el dashboard, pero sin contexto explicativo
- Timestamp de exportación y versión del sistema
- Identificador de la conversación y hash del participante

**Archivos a crear/modificar:**
- Nuevo: `src/app/dashboard/pdf_export.py` — función `render_pdf(id_conversacion, user) → bytes`
- Modificar: `src/app/dashboard/router.py` — agregar la ruta `GET /conversacion/{id}/pdf`
- Modificar: `src/requirements.txt` — añadir `weasyprint`

**Estimación de complejidad: MEDIO**  
La mayor parte del trabajo es diseñar el template HTML del PDF (1 archivo nuevo). La integración con el router y la DB sigue el mismo patrón que ya existe en el dashboard.

---

## Apéndice — Observaciones de seguridad

1. **HMAC no conectado** (ver 4.1): el endpoint `POST /webhook` no valida la firma de Meta. Cualquier cliente puede inyectar mensajes falsos.
2. **`SESSION_SECRET` hardcodeado**: el valor por defecto `"link_seguro_secret_2024"` está en el código fuente. Si se deployara sin cambiar `SESSION_SECRET` en `.env`, las cookies serían predecibles.
3. **Conversaciones reales en `src/data/conversations/`**: el `.gitignore` excluye este directorio, pero existe en disco con datos de Instagram. Los archivos de backup (`src/data/backups/`) también están excluidos del repo pero presentes localmente.
4. **`src/.env`**: existe en disco (1835 bytes) con credenciales reales. Está correctamente en `.gitignore`.

---

*Este documento fue generado por análisis estático del código fuente. No se ejecutó ningún proceso ni se modificó ningún archivo.*
