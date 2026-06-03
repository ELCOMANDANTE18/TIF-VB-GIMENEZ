"""
Autenticación del dashboard: bcrypt + itsdangerous.
Sin JWT, sin librerías externas de auth.
"""
import hashlib
import os
import sqlite3
from pathlib import Path

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

try:
    import bcrypt
    USING_BCRYPT = True
except ImportError:
    USING_BCRYPT = False


DB_PATH = Path(__file__).parent.parent.parent / "data" / "phishing_detector.db"

SESSION_MAX_AGE = 8 * 60 * 60  # 8 horas en segundos
SESSION_SALT = "link-seguro-session"
COOKIE_NAME = "session"


def hash_password(password: str) -> str:
    if USING_BCRYPT:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    salt = os.urandom(16).hex()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith("sha256$"):
        try:
            _, salt, digest = hashed.split("$", 2)
        except ValueError:
            return False
        candidate = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return candidate == digest
    if USING_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
    return False


def get_usuario_by_username(username: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id, username, password_hash, ig_user_id, ig_username, es_admin "
            "FROM usuario_sistema WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SESSION_SECRET, salt=SESSION_SALT)


def create_session_token(user_data: dict) -> str:
    payload = {
        "id": user_data["id"],
        "username": user_data["username"],
        "ig_user_id": user_data.get("ig_user_id"),
        "es_admin": int(user_data.get("es_admin") or 0),
    }
    return _serializer().dumps(payload)


def verify_session_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        return _serializer().loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return verify_session_token(token)
