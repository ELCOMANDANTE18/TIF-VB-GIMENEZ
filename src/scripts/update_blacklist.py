#!/usr/bin/env python3
"""Descarga el CSV actualizado de PhishTank y reemplaza data/blacklist/phishtank.csv."""
import csv
import logging
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PHISHTANK_URL = "http://data.phishtank.com/data/online-valid.csv"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "blacklist" / "phishtank.csv"


def _count_urls(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def main() -> None:
    previous_count = _count_urls(OUTPUT_PATH)
    logger.info("CSV anterior: %d URLs", previous_count)

    logger.info("Descargando PhishTank desde %s", PHISHTANK_URL)
    with httpx.Client(timeout=60.0) as client:
        response = client.get(PHISHTANK_URL)
        response.raise_for_status()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(response.content)

    new_count = _count_urls(OUTPUT_PATH)
    diff = new_count - previous_count
    logger.info("CSV nuevo: %d URLs (%+d vs anterior)", new_count, diff)


if __name__ == "__main__":
    main()
