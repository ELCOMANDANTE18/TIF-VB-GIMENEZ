import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.notifications.email_notifier import send_email_alert
from app.notifications.messenger import send_phishing_alert
from app.dashboard.auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    create_session_token,
    get_current_user,
    get_usuario_by_username,
    verify_password,
)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "phishing_detector.db"
TZ = ZoneInfo("America/Argentina/Mendoza")

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _fmt_ts(ts) -> str:
    if ts is None:
        return "—"
    if isinstance(ts, (int, float)):
        epoch = ts / 1000 if ts > 9_999_999_999 else ts
        return datetime.fromtimestamp(epoch, tz=TZ).strftime("%Y-%m-%d %H:%M:%S")
    try:
        dt = datetime.fromisoformat(str(ts)[:19])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(ts)[:19]


def get_dashboard_data(ig_user_id: str | None = None) -> dict:
    """
    Si ig_user_id es None → ve todas las conversaciones (admin).
    Si ig_user_id viene → filtra c.cuenta_monitoreada = ig_user_id.
    """
    where_clause = "WHERE c.cuenta_monitoreada = ?" if ig_user_id else ""
    where_counts = "WHERE cuenta_monitoreada = ?" if ig_user_id else ""
    params: tuple = (ig_user_id,) if ig_user_id else ()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            f"SELECT risk_level_actual, COUNT(*) AS cnt FROM conversacion {where_counts} "
            "GROUP BY risk_level_actual",
            params,
        )
        risk_counts = {row["risk_level_actual"]: row["cnt"] for row in cur.fetchall()}

        if ig_user_id:
            cur = conn.execute(
                """SELECT MAX(a.analizado_at) AS last
                   FROM analisis_conversacion a
                   JOIN conversacion c ON c.id_conversacion = a.id_conversacion
                   WHERE c.cuenta_monitoreada = ?""",
                params,
            )
        else:
            cur = conn.execute("SELECT MAX(analizado_at) AS last FROM analisis_conversacion")
        row = cur.fetchone()
        last_analysis = row["last"] if row and row["last"] else None

        cur = conn.execute(f"""
            SELECT
                c.id_conversacion,
                c.participante_username,
                c.participante_id,
                c.risk_level_actual,
                c.total_mensajes,
                c.ultimo_mensaje_at,
                a.categoria_ataque,
                a.tecnica_mitre,
                a.score_final,
                a.etapa_lifecycle,
                a.accion_recomendada,
                a.explicacion_usuario,
                a.explicacion_analista,
                a.principios_cialdini,
                a.urls_sospechosas,
                a.respuesta_enviada,
                a.analizado_at
            FROM conversacion c
            LEFT JOIN analisis_conversacion a
                ON c.id_conversacion = a.id_conversacion
                AND a.id_analisis = (
                    SELECT MAX(id_analisis)
                    FROM analisis_conversacion
                    WHERE id_conversacion = c.id_conversacion
                )
            {where_clause}
            ORDER BY
                CASE c.risk_level_actual
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    ELSE 3
                END,
                c.ultimo_mensaje_at DESC
        """, params)
        conversations = [dict(r) for r in cur.fetchall()]

        for conv in conversations:
            cur = conn.execute(
                """SELECT sender_id, es_entrante, texto, timestamp_ig
                   FROM mensaje
                   WHERE id_conversacion = ?
                   ORDER BY timestamp_ig DESC
                   LIMIT 10""",
                (conv["id_conversacion"],),
            )
            conv["mensajes"] = [dict(r) for r in cur.fetchall()]

            for field in ("principios_cialdini", "urls_sospechosas"):
                try:
                    conv[field] = json.loads(conv[field] or "[]")
                except (json.JSONDecodeError, TypeError):
                    conv[field] = []

        return {
            "total": sum(risk_counts.values()),
            "high_count": risk_counts.get("HIGH", 0),
            "medium_count": risk_counts.get("MEDIUM", 0),
            "low_count": risk_counts.get("LOW", 0),
            "last_analysis": last_analysis,
            "conversations": conversations,
        }
    finally:
        conn.close()


def get_all_ig_usuarios() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT ig_user_id, ig_username, username FROM usuario_sistema "
            "WHERE ig_user_id IS NOT NULL ORDER BY username"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_conversacion_para_accion(id_conversacion: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """SELECT
                c.id_conversacion,
                c.cuenta_monitoreada,
                c.participante_id,
                c.participante_username,
                c.risk_level_actual,
                a.id_analisis,
                a.categoria_ataque,
                a.tecnica_mitre,
                a.explicacion_usuario,
                u.email      AS owner_email,
                u.ig_username AS owner_ig_username,
                u.username    AS owner_username
            FROM conversacion c
            LEFT JOIN analisis_conversacion a
                ON c.id_conversacion = a.id_conversacion
                AND a.id_analisis = (
                    SELECT MAX(id_analisis) FROM analisis_conversacion
                    WHERE id_conversacion = c.id_conversacion
                )
            LEFT JOIN usuario_sistema u ON u.ig_user_id = c.cuenta_monitoreada
            WHERE c.id_conversacion = ?""",
            (id_conversacion,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _get_token_for_account(ig_user_id: str) -> str:
    if ig_user_id == settings.FLIA_TEST_IG_USER_ID:
        return settings.FLIA_TEST_TOKEN
    return ""


def _marcar_respondido_sync(id_conversacion: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """UPDATE analisis_conversacion
               SET respuesta_enviada = 1, respuesta_enviada_at = CURRENT_TIMESTAMP
               WHERE id_conversacion = ?
               AND id_analisis = (
                   SELECT MAX(id_analisis) FROM analisis_conversacion
                   WHERE id_conversacion = ?
               )""",
            (id_conversacion, id_conversacion),
        )
        conn.commit()
    finally:
        conn.close()


_RISK_COLOR  = {"HIGH": "#C2554B", "MEDIUM": "#B59628", "LOW": "#6E8F73"}
_RISK_BG     = {"HIGH": "#F5D9CC", "MEDIUM": "#F5E9C2", "LOW": "#E8F3EA"}
_RISK_EMOJI  = {"HIGH": "🔴",      "MEDIUM": "🟡",      "LOW": "🟢"}
_ROW_BG      = {"HIGH": "#FDECEA", "MEDIUM": "#FEF9E7", "LOW": "#FAFAF8"}
_ROW_BORDER  = {"HIGH": "#C2554B", "MEDIUM": "#B59628", "LOW": "#E9E6DD"}


def _enrich_conversations(conversations: list, is_admin: bool) -> list:
    result = []
    for conv in conversations:
        c = dict(conv)
        risk = c.get("risk_level_actual") or "LOW"
        c["risk_color"]  = _RISK_COLOR.get(risk, "#888")
        c["risk_bg"]     = _RISK_BG.get(risk, "#eee")
        c["risk_emoji"]  = _RISK_EMOJI.get(risk, "⚪")
        c["row_bg"]      = _ROW_BG.get(risk, "")
        c["row_border"]  = _ROW_BORDER.get(risk, "transparent")

        uname = c.get("participante_username") or ""
        pid   = str(c.get("participante_id") or "")
        c["usuario_display"]  = f"@{uname}" if uname else f"...{pid[-8:]}"
        c["usuario_is_named"] = bool(uname)

        score = c.get("score_final")
        c["score_str"] = f"{score:.2f}" if score is not None else "—"
        c["score_pct"] = int(score * 100) if score is not None else 0

        c["ultimo_fmt"] = _fmt_ts(c.get("ultimo_mensaje_at"))

        msgs = list(reversed(c.get("mensajes") or []))
        for m in msgs:
            m["ts_fmt"]        = _fmt_ts(m.get("timestamp_ig"))
            m["texto_display"] = None if is_admin else (m.get("texto") or "")
        c["mensajes_display"] = msgs

        result.append(c)
    return result


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": ""})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = get_usuario_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Usuario o contraseña incorrectos"},
            status_code=401,
        )
    token = create_session_token(user)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.post("/dashboard/accion/notificar")
async def accion_notificar(request: Request, id_conversacion: str = Form(...)):
    user = get_current_user(request)
    if not user or not user.get("es_admin"):
        return JSONResponse({"ok": False, "message": "Solo el admin puede notificar"}, status_code=403)

    conv = get_conversacion_para_accion(id_conversacion)
    if not conv:
        return JSONResponse({"ok": False, "message": "Conversación no encontrada"}, status_code=404)

    if conv.get("risk_level_actual") not in ("HIGH", "MEDIUM"):
        return JSONResponse({"ok": False, "message": "Acción no disponible: la conversación no presenta riesgo"})

    owner_email = conv.get("owner_email") or ""
    if not owner_email or "@" not in owner_email:
        return JSONResponse({"ok": False, "message": "El usuario no tiene email configurado"})

    ok = await send_email_alert(
        to_email=owner_email,
        username=conv.get("owner_username") or "usuario",
        sender_handle=conv.get("participante_username") or conv.get("participante_id") or "desconocido",
        risk_level=conv.get("risk_level_actual") or "HIGH",
        categoria=conv.get("categoria_ataque") or "Actividad sospechosa detectada",
        explanation=conv.get("explicacion_usuario") or "Se detectó actividad sospechosa en tu cuenta.",
        mitre_technique=conv.get("tecnica_mitre") or "—",
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        smtp_password=settings.SMTP_PASSWORD,
        smtp_from=settings.SMTP_FROM,
    )
    if ok:
        return JSONResponse({"ok": True, "message": f"Email enviado a {owner_email}"})
    return JSONResponse({"ok": False, "message": "No se pudo enviar el email (SMTP)"})


@router.post("/dashboard/accion/responder")
async def accion_responder(request: Request, id_conversacion: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "message": "No autorizado"}, status_code=403)

    conv = get_conversacion_para_accion(id_conversacion)
    if not conv:
        return JSONResponse({"ok": False, "message": "Conversación no encontrada"}, status_code=404)

    if conv.get("risk_level_actual") not in ("HIGH", "MEDIUM"):
        return JSONResponse({"ok": False, "message": "Acción no disponible: la conversación no presenta riesgo"})

    cuenta_id = conv.get("cuenta_monitoreada") or ""
    sender_id = conv.get("participante_id") or ""

    if not sender_id:
        return JSONResponse({"ok": False, "message": "ID del remitente no disponible"})

    token = _get_token_for_account(cuenta_id)
    if not token:
        return JSONResponse({"ok": False, "message": "Esta cuenta no tiene token configurado"})

    ok = await send_phishing_alert(
        ig_user_id=cuenta_id,
        sender_id=sender_id,
        explanation=conv.get("explicacion_usuario") or "Se detectó actividad sospechosa en este mensaje.",
        categoria=conv.get("categoria_ataque") or "phishing",
        token=token,
    )
    if ok:
        _marcar_respondido_sync(id_conversacion)
        return JSONResponse({"ok": True, "message": "DM enviado al remitente"})
    return JSONResponse({"ok": False, "message": "No se pudo enviar el DM (ventana 24hs o token inválido)"})


@router.get("/conversacion/{id_conversacion}/pdf")
def export_pdf(request: Request, id_conversacion: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    from app.dashboard.pdf_export import render_pdf
    pdf_bytes = render_pdf(id_conversacion)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="analisis_{id_conversacion}.pdf"'},
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, filtro: str | None = Query(default=None)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    usuarios_list: list = []
    if user.get("es_admin"):
        usuarios_list = get_all_ig_usuarios()
        ig_filter = None
        if filtro:
            ig_filter = next(
                (u["ig_user_id"] for u in usuarios_list if u["ig_username"] == filtro),
                None,
            )
    else:
        ig_filter = user.get("ig_user_id")
        filtro = None

    data = get_dashboard_data(ig_user_id=ig_filter)
    is_admin = bool(user.get("es_admin"))
    conversations = _enrich_conversations(data["conversations"], is_admin)

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "conversations": conversations,
        "total": data["total"],
        "high_count": data["high_count"],
        "medium_count": data["medium_count"],
        "low_count": data["low_count"],
        "last_analysis": _fmt_ts(data["last_analysis"]),
        "usuarios_list": usuarios_list,
        "filtro_activo": filtro,
    })
