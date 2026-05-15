"""
Import runtime stats from data/bots/runtime.json into bot_runtime.

Requires: bots already in DB (import_bots_json_to_postgres.py), migration bot_runtime applied.

Run from backend:
  python scripts/import_runtime_json_to_postgres.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_JSON = BASE_DIR / "data" / "bots" / "runtime.json"

UPSERT_SQL = """
INSERT INTO bot_runtime (
    bot_id, status, last_heartbeat_utc, last_started_utc, last_stopped_utc,
    items_found, success_rate, last_error
) VALUES (
    %(bot_id)s, %(status)s, %(last_heartbeat_utc)s, %(last_started_utc)s, %(last_stopped_utc)s,
    %(items_found)s, %(success_rate)s, %(last_error)s
)
ON CONFLICT (bot_id) DO UPDATE SET
    status = EXCLUDED.status,
    last_heartbeat_utc = EXCLUDED.last_heartbeat_utc,
    last_started_utc = EXCLUDED.last_started_utc,
    last_stopped_utc = EXCLUDED.last_stopped_utc,
    items_found = EXCLUDED.items_found,
    success_rate = EXCLUDED.success_rate,
    last_error = EXCLUDED.last_error;
"""


def parse_timestamp(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def row_from_entry(bot_id, entry):
    return {
        "bot_id": bot_id,
        "status": (entry.get("status") or "unknown")[:32],
        "last_heartbeat_utc": parse_timestamp(entry.get("lastHeartbeatUtc")),
        "last_started_utc": parse_timestamp(entry.get("lastStartedUtc")),
        "last_stopped_utc": parse_timestamp(entry.get("lastStoppedUtc")),
        "items_found": int(entry.get("itemsFound", 0) or 0),
        "success_rate": entry.get("successRate"),
        "last_error": entry.get("lastError"),
    }


def main():
    load_dotenv(BASE_DIR / ".env")
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        print("Brak DATABASE_URL w backend/.env", file=sys.stderr)
        return 1

    if not RUNTIME_JSON.exists():
        print(f"Brak pliku: {RUNTIME_JSON}", file=sys.stderr)
        return 1

    with RUNTIME_JSON.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        print("runtime.json: oczekiwany obiekt { bot_id: { ... } }", file=sys.stderr)
        return 1

    rows = []
    for bot_id, entry in payload.items():
        bot_id = str(bot_id).strip()
        if not bot_id or not isinstance(entry, dict):
            continue
        rows.append(row_from_entry(bot_id, entry))

    if not rows:
        print("Brak wpisów runtime do importu.", file=sys.stderr)
        return 1

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(UPSERT_SQL, row)
        conn.commit()

    print(f"Zaimportowano / zaktualizowano runtime dla {len(rows)} botów.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())