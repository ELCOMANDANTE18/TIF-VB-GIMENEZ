# Base de Datos — Supabase PostgreSQL

## 1. Tablas del sistema

### Tabla `conversations`

Registro de cada conversación única entre un usuario de Instagram y la cuenta monitoreada.

| Campo | Tipo PostgreSQL | Descripción |
|---|---|---|
| `conversation_id` | `text` PRIMARY KEY | SHA256(sender_id + recipient_id)[:16] — identificador único de la conversación |
| `ig_user_id` | `text` | ID de la cuenta de Instagram monitoreada (recipient) |
| `participant_id` | `text` | SHA256(sender_id)[:12] — hash del ID del participante externo |
| `updated_at` | `timestamptz` | Última actualización en UTC (se actualiza en cada upsert) |

---

### Tabla `messages`

Registro de cada mensaje individual recibido por el webhook.

| Campo | Tipo PostgreSQL | Descripción |
|---|---|---|
| `message_id` | `text` PRIMARY KEY | ID único del mensaje provisto por Meta (`mid`) |
| `conversation_id` | `text` FK → conversations | Referencia a la conversación padre |
| `sender_id` | `text` | ID real del emisor (tal como llega de Meta) |
| `sender_id_hash` | `text` | SHA256(sender_id)[:12] — versión anonimizada para logs y análisis |
| `recipient_id` | `text` | ID de la cuenta monitoreada |
| `text` | `text` | Contenido completo del mensaje |
| `timestamp` | `bigint` | Unix timestamp en milisegundos (provisto por Meta) |

> **Nota**: `sender_id` se guarda en texto plano en esta tabla para permitir correlación si fuera necesario. La decisión de anonimizarlo más agresivamente (como en `analysis_results`) queda para una versión futura con RLS activado.

---

### Tabla `analysis_results`

Resultado de cada ejecución del motor de análisis sobre un mensaje.

| Campo | Tipo PostgreSQL | Descripción |
|---|---|---|
| `id` | `bigint` SERIAL PRIMARY KEY | Autogenerado por Supabase |
| `message_id` | `text` FK → messages | Mensaje que fue analizado |
| `conversation_id` | `text` FK → conversations | Conversación a la que pertenece |
| `sender_id_hash` | `text` | SHA256(sender_id)[:12] — siempre anonimizado en resultados |
| `text_preview` | `text` | Primeros 30 caracteres del texto analizado |
| `final_score` | `float8` | Score final (0.0 a 1.0) combinando heurística + Groq |
| `risk_level` | `text` | Nivel de riesgo: `"LOW"`, `"MEDIUM"` o `"HIGH"` |
| `urls_found` | `text[]` | Array de URLs detectadas en el mensaje |
| `reasons` | `text[]` | Array de razones del score (de URLAnalyzer + TextAnalyzer) |
| `urlhaus_checked` | `boolean` | Si se consultó URLhaus para este análisis |
| `created_at` | `timestamptz` | Timestamp de inserción (autogenerado por Supabase) |

---

## 2. Diagrama de relaciones entre tablas

```
┌─────────────────────────────────┐
│          conversations          │
├─────────────────────────────────┤
│ conversation_id  TEXT  PK       │◄──────────────┐
│ ig_user_id       TEXT           │               │
│ participant_id   TEXT           │               │
│ updated_at       TIMESTAMPTZ    │               │
└─────────────────────────────────┘               │
                                                  │
┌─────────────────────────────────┐               │
│            messages             │               │
├─────────────────────────────────┤               │
│ message_id       TEXT  PK       │◄──────┐       │
│ conversation_id  TEXT  FK ──────┼───────┼───────┘
│ sender_id        TEXT           │       │
│ sender_id_hash   TEXT           │       │
│ recipient_id     TEXT           │       │
│ text             TEXT           │       │
│ timestamp        BIGINT         │       │
└─────────────────────────────────┘       │
                                          │
┌─────────────────────────────────┐       │
│         analysis_results        │       │
├─────────────────────────────────┤       │
│ id               BIGINT  PK     │       │
│ message_id       TEXT  FK ──────┼───────┘
│ conversation_id  TEXT  FK ──────┼──────────────► conversations
│ sender_id_hash   TEXT           │
│ text_preview     TEXT           │
│ final_score      FLOAT8         │
│ risk_level       TEXT           │
│ urls_found       TEXT[]         │
│ reasons          TEXT[]         │
│ urlhaus_checked  BOOLEAN        │
│ created_at       TIMESTAMPTZ    │
└─────────────────────────────────┘
```

---

## 3. Por qué se eligió Supabase

| Criterio | Justificación |
|---|---|
| PostgreSQL real | Los datos son relacionales: mensaje → conversación → resultado. Un sistema de documentos sería forzado. |
| SDK Python oficial | `supabase-py` provee un cliente con métodos `.table().upsert().execute()` sin necesidad de escribir SQL raw. |
| Acceso remoto nativo | El servicio FastAPI corre en un servidor separado del cliente. Supabase expone la base de datos vía REST API autenticada. |
| Dashboard visual | Permite inspeccionar las tablas, ejecutar queries y monitorear inserciones sin herramientas adicionales. |
| Plan gratuito generoso | 500MB de storage y API ilimitada cubre holgadamente el volumen de un prototipo académico. |
| Row Level Security | PostgreSQL nativo, listo para activar cuando se requiera control de acceso granular. |

---

## 4. Cómo se genera el `conversation_id`

Archivo: `app/db/supabase_client.py`

```python
def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

conversation_id = _sha256(sender_id + recipient_id)[:16]
```

**Propiedades del diseño**:
- **Determinístico**: la misma combinación de sender + recipient siempre produce el mismo ID.
- **Compacto**: 16 caracteres hex (64 bits de entropía) son suficientes para identificar conversaciones únicas en el volumen del prototipo.
- **Consistente ante reintentos**: si Meta reenvía el mismo evento, `save_message()` hace upsert y no crea duplicados.
- **Sin colisiones en la práctica**: SHA256 tiene una probabilidad de colisión de 1 en 2^64 para 16 caracteres hex.

---

## 5. Por qué se anonimiza el `sender_id`

El `sender_id` es el ID numérico real de un usuario de Instagram, clasificado como **PII (Personally Identifiable Information)** bajo GDPR y legislaciones de privacidad similares.

**Estrategia adoptada**:

```python
sender_id_hash = _sha256(sender_id)[:12]
```

- El hash es **unidireccional**: no es posible recuperar el `sender_id` original a partir del hash.
- Los primeros **12 caracteres hex** (48 bits) son suficientes para correlacionar todos los mensajes de un mismo usuario dentro del sistema.
- En los **logs** solo se imprime `sender_id[-4:]` (los últimos 4 dígitos) para depuración sin exponer el ID completo.
- En `analysis_results`, el `sender_id` real nunca se persiste — solo el hash.

---

## 6. Índices creados y por qué

Los índices de Supabase se configuran en el dashboard o mediante migraciones SQL.

| Tabla | Campo indexado | Tipo | Justificación |
|---|---|---|---|
| `messages` | `message_id` | PRIMARY KEY (automático) | Lookup O(log n) en upsert idempotente por `message_id` |
| `conversations` | `conversation_id` | PRIMARY KEY (automático) | Lookup O(log n) en upsert por `conversation_id` |
| `messages` | `conversation_id` | B-tree recomendado | `get_conversation_history()` filtra por este campo con `.eq("conversation_id", ...)` |
| `analysis_results` | `message_id` | B-tree recomendado | Correlación entre mensaje y resultado de análisis |
| `analysis_results` | `risk_level` | B-tree recomendado | Consultas futuras filtrando por nivel de riesgo |

---

## 7. Cómo configurar el proyecto desde cero

### Paso 1 — Crear proyecto en Supabase

1. Ir a [supabase.com](https://supabase.com) y crear un nuevo proyecto.
2. Anotar la **Project URL** y la **anon/public key** desde **Settings → API**.

### Paso 2 — Variables de entorno

```env
SUPABASE_URL=https://{PROJECT_REF}.supabase.co
SUPABASE_KEY={ANON_PUBLIC_KEY}
```

### Paso 3 — Crear las tablas

Ejecutar en el **SQL Editor** de Supabase:

```sql
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    ig_user_id      TEXT NOT NULL,
    participant_id  TEXT NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    message_id      TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
    sender_id       TEXT NOT NULL,
    sender_id_hash  TEXT NOT NULL,
    recipient_id    TEXT NOT NULL,
    text            TEXT NOT NULL,
    timestamp       BIGINT NOT NULL
);

CREATE TABLE analysis_results (
    id               BIGSERIAL PRIMARY KEY,
    message_id       TEXT NOT NULL REFERENCES messages(message_id),
    conversation_id  TEXT NOT NULL REFERENCES conversations(conversation_id),
    sender_id_hash   TEXT NOT NULL,
    text_preview     TEXT,
    final_score      FLOAT8 NOT NULL,
    risk_level       TEXT NOT NULL,
    urls_found       TEXT[],
    reasons          TEXT[],
    urlhaus_checked  BOOLEAN NOT NULL DEFAULT false,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices recomendados
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_analysis_results_message_id ON analysis_results(message_id);
CREATE INDEX idx_analysis_results_risk_level ON analysis_results(risk_level);
```

---

## 8. Row Level Security — Estado actual y consideraciones

### Estado actual

RLS **no está activado** en la v0.1.0. El acceso a las tablas se controla únicamente a través de la `SUPABASE_KEY` (anon key) configurada en variables de entorno.

### Consideraciones para activarlo

Si se activa RLS, se deben crear políticas explícitas para que el servicio pueda leer y escribir:

```sql
-- Habilitar RLS en cada tabla
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;

-- Política de ejemplo: el service role puede hacer todo
CREATE POLICY "service_role_all" ON conversations
    FOR ALL USING (auth.role() = 'service_role');
```

> Para usar RLS con el backend, se debe reemplazar la `anon key` por la **`service_role` key** en la variable `SUPABASE_KEY`. La `service_role` key bypasea RLS y debe mantenerse **estrictamente privada** (nunca en el frontend).

### Recomendación futura

Activar RLS y usar la `service_role` key en el backend para seguir el principio de menor privilegio, especialmente si el proyecto escala a múltiples usuarios o se expone una interfaz de administración.
