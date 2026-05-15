import json

from openai import AsyncOpenAI

from app.ai.prompts import SYSTEM_PROMPT
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_RESULT = {
    "is_phishing": False,
    "severity": "LOW",
    "confidence": 0.0,
    "scam_category": "none",
    "mitre_technique": "none",
    "cialdini_principles": [],
    "lifecycle_stage": "n/a",
    "indicators": [],
    "suspicious_urls": [],
    "recommended_action": "allow",
    "explanation_user": "",
    "explanation_analyst": "",
}

# Límite de mensajes del historial enviados al modelo para no exceder el contexto
_MAX_HISTORY_MSGS = 20


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.UM_API_KEY,
        base_url=settings.UM_BASE_URL,
    )


def _format_history(conversation_history: list[dict]) -> str:
    # Toma los últimos N mensajes para no exceder el contexto del modelo
    msgs = conversation_history[-_MAX_HISTORY_MSGS:]
    lines = []
    for msg in msgs:
        prefix = "[entrante]" if msg.get("es_entrante") else "[saliente]"
        # Truncar mensajes muy largos
        text = (msg.get("texto") or "")[:300]
        lines.append(f"{prefix} {text}")
    return "\n".join(lines) if lines else "(sin historial previo)"


async def analyze_conversation(
    current_message: str,
    conversation_history: list[dict],
    url_score: float,
    text_score: float,
    reasons: list[str],
    conversation_id: str = "",
) -> dict:
    if not settings.UM_API_KEY:
        return {}

    try:
        history_text = _format_history(conversation_history)
        reasons_text = "\n".join(f"- {r}" for r in reasons) if reasons else "- Ninguno"

        user_prompt = (
            f"Historial de la conversación:\n{history_text}\n\n"
            f'Mensaje actual siendo analizado:\n"{current_message[:500]}"\n\n'
            f"Resultados del análisis heurístico:\n"
            f"- URL score: {url_score:.2f}\n"
            f"- Text score: {text_score:.2f}\n"
            f"- Indicadores detectados:\n{reasons_text}\n\n"
            "Analizá si esta conversación representa un intento de phishing o ingeniería social."
        )

        client = get_client()
        response = await client.chat.completions.create(
            model=settings.UM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    except json.JSONDecodeError:
        logger.warning("UM Cloud devolvió respuesta no-JSON — análisis omitido")
        return {}
    except Exception as exc:
        logger.warning("UM Cloud análisis omitido: %s", exc)
        return {}
