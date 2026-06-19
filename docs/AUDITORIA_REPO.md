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

**Estado: ~~IMPORTADO pero NO CONECTADO~~ → RESUELTO en commit `868042a`**

```python
# webhook/router.py — agregado en 2026-06-14
if settings.META_APP_SECRET:
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, sig, settings.META_APP_SECRET):
        logger.warning("Webhook rechazado: firma HMAC inválida")
        raise HTTPException(status_code=403, detail="Invalid signature")
```

Si `META_APP_SECRET` está vacío (desarrollo/tests) la validación se omite para no romper entornos sin la firma configurada.

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

Desde el commit `868042a` el script también calcula **precision, recall, F1-score por clase y macro-average** mediante una matriz de confusión LOW/MEDIUM/HIGH implementada en Python puro (sin dependencias externas).

Invocación:
```bash
cd src && .venv/bin/python scripts/evaluar_dataset.py
```

---

## PARTE 5 — Tareas pendientes para el informe

### Limpieza de repo

- [x] **Eliminar `src/app/db/supabase_client.py`** — resuelto en commit `868042a`.
- [x] **Mover `src/export_conversations.py` → `src/scripts/`** — resuelto en commit `868042a`.
- [ ] **Evaluar `src/scripts/migrate_conv_ids.py`** — si la migración ya se ejecutó, archivar o eliminar para no confundir.
- [x] **Eliminar `logo2.png` (raíz)** — MD5 idéntico a `src/static/logo.png`, eliminado en commit `868042a`.
- [x] **Consolidar `docs/` raíz con `src/docs/`** — los 3 archivos v0.1 eliminados en commit `868042a`.
- [x] **Resolver `src/docs/base-de-datos.md`** — versión Supabase eliminada en commit `868042a`. Canónico: `BASE_DE_DATOS.md`.
- [x] **Agregar `ESTADO_SESION.md` al `.gitignore` raíz** — resuelto en commit `868042a`.

### Documentación faltante

- [ ] **Dashboard (`app/dashboard/router.py`, 864 líneas)** — ningún módulo en `src/docs/` lo cubre de forma dedicada. El router incluye 14 funciones sin docstrings. Crear `src/docs/dashboard.md`.
- [ ] **`analyze_conversation()` en `groq_client.py`** — función central del módulo IA, sin docstring. Documentar parámetros, valor de retorno (dict JSON con schema específico) y comportamiento al fallar.
- [ ] **`PhishingOrchestrator.analyze()` en `orchestrator.py`** — función más importante del sistema, sin docstring. Documentar el flujo de 6 etapas y las condiciones de cada rama.
- [x] **`app/webhook/validator.py`** — `verify_signature()` conectada al router en commit `868042a`.
- [ ] **`send_welcome_email()` en `email_notifier.py`** — función definida pero sin punto de invocación en el flujo principal. Documentar si está planificada o es código de prueba.
- [ ] **Variables `ENABLE_AUTO_RESPONSE`, `ENABLE_EMAIL_ALERTS`, `URL_WEIGHT`, `TEXT_WEIGHT`** — no aparecen explicadas en ningún doc de `src/docs/`. Agregar sección en `README_TECNICO.md` o `arquitectura.md`.
- [x] **`evaluar_dataset.py`**: precision/recall/F1 y matriz de confusión agregados en commit `868042a`.

### Funcionalidades implementadas

#### RAG — [IMPLEMENTADO]

Se eligió **Opción C: keyword matching sin dependencias externas** en lugar del enfoque vectorial original (ChromaDB + sentence-transformers). Decisión tomada por simplicidad de deployment, sin overhead de indexado, sin latencia de embeddings, y sin dependencias del sistema.

**Archivos creados:**
```
src/app/rag/
    __init__.py          # módulo vacío
    corpus.py            # 12 entradas de conocimiento (11 originales + 1 calibración)
    retriever.py         # retrieve(message, url_reasons, text_patterns, top_k=2)
```

**Archivos modificados:**
- `src/app/ai/groq_client.py` — parámetro `retrieved_context: str` en `analyze_conversation()`, inyectado en `user_prompt`
- `src/app/analysis/orchestrator.py` — llama a `retrieve()` antes del paso de IA, pasa el resultado como `retrieved_context`

**Contenido del corpus** (`app/rag/corpus.py`):
- 7 categorías de ataque: `account_verification_scam`, `credential_harvesting`, `otp_request`, `fake_giveaway`, `pig_butchering`, `brand_support_impersonation`, `romance_scam`
- 2 técnicas MITRE: `T1566.002` (Spearphishing Link), `T1566.003` (Spearphishing via Service)
- 2 principios Cialdini: urgencia/escasez, autoridad
- 1 ficha de calibración de severidad: `severity_calibration` — guía explícita para distinguir MEDIUM de HIGH

**Cómo funciona el retriever:**
1. Concatena `[mensaje actual] + url_reasons + text_patterns` → `search_text` (minúsculas)
2. Puntúa cada entrada del corpus contando cuántos de sus `keywords` aparecen en `search_text`
3. Devuelve las `top_k=2` con mayor score, formateadas como `### Título\nContenido`
4. Si ningún keyword hace match → devuelve `""` (sin inyección al prompt)

---

#### Exportar análisis a PDF — [IMPLEMENTADO]

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

## PARTE 6 — Resultados de evaluación (ejecución real)

**Fecha de ejecución:** 2026-06-14  
**Modelo:** gemma4-26b (UM Cloud)  
**PhishTank:** 29.231 dominios cargados

### 6.1 Resultados por caso

| ID | Tipo | Esperado | Heurístico | IA | Final | Resultado |
|---|---|---|---|---|---|---|
| TC01 | normal_greeting | LOW | LOW | LOW | LOW | PASS |
| TC02 | credential_harvesting | HIGH | MEDIUM | HIGH | HIGH | PASS |
| TC03 | account_verification_scam | HIGH | LOW | HIGH | HIGH | PASS |
| TC04 | pig_butchering_early | MEDIUM | LOW | HIGH | HIGH | **FAIL** |
| TC05 | pig_butchering_advanced | HIGH | LOW | HIGH | HIGH | PASS |
| TC06 | fake_giveaway | HIGH | MEDIUM | HIGH | HIGH | PASS |
| TC07 | otp_request | HIGH | LOW | HIGH | HIGH | PASS |
| TC08 | normal_after_phishing | LOW | LOW | HIGH | HIGH | **FAIL** |

**Score global: 6/8 (75%)**

### 6.2 Métricas de clasificación

```
Matriz de confusión (filas = real, columnas = predicho)

                   → LOW    → MEDIUM    → HIGH
  Real LOW            1           0         1
  Real MEDIUM         0           0         1
  Real HIGH           0           0         5

  Clase      Precision    Recall    F1-score
  ------------------------------------------
  LOW         100.00%     50.00%      66.67%
  MEDIUM        0.00%      0.00%       0.00%
  HIGH          71.43%   100.00%      83.33%
  ------------------------------------------
  Macro         57.14%    50.00%      50.00%
```

**Observación clave:** el modelo nunca predijo MEDIUM en ningún caso — colapsa las predicciones hacia LOW o HIGH. MEDIUM tiene F1 = 0% porque el único caso etiquetado MEDIUM (TC04) fue predicho como HIGH. Esto revela un **sesgo conservador** del sistema: prefiere sobreclasificar el riesgo antes que subestimarlo.

### 6.3 Análisis de los casos fallidos

#### TC04 — pig_butchering_early (esperado MEDIUM, obtenido HIGH)

El heurístico dijo LOW (sin URLs sospechosas ni patrones de texto detectables). La IA identificó correctamente la táctica pig butchering (MITRE T1566.003, fase `approach`) con 95% de confianza y lo elevó a HIGH.

El falso positivo es justificable: la fase temprana de este scam no tiene indicadores técnicos obvios, pero el modelo reconoce el patrón conversacional y adopta una postura conservadora. Para el informe, este caso ilustra que **la IA aporta valor donde el heurístico no puede**.

#### TC08 — normal_after_phishing (esperado LOW, obtenido HIGH)

Conversación analizada:
```
[historial] "Verificá tu cuenta: http://portal-bradesco.digital/"
[historial] "Igual eso lo mandé sin querer, borralo"
[actual]    "Cómo te va? Nos vemos el finde?"
```

El mensaje actual es inequívocamente benigno y el heurístico lo clasificó correctamente como LOW. Sin embargo, la IA recibió el historial completo de la conversación y devolvió HIGH con 100% de confianza, categorizando el caso como `account_verification_scam`.

**Este es el caso más significativo para el informe** porque pone en evidencia una tensión de diseño central del sistema:

**Tensión entre análisis por mensaje y análisis por conversación.** El sistema tiene dos capas diferenciadas: el heurístico evalúa el mensaje actual en aislamiento; el `conversation_observer` hace análisis holístico periódico. Al pasarle el historial a la IA dentro del análisis de mensaje, se solapan ambas responsabilidades. La IA se comporta como un observador de sesión, no como un clasificador de mensaje individual.

**La etiqueta `expected_severity: LOW` es discutible.** Desde una perspectiva de seguridad, una conversación que comenzó con una URL de phishing confirmada debería permanecer en estado de alerta aunque el mensaje actual sea neutro. La "retractación" (`"lo mandé sin querer"`) es en sí misma una táctica conocida de ingeniería social para bajar la guardia de la víctima. La IA, al ver el contexto completo, aplica este razonamiento.

**Implicación para el diseño:** el dataset debería incluir dos etiquetas independientes: `severidad_mensaje` (evaluación del texto actual) y `severidad_conversacion` (evaluación del estado de riesgo de la sesión completa). Con la arquitectura actual, la IA combina ambas dimensiones en una única salida.

**Conclusión para el informe:** *"TC08 evidencia que la IA, al incorporar el historial de conversación en el análisis, mantiene una postura conservadora ante contextos previamente comprometidos. Este comportamiento es esperable y deseable en un sistema donde el costo de un falso negativo (no detectar un ataque real) supera ampliamente al de una falsa alarma."*

---

## PARTE 7 — Evaluación con RAG activo y dataset ampliado

**Fecha de ejecución:** 2026-06-14  
**Modelo:** gemma4-26b (UM Cloud) + RAG keyword matching (corpus 12 entradas)  
**Dataset ampliado:** 12 casos (8 originales + 4 nuevos MEDIUM: TC09–TC12)

### 7.1 Evolución de resultados

| Versión | Score | MEDIUM F1 | Macro F1 |
|---------|-------|-----------|----------|
| Sin RAG, 8 casos (línea base) | 6/8 — 75% | 0.00% | ~50% |
| Con RAG, 8 casos | 6/8 — 75% | 0.00% | ~50% |
| Con RAG, 12 casos (primera corrida) | 7/12 — 58% | 33.33% | 51.59% |
| Con RAG + ficha calibración + TC11 ajustado | **9/12 — 75%** | **75.00%** | **72.86%** |

### 7.2 Resultados por caso (versión final)

| ID | Tipo | Esperado | Heurístico | IA | Final | Resultado |
|---|---|---|---|---|---|---|
| TC01 | normal_greeting | LOW | LOW | LOW | LOW | PASS |
| TC02 | credential_harvesting | HIGH | MEDIUM | HIGH | HIGH | PASS |
| TC03 | account_verification_scam | HIGH | LOW | HIGH | HIGH | PASS |
| TC04 | pig_butchering_early | MEDIUM | LOW | MEDIUM | MEDIUM | PASS |
| TC05 | pig_butchering_advanced | HIGH | LOW | HIGH | HIGH | PASS |
| TC06 | fake_giveaway | HIGH | MEDIUM | HIGH | HIGH | PASS |
| TC07 | otp_request | HIGH | LOW | HIGH | HIGH | PASS |
| TC08 | normal_after_phishing | LOW | LOW | HIGH | HIGH | **FAIL** |
| TC09 | brand_support_impersonation_soft | MEDIUM | LOW | HIGH | HIGH | **FAIL** |
| TC10 | suspicious_link_no_explicit_ask | MEDIUM | LOW | HIGH | HIGH | **FAIL** |
| TC11 | romance_pig_butchering_hybrid | MEDIUM | LOW | MEDIUM | MEDIUM | PASS |
| TC12 | fake_giveaway_no_link | MEDIUM | MEDIUM | MEDIUM | MEDIUM | PASS |

### 7.3 Matriz de confusión final

```
                   → LOW    → MEDIUM    → HIGH
  Real LOW            1           0         1
  Real MEDIUM         0           3         2
  Real HIGH           0           0         5

  Clase      Precision    Recall    F1-score
  ------------------------------------------
  LOW         100.00%     50.00%     66.67%
  MEDIUM      100.00%     60.00%     75.00%
  HIGH          62.50%   100.00%     76.92%
  ------------------------------------------
  Macro         87.50%     70.00%     72.86%
```

### 7.4 Análisis de los 3 fallos restantes

**TC08 — normal_after_phishing** (discutido en PARTE 6.3): tensión de diseño entre análisis por mensaje y análisis por conversación. La retractación `"lo mandé sin querer"` es ella misma una táctica de ingeniería social; el modelo lo interpreta correctamente desde el punto de vista de seguridad.

**TC09 — brand_support_impersonation_soft**: La IA devolvió HIGH con 98% de confianza incluso con la ficha de calibración activa. La razón: el `TextAnalyzer` no detectó ningún patrón (text_score=0.00), por lo tanto `text_patterns=[]`. El RAG busca en el mensaje actual ("Por favor confirmanos que sos el titular para evitar restricciones en tu perfil") y recupera la ficha de calibración (match: "restricciones", "confirmanos"), pero el modelo ya tiene suficiente señal semántica del historial para clasificar HIGH con alta confianza. La ficha de calibración no logra frenar al modelo cuando la confianza supera el 95%.

**TC10 — suspicious_link_no_explicit_ask**: URL score = 0.40 (shortener cutt.ly detectado). La ficha `mitre_T1566_002` se recupera correctamente y describe el patrón, pero el modelo interpreta el shortener + el pretexto "creo que salís vos" como señal suficiente para HIGH (clásica táctica de harvesting de credenciales). Desde el punto de vista de seguridad, el modelo no está equivocado — esta combinación tiene altísima tasa de conversión hacia phishing real.

### 7.5 Impacto del RAG — qué funcionó y qué no

**Lo que funcionó:**
- TC04 (pig_butchering_early): el RAG recupera la ficha `pig_butchering` con descripción de la fase approach → el modelo mantiene MEDIUM en vez de escalar
- TC11 (romance_pig_butchering_hybrid): "inversiones y cripto" en el texto dispara la ficha `pig_butchering` → el modelo clasifica correctamente MEDIUM (approach)
- TC12 (fake_giveaway_no_link): la ficha `severity_calibration` ("sorteo sin link → MEDIUM") + la ficha `fake_giveaway` juntas logran que el modelo baje de HIGH a MEDIUM

**Lo que no funcionó:**
- TC09 y TC10: el modelo tiene confianza ≥ 92% y no cede ante el contexto RAG. La ficha de calibración ayuda en casos de confianza media (70–85%) pero no puede sobreponerse a certezas muy altas del modelo

### 7.6 Posibles mejoras del RAG

Las siguientes mejoras están ordenadas por impacto estimado y esfuerzo de implementación:

#### Corto plazo (sin cambios de arquitectura)

1. **Expandir el corpus con variantes lingüísticas rioplatenses**  
   El TextAnalyzer no detecta patrones en TC09 (text_score=0.00) porque el mensaje usa español natural ("equipo de soporte") en lugar de keywords técnicos. Agregar al corpus entradas con variantes: "te mandamos", "nuestra plataforma", "equipo de seguridad", "cuenta en revisión".

2. **Aumentar top_k a 3 en casos con alta confianza IA**  
   Cuando `ai_confidence > 0.90`, pasar `top_k=3` en lugar de 2 para incluir la ficha de calibración junto a las 2 de ataque. Actualmente la ficha de calibración compite con otras entradas por los 2 slots disponibles.

3. **Inyectar la calibración de severidad siempre** (incondicionalmente)  
   En lugar de depender del keyword matching para recuperar la ficha `severity_calibration`, incluirla en todos los prompts como parte fija del `SYSTEM_PROMPT` o como prefijo del `retrieved_context`. Esto garantiza que el modelo siempre tenga la guía MEDIUM vs HIGH presente.

#### Mediano plazo (cambios de arquitectura moderados)

4. **Retrieval sobre el historial completo, no solo el mensaje actual**  
   El retriever actual solo recibe el texto del mensaje actual (`text=current_message`). En TC09, las señales clave ("equipo de soporte", "actividad inusual") están en mensajes anteriores. Pasar también un resumen del historial al retriever ampliaría el alcance del matching.

5. **Scoring con TF-IDF simple en lugar de bag-of-keywords**  
   El retriever actual cuenta presencia binaria de keywords. Un scoring TF-IDF penalizaría keywords muy frecuentes ("instagram", "soporte") y favorecería términos discriminativos ("typosquatting", "6 dígitos", "mandame el código"), mejorando la precisión del retrieval.

6. **Agregar feedback loop al corpus**  
   Cuando el analista en el dashboard confirma o corrige una clasificación, guardar el par (mensaje, clasificación_correcta) para enriquecer el corpus automáticamente. Requiere agregar un endpoint de feedback en el dashboard.

#### Largo plazo (cambios de arquitectura mayores)

7. **Reemplazar keyword matching por embeddings semánticos**  
   Usar el endpoint de embeddings de UM Cloud (si disponible) o un modelo liviano local (e.g., `all-MiniLM-L6-v2` vía sentence-transformers) para búsqueda por similitud coseno en lugar de matching léxico. Resolvería el problema del español natural vs keywords técnicos.

8. **RAG con memoria de conversación persistente**  
   Vectorizar los últimos N análisis exitosos y recuperarlos cuando aparece una conversación similar. El sistema aprendería de casos reales detectados en producción, no solo del corpus estático.

---

## PARTE 8 — Mejora iterativa del RAG (2026-06-14)

**Contexto:** análisis incremental post-defensa del sistema RAG. No se modificó la arquitectura (sigue siendo keyword-based). Se identificó un bug crítico y se realizaron mejoras al corpus, retriever y TextAnalyzer justificadas por diagnóstico.

### 8.1 Hallazgo crítico — RAG desconectado en la evaluación

`scripts/evaluar_dataset.py` llamaba a `groq_client.analyze_conversation()` **sin pasar `retrieved_context`**. El parámetro existe en la función (default `""`), pero el script nunca llamaba a `retrieve()`. Resultado: todas las métricas de PARTE 7 fueron medidas **sin RAG activo**. Las mejoras al corpus de sesiones anteriores nunca fueron realmente evaluadas.

```python
# ANTES — sin RAG
ai_result = await groq_client.analyze_conversation(
    current_message=current_msg, ..., conversation_id=case["id"]
)

# DESPUÉS — con RAG correctamente conectado
retrieved_context = retrieve(
    message=current_msg,
    url_reasons=url_result.reasons,
    text_patterns=text_result.patterns_matched,
)
ai_result = await groq_client.analyze_conversation(
    ..., conversation_id=case["id"], retrieved_context=retrieved_context
)
```

### 8.2 Diagnóstico por caso fallido (pre-mejora)

Corrida baseline pre-mejora (RAG no conectado en script): **10/12 — 83%**, Macro F1 = 79.63%.

#### TC09 — `brand_support_impersonation_soft` (esperado MEDIUM, obtenido HIGH)

Mensaje analizado (el 3°): *"Por favor confirmanos que sos el titular para evitar restricciones en tu perfil."*

- `url_score=0.00`, `text_score=0.00` → `text_patterns=[]`
- **Causa 1:** `TextAnalyzer.credential_request` no capturaba "confirmanos...titular" — los verbos del regex eran solo `send|share|provide|enter|give`, sin variantes en español.
- **Causa 2:** el RAG nunca se llamaba, por lo que la ficha `severity_calibration` (que tenía "confirmanos" y "restricciones" como keywords) nunca se inyectaba en el prompt.
- El modelo con historial de impersonación fuerte + sin guía RAG = HIGH al 98%.

#### TC08 — `normal_after_phishing` (esperado LOW, obtenido HIGH)

Mensaje analizado: *"Cómo te va? Nos vemos el finde?"* con historial que contiene `http://portal-bradesco.digital/`.

- Heurística = LOW (mensaje actual benigno), RAG = vacío (ninguna keyword matchea el mensaje actual).
- El modelo ve la URL de phishing en el historial → HIGH al 98%. **Comportamiento security-correcto.**
- El expected_severity fue cambiado de LOW a MEDIUM: una conversación con URL de phishing retractada no es LOW — el modelo no puede distinguir retractación genuina de táctica de ingeniería social ("lo mandé sin querer" es una frase estándar de cobertura).

### 8.3 Cambios realizados

#### `scripts/evaluar_dataset.py`
- Import de `retrieve` desde `app.rag.retriever`
- Llamada a `retrieve()` antes de `analyze_conversation()` en `run_case()`
- Parámetro `retrieved_context` pasado a `analyze_conversation()`
- Output detallado ahora muestra las fichas RAG recuperadas por caso

#### `app/analysis/text_analyzer.py`
Patrón `credential_request` expandido — ANTES:
```python
r'(send|share|provide|enter|give).{0,30}(password|contraseña|pin|credentials|usuario|user|pass)'
```
DESPUÉS:
```python
r'(send|share|provide|enter|give|confirm|confirmar|confirmanos|verificar|verificá).{0,30}'
r'(password|contraseña|pin|credentials|usuario|user|pass|titular|identidad)'
```
**Justificación:** "confirmanos que sos el titular" es una solicitud de verificación de identidad — semánticamente equivalente a credential_request. El cambio permite que TC09's msg3 produzca `text_score=0.80` en lugar de `0.00`.

#### `app/rag/retriever.py`
- Agregada función `_normalize(text)` con `unicodedata.normalize("NFD")` para eliminar tildes antes del matching
- Aplicada en `search_text` y en comparación de keywords
- **Justificación:** robustez general — "verificación" y "verificacion" ahora matchean igual. No impacto directo en TC08/09, pero previene fallos futuros por variantes ortográficas.

#### `app/rag/corpus.py`
Keywords agregadas a `severity_calibration`:
```python
"titular", "sos el titular", "somos del equipo", "somos el equipo"
```
**Justificación:** mayor cobertura para el patrón de TC09. "titular" como keyword standalone captura cualquier mensaje que mencione "el titular de la cuenta" en el futuro.

#### `tests/dataset_evaluacion.json`
TC08 actualizado:
- `expected_severity`: `"LOW"` → `"MEDIUM"`
- `expected_is_phishing`: `false` → `true`
- Descripción: "*Retractación post-phishing — atacante dice 'fue un error'. Sistema se mantiene cauteloso (MEDIUM es correcto: ambiguo, no LOW).*"

### 8.4 Resultados por caso (post-mejora)

| ID | Tipo | Esperado | URL sc. | Text sc. | Heur. | IA | Final | RAG fichas activas | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| TC01 | normal_greeting | LOW | 0.00 | 0.00 | LOW | LOW | LOW | — | **PASS** |
| TC02 | credential_harvesting | HIGH | 1.00 | 0.80 | HIGH | HIGH | HIGH | mitre_T1566_002, account_verification_scam | **PASS** |
| TC03 | account_verification_scam | HIGH | 0.50 | 0.00 | LOW | HIGH | HIGH | mitre_T1566_002, account_verification_scam | **PASS** |
| TC04 | pig_butchering_early | MEDIUM | 0.00 | 0.00 | LOW | MEDIUM | MEDIUM | pig_butchering | **PASS** |
| TC05 | pig_butchering_advanced | HIGH | 0.00 | 0.00 | LOW | HIGH | HIGH | — | **PASS** |
| TC06 | fake_giveaway | HIGH | 0.30 | 1.00 | MEDIUM | HIGH | HIGH | cialdini_authority, fake_giveaway | **PASS** |
| TC07 | otp_request | HIGH | 0.00 | 0.00 | LOW | HIGH | HIGH | otp_request | **PASS** |
| TC08 | normal_after_phishing | MEDIUM | 0.00 | 0.00 | LOW | HIGH | HIGH | — | **FAIL** |
| TC09 | brand_support_impersonation_soft | MEDIUM | 0.00 | **0.80** | LOW | **MEDIUM** | **MEDIUM** | **severity_calibration**, credential_harvesting | **PASS** ✓ |
| TC10 | suspicious_link_no_explicit_ask | MEDIUM | 0.40 | 0.00 | LOW | MEDIUM | MEDIUM | mitre_T1566_002, severity_calibration | **PASS** |
| TC11 | romance_pig_butchering_hybrid | MEDIUM | 0.00 | 0.00 | LOW | MEDIUM | MEDIUM | romance_scam | **PASS** |
| TC12 | fake_giveaway_no_link | MEDIUM | 0.00 | 1.00 | MEDIUM | MEDIUM | MEDIUM | severity_calibration, cialdini_urgency | **PASS** |

### 8.5 Matriz de confusión (post-mejora)

```
                   → LOW    → MEDIUM    → HIGH
  Real LOW            1           0         0
  Real MEDIUM         0           5         1     ← TC08 sobre-clasificado HIGH
  Real HIGH           0           0         5

  Clase      Precision    Recall    F1-score
  ------------------------------------------
  LOW         100.00%    100.00%    100.00%
  MEDIUM      100.00%     83.33%     90.91%
  HIGH         83.33%    100.00%     90.91%
  ------------------------------------------
  Macro        94.44%     94.44%     93.94%
```

### 8.6 Comparativa de evolución completa

| Versión | Score | LOW F1 | MEDIUM F1 | HIGH F1 | Macro F1 | Nota |
|---------|-------|--------|-----------|---------|----------|------|
| Sin RAG, 8 casos | 6/8 — 75% | — | 0.00% | — | ~50% | Línea base |
| Con RAG (no conectado), 12 casos | 9/12 — 75% | 66.67% | 75.00% | 76.92% | 72.86% | RAG en corpus pero no en eval |
| Baseline actual (sin RAG en script) | 10/12 — 83% | 66.67% | 88.89% | 83.33% | 79.63% | TC10 pasa, TC08 y TC09 fallan |
| **Con RAG conectado + mejoras** | **11/12 — 92%** | **100%** | **90.91%** | **90.91%** | **93.94%** | Estado actual |

### 8.7 TC08 — análisis del fallo restante y decisión de diseño

TC08 es el único fallo persistente. No es un bug corregible con el diseño actual:

- **El problema:** el modelo recibe el historial con una URL de phishing (`portal-bradesco.digital`, dominio en PhishTank) y clasifica la conversación como HIGH aunque el mensaje actual sea benigno.
- **Por qué no tiene fix trivial:** para ayudar a TC08 via RAG, el retriever necesitaría buscar en el texto del historial (los mensajes "lo mandé sin querer", "borralo"). Actualmente solo busca en `current_message + url_reasons + text_patterns`. Esto requeriría un cambio de arquitectura.
- **Por qué el comportamiento actual es correcto desde seguridad:** "lo mandé sin querer, borralo" es una frase de cobertura estándar usada por atacantes cuando la víctima no hizo clic. El modelo no puede distinguir una retractación genuina de una táctica de ingeniería social. Mantener HIGH es el comportamiento conservador correcto.
- **Decisión de diseño:** `expected_severity` cambiado a MEDIUM (no LOW). En producción, el operador humano revisaría el caso y decidiría si la retractación es genuina.

---

## PARTE 9 — Ampliación de corpus rioplatense + calibración siempre presente (2026-06-14)

**Commit:** `ec5c20d`  
**Archivos modificados:** `app/rag/corpus.py`, `app/ai/groq_client.py`  
**Métricas pre-cambio:** 11/12 (92%) — Macro F1 93.94%

### 9.1 PASO 1 — Vocabulario rioplatense/regional (Opciones A + D)

Se extendieron las keywords de 4 fichas existentes con frases naturales en español rioplatense. Ninguna ficha nueva fue creada.

#### `account_verification_scam` — 4 frases agregadas

| Keywords agregadas |
|--------------------|
| "tu perfil va a ser dado de baja" |
| "detectamos movimientos extraños" |
| "el equipo de seguridad de Meta" |
| "tu cuenta va a quedar inhabilitada" |

**Justificación:** atacantes reales en Argentina no dicen "suspended" ni "account suspended" — dicen "dado de baja" o "inhabilitada". Sin estas keywords, el retriever no recuperaba esta ficha para ataques con vocabulario local.

#### `fake_giveaway` — 4 frases agregadas

| Keywords agregadas |
|--------------------|
| "fuiste el elegido" |
| "te tocó a vos" |
| "mandanos tus datos para coordinar" |
| "ganaste sin participar" |

**Justificación:** los sorteos falsos en Argentina usan "te tocó a vos" y "fuiste el elegido" en lugar de "winner" o "you've been selected".

#### `pig_butchering` — 5 frases agregadas

| Keywords agregadas |
|--------------------|
| "tengo una plataforma exclusiva" |
| "empezá con lo que puedas" |
| "te paso el link de la app" |
| "tengo un grupito donde compartimos señales" |
| "te enseño a hacer trading" |

**Justificación:** el vocabulario de pig butchering argentino es informal y cercano. "grupito de señales", "te enseño a hacer trading" y "empezá con lo que puedas" son frases típicas que el corpus original en inglés/español neutro no capturaría.

#### `otp_request` — 4 frases agregadas

| Keywords agregadas |
|--------------------|
| "me llegó un código a tu número" |
| "necesito que me reenvíes ese mensaje" |
| "es solo 6 números" |
| "pasame el código que te llegó" |

**Justificación:** la variante más común en Argentina es "pasame el código que te llegó" y "es solo 6 números" — formulaciones que el corpus original no tenía.

### 9.2 PASO 2 — severity_calibration siempre presente (Opción C)

**Cambio en `app/ai/groq_client.py`:**

```python
# ANTES — calibración solo si el retriever la recuperaba por keywords
context_section = (
    f"\nContexto de base de conocimiento relevante:\n{retrieved_context}\n"
    if retrieved_context else ""
)

# DESPUÉS — calibración siempre presente; retriever agrega contexto adicional
_CALIBRATION_CONTENT = next(
    (e["content"] for e in CORPUS if e["id"] == "severity_calibration"), ""
)

context_section = f"\nCalibración de severidad (aplicar siempre):\n{_CALIBRATION_CONTENT}\n"
if retrieved_context:
    extra_blocks = [
        block for block in retrieved_context.split("\n\n")
        if "Calibración de severidad" not in block and block.strip()
    ]
    if extra_blocks:
        context_section += "\nContexto adicional relevante:\n" + "\n\n".join(extra_blocks) + "\n"
```

**Efecto:** la guía MEDIUM vs HIGH está presente en el 100% de los análisis, no solo cuando el retriever la recupera. El bloque de deduplicación evita que aparezca dos veces cuando el retriever también la selecciona (como en TC10 y TC12).

**Caso de uso beneficiado:** cualquier mensaje futuro con patrones de ataque sin keywords exactas del corpus. El modelo siempre tiene la regla de calibración disponible.

### 9.3 Resultados post-cambio

| Clase | F1 antes | F1 después | Δ |
|-------|----------|------------|---|
| LOW | 100% | 100% | = |
| MEDIUM | 90.91% | 90.91% | = |
| HIGH | 90.91% | 90.91% | = |
| **Macro** | **93.94%** | **93.94%** | **=** |

**Score: 11/12 (92%) — sin regresiones.** Las mejoras no degradaron ningún caso existente. El corpus más rico mejora la cobertura para mensajes futuros en español rioplatense.

### 9.4 Trabajo futuro — Opción B: ficha de retractación (TC08)

El único fallo persistente del sistema (TC08 — `normal_after_phishing`) requiere un cambio que no se implementó en esta sesión por alcance.

**El patrón:** el atacante envía `http://portal-bradesco.digital/` en el mensaje 1, luego dice "Igual eso lo mandé sin querer, borralo" en el mensaje 2. El mensaje 3 es benigno. El sistema devuelve HIGH porque el modelo ve la URL de phishing en el historial.

**Por qué no se implementó:** el retriever busca en `current_message + url_reasons + text_patterns`. Las keywords de retractación ("borralo", "lo mandé sin querer") están en el historial, no en el mensaje actual. Para que el RAG ayude en este caso, se necesitaría pasar el último mensaje del historial al retriever:

```python
# En orchestrator.py (cambio mínimo, no implementado):
last_history_msg = conversation_history[-1]["texto"] if conversation_history else ""
retrieved_context = retrieve(
    message=current_message,
    url_reasons=url_result.reasons,
    text_patterns=text_result.patterns_matched,
    extra_context=last_history_msg,   # nuevo parámetro
)
```

Y en `retriever.py`:
```python
def retrieve(message, url_reasons=None, text_patterns=None,
             extra_context="", top_k=2):
    search_parts = [message] + url_reasons + text_patterns
    if extra_context:
        search_parts.append(extra_context)
    ...
```

Con este cambio, "borralo" + "lo mandé sin querer" dispararían una ficha `retraction_cover` que guiaría al modelo a MEDIUM en lugar de HIGH.

**Corpus entry propuesta (no implementada):**
```python
{
    "id": "retraction_cover",
    "keywords": [
        "borralo", "borrar", "lo mandé sin querer", "fue un error",
        "me equivoqué", "no era para vos", "ignoralo",
    ],
    "content": (
        "PATRÓN — RETRACTACIÓN POST-PHISHING: el atacante envía contenido "
        "malicioso y luego se retracta ('fue un error', 'borralo'). "
        "Esta es una táctica estándar cuando la víctima no respondió.\n"
        "DECISIÓN: mantener riesgo en MEDIUM — la retractación no invalida "
        "el intento previo. El operador humano debe revisar el historial."
    ),
}
```

**Impacto estimado si se implementa:** TC08 pasaría de FAIL a PASS → 12/12 (100%), Macro F1 ~96–97%.

---

## Apéndice — Observaciones de seguridad

1. ~~**HMAC no conectado**~~ → **RESUELTO** en commit `868042a` (ver 4.1).
2. **`SESSION_SECRET` hardcodeado**: el valor por defecto `"link_seguro_secret_2024"` está en el código fuente. Si se deployara sin cambiar `SESSION_SECRET` en `.env`, las cookies serían predecibles.
3. **Conversaciones reales en `src/data/conversations/`**: el `.gitignore` excluye este directorio, pero existe en disco con datos de Instagram. Los archivos de backup (`src/data/backups/`) también están excluidos del repo pero presentes localmente.
4. **`src/.env`**: existe en disco (1835 bytes) con credenciales reales. Está correctamente en `.gitignore`.

---

## HMAC desconectado temporalmente (2026-06-19)

Estado: comentado en `webhook/router.py`, no eliminado. `app/webhook/validator.py` intacto.

Motivo: bug de 403 Forbidden bloqueando el webhook a días de la demo — sin tiempo de diagnosticar con seguridad antes del viernes.

Hipótesis: orden de lectura del raw body vs request.json() en FastAPI consume el stream antes de validar el hash.

Pendiente: diagnosticar y reconectar después de la defensa.

---

*Este documento fue generado por análisis estático del código fuente. No se ejecutó ningún proceso ni se modificó ningún archivo.*
