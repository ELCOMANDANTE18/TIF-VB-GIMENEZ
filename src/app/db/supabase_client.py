import asyncio
import hashlib
from datetime import datetime, timezone

from supabase import create_client, Client

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def save_message(
    sender_id: str,
    recipient_id: str,
    text: str,
    timestamp: int,
    message_id: str,
) -> str:
    conversation_id = _sha256(sender_id + recipient_id)[:16]
    sender_id_hash = _sha256(sender_id)[:12]

    def _upsert() -> None:
        client = get_client()
        client.table("conversations").upsert(
            {
                "conversation_id": conversation_id,
                "ig_user_id": recipient_id,
                "participant_id": sender_id_hash,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="conversation_id",
        ).execute()
        client.table("messages").upsert(
            {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "sender_id_hash": sender_id_hash,
                "recipient_id": recipient_id,
                "text": text,
                "timestamp": timestamp,
            },
            on_conflict="message_id",
        ).execute()

    await asyncio.to_thread(_upsert)
    return conversation_id


async def get_conversation_history(conversation_id: str, limit: int = 10) -> list[dict]:
    def _select() -> list[dict]:
        client = get_client()
        response = (
            client.table("messages")
            .select("message_id, text, sender_id_hash, timestamp")
            .eq("conversation_id", conversation_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(response.data))

    return await asyncio.to_thread(_select)


async def save_analysis_result(
    message_id: str,
    conversation_id: str,
    sender_id: str,
    text_preview: str,
    final_score: float,
    risk_level: str,
    urls_found: list,
    reasons: list,
    urlhaus_checked: bool,
) -> None:
    sender_id_hash = _sha256(sender_id)[:12]

    def _insert() -> None:
        client = get_client()
        client.table("analysis_results").insert(
            {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "sender_id_hash": sender_id_hash,
                "text_preview": text_preview[:30],
                "final_score": final_score,
                "risk_level": risk_level,
                "urls_found": urls_found,
                "reasons": reasons,
                "urlhaus_checked": urlhaus_checked,
            }
        ).execute()

    await asyncio.to_thread(_insert)
