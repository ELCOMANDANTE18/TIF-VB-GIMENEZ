"""Migración one-shot: recalcula id_conversacion al hash bidireccional.

Antes, los id_conversacion se generaban como SHA256(sender + recipient)[:16],
que NO es bidireccional: A->B y B->A producían ids distintos y la misma
conversación quedaba partida en dos filas. La lógica ya fue corregida en
app/db/sqlite_client.py (usa sorted([sender, recipient])), pero los datos
históricos siguen con los ids viejos.

Este script:
  - Recalcula el id correcto = SHA256("".join(sorted([part, cuenta])))[:16].
  - Reapunta mensaje.id_conversacion y analisis_conversacion.id_conversacion.
  - Fusiona las filas de conversacion que colapsan al mismo id nuevo
    (eran la misma conversación invertida), sumando contadores y
    conservando todos los mensajes y análisis. NO borra datos: solo
    elimina la fila duplicada de conversacion tras consolidarla.
  - Es idempotente: si los ids ya están bien, no cambia nada.

Uso:
    cd src && .venv/bin/python scripts/migrate_conv_ids.py
"""

import hashlib
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "phishing_detector.db"

RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def correct_id(part_a: str, part_b: str) -> str:
    """Hash bidireccional: mismo resultado sin importar el orden."""
    a, b = sorted([part_a, part_b])
    return hashlib.sha256((a + b).encode()).hexdigest()[:16]


def max_risk(values) -> str:
    vals = [v for v in values if v in RISK_ORDER]
    if not vals:
        return "LOW"
    return max(vals, key=lambda v: RISK_ORDER[v])


def first_nonempty(values, default=""):
    for v in values:
        if v not in (None, ""):
            return v
    return default


def min_notnull(values):
    vals = [v for v in values if v not in (None, "")]
    return min(vals) if vals else None


def max_notnull(values):
    vals = [v for v in values if v not in (None, "")]
    return max(vals) if vals else None


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: no existe la base {DB_PATH}", file=sys.stderr)
        return 1

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = OFF")

    rows = con.execute(
        """SELECT id_conversacion, ig_conversation_id, cuenta_monitoreada,
                  participante_id, participante_username,
                  risk_level_actual, risk_level_conversacion,
                  primer_mensaje_at, ultimo_mensaje_at, observado_at, creada_at
           FROM conversacion"""
    ).fetchall()

    total_antes = len(rows)
    print(f"Conversaciones antes: {total_antes}")

    # Frecuencia de cada ID a través de todas las conversaciones. La cuenta
    # monitoreada (cuenta de IG del negocio) aparece en muchas conversaciones,
    # así desambiguamos la orientación al fusionar pares invertidos.
    freq = defaultdict(int)
    for r in rows:
        freq[r["participante_id"]] += 1
        freq[r["cuenta_monitoreada"]] += 1

    # Agrupar filas por id nuevo.
    groups = defaultdict(list)
    id_map = {}  # old_id -> new_id
    for r in rows:
        new_id = correct_id(r["participante_id"], r["cuenta_monitoreada"])
        id_map[r["id_conversacion"]] = new_id
        groups[new_id].append(r)

    total_despues = len(groups)
    fusionadas = total_antes - total_despues

    # Construir la fila canónica de cada grupo (en memoria).
    canonical = {}
    for new_id, grp in groups.items():
        if len(grp) == 1:
            r = grp[0]
            participante_id = r["participante_id"]
            cuenta_monitoreada = r["cuenta_monitoreada"]
        else:
            # Reorientar: la cuenta monitoreada es el ID más frecuente del par;
            # el participante (usuario externo) es el otro. Cualquier fila del
            # grupo comparte el mismo par {participante, cuenta}.
            id_a, id_b = sorted([grp[0]["participante_id"], grp[0]["cuenta_monitoreada"]])
            if freq[id_a] >= freq[id_b]:
                cuenta_monitoreada, participante_id = id_a, id_b
            else:
                cuenta_monitoreada, participante_id = id_b, id_a

        canonical[new_id] = {
            "id_conversacion": new_id,
            "ig_conversation_id": first_nonempty(r["ig_conversation_id"] for r in grp),
            "cuenta_monitoreada": cuenta_monitoreada,
            "participante_id": participante_id,
            "participante_username": first_nonempty(
                r["participante_username"] for r in grp
            ),
            "risk_level_actual": max_risk(r["risk_level_actual"] for r in grp),
            "risk_level_conversacion": max_risk(
                r["risk_level_conversacion"] for r in grp
            ),
            "primer_mensaje_at": min_notnull(r["primer_mensaje_at"] for r in grp),
            "ultimo_mensaje_at": max_notnull(r["ultimo_mensaje_at"] for r in grp),
            "observado_at": max_notnull(r["observado_at"] for r in grp),
            "creada_at": min_notnull(r["creada_at"] for r in grp),
        }

    try:
        con.execute("BEGIN")

        # Tabla temporal de mapeo old -> new para reapuntar las tablas hijas
        # de una sola pasada (sin colisiones de PK porque no tienen UNIQUE).
        con.execute("CREATE TEMP TABLE id_map(old TEXT PRIMARY KEY, new TEXT)")
        con.executemany(
            "INSERT INTO id_map(old, new) VALUES (?, ?)", list(id_map.items())
        )

        con.execute(
            """UPDATE mensaje
               SET id_conversacion = (
                   SELECT new FROM id_map WHERE old = mensaje.id_conversacion)
               WHERE id_conversacion IN (SELECT old FROM id_map)"""
        )
        con.execute(
            """UPDATE analisis_conversacion
               SET id_conversacion = (
                   SELECT new FROM id_map WHERE old = analisis_conversacion.id_conversacion)
               WHERE id_conversacion IN (SELECT old FROM id_map)"""
        )

        # Reconstruir conversacion desde las filas canónicas. total_mensajes se
        # recalcula contando los mensajes ya reapuntados (evita doble conteo).
        con.execute("DELETE FROM conversacion")
        for new_id, c in canonical.items():
            total = con.execute(
                "SELECT COUNT(*) FROM mensaje WHERE id_conversacion = ?", (new_id,)
            ).fetchone()[0]
            con.execute(
                """INSERT INTO conversacion
                   (id_conversacion, ig_conversation_id, cuenta_monitoreada,
                    participante_id, participante_username,
                    risk_level_actual, risk_level_conversacion, total_mensajes,
                    primer_mensaje_at, ultimo_mensaje_at, observado_at, creada_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    c["id_conversacion"], c["ig_conversation_id"],
                    c["cuenta_monitoreada"], c["participante_id"],
                    c["participante_username"], c["risk_level_actual"],
                    c["risk_level_conversacion"], total,
                    c["primer_mensaje_at"], c["ultimo_mensaje_at"],
                    c["observado_at"], c["creada_at"],
                ),
            )

        con.execute("DROP TABLE id_map")
        con.commit()
    except Exception:
        con.rollback()
        print("ERROR: migración revertida (rollback). No se modificó nada.",
              file=sys.stderr)
        raise
    finally:
        con.close()

    print(f"Conversaciones fusionadas: {fusionadas}")
    print(f"Conversaciones después: {total_despues}")
    if fusionadas == 0:
        print("Nada que migrar — los ids ya eran correctos (idempotente).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
