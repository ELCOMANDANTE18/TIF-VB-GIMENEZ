import asyncio

from app.analysis.url_analyzer import URLAnalyzer
from app.analysis.text_analyzer import TextAnalyzer
from app.db.sqlite_client import (
    save_analysis_result,
    get_conversation_history,
    get_conversation_info,
)
from app.analysis import conversation_observer
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

        # Leer estado previo antes de modificarlo
        conv_info = await get_conversation_info(conversation_id)
        prev_risk = conv_info.get("risk_level_actual", "LOW")
        total_mensajes = conv_info.get("total_mensajes", 1)
        username = conv_info.get("participante_username", "")

        url_result, text_result = await asyncio.gather(
            asyncio.to_thread(self.url_analyzer.analyze, text),
            asyncio.to_thread(self.text_analyzer.analyze, text),
        )

        urlhaus_checked = False
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

        _risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
        _level_from_str = {"LOW": RiskLevel.LOW, "MEDIUM": RiskLevel.MEDIUM, "HIGH": RiskLevel.HIGH}

        if heuristic_score >= settings.RISK_THRESHOLD_HIGH:
            risk_level = RiskLevel.HIGH
        elif heuristic_score >= settings.RISK_THRESHOLD_MEDIUM:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        final_score = heuristic_score

        # Campos del resultado IA con defaults
        ai_severity: str = risk_level.value
        ai_confidence: float = 0.0
        ai_categoria: str = "none"
        ai_mitre: str = "none"
        ai_cialdini: list = []
        ai_lifecycle: str = "n/a"
        ai_suspicious_urls: list = []
        ai_accion: str = "allow"
        ai_explicacion_usuario: str = ""
        ai_explicacion_analista: str = ""

        try:
            # Excluye el mensaje actual (ya guardado en DB) para no duplicarlo en el prompt
            history = await get_conversation_history(
                conversation_id, limit=50, exclude_message_id=message_id
            )
            mensajes_analizados = len(history) + 1

            ai_result = await groq_client.analyze_conversation(
                current_message=text,
                conversation_history=history,
                url_score=url_result.score,
                text_score=text_result.score,
                reasons=url_result.reasons + text_result.patterns_matched,
                conversation_id=conversation_id,
            )

            if ai_result:
                ai_confidence = ai_result.get("confidence", 0.0)
                ai_severity = ai_result.get("severity", risk_level.value)
                ai_risk = _level_from_str.get(ai_severity, RiskLevel.LOW)

                # Convertir severidad IA a score en la misma escala que el heurístico
                # para no inflar el score cuando la IA dice LOW con alta confianza
                _severity_to_score = {RiskLevel.LOW: 0.15, RiskLevel.MEDIUM: 0.55, RiskLevel.HIGH: 0.90}
                ai_risk_score = _severity_to_score[ai_risk] * ai_confidence
                final_score = max(heuristic_score, ai_risk_score)

                if _risk_order[ai_risk] > _risk_order[risk_level]:
                    risk_level = ai_risk

                ai_categoria = ai_result.get("scam_category", "none")
                ai_mitre = ai_result.get("mitre_technique", "none")
                ai_cialdini = ai_result.get("cialdini_principles", [])
                ai_lifecycle = ai_result.get("lifecycle_stage", "n/a")
                ai_suspicious_urls = ai_result.get("suspicious_urls", [])
                ai_accion = ai_result.get("recommended_action", "allow")
                ai_explicacion_usuario = ai_result.get("explanation_user", "")
                ai_explicacion_analista = ai_result.get("explanation_analyst", "")

                logger.info(
                    "UM Cloud analysis | severity=%s confidence=%.2f category=%s mitre=%s",
                    ai_severity, ai_confidence, ai_categoria, ai_mitre,
                )
        except Exception as exc:
            logger.warning("UM Cloud integration skipped: %s", exc)
            mensajes_analizados = 1

        logger.info(
            "Analysis done | sender=%s score=%.2f risk=%s",
            sender_id, final_score, risk_level,
        )

        try:
            await save_analysis_result(
                id_mensaje_disparador=message_id,
                id_conversacion=conversation_id,
                score_urls=url_result.score,
                score_texto=text_result.score,
                score_ia=ai_confidence,
                score_final=final_score,
                risk_level=risk_level.value,
                categoria_ataque=ai_categoria,
                tecnica_mitre=ai_mitre,
                principios_cialdini=ai_cialdini,
                etapa_lifecycle=ai_lifecycle,
                urls_sospechosas=ai_suspicious_urls,
                accion_recomendada=ai_accion,
                explicacion_usuario=ai_explicacion_usuario,
                explicacion_analista=ai_explicacion_analista,
                mensajes_analizados=mensajes_analizados,
            )
        except Exception as exc:
            logger.error("SQLite save_analysis_result failed: %s", exc)

        # Observador: análisis holístico si se cumplen los criterios
        try:
            await conversation_observer.observe(
                conversation_id=conversation_id,
                username=username,
                total_mensajes=total_mensajes,
                prev_risk=prev_risk,
                current_risk=risk_level.value,
            )
        except Exception as exc:
            logger.warning("Conversation observer skipped: %s", exc)

        result = AnalysisResult(
            sender_id=sender_id,
            text=text,
            risk_level=risk_level,
            final_score=final_score,
            url_result=url_result,
            text_result=text_result,
        )
        result.ai_explanation = ai_explicacion_usuario
        result.ai_recommendation = ai_accion
        result.ai_confidence = ai_confidence
        result.ai_categoria = ai_categoria
        result.ai_lifecycle = ai_lifecycle
        return result
