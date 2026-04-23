import re

from app.models.schemas import TextResult

_PATTERNS: dict[str, re.Pattern[str]] = {
    "credential_request": re.compile(
        r'(send|share|provide|enter|give).{0,30}(password|contraseña|pin|credentials|usuario|user|pass)',
        re.IGNORECASE,
    ),
    "urgency": re.compile(
        r'(urgent|urgente|immediately|inmediatamente|act now|actúa ahora|'
        r'expire|vence|suspended|suspendido|limited time|tiempo limitado)',
        re.IGNORECASE,
    ),
    "support_impersonation": re.compile(
        r'(support team|equipo de soporte|instagram support|meta support|'
        r'official|oficial|verified|verificado|help desk)',
        re.IGNORECASE,
    ),
    "fraudulent_offer": re.compile(
        r'(winner|ganador|won|ganaste|prize|premio|free|gratis|claim|reclama|'
        r'gift card|reward|recompensa|earn money|ganar dinero)',
        re.IGNORECASE,
    ),
}

_WEIGHTS: dict[str, float] = {
    "credential_request": 0.8,
    "urgency": 0.5,
    "support_impersonation": 0.6,
    "fraudulent_offer": 0.5,
}


class TextAnalyzer:
    def analyze(self, text: str) -> TextResult:
        matched: list[str] = []
        total = 0.0

        for name, pattern in _PATTERNS.items():
            if pattern.search(text):
                matched.append(name)
                total += _WEIGHTS[name]

        return TextResult(score=min(total, 1.0), patterns_matched=matched)
