# Link Seguro — Documentación Técnica

## 1. Descripción del sistema

**Link Seguro** es un sistema de detección automática de phishing en mensajes directos de Instagram que analiza conversaciones completas en tiempo real mediante heurísticas y un modelo de IA generativa institucional.

### Problema que resuelve

Los ataques de phishing distribuidos a través de Instagram DMs crecieron de forma sostenida durante 2023-2024 (APWG eCrime Q4 2024). Las víctimas reciben mensajes aparentemente legítimos que buscan robar credenciales, solicitar OTPs o redirigir hacia sitios fraudulentos. A diferencia del email, no existe infraestructura de filtrado masivo para DMs de redes sociales, y los ataques explotan la confianza inherente a la plataforma social.

### Contexto académico

Trabajo Integrador Final (TIF) — Ingeniería en Sistemas de Información, Universidad de Mendoza. El sistema fue desarrollado como prototipo funcional end-to-end conectado a la API real de Meta.

---

## 2. Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FLUJO COMPLETO                               │
└─────────────────────────────────────────────────────────────────────┘

  [Usuario Instagram]
         │
         │  DM entrante
         ▼
  [Meta Graph API v25.0]
         │
         │  POST /webhook  (HMAC-SHA256 verificado)
         ▼
  ┌─────────────────────────────────────────────────────┐
  │              FastAPI — app/webhook/router.py         │
  │                                                      │
  │  1. Verificar firma Meta (webhook/validator.py)      │
  │  2. Extraer sender_id, text, message_id, timestamp   │
  │  3. save_message() → SQLite (idempotente)            │
  │  4. Encolar análisis en BackgroundTask               │
  │  5. Retornar {"status": "ok"} a Meta inmediatamente  │
  └──────────────────────────┬──────────────────────────┘
                             │ (background)
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │          PhishingOrchestrator — análisis/orchestrator│
  │                                                      │
  │  ┌─────────────────────┐  ┌─────────────────────┐   │
  │  │    URLAnalyzer      │  │    TextAnalyzer      │   │
  │  │                     │  │                      │   │
  │  │ • PhishTank CSV     │  │ • credential_request │   │
  │  │ • blacklist.txt     │  │ • urgency            │   │
  │  │ • URLhaus API RT    │  │ • support_imperson.  │   │
  │  │ • HTTP inseguro     │  │ • fraudulent_offer   │   │
  │  │ • Shorteners        │  │                      │   │
  │  │ • Keywords en URL   │  │  score (0.0–1.0)     │   │
  │  │ • URL muy larga     │  │  peso: 0.4           │   │
  │  │                     │  └─────────────────────┘   │
  │  │  score (0.0–1.0)    │                             │
  │  │  peso: 0.6          │                             │
  │  └─────────────────────┘                             │
  │                                                      │
  │  heuristic_score = url*0.6 + text*0.4                │
  │                                                      │
  │  ┌─────────────────────────────────────────────┐     │
  │  │    UM Cloud — gemma4-26b                    │     │
  │  │    (ai.cloud.um.edu.ar)                     │     │
  │  │                                             │     │
  │  │  Input: historial (≤20 msgs) + heurísticas  │     │
  │  │  Output: JSON con severity, confidence,     │     │
  │  │          categoria, MITRE, Cialdini,        │     │
  │  │          lifecycle, accion, explicaciones   │     │
  │  └─────────────────────────────────────────────┘     │
  │                                                      │
  │  final_score = max(heuristic_score, ia_risk_score)   │
  └──────────────────────────┬──────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │              SQLite — data/phishing_detector.db      │
  │                                                      │
  │  conversacion │ mensaje │ analisis_conversacion       │
  └──────────────────────────┬──────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │     Dashboard — GET /dashboard (HTML auto-refresh)   │
  │     Tabla ordenada HIGH→MEDIUM→LOW con detalle       │
  └─────────────────────────────────────────────────────┘
```

### Descripción de cada componente

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Webhook receiver | `app/webhook/router.py` | Valida firma HMAC, extrae mensajes, persiste y encola análisis |
| Webhook validator | `app/webhook/validator.py` | Verifica `X-Hub-Signature-256` de Meta |
| Orchestrator | `app/analysis/orchestrator.py` | Coordina URL analyzer + Text analyzer + UM Cloud + persistencia |
| URL Analyzer | `app/analysis/url_analyzer.py` | Blacklists PhishTank/local, URLhaus RT, regex de señales |
| Text Analyzer | `app/analysis/text_analyzer.py` | 4 patrones regex con pesos (credential, urgency, impersonation, offer) |
| UM Cloud client | `app/ai/groq_client.py` | Llama a `ai.cloud.um.edu.ar` con `AsyncOpenAI` compatible |
| System prompt | `app/ai/prompts.py` | Prompt especializado con MITRE + APWG + Cialdini |
| Conversation observer | `app/analysis/conversation_observer.py` | Análisis holístico periódico (mensajes 3, 5, 10, luego cada 5) |
| SQLite client | `app/db/sqlite_client.py` | CRUD asíncrono sobre las 3 tablas |
| Dashboard | `app/dashboard/router.py` + `src/templates/` | Jinja2 templates, auto-refresh 30s, sin JS framework |
| Config | `app/config.py` | Variables de entorno via pydantic-settings |

### Por qué se eligió cada tecnología

- **FastAPI**: soporte nativo async/await, BackgroundTasks incorporado, validación con Pydantic, rendimiento superior a Flask en I/O concurrente.
- **SQLite + aiosqlite**: base de datos local embebida, sin servidor, reproducible en cualquier PC con `python database/init_db.py`.
- **UM Cloud (gemma4-26b)**: recurso institucional de la Universidad de Mendoza, API compatible con OpenAI, sin costo de API externa, modelo de 26B parámetros con capacidad de razonamiento complejo.
- **PhishTank CSV + URLhaus**: dos fuentes complementarias — PhishTank provee ~29k dominios verificados por la comunidad, URLhaus confirma en tiempo real si una URL está activa como maliciosa.
- **pydantic-settings**: carga `.env` automáticamente con tipado estricto.

---

## 3. Las 4 capas del sistema

### Capa 1 — Ingesta (Webhook + Meta Graph API)

El endpoint `POST /webhook` recibe el payload de Meta, verifica la firma HMAC-SHA256 con `META_APP_SECRET`, extrae los campos `sender_id`, `recipient_id`, `message_id`, `text` y `timestamp`, filtra mensajes echo (`is_echo=True`) propios de la cuenta monitoreada, persiste el mensaje en SQLite de forma idempotente (`INSERT OR IGNORE`), y retorna `{"status": "ok"}` a Meta antes de 20 segundos (requisito de la plataforma). El análisis corre en background.

El endpoint `GET /webhook` implementa el handshake de verificación de Meta: valida `hub.verify_token` contra la variable de entorno y retorna `hub.challenge`.

### Capa 2 — Motor heurístico

Dos analizadores corren en paralelo (`asyncio.gather`):

**URLAnalyzer** extrae todas las URLs del texto con regex y las evalúa contra:
- `data/blacklist/phishtank.csv`: dominios de phishing verificados por la comunidad (carga en memoria al iniciar)
- `data/blacklist.txt`: lista negra local adicional
- URLhaus API (`https://urlhaus-api.abuse.ch/v1/url/`): consulta en tiempo real solo si el score URL supera 0.3
- Señales adicionales: HTTP inseguro (+0.3), acortador (+0.4), keyword sospechosa en URL (+0.2), URL > 100 chars (+0.2)

**TextAnalyzer** aplica 4 patrones regex con pesos fijos:
- `credential_request` (peso 0.8): solicitud de contraseña, PIN, credenciales
- `support_impersonation` (peso 0.6): soporte de Instagram/Meta, equipo oficial
- `urgency` (peso 0.5): urgente, suspendido, 24 horas, act now
- `fraudulent_offer` (peso 0.5): ganador, premio, gratis, gift card

Score final heurístico: `url_score × 0.6 + text_score × 0.4`

### Capa 3 — IA Generativa (UM Cloud gemma4-26b)

El cliente usa `AsyncOpenAI` apuntando a `https://ai.cloud.um.edu.ar/api/v1` con el modelo `gemma4-26b`. Recibe como input:
- Historial de la conversación (hasta 20 mensajes previos, cada uno truncado a 300 chars)
- El mensaje actual (truncado a 500 chars)
- Los scores heurísticos (url_score, text_score)
- Los indicadores detectados por el heurístico

Parámetros de inferencia: `temperature=0.1` (respuestas deterministas), `max_tokens=2000`.

La respuesta es un JSON con 11 campos incluyendo `severity`, `confidence`, `scam_category`, `mitre_technique`, `cialdini_principles`, `lifecycle_stage`, `recommended_action`, `explanation_user` (español, ≤280 chars), `explanation_analyst` (inglés técnico, ≤500 chars).

Fusión de scores: `final_score = max(heuristic_score, severity_to_score[ai_risk] × confidence)` donde `severity_to_score = {LOW: 0.15, MEDIUM: 0.55, HIGH: 0.90}`. Este diseño evita que la IA infle el score cuando dice LOW con alta confianza.

**Conversation observer**: módulo adicional que reanáliza la conversación completa en los mensajes 3, 5, 10, luego cada 5 mensajes, y en cualquier escalada de riesgo. Persiste el resultado en `risk_level_conversacion` de la tabla `conversacion`.

### Capa 4 — Persistencia y visualización

SQLite con 3 tablas relacionadas (ver sección de base de datos). El dashboard en `GET /dashboard` usa Jinja2 templates (`src/templates/`) con auto-refresh cada 30 segundos. Muestra tarjetas de resumen (total, HIGH, MEDIUM, LOW, último análisis) y una tabla ordenada por severidad. Cada fila es expandible para ver explicaciones, principios de Cialdini, URLs sospechosas e historial de los últimos 10 mensajes. En vista admin, la columna "Usuario" incluye `↳ @cuenta` para identificar a qué cuenta monitoreada pertenece cada conversación.

---

## 4. Decisiones de diseño

### FastAPI sobre Flask
FastAPI soporta `async/await` de forma nativa, lo que permite que el webhook retorne inmediatamente a Meta mientras el análisis corre en background. Flask requiere workers externos (Celery) para lograr lo mismo. Además, `BackgroundTasks` de FastAPI es suficiente para el volumen de un TIF sin agregar dependencias.

### SQLite local sobre Supabase
Decisión tomada por el tutor durante el desarrollo (versión anterior usó Supabase). SQLite local garantiza reproducibilidad completa: cualquier evaluador puede clonar el repo, ejecutar `python database/init_db.py` y tener el sistema funcionando sin cuentas externas. La base puede inspeccionarse directamente con `sqlite3`. Para producción a escala se migraría a PostgreSQL.

### UM Cloud sobre Groq o OpenAI
UM Cloud es un recurso institucional de la Universidad de Mendoza disponible para estudiantes e investigadores. No tiene costo de API, la API es compatible con el SDK de OpenAI (misma interfaz), y permite usar el modelo más grande disponible sin restricciones de créditos. Usar un recurso propio de la universidad también tiene valor académico.

### gemma4-26b como modelo principal
Es el modelo de mayor capacidad disponible en UM Cloud al momento del desarrollo. Con 26B parámetros tiene capacidad suficiente para razonamiento complejo sobre patrones de ingeniería social, seguimiento del lifecycle conversacional y generación de explicaciones en español.

### PhishTank + URLhaus como fuentes complementarias
PhishTank provee una base de conocimiento histórica amplia (~29k dominios verificados por la comunidad). URLhaus complementa con verificación en tiempo real del estado activo de una URL maliciosa. Ninguna fuente por sí sola es suficiente: PhishTank puede tener URLs caídas, URLhaus puede no conocer dominios nuevos.

### Análisis conversacional completo
El sistema no analiza mensajes aislados sino el historial completo (hasta 50 mensajes en SQLite, hasta 20 enviados al modelo). Los ataques de ingeniería social operan en fases: la primera interacción suele ser inofensiva (approach/bond) y el gancho aparece después. Sin contexto histórico, los primeros mensajes de un ataque siempre clasificarían como LOW.

### BackgroundTasks para no bloquear el webhook
Meta requiere respuesta del webhook en menos de 20 segundos o reintenta el evento. El análisis completo (heurístico + URLhaus + UM Cloud) puede tomar varios segundos. BackgroundTasks permite retornar `{"status": "ok"}` inmediatamente y procesar en segundo plano, evitando reenvíos duplicados.

---

## 5. Flujo detallado de un mensaje de phishing

```
1. LLEGADA
   Usuario externo envía DM a la cuenta monitoreada.
   Meta entrega el evento a POST /webhook con payload JSON.

2. VALIDACIÓN
   webhook/validator.py verifica X-Hub-Signature-256
   usando HMAC-SHA256(META_APP_SECRET, body).
   Si falla → HTTP 403.

3. EXTRACCIÓN
   Se parsea sender_id, recipient_id, message_id, text,
   timestamp. Se filtra is_echo=True (mensajes propios).

4. PERSISTENCIA INMEDIATA
   save_message() calcula id_conversacion = SHA256(sender+recipient)[:16].
   INSERT OR IGNORE en tabla mensaje (idempotente ante reenvíos de Meta).
   UPSERT en tabla conversacion (incrementa total_mensajes si es nuevo).

5. RESPUESTA A META
   Se retorna {"status": "ok"} inmediatamente.
   El análisis se encola como BackgroundTask.

6. ANÁLISIS HEURÍSTICO (background, paralelo)
   URLAnalyzer extrae URLs con regex.
   Verifica contra PhishTank CSV + blacklist.txt (en memoria).
   Evalúa HTTP inseguro, shorteners, keywords, longitud.
   TextAnalyzer aplica 4 patrones regex sobre el texto.
   Ambos corren en paralelo con asyncio.gather().

7. URLHAUS (condicional)
   Si url_score > 0.3 y hay URLs detectadas:
   Se consulta URLhaus API en tiempo real para cada URL.
   Si query_status == "is_online" → url_score = min(score + 0.9, 1.0).

8. SCORE HEURÍSTICO
   heuristic_score = url_score * 0.6 + text_score * 0.4
   Umbral HIGH >= 0.7, MEDIUM >= 0.4

9. ANÁLISIS IA (UM Cloud gemma4-26b)
   Se recupera historial de la conversación (hasta 50 msgs de SQLite,
   excluye el mensaje actual para no duplicarlo en el prompt).
   Se envían los últimos 20 mensajes al modelo.
   El system prompt guía análisis chain-of-thought:
   identidad → lingüística → URLs → acción solicitada → lifecycle.
   El modelo retorna JSON con severity, confidence, categoria, etc.

10. FUSIÓN DE SCORES
    ai_risk_score = severity_map[ai_severity] × confidence
    final_score = max(heuristic_score, ai_risk_score)
    risk_level = max(heuristic_risk, ai_risk) por orden HIGH>MEDIUM>LOW

11. PERSISTENCIA DEL ANÁLISIS
    save_analysis_result() inserta en analisis_conversacion con todos
    los campos del análisis.
    UPDATE conversacion SET risk_level_actual = risk_level.

12. CONVERSATION OBSERVER (condicional)
    Si total_mensajes ∈ {3,5,10} o total>10 y múltiplo de 5,
    o si hubo escalada de riesgo:
    Se lanza un segundo análisis holístico con toda la conversación.
    Resultado guardado en risk_level_conversacion de conversacion.

13. LOGGING
    HIGH → logger.warning() con sender truncado, score, categoria, lifecycle.
    MEDIUM → logger.warning() con score.
    LOW → logger.info().

14. DASHBOARD
    GET /dashboard consulta SQLite, genera HTML con filas ordenadas
    HIGH→MEDIUM→LOW. Fila expandible muestra: explicación usuario,
    explicación analista, principios Cialdini, URLs sospechosas,
    últimos 10 mensajes. Auto-refresh cada 30 segundos.
```

---

## 6. Stack tecnológico completo

| Componente | Tecnología | Versión | Justificación |
|---|---|---|---|
| Framework web | FastAPI | ≥0.110 | Async nativo, BackgroundTasks, Pydantic integrado |
| Servidor ASGI | Uvicorn | ≥0.29 | Servidor de producción para FastAPI |
| IA generativa | UM Cloud gemma4-26b | API v1 | Recurso institucional UM, sin costo, 26B parámetros |
| Cliente IA | openai (AsyncOpenAI) | ≥1.x | Compatibilidad con endpoint UM Cloud |
| Base de datos | SQLite + aiosqlite | 3.x / ≥0.20 | Local, embebida, sin servidor, async |
| Config | pydantic-settings | ≥2.x | Carga .env con tipado y validación |
| HTTP cliente | httpx | ≥0.27 | Consultas async a URLhaus API |
| Blacklist histórica | PhishTank CSV | Dataset ~29k dominios | Fuente comunitaria verificada |
| Blacklist tiempo real | URLhaus API | abuse.ch v1 | Verificación estado activo de URLs |
| Túnel desarrollo | ngrok | ≥3.x | Expone localhost a Meta Webhook |
| Logging | Python logging | stdlib | Logger jerárquico por módulo |
| Runtime | Python | 3.10+ | Async/await, match, type hints modernos |
