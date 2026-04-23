import json

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.utils.logger import get_logger
from app.webhook.validator import verify_signature

router = APIRouter(prefix="/webhook")
logger = get_logger(__name__)


@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if not verify_signature(body, signature, settings.META_APP_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(body)

    for entry in payload.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id: str = messaging.get("sender", {}).get("id", "")
            text: str = messaging.get("message", {}).get("text", "")
            if sender_id and text:
                logger.info("Mensaje recibido | sender=%s | texto=%s", sender_id, text)

    return {"status": "ok"}
