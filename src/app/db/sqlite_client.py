import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_db_path() -> Path:
    return Path(__file__).parent.parent.parent / "data" / "phishing_detector.db"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def save_message(
    sender_id: str,
    recipient_id: str,
    text: str,
    timestamp: int,
    message_id: str,
    ig_conversation_id: str = "",
    es_entrante: bool = True,
    participante_username: str = "",
) -> str:
    id_conversacion = _sha256(sender_id + recipient_id)[:16]
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(get_db_path()) as db:
        # Insertar mensaje primero — OR IGNORE para idempotencia
        cursor = await db.execute(
            """INSERT OR IGNORE INTO mensaje
               (id_mensaje, id_conversacion, sender_id, es_entrante, texto, timestamp_ig)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, id_conversacion, sender_id, int(es_entrante), text, timestamp),
        )
        is_new = cursor.rowcount > 0  # False si el mensaje ya existía

        # Upsert conversación — solo incrementa contador si el mensaje era nuevo
        await db.execute(
            """INSERT INTO conversacion
               (id_conversacion, ig_conversation_id, cuenta_monitoreada,
                participante_id, participante_username,
                primer_mensaje_at, ultimo_mensaje_at, total_mensajes)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)
               ON CONFLICT(id_conversacion) DO UPDATE SET
                   participante_username = CASE
                       WHEN excluded.participante_username != ''
                       THEN excluded.participante_username
                       ELSE participante_username
                   END,
                   ultimo_mensaje_at = CASE WHEN ? THEN ? ELSE ultimo_mensaje_at END,
                   total_mensajes     = CASE WHEN ? THEN total_mensajes + 1 ELSE total_mensajes END""",
            (
                id_conversacion, ig_conversation_id, recipient_id,
                sender_id, participante_username, now, now,
                is_new, now,   # para ultimo_mensaje_at
                is_new,        # para total_mensajes
            ),
        )
        await db.commit()

    return id_conversacion


async def get_conversation_history(
    id_conversacion: str,
    limit: int = 50,
    exclude_message_id: str = "",
) -> list[dict]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id_mensaje, sender_id, es_entrante, texto, timestamp_ig
               FROM mensaje
               WHERE id_conversacion = ?
                 AND (? = '' OR id_mensaje != ?)
               ORDER BY timestamp_ig ASC
               LIMIT ?""",
            (id_conversacion, exclude_message_id, exclude_message_id, limit),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_conversation_info(id_conversacion: str) -> dict:
    """Devuelve metadata de la conversación: username, total_mensajes, risk previo."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT participante_username, total_mensajes,
                      risk_level_actual, risk_level_conversacion, observado_at
               FROM conversacion WHERE id_conversacion = ?""",
            (id_conversacion,),
        )
        row = await cur.fetchone()
    return dict(row) if row else {}


async def update_conversation_observer_result(
    id_conversacion: str,
    risk_level_conversacion: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """UPDATE conversacion
               SET risk_level_conversacion = ?, observado_at = ?
               WHERE id_conversacion = ?""",
            (risk_level_conversacion, now, id_conversacion),
        )
        await db.commit()


async def save_analysis_result(
    id_mensaje_disparador: str,
    id_conversacion: str,
    score_urls: float,
    score_texto: float,
    score_ia: float,
    score_final: float,
    risk_level: str,
    categoria_ataque: str,
    tecnica_mitre: str,
    principios_cialdini: list,
    etapa_lifecycle: str,
    urls_sospechosas: list,
    accion_recomendada: str,
    explicacion_usuario: str,
    explicacion_analista: str,
    mensajes_analizados: int,
) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO analisis_conversacion
               (id_conversacion, id_mensaje_disparador, mensajes_analizados,
                score_urls, score_texto, score_ia, score_final, risk_level,
                categoria_ataque, tecnica_mitre, principios_cialdini,
                etapa_lifecycle, urls_sospechosas, accion_recomendada,
                explicacion_usuario, explicacion_analista)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id_conversacion,
                id_mensaje_disparador,
                mensajes_analizados,
                score_urls,
                score_texto,
                score_ia,
                score_final,
                risk_level,
                categoria_ataque,
                tecnica_mitre,
                json.dumps(principios_cialdini),
                etapa_lifecycle,
                json.dumps(urls_sospechosas),
                accion_recomendada,
                explicacion_usuario,
                explicacion_analista,
            ),
        )
        await db.execute(
            "UPDATE conversacion SET risk_level_actual = ? WHERE id_conversacion = ?",
            (risk_level, id_conversacion),
        )
        await db.commit()
