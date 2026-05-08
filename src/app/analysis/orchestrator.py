import asyncio

from app.analysis.url_analyzer import URLAnalyzer
from app.analysis.text_analyzer import TextAnalyzer
from app.db.supabase_client import save_analysis_result
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

        final_score = (
            url_result.score * settings.URL_WEIGHT
            + text_result.score * settings.TEXT_WEIGHT
        )

        if final_score >= settings.RISK_THRESHOLD_HIGH:
            risk_level = RiskLevel.HIGH
        elif final_score >= settings.RISK_THRESHOLD_MEDIUM:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

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

        return AnalysisResult(
            sender_id=sender_id,
            text=text,
            risk_level=risk_level,
            final_score=final_score,
            url_result=url_result,
            text_result=text_result,
        )
