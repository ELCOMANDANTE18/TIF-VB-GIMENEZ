# Módulo: Webhook

## Propósito

Recibe y valida los eventos de Instagram enviados por la API de Meta, persiste cada mensaje en SQLite y delega el análisis pesado a tareas en segundo plano sin bloquear la respuesta.

## Archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `app/webhook/router.py` | Router FastAPI con los dos endpoints de Meta (`GET` verificación, `POST` eventos) |
| `app/webhook/validator.py` | Función `verify_signature()` para validar la firma HMAC-SHA256 de Meta |

## Funciones principales

### `verify_webhook(hub_mode, hub_verify_token, hub_challenge)` — GET /webhook

Responde al handshake de Meta cuando se registra el webhook. Meta envía los tres parámetros como query string; si el `verify_token` coincide con el configurado en `.env`, se devuelve el `hub_challenge` como entero.

```python
# Meta llama a GET /webhook?hub.mode=subscribe&hub.verify_token=XXX&hub.challenge=YYY
# El router responde int(hub_challenge) si el token coincide, 403 si no.
```

### `receive_webhook(request, background_tasks)` — POST /webhook

Punto de entrada principal. Flujo:

1. Lee el body crudo (`await request.body()`) antes de parsear JSON — necesario para la validación HMAC.
2. Si `META_APP_SECRET` está configurado, valida la firma `X-Hub-Signature-256`. Rechaza con HTTP 403 si es inválida.
3. Itera sobre `entry[].messaging[]`, ignorando:
   - Mensajes propios (`is_echo=True`)
   - Mensajes vacíos (sin `text`)
   - Mensajes de cuentas propias monitoreadas (`es_cuenta_propia()`) para evitar loop infinito con el DM automático.
4. Llama a `save_message()` para persistir en SQLite.
5. Registra `_analyze_and_log` como `BackgroundTask` — el análisis corre **después** de responder.
6. Registra `update_username_if_missing` como segundo `BackgroundTask` para resolver el username del remitente via Graph API.
7. Devuelve `{"status": "ok"}` inmediatamente.

```python
# Meta exige respuesta en < 20s o reintenta. El análisis (IA ~4s) corre en background.
return {"status": "ok"}
```

### `_analyze_and_log(sender_id, text, recipient_id, message_id, conversation_id)`

Wrapper interno que llama a `PhishingOrchestrator.analyze()` y loguea el resultado con nivel apropiado (`WARNING` para HIGH/MEDIUM, `INFO` para LOW).

### `verify_signature(payload_body, signature_header, app_secret)` — `validator.py`

```python
def verify_signature(payload_body: bytes, signature_header: str, app_secret: str) -> bool
```

- Verifica la firma HMAC-SHA256 enviada por Meta en el header `X-Hub-Signature-256`.
- Usa `hmac.compare_digest()` para prevenir timing attacks.
- Devuelve `False` si el header no empieza con `sha256=` o si la firma no coincide.

## Flujo de datos

```
Meta (POST /webhook)
    │
    ▼
receive_webhook()
    │── HMAC validation (si META_APP_SECRET está set)
    │── save_message() → SQLite
    │
    ├── BackgroundTask: _analyze_and_log()
    │       └── PhishingOrchestrator.analyze()  [ver 02-analysis.md]
    │
    └── BackgroundTask: update_username_if_missing()
            └── Graph API: GET /v25.0/{id}?fields=username,name
```

## Decisiones de diseño

**BackgroundTasks en lugar de respuesta síncrona**: Meta marca el webhook como fallido y reintenta si no recibe respuesta en 20 segundos. El análisis completo (URLhaus + UM Cloud AI) puede tomar 4–8 segundos. La separación mediante `BackgroundTasks` garantiza que Meta siempre reciba `200 OK` antes del timeout.

**HMAC condicional**: la validación solo se activa si `META_APP_SECRET` tiene valor en `.env`. Cuando está vacío (entorno de desarrollo, tests con curl) se omite — permite testear sin firma válida sin modificar código. Ver `decisiones_tecnicas.md` #1.

**Anti-loop con `es_cuenta_propia()`**: cuando el sistema envía un DM automático al atacante, Meta reenvía ese DM como un nuevo evento POST al webhook. Sin este chequeo el sistema analizaría sus propios mensajes y podría enviar respuestas infinitas.

**HMAC activo desde commit `868042a`**: a diferencia de lo documentado en versiones anteriores, la firma está **conectada** al router desde ese commit.

## Estado actual

- [x] Verificación de handshake Meta (`GET /webhook`)
- [x] Recepción de eventos de mensajes (`POST /webhook`)
- [x] Persistencia de mensajes en SQLite
- [x] Análisis en background (no bloquea a Meta)
- [x] Validación HMAC-SHA256 (activa si `META_APP_SECRET` está configurado)
- [x] Resolución de username en background
- [x] Anti-loop para mensajes de cuentas propias
