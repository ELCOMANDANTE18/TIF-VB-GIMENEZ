# Link Seguro — Registro de Decisiones de Arquitectura

Este documento registra las decisiones técnicas relevantes tomadas durante el desarrollo del TIF. Cada decisión incluye el contexto que la motivó, las alternativas evaluadas y las consecuencias conocidas.

---

## DA-01: FastAPI sobre Flask

**Fecha:** inicio del proyecto (v0.1)

**Contexto:** Se necesitaba un framework Python para exponer un endpoint de webhook que debía responder a Meta en menos de 20 segundos mientras procesaba mensajes en background. El análisis completo (heurístico + URLhaus + UM Cloud) puede tomar entre 2 y 8 segundos según la latencia de los servicios externos.

**Opciones evaluadas:**
- **Flask**: framework síncrono, maduro, bien documentado. Para background tasks requiere integrar Celery + Redis o usar threading manual.
- **FastAPI**: framework async nativo, `BackgroundTasks` incorporado, validación automática con Pydantic, documentación OpenAPI generada automáticamente.
- **Django**: framework completo, excesivo para una API de un solo endpoint de webhook.

**Decisión:** FastAPI.

**Justificación:** `BackgroundTasks` de FastAPI permite encolar el análisis pesado en una línea (`background_tasks.add_task(...)`) y retornar `{"status": "ok"}` a Meta inmediatamente. Sin background tasks, Meta reintentaría el evento si la respuesta demora más de 20s, generando análisis duplicados. Además, el soporte async nativo (`asyncio.gather()`) permite ejecutar URLAnalyzer y TextAnalyzer en paralelo sin threading manual.

**Consecuencias:**
- Requiere servidor ASGI (uvicorn) en lugar del servidor de desarrollo de Flask.
- El código debe ser consciente del event loop (`async/await`, `asyncio.to_thread` para código síncrono como los analizadores regex).
- BackgroundTasks de FastAPI no garantiza ejecución si el proceso cae; para producción se necesitaría una cola real (Celery). Para el TIF es aceptable.

---

## DA-02: SQLite local sobre Supabase

**Fecha:** v0.2.0 (migración desde v0.1 que usaba Supabase)

**Contexto:** La versión inicial del sistema usó Supabase (PostgreSQL managed en la nube) como backend de persistencia. El tutor indicó que para el TIF se prefería una solución reproducible localmente sin dependencias de cuentas externas.

**Opciones evaluadas:**
- **Supabase**: PostgreSQL en la nube con SDK de Python, tiempo real, sin administración de servidor. Requiere `SUPABASE_URL` y `SUPABASE_KEY`.
- **SQLite local**: base de datos embebida en un único archivo, sin servidor, async via `aiosqlite`.
- **PostgreSQL local**: más potente que SQLite, pero requiere instalación y configuración de un servidor Postgres.

**Decisión:** SQLite local.

**Justificación:** para un prototipo académico con un único proceso de escritura concurrente, SQLite es más que suficiente. Cualquier evaluador puede reproducir el sistema completo con `python database/init_db.py` sin configurar cuentas externas. El archivo `phishing_detector.db` puede compartirse directamente para revisión. Las variables de Supabase quedaron comentadas en `config.py` y el módulo `supabase_client.py` se preserva como referencia histórica.

**Consecuencias:**
- No hay replicación ni backups automáticos.
- SQLite tiene limitaciones de concurrencia en escritura (WAL mode mitiga esto, pero no está activado explícitamente).
- Para escalar a múltiples procesos o alta concurrencia, se requeriría migrar a PostgreSQL.
- El módulo `app/db/supabase_client.py` existe pero no es invocado por ningún módulo activo del sistema.

---

## DA-03: UM Cloud sobre Groq o OpenAI

**Fecha:** v0.2.0

**Contexto:** El sistema necesitaba un modelo de lenguaje para análisis conversacional. Se evaluaron servicios externos de pago y el recurso institucional de la Universidad de Mendoza.

**Opciones evaluadas:**
- **Groq API**: muy alta velocidad de inferencia (LPU), modelos Llama disponibles, API gratuita con límites. Versión anterior del código usó Groq (el módulo se llama `groq_client.py` por razones históricas).
- **OpenAI API**: GPT-4o, máxima calidad, pero costo por token elevado para un TIF.
- **UM Cloud** (`ai.cloud.um.edu.ar`): recurso institucional de la Universidad de Mendoza, API compatible con OpenAI SDK, sin costo para estudiantes e investigadores.

**Decisión:** UM Cloud.

**Justificación:** el recurso institucional elimina el costo de API y es académicamente coherente con el contexto del TIF. La API es compatible con `openai.AsyncOpenAI` (solo cambia `base_url` y `api_key`), lo que simplificó la migración desde Groq. El nombre del archivo `groq_client.py` se preservó por continuidad histórica aunque ya no invoca Groq.

**Consecuencias:**
- Dependencia de la disponibilidad de `ai.cloud.um.edu.ar` (uptime institucional).
- Si la API no está disponible, el sistema degrada a análisis solo heurístico (el bloque `try/except` en el orquestador captura la excepción).
- El módulo puede migrarse a Groq/OpenAI en cualquier momento cambiando `UM_BASE_URL` y `UM_API_KEY` sin modificar código.

---

## DA-04: gemma4-26b como modelo principal

**Fecha:** v0.2.0

**Contexto:** UM Cloud ofrece varios modelos. Se debía elegir uno para el análisis de phishing.

**Opciones evaluadas:**
- Modelos pequeños (7B parámetros): más rápidos, menor calidad de razonamiento complejo.
- **gemma4-26b**: el modelo de mayor capacidad disponible en UM Cloud al momento del desarrollo.

**Decisión:** gemma4-26b.

**Justificación:** la detección de phishing conversacional requiere razonamiento complejo: identificar patrones de lifecycle en múltiples mensajes, distinguir urgencia legítima de urgencia fraudulenta, detectar sutilezas de ingeniería social. Los modelos más grandes tienen mejor capacidad de seguir instrucciones complejas (el system prompt tiene 6 secciones estructuradas) y de razonamiento chain-of-thought. `temperature=0.1` asegura respuestas cuasi-deterministas independientemente del tamaño del modelo.

**Consecuencias:**
- Mayor latencia de inferencia que modelos más pequeños.
- El parámetro `UM_MODEL` en `.env` permite cambiar el modelo sin modificar código, facilitando comparaciones en futuras iteraciones.

---

## DA-05: Análisis de conversación completa vs. mensaje aislado

**Fecha:** v0.1 (decisión inicial de diseño)

**Contexto:** la primera versión del sistema analizaba cada mensaje de forma independiente. Esto producía falsos negativos en la fase approach/bond de los ataques de phishing multi-etapa.

**Opciones evaluadas:**
- **Mensaje aislado**: más simple, menos contexto para la IA, falla en ataques de múltiples fases.
- **Historial completo** (hasta 50 mensajes en SQLite, hasta 20 al modelo): permite detectar lifecycle conversacional, más costoso computacionalmente.

**Decisión:** historial completo.

**Justificación:** los ataques de ingeniería social sofisticados (pig_butchering, romance_scam) operan en fases que pueden durar días o semanas. El primer mensaje siempre es inofensivo. Sin contexto histórico, un atacante que saluda amablemente durante 5 mensajes antes de enviar un link malicioso elude completamente la detección. La recuperación del historial es una query simple a SQLite (`SELECT ... WHERE id_conversacion = ? ORDER BY timestamp_ig ASC LIMIT 50`) con costo despreciable.

**Consecuencias:**
- El orquestador llama a `get_conversation_history()` en cada análisis.
- El mensaje actual se excluye del historial (`exclude_message_id`) para no duplicarlo en el prompt.
- Se limita a 20 mensajes enviados al modelo (`_MAX_HISTORY_MSGS = 20`) para no exceder el contexto del modelo y controlar latencia.
- El `conversation_observer` complementa con análisis holísticos periódicos.

---

## DA-06: BackgroundTasks para procesamiento asíncrono

**Fecha:** v0.1

**Contexto:** Meta requiere que el webhook responda en menos de 20 segundos. El análisis completo puede superar ese tiempo si URLhaus o UM Cloud tienen latencia alta.

**Opciones evaluadas:**
- **Procesamiento síncrono**: el webhook bloquea hasta completar el análisis. Riesgo de timeout de Meta → reenvíos duplicados.
- **BackgroundTasks de FastAPI**: el webhook retorna inmediatamente, el análisis corre en segundo plano en el mismo proceso.
- **Cola externa (Celery + Redis)**: robusto para producción, excesivo para el TIF.

**Decisión:** BackgroundTasks de FastAPI.

**Justificación:** es la solución de menor complejidad que resuelve el problema. Un único `background_tasks.add_task(_analyze_and_log, ...)` evita el timeout sin agregar dependencias de Redis o workers externos. Para el volumen de un prototipo académico (decenas de mensajes, no miles por segundo), es suficiente.

**Consecuencias:**
- Si el proceso de uvicorn se reinicia mientras hay un análisis en background, ese análisis se pierde (sin retry).
- No hay visibility sobre tareas en background fallidas más allá de los logs.
- Para producción a escala se reemplazaría por Celery o similar.

---

## DA-07: PhishTank + URLhaus como fuentes de blacklist

**Fecha:** v0.1, extendido en v0.2

**Contexto:** el URLAnalyzer necesitaba fuentes de dominios/URLs maliciosas conocidas.

**Opciones evaluadas:**
- **Solo PhishTank**: base histórica amplia (~29k dominios), pero puede incluir URLs ya caídas.
- **Solo URLhaus**: verificación en tiempo real, pero no tiene cobertura histórica completa.
- **Google Safe Browsing API**: buena cobertura pero requiere key y tiene límites de cuota.
- **PhishTank + URLhaus** (combinación): cobertura histórica + verificación de estado activo.

**Decisión:** PhishTank (carga en memoria al inicio) + URLhaus API (consulta en tiempo real condicional).

**Justificación:** las dos fuentes son complementarias. PhishTank provee cobertura amplia sin latencia (cargado en memoria al iniciar el servidor). URLhaus se consulta solo cuando el score URL ya supera 0.3 (hay sospecha), añadiendo la confirmación de si la URL está activa en ese momento. Esto evita llamadas a URLhaus para mensajes sin URLs o con URLs de bajo riesgo.

**Consecuencias:**
- Si PhishTank CSV no existe, el sistema arranca con solo `blacklist.txt` (warning en log, no error fatal).
- URLhaus tiene timeout de 3 segundos (`httpx.AsyncClient(timeout=3.0)`) para no bloquear el análisis.
- El `blacklist.txt` local permite agregar dominios específicos del contexto sin esperar actualización de PhishTank.

---

## DA-08: sender_id real sin anonimización

**Fecha:** v0.1

**Contexto:** se debía decidir cómo almacenar el identificador del remitente en la base de datos. Almacenar el ID real facilita la operación pero tiene implicancias de privacidad.

**Opciones evaluadas:**
- **ID real** (`sender_id` como lo entrega Meta): necesario para consultas a la API de Meta Graph (obtener username, etc.). Legible directamente.
- **Hash unidireccional** (SHA256 del sender_id): anonimización parcial, impide consultas a la API de Meta.
- **Tokenización reversible** (AES-GCM): privacidad con posibilidad de recuperar el ID original, agrega complejidad operativa.

**Decisión:** ID real, con truncamiento en logs.

**Justificación:** el sender_id de Instagram es un identificador numérico opaco asignado por Meta (no es un dato directamente identificable como nombre o email). La API de Graph requiere el ID real para consultas de usuario. El sistema está diseñado para monitorear la propia cuenta del operador: los participantes son usuarios que inician contacto con esa cuenta. En el logging, el sender_id se trunca a los últimos 4 dígitos para no exponerlo en outputs compartibles.

**Consecuencias:**
- Los sender_ids reales están en la BD local, no en logs ni en el dashboard (el dashboard muestra `participante_username` cuando está disponible).
- Para una versión de producción orientada a múltiples usuarios se revisaría esta decisión e implementaría tokenización reversible.
- Esta decisión fue explícitamente evaluada y documentada como parte del TIF.

---

## DA-09: Prompt basado en MITRE ATT&CK + APWG + Cialdini

**Fecha:** v0.2.0

**Contexto:** se necesitaba diseñar el system prompt para el análisis de phishing. La calidad del prompt determina directamente la tasa de falsos positivos y negativos del sistema.

**Opciones evaluadas:**
- **Prompt genérico**: "¿Es este mensaje de phishing? Responde sí/no." — alta tasa de falsos positivos y falsos negativos sin contexto de dominio.
- **Prompt con ejemplos (few-shot)**: ejemplos de phishing real en el prompt — efectivo pero los ejemplos ocupan tokens y pueden sesgar hacia patrones específicos.
- **Prompt estructurado con frameworks** (MITRE + APWG + Cialdini + lifecycle): más largo, pero cada sección activa conocimiento específico del dominio.

**Decisión:** prompt estructurado con múltiples frameworks.

**Justificación:** los frameworks MITRE ATT&CK (T1566.002, T1566.003), la taxonomía APWG y los principios de Cialdini son el estándar de la industria para clasificar ataques de phishing. Incluirlos explícitamente en el KNOWLEDGE BASE activa ese conocimiento en el espacio de atención del modelo. El ANALYSIS PROCEDURE con 6 pasos fuerza razonamiento chain-of-thought que reduce la varianza. El GUARDRAIL de false-positive check (paso 6) reduce drásticamente los falsos positivos en conversaciones legítimas.

**Consecuencias:**
- El prompt ocupa ~800 tokens de contexto en cada llamada.
- `temperature=0.1` combinado con el prompt estructurado produce clasificaciones cuasi-deterministas.
- El output JSON estricto permite parseo confiable en Python sin postprocesamiento de texto.
- El campo `explanation_user` (español, ≤280 chars) está calibrado para mostrarse directamente en el dashboard sin edición.
