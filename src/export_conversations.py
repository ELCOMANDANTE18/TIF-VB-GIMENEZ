"""
export_conversations.py
=======================
Exporta todas las conversaciones e historial de mensajes de la cuenta
de Instagram monitoreada (flia_test) a archivos JSON locales.

Uso:
    python export_conversations.py

Requiere:
    - .env con FLIA_TEST_TOKEN y FLIA_TEST_IG_USER_ID configurados
    - pip install httpx python-dotenv
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Configuración ─────────────────────────────────────────────
TOKEN = os.getenv("FLIA_TEST_TOKEN") or os.getenv("PAGE_ACCESS_TOKEN")
IG_USER_ID = os.getenv("FLIA_TEST_IG_USER_ID")
API_VERSION = "v25.0"
BASE_URL = f"https://graph.instagram.com/{API_VERSION}"
OUTPUT_DIR = Path("data/conversations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not TOKEN or not IG_USER_ID:
    raise ValueError("Faltan FLIA_TEST_TOKEN y FLIA_TEST_IG_USER_ID en el .env")


def get_conversations() -> list[dict]:
    """Obtiene todas las conversaciones con paginación cursor-based."""
    conversations = []
    base_url = f"{BASE_URL}/{IG_USER_ID}/conversations"
    params = {
        "platform": "instagram",
        "fields": "id,participants,updated_time",
        "access_token": TOKEN,
        "limit": 20,
    }

    print("Obteniendo conversaciones...")
    while True:
        response = httpx.get(base_url, params=params)
        data = response.json()

        if "error" in data:
            print(f"  Error: {data['error']['message']}")
            break

        batch = data.get("data", [])
        conversations.extend(batch)
        print(f"  → {len(batch)} conversaciones obtenidas (total: {len(conversations)})")

        # Cursor-based: el access_token se mantiene siempre en params
        after = data.get("paging", {}).get("cursors", {}).get("after")
        if after:
            params = {**params, "after": after}
        else:
            break

        time.sleep(0.3)

    return conversations


def get_messages(conversation_id: str) -> list[dict]:
    """Obtiene todos los mensajes de una conversación con paginación cursor-based."""
    messages = []
    base_url = f"{BASE_URL}/{conversation_id}/messages"
    params = {
        "fields": "message,from,created_time,attachments",
        "access_token": TOKEN,
        "limit": 50,
    }

    while True:
        response = httpx.get(base_url, params=params)
        data = response.json()

        if "error" in data:
            print(f"    Error al obtener mensajes: {data['error']['message']}")
            break

        batch = data.get("data", [])
        messages.extend(batch)

        # Cursor-based: access_token siempre incluido, sin depender de next URL
        after = data.get("paging", {}).get("cursors", {}).get("after")
        if after:
            params = {**params, "after": after}
        else:
            break

        time.sleep(0.2)

    return messages


def export_all():
    """Exporta todas las conversaciones y mensajes a JSON."""
    print("=" * 50)
    print("Exportador de conversaciones de Instagram")
    print("=" * 50)

    conversations = get_conversations()

    if not conversations:
        print("No se encontraron conversaciones.")
        return

    full_export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "ig_user_id": IG_USER_ID,
        "total_conversations": len(conversations),
        "conversations": [],
    }

    for i, conv in enumerate(conversations, 1):
        conv_id = conv["id"]
        participants = [
            p["username"]
            for p in conv.get("participants", {}).get("data", [])
        ]

        print(f"\nConversación {i}/{len(conversations)}: {' ↔ '.join(participants)}")

        messages = get_messages(conv_id)
        print(f"  → {len(messages)} mensajes obtenidos")

        conv_data = {
            "conversation_id": conv_id,
            "participants": conv.get("participants", {}).get("data", []),
            "updated_time": conv.get("updated_time"),
            "total_messages": len(messages),
            "messages": messages,
        }

        full_export["conversations"].append(conv_data)

        safe_name = "_".join(p.replace(".", "_") for p in participants)
        conv_file = OUTPUT_DIR / f"conv_{safe_name}.json"
        with open(conv_file, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, ensure_ascii=False, indent=2)
        print(f"  → Guardado en: {conv_file}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    full_file = OUTPUT_DIR / f"export_completo_{timestamp}.json"
    with open(full_file, "w", encoding="utf-8") as f:
        json.dump(full_export, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"Export completo guardado en: {full_file}")
    print(f"Total conversaciones: {len(conversations)}")
    total_msgs = sum(c["total_messages"] for c in full_export["conversations"])
    print(f"Total mensajes: {total_msgs}")
    print("=" * 50)

    return full_export


if __name__ == "__main__":
    export_all()
