# Integración con Meta — Link Seguro v0.1.0

## 1. Configuración de la app en Meta for Developers

### Pasos de configuración

1. Ir a [developers.facebook.com](https://developers.facebook.com) y crear una nueva app.
2. Seleccionar tipo de app: **Business** (requerido para Instagram Messaging).
3. Agregar el producto **Webhooks** y el producto **Instagram**.
4. En la sección **Instagram → Webhooks**, configurar:
   - **Callback URL**: `https://{TU_DOMINIO}/webhook`
   - **Verify Token**: el valor de `META_VERIFY_TOKEN` del archivo `.env`
5. Suscribirse al campo `messages` del webhook.
6. Vincular la **Página de Facebook** asociada a la cuenta de Instagram.
7. Generar el `PAGE_ACCESS_TOKEN` desde el **Graph API Explorer** o el flujo de OAuth.

### Variables de entorno requeridas

```env
FACEBOOK_PAGE_ID={FACEBOOK_PAGE_ID}
META_APP_ID={META_APP_ID}
META_APP_SECRET={META_APP_SECRET}
META_VERIFY_TOKEN={META_VERIFY_TOKEN}
PAGE_ACCESS_TOKEN={PAGE_ACCESS_TOKEN}
```

---

## 2. Permisos requeridos

| Permiso | Para qué sirve |
|---|---|
| `pages_messaging` | Recibir y enviar mensajes desde la Página de Facebook vinculada |
| `instagram_manage_messages` | Acceder a los DMs de la cuenta de Instagram Professional |
| `pages_read_engagement` | Leer información básica de interacciones de la página |
| `instagram_basic` | Acceso básico al perfil de Instagram |

> En **modo desarrollo**, estos permisos solo funcionan para cuentas de Instagram agregadas manualmente como evaluadoras de la app.

---

## 3. Flujo de verificación del Webhook (GET /webhook)

Cuando se configura el webhook en Meta for Developers, Meta realiza una petición GET para verificar que el servidor está online y bajo control del desarrollador.

### Código real del router (`app/webhook/router.py`)

```python
@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
```

### Flujo paso a paso

```
Meta → GET /webhook?hub.mode=subscribe
                    &hub.verify_token={META_VERIFY_TOKEN}
                    &hub.challenge=1234567890

Servidor:
  1. Verifica hub.mode == "subscribe"
  2. Compara hub.verify_token con settings.META_VERIFY_TOKEN
  3. Si coincide → responde con int(hub_challenge) = 1234567890
  4. Si no coincide → HTTP 403 "Verification failed"

Meta recibe el challenge → webhook verificado ✓
```

---

## 4. Flujo de recepción de eventos (POST /webhook)

Una vez verificado, Meta envía eventos en tiempo real a `POST /webhook`.

### Código real del router

```python
@router.post("")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    payload = json.loads(body)

    for entry in payload.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id    = messaging.get("sender", {}).get("id", "")
            recipient_id = messaging.get("recipient", {}).get("id", "")
            message_id   = messaging.get("message", {}).get("mid", "")
            text         = messaging.get("message", {}).get("text", "")
            timestamp    = messaging.get("timestamp", 0)
            is_echo      = messaging.get("message", {}).get("is_echo", False)

            if sender_id and text and not is_echo:
                conv_id = await save_message(
                    sender_id, recipient_id, text, timestamp, message_id
                )
                background_tasks.add_task(
                    _analyze_and_log, sender_id, text, recipient_id, message_id, conv_id
                )

    return {"status": "ok"}
```

### Lógica de filtrado

- **`is_echo=True`**: mensajes enviados **desde** la página (no del usuario). Se ignoran para evitar analizar las propias respuestas del sistema.
- **`text` vacío**: eventos sin texto (stickers, reacciones, adjuntos) se omiten porque no hay contenido que analizar.
- **`sender_id` vacío**: evento malformado, se ignora.

---

## 5. Estructura real del payload de Instagram

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "{FACEBOOK_PAGE_ID}",
      "time": 1746700000,
      "messaging": [
        {
          "sender": {
            "id": "123456789012345"
          },
          "recipient": {
            "id": "{IG_USER_ID}"
          },
          "timestamp": 1746700000000,
          "message": {
            "mid": "m_AbCdEfGhIjKlMnOp",
            "text": "Hola, clickeá este link: http://ejemplo-phishing.ml"
          }
        }
      ]
    }
  ]
}
```

> **Nota**: `entry[].id` corresponde al `FACEBOOK_PAGE_ID` (ID de la Página de Facebook, no del usuario de Instagram). El campo `recipient.id` es el `IG_USER_ID` de la cuenta monitoreada.

### Campos extraídos por el sistema

| Campo en payload | Variable en código | Tipo | Uso |
|---|---|---|---|
| `messaging[].sender.id` | `sender_id` | `str` | Identificación del emisor (se hashea antes de guardar) |
| `messaging[].recipient.id` | `recipient_id` | `str` | ID de la cuenta monitoreada |
| `messaging[].message.mid` | `message_id` | `str` | ID único del mensaje (para upsert idempotente) |
| `messaging[].message.text` | `text` | `str` | Contenido a analizar |
| `messaging[].timestamp` | `timestamp` | `int` | Unix timestamp en milisegundos |
| `messaging[].message.is_echo` | `is_echo` | `bool` | Filtra mensajes propios |

---

## 6. IDs del proyecto (placeholders)

Los IDs reales son confidenciales y se manejan exclusivamente como variables de entorno.

| Placeholder | Variable de entorno | Descripción |
|---|---|---|
| `{FACEBOOK_PAGE_ID}` | `FACEBOOK_PAGE_ID` | ID numérico de la Página de Facebook vinculada |
| `{IG_USER_ID}` | `FLIA_TEST_IG_USER_ID` | ID numérico de la cuenta de Instagram monitoreada |
| `{META_APP_ID}` | `META_APP_ID` | ID de la aplicación en Meta for Developers |
| `{META_VERIFY_TOKEN}` | `META_VERIFY_TOKEN` | Token secreto para verificación del webhook |

---

## 7. Limitaciones del modo desarrollo

En modo desarrollo de Meta, aplican las siguientes restricciones:

| Limitación | Descripción |
|---|---|
| Solo evaluadores | Solo los usuarios de Instagram agregados como **Testers** o **Developers** en la app pueden enviar DMs que lleguen al webhook |
| Sin acceso a usuarios reales | Usuarios fuera de la app no disparan eventos |
| Permisos no revisados | Los permisos avanzados (como `instagram_manage_messages`) requieren revisión de Meta para ir a producción |
| Rate limits más bajos | El volumen de requests a la Graph API está limitado en modo desarrollo |

---

## 8. Cómo agregar evaluadores de Instagram

Para poder probar el webhook con cuentas de Instagram reales en modo desarrollo:

1. Ir a **Meta for Developers → Tu App → Roles → Testers**.
2. Hacer clic en **Add Testers** e ingresar el nombre de usuario de Instagram.
3. El usuario invitado debe aceptar la invitación desde [developers.facebook.com/apps](https://developers.facebook.com/apps).
4. Una vez aceptada, esa cuenta puede enviar DMs a la cuenta monitoreada y los eventos llegarán al webhook.

> La cuenta de Instagram a agregar debe ser de tipo **Professional** (Business o Creator) para que funcione la integración de mensajería.
