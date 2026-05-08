# Stack Tecnológico — Link Seguro v0.1.0

## 1. Tabla completa de dependencias

Basada en `requirements.txt` real del proyecto.

| Componente | Tecnología | Versión | Rol en el sistema |
|---|---|---|---|
| Framework web | FastAPI | 0.136.1 | Servidor HTTP, routing, BackgroundTasks |
| Servidor ASGI | Uvicorn | 0.46.0 | Servidor de producción con soporte async |
| ASGI toolkit | Starlette | 1.0.0 | Base de FastAPI (Request, Response) |
| Validación de datos | Pydantic | 2.13.3 | Schemas: AnalysisResult, URLResult, TextResult |
| Configuración | pydantic-settings | 2.14.0 | Carga de variables de entorno vía .env |
| Variables de entorno | python-dotenv | 1.2.2 | Soporte para archivo .env |
| Cliente IA | groq | 1.2.0 | API de Groq (LLaMA 3.3 70B) |
| Base de datos | supabase | 2.30.0 | Cliente Python para Supabase PostgreSQL |
| Cliente PostgREST | postgrest | 2.30.0 | ORM ligero sobre la API REST de Supabase |
| HTTP asincrónico | httpx | 0.28.1 | Consultas a URLhaus API (async) |
| HTTP sincrónico | requests | 2.33.1 | Disponible para scripts auxiliares |
| Criptografía | cryptography | 48.0.0 | Soporte HMAC y operaciones criptográficas |
| Logging | (stdlib) | — | `logging` estándar de Python con wrapper en `utils/logger.py` |
| Testing | pytest | 9.0.3 | Suite de tests unitarios |
| Testing async | pytest-asyncio | 1.3.0 | Soporte para tests de corrutinas |
| Loop async | uvloop | 0.22.1 | Event loop de alta performance (reemplaza al de CPython) |
| WebSockets | websockets | 15.0.1 | Dependencia transitiva de Supabase realtime |

---

## 2. Por qué FastAPI sobre Flask

| Criterio | FastAPI | Flask |
|---|---|---|
| Soporte nativo async/await | Sí (primer ciudadano) | Parcial (requiere extensiones) |
| BackgroundTasks integrado | Sí, en el propio framework | No nativo |
| Validación automática | Pydantic integrado | Manual o con extensiones |
| Tipado y autocompletado | Total (type hints) | Limitado |
| Performance | ASGI (comparable a NodeJS) | WSGI (bloqueante) |

El sistema analiza mensajes con I/O intensivo (consultas a URLhaus, Groq, Supabase). FastAPI permite ejecutar estas operaciones de forma no bloqueante con `asyncio.gather` y `asyncio.to_thread`, lo que sería significativamente más complejo con Flask. Además, el mecanismo `BackgroundTasks` es fundamental para responder a Meta en menos de 15 segundos.

---

## 3. Por qué Groq + LLaMA sobre OpenAI

| Criterio | Groq + LLaMA 3.3 70B | OpenAI GPT-4 |
|---|---|---|
| Latencia | Muy baja (hardware LPU especializado) | Mayor latencia en modelos grandes |
| Costo | Plan gratuito disponible | Solo de pago |
| Modelo open source | Sí (Meta LLaMA) | No |
| Razonamiento en español | Excelente (LLaMA 3.3 multilingüe) | Excelente |
| Control de temperatura | Sí (0.1 configurado) | Sí |
| JSON mode | Sí (forzado via prompt) | Sí (nativo) |

La baja latencia de Groq es crítica para el caso de uso: el análisis de IA se ejecuta dentro de un `BackgroundTask` que no debe tardar más de unos segundos. El plan gratuito de Groq cubre el volumen de un prototipo académico sin costo.

---

## 4. Por qué Supabase sobre SQLite o MongoDB

| Criterio | Supabase (PostgreSQL) | SQLite | MongoDB |
|---|---|---|---|
| Acceso remoto | Sí (REST API + SDK) | No (archivo local) | Sí |
| Datos relacionales | Sí, con foreign keys | Sí | No (documentos) |
| SDK Python oficial | Sí (`supabase-py`) | `sqlite3` stdlib | `pymongo` |
| Dashboard web | Sí (visualización y queries) | No | Atlas (pago) |
| Plan gratuito | Sí (500MB, API ilimitada) | N/A | Limitado |
| Escalabilidad | PostgreSQL en producción | No escala | Sí |
| Row Level Security | Sí (built-in) | No | No nativo |

SQLite fue descartado porque el servicio corre en un servidor remoto (Render/Railway) y los datos deben persistir independientemente del proceso. MongoDB fue descartado porque los datos son relacionales: un mensaje pertenece a una conversación, y un resultado de análisis pertenece a un mensaje.

---

## 5. Por qué PhishTank + URLhaus

| Fuente | Tipo | Actualización | Uso en el sistema |
|---|---|---|---|
| PhishTank | CSV local (`data/blacklist/phishtank.csv`) | Manual vía `scripts/update_blacklist.py` | Lookup offline de dominios conocidos como phishing |
| URLhaus (abuse.ch) | API REST en tiempo real | Continua (mantenida por la comunidad) | Verificación online si el score local supera 0.3 |
| `data/blacklist.txt` | Texto plano local | Manual | Blacklist de dominios custom del proyecto |

**Complementariedad de las fuentes:**
- PhishTank es la mayor base de datos de phishing verificado por la comunidad. El lookup es instantáneo porque se hace contra un CSV local cargado en memoria al iniciar.
- URLhaus cubre malware y URLs activas de distribución de exploits. Como la consulta es online (latencia ~300ms), solo se hace cuando el análisis local ya sugiere riesgo (`url_score > 0.3`), minimizando llamadas externas.

---

## 6. Integración con Meta

### Graph API v25.0

La integración usa la **Graph API v25.0** de Meta para recibir eventos de Instagram DMs a través del sistema de webhooks.

### Webhooks

- **Tipo de suscripción**: `messages` (eventos de mensajes entrantes)
- **Verificación**: GET con `hub.mode=subscribe`, `hub.verify_token` y `hub.challenge`
- **Entrega de eventos**: POST con payload JSON firmado con HMAC-SHA256 en el header `X-Hub-Signature-256`

### Instagram Business Login

El flujo de autorización requiere:
1. App de Meta con tipo **Business** o **Consumer**
2. Página de Facebook vinculada a la cuenta de Instagram
3. Token de acceso de página (`PAGE_ACCESS_TOKEN`) con permisos de mensajería
4. La cuenta de Instagram debe ser de tipo **Professional** (Business o Creator)

---

## 7. Stack de seguridad

| Mecanismo | Implementación | Archivo |
|---|---|---|
| Verificación de origen | HMAC-SHA256 sobre el body del request | `app/webhook/validator.py` |
| Comparación segura | `hmac.compare_digest()` (resistente a timing attacks) | `app/webhook/validator.py` |
| Anonimización PII | SHA256 del `sender_id` real, se guarda solo los primeros 12 hex | `app/db/supabase_client.py` |
| `conversation_id` | SHA256 de `sender_id + recipient_id`, primeros 16 hex | `app/db/supabase_client.py` |
| Truncado de contenido | `text_preview = text[:30]` al persistir en analysis_results | `app/db/supabase_client.py` |
| Credenciales | 100% en variables de entorno, nunca hardcodeadas | `app/config.py` |
| Logs privados | Solo se logea `sender_id[-4:]` (últimos 4 dígitos) | `app/webhook/router.py` |
