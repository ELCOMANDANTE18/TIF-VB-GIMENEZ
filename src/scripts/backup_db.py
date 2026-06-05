"""
Exporta el contenido completo de la BD SQLite a un JSON de backup.
Guarda conversaciones + mensajes + análisis. No incluye usuarios del sistema.

Uso:
    cd src
    .venv/bin/python scripts/backup_db.py
    .venv/bin/python scripts/backup_db.py --out data/backups/mi_backup.json
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta la BD a un JSON de backup")
    parser.add_argument("--out", default=None, help="Ruta del archivo de salida (opcional)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: BD no encontrada en {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.out) if args.out else BACKUP_DIR / f"backup_{ts}.json"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Conversaciones
        convs = [dict(r) for r in conn.execute("SELECT * FROM conversacion").fetchall()]

        # Mensajes por conversación
        for conv in convs:
            msgs = conn.execute(
                "SELECT * FROM mensaje WHERE id_conversacion = ? ORDER BY timestamp_ig ASC",
                (conv["id_conversacion"],),
            ).fetchall()
            conv["mensajes"] = [dict(m) for m in msgs]

        # Análisis por conversación
        for conv in convs:
            analisis = conn.execute(
                "SELECT * FROM analisis_conversacion WHERE id_conversacion = ? ORDER BY id_analisis ASC",
                (conv["id_conversacion"],),
            ).fetchall()
            conv["analisis"] = [dict(a) for a in analisis]

        total_msgs = sum(len(c["mensajes"]) for c in convs)
        total_analisis = sum(len(c["analisis"]) for c in convs)

        backup = {
            "backup_at": datetime.now(tz=timezone.utc).isoformat(),
            "version": 1,
            "total_conversaciones": len(convs),
            "total_mensajes": total_msgs,
            "total_analisis": total_analisis,
            "conversaciones": convs,
        }

        out_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")

        print()
        print("─" * 50)
        print("  Backup completado — Link Seguro")
        print("─" * 50)
        print(f"  Conversaciones: {len(convs)}")
        print(f"  Mensajes:       {total_msgs}")
        print(f"  Análisis:       {total_analisis}")
        print(f"  Archivo:        {out_path}")
        print("─" * 50)
        print()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
