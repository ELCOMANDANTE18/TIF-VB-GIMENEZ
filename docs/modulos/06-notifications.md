# Módulo: Notificaciones

## Propósito

Envía alertas automáticas por dos canales cuando el sistema detecta riesgo HIGH: un DM directo al remitente sospechoso vía Instagram Messages API, y un email HTML al dueño de la cuenta monitoreada.

## Archivos

| Archivo | Responsabilidad |
|---------|----------------|
| `app/notifications/messenger.py` | DM automático vía Instagram Graph API v25.0 |
| `app/notifications/email_notifier.py` | Email HTML vía SMTP (Gmail STARTTLS) |

## Funciones principales

### `send_phishing_alert(ig_user_id, sender_id, explanation, categoria, token) → bool` — `messenger.py`

```python
async def send_phishing_alert(
    ig_user_id: str,    # ID de la cuenta monitoreada (quien envía el DM)
    sender_id: str,     # ID del atacante (destinatario del DM)
    explanation: str,   # Explicación IA para el usuario
    categoria: str,     # Categoría de ataque detectada
    token: str,         # Instagram access token
) -> bool
```

Envía un DM de alerta al remitente sospechoso desde la cuenta monitoreada. Devuelve `True` solo si recibe HTTP 200. Nunca lanza excepción — cualquier error se loguea y devuelve `False`.

**Endpoint de la API:**
```
POST https://graph.instagram.com/v25.0/{ig_user_id}/messages
Authorization: Bearer {token}
Body: {"recipient": {"id": sender_id}, "message": {"text": "..."}}
```

**Mensaje enviado** (`_build_alert_message`):
```
⚠️ AVISO AUTOMÁTICO DE SEGURIDAD

Este es un mensaje generado automáticamente por Link Seguro...
Se identificó que este mensaje podría ser un intento de {categoria}.
Por favor no continúes con esta conversación si recibiste una solicitud
de datos personales, contraseñas o dinero.
━━━━━━━━━━━━━━━━━━━━
Link Seguro · Mensaje automático
No responder a este mensaje.
```

**Ventana de 24 horas**: Instagram solo permite enviar mensajes dentro de las 24 horas del último mensaje del usuario. Fuera de esa ventana la API devuelve HTTP 403. El sistema lo detecta y loguea sin crashear.

### `send_email_alert(to_email, username, sender_handle, ...) → bool` — `email_notifier.py`

```python
async def send_email_alert(
    to_email: str,
    username: str,          # @handle del dueño de la cuenta
    sender_handle: str,     # @handle del remitente sospechoso
    risk_level: str,        # HIGH / MEDIUM / LOW
    categoria: str,
    explanation: str,
    mitre_technique: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    smtp_from: str = "Link Seguro <no-reply@linkseguro.com>",
) -> bool
```

Envía un email HTML al dueño de la cuenta. Usa `smtplib` con STARTTLS corriendo en `asyncio.to_thread` para no bloquear el event loop.

**Contenido del email HTML:**
- Header con logo y nombre del sistema
- Badge de riesgo con color según nivel (`HIGH` → rojo, `MEDIUM` → naranja, `LOW` → verde)
- Tabla con remitente, tipo de ataque y técnica MITRE
- Explicación generada por la IA
- Box de recomendaciones (no hacer clic, no compartir contraseñas)
- Footer con referencia al TIF

### `send_welcome_email(to_email, username, ig_username, ...) → bool`

Envía un email de bienvenida cuando se registra un nuevo usuario en el sistema. Incluye botón con enlace al dashboard. Actualmente se llama manualmente desde `scripts/setup_usuarios.py` pero no está integrado en el flujo automático del webhook.

## Flujo de datos

```
orchestrator [HIGH risk detectado]
    │
    ├── ya_fue_respondido(conv_id)?  ← SQLite
    │       │ No
    │       ▼
    │   send_phishing_alert()
    │       │ POST /v25.0/{ig_user_id}/messages
    │       │ Instagram Graph API
    │       │
    │       ▼ [True si 200 OK]
    │   marcar_respuesta_enviada(id_analisis)  ← SQLite
    │
    └── [ENABLE_EMAIL_ALERTS=True]
            │
            ▼
        SELECT email FROM usuario_sistema WHERE ig_user_id = recipient_id
            │
            ▼
        send_email_alert()
            │ asyncio.to_thread → smtplib STARTTLS → Gmail
            ▼
        email HTML al dueño de la cuenta
```

## Decisiones de diseño

**Idempotencia del DM automático**: el campo `respuesta_enviada` en `analisis_conversacion` garantiza que el atacante recibe como máximo una alerta, aunque el sistema detecte múltiples mensajes HIGH en la misma conversación. Sin este control, el atacante recibiría un DM por cada mensaje phishing que envíe.

**Falla silenciosa en ambos canales**: ni `send_phishing_alert` ni `send_email_alert` lanzan excepciones. Devuelven `bool` para que el orchestrator pueda loguear el resultado sin interrumpir el flujo. Un fallo en las notificaciones no afecta la persistencia del análisis.

**`asyncio.to_thread` para SMTP**: `smtplib` es una librería síncrona y bloqueante. Correrla en el thread pool del executor evita que el envío de email bloquee el event loop de FastAPI durante los ~1-2s que tarda la conexión SMTP.

**Un solo token de Instagram**: todas las llamadas a Graph API usan `settings.FLIA_TEST_TOKEN`. La arquitectura de la DB soporta múltiples cuentas (`ig_user_id` en `usuario_sistema`) pero el código de notificaciones no hace lookup del token por cuenta receptora. Ver `decisiones_tecnicas.md` #4.

**Ventana de 24h de Instagram**: la política de mensajería de Meta restringe los mensajes proactivos a la ventana de 24 horas posteriores al último mensaje del usuario. Fuera de esa ventana el sistema no puede enviar el DM automático. Esto es una restricción de la plataforma, no del sistema.

## Estado actual

- [x] DM automático al atacante vía Instagram Messages API
- [x] Idempotencia: un solo DM por conversación
- [x] Manejo de ventana de 24h (HTTP 403 esperado)
- [x] Email HTML al dueño de la cuenta (SMTP Gmail STARTTLS)
- [x] Badge de color por nivel de riesgo en el email
- [x] `send_welcome_email()` implementada
- [ ] `send_welcome_email()` no está integrada en el flujo automático del webhook
- [ ] Soporte de múltiples tokens de Instagram por cuenta monitoreada
- [ ] Templates de email externalizados (actualmente HTML inline en Python)
