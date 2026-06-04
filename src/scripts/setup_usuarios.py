"""
Crea los usuarios iniciales del dashboard en la BD.
Idempotente: usar INSERT OR IGNORE. Ejecutar UNA SOLA VEZ manualmente.

Uso:
    cd src && python scripts/setup_usuarios.py
"""
import sqlite3
import sys
from pathlib import Path

try:
    import bcrypt
    USING_BCRYPT = True
except ImportError:
    import hashlib
    import os
    USING_BCRYPT = False


DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"


def hash_password(password: str) -> str:
    if USING_BCRYPT:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    salt = os.urandom(16).hex()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


USUARIOS = [
    {
        "username": "admin",
        "password": "admin123",
        "ig_user_id": None,
        "ig_username": None,
        "es_admin": 1,
        "email": "linkseguro.tif@gmail.com",
    },
    {
        "username": "flia_test",
        "password": "link2024",
        "ig_user_id": "17841428323852479",
        "ig_username": "fliagimenez2026",
        "es_admin": 0,
        "email": "fliagimenez2026@gmail.com",
    },
    {
        "username": "hernesto",
        "password": "link2024",
        "ig_user_id": "955769153705305",
        "ig_username": "hernestolopez2026",
        "es_admin": 0,
        "email": "hernestolopez2026@gmail.com",
    },
    {
        "username": "benja",
        "password": "link2024",
        "ig_user_id": "17841407634191670",
        "ig_username": "gimenezbenja2",
        "es_admin": 0,
        "email": "gimenezbenja2@gmail.com",
    },
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: no existe la BD en {DB_PATH}", file=sys.stderr)
        print("Ejecutá primero: python database/init_db.py", file=sys.stderr)
        sys.exit(1)

    if not USING_BCRYPT:
        print("ADVERTENCIA: bcrypt no disponible — usando SHA256+salt como fallback.")

    conn = sqlite3.connect(DB_PATH)
    try:
        for u in USUARIOS:
            conn.execute(
                """INSERT OR IGNORE INTO usuario_sistema
                   (username, password_hash, ig_user_id, ig_username, es_admin, email)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    u["username"],
                    hash_password(u["password"]),
                    u["ig_user_id"],
                    u["ig_username"],
                    u["es_admin"],
                    u.get("email", ""),
                ),
            )
            # Actualizar email en usuarios ya existentes
            conn.execute(
                "UPDATE usuario_sistema SET email = ? WHERE username = ?",
                (u.get("email", ""), u["username"]),
            )
        conn.commit()

        cur = conn.execute(
            "SELECT id, username, ig_user_id, ig_username, es_admin, creado_at "
            "FROM usuario_sistema ORDER BY id"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    print()
    print(f"Usuarios en la BD ({len(rows)} total):")
    print("-" * 78)
    print(f"{'ID':<4}{'username':<14}{'rol':<10}{'ig_user_id':<22}{'ig_username':<22}")
    print("-" * 78)
    for r in rows:
        rol = "ADMIN" if r[4] else "usuario"
        print(f"{r[0]:<4}{r[1]:<14}{rol:<10}{(r[2] or '—'):<22}{(r[3] or '—'):<22}")
    print("-" * 78)
    print()
    print("Listo. Las contraseñas NO se imprimen por seguridad.")


if __name__ == "__main__":
    main()
