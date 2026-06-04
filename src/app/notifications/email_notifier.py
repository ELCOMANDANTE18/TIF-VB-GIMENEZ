"""Notificaciones por email al detectar phishing de riesgo alto.

Usa smtplib de la stdlib con STARTTLS (Gmail app password).
Nunca lanza excepción — retorna bool para que el caller decida.
"""

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils.logger import get_logger

logger = get_logger(__name__)

_RISK_COLOR = {
    "HIGH": ("#ff4444", "#2d0000", "🔴 ALTO"),
    "MEDIUM": ("#ffaa00", "#2d2000", "🟡 MEDIO"),
    "LOW": ("#44ff88", "#002d00", "🟢 BAJO"),
}


def _build_html(
    username: str,
    sender_handle: str,
    risk_level: str,
    categoria: str,
    explanation: str,
    mitre_technique: str,
) -> str:
    color, bg, label = _RISK_COLOR.get(risk_level.upper(), ("#888", "#1a1a1a", risk_level))
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ margin:0; padding:0; background:#f4f4f4; font-family:Arial,sans-serif; }}
  .wrapper {{ max-width:600px; margin:30px auto; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.12); }}
  .header {{ background:#0f0f0f; padding:28px 32px; text-align:center; }}
  .header h1 {{ color:#00ff88; margin:0; font-size:1.5rem; letter-spacing:1px; }}
  .header p {{ color:#888; margin:6px 0 0; font-size:0.85rem; }}
  .body {{ padding:28px 32px; }}
  .greeting {{ font-size:1rem; color:#222; margin-bottom:20px; }}
  .risk-badge {{
    display:inline-block; background:{bg}; border:2px solid {color};
    color:{color}; padding:6px 18px; border-radius:20px;
    font-weight:bold; font-size:1rem; margin-bottom:22px;
  }}
  .section-title {{ font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#999; margin-bottom:8px; margin-top:20px; }}
  .data-table {{ width:100%; border-collapse:collapse; }}
  .data-table td {{ padding:9px 12px; border-bottom:1px solid #f0f0f0; font-size:0.88rem; }}
  .data-table td:first-child {{ color:#999; width:38%; }}
  .data-table td:last-child {{ color:#222; font-weight:500; }}
  .explanation {{ background:#f9f9f9; border-left:3px solid {color}; padding:12px 16px; font-size:0.88rem; color:#444; line-height:1.6; margin-top:16px; border-radius:0 4px 4px 0; }}
  .rec-box {{ background:#f0faf5; border:1px solid #c3e6cb; border-radius:6px; padding:16px 20px; margin-top:20px; }}
  .rec-box p {{ margin:0 0 6px; font-size:0.85rem; color:#2d6a4f; }}
  .rec-box p:last-child {{ margin-bottom:0; }}
  .rec-box strong {{ color:#1b4332; }}
  .footer {{ background:#f8f8f8; border-top:1px solid #eee; padding:18px 32px; text-align:center; }}
  .footer p {{ margin:0; font-size:0.75rem; color:#aaa; line-height:1.7; }}
</style>
</head>
<body>
<div class="wrapper">

  <div class="header">
    <h1>🛡️ Link Seguro</h1>
    <p>Sistema de detección de phishing</p>
  </div>

  <div class="body">
    <p class="greeting">
      Hola <strong>@{username}</strong>, detectamos actividad sospechosa en tu cuenta de Instagram.
    </p>

    <div class="risk-badge">{label} RIESGO {risk_level.upper()}</div>

    <div class="section-title">Datos del análisis</div>
    <table class="data-table">
      <tr><td>Remitente</td><td>@{sender_handle}</td></tr>
      <tr><td>Tipo de ataque</td><td>{categoria}</td></tr>
      <tr><td>Técnica MITRE</td><td>{mitre_technique}</td></tr>
    </table>

    <div class="section-title">Análisis</div>
    <div class="explanation">{explanation or "Sin análisis detallado disponible."}</div>

    <div class="section-title">Recomendaciones</div>
    <div class="rec-box">
      <p>🚫 <strong>No hagas clic</strong> en links desconocidos o acortados.</p>
      <p>🔒 <strong>No compartas</strong> tu contraseña ni códigos OTP con nadie.</p>
      <p>✅ Si recibiste este email, podés ignorarlo con tranquilidad — tu sistema está funcionando.</p>
    </div>
  </div>

  <div class="footer">
    <p><strong>Link Seguro</strong> — Sistema de detección de phishing</p>
    <p>Universidad de Mendoza — Trabajo Integrador Final 2026</p>
    <p>Este es un mensaje automático, no respondas a este email.</p>
  </div>

</div>
</body>
</html>"""


def _send_sync(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
    return True


async def send_email_alert(
    to_email: str,
    username: str,
    sender_handle: str,
    risk_level: str,
    categoria: str,
    explanation: str,
    mitre_technique: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    smtp_from: str = "Link Seguro <no-reply@linkseguro.com>",
) -> bool:
    if not to_email or not smtp_user or not smtp_password:
        logger.warning("Email no enviado: faltan credenciales SMTP o email destino")
        return False

    subject = "🛡️ Link Seguro — Alerta de seguridad detectada"
    html_body = _build_html(username, sender_handle, risk_level, categoria, explanation, mitre_technique)

    try:
        await asyncio.to_thread(
            _send_sync,
            smtp_host, smtp_port, smtp_user, smtp_password,
            smtp_from, to_email, subject, html_body,
        )
        logger.info("Email de alerta enviado a %s (@%s)", to_email, username)
        return True
    except Exception as exc:
        logger.warning("No se pudo enviar email a %s: %s", to_email, exc)
        return False


def _build_welcome_html(username: str, ig_username: str | None, dashboard_url: str) -> str:
    handle = ig_username or username
    monitored_row = (
        f"      <tr><td>Cuenta monitoreada</td><td>@{handle}</td></tr>"
        if ig_username else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ margin:0; padding:0; background:#f4f4f4; font-family:Arial,sans-serif; }}
  .wrapper {{ max-width:600px; margin:30px auto; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.12); }}
  .header {{ background:#0f0f0f; padding:28px 32px; text-align:center; }}
  .header h1 {{ color:#00ff88; margin:0; font-size:1.5rem; letter-spacing:1px; }}
  .header p {{ color:#888; margin:6px 0 0; font-size:0.85rem; }}
  .body {{ padding:28px 32px; }}
  .greeting {{ font-size:1rem; color:#222; margin-bottom:20px; line-height:1.6; }}
  .welcome-badge {{
    display:inline-block; background:#e8fff5; border:2px solid #00c06a;
    color:#00804a; padding:6px 18px; border-radius:20px;
    font-weight:bold; font-size:0.95rem; margin-bottom:22px;
  }}
  .section-title {{ font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#999; margin-bottom:8px; margin-top:20px; }}
  .data-table {{ width:100%; border-collapse:collapse; }}
  .data-table td {{ padding:9px 12px; border-bottom:1px solid #f0f0f0; font-size:0.88rem; }}
  .data-table td:first-child {{ color:#999; width:38%; }}
  .data-table td:last-child {{ color:#222; font-weight:500; }}
  .info-box {{ background:#f0faf5; border:1px solid #c3e6cb; border-radius:6px; padding:16px 20px; margin-top:16px; }}
  .info-box p {{ margin:0 0 8px; font-size:0.85rem; color:#2d6a4f; line-height:1.5; }}
  .info-box p:last-child {{ margin-bottom:0; }}
  .btn-dashboard {{
    display:inline-block; margin-top:22px; padding:12px 28px;
    background:#0f0f0f; color:#00ff88; border-radius:4px;
    text-decoration:none; font-weight:bold; font-size:0.88rem; letter-spacing:0.5px;
  }}
  .footer {{ background:#f8f8f8; border-top:1px solid #eee; padding:18px 32px; text-align:center; }}
  .footer p {{ margin:0; font-size:0.75rem; color:#aaa; line-height:1.7; }}
</style>
</head>
<body>
<div class="wrapper">

  <div class="header">
    <h1>🛡️ Link Seguro</h1>
    <p>Sistema de detección de phishing en Instagram</p>
  </div>

  <div class="body">
    <p class="greeting">
      ¡Hola <strong>@{username}</strong>!<br>
      Tu cuenta fue registrada en <strong>Link Seguro</strong>, el sistema automático de
      detección de phishing de la Universidad de Mendoza.
    </p>

    <div class="welcome-badge">✅ Cuenta activa y monitoreada</div>

    <div class="section-title">Tu configuración</div>
    <table class="data-table">
      <tr><td>Usuario del sistema</td><td>{username}</td></tr>
{monitored_row}
    </table>

    <div class="section-title">¿Qué hace Link Seguro?</div>
    <div class="info-box">
      <p>🔍 <strong>Analiza</strong> automáticamente los mensajes directos que recibís en Instagram.</p>
      <p>⚡ <strong>Detecta</strong> URLs maliciosas, patrones de phishing e ingeniería social en tiempo real.</p>
      <p>📧 <strong>Te avisa por email</strong> cuando detecta una amenaza de riesgo alto.</p>
      <p>💬 <strong>Responde automáticamente</strong> al remitente sospechoso para advertirle.</p>
      <p>📊 <strong>Dashboard web</strong> con el historial completo de análisis y clasificación MITRE.</p>
    </div>

    <a href="{dashboard_url}" class="btn-dashboard">Ir al Dashboard →</a>
  </div>

  <div class="footer">
    <p><strong>Link Seguro</strong> — Sistema de detección de phishing</p>
    <p>Universidad de Mendoza — Trabajo Integrador Final 2026</p>
    <p>Este es un mensaje automático, no respondas a este email.</p>
  </div>

</div>
</body>
</html>"""


async def send_welcome_email(
    to_email: str,
    username: str,
    ig_username: str | None = None,
    dashboard_url: str = "http://localhost:8000/dashboard",
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    smtp_from: str = "Link Seguro <no-reply@linkseguro.com>",
) -> bool:
    if not to_email or not smtp_user or not smtp_password:
        logger.warning("Bienvenida no enviada: faltan credenciales SMTP o email destino")
        return False

    subject = "🛡️ Link Seguro — Bienvenido al sistema de protección"
    html_body = _build_welcome_html(username, ig_username, dashboard_url)

    try:
        await asyncio.to_thread(
            _send_sync,
            smtp_host, smtp_port, smtp_user, smtp_password,
            smtp_from, to_email, subject, html_body,
        )
        logger.info("Email de bienvenida enviado a %s (@%s)", to_email, username)
        return True
    except Exception as exc:
        logger.warning("No se pudo enviar bienvenida a %s: %s", to_email, exc)
        return False
