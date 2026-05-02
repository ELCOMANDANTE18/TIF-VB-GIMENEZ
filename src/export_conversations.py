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
from datetime import datetime
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
    """Obtiene todas las conversaciones de la cuenta con paginación."""
    conversations = []
    url = f"{BASE_URL}/{IG_USER_ID}/conversations"
    params = {
        "platform": "instagram",
        "fields": "id,participants,updated_time",
        "access_token": TOKEN,
        "limit": 20,
    }

    print("Obteniendo conversaciones...")
    while url:
        response = httpx.get(url, params=params if "graph.instagram" in url else {})
        data = response.json()

        if "error" in data:
            print(f"Error: {data['error']['message']}")
            break

        batch = data.get("data", [])
        conversations.extend(batch)
        print(f"  → {len(batch)} conversaciones obtenidas (total: {len(conversations)})")

        # Paginación
        url = data.get("paging", {}).get("next")
        params = {}  # La URL de next ya incluye todos los params
        time.sleep(0.3)  # Rate limiting básico

    return conversations


def get_messages(conversation_id: str) -> list[dict]:
    """Obtiene todos los mensajes de una conversación con paginación."""
    messages = []
    url = f"{BASE_URL}/{conversation_id}/messages"
    params = {
        "fields": "message,from,created_time,attachments",
        "access_token": TOKEN,
        "limit": 50,
    }

    while url:
        response = httpx.get(url, params=params if "graph.instagram" in url else {})
        data = response.json()

        if "error" in data:
            print(f"    Error al obtener mensajes: {data['error']['message']}")
            break

        batch = data.get("data", [])
        messages.extend(batch)

        url = data.get("paging", {}).get("next")
        params = {}
        time.sleep(0.2)

    return messages


def export_all():
    """Exporta todas las conversaciones y mensajes a JSON."""
    print("=" * 50)
    print("Exportador de conversaciones de Instagram")
    print("=" * 50)

    # 1. Obtener todas las conversaciones
    conversations = get_conversations()

    if not conversations:
        print("No se encontraron conversaciones.")
        return

    # 2. Para cada conversación obtener los mensajes
    full_export = {
        "exported_at": datetime.now(datetime.UTC).isoformat(),
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

        # Guardar cada conversación individualmente también
        safe_name = "_".join(p.replace(".", "_") for p in participants)
        conv_file = OUTPUT_DIR / f"conv_{safe_name}.json"
        with open(conv_file, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, ensure_ascii=False, indent=2)
        print(f"  → Guardado en: {conv_file}")

    # 3. Guardar el export completo
    timestamp = datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
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
