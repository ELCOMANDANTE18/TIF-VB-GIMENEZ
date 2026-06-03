"""Envío de alertas automáticas vía Instagram Messages API.

La cuenta monitoreada responde al remitente cuando se detecta phishing de
riesgo alto. El envío nunca lanza excepción: devuelve un bool para que el
orchestrator pueda decidir si marcar el análisis como respondido.
"""

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)

GRAPH_API_VERSION = "v25.0"
GRAPH_BASE_URL = "https://graph.instagram.com"
TIMEOUT_SECONDS = 5.0


def _build_alert_message(explanation: str, categoria: str) -> str:
    return (
        f"⚠️ Link Seguro detectó que este mensaje "
        f"podría ser un intento de {categoria}.\n\n"
        f"{explanation}\n\n"
        "Este mensaje fue analizado automáticamente "
        "por un sistema de seguridad."
    )


async def send_phishing_alert(
    ig_user_id: str,
    sender_id: str,
    explanation: str,
    categoria: str,
    token: str,
) -> bool:
    """Envía la alerta de phishing al remitente. Devuelve True solo si 200 OK.

    Nunca lanza: ante cualquier error loguea y devuelve False.
    """
    if not token:
        logger.warning("No se pudo enviar alerta: PAGE_ACCESS_TOKEN vacío")
        return False

    url = f"{GRAPH_BASE_URL}/{GRAPH_API_VERSION}/{ig_user_id}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "recipient": {"id": sender_id},
        "message": {"text": _build_alert_message(explanation, categoria)},
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=headers, json=body)

        if response.status_code == 200:
            logger.info("Respuesta automática enviada a sender=...%s", sender_id[-4:])
            return True

        detail = response.text
        # La API de Instagram solo permite responder dentro de las 24hs del
        # último mensaje del usuario; fuera de esa ventana devuelve 403.
        if response.status_code == 403 and "período permitido" in detail.lower():
            logger.warning(
                "No se pudo enviar respuesta automática a sender=...%s: "
                "ventana de 24hs expirada",
                sender_id[-4:],
            )
        else:
            logger.warning(
                "No se pudo enviar respuesta automática a sender=...%s: HTTP %s — %s",
                sender_id[-4:], response.status_code, detail[:300],
            )
        return False
    except Exception as exc:
        logger.warning(
            "No se pudo enviar respuesta automática a sender=...%s: %s",
            sender_id[-4:], exc,
        )
        return False
