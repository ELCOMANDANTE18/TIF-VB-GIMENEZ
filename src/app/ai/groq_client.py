import json

from app.ai.prompts import SYSTEM_PROMPT
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _format_history(conversation_history: list[dict]) -> str:
    lines = []
    for msg in conversation_history[-10:]:
        sender = msg.get("sender_id_hash", "Usuario")
        text = msg.get("text", "")
        lines.append(f"Usuario {sender}: {text}")
    return "\n".join(lines)


async def analyze_conversation(
    current_message: str,
    conversation_history: list[dict],
    url_score: float,
    text_score: float,
    reasons: list[str],
) -> dict:
    if not settings.GROQ_API_KEY:
        return {}

    try:
        from groq import AsyncGroq

        history_text = _format_history(conversation_history)
        reasons_text = "\n".join(f"- {r}" for r in reasons) if reasons else "- Ninguno"

        user_prompt = f"""Historial de la conversación:
{history_text}

Mensaje actual siendo analizado:
"{current_message}"

Resultados del análisis heurístico:
- URL score: {url_score:.2f}
- Text score: {text_score:.2f}
- Indicadores detectados:
{reasons_text}

Analizá si esta conversación representa un intento de phishing o ingeniería social."""

        client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=10.0)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=512,
        )

        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    except json.JSONDecodeError:
        logger.warning("Groq returned non-JSON response")
        return {"risk_level": "LOW", "confidence": 0.0}
    except Exception as exc:
        logger.warning("Groq analysis skipped: %s", exc)
        return {}
