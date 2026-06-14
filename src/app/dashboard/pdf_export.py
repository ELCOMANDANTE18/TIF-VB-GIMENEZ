"""
Genera un PDF de reporte por conversación con información que no aparece
en el dashboard: desglose numérico de scores, explicación completa del analista,
principios de Cialdini, historial completo de mensajes.
"""

import html
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from weasyprint import HTML

DB_PATH = Path(__file__).parent.parent.parent / "data" / "phishing_detector.db"
TZ = ZoneInfo("America/Argentina/Mendoza")


def _e(value) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts, tz=TZ)
        else:
            dt = datetime.fromisoformat(str(ts)).replace(tzinfo=TZ)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(ts)


def _risk_color(level: str) -> str:
    return {"HIGH": "#C2554B", "MEDIUM": "#B59628", "LOW": "#6E8F73"}.get(level, "#8A8B85")


def _risk_label(level: str) -> str:
    return {"HIGH": "ALTO", "MEDIUM": "MEDIO", "LOW": "BAJO"}.get(level, level)


def _get_data(id_conversacion: str) -> dict | None:
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
                c.total_mensajes,
                c.primer_mensaje_at,
                c.ultimo_mensaje_at,
                a.score_urls,
                a.score_texto,
                a.score_ia,
                a.score_final,
                a.risk_level,
                a.categoria_ataque,
                a.tecnica_mitre,
                a.principios_cialdini,
                a.etapa_lifecycle,
                a.urls_sospechosas,
                a.accion_recomendada,
                a.explicacion_usuario,
                a.explicacion_analista,
                a.analizado_at
            FROM conversacion c
            LEFT JOIN analisis_conversacion a
                ON c.id_conversacion = a.id_conversacion
                AND a.id_analisis = (
                    SELECT MAX(id_analisis) FROM analisis_conversacion
                    WHERE id_conversacion = c.id_conversacion
                )
            WHERE c.id_conversacion = ?""",
            (id_conversacion,),
        )
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)

        MSG_LIMIT = 100
        cur = conn.execute(
            """SELECT sender_id, es_entrante, texto, timestamp_ig
               FROM mensaje WHERE id_conversacion = ?
               ORDER BY timestamp_ig DESC LIMIT ?""",
            (id_conversacion, MSG_LIMIT),
        )
        data["mensajes"] = list(reversed([dict(r) for r in cur.fetchall()]))
        data["mensajes_truncados"] = data["total_mensajes"] > MSG_LIMIT

        for field in ("principios_cialdini", "urls_sospechosas"):
            try:
                data[field] = json.loads(data[field] or "[]")
            except (json.JSONDecodeError, TypeError):
                data[field] = []

        return data
    finally:
        conn.close()


def _build_html(data: dict) -> str:
    id_conv = data["id_conversacion"]
    risk_level = data.get("risk_level") or data.get("risk_level_actual") or "LOW"
    risk_color = _risk_color(risk_level)
    risk_label = _risk_label(risk_level)
    username = data.get("participante_username") or f"...{(data.get('participante_id') or '')[-8:]}"
    now = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")

    s_url = data.get("score_urls") or 0.0
    s_txt = data.get("score_texto") or 0.0
    s_ia = data.get("score_ia") or 0.0
    s_fin = data.get("score_final") or 0.0

    def bar(score: float) -> str:
        w = min(int(score * 80), 80)
        return (
            f'<span style="display:inline-block;width:80px;height:6px;'
            f'background:#ECEAE3;border-radius:3px;vertical-align:middle;">'
            f'<span style="display:inline-block;width:{w}px;height:6px;'
            f'background:{risk_color};border-radius:3px;"></span></span>'
        )

    # Historial de mensajes (máx 100, los más recientes)
    total_msgs = data.get("total_mensajes", 0)
    truncado = data.get("mensajes_truncados", False)
    msgs_header = (
        f'Historial completo — {total_msgs} mensajes'
        if not truncado
        else f'Últimos 100 mensajes de {total_msgs} totales'
    )

    msgs_html = ""
    for m in data.get("mensajes", []):
        es_entrante = bool(m.get("es_entrante"))
        bg = "#FFF5F5" if es_entrante else "#F0F4F0"
        border = "#C2554B" if es_entrante else "#6E8F73"
        tipo = "Entrante" if es_entrante else "Saliente"
        msgs_html += (
            f'<div style="padding:8px 12px;margin-bottom:6px;border-radius:0 6px 6px 0;'
            f'background:{bg};border-left:3px solid {border};">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
            f'<span style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.05em;color:{border};">{tipo}</span>'
            f'<span style="font-size:9px;color:#8A8B85;">{_fmt_ts(m.get("timestamp_ig"))}</span>'
            f'</div>'
            f'<div style="font-size:11px;word-break:break-word;">{_e(m.get("texto", ""))}</div>'
            f'</div>'
        )

    # URLs sospechosas
    urls_html = ""
    for u in data.get("urls_sospechosas", []):
        if isinstance(u, dict):
            url_txt = _e(u.get("url", ""))
            razon = _e(u.get("razon") or u.get("reason", ""))
            urls_html += f'<li><code>{url_txt}</code> — {razon}</li>'
        else:
            urls_html += f'<li><code>{_e(str(u))}</code></li>'

    urls_section = ""
    if data.get("urls_sospechosas"):
        urls_section = f"""
        <div class="section">
          <div class="section-title">URLs sospechosas detectadas</div>
          <ul style="padding-left:16px;font-size:11px;">{urls_html}</ul>
        </div>"""

    cialdini = data.get("principios_cialdini", [])
    cialdini_str = ", ".join(_e(p) for p in cialdini) if cialdini else "—"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; color: #1B1D1C; font-size: 11px; line-height: 1.5; padding: 28px; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #ECEAE3; padding-bottom: 14px; margin-bottom: 18px; }}
  .h-title {{ font-size: 18px; font-weight: 700; }}
  .h-sub {{ font-size: 10px; color: #8A8B85; margin-top: 3px; }}
  .h-meta {{ text-align: right; font-size: 9px; color: #8A8B85; }}
  .section {{ margin-bottom: 18px; }}
  .section-title {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #8A8B85; border-bottom: 1px solid #ECEAE3; padding-bottom: 5px; margin-bottom: 10px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .card {{ background: #F9F8F5; border: 1px solid #ECEAE3; border-radius: 5px; padding: 10px; }}
  .card-label {{ font-size: 9px; color: #8A8B85; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 3px; }}
  .card-value {{ font-size: 12px; font-weight: 600; }}
  .score-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .score-table th {{ background: #F9F8F5; font-size: 9px; text-transform: uppercase; color: #8A8B85; padding: 5px 8px; text-align: left; border-bottom: 1px solid #ECEAE3; }}
  .score-table td {{ padding: 6px 8px; border-bottom: 1px solid #ECEAE3; }}
  .score-table tr:last-child td {{ font-weight: 700; background: #F9F8F5; }}
  .expl {{ background: #F9F8F5; border-left: 3px solid #6E8F73; padding: 9px 13px; border-radius: 0 5px 5px 0; font-size: 11px; line-height: 1.6; margin-bottom: 8px; }}
  .expl-analista {{ border-left-color: #B59628; font-family: monospace; font-size: 10px; }}
  code {{ font-family: monospace; font-size: 10px; background: #ECEAE3; padding: 1px 4px; border-radius: 2px; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 3px; font-weight: 700; font-size: 12px; color: white; background: {risk_color}; }}
  .footer {{ margin-top: 22px; padding-top: 10px; border-top: 1px solid #ECEAE3; font-size: 9px; color: #8A8B85; display: flex; justify-content: space-between; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="h-title">Link Seguro — Reporte de Análisis</div>
    <div class="h-sub">Conversación <code>{_e(id_conv)}</code></div>
  </div>
  <div class="h-meta">Generado: {now}<br>Sistema v0.5.0</div>
</div>

<div class="section">
  <div class="section-title">Evaluación de riesgo</div>
  <div class="grid">
    <div class="card">
      <div class="card-label">Nivel de riesgo</div>
      <div style="margin-top:5px;"><span class="badge">{risk_label}</span></div>
    </div>
    <div class="card">
      <div class="card-label">Score final</div>
      <div class="card-value" style="color:{risk_color};">{s_fin:.1%}</div>
    </div>
    <div class="card">
      <div class="card-label">Participante</div>
      <div class="card-value">@{_e(username)}</div>
    </div>
    <div class="card">
      <div class="card-label">Total de mensajes</div>
      <div class="card-value">{data.get('total_mensajes', 0)}</div>
    </div>
    <div class="card">
      <div class="card-label">Primer mensaje</div>
      <div class="card-value">{_fmt_ts(data.get('primer_mensaje_at'))}</div>
    </div>
    <div class="card">
      <div class="card-label">Último mensaje</div>
      <div class="card-value">{_fmt_ts(data.get('ultimo_mensaje_at'))}</div>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Desglose de scores (detalle no visible en el dashboard)</div>
  <table class="score-table">
    <thead>
      <tr><th>Componente</th><th>Score</th><th>Peso</th><th>Aporte</th><th>Visualización</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>Análisis de URLs</td>
        <td>{s_url:.1%}</td><td>60 %</td><td>{s_url * 0.6:.1%}</td>
        <td>{bar(s_url)}</td>
      </tr>
      <tr>
        <td>Análisis de texto</td>
        <td>{s_txt:.1%}</td><td>40 %</td><td>{s_txt * 0.4:.1%}</td>
        <td>{bar(s_txt)}</td>
      </tr>
      <tr>
        <td>Confianza IA (UM Cloud)</td>
        <td>{s_ia:.1%}</td><td>—</td><td>—</td>
        <td>{bar(s_ia)}</td>
      </tr>
      <tr>
        <td>Score final (combinado)</td>
        <td style="color:{risk_color};">{s_fin:.1%}</td><td>—</td><td>—</td>
        <td>{bar(s_fin)}</td>
      </tr>
    </tbody>
  </table>
</div>

<div class="section">
  <div class="section-title">Clasificación IA — gemma4-26b (UM Cloud)</div>
  <div class="grid">
    <div class="card">
      <div class="card-label">Categoría de ataque</div>
      <div class="card-value"><code>{_e(data.get('categoria_ataque') or '—')}</code></div>
    </div>
    <div class="card">
      <div class="card-label">Técnica MITRE ATT&amp;CK</div>
      <div class="card-value"><code>{_e(data.get('tecnica_mitre') or '—')}</code></div>
    </div>
    <div class="card">
      <div class="card-label">Etapa del lifecycle</div>
      <div class="card-value">{_e(data.get('etapa_lifecycle') or '—')}</div>
    </div>
    <div class="card">
      <div class="card-label">Acción recomendada</div>
      <div class="card-value"><code>{_e(data.get('accion_recomendada') or '—')}</code></div>
    </div>
  </div>
  <div style="margin-top:10px;">
    <div class="card-label" style="margin-bottom:5px;">Principios de Cialdini detectados</div>
    <div style="font-size:11px;">{cialdini_str}</div>
  </div>
</div>

{urls_section}

<div class="section">
  <div class="section-title">Explicaciones completas</div>
  <div class="card-label" style="margin-bottom:5px;">Para el usuario final</div>
  <div class="expl">{_e(data.get('explicacion_usuario') or '—')}</div>
  <div class="card-label" style="margin-bottom:5px;margin-top:10px;">Para el analista (detalle técnico)</div>
  <div class="expl expl-analista">{_e(data.get('explicacion_analista') or '—')}</div>
</div>

<div class="section">
  <div class="section-title">{msgs_header}</div>
  {msgs_html or '<p style="color:#8A8B85;">Sin mensajes registrados.</p>'}
</div>

<div class="footer">
  <span>Link Seguro v0.5.0 · TIF Ingeniería en Sistemas UM · Análisis automático de phishing en Instagram DMs</span>
  <span>Conv: <code>{_e(id_conv)}</code> · {now}</span>
</div>

</body>
</html>"""


def render_pdf(id_conversacion: str) -> bytes | None:
    data = _get_data(id_conversacion)
    if not data:
        return None
    return HTML(string=_build_html(data)).write_pdf()
