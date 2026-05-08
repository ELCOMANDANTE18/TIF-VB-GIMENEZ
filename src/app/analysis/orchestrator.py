import asyncio

from app.analysis.url_analyzer import URLAnalyzer
from app.analysis.text_analyzer import TextAnalyzer
from app.db.supabase_client import save_analysis_result, get_conversation_history
from app.ai import groq_client
from app.models.schemas import AnalysisResult, RiskLevel
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PhishingOrchestrator:
    def __init__(self) -> None:
        self.url_analyzer = URLAnalyzer()
        self.text_analyzer = TextAnalyzer()

    async def analyze(self, message: dict) -> AnalysisResult:
        sender_id: str = message.get("sender_id", "")
        text: str = message.get("text", "")
        message_id: str = message.get("message_id", "")
        conversation_id: str = message.get("conversation_id", "")

        url_result, text_result = await asyncio.gather(
            asyncio.to_thread(self.url_analyzer.analyze, text),
            asyncio.to_thread(self.text_analyzer.analyze, text),
        )

        urlhaus_checked = False
        # Si el score local supera 0.3, consultar URLhaus para cada URL encontrada
        if url_result.score > 0.3 and url_result.urls_found:
            urlhaus_checked = True
            urlhaus_results = await asyncio.gather(
                *[self.url_analyzer.analyze_with_urlhaus(u) for u in url_result.urls_found]
            )
            for uh in urlhaus_results:
                if uh.get("query_status") == "is_online":
                    url_result.score = min(url_result.score + 0.9, 1.0)
                    url_result.reasons.append("URLhaus: URL confirmed active and malicious")
                    break

        heuristic_score = (
            url_result.score * settings.URL_WEIGHT
            + text_result.score * settings.TEXT_WEIGHT
        )

        # Mapa de riesgo para comparar niveles
        _risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
        _level_from_str = {"LOW": RiskLevel.LOW, "MEDIUM": RiskLevel.MEDIUM, "HIGH": RiskLevel.HIGH}

        if heuristic_score >= settings.RISK_THRESHOLD_HIGH:
            risk_level = RiskLevel.HIGH
        elif heuristic_score >= settings.RISK_THRESHOLD_MEDIUM:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        final_score = heuristic_score
        ai_explanation: str | None = None
        ai_recommendation: str | None = None

        try:
            history = await get_conversation_history(conversation_id, limit=10)
            groq_result = await groq_client.analyze_conversation(
                current_message=text,
                conversation_history=history,
                url_score=url_result.score,
                text_score=text_result.score,
                reasons=url_result.reasons + text_result.patterns_matched,
            )
            if groq_result:
                groq_confidence: float = groq_result.get("confidence", 0.0)
                groq_risk_str: str = groq_result.get("risk_level", "LOW")
                groq_risk = _level_from_str.get(groq_risk_str, RiskLevel.LOW)

                final_score = max(heuristic_score, groq_confidence)
                if _risk_order[groq_risk] > _risk_order[risk_level]:
                    risk_level = groq_risk

                ai_explanation = groq_result.get("explanation")
                ai_recommendation = groq_result.get("recommendation")
                logger.info(
                    "Groq analysis | risk=%s confidence=%.2f",
                    groq_risk_str, groq_confidence,
                )
        except Exception as exc:
            logger.warning("Groq integration skipped: %s", exc)

        logger.info(
            "Analysis done | sender=%s score=%.2f risk=%s",
            sender_id, final_score, risk_level,
        )

        try:
            await save_analysis_result(
                message_id=message_id,
                conversation_id=conversation_id,
                sender_id=sender_id,
                text_preview=text,
                final_score=final_score,
                risk_level=risk_level.value,
                urls_found=url_result.urls_found,
                reasons=url_result.reasons + text_result.patterns_matched,
                urlhaus_checked=urlhaus_checked,
            )
        except Exception as exc:
            logger.error("Supabase save_analysis_result failed: %s", exc)

        result = AnalysisResult(
            sender_id=sender_id,
            text=text,
            risk_level=risk_level,
            final_score=final_score,
            url_result=url_result,
            text_result=text_result,
        )
        if ai_explanation:
            result.ai_explanation = ai_explanation
        if ai_recommendation:
            result.ai_recommendation = ai_recommendation
        return result
