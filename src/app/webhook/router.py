import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from app.analysis.orchestrator import PhishingOrchestrator
from app.config import settings
from app.db.sqlite_client import save_message
from app.models.schemas import RiskLevel
from app.utils.logger import get_logger
from app.webhook.validator import verify_signature

router = APIRouter(prefix="/webhook")
logger = get_logger(__name__)
_orchestrator = PhishingOrchestrator()


@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


async def _analyze_and_log(
    sender_id: str,
    text: str,
    recipient_id: str = "",
    message_id: str = "",
    conversation_id: str = "",
) -> None:
    result = await _orchestrator.analyze({
        "sender_id": sender_id,
        "text": text,
        "recipient_id": recipient_id,
        "message_id": message_id,
        "conversation_id": conversation_id,
    })
    reasons = result.url_result.reasons + result.text_result.patterns_matched
    reasons_str = "\n" + "\n".join(f"   → {r}" for r in reasons) if reasons else ""

    if result.risk_level == RiskLevel.HIGH:
        logger.warning(
            "HIGH RISK detectado | sender=...%s score=%.2f categoria=%s lifecycle=%s%s",
            sender_id[-4:],
            result.final_score,
            result.ai_categoria or "n/a",
            result.ai_lifecycle or "n/a",
            reasons_str,
        )
    elif result.risk_level == RiskLevel.MEDIUM:
        logger.warning(
            "MEDIUM RISK detectado | sender=...%s score=%.2f%s",
            sender_id[-4:], result.final_score, reasons_str,
        )
    else:
        logger.info(
            "LOW - mensaje limpio | sender=...%s score=%.2f%s",
            sender_id[-4:], result.final_score, reasons_str,
        )


@router.post("")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    payload = json.loads(body)

    for entry in payload.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id = messaging.get("sender", {}).get("id", "")
            recipient_id = messaging.get("recipient", {}).get("id", "")
            message_id = messaging.get("message", {}).get("mid", "")
            text = messaging.get("message", {}).get("text", "")
            timestamp = messaging.get("timestamp", 0)
            is_echo = messaging.get("message", {}).get("is_echo", False)
            ig_conversation_id = messaging.get("message", {}).get("conversation_id", "")

            if sender_id and text and not is_echo:
                logger.info("Mensaje entrante: sender=...%s | texto=%s",
                            sender_id[-4:], text[:50])
                conv_id = ""
                try:
                    conv_id = await save_message(
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        text=text,
                        timestamp=timestamp,
                        message_id=message_id,
                        ig_conversation_id=ig_conversation_id,
                    )
                except Exception as exc:
                    logger.warning("SQLite save_message failed: %s", exc)
                background_tasks.add_task(
                    _analyze_and_log, sender_id, text, recipient_id, message_id, conv_id
                )

    return {"status": "ok"}
