import html
import json
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

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


def _build_rows(conversations: list, is_admin: bool = False) -> str:
    if not conversations:
        return (
            '<tr><td colspan="10" style="text-align:center;padding:40px;color:#555;">'
            "No hay análisis registrados todavía</td></tr>"
        )

    RISK_COLOR = {"HIGH": "#ff4444", "MEDIUM": "#ffaa00", "LOW": "#44ff88"}
    RISK_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    ROW_BG = {"HIGH": "#2d0000", "MEDIUM": "#2d2000", "LOW": "#002d00"}

    rows = []
    for i, conv in enumerate(conversations):
        risk = conv.get("risk_level_actual") or "LOW"
        uname = conv.get("participante_username") or ""
        pid = str(conv.get("participante_id") or "")
        if uname:
            usuario_html = f"@{_e(uname)}"
        else:
            usuario_html = f"...{_e(pid[-8:])}"

        badge_color = RISK_COLOR.get(risk, "#888")
        emoji = RISK_EMOJI.get(risk, "⚪")
        row_bg = ROW_BG.get(risk, "#111")

        score = conv.get("score_final")
        score_str = f"{score:.2f}" if score is not None else "—"

        # Estado de la respuesta automática
        if conv.get("respuesta_enviada"):
            alerta_html = (
                '<span class="alert-badge ok">✅ Alertado</span>'
            )
        elif risk == "HIGH":
            alerta_html = (
                '<span class="alert-badge pending">⏳ Pendiente</span>'
            )
        else:
            alerta_html = "—"

        ultimo_raw = conv.get("ultimo_mensaje_at")
        ultimo = _e(_fmt_ts(ultimo_raw))

        # Cialdini badges
        cialdini_html = " ".join(
            f'<span class="badge">{_e(p)}</span>'
            for p in (conv.get("principios_cialdini") or [])
        ) or "—"

        # Suspicious URLs
        urls_items = []
        for u in (conv.get("urls_sospechosas") or []):
            if isinstance(u, dict):
                url_txt = _e(u.get("url", ""))
                razon = _e(u.get("razon") or u.get("reason", ""))
                urls_items.append(
                    f'<div class="url-item">'
                    f'<span class="url-text">{url_txt}</span>'
                    f' — <span class="url-reason">{razon}</span></div>'
                )
            else:
                urls_items.append(f'<div class="url-item">{_e(str(u))}</div>')
        urls_html = "".join(urls_items) or "—"

        # Message history (show oldest → newest)
        mensajes = list(reversed(conv.get("mensajes") or []))
        msg_rows = []
        for m in mensajes:
            ts_str = _fmt_ts(m.get("timestamp_ig"))
            direction = "←" if m.get("es_entrante") else "→"
            sender = _e(m.get("sender_id", ""))
            texto = _e(m.get("texto", ""))
            msg_rows.append(
                f'<div class="msg-row">'
                f'<span class="msg-ts">{ts_str}</span>'
                f'<span class="msg-dir">{direction}</span>'
                f'<span class="msg-sender">{sender}</span>'
                f'<span class="msg-text">{texto}</span>'
                f"</div>"
            )
        msgs_html = "".join(msg_rows) or "— sin mensajes —"

        conv_id_esc = html.escape(conv.get("id_conversacion", ""))
        already_responded = bool(conv.get("respuesta_enviada"))
        if already_responded:
            responder_btn = (
                '<button class="btn-action" disabled>✅ DM ya enviado</button>'
            )
        else:
            responder_btn = (
                f'<button class="btn-action btn-responder" data-id="{conv_id_esc}" '
                f'onclick="accionResponder(this)">💬 Responder DM</button>'
            )
        notificar_btn = (
            f'<button class="btn-action btn-notificar" data-id="{conv_id_esc}" '
            f'onclick="accionNotificar(this)">📧 Notificar usuario</button>'
        ) if is_admin else ""

        acciones_html = (
            '<div class="detail-block full-width actions-block">'
            '<div class="detail-label">Acciones manuales</div>'
            '<div class="action-btns">' + responder_btn + notificar_btn + '</div>'
            '</div>'
        )

        detail = (
            '<div class="detail-section">'
            '<div class="detail-block">'
            '<div class="detail-label">Explicación para el usuario</div>'
            f'<div class="detail-value">{_e(conv.get("explicacion_usuario"))}</div>'
            "</div>"
            '<div class="detail-block">'
            '<div class="detail-label">Explicación técnica (analista)</div>'
            f'<div class="detail-value mono">{_e(conv.get("explicacion_analista"))}</div>'
            "</div>"
            '<div class="detail-block">'
            '<div class="detail-label">Principios de Cialdini detectados</div>'
            f'<div class="detail-value">{cialdini_html}</div>'
            "</div>"
            '<div class="detail-block">'
            '<div class="detail-label">URLs sospechosas encontradas</div>'
            f'<div class="detail-value">{urls_html}</div>'
            "</div>"
            '<div class="detail-block full-width">'
            '<div class="detail-label">Últimos 10 mensajes</div>'
            f'<div class="msg-list">{msgs_html}</div>'
            "</div>"
            f'{acciones_html}'
            "</div>"
        )

        rows.append(
            f'<tr class="conv-row" style="background:{row_bg};" onclick="toggleDetail({i})">'
            f'<td class="mono">{usuario_html}</td>'
            f'<td><span class="risk-badge" style="background:{badge_color};">{emoji} {risk}</span></td>'
            f'<td class="mono small">{_e(conv.get("categoria_ataque"))}</td>'
            f'<td class="mono small">{_e(conv.get("tecnica_mitre"))}</td>'
            f'<td class="mono center">{score_str}</td>'
            f'<td class="mono small">{_e(conv.get("etapa_lifecycle"))}</td>'
            f'<td class="mono small">{_e(conv.get("accion_recomendada"))}</td>'
            f'<td class="center">{alerta_html}</td>'
            f'<td class="mono small">{ultimo}</td>'
            f'<td><button class="btn-detail" id="btn-{i}" onclick="event.stopPropagation();toggleDetail({i})">▼ Ver</button></td>'
            "</tr>"
            f'<tr id="detail-{i}" class="detail-row" style="display:none;">'
            f"<td colspan=\"10\">{detail}</td>"
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
    admin_badge = (
        '<span class="admin-badge">ADMIN</span>' if user.get("es_admin") else ""
    )

    filter_bar_html = ""
    if user.get("es_admin") and usuarios_list:
        all_active = " active" if not filtro_activo else ""
        btns = [f'<a href="/dashboard" class="filter-btn{all_active}">Todas las cuentas</a>']
        for u in usuarios_list:
            ig = u.get("ig_username") or ""
            if not ig:
                continue
            act = " active" if ig == filtro_activo else ""
            btns.append(
                f'<a href="/dashboard?filtro={html.escape(ig)}" class="filter-btn{act}">@{html.escape(ig)}</a>'
            )
        filter_bar_html = (
            '<div class="filter-bar"><span class="filter-label">Filtrar por cuenta:</span>'
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
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0f0f0f; color:#e0e0e0; font-family:'Courier New',Courier,monospace; }}

header {{
  background:#111; border-bottom:1px solid #1e1e1e;
  padding:14px 24px; display:flex; justify-content:space-between; align-items:center;
}}
h1 {{ font-size:1.35rem; color:#00ff88; letter-spacing:1px; }}
.refresh-info {{ font-size:0.78rem; color:#555; }}
.refresh-info span {{ color:#00ccff; }}

.header-right {{ display:flex; align-items:center; gap:14px; }}
.user-info {{ font-size:0.82rem; color:#bbb; }}
.user-info b {{ color:#00ccff; }}
.admin-badge {{
  display:inline-block; background:#3a0000; border:1px solid #ff4444;
  color:#ff4444; padding:2px 8px; border-radius:10px;
  font-size:0.65rem; font-weight:bold; letter-spacing:1px; margin-left:6px;
}}
.btn-logout {{
  background:#1a0a0a; border:1px solid #ff4444; color:#ff4444;
  padding:5px 12px; border-radius:4px; cursor:pointer;
  font-size:0.72rem; font-family:inherit; text-decoration:none;
}}
.btn-logout:hover {{ background:#ff4444; color:#000; }}

.container {{ padding:24px; max-width:1700px; margin:0 auto; }}

/* ── Cards ── */
.cards {{ display:flex; gap:14px; margin-bottom:26px; flex-wrap:wrap; }}
.card {{
  flex:1; min-width:155px; background:#131313;
  border:1px solid #232323; border-radius:6px; padding:18px;
}}
.card-label {{ font-size:0.72rem; color:#666; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }}
.card-value {{ font-size:2rem; font-weight:bold; }}
.card-value.total   {{ color:#00ccff; }}
.card-value.high    {{ color:#ff4444; }}
.card-value.medium  {{ color:#ffaa00; }}
.card-value.low     {{ color:#44ff88; }}
.card-value.ts      {{ font-size:0.82rem; color:#888; margin-top:4px; }}
.card-sub {{ font-size:0.68rem; color:#444; margin-top:5px; }}

/* ── Table ── */
.table-wrapper {{ overflow-x:auto; border-radius:6px; border:1px solid #222; }}
table {{ width:100%; border-collapse:collapse; }}
thead th {{
  background:#161616; color:#00ff88; padding:11px 10px;
  text-align:left; font-size:0.72rem; text-transform:uppercase;
  letter-spacing:1px; border-bottom:1px solid #2a2a2a; white-space:nowrap;
}}
.conv-row {{ cursor:pointer; transition:filter 0.12s; }}
.conv-row:hover {{ filter:brightness(1.35); }}
.conv-row td {{ padding:9px 10px; border-bottom:1px solid #181818; font-size:0.81rem; vertical-align:middle; }}
.mono   {{ font-family:'Courier New',Courier,monospace; }}
.small  {{ font-size:0.73rem; }}
.center {{ text-align:center; }}

.risk-badge {{
  display:inline-block; padding:3px 10px; border-radius:12px;
  font-size:0.72rem; font-weight:bold; color:#000;
}}
.alert-badge {{
  display:inline-block; padding:3px 9px; border-radius:10px;
  font-size:0.7rem; font-weight:bold; white-space:nowrap;
}}
.alert-badge.ok {{ background:#0a2d12; border:1px solid #44ff88; color:#44ff88; }}
.alert-badge.pending {{ background:#2d2000; border:1px solid #ffaa00; color:#ffaa00; }}
.btn-detail {{
  background:#0a1a0a; border:1px solid #00ff88; color:#00ff88;
  padding:4px 11px; border-radius:4px; cursor:pointer;
  font-size:0.72rem; font-family:inherit; white-space:nowrap;
}}
.btn-detail:hover {{ background:#00ff88; color:#000; }}

/* ── Detail row ── */
.detail-row td {{ background:#090909; padding:0; border-bottom:2px solid #2a2a2a; }}
.detail-section {{
  padding:18px 24px; display:grid;
  grid-template-columns:1fr 1fr; gap:14px;
}}
.detail-block {{
  background:#111; border:1px solid #1e1e1e;
  border-radius:4px; padding:14px;
}}
.full-width {{ grid-column:1 / -1; }}
.detail-label {{ font-size:0.68rem; text-transform:uppercase; letter-spacing:1px; color:#444; margin-bottom:8px; }}
.detail-value {{ font-size:0.8rem; color:#bbb; line-height:1.55; }}
.detail-value.mono {{ font-size:0.75rem; }}

.badge {{
  display:inline-block; background:#1a1000; border:1px solid #ffaa00;
  color:#ffaa00; padding:2px 8px; border-radius:10px;
  font-size:0.7rem; margin:2px;
}}
.url-item {{ font-size:0.76rem; padding:4px 0; border-bottom:1px solid #181818; }}
.url-text   {{ color:#ff6666; }}
.url-reason {{ color:#666; font-style:italic; }}

.msg-list {{ max-height:220px; overflow-y:auto; }}
.msg-row {{
  display:flex; gap:10px; padding:5px 0;
  border-bottom:1px solid #161616; font-size:0.73rem; flex-wrap:wrap;
}}
.msg-ts     {{ color:#444; min-width:138px; }}
.msg-dir    {{ color:#333; }}
.msg-sender {{ color:#00ccff; min-width:80px; }}
.msg-text   {{ color:#bbb; flex:1; word-break:break-all; }}

/* ── Action buttons ── */
.actions-block {{ border-color:#1a2a1a; background:#0a0f0a; }}
.action-btns {{ display:flex; gap:10px; flex-wrap:wrap; padding-top:4px; }}
.btn-action {{
  padding:8px 20px; border-radius:4px; cursor:pointer; border:1px solid;
  font-size:0.78rem; font-family:'Courier New',Courier,monospace;
  font-weight:bold; transition:all 0.15s;
}}
.btn-action:disabled {{ opacity:0.4; cursor:not-allowed; }}
.btn-responder {{ background:#0a1a0a; border-color:#00ff88; color:#00ff88; }}
.btn-responder:hover:not(:disabled) {{ background:#00ff88; color:#000; }}
.btn-notificar {{ background:#0a0a1a; border-color:#00ccff; color:#00ccff; }}
.btn-notificar:hover:not(:disabled) {{ background:#00ccff; color:#000; }}
.btn-action.success {{ border-color:#44ff88 !important; color:#44ff88 !important; background:#001a00 !important; }}
.btn-action.error   {{ border-color:#ff4444 !important; color:#ff4444 !important; background:#1a0000 !important; }}

/* ── Filter bar ── */
.filter-bar {{ display:flex; gap:8px; align-items:center; margin-bottom:20px; flex-wrap:wrap; }}
.filter-label {{ font-size:0.7rem; color:#555; text-transform:uppercase; letter-spacing:1px; margin-right:4px; }}
.filter-btn {{
  padding:5px 14px; border-radius:14px; border:1px solid #2a2a2a;
  color:#666; font-size:0.76rem; text-decoration:none;
  font-family:'Courier New',Courier,monospace; background:#131313;
}}
.filter-btn:hover {{ border-color:#00ccff; color:#00ccff; }}
.filter-btn.active {{ border-color:#00ff88; color:#00ff88; background:#0a1a0a; font-weight:bold; }}
</style>
</head>
<body>
<header>
  <h1>&#x1F6E1;&#xFE0F; Link Seguro &mdash; Dashboard de Phishing</h1>
  <div class="header-right">
    <span class="refresh-info">Próxima actualización en <span id="cd">30</span>s</span>
    <span class="user-info">Bienvenido, <b>@{username_html}</b>{admin_badge}</span>
    <a href="/logout" class="btn-logout">Cerrar sesión</a>
  </div>
</header>
<div class="container">

  <div class="cards">
    <div class="card">
      <div class="card-label">Total conversaciones</div>
      <div class="card-value total">{data["total"]}</div>
    </div>
    <div class="card">
      <div class="card-label">&#x1F534; HIGH risk</div>
      <div class="card-value high">{data["high_count"]}</div>
    </div>
    <div class="card">
      <div class="card-label">&#x1F7E1; MEDIUM risk</div>
      <div class="card-value medium">{data["medium_count"]}</div>
    </div>
    <div class="card">
      <div class="card-label">&#x1F7E2; LOW risk</div>
      <div class="card-value low">{data["low_count"]}</div>
    </div>
    <div class="card">
      <div class="card-label">Último análisis</div>
      <div class="card-value ts">{last}</div>
      <div class="card-sub">analizado_at (GMT-3 Mendoza)</div>
    </div>
  </div>

  {filter_bar_html}
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Usuario</th>
          <th>Riesgo</th>
          <th>Categoría de ataque</th>
          <th>Técnica MITRE</th>
          <th>Score</th>
          <th>Lifecycle</th>
          <th>Acción</th>
          <th>Alerta</th>
          <th>Último mensaje</th>
          <th>Detalle</th>
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
  var secs = 30;
  var el = document.getElementById('cd');
  setInterval(function () {{
    secs--;
    if (secs <= 0) secs = 30;
    el.textContent = secs;
  }}, 1000);
}})();

function toggleDetail(i) {{
  var row = document.getElementById('detail-' + i);
  var btn = document.getElementById('btn-' + i);
  if (row.style.display === 'none') {{
    row.style.display = '';
    btn.textContent = '▲ Cerrar';
  }} else {{
    row.style.display = 'none';
    btn.textContent = '▼ Ver';
  }}
}}

async function _accion(endpoint, btn, labelOk, labelErr) {{
  var original = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Enviando...';
  try {{
    var r = await fetch(endpoint, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: 'id_conversacion=' + encodeURIComponent(btn.dataset.id)
    }});
    var data = await r.json();
    if (data.ok) {{
      btn.textContent = '✅ ' + (data.message || labelOk);
      btn.classList.add('success');
    }} else {{
      btn.textContent = '❌ ' + (data.message || labelErr);
      btn.classList.add('error');
      setTimeout(function() {{
        btn.textContent = original;
        btn.classList.remove('error');
        btn.disabled = false;
      }}, 4000);
    }}
  }} catch(e) {{
    btn.textContent = '❌ Error de red';
    btn.classList.add('error');
    setTimeout(function() {{
      btn.textContent = original;
      btn.classList.remove('error');
      btn.disabled = false;
    }}, 4000);
  }}
}}

function accionResponder(btn) {{
  _accion('/dashboard/accion/responder', btn, 'DM enviado', 'No se pudo enviar');
}}

function accionNotificar(btn) {{
  _accion('/dashboard/accion/notificar', btn, 'Email enviado', 'No se pudo notificar');
}}
</script>
</body>
</html>"""


def _render_login(error: str = "") -> str:
    error_html = (
        f'<div class="login-error">{_e(error)}</div>' if error else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Link Seguro — Login</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background:#0f0f0f; color:#e0e0e0;
  font-family:'Courier New',Courier,monospace;
  min-height:100vh; display:flex; align-items:center; justify-content:center;
}}
.login-box {{
  background:#131313; border:1px solid #232323; border-radius:8px;
  padding:38px 34px; width:100%; max-width:380px;
}}
.login-title {{
  color:#00ff88; font-size:1.25rem; letter-spacing:1px;
  margin-bottom:6px; text-align:center;
}}
.login-sub {{
  color:#555; font-size:0.78rem; text-align:center; margin-bottom:26px;
}}
.field {{ margin-bottom:16px; }}
.field label {{
  display:block; font-size:0.7rem; color:#666;
  text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;
}}
.field input {{
  width:100%; padding:10px 12px; background:#0a0a0a;
  border:1px solid #2a2a2a; border-radius:4px;
  color:#e0e0e0; font-family:inherit; font-size:0.88rem;
}}
.field input:focus {{ outline:none; border-color:#00ff88; }}
.btn-submit {{
  width:100%; padding:11px; margin-top:8px;
  background:#0a1a0a; border:1px solid #00ff88; color:#00ff88;
  border-radius:4px; cursor:pointer; font-family:inherit;
  font-size:0.88rem; letter-spacing:1px;
}}
.btn-submit:hover {{ background:#00ff88; color:#000; }}
.login-error {{
  background:#2d0000; border:1px solid #ff4444; color:#ff4444;
  padding:9px 12px; border-radius:4px; font-size:0.78rem;
  margin-bottom:16px; text-align:center;
}}
</style>
</head>
<body>
  <form class="login-box" method="post" action="/login">
    <div class="login-title">&#x1F6E1;&#xFE0F; Link Seguro</div>
    <div class="login-sub">Dashboard de phishing</div>
    {error_html}
    <div class="field">
      <label for="username">Usuario o email</label>
      <input id="username" name="username" type="text" required autofocus autocomplete="username" placeholder="usuario o correo electrónico">
    </div>
    <div class="field">
      <label for="password">Contraseña</label>
      <input id="password" name="password" type="password" required autocomplete="current-password">
    </div>
    <button type="submit" class="btn-submit">Ingresar</button>
  </form>
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
