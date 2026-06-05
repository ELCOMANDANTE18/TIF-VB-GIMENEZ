"""
Restaura la BD desde un archivo de backup generado por backup_db.py.
Por defecto usa el backup más reciente en data/backups/.

Uso:
    cd src
    .venv/bin/python scripts/restore_db.py                             # backup más reciente
    .venv/bin/python scripts/restore_db.py --file data/backups/backup_20260605_120000.json
    .venv/bin/python scripts/restore_db.py --limpiar                   # limpia BD antes de restaurar
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


def _latest_backup() -> Path | None:
    backups = sorted(BACKUP_DIR.glob("backup_*.json"), reverse=True)
    return backups[0] if backups else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Restaura la BD desde un backup JSON")
    parser.add_argument("--file", default=None, help="Ruta del backup (default: el más reciente)")
    parser.add_argument("--limpiar", action="store_true", help="Limpia la BD antes de restaurar")
    args = parser.parse_args()

    backup_path = Path(args.file) if args.file else _latest_backup()
    if not backup_path or not backup_path.exists():
        print("ERROR: No se encontró ningún backup.", file=sys.stderr)
        print(f"Buscado en: {BACKUP_DIR}", file=sys.stderr)
        sys.exit(1)

    backup = json.loads(backup_path.read_text(encoding="utf-8"))

    if backup.get("version") != 1:
        print("ERROR: Formato de backup no reconocido.", file=sys.stderr)
        sys.exit(1)

    convs = backup["conversaciones"]

    print()
    print("─" * 55)
    print("  Restore de BD — Link Seguro")
    print("─" * 55)
    print(f"  Backup:         {backup_path.name}")
    print(f"  Generado:       {backup.get('backup_at', '—')}")
    print(f"  Conversaciones: {backup['total_conversaciones']}")
    print(f"  Mensajes:       {backup['total_mensajes']}")
    print(f"  Análisis:       {backup['total_analisis']}")
    print("─" * 55)
    print()

    if args.limpiar:
        print("  ⚠️  Se limpiarán todos los datos actuales de la BD.")
    else:
        print("  ℹ️  Modo additive: se insertan solo registros que no existen (ON CONFLICT IGNORE).")
    print()

    respuesta = input("¿Confirmar restore? (s/n): ").strip().lower()
    if respuesta != "s":
        print("Operación cancelada.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        if args.limpiar:
            conn.execute("DELETE FROM analisis_conversacion")
            conn.execute("DELETE FROM mensaje")
            conn.execute("DELETE FROM conversacion")
            conn.commit()
            print("\n  Datos anteriores eliminados.")

        conv_ok = msg_ok = analisis_ok = 0
        conv_skip = msg_skip = analisis_skip = 0

        for conv in convs:
            mensajes = conv.pop("mensajes", [])
            analisis = conv.pop("analisis", [])

            try:
                conn.execute(
                    """INSERT OR IGNORE INTO conversacion
                       (id_conversacion, cuenta_monitoreada, participante_id, participante_username,
                        risk_level_actual, risk_level_conversacion, total_mensajes,
                        primer_mensaje_at, ultimo_mensaje_at, observado_at)
                       VALUES (:id_conversacion, :cuenta_monitoreada, :participante_id, :participante_username,
                               :risk_level_actual, :risk_level_conversacion, :total_mensajes,
                               :primer_mensaje_at, :ultimo_mensaje_at, :observado_at)""",
                    conv,
                )
                if conn.execute("SELECT changes()").fetchone()[0]:
                    conv_ok += 1
                else:
                    conv_skip += 1
            except Exception as exc:
                print(f"  [WARN] conversacion {conv.get('id_conversacion')}: {exc}")
                conv_skip += 1

            for msg in mensajes:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO mensaje
                           (id_mensaje, id_conversacion, sender_id, recipient_id, texto,
                            timestamp_ig, es_entrante, ig_message_id)
                           VALUES (:id_mensaje, :id_conversacion, :sender_id, :recipient_id, :texto,
                                   :timestamp_ig, :es_entrante, :ig_message_id)""",
                        msg,
                    )
                    if conn.execute("SELECT changes()").fetchone()[0]:
                        msg_ok += 1
                    else:
                        msg_skip += 1
                except Exception as exc:
                    print(f"  [WARN] mensaje {msg.get('id_mensaje')}: {exc}")
                    msg_skip += 1

            for anal in analisis:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO analisis_conversacion
                           (id_analisis, id_mensaje_disparador, id_conversacion,
                            score_urls, score_texto, score_ia, score_final,
                            risk_level, categoria_ataque, tecnica_mitre,
                            principios_cialdini, etapa_lifecycle, urls_sospechosas,
                            accion_recomendada, explicacion_usuario, explicacion_analista,
                            mensajes_analizados, respuesta_enviada, respuesta_enviada_at,
                            analizado_at)
                           VALUES (:id_analisis, :id_mensaje_disparador, :id_conversacion,
                                   :score_urls, :score_texto, :score_ia, :score_final,
                                   :risk_level, :categoria_ataque, :tecnica_mitre,
                                   :principios_cialdini, :etapa_lifecycle, :urls_sospechosas,
                                   :accion_recomendada, :explicacion_usuario, :explicacion_analista,
                                   :mensajes_analizados, :respuesta_enviada, :respuesta_enviada_at,
                                   :analizado_at)""",
                        anal,
                    )
                    if conn.execute("SELECT changes()").fetchone()[0]:
                        analisis_ok += 1
                    else:
                        analisis_skip += 1
                except Exception as exc:
                    print(f"  [WARN] analisis {anal.get('id_analisis')}: {exc}")
                    analisis_skip += 1

        conn.commit()

        print()
        print("─" * 55)
        print("  Restore completado")
        print("─" * 55)
        print(f"  Conversaciones insertadas: {conv_ok}  (omitidas: {conv_skip})")
        print(f"  Mensajes insertados:       {msg_ok}  (omitidos: {msg_skip})")
        print(f"  Análisis insertados:       {analisis_ok}  (omitidos: {analisis_skip})")
        print("─" * 55)
        print()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
