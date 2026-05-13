"""
Import botów z data/bots/bots.json do tabeli Postgres `bots`.

Wymagania:
  - DATABASE_URL w backend/.env
  - Wykonana migracja: alembic upgrade head (tabela bots)

Uruchomienie (z katalogu backend):
  python scripts/import_bots_json_to_postgres.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Json

BASE_DIR = Path(__file__).resolve().parent.parent
BOTS_JSON = BASE_DIR / "data" / "bots" / "bots.json"

UPSERT_SQL = """
INSERT INTO bots (
    id, name, source, urls_olx, urls_vinted, webhook_url, prompt_text,
    enabled, history_file, created_at_utc, updated_at_utc
) VALUES (
    %(id)s, %(name)s, %(source)s, %(urls_olx)s, %(urls_vinted)s, %(webhook_url)s,
    %(prompt_text)s, %(enabled)s, %(history_file)s, %(created_at_utc)s, %(updated_at_utc)s
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    source = EXCLUDED.source,
    urls_olx = EXCLUDED.urls_olx,
    urls_vinted = EXCLUDED.urls_vinted,
    webhook_url = EXCLUDED.webhook_url,
    prompt_text = EXCLUDED.prompt_text,
    enabled = EXCLUDED.enabled,
    history_file = EXCLUDED.history_file,
    created_at_utc = EXCLUDED.created_at_utc,
    updated_at_utc = EXCLUDED.updated_at_utc;
"""


def _parse_ts(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _row_from_item(item: dict) -> dict:
    bot_id = str(item.get("id", "")).strip()
    if not bot_id:
        raise ValueError("Bot bez id")

    urls_olx = item.get("urlsOlx") or []
    urls_vinted = item.get("urlsVinted") or []
    if not isinstance(urls_olx, list):
        urls_olx = []
    if not isinstance(urls_vinted, list):
        urls_vinted = []

    created = _parse_ts(item.get("createdAtUtc"))
    updated = _parse_ts(item.get("updatedAtUtc"))
    now_utc = datetime.now(timezone.utc)
    if created is None:
        created = updated or now_utc
    if updated is None:
        updated = created or now_utc

    return {
        "id": bot_id,
        "name": (item.get("name") or "Unnamed")[:255],
        "source": (item.get("source") or "mixed")[:32],
        "urls_olx": Json(urls_olx),
        "urls_vinted": Json(urls_vinted),
        "webhook_url": item.get("webhookUrl"),
        "prompt_text": item.get("promptText"),
        "enabled": bool(item.get("enabled", True)),
        "history_file": (item.get("historyFile") or "")[:512] or None,
        "created_at_utc": created,
        "updated_at_utc": updated,
    }


def main() -> int:
    load_dotenv(BASE_DIR / ".env")
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        print("Brak DATABASE_URL w backend/.env", file=sys.stderr)
        return 1

    if not BOTS_JSON.exists():
        print(f"Brak pliku: {BOTS_JSON}", file=sys.stderr)
        return 1

    with BOTS_JSON.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    items = payload.get("items")
    if not isinstance(items, list):
        print("bots.json: brak listy 'items'", file=sys.stderr)
        return 1

    rows = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        try:
            rows.append(_row_from_item(raw))
        except ValueError as e:
            print(f"Pominięto wpis: {e}", file=sys.stderr)

    if not rows:
        print("Brak poprawnych rekordów do importu.", file=sys.stderr)
        return 1

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(UPSERT_SQL, row)
        conn.commit()

    print(f"Zaimportowano / zaktualizowano {len(rows)} botów w Postgres.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
