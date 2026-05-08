"""
Importa los archivos conv_*.json de data/conversations/ a Supabase.
Uso: python scripts/import_conversations.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Permite importar módulos de app/ sin instalar el paquete
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.db.supabase_client import save_message
from app.utils.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "conversations"


def _parse_timestamp(created_time: str) -> int:
    dt = datetime.strptime(created_time, "%Y-%m-%dT%H:%M:%S+0000")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


async def import_file(filepath: Path) -> tuple[int, int]:
    """Retorna (mensajes_importados, errores)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    participants = data.get("participants", [])
    if len(participants) < 2:
        logger.warning("Archivo %s sin 2 participantes, se omite", filepath.name)
        return 0, 0

    page_id = participants[0]["id"]
    external_id = participants[1]["id"]

    messages = data.get("messages", [])
    imported = 0
    errors = 0

    for msg in messages:
        sender_id = msg["from"]["id"]
        recipient_id = external_id if sender_id == page_id else page_id
        text = msg.get("message", "")
        message_id = msg["id"]
        timestamp = _parse_timestamp(msg["created_time"])

        if not text:
            logger.debug("Mensaje sin texto omitido: %s", message_id)
            continue

        try:
            conv_id = await save_message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                text=text,
                timestamp=timestamp,
                message_id=message_id,
            )
            logger.info(
                "  [OK] msg=%.30s | conv=%s | from=%s",
                message_id, conv_id, msg["from"]["username"],
            )
            imported += 1
        except Exception as exc:
            logger.error(
                "  [ERR] msg=%s | %s", message_id, exc
            )
            errors += 1

    return imported, errors


async def main() -> None:
    conv_files = sorted(DATA_DIR.glob("conv_*.json"))

    if not conv_files:
        print(f"No se encontraron archivos conv_*.json en {DATA_DIR}")
        return

    total_convs = 0
    total_imported = 0
    total_errors = 0

    for filepath in conv_files:
        print(f"\n→ Procesando: {filepath.name}")
        imported, errors = await import_file(filepath)
        total_convs += 1
        total_imported += imported
        total_errors += errors
        print(f"  Mensajes importados: {imported} | Errores: {errors}")

    print("\n" + "─" * 45)
    print(f"Total conversaciones procesadas: {total_convs}")
    print(f"Total mensajes importados:       {total_imported}")
    print(f"Errores:                         {total_errors}")
    print("─" * 45)


if __name__ == "__main__":
    asyncio.run(main())
