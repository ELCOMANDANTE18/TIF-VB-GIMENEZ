"""
Prueba de envío de emails — Link Seguro.

Escenarios que se envían a TODOS los usuarios con email real:
  1. Bienvenida        — onboarding al sistema
  2. Alerta HIGH       — phishing de credenciales crítico
  3. Alerta MEDIUM     — scam de premios, riesgo moderado

Uso:
    cd src && python scripts/test_email.py
"""
import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.notifications.email_notifier import send_email_alert, send_welcome_email

DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"

ALERT_SCENARIOS = [
    {
        "tipo": "HIGH",
        "sender_handle": "soporte_ig_oficial",
        "categoria": "Phishing de credenciales",
        "explanation": (
            "[PRUEBA] El remitente se hace pasar por soporte de Instagram y envía "
            "un enlace falso para capturar usuario y contraseña. "
            "La URL apunta a un dominio typosquatting (instagram-verify.com) "
            "no relacionado con Meta."
        ),
        "mitre": "T1566.004 — Spearphishing via Service",
    },
    {
        "tipo": "MEDIUM",
        "sender_handle": "marketing_premios2026",
        "categoria": "Scam de premios / Gift card",
        "explanation": (
            "[PRUEBA] El mensaje promete un premio o tarjeta de regalo para generar urgencia "
            "y llevar al usuario a un sitio externo donde se solicitan datos personales. "
            "Patrón de ingeniería social con principio de escasez (Cialdini)."
        ),
        "mitre": "T1598 — Phishing for Information",
    },
]


async def main() -> None:
    if not settings.ENABLE_EMAIL_ALERTS:
        print("ENABLE_EMAIL_ALERTS=false — activalo en .env y volvé a correr.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    usuarios = conn.execute(
        "SELECT username, ig_username, email FROM usuario_sistema ORDER BY id"
    ).fetchall()
    conn.close()

    usuarios = [(u, ig, em) for u, ig, em in usuarios if em and "@" in em]
    n = len(usuarios)

    smtp = dict(
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        smtp_password=settings.SMTP_PASSWORD,
        smtp_from=settings.SMTP_FROM,
    )

    # ── 1. Bienvenida ──────────────────────────────────────────
    print(f"\n{'='*54}")
    print(f"  1. EMAILS DE BIENVENIDA  ({n} usuarios)")
    print(f"{'='*54}")
    for username, ig_username, email in usuarios:
        ok = await send_welcome_email(
            to_email=email,
            username=username,
            ig_username=ig_username,
            dashboard_url="http://localhost:8000/dashboard",
            **smtp,
        )
        estado = "✅" if ok else "❌"
        print(f"  {estado}  @{(ig_username or username):<24} → {email}")

    # ── 2 & 3. Alertas ────────────────────────────────────────
    for s in ALERT_SCENARIOS:
        print(f"\n{'='*54}")
        print(f"  ALERTA {s['tipo']}  —  {s['categoria']}")
        print(f"{'='*54}")
        for username, ig_username, email in usuarios:
            ok = await send_email_alert(
                to_email=email,
                username=username,
                sender_handle=s["sender_handle"],
                risk_level=s["tipo"],
                categoria=s["categoria"],
                explanation=s["explanation"],
                mitre_technique=s["mitre"],
                **smtp,
            )
            estado = "✅" if ok else "❌"
            print(f"  {estado}  @{(ig_username or username):<24} → {email}")

    total = n * (1 + len(ALERT_SCENARIOS))
    print(f"\n  Total enviados: {total} emails ({n} usuarios × {1 + len(ALERT_SCENARIOS)} escenarios)\n")


if __name__ == "__main__":
    asyncio.run(main())
