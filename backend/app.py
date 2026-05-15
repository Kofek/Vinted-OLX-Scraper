from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, timezone
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
from logging_config import configure_logging
import psycopg
from psycopg.rows import dict_row

app = FastAPI(title="BotVinted API")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


load_dotenv(BASE_DIR / ".env")
configure_logging()

CORS_ORIGINS_RAW = os.getenv("BACKEND_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]
STATUS_PATH = BASE_DIR / "data" / "state" / "bot_status.json"
BOT_STATUS_STALE_SECONDS = int(os.getenv("BOT_STATUS_STALE_SECONDS", "90"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def read_json_file(path: Path, default_value):
    if not path.exists():
        return default_value
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default_value

def read_bot_running_status() -> tuple[bool, str]:
    if not STATUS_PATH.exists():
        return False, "status file not found"
    try:
        with STATUS_PATH.open("r", encoding="utf-8") as status_file:
            data = json.load(status_file)
        running_value = data.get("running", False)
        return bool(running_value), "status file loaded"
    except json.JSONDecodeError:
        return False, "status file has invalid JSON"
    except Exception:
        return False, "status file read error"

def apply_heartbeat_staleness(bot_running: bool, bot_status_message: str) -> tuple[bool, str]:
    if not STATUS_PATH.exists() or not bot_running:
        return bot_running, bot_status_message

    try:
        with STATUS_PATH.open("r", encoding="utf-8") as status_file:
            data = json.load(status_file)

        heartbeat_raw = data.get("last_heartbeat_utc")
        if not heartbeat_raw:
            return False, "status stale: missing last_heartbeat_utc"

        heartbeat_dt = datetime.fromisoformat(heartbeat_raw.replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        age_seconds = (now_utc - heartbeat_dt).total_seconds()

        if age_seconds > BOT_STATUS_STALE_SECONDS:
            return False, f"status stale: heartbeat older than {BOT_STATUS_STALE_SECONDS}s"

        return True, "status file loaded (heartbeat fresh)"
    except Exception:
        return False, "status stale: invalid heartbeat timestamp"

def _db_error_hint(message: str):
    """Krótkie podpowiedzi do typowych problemów z Neon / Postgres."""
    lower = message.lower()
    if "password authentication failed" in lower or "invalid_password" in lower:
        return "Złe hasło użytkownika bazy — w Neon: reset hasła roli, nowy connection string do .env."
    if "connection refused" in lower or "could not connect" in lower:
        return "Host/port nieosiągalny — sprawdź URL, firewall; pierwsze połączenie po uśpieniu Neona może chwilę trwać."
    if "ssl" in lower or "tls" in lower or "certificate" in lower:
        return "SSL — w URL zostaw ?sslmode=require jak w panelu Neona."
    if "does not exist" in lower and "database" in lower:
        return "Zła nazwa bazy w URL — sprawdź fragment po ostatnim / (np. neondb)."
    if "could not translate host name" in lower or "name or service not known" in lower:
        return "DNS — literówka w hoście albo brak internetu."
    return "Sprawdź DATABASE_URL w backend/.env i uruchomienie uvicorn z katalogu backend."

BOTS_WITH_RUNTIME_SQL = """
SELECT
    b.id,
    b.name,
    b.source,
    b.urls_olx,
    b.urls_vinted,
    b.webhook_url,
    b.prompt_text,
    b.enabled,
    b.history_file,
    b.created_at_utc,
    b.updated_at_utc,
    r.status AS runtime_status,
    r.last_heartbeat_utc,
    r.last_started_utc,
    r.last_stopped_utc,
    r.items_found,
    r.success_rate,
    r.last_error
FROM bots b
LEFT JOIN bot_runtime r ON r.bot_id = b.id
ORDER BY b.id
"""

def to_iso_string(value):
    """Converts a datetime object to an ISO 8601 string in UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()

def serialize_bot_list_item(row):
    """
    Maps a joined bots + bot_runtime to a camelCase dictionary formatted for the frontend API.
    Ensures fallback values for missing fields and converts timestamps to ISO strings.
    """
    urls_olx = row.get("urls_olx")
    urls_vinted = row.get("urls_vinted")
    if not isinstance(urls_olx, list):
        urls_olx = []
    if not isinstance(urls_vinted, list):
        urls_vinted = []

    success_rate = row.get("success_rate")
    if success_rate is not None:
        success_rate = float(success_rate)

    return {
        "id": row["id"],
        "name": row.get("name") or "Unnamed bot",
        "source": row.get("source") or "mixed",
        "urlsOlx": urls_olx,
        "urlsVinted": urls_vinted,
        "webhookUrl": row.get("webhook_url"),
        "promptText": row.get("prompt_text") or "",
        "enabled": bool(row.get("enabled", False)),
        "historyFile": row.get("history_file"),
        "createdAtUtc": to_iso_string(row.get("created_at_utc")),
        "updatedAtUtc": to_iso_string(row.get("updated_at_utc")),
        "runtime": {
            "status": row.get("runtime_status") or "unknown",
            "lastHeartbeatUtc": to_iso_string(row.get("last_heartbeat_utc")),
            "lastStartedUtc": to_iso_string(row.get("last_started_utc")),
            "lastStoppedUtc": to_iso_string(row.get("last_stopped_utc")),
            "itemsFound": int(row.get("items_found") or 0),
            "successRate": success_rate,
            "lastError": row.get("last_error"),
        },
    }

def fetch_bots_from_database():
    """Fetches bots with runtime (LEFT JOIN) from PostgreSQL as camelCase dictionaries."""

    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(BOTS_WITH_RUNTIME_SQL)
                rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
    return [serialize_bot_list_item(row) for row in rows]

@app.get("/api/db-health")
def db_health() -> dict[str, str | bool]:
    """SELECT 1 przez psycopg. Uruchom: python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000 — sprawdź: /api/db-health"""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return {
            "databaseOk": False,
            "detail": "Brak zmiennej DATABASE_URL.",
            "hint": "Dodaj DATABASE_URL do backend/.env (Connection string z Neona).",
            "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        }
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {
            "databaseOk": True,
            "detail": "SELECT 1 OK",
            "hint": "",
            "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        detail = str(exc)
        return {
            "databaseOk": False,
            "detail": detail,
            "hint": _db_error_hint(detail),
            "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        }

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/status")
def status() -> dict[str, str | bool | int | list[str]]:
    categories: list[dict] = []
    missing_history_files: list[str] = []
    total_history_entries = 0
    config_loaded = False

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)
            categories = config_data.get("categories", [])
            config_loaded = True
    except Exception:
        config_loaded = False

    bot_running, bot_status_message = read_bot_running_status()
    bot_running, bot_status_message = apply_heartbeat_staleness(bot_running, bot_status_message)

    for category in categories:
        history_file_rel = category.get("history_file")
        if not history_file_rel:
            continue

        history_path = BASE_DIR / history_file_rel
        if not history_path.exists():
            missing_history_files.append(str(history_file_rel))
            continue

        try:
            with history_path.open("r", encoding="utf-8") as history_file:
                lines = [line.strip() for line in history_file if line.strip()]
                total_history_entries += len(lines)
        except Exception:
            missing_history_files.append(str(history_file_rel))

    return {
        "botRunning": bot_running,
        "botStatusMessage": bot_status_message,
        "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        "configLoaded": config_loaded,
        "categoriesCount": len(categories),
        "historyEntriesCount": total_history_entries,
        "missingHistoryFiles": missing_history_files,
        "message": "Status endpoint is connected to config and history files",
    }


@app.get("/api/bots")
def list_bots(page: int = Query(default=1, ge=1), pageSize: int = Query(default=6, ge=1, le=24)):
    merged_bots_data = fetch_bots_from_database()
    active_bots_count = 0
    total_items_found = 0
    for bot in merged_bots_data:
        runtime = bot.get("runtime") or {}
        if runtime.get("status") == "running":
            active_bots_count += 1
        total_items_found += int(runtime.get("itemsFound") or 0)
    total_bots = len(merged_bots_data)
    total_pages = (total_bots + pageSize - 1) // pageSize if total_bots > 0 else 1
    safe_page = min(page, total_pages)
    start_idx = (safe_page - 1) * pageSize
    end_idx = start_idx + pageSize
    page_items = merged_bots_data[start_idx:end_idx]
    return {
        "items": page_items,
        "pagination": {
            "page": safe_page,
            "pageSize": pageSize,
            "totalBots": total_bots,
            "totalPages": total_pages,
            "hasPrev": safe_page > 1,
            "hasNext": safe_page < total_pages,
        },
        "summary": {
            "activeBotsCount": active_bots_count,
            "totalItemsFound": total_items_found,
        },
        "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
    }