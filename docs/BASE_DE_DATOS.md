# Link Seguro — Documentación de Base de Datos

## 1. Decisión de usar SQLite local

### Por qué local vs. nube

La versión anterior del sistema (v0.1) usó Supabase como backend de persistencia. Por indicación del tutor, se migró a SQLite local por las siguientes razones:

- **Reproducibilidad completa**: cualquier evaluador puede clonar el repositorio y ejecutar `python database/init_db.py` sin configurar ninguna cuenta externa. La base queda en `data/phishing_detector.db`.
- **Eliminación de dependencias externas**: sin Supabase no hay SUPABASE_URL ni SUPABASE_KEY en el `.env`. El sistema arranca con solo las variables de Meta y UM Cloud.
- **Inspección directa**: la BD puede inspeccionarse con `sqlite3 data/phishing_detector.db` desde la terminal, sin herramientas adicionales.
- **Apropiado para la escala del TIF**: el volumen de mensajes de un prototipo académico no justifica la complejidad operativa de una BD en la nube.

Las variables de Supabase permanecen comentadas en `app/config.py` y el módulo `app/db/supabase_client.py` existe pero no es invocado por ningún módulo activo.

### Por qué SQLite vs. PostgreSQL o MongoDB

- vs. **PostgreSQL**: PostgreSQL requiere un servidor corriendo. SQLite es serverless; el archivo ES la base de datos. Para un prototipo con un único proceso de escritura, SQLite es suficiente y más simple.
- vs. **MongoDB**: el modelo de datos del sistema es inherentemente relacional (conversación → mensajes → análisis). Un esquema SQL con FK y constraints es más apropiado que documentos anidados. Además, SQLite soporta `asyncio` via `aiosqlite`.

### Cómo se crea en una PC nueva

```bash
python database/init_db.py
```

Este script:
1. Crea el directorio `data/` si no existe (`DB_PATH.parent.mkdir(exist_ok=True)`)
2. Ejecuta `database/schema.sql` con `conn.executescript()`
3. Aplica migraciones idempotentes para columnas nuevas (función `_apply_migrations`)
4. Confirma con `Base de datos lista en data/phishing_detector.db`

---

## 2. Las 3 tablas con todos sus campos

### Tabla `conversacion`

Unidad central del sistema. Representa el canal de comunicación entre la cuenta monitoreada y un participante externo.

| Campo | Tipo | Descripción | Justificación |
|---|---|---|---|
| `id_conversacion` | TEXT PK | SHA256(sender_id + recipient_id)[:16] — 16 hex chars | Identificador determinista y estable derivado de los actores |
| `ig_conversation_id` | TEXT | ID de conversación asignado por Meta (cuando disponible) | Permite correlacionar con la API de Meta si se necesita |
| `cuenta_monitoreada` | TEXT NOT NULL | `recipient_id`: el Instagram ID de la cuenta monitoreada | Identifica qué cuenta está siendo protegida |
| `participante_id` | TEXT NOT NULL | `sender_id`: el Instagram ID del participante externo | ID real de la cuenta que envía mensajes |
| `participante_username` | TEXT | @username del participante (cuando la API lo provee) | Legibilidad en el dashboard |
| `risk_level_actual` | TEXT | `LOW` / `MEDIUM` / `HIGH` — nivel actual de riesgo | Se actualiza con cada análisis; refleja el estado más reciente |
| `risk_level_conversacion` | TEXT | Nivel de riesgo holístico del conversation observer | Evaluación global del riesgo acumulado de toda la conversación |
| `total_mensajes` | INTEGER | Contador de mensajes procesados | Determina cuándo disparar el conversation observer |
| `primer_mensaje_at` | DATETIME | Timestamp UTC del primer mensaje | Permite analizar duración del ataque |
| `ultimo_mensaje_at` | DATETIME | Timestamp UTC del mensaje más reciente | Ordenamiento en el dashboard |
| `observado_at` | DATETIME | Cuándo corrió el conversation observer por última vez | Trazabilidad de análisis holísticos |
| `creada_at` | DATETIME | Timestamp de inserción en la BD | Auditoría |

**Constraints**: `risk_level_actual` y `risk_level_conversacion` tienen `CHECK IN ('LOW','MEDIUM','HIGH')`. Índice en `risk_level_actual` para el query del dashboard.

### Tabla `mensaje`

Almacena cada mensaje individual recibido o enviado en la conversación monitoreada.

| Campo | Tipo | Descripción | Justificación |
|---|---|---|---|
| `id_mensaje` | TEXT PK | `mid` (message ID) asignado por Meta | La PK de Meta garantiza unicidad e idempotencia |
| `id_conversacion` | TEXT FK → conversacion | FK a la conversación contenedora | Relación N:1 con conversacion |
| `sender_id` | TEXT NOT NULL | Instagram ID de quien envió el mensaje | Necesario para distinguir dirección del mensaje |
| `es_entrante` | BOOLEAN | `1` = mensaje recibido, `0` = mensaje enviado por la cuenta | Permite filtrar por dirección en el historial |
| `texto` | TEXT | Contenido textual del mensaje | El objeto central del análisis |
| `urls_detectadas` | TEXT | JSON array de URLs encontradas en el texto (default `[]`) | Caché para no re-extraer URLs en análisis sucesivos |
| `timestamp_ig` | INTEGER | Epoch milliseconds del timestamp de Meta | Ordenamiento cronológico exacto |
| `recibido_at` | DATETIME | Timestamp de inserción en la BD | Distingue timestamp de Meta vs. timestamp de procesamiento |

**Notas de implementación**: `INSERT OR IGNORE` garantiza idempotencia — si Meta reenvía el mismo evento, la segunda inserción es silenciosa. El flag `is_new = cursor.rowcount > 0` controla si se incrementa `total_mensajes` en la conversación.

### Tabla `analisis_conversacion`

Registro de cada análisis ejecutado. Una conversación puede tener múltiples análisis (uno por mensaje + análisis del conversation observer).

| Campo | Tipo | Descripción | Justificación |
|---|---|---|---|
| `id_analisis` | INTEGER PK AUTOINCREMENT | Clave primaria autonumérica | Unicidad simple para análisis múltiples |
| `id_conversacion` | TEXT FK → conversacion | Conversación analizada | Relación N:1 |
| `id_mensaje_disparador` | TEXT FK → mensaje | Mensaje que disparó este análisis | Trazabilidad: qué mensaje gatilló el análisis |
| `mensajes_analizados` | INTEGER | Cuántos mensajes del historial se incluyeron en el análisis | Indica si la IA tuvo contexto suficiente |
| `score_urls` | REAL | Score 0.0–1.0 del URLAnalyzer | Desglose por componente del heurístico |
| `score_texto` | REAL | Score 0.0–1.0 del TextAnalyzer | Desglose por componente del heurístico |
| `score_ia` | REAL | `confidence` retornado por el modelo (0.0–1.0) | Confianza del modelo en su clasificación |
| `score_final` | REAL | `max(heuristic_score, ai_risk_score)` | Score integrado final para clasificación |
| `risk_level` | TEXT | `LOW` / `MEDIUM` / `HIGH` del análisis | Resultado de este análisis puntual |
| `categoria_ataque` | TEXT | Categoría APWG detectada por la IA | Taxonomía del tipo de ataque |
| `tecnica_mitre` | TEXT | `T1566.002`, `T1566.003`, `T1566.001` o `none` | Mapeo al framework MITRE ATT&CK |
| `principios_cialdini` | TEXT | JSON array de strings con principios detectados | Almacenado como JSON string (ver decisión de diseño) |
| `etapa_lifecycle` | TEXT | Etapa del lifecycle conversacional de phishing | approach / bond / hook / pressure / re_victimization |
| `urls_sospechosas` | TEXT | JSON array de objetos `{"url": ..., "reason": ...}` | Almacenado como JSON string |
| `accion_recomendada` | TEXT | `allow` / `warn_user` / `block_and_report` | Recomendación operativa de la IA |
| `explicacion_usuario` | TEXT | Explicación en español ≤280 chars para el usuario final | Legible sin conocimiento técnico |
| `explicacion_analista` | TEXT | Rationale técnico ≤500 chars para el analista | Para triage y auditoría |
| `analizado_at` | DATETIME | Timestamp de ejecución del análisis | Trazabilidad temporal |

---

## 3. Diagrama de relaciones

```
┌──────────────────────────────────────┐
│            conversacion              │
│                                      │
│  id_conversacion (PK)                │
│  ig_conversation_id                  │
│  cuenta_monitoreada                  │
│  participante_id                     │
│  participante_username               │
│  risk_level_actual                   │
│  risk_level_conversacion             │
│  total_mensajes                      │
│  primer_mensaje_at                   │
│  ultimo_mensaje_at                   │
│  observado_at                        │
│  creada_at                           │
└──────────┬──────────────────┬────────┘
           │ (1)              │ (1)
           │                  │
          (N)                (N)
           │                  │
┌──────────▼──────┐   ┌───────▼──────────────────────────┐
│     mensaje     │   │      analisis_conversacion        │
│                 │   │                                   │
│ id_mensaje (PK)◄├───┤ id_mensaje_disparador (FK)        │
│ id_conversacion │   │ id_conversacion (FK)              │
│ sender_id       │   │ id_analisis (PK AUTOINCREMENT)    │
│ es_entrante     │   │ mensajes_analizados               │
│ texto           │   │ score_urls                        │
│ urls_detectadas │   │ score_texto                       │
│ timestamp_ig    │   │ score_ia                          │
│ recibido_at     │   │ score_final                       │
└─────────────────┘   │ risk_level                        │
                      │ categoria_ataque                  │
                      │ tecnica_mitre                     │
                      │ principios_cialdini               │
                      │ etapa_lifecycle                   │
                      │ urls_sospechosas                  │
                      │ accion_recomendada                │
                      │ explicacion_usuario               │
                      │ explicacion_analista              │
                      │ analizado_at                      │
                      └───────────────────────────────────┘

conversacion  (1) ──────────────────< (N)  mensaje
conversacion  (1) ──────────────────< (N)  analisis_conversacion
mensaje       (1) ──────────────────< (N)  analisis_conversacion
```

---

## 4. Decisiones de diseño del modelo

### Por qué id_conversacion es SHA256(sender + recipient)[:16]

```python
id_conversacion = hashlib.sha256((sender_id + recipient_id).encode()).hexdigest()[:16]
```

**Determinismo**: dado el mismo par (sender_id, recipient_id), el id_conversacion es siempre el mismo. Esto permite hacer UPSERT en la tabla `conversacion` sin necesidad de un lookup previo.

**Idempotencia ante reenvíos**: si Meta reenvía el mismo evento (fallo de red, timeout), el `save_message()` calcula el mismo id_conversacion y el `INSERT OR IGNORE` en mensaje no duplica registros.

**Privacidad parcial**: el id_conversacion no revela directamente los sender/recipient IDs en el log. Solo los 16 primeros caracteres hexadecimales (64 bits de entropía) son suficientes para unicidad en el volumen de un prototipo.

**Limitación conocida**: si la misma persona escribe desde dos cuentas distintas, serán conversaciones separadas. Es un trade-off aceptable.

### Por qué se guarda sender_id real (no hash)

El sistema almacena `sender_id` y `participante_id` como IDs numéricos de Instagram, sin anonimización. Esta decisión fue evaluada durante el desarrollo:

**Justificación operativa**: el sender_id es necesario para consultar la API de Meta Graph (para obtener username, por ejemplo) y para correlacionar con alertas externas. Un hash unidireccional haría imposible estas consultas.

**Contexto de uso**: el sistema está diseñado para uso operativo en la cuenta propia del operador (su propia cuenta de Instagram). No procesa cuentas de terceros sin su consentimiento.

**Mitigación**: en el logging, el sender_id se trunca a los últimos 4 dígitos (`sender_id[-4:]`) para no exponer el ID completo en logs que podrían compartirse. El ID completo solo vive en la BD local.

**Para producción**: en un sistema productivo se evaluaría tokenización reversible (AES-GCM) sobre los IDs con una clave separada de la BD.

### Por qué risk_level_actual en conversacion se actualiza

Cada análisis ejecuta `UPDATE conversacion SET risk_level_actual = risk_level`. Este campo refleja el último nivel de riesgo calculado (no el histórico máximo). Esta decisión permite que una conversación que fue HIGH y luego generó mensajes LOW vuelva a LOW si el modelo determina que el peligro pasó.

El campo `risk_level_conversacion` (calculado por el conversation observer) mantiene la evaluación holística acumulada, que puede ser diferente al último análisis mensaje a mensaje.

### Por qué principios_cialdini y urls_sospechosas son JSON string

SQLite no tiene tipo nativo array. Las alternativas eran:

1. **Tabla separada** para cada principio/URL detectada → normalización completa, pero agrega complejidad y JOINs adicionales para recuperar un dato de un solo análisis.
2. **JSON string** → simple, el dashboard lo parsea con `json.loads()`, sin JOINs adicionales.

Se eligió JSON string (`principios_cialdini TEXT DEFAULT '[]'`) porque los arrays son pequeños (máx. 6 principios, máx. ~10 URLs), siempre se leen como parte del análisis completo, y SQLite 3.38+ soporta funciones JSON nativas si se necesitaran queries sobre el contenido.

### Por qué el análisis referencia la conversación Y el mensaje

`analisis_conversacion` tiene FK tanto a `conversacion` (id_conversacion) como a `mensaje` (id_mensaje_disparador). Esto responde a dos necesidades distintas:

- **FK a conversacion**: permite recuperar todos los análisis de una conversación (para el conversation observer y el dashboard).
- **FK a mensaje**: permite saber exactamente qué mensaje disparó este análisis, útil para auditoría y para el dashboard que muestra el análisis más reciente con el historial de mensajes.

El dashboard usa `MAX(id_analisis)` agrupado por `id_conversacion` para mostrar el análisis más reciente de cada conversación.

---

## 5. Cómo reproducir la BD desde cero

```bash
# Desde el directorio src/
python database/init_db.py
```

Salida esperada:
```
Base de datos lista en /ruta/a/src/data/phishing_detector.db
```

Si la BD ya existe con una versión anterior del esquema, `_apply_migrations()` agrega las columnas faltantes sin destruir los datos existentes. La función verifica columnas existentes con `PRAGMA table_info(conversacion)` antes de ejecutar cualquier `ALTER TABLE`.

Para inspección directa:
```bash
sqlite3 data/phishing_detector.db
sqlite> .tables
sqlite> .schema conversacion
sqlite> SELECT COUNT(*) FROM analisis_conversacion;
sqlite> SELECT id_conversacion, risk_level_actual, total_mensajes FROM conversacion;
```
