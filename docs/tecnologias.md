# Stack Tecnológico — Link Seguro

## 1. Tabla de tecnologías

| Componente             | Tecnología          | Versión        | Justificación                                                                 |
|------------------------|---------------------|----------------|-------------------------------------------------------------------------------|
| Lenguaje               | Python              | 3.14           | Ecosistema maduro para análisis de texto y regex; amplio soporte de librerías de seguridad. |
| Framework web          | FastAPI             | >= 0.111.0     | Tipado nativo, validación automática con Pydantic, soporte async de primera clase. |
| Servidor ASGI          | Uvicorn [standard]  | >= 0.29.0      | Servidor ASGI de alto rendimiento, requerido por FastAPI para manejar async I/O. |
| Validación y schemas   | Pydantic            | >= 2.7.0       | Modelos de datos tipados y validados en tiempo de ejecución para requests y resultados. |
| Configuración          | pydantic-settings   | >= 2.2.0       | Carga y valida variables de entorno desde `.env` con el mismo sistema de tipos de Pydantic. |
| Variables de entorno   | python-dotenv       | >= 1.0.0       | Carga el archivo `.env` en el entorno del proceso durante desarrollo local.   |
| Cliente HTTP           | httpx               | >= 0.27.0      | Cliente HTTP async compatible con el event loop de FastAPI (previsto para llamadas salientes). |
| Testing                | pytest              | >= 8.2.0       | Framework de testing estándar de Python con fixtures y plugins extensibles.   |
| Testing async          | pytest-asyncio      | >= 0.23.0      | Extensión de pytest para correr coroutines en tests sin boilerplate adicional. |
| API externa            | Meta Graph API      | v25.0          | API oficial de Meta para recibir eventos de mensajería de Instagram Business. |
| Túnel de desarrollo    | ngrok               | v3             | Expone el servidor local a internet con HTTPS para recibir webhooks de Meta.  |

---

## 2. Por qué FastAPI sobre Flask u otras alternativas

**FastAPI** fue elegido por tres razones concretas para este proyecto:

- **Soporte async nativo:** el webhook de Meta puede recibir múltiples eventos simultáneos. FastAPI corre sobre ASGI (Uvicorn) y maneja concurrencia sin bloqueos, lo que permite procesar mensajes en paralelo con `asyncio.gather`.
- **Validación automática vía Pydantic:** los parámetros de query del endpoint de verificación (`hub.mode`, `hub.verify_token`, `hub.challenge`) y los cuerpos de request se validan automáticamente, reduciendo código de verificación manual.
- **Documentación interactiva automática:** FastAPI genera Swagger UI en `/docs` sin configuración adicional, útil para inspeccionar y probar los endpoints durante desarrollo.

Flask es síncrono por defecto y requeriría extensiones (Flask-Async, Marshmallow) para lograr lo que FastAPI ofrece de forma integrada.

---

## 3. Por qué Pydantic v2 para validación y configuración

Pydantic v2 se usa en dos roles distintos dentro del proyecto:

**Schemas de datos** (`app/models/schemas.py`): los modelos `URLResult`, `TextResult` y `AnalysisResult` garantizan que los resultados del análisis siempre tengan la forma correcta antes de ser logueados o devueltos. El enum `RiskLevel` como `str, Enum` permite serialización JSON directa sin conversión adicional.

**Configuración** (`app/config.py`): `pydantic-settings` extiende `BaseSettings` para leer variables de entorno o un archivo `.env` y validarlas con tipos. Si falta `META_APP_SECRET` o `FACEBOOK_PAGE_ID` al arrancar, el proceso falla inmediatamente con un error claro en lugar de explotar en runtime al primer uso.

La migración a v2 (respecto a v1) aporta validación más estricta por defecto y mejor rendimiento en la creación de instancias.

---

## 4. Integración con Meta: Graph API, Webhooks e Instagram Business Login

**Meta Graph API v25.0** es la superficie de integración. El proyecto la usa de dos formas:

- **Webhook subscription:** Meta envía eventos HTTP POST al endpoint `/webhook` cada vez que un usuario envía un mensaje a la cuenta de Instagram Business. No requiere polling.
- **Verificación del webhook:** antes de empezar a enviar eventos, Meta realiza un GET con `hub.mode=subscribe`, `hub.verify_token` y `hub.challenge`. El servidor debe responder el challenge para completar el registro.

**Instagram Business Login** es el flujo OAuth que otorga el `PAGE_ACCESS_TOKEN`. Este token permite a la app leer mensajes y responder en nombre de la cuenta de Instagram Business vinculada.

El proyecto requiere que la app de Meta tenga la suscripción `messages` habilitada en el producto Instagram de la app.

---

## 5. Herramientas de desarrollo

**ngrok v3**
Durante desarrollo, el servidor corre en `localhost`. Meta exige una URL pública HTTPS para enviar webhooks. ngrok crea un túnel que expone el puerto local con un dominio temporal `*.ngrok-free.app` con HTTPS válido. El flujo es:

```
ngrok http 8000  →  https://<id>.ngrok-free.app  →  localhost:8000
```

**pytest + pytest-asyncio**
El stack de testing permite escribir tests unitarios e integrados de los analizadores y endpoints. `pytest-asyncio` es necesario para testear las coroutines del orchestrator y el router sin convertirlas a síncronas.

**python-dotenv**
Carga el archivo `.env` ubicado en `src/` para desarrollo local. En producción, las variables de entorno se inyectan directamente sin depender del archivo. `pydantic-settings` usa python-dotenv internamente cuando encuentra la configuración `env_file`.

---

## 6. Stack de seguridad

| Mecanismo               | Implementación                          | Archivo                        |
|-------------------------|----------------------------------------|-------------------------------|
| Verificación de firma   | HMAC-SHA256 con `META_APP_SECRET`      | `app/webhook/validator.py`    |
| Credenciales en entorno | Variables de entorno vía `.env`        | `app/config.py`               |
| Anonimización de PII    | Solo últimos 4 chars del `sender_id`   | `app/webhook/router.py`       |
| Token de acceso         | `PAGE_ACCESS_TOKEN` nunca en código    | `app/config.py` + `.env`      |

**HMAC-SHA256:** Meta firma cada POST con el header `X-Hub-Signature-256: sha256=<hash>`. La función `verify_signature()` recalcula el hash del body con `META_APP_SECRET` y compara usando `hmac.compare_digest()` para evitar timing attacks.

**Variables de entorno:** ninguna credencial (tokens, secrets, IDs) está hardcodeada en el código fuente. Todas se definen en `.env`, que está excluido de git vía `.gitignore`.

**Anonimización de PII:** el `sender_id` de Instagram es un identificador único de usuario. El logger solo escribe `sender=...XXXX` (los 4 últimos caracteres) para reducir exposición en logs.

---

## 7. Dependencias del requirements.txt

```
fastapi>=0.111.0          # Framework web ASGI con validación automática
uvicorn[standard]>=0.29.0 # Servidor ASGI; [standard] incluye websockets y watchfiles
pydantic>=2.7.0           # Validación de datos y schemas tipados
pydantic-settings>=2.2.0  # Lectura y validación de variables de entorno
python-dotenv>=1.0.0      # Carga de archivo .env durante desarrollo
httpx>=0.27.0             # Cliente HTTP async para llamadas salientes futuras
pytest>=8.2.0             # Framework de testing
pytest-asyncio>=0.23.0    # Soporte de coroutines en pytest
```
