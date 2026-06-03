from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a tablas existentes (idempotente)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(conversacion)")}
    nuevas = {
        "risk_level_conversacion": "ALTER TABLE conversacion ADD COLUMN risk_level_conversacion TEXT DEFAULT 'LOW'",
        "observado_at":            "ALTER TABLE conversacion ADD COLUMN observado_at DATETIME",
    }
    for col, sql in nuevas.items():
        if col not in existing:
            conn.execute(sql)
            print(f"  Migración aplicada: columna '{col}' agregada a conversacion")

    existing_an = {row[1] for row in conn.execute("PRAGMA table_info(analisis_conversacion)")}
    nuevas_an = {
        "respuesta_enviada":    "ALTER TABLE analisis_conversacion ADD COLUMN respuesta_enviada INTEGER DEFAULT 0",
        "respuesta_enviada_at": "ALTER TABLE analisis_conversacion ADD COLUMN respuesta_enviada_at DATETIME",
    }
    for col, sql in nuevas_an.items():
        if col not in existing_an:
            conn.execute(sql)
            print(f"  Migración aplicada: columna '{col}' agregada a analisis_conversacion")
    conn.commit()


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _apply_migrations(conn)
    conn.commit()
    conn.close()
    print(f"Base de datos lista en {DB_PATH}")


if __name__ == "__main__":
    init_db()
