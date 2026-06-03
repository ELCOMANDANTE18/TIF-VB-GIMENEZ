"""Limpia los análisis de la BD para poder probar el pipeline desde cero.

Borra SOLO analisis_conversacion y resetea risk levels en conversacion.
NO toca mensajes ni conversaciones.

Uso:
    cd src && python scripts/reset_analisis.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: no existe la BD en {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        total_analisis = conn.execute("SELECT COUNT(*) FROM analisis_conversacion").fetchone()[0]
        total_conv = conn.execute("SELECT COUNT(*) FROM conversacion").fetchone()[0]
        total_msg = conn.execute("SELECT COUNT(*) FROM mensaje").fetchone()[0]

        print()
        print("─" * 50)
        print("  Reset de análisis — Link Seguro")
        print("─" * 50)
        print(f"  Conversaciones (se mantienen): {total_conv}")
        print(f"  Mensajes       (se mantienen): {total_msg}")
        print(f"  Análisis       (se borrarán):  {total_analisis}")
        print("─" * 50)
        print()

        if total_analisis == 0:
            print("No hay análisis para borrar. La BD ya está limpia.")
            return

        respuesta = input("¿Confirmar limpieza de análisis? (s/n): ").strip().lower()
        if respuesta != "s":
            print("Operación cancelada.")
            return

        conn.execute("DELETE FROM analisis_conversacion")
        conn.execute("UPDATE conversacion SET risk_level_actual = 'LOW', risk_level_conversacion = 'LOW', observado_at = NULL")
        conn.execute("UPDATE analisis_conversacion SET respuesta_enviada = 0")
        conn.commit()

        print()
        print(f"  ✓ {total_analisis} análisis eliminados.")
        print(f"  ✓ {total_conv} conversaciones reseteadas a LOW.")
        print("  ✓ Mensajes intactos.")
        print()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
