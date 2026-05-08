# Arquitectura del Sistema — Link Seguro v0.1.0

## 1. Descripción general

**Link Seguro** es un sistema de detección de phishing e ingeniería social en tiempo real para Instagram DMs. Recibe mensajes a través del webhook de Meta, los analiza con un motor heurístico multicapa y con IA generativa (Groq), y persiste los resultados en Supabase PostgreSQL.

El sistema está diseñado para funcionar de forma **asincrónica**: el webhook responde inmediatamente con `{"status": "ok"}` y el análisis se ejecuta en segundo plano (`BackgroundTasks`), garantizando que Meta no reintente el envío por timeout.

---

## 2. Diagrama ASCII — Flujo completo

```
Instagram DM (usuario envía mensaje)
         │
         ▼
┌─────────────────────┐
│   Meta Webhook      │  POST /webhook
│   (Graph API v25.0) │──────────────────────────────────────────┐
└─────────────────────┘                                           │
                                                                  ▼
                                               ┌─────────────────────────────┐
                                               │   FastAPI — router.py       │
                                               │                             │
                                               │  1. Parsea payload JSON     │
                                               │  2. Ignora is_echo=True     │
                                               │  3. save_message()          │──► Supabase
                                               │  4. BackgroundTask ──────── │
                                               │  5. Retorna {"status":"ok"} │
                                               └──────────────┬──────────────┘
                                                              │ (background)
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │  PhishingOrchestrator       │
                                               │                             │
                                               │  ┌──────────┐ ┌──────────┐ │
                                               │  │URL       │ │Text      │ │
                                               │  │Analyzer  │ │Analyzer  │ │
                                               │  │(asyncio) │ │(asyncio) │ │
                                               │  └────┬─────┘ └────┬─────┘ │
                                               │       └──────┬──────┘       │
                                               │              │ score > 0.3? │
                                               │              ▼              │
                                               │       URLhaus API           │
                                               │       (si hay URLs)         │
                                               │              │              │
                                               │              ▼              │
                                               │    heuristic_score =        │
                                               │    url*0.6 + text*0.4       │
                                               │              │              │
                                               │              ▼              │
                                               │  ┌───────────────────────┐  │
                                               │  │  Groq LLaMA 3.3 70B   │  │
                                               │  │  + historial Supabase │  │
                                               │  └──────────┬────────────┘  │
                                               │             │               │
                                               │             ▼               │
                                               │  final_score = max(         │
                                               │    heuristic, groq_conf)    │
                                               │  risk_level = max(          │
                                               │    heurístico, groq_risk)   │
                                               └──────────────┬──────────────┘
                                                              │
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │  Supabase PostgreSQL        │
                                               │  save_analysis_result()     │
                                               └──────────────┬──────────────┘
                                                              │
                                                              ▼
                                               ┌─────────────────────────────┐
                                               │  Logger (structured)        │
                                               │  🔴 HIGH | 🟡 MEDIUM | 🟢 LOW │
                                               └─────────────────────────────┘
```

---

## 3. Las 4 capas del sistema

### Capa 1 — Ingesta (Webhook + Meta API)

| Archivo | Responsabilidad |
|---|---|
| `app/webhook/router.py` | Recibe y parsea eventos de Meta |
| `app/webhook/validator.py` | Verifica firma HMAC-SHA256 |
| `app/config.py` | Gestiona credenciales vía variables de entorno |

- **GET /webhook**: responde al desafío de verificación de Meta comparando `hub.verify_token` contra `META_VERIFY_TOKEN`.
- **POST /webhook**: itera sobre `entry[].messaging[]`, filtra mensajes de eco (`is_echo=True`), persiste el mensaje en Supabase y delega el análisis a `BackgroundTasks`.
- Los campos extraídos por evento son: `sender_id`, `recipient_id`, `message_id`, `text`, `timestamp`.

### Capa 2 — Motor heurístico (PhishTank + URLhaus + Regex)

| Archivo | Responsabilidad |
|---|---|
| `app/analysis/orchestrator.py` | Coordina el análisis completo |
| `app/analysis/url_analyzer.py` | Analiza URLs con blacklists y URLhaus |
| `app/analysis/text_analyzer.py` | Analiza texto con patrones regex |

- `URLAnalyzer` y `TextAnalyzer` se ejecutan **en paralelo** vía `asyncio.gather`.
- Si `url_score > 0.3` y hay URLs detectadas, se consulta la API de URLhaus en tiempo real.
- La fórmula de score heurístico es: `url_score × 0.6 + text_score × 0.4`.

### Capa 3 — IA Generativa (Groq LLaMA 3.3 70B)

| Archivo | Responsabilidad |
|---|---|
| `app/ai/groq_client.py` | Cliente asincrónico de Groq |
| `app/ai/prompts.py` | System prompt del modelo |

- Recibe el historial de los últimos 10 mensajes de la conversación desde Supabase para análisis contextual.
- El modelo retorna JSON estructurado con `risk_level`, `confidence`, `explanation` y `recommendation`.
- `final_score = max(heuristic_score, groq_confidence)`.
- `risk_level = max(nivel heurístico, nivel Groq)` — siempre se toma el más severo.
- Si Groq falla (timeout, error de red, JSON inválido), el sistema continúa con el score heurístico (fallback silencioso).

### Capa 4 — Persistencia (Supabase PostgreSQL)

| Archivo | Responsabilidad |
|---|---|
| `app/db/supabase_client.py` | Todas las operaciones de base de datos |

- **Tabla `conversations`**: upsert por `conversation_id` (evita duplicados).
- **Tabla `messages`**: upsert por `message_id` (idempotente ante reintentos de Meta).
- **Tabla `analysis_results`**: insert de cada resultado de análisis.
- El `sender_id` real **nunca se persiste en texto plano**: se hashea con SHA256 (primeros 12 caracteres) antes de guardar.

---

## 4. Endpoints disponibles

| Método | Ruta | Descripción | Autenticación |
|---|---|---|---|
| `GET` | `/health` | Health check del servicio | Ninguna |
| `GET` | `/webhook` | Verificación del webhook de Meta | `hub.verify_token` |
| `POST` | `/webhook` | Recepción de eventos de Instagram | Firma HMAC-SHA256 (disponible en `validator.py`) |

---

## 5. Flujo detallado de un mensaje

```
1. Usuario de Instagram envía DM con una URL sospechosa

2. Meta Graph API entrega el evento vía POST /webhook
   Payload: {"entry": [{"messaging": [{
     "sender": {"id": "123456789"},
     "recipient": {"id": "{IG_USER_ID}"},
     "message": {"mid": "m_abc123", "text": "Ganaste! Entrá a http://login-prize.ml"},
     "timestamp": 1746700000
   }]}]}

3. router.py extrae los campos y verifica is_echo=False

4. save_message() ejecuta:
   - conversation_id = SHA256("123456789" + "{IG_USER_ID}")[:16]
   - sender_id_hash  = SHA256("123456789")[:12]
   - UPSERT en conversations (conversation_id, ig_user_id, participant_id, updated_at)
   - UPSERT en messages (message_id, conversation_id, sender_id, sender_id_hash, text, timestamp)
   - Retorna conversation_id

5. BackgroundTask ejecuta _analyze_and_log():

   5a. URLAnalyzer.analyze("Ganaste! Entrá a http://login-prize.ml")
       → detecta URL: http://login-prize.ml
       → http:// → +0.3 (insecure)
       → keyword "login" → +0.2
       → url_score = 0.5

   5b. TextAnalyzer.analyze("Ganaste! Entrá a ...")
       → match "fraudulent_offer" (ganaste, ganador) → +0.5
       → text_score = 0.5

   5c. url_score (0.5) > 0.3 → consulta URLhaus API
       → si query_status == "is_online" → url_score = min(0.5 + 0.9, 1.0) = 1.0

   5d. heuristic_score = 1.0 × 0.6 + 0.5 × 0.4 = 0.8

   5e. risk_level heurístico = HIGH (>= 0.7)

   5f. get_conversation_history(conversation_id, limit=10) → últimos mensajes

   5g. groq_client.analyze_conversation() → llama-3.3-70b-versatile
       → retorna {"risk_level": "HIGH", "confidence": 0.92, "explanation": "...", ...}

   5h. final_score = max(0.8, 0.92) = 0.92
       risk_level = max(HIGH, HIGH) = HIGH

   5i. save_analysis_result() → INSERT en analysis_results
       (message_id, conversation_id, sender_id_hash, text_preview[:30],
        final_score=0.92, risk_level="HIGH", urls_found, reasons, urlhaus_checked=True)

   5j. Logger: "🔴 HIGH RISK detectado | sender=...6789 score=0.92"
```

---

## 6. Decisiones de arquitectura

| Decisión | Justificación |
|---|---|
| Análisis en `BackgroundTasks` | Meta requiere respuesta en < 15s o reintenta; el análisis puede tardar más por Groq y URLhaus |
| `asyncio.gather` para URL + Text | Ambos analizadores son independientes; correr en paralelo reduce latencia total |
| `asyncio.to_thread` para Supabase | El cliente `supabase-py` es sincrónico; envolverlo evita bloquear el event loop |
| Upsert idempotente en messages | Meta puede reenviar el mismo evento ante fallo; el `upsert` por `message_id` previene duplicados |
| SHA256 para sender_id | Anonimización de PII: permite correlacionar mensajes de la misma persona sin exponer el ID real |
| `conversation_id` como hash corto | `SHA256(sender+recipient)[:16]` es determinístico, compacto y consistente entre reintentos |
| Fallback silencioso de Groq | Si la IA no responde, el sistema opera con el motor heurístico; nunca bloquea la cadena |
| `final_score = max(heurístico, groq)` | Se toma la señal de mayor riesgo para minimizar falsos negativos |

---

## 7. Limitaciones conocidas de la v0.1.0

| Limitación | Descripción |
|---|---|
| Sin respuesta automática al usuario | El sistema detecta pero no envía alertas de vuelta al DM |
| `verify_signature` no se aplica en el router | La función existe en `validator.py` pero no está conectada al POST del webhook |
| `SLACK_WEBHOOK_URL` configurado pero sin uso | La variable existe en `config.py` pero no hay código que la invoque |
| PhishTank depende de CSV local | El archivo `data/blacklist/phishtank.csv` debe actualizarse manualmente (existe `scripts/update_blacklist.py`) |
| Modo desarrollo de Meta | Solo cuentas añadidas como evaluadoras pueden enviar DMs al webhook |
| `text_preview` truncado a 30 caracteres | Para anonimización parcial del contenido persistido |
| Sin rate limiting | No hay protección contra flood de eventos en el endpoint POST /webhook |
