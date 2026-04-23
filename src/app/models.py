from pydantic import BaseModel
from typing import Any


# --- Webhook payload schemas (Meta / Instagram) ---

class WebhookVerification(BaseModel):
    hub_mode: str
    hub_challenge: str
    hub_verify_token: str


class MessageValue(BaseModel):
    sender_id: str
    recipient_id: str
    text: str | None = None
    timestamp: int | None = None


# --- Analysis schemas ---

class AnalysisRequest(BaseModel):
    message_id: str
    text: str
    sender_id: str


class AnalysisResult(BaseModel):
    message_id: str
    is_phishing: bool
    confidence: float
    reasons: list[str]
    raw: dict[str, Any] = {}
