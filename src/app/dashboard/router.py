import html
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

DB_PATH = Path(__file__).parent.parent.parent / "data" / "phishing_detector.db"

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
        return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)[:19]


def get_dashboard_data() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT risk_level_actual, COUNT(*) AS cnt FROM conversacion GROUP BY risk_level_actual"
        )
        risk_counts = {row["risk_level_actual"]: row["cnt"] for row in cur.fetchall()}

        cur = conn.execute("SELECT MAX(analizado_at) AS last FROM analisis_conversacion")
        row = cur.fetchone()
        last_analysis = row["last"] if row and row["last"] else None

        cur = conn.execute("""
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
                a.analizado_at
            FROM conversacion c
            LEFT JOIN analisis_conversacion a
                ON c.id_conversacion = a.id_conversacion
                AND a.id_analisis = (
                    SELECT MAX(id_analisis)
                    FROM analisis_conversacion
                    WHERE id_conversacion = c.id_conversacion
                )
            ORDER BY
                CASE c.risk_level_actual
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    ELSE 3
                END,
                c.ultimo_mensaje_at DESC
        """)
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


def _build_rows(conversations: list) -> str:
    if not conversations:
        return (
            '<tr><td colspan="9" style="text-align:center;padding:40px;color:#555;">'
            "No hay análisis registrados todavía</td></tr>"
        )

    RISK_COLOR = {"HIGH": "#ff4444", "MEDIUM": "#ffaa00", "LOW": "#44ff88"}
    RISK_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    ROW_BG = {"HIGH": "#2d0000", "MEDIUM": "#2d2000", "LOW": "#002d00"}

    rows = []
    for i, conv in enumerate(conversations):
        risk = conv.get("risk_level_actual") or "LOW"
        username = conv.get("participante_username") or conv.get("participante_id") or "unknown"

        badge_color = RISK_COLOR.get(risk, "#888")
        emoji = RISK_EMOJI.get(risk, "⚪")
        row_bg = ROW_BG.get(risk, "#111")

        score = conv.get("score_final")
        score_str = f"{score:.2f}" if score is not None else "—"

        ultimo_raw = conv.get("ultimo_mensaje_at")
        ultimo = _e(ultimo_raw[:19] if ultimo_raw else None)

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
            "</div>"
        )

        rows.append(
            f'<tr class="conv-row" style="background:{row_bg};" onclick="toggleDetail({i})">'
            f'<td class="mono">@{_e(username)}</td>'
            f'<td><span class="risk-badge" style="background:{badge_color};">{emoji} {risk}</span></td>'
            f'<td class="mono small">{_e(conv.get("categoria_ataque"))}</td>'
            f'<td class="mono small">{_e(conv.get("tecnica_mitre"))}</td>'
            f'<td class="mono center">{score_str}</td>'
            f'<td class="mono small">{_e(conv.get("etapa_lifecycle"))}</td>'
            f'<td class="mono small">{_e(conv.get("accion_recomendada"))}</td>'
            f'<td class="mono small">{ultimo}</td>'
            f'<td><button class="btn-detail" id="btn-{i}" onclick="event.stopPropagation();toggleDetail({i})">▼ Ver</button></td>'
            "</tr>"
            f'<tr id="detail-{i}" class="detail-row" style="display:none;">'
            f"<td colspan=\"9\">{detail}</td>"
            "</tr>"
        )

    return "\n".join(rows)


def render_html(data: dict) -> str:
    rows_html = _build_rows(data["conversations"])
    last = _e(data["last_analysis"])

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
</style>
</head>
<body>
<header>
  <h1>&#x1F6E1;&#xFE0F; Link Seguro &mdash; Dashboard de Phishing</h1>
  <span class="refresh-info">Próxima actualización en <span id="cd">30</span>s</span>
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
      <div class="card-sub">analizado_at (UTC)</div>
    </div>
  </div>

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
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    data = get_dashboard_data()
    return render_html(data)
