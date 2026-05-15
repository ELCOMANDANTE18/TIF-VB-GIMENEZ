from app.ai import groq_client
from app.db.sqlite_client import (
    get_conversation_history,
    save_analysis_result,
    update_conversation_observer_result,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Disparar en estos umbrales de mensajes y luego cada 5
_THRESHOLDS = {3, 5, 10}
_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def should_trigger(total_mensajes: int, prev_risk: str, current_risk: str) -> bool:
    """Decide si el observador debe correr para esta conversación."""
    if total_mensajes in _THRESHOLDS:
        return True
    if total_mensajes > 10 and total_mensajes % 5 == 0:
        return True
    # Escalada de riesgo (LOW→MEDIUM, LOW→HIGH, MEDIUM→HIGH)
    if _RISK_ORDER.get(current_risk, 0) > _RISK_ORDER.get(prev_risk, 0):
        return True
    return False


async def observe(
    conversation_id: str,
    username: str,
    total_mensajes: int,
    prev_risk: str,
    current_risk: str,
) -> None:
    """Analiza el riesgo acumulado de la conversación completa."""
    if not should_trigger(total_mensajes, prev_risk, current_risk):
        return

    logger.info(
        "Observador disparado | conv=%s @%s | msgs=%d prev=%s curr=%s",
        conversation_id, username, total_mensajes, prev_risk, current_risk,
    )

    history = await get_conversation_history(conversation_id, limit=50)
    if len(history) < 2:
        return

    # Último mensaje como "current", el resto como historial
    last = history[-1]
    prev_history = history[:-1]
    last_message_id = last.get("id_mensaje", f"OBSERVER_{conversation_id}")

    result = await groq_client.analyze_conversation(
        current_message=last["texto"],
        conversation_history=prev_history,
        url_score=0.0,
        text_score=0.0,
        reasons=[
            "[OBSERVADOR DE HISTORIAL] Evaluación holística del riesgo acumulado.",
            f"Conversación de {total_mensajes} mensajes con @{username}.",
            "Determiná el riesgo GLOBAL de la conversación completa, no solo del último mensaje.",
        ],
        conversation_id=conversation_id,
    )

    if not result:
        logger.warning("Observador: UM Cloud sin respuesta para conv=%s", conversation_id)
        return

    risk          = result.get("severity", "LOW")
    confidence    = result.get("confidence", 0.0)
    categoria     = result.get("scam_category", "none")
    mitre         = result.get("mitre_technique", "none")
    cialdini      = result.get("cialdini_principles", [])
    lifecycle     = result.get("lifecycle_stage", "n/a")
    urls          = result.get("suspicious_urls", [])
    accion        = result.get("recommended_action", "allow")
    expl_usuario  = result.get("explanation_user", "")
    expl_analista = result.get("explanation_analyst", "")

    # Persistir resultado holístico
    await update_conversation_observer_result(
        id_conversacion=conversation_id,
        risk_level_conversacion=risk,
    )

    await save_analysis_result(
        id_mensaje_disparador=last_message_id,
        id_conversacion=conversation_id,
        score_urls=0.0,
        score_texto=0.0,
        score_ia=confidence,
        score_final=confidence,
        risk_level=risk,
        categoria_ataque=categoria,
        tecnica_mitre=mitre,
        principios_cialdini=cialdini,
        etapa_lifecycle=lifecycle,
        urls_sospechosas=urls,
        accion_recomendada=accion,
        explicacion_usuario=expl_usuario,
        explicacion_analista=expl_analista,
        mensajes_analizados=total_mensajes,
    )

    logger.info(
        "Observador completado | @%s | risk_conversacion=%s confidence=%.2f lifecycle=%s category=%s",
        username, risk, confidence, lifecycle, categoria,
    )

    if risk == "HIGH":
        logger.warning(
            "\n  ╔══ ALERTA CONVERSACION ════════════════════════════╗\n"
            "  ║  @%-20s  msgs=%-3d  risk=HIGH          ║\n"
            "  ║  lifecycle=%-12s  category=%-20s║\n"
            "  ║  accion: %-43s║\n"
            "  ║  %s\n"
            "  ╚═══════════════════════════════════════════════════╝",
            username, total_mensajes,
            lifecycle, categoria,
            accion,
            (expl_usuario[:70] + "...") if len(expl_usuario) > 70 else expl_usuario,
        )
    elif risk == "MEDIUM":
        logger.warning(
            "ALERTA CONVERSACION | @%s | risk=MEDIUM | lifecycle=%s | category=%s | → %s",
            username, lifecycle, categoria, accion,
        )
