import html
import json
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

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


def _e(value) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


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
                CASE
                    WHEN c.participante_username IS NOT NULL AND c.participante_username != ''
                    THEN c.participante_username
                    ELSE '...' || SUBSTR(CAST(c.participante_id AS TEXT), -8)
                END AS usuario_display,
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


def _build_rows(conversations: list, is_admin: bool = False) -> str:  # noqa: C901
    if not conversations:
        return (
            '<tr><td colspan="10" class="text-center py-10 text-[#8A8B85] text-base">'
            "No hay análisis registrados todavía</td></tr>"
        )

    RISK_COLOR = {"HIGH": "#C2554B", "MEDIUM": "#B59628", "LOW": "#6E8F73"}
    RISK_BG    = {"HIGH": "#F5D9CC",  "MEDIUM": "#F5E9C2",  "LOW": "#E8F3EA"}
    RISK_EMOJI = {"HIGH": "🔴",       "MEDIUM": "🟡",        "LOW": "🟢"}
    ROW_BG     = {"HIGH": "#FDECEA",   "MEDIUM": "#FEF9E7",   "LOW": "#FAFAF8"}
    ROW_BORDER = {"HIGH": "#C2554B",   "MEDIUM": "#B59628",   "LOW": "#E9E6DD"}

    rows = []
    for i, conv in enumerate(conversations):
        risk = conv.get("risk_level_actual") or "LOW"
        uname = conv.get("participante_username") or ""
        pid = str(conv.get("participante_id") or "")
        if uname:
            usuario_html = f'<span class="font-mono text-[#6E8F73]">@{_e(uname)}</span>'
        else:
            usuario_html = f'<span class="font-mono text-[#8A8B85]">...{_e(pid[-8:])}</span>'

        badge_color = RISK_COLOR.get(risk, "#888")
        badge_bg    = RISK_BG.get(risk, "#1a1a1a")
        emoji       = RISK_EMOJI.get(risk, "⚪")
        row_bg      = ROW_BG.get(risk, "")
        row_border  = ROW_BORDER.get(risk, "transparent")

        row_style = f"background:{row_bg}; border-left:5px solid {row_border};"

        score = conv.get("score_final")
        score_val = score if score is not None else 0.0
        score_str = f"{score:.2f}" if score is not None else "—"
        score_pct = int(score_val * 100)

        if conv.get("respuesta_enviada"):
            alerta_html = (
                '<span class="inline-block text-sm py-1 px-3 rounded-xl '
                'bg-[#E8F3EA] text-[#6E8F73] border border-[#6E8F73] font-medium whitespace-nowrap">'
                '✅ Alertado</span>'
            )
        elif risk == "HIGH":
            alerta_html = (
                '<span class="inline-block text-sm py-1 px-3 rounded-xl '
                'bg-[#F5E9C2] text-[#B59628] border border-[#B59628] font-medium whitespace-nowrap">'
                '⏳ Pendiente</span>'
            )
        else:
            alerta_html = '<span class="text-[#8A8B85]">—</span>'

        ultimo = _e(_fmt_ts(conv.get("ultimo_mensaje_at")))

        cialdini_html = " ".join(
            f'<span class="inline-block text-sm py-1 px-3 rounded-full '
            f'bg-[#F5E9C2] text-[#B59628] border border-[#B59628] m-0.5">{_e(p)}</span>'
            for p in (conv.get("principios_cialdini") or [])
        ) or '<span class="text-[#8A8B85]">—</span>'

        urls_items = []
        for u in (conv.get("urls_sospechosas") or []):
            if isinstance(u, dict):
                url_txt = _e(u.get("url", ""))
                razon   = _e(u.get("razon") or u.get("reason", ""))
                urls_items.append(
                    f'<div class="flex gap-2 items-start py-1.5 border-b border-[#E9E6DD] text-sm">'
                    f'<span class="text-[#C2554B] font-mono break-all">{url_txt}</span>'
                    f'<span class="text-[#8A8B85] italic shrink-0">— {razon}</span></div>'
                )
            else:
                urls_items.append(
                    f'<div class="py-1.5 text-sm font-mono text-[#C2554B]">{_e(str(u))}</div>'
                )
        urls_html = "".join(urls_items) or '<span class="text-[#8A8B85]">—</span>'

        mensajes = list(reversed(conv.get("mensajes") or []))
        msg_rows = []
        for m in mensajes:
            ts_str = _fmt_ts(m.get("timestamp_ig"))
            is_incoming = m.get("es_entrante")
            if is_admin:
                texto = '<em class="text-[#8A8B85] text-sm">[contenido protegido — solo visible para el operador]</em>'
            else:
                texto = _e(m.get("texto", ""))
            if is_incoming:
                bubble = "bg-[#F7F5EE] rounded-2xl rounded-tl-sm"
                wrap   = "justify-start"
            else:
                bubble = "bg-[#E8F3EA] rounded-2xl rounded-tr-sm"
                wrap   = "justify-end"
            msg_rows.append(
                f'<div class="flex {wrap} mb-2">'
                f'<div class="{bubble} px-4 py-2 max-w-[80%]">'
                f'<p class="text-base text-[#1B1D1C] break-words">{texto}</p>'
                f'<p class="text-xs text-[#8A8B85] mt-1">{ts_str}</p>'
                f'</div></div>'
            )
        msgs_html = (
            "".join(msg_rows)
            or '<p class="text-[#8A8B85] text-sm">— sin mensajes —</p>'
        )

        conv_id_esc = html.escape(conv.get("id_conversacion", ""))

        pdf_btn = (
            f'<a href="/conversacion/{conv_id_esc}/pdf" target="_blank" '
            f'class="inline-flex items-center gap-2 text-base py-3 px-6 rounded-xl font-semibold '
            f'bg-[#F7F5EE] border border-[#1B1D1C] text-[#1B1D1C] '
            f'hover:bg-[#1B1D1C] hover:text-white transition-colors no-underline">'
            f'⬇ Exportar PDF</a>'
        )

        if risk in ("HIGH", "MEDIUM"):
            auto_dm_html = ""
            if conv.get("respuesta_enviada"):
                auto_dm_html = (
                    '<span class="inline-flex items-center gap-2 text-base py-2 px-4 rounded-xl '
                    'bg-[#E8F3EA] text-[#6E8F73] border border-[#6E8F73] font-medium">'
                    '✅ DM automático enviado</span>'
                )
            notificar_btn = (
                f'<button class="btn-action btn-notificar flex items-center gap-2 text-base py-3 px-6 '
                f'rounded-xl font-semibold bg-[#EEF3FA] border border-[#4A6A99] text-[#4A6A99] '
                f'hover:bg-[#4A6A99] hover:text-white transition-colors cursor-pointer" '
                f'data-id="{conv_id_esc}" onclick="accionNotificar(this)">'
                f'📧 Notificar usuario</button>'
            ) if is_admin else ""
            acciones_html = (
                '<div class="col-span-2 bg-[#F0F8F0] border border-[#A8C8A8] rounded-xl p-5">'
                '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">Acciones manuales</p>'
                f'<div class="flex gap-3 flex-wrap">{notificar_btn}{auto_dm_html}{pdf_btn}</div>'
                '</div>'
            )
        else:
            acciones_html = (
                '<div class="col-span-2 bg-[#F7F5EE] border border-[#E9E6DD] rounded-xl p-5">'
                '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">Acciones manuales</p>'
                f'<div class="flex gap-3 flex-wrap items-center">'
                f'<span class="text-sm text-[#8A8B85]">— Sin riesgo detectado —</span>'
                f'{pdf_btn}</div>'
                '</div>'
            )

        detail = (
            '<div class="bg-[#F7F5EE] p-6 rounded-b-2xl grid grid-cols-1 md:grid-cols-2 gap-4">'
            '<div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-xl p-4">'
            '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">Explicación para el usuario</p>'
            f'<p class="text-base text-[#1B1D1C] leading-relaxed">{_e(conv.get("explicacion_usuario"))}</p>'
            '</div>'
            '<div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-xl p-4">'
            '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">Explicación técnica (analista)</p>'
            f'<p class="text-sm font-mono text-[#1B1D1C] leading-relaxed">{_e(conv.get("explicacion_analista"))}</p>'
            '</div>'
            '<div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-xl p-4">'
            '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">Principios de Cialdini</p>'
            f'<div class="flex flex-wrap gap-1">{cialdini_html}</div>'
            '</div>'
            '<div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-xl p-4">'
            '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">URLs sospechosas</p>'
            f'<div>{urls_html}</div>'
            '</div>'
            '<div class="col-span-full bg-[#FFFFFF] border border-[#E9E6DD] rounded-xl p-4">'
            '<p class="text-base font-semibold uppercase tracking-wider text-[#8A8B85] mb-3">Últimos 10 mensajes</p>'
            f'<div class="max-h-64 overflow-y-auto">{msgs_html}</div>'
            '</div>'
            f'{acciones_html}'
            '</div>'
        )

        rows.append(
            f'<tr class="conv-row cursor-pointer transition-all" style="{row_style}" onclick="toggleDetail({i})">'
            f'<td class="py-4 px-4">{usuario_html}</td>'
            f'<td class="py-4 px-4">'
            f'<span class="inline-block text-sm py-1 px-3 rounded-full font-semibold border" '
            f'style="background:{badge_bg}; color:{badge_color}; border-color:{badge_color};">'
            f'{emoji} {risk}</span></td>'
            f'<td class="py-4 px-4 text-base text-[#8A8B85] font-mono">{_e(conv.get("categoria_ataque"))}</td>'
            f'<td class="py-4 px-4 text-base text-[#8A8B85] font-mono">{_e(conv.get("tecnica_mitre"))}</td>'
            f'<td class="py-4 px-4 text-center">'
            f'<span class="font-mono text-base font-semibold" style="color:{badge_color};">{score_str}</span>'
            f'<div class="w-20 h-2 bg-[#E9E6DD] rounded-full mt-1 mx-auto overflow-hidden">'
            f'<div class="h-full rounded-full" style="width:{score_pct}%;background:{badge_color};"></div>'
            f'</div></td>'
            f'<td class="py-4 px-4 text-base text-[#8A8B85] font-mono">{_e(conv.get("etapa_lifecycle"))}</td>'
            f'<td class="py-4 px-4 text-base text-[#8A8B85] font-mono">{_e(conv.get("accion_recomendada"))}</td>'
            f'<td class="py-4 px-4 text-center">{alerta_html}</td>'
            f'<td class="py-4 px-4 text-base font-mono text-[#8A8B85] whitespace-nowrap">{ultimo}</td>'
            f'<td class="py-4 px-4">'
            f'<button class="flex items-center gap-1 text-sm py-2 px-4 rounded-lg '
            f'bg-[#F7F5EE] hover:bg-[#E9E6DD] text-[#1B1D1C] border border-[#E9E6DD] '
            f'cursor-pointer transition-colors whitespace-nowrap" '
            f'id="btn-{i}" onclick="event.stopPropagation();toggleDetail({i})">'
            f'<span id="chevron-{i}" style="display:inline-block;transition:transform 0.2s;">▼</span>'
            f' Ver</button></td>'
            "</tr>"
            f'<tr id="detail-{i}" style="display:none;">'
            f'<td colspan="10" class="p-0 border-b-2 border-[#E9E6DD]">{detail}</td>'
            "</tr>"
        )

    return "\n".join(rows)


def render_html(
    data: dict,
    user: dict,
    usuarios_list: list | None = None,
    filtro_activo: str | None = None,
) -> str:
    rows_html = _build_rows(data["conversations"], is_admin=bool(user.get("es_admin")))
    last = _e(_fmt_ts(data["last_analysis"]))
    username_html = _e(user.get("username", ""))

    if user.get("es_admin"):
        role_badge = (
            '<span class="text-sm py-1 px-3 rounded-full bg-[#C9D6E8] '
            'text-[#7A95C2] border border-[#5D7DAB] font-semibold">ADMIN</span>'
        )
    else:
        role_badge = (
            '<span class="text-sm py-1 px-3 rounded-full bg-[#F7F5EE] '
            'text-[#8A8B85] border border-[#E9E6DD] font-semibold">USER</span>'
        )

    filter_bar_html = ""
    if user.get("es_admin") and usuarios_list:
        all_cls = ("border-[#7A95C2] text-[#4A6A99] bg-[#C9D6E8] font-bold"
                   if not filtro_activo
                   else "border-[#E9E6DD] text-[#8A8B85]")
        btns = [
            f'<a href="/dashboard" class="py-1.5 px-4 rounded-full border text-sm '
            f'no-underline transition-colors {all_cls}">Todas las cuentas</a>'
        ]
        for u in usuarios_list:
            ig = u.get("ig_username") or ""
            if not ig:
                continue
            act_cls = ("border-[#7A95C2] text-[#4A6A99] bg-[#C9D6E8] font-bold"
                       if ig == filtro_activo
                       else "border-[#E9E6DD] text-[#8A8B85]")
            btns.append(
                f'<a href="/dashboard?filtro={html.escape(ig)}" '
                f'class="py-1.5 px-4 rounded-full border text-sm no-underline transition-colors {act_cls}">'
                f'@{html.escape(ig)}</a>'
            )
        filter_bar_html = (
            '<div class="flex gap-2 items-center mb-5 flex-wrap">'
            '<span class="text-sm text-[#8A8B85] uppercase tracking-wider mr-1">Filtrar:</span>'
            + "".join(btns)
            + "</div>"
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Link Seguro — Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
  body {{ font-family: 'Inter', sans-serif; }}
  .font-mono {{ font-family: 'JetBrains Mono', monospace !important; }}
  .btn-action:disabled {{ opacity: 0.4; cursor: not-allowed !important; }}
  .btn-action.success {{ border-color: #6E8F73 !important; color: #6E8F73 !important; background: #E8F3EA !important; }}
  .btn-action.error   {{ border-color: #C2554B !important; color: #C2554B !important; background: #FEF2F2 !important; }}
  table {{ border-collapse: collapse; width: 100%; }}
  .conv-row:hover {{ filter: brightness(0.96); }}
  #progress-bar {{ transition: width 1s linear; }}
  td {{ vertical-align: middle; border-bottom: 2px solid #E9E6DD; }}
  tbody tr:nth-child(even) td {{ background: rgba(0,0,0,0.025); }}
</style>
</head>
<body class="bg-[#ECEAE3] text-[#1B1D1C] min-h-screen">

<header class="h-16 fixed top-0 left-0 right-0 z-50 bg-[#FFFFFF] border-b border-[#E9E6DD] flex items-center justify-between px-6">
  <div class="flex items-center gap-2">
    <img src="/static/logo.png" alt="Link Seguro" class="h-10 w-auto">
    <span class="text-xl font-bold text-[#1B1D1C] hidden sm:inline">Link Seguro</span>
  </div>
  <span class="text-sm text-[#8A8B85] hidden md:block">Dashboard de Seguridad</span>
  <div class="flex items-center gap-3">
    <span class="text-base font-medium text-[#1B1D1C]">@{username_html}</span>
    {role_badge}
    <a href="/logout" class="text-base py-2 px-4 rounded-lg bg-[#F7F5EE] hover:bg-[#F5D9CC] text-[#1B1D1C] border border-[#E9E6DD] no-underline transition-colors">Cerrar sesión</a>
  </div>
</header>

<div class="pt-20 px-6 pb-8 max-w-[1800px] mx-auto">

  <div class="flex items-center justify-end mb-5">
    <div class="flex items-center gap-3">
      <span class="text-sm text-[#8A8B85]">Próxima actualización en <span id="cd" class="text-[#6E8F73] font-semibold">30</span>s</span>
      <div class="w-32 h-1 bg-[#E9E6DD] rounded-full overflow-hidden">
        <div id="progress-bar" class="h-full bg-[#6E8F73] rounded-full" style="width:100%"></div>
      </div>
    </div>
  </div>

  <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
    <div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-2xl p-6" style="border-left:4px solid #7A95C2">
      <div class="flex items-center justify-between mb-2">
        <span class="text-base text-[#8A8B85]">Total</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-[#7A95C2]" viewBox="0 0 24 24" fill="currentColor"><path d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0016.5 9h-1.875a1.875 1.875 0 01-1.875-1.875V5.25A3.75 3.75 0 009 1.5H5.625z"/><path d="M12.971 1.816A5.23 5.23 0 0114.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 013.434 1.279 9.768 9.768 0 00-6.963-6.963z"/></svg>
      </div>
      <div class="text-4xl font-bold text-[#7A95C2]">{data["total"]}</div>
      <div class="text-base text-[#8A8B85] mt-1">conversaciones</div>
    </div>
    <div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-2xl p-6" style="border-left:4px solid #C2554B">
      <div class="flex items-center justify-between mb-2">
        <span class="text-base text-[#8A8B85]">HIGH</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-[#C2554B]" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd"/></svg>
      </div>
      <div class="text-4xl font-bold text-[#C2554B]">{data["high_count"]}</div>
      <div class="text-base text-[#8A8B85] mt-1">alto riesgo</div>
    </div>
    <div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-2xl p-6" style="border-left:4px solid #B59628">
      <div class="flex items-center justify-between mb-2">
        <span class="text-base text-[#8A8B85]">MEDIUM</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-[#B59628]" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm8.706-1.442c1.146-.573 2.437.463 2.126 1.706l-.709 2.836.042-.02a.75.75 0 01.67 1.34l-.04.022c-1.147.573-2.438-.463-2.127-1.706l.71-2.836-.042.02a.75.75 0 11-.671-1.34l.041-.022zM12 9a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd"/></svg>
      </div>
      <div class="text-4xl font-bold text-[#B59628]">{data["medium_count"]}</div>
      <div class="text-base text-[#8A8B85] mt-1">riesgo medio</div>
    </div>
    <div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-2xl p-6" style="border-left:4px solid #6E8F73">
      <div class="flex items-center justify-between mb-2">
        <span class="text-base text-[#8A8B85]">LOW</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-[#6E8F73]" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd"/></svg>
      </div>
      <div class="text-4xl font-bold text-[#6E8F73]">{data["low_count"]}</div>
      <div class="text-base text-[#8A8B85] mt-1">bajo riesgo</div>
    </div>
    <div class="bg-[#FFFFFF] border border-[#E9E6DD] rounded-2xl p-6" style="border-left:4px solid #8A8B85">
      <div class="flex items-center justify-between mb-2">
        <span class="text-base text-[#8A8B85]">Último análisis</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-[#8A8B85]" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zM12.75 6a.75.75 0 00-1.5 0v6c0 .414.336.75.75.75h4.5a.75.75 0 000-1.5h-3.75V6z" clip-rule="evenodd"/></svg>
      </div>
      <div class="text-base font-mono font-semibold text-[#8A8B85]">{last}</div>
      <div class="text-sm text-[#8A8B85] mt-1">GMT-3 Mendoza</div>
    </div>
  </div>

  {filter_bar_html}

  <div class="overflow-x-auto rounded-2xl border border-[#E9E6DD]">
    <table>
      <thead>
        <tr class="bg-[#FFFFFF] border-b border-[#E9E6DD]">
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Usuario</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Riesgo</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Categoría</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">MITRE</th>
          <th class="text-center text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Score</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Lifecycle</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Acción</th>
          <th class="text-center text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Alerta</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Último msg</th>
          <th class="text-left text-sm uppercase tracking-wider text-[#8A8B85] py-4 px-4 whitespace-nowrap">Detalle</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
</div>

<script>
(function () {{
  var total = 30;
  var secs = total;
  var el = document.getElementById('cd');
  var bar = document.getElementById('progress-bar');
  setInterval(function () {{
    secs--;
    if (secs <= 0) secs = total;
    el.textContent = secs;
    bar.style.width = (secs / total * 100) + '%';
  }}, 1000);
}})();

function toggleDetail(i) {{
  var row = document.getElementById('detail-' + i);
  var chevron = document.getElementById('chevron-' + i);
  if (row.style.display === 'none') {{
    row.style.display = '';
    chevron.style.transform = 'rotate(180deg)';
  }} else {{
    row.style.display = 'none';
    chevron.style.transform = '';
  }}
}}

async function _accion(endpoint, btn, labelOk, labelErr) {{
  var original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '⏳ Enviando...';
  try {{
    var r = await fetch(endpoint, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: 'id_conversacion=' + encodeURIComponent(btn.dataset.id)
    }});
    var data = await r.json();
    if (data.ok) {{
      btn.innerHTML = '✅ ' + (data.message || labelOk);
      btn.classList.add('success');
    }} else {{
      btn.innerHTML = '❌ ' + (data.message || labelErr);
      btn.classList.add('error');
      setTimeout(function() {{
        btn.innerHTML = original;
        btn.classList.remove('error');
        btn.disabled = false;
      }}, 4000);
    }}
  }} catch(e) {{
    btn.innerHTML = '❌ Error de red';
    btn.classList.add('error');
    setTimeout(function() {{
      btn.innerHTML = original;
      btn.classList.remove('error');
      btn.disabled = false;
    }}, 4000);
  }}
}}

function accionNotificar(btn) {{
  _accion('/dashboard/accion/notificar', btn, 'Email enviado', 'No se pudo notificar');
}}
</script>
</body>
</html>"""


def _render_login(error: str = "") -> str:
    error_html = (
        f'<div class="mb-5 flex items-center gap-3 rounded-xl border border-[#C2554B] bg-[#FEF2F2] px-4 py-3 text-base text-[#C2554B]">'
        f'<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>'
        f'{_e(error)}</div>'
    ) if error else ""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Link Seguro — Login</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
  body {{ font-family: 'Inter', sans-serif; }}
  .mono {{ font-family: 'JetBrains Mono', monospace; }}
  input:focus {{ outline: none; border-color: #7A95C2 !important; box-shadow: 0 0 0 2px rgba(122,149,194,0.25); }}
</style>
</head>
<body class="min-h-screen bg-[#ECEAE3] flex items-center justify-center px-4">
  <form method="post" action="/login" class="w-full max-w-md bg-[#FFFFFF] border border-[#E9E6DD] rounded-2xl shadow-2xl p-10">

    <div class="flex flex-col items-center mb-8">
      <img src="/static/logo.png" alt="Link Seguro" class="h-40 w-auto mb-2 drop-shadow-sm">
      <p class="text-base text-[#8A8B85] mt-1">Sistema de detección de phishing</p>
    </div>

    {error_html}

    <div class="mb-5">
      <label for="username" class="block text-base font-medium text-[#1B1D1C] mb-2">Usuario o email</label>
      <input id="username" name="username" type="text" required autofocus autocomplete="username"
        placeholder="usuario o correo electrónico"
        class="w-full text-lg py-3 px-4 rounded-xl bg-[#F7F5EE] border border-[#E9E6DD] text-[#1B1D1C] placeholder-[#8A8B85] transition-colors">
    </div>

    <div class="mb-6">
      <label for="password" class="block text-base font-medium text-[#1B1D1C] mb-2">Contraseña</label>
      <div class="relative">
        <input id="password" name="password" type="password" required autocomplete="current-password"
          placeholder="••••••••"
          class="w-full text-lg py-3 px-4 pr-12 rounded-xl bg-[#F7F5EE] border border-[#E9E6DD] text-[#1B1D1C] placeholder-[#8A8B85] transition-colors">
        <button type="button" onclick="togglePwd()" class="absolute inset-y-0 right-0 px-4 text-[#8A8B85] hover:text-[#1B1D1C]" tabindex="-1">
          <svg id="eye-show" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
            <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
          </svg>
          <svg id="eye-hide" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 hidden" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clip-rule="evenodd"/>
            <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.064 7 9.542 7 .847 0 1.669-.105 2.454-.303z"/>
          </svg>
        </button>
      </div>
    </div>

    <button type="submit"
      class="w-full text-lg py-3 font-semibold rounded-xl bg-[#7A95C2] hover:bg-[#4A6A99] text-white cursor-pointer transition-colors">
      Ingresar
    </button>
  </form>

  <script>
  function togglePwd() {{
    var inp = document.getElementById('password');
    var show = document.getElementById('eye-show');
    var hide = document.getElementById('eye-hide');
    if (inp.type === 'password') {{
      inp.type = 'text';
      show.classList.add('hidden');
      hide.classList.remove('hidden');
    }} else {{
      inp.type = 'password';
      show.classList.remove('hidden');
      hide.classList.add('hidden');
    }}
  }}
  </script>
</body>
</html>"""


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/dashboard", status_code=303)
    return HTMLResponse(_render_login())


@router.post("/login")
def login_submit(
    username: str = Form(...),
    password: str = Form(...),
):
    user = get_usuario_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return HTMLResponse(
            _render_login("Usuario o contraseña incorrectos"),
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
    return render_html(data, user, usuarios_list=usuarios_list, filtro_activo=filtro)
