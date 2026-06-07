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
    # Hash bidireccional: ordenamos los IDs para que entrante y saliente
    # de la misma conversación produzcan el mismo id_conversacion.
    a, b = sorted([sender_id, recipient_id])
    id_conversacion = _sha256(a + b)[:16]
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
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
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
        return cursor.lastrowid


async def marcar_respuesta_enviada(id_analisis: int) -> None:
    """Marca un análisis como ya respondido automáticamente (idempotencia)."""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """UPDATE analisis_conversacion
               SET respuesta_enviada = 1,
                   respuesta_enviada_at = CURRENT_TIMESTAMP
               WHERE id_analisis = ?""",
            (id_analisis,),
        )
        await db.commit()


async def ya_fue_respondido(id_conversacion: str) -> bool:
    """True si en esta conversación ya se envió una respuesta automática."""
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM analisis_conversacion
               WHERE id_conversacion = ? AND respuesta_enviada = 1""",
            (id_conversacion,),
        )
        row = await cursor.fetchone()
    return bool(row[0]) if row else False


async def update_username_if_missing(
    id_conversacion: str,
    participante_id: str,
    token: str,
) -> str:
    try:
        async with aiosqlite.connect(get_db_path()) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT participante_username FROM conversacion WHERE id_conversacion = ?",
                (id_conversacion,),
            )
            row = await cur.fetchone()
            if row and row["participante_username"]:
                return row["participante_username"]

        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"https://graph.instagram.com/v25.0/{participante_id}",
                params={"fields": "username,name", "access_token": token},
            )
        if resp.status_code == 200:
            data = resp.json()
            username = data.get("username") or data.get("name") or ""
            if username:
                async with aiosqlite.connect(get_db_path()) as db:
                    await db.execute(
                        "UPDATE conversacion SET participante_username = ? WHERE id_conversacion = ?",
                        (username, id_conversacion),
                    )
                    await db.commit()
                return username
    except Exception:
        pass
    return f"...{participante_id[-8:]}"


async def es_cuenta_propia(ig_user_id: str) -> bool:
    """True si el ig_user_id pertenece a una cuenta activamente monitoreada (flia_test, benja).
    Exluye cuentas de prueba como hernesto que solo envían mensajes de test."""
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM usuario_sistema WHERE ig_user_id = ? AND es_cuenta_monitoreada = 1",
            (ig_user_id,),
        )
        row = await cursor.fetchone()
    return bool(row[0]) if row else False
