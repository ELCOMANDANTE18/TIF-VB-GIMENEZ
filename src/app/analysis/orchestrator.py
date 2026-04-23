import asyncio

from app.analysis.url_analyzer import URLAnalyzer
from app.analysis.text_analyzer import TextAnalyzer
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

        url_result, text_result = await asyncio.gather(
            asyncio.to_thread(self.url_analyzer.analyze, text),
            asyncio.to_thread(self.text_analyzer.analyze, text),
        )

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

        return AnalysisResult(
            sender_id=sender_id,
            text=text,
            risk_level=risk_level,
            final_score=final_score,
            url_result=url_result,
            text_result=text_result,
        )
