# Integración con Meta — Link Seguro

## 1. Configuración de la app en Meta for Developers

Para conectar Link Seguro con Instagram se necesita una app en [Meta for Developers](https://developers.facebook.com):

1. Crear una app de tipo **Business**.
2. Agregar el producto **Instagram** desde el panel de la app.
3. Dentro del producto Instagram, habilitar la suscripción al webhook con el evento `messages`.
4. Configurar la URL del webhook apuntando al endpoint público (ngrok en desarrollo):
   ```
   https://<id>.ngrok-free.app/webhook
   ```
5. Ingresar el `META_VERIFY_TOKEN` elegido (debe coincidir exactamente con el valor en `.env`).
6. Vincular la cuenta de Instagram Business a la app mediante el flujo de **Instagram Business Login**.
7. Copiar el `PAGE_ACCESS_TOKEN` generado y guardarlo en `.env`.

---

## 2. Permisos requeridos

| Permiso                        | Para qué sirve                                                          |
|--------------------------------|-------------------------------------------------------------------------|
| `instagram_basic`              | Leer información básica de la cuenta de Instagram Business.             |
| `instagram_manage_messages`    | Recibir y leer mensajes entrantes de la bandeja de Instagram Business.  |
| `pages_show_list`              | Listar las Pages de Facebook vinculadas a la cuenta.                    |
| `pages_messaging`              | Enviar mensajes en nombre de la Page (para respuestas futuras).         |

Todos estos permisos deben ser aprobados en la revisión de Meta antes de salir del modo desarrollo.

---

## 3. Flujo de verificación del Webhook (GET /webhook)

Cuando se registra o actualiza el webhook en el panel de Meta, Meta realiza una petición GET para confirmar que el servidor es legítimo:

```
GET /webhook?hub.mode=subscribe&hub.verify_token={TOKEN}&hub.challenge={CHALLENGE}
```

**Implementación** (`app/webhook/router.py`):

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

**Flujo paso a paso:**

```
Meta                          FastAPI
 │                               │
 │── GET /webhook?hub.mode=      │
 │       subscribe               │
 │       hub.verify_token=TOKEN  │
 │       hub.challenge=12345 ───▶│
 │                               │ Verifica TOKEN == META_VERIFY_TOKEN
 │                               │ Verifica hub_mode == "subscribe"
 │◀─── 200 OK: 12345 ───────────│
 │                               │
 │  (suscripción confirmada)     │
```

Si el token no coincide, el servidor devuelve `403 Forbidden` y Meta no activa la suscripción.

---

## 4. Flujo de recepción de eventos (POST /webhook)

Una vez verificado el webhook, Meta envía un POST por cada evento de mensajería:

```
POST /webhook
Headers:
  X-Hub-Signature-256: sha256=<hmac_hash>
  Content-Type: application/json

Body: { "entry": [...], "object": "instagram" }
```

**Implementación** (`app/webhook/router.py`):

```python
@router.post("")
async def receive_webhook(request: Request):
    body = await request.body()
    payload = json.loads(body)

    for entry in payload.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id = messaging.get("sender", {}).get("id", "")
            text = messaging.get("message", {}).get("text", "")
            is_echo = messaging.get("message", {}).get("is_echo", False)

            if sender_id and text and not is_echo:
                logger.info("📨 MENSAJE ENTRANTE: sender=...%s | texto=%s",
                           sender_id[-4:], text[:50])
                # TODO: llamar al orchestrator de análisis

    return {"status": "ok"}
```

El servidor siempre devuelve `{"status": "ok"}` con HTTP 200. Si Meta no recibe un 200, reintenta el envío.

---

## 5. Estructura del payload de Instagram

Ejemplo de payload completo que Meta envía al recibir un mensaje:

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "{FACEBOOK_PAGE_ID}",
      "time": 1714000000,
      "messaging": [
        {
          "sender": {
            "id": "{SENDER_IGSID}"
          },
          "recipient": {
            "id": "{INSTAGRAM_BUSINESS_ACCOUNT_ID}"
          },
          "timestamp": 1714000001000,
          "message": {
            "mid": "aGVsbG8gd29ybGQ=",
            "text": "Hola, necesito ayuda con mi cuenta"
          }
        }
      ]
    }
  ]
}
```

**Campos relevantes extraídos por el router:**

| Campo                                  | Descripción                                        |
|----------------------------------------|----------------------------------------------------|
| `entry[].id`                           | ID de la Facebook Page vinculada                   |
| `entry[].messaging[].sender.id`        | IGSID del usuario que envió el mensaje             |
| `entry[].messaging[].recipient.id`     | ID de la cuenta de Instagram Business              |
| `entry[].messaging[].message.text`     | Contenido de texto del mensaje                     |
| `entry[].messaging[].message.is_echo`  | `true` si es una copia del mensaje enviado por la propia página |
| `entry[].messaging[].message.mid`      | Message ID único de Meta                           |

Los mensajes con `is_echo: true` son descartados para evitar que la página analice sus propias respuestas.

---

## 6. IDs importantes del proyecto

Los siguientes identificadores son necesarios para la configuración y no deben hardcodearse en el código:

| Variable               | Descripción                                                  | Dónde se usa           |
|------------------------|--------------------------------------------------------------|------------------------|
| `{FACEBOOK_PAGE_ID}`   | ID numérico de la Facebook Page vinculada a la cuenta IG     | Identificar eventos entrantes |
| `{META_APP_ID}`        | ID de la app en Meta for Developers                          | Autenticación OAuth    |
| `{META_APP_SECRET}`    | Secret de la app, usado para validar firma HMAC              | `validator.py`         |
| `{META_VERIFY_TOKEN}`  | Token elegido al registrar el webhook                        | Verificación GET       |
| `{PAGE_ACCESS_TOKEN}`  | Token de acceso de la Page para llamadas a Graph API         | Llamadas salientes     |
| `{INSTAGRAM_BUSINESS_ACCOUNT_ID}` | ID de la cuenta Instagram Business               | `recipient.id` en payload |

Todos deben definirse en `src/.env`:

```env
FACEBOOK_PAGE_ID={FACEBOOK_PAGE_ID}
META_APP_ID={META_APP_ID}
META_APP_SECRET={META_APP_SECRET}
META_VERIFY_TOKEN={META_VERIFY_TOKEN}
PAGE_ACCESS_TOKEN={PAGE_ACCESS_TOKEN}
```

---

## 7. Limitaciones del modo desarrollo

Mientras la app de Meta no haya pasado la **revisión de permisos** de Meta, opera en modo desarrollo con las siguientes restricciones:

- Solo los usuarios listados explícitamente como **evaluadores** (testers) o **desarrolladores** en el panel de la app pueden enviar mensajes que el webhook reciba.
- Los mensajes de usuarios reales no llegan al webhook aunque escriban a la cuenta de Instagram.
- Los permisos `instagram_manage_messages` y `pages_messaging` requieren revisión manual de Meta antes de activarse para el público general.
- La app no puede enviarse a revisión hasta que cumpla con la [Política de uso de la plataforma de Meta](https://developers.facebook.com/policy/).

---

## 8. Pasos para agregar evaluadores de Instagram

Para que un usuario de Instagram pueda probar el sistema en modo desarrollo:

1. Ir al panel de la app en Meta for Developers.
2. Navegar a **Roles** → **Roles**.
3. Hacer clic en **Add Instagram Testers**.
4. Ingresar el nombre de usuario de Instagram del evaluador.
5. El evaluador debe ir a `instagram.com/accounts/manage_access/` y aceptar la invitación pendiente.
6. Una vez aceptada, los mensajes que ese usuario envíe a la cuenta de Instagram Business llegarán al webhook.

Para remover un evaluador, eliminarlo desde el mismo panel de Roles.
