from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import uuid
from logging_config import configure_logging
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from pydantic import BaseModel, Field

from bot_status import get_scraper_running_status, get_scraper_worker_snapshot

app = FastAPI(title="BotVinted API")
BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
configure_logging()

CORS_ORIGINS_RAW = os.getenv("BACKEND_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]
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

def collect_history_stats(bots):
    """Counts history file lines for bots stored in Postgres."""
    missing_history_files = []
    total_history_entries = 0
    seen_history_files = set()

    for bot in bots:
        history_file_rel = bot.get("historyFile")
        if not history_file_rel or history_file_rel in seen_history_files:
            continue
        seen_history_files.add(history_file_rel)

        history_path = BASE_DIR / history_file_rel
        if not history_path.exists():
            missing_history_files.append(str(history_file_rel))
            continue

        try:
            with history_path.open("r", encoding="utf-8") as history_file:
                total_history_entries += sum(1 for line in history_file if line.strip())
        except Exception:
            missing_history_files.append(str(history_file_rel))

    return total_history_entries, missing_history_files


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

BOT_BY_ID_SQL = """
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
WHERE b.id = %(bot_id)s
"""

INSERT_BOT_SQL = """
INSERT INTO bots (
    id, name, source, urls_olx, urls_vinted, webhook_url, prompt_text,
    enabled, history_file, created_at_utc, updated_at_utc
) VALUES (
    %(id)s, %(name)s, %(source)s, %(urls_olx)s, %(urls_vinted)s, %(webhook_url)s,
    %(prompt_text)s, %(enabled)s, %(history_file)s, %(created_at_utc)s, %(updated_at_utc)s
)
"""
INSERT_BOT_RUNTIME_SQL = """
INSERT INTO bot_runtime (bot_id, status, items_found)
VALUES (%(bot_id)s, %(status)s, %(items_found)s)
"""

UPDATE_BOT_SQL = """
UPDATE bots SET
    name = %(name)s,
    source = %(source)s,
    urls_olx = %(urls_olx)s,
    urls_vinted = %(urls_vinted)s,
    webhook_url = %(webhook_url)s,
    prompt_text = %(prompt_text)s,
    enabled = %(enabled)s,
    updated_at_utc = %(updated_at_utc)s
WHERE id = %(id)s
"""

DELETE_BOT_SQL = "DELETE FROM bots WHERE id = %(bot_id)s RETURNING history_file"

PAUSE_BOT_RUNTIME_SQL = """
INSERT INTO bot_runtime (bot_id, status, last_stopped_utc)
VALUES (%(bot_id)s, 'paused', %(now)s)
ON CONFLICT (bot_id) DO UPDATE SET
    status = 'paused',
    last_stopped_utc = %(now)s
"""

RESUME_BOT_RUNTIME_SQL = """
INSERT INTO bot_runtime (bot_id, status, items_found)
VALUES (%(bot_id)s, 'waiting', 0)
ON CONFLICT (bot_id) DO UPDATE SET
    status = 'waiting'
"""

SET_BOT_ENABLED_SQL = "UPDATE bots SET enabled = %(enabled)s, updated_at_utc = %(now)s WHERE id = %(bot_id)s"

class CreateBotBody(BaseModel):
    """Shape of JSON clients send when creating a bot."""
    name: str = Field(min_length=1, max_length=255)
    source: Literal["mixed", "olx", "vinted"] = "mixed"
    urlsOlx: list[str] = Field(default_factory=list)
    urlsVinted: list[str] = Field(default_factory=list)
    webhookUrl: str = Field(min_length=1, max_length=2048)
    promptText: str = Field(min_length=1, max_length=10000)
    enabled: bool = True


UpdateBotBody = CreateBotBody


def validate_bot_urls(source, urls_olx, urls_vinted):
    """Raises HTTP 400 when source and URL lists do not match."""
    source_norm = (source or "mixed").strip().lower()
    if source_norm == "olx" and not urls_olx:
        raise HTTPException(status_code=400, detail="source=olx requires at least one OLX URL")
    if source_norm == "vinted" and not urls_vinted:
        raise HTTPException(status_code=400, detail="source=vinted requires at least one Vinted URL")
    if source_norm == "mixed" and not urls_olx and not urls_vinted:
        raise HTTPException(status_code=400, detail="mixed source requires at least one OLX or Vinted URL")


def get_database_url():
    """Returns the DATABASE_URL from the env file."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise HTTPException(status_code=503, detail="DATABASE_URL not configured")
    return url

def generate_bot_id():
    """Generates a random UUID for a new bot."""
    return f"bot_{uuid.uuid4().hex[:8]}"

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

    url = get_database_url()
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(BOTS_WITH_RUNTIME_SQL)
                rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
    return [serialize_bot_list_item(row) for row in rows]

def fetch_bot_by_id(bot_id):
    """Returns one bot with runtime in API shape, or None if not found."""
    url = get_database_url()
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(BOT_BY_ID_SQL, {"bot_id": bot_id})
                row = cur.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
    if not row:
        return None
    return serialize_bot_list_item(row)

def create_bot_in_database(body):
    """Inserts into bots + bot_runtime and returns the created bot for the API."""
    bot_id = generate_bot_id()
    now_utc = datetime.now(timezone.utc)
    history_file = f"data/history/{bot_id}.txt"
    urls_olx = [u.strip() for u in body.urlsOlx if isinstance(u, str) and u.strip()]
    urls_vinted = [u.strip() for u in body.urlsVinted if isinstance(u, str) and u.strip()]
    validate_bot_urls(body.source, urls_olx, urls_vinted)

    bot_row = {
        "id": bot_id,
        "name": body.name.strip(),
        "source": body.source.strip()[:32],
        "urls_olx": Json(urls_olx),
        "urls_vinted": Json(urls_vinted),
        "webhook_url": body.webhookUrl,
        "prompt_text": body.promptText,
        "enabled": body.enabled,
        "history_file": history_file,
        "created_at_utc": now_utc,
        "updated_at_utc": now_utc,
    }
    runtime_row = {
        "bot_id": bot_id,
        "status": "waiting" if body.enabled else "paused",
        "items_found": 0,
    }

    url = get_database_url()
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(INSERT_BOT_SQL, bot_row)
                cur.execute(INSERT_BOT_RUNTIME_SQL, runtime_row)
            conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")

    return fetch_bot_by_id(bot_id)


def update_bot_in_database(bot_id, body):
    """Updates an existing bot row and returns it in API shape."""
    if not fetch_bot_by_id(bot_id):
        raise HTTPException(status_code=404, detail="Bot not found")

    urls_olx = [u.strip() for u in body.urlsOlx if isinstance(u, str) and u.strip()]
    urls_vinted = [u.strip() for u in body.urlsVinted if isinstance(u, str) and u.strip()]
    validate_bot_urls(body.source, urls_olx, urls_vinted)

    bot_row = {
        "id": bot_id,
        "name": body.name.strip(),
        "source": body.source.strip()[:32],
        "urls_olx": Json(urls_olx),
        "urls_vinted": Json(urls_vinted),
        "webhook_url": body.webhookUrl,
        "prompt_text": body.promptText,
        "enabled": body.enabled,
        "updated_at_utc": datetime.now(timezone.utc),
    }

    url = get_database_url()
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(UPDATE_BOT_SQL, bot_row)
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Bot not found")
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")

    return fetch_bot_by_id(bot_id)


def delete_bot_in_database(bot_id):
    """Deletes bot (runtime removed by CASCADE). Removes history file from disk if present."""
    url = get_database_url()
    history_rel = None
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(DELETE_BOT_SQL, {"bot_id": bot_id})
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Bot not found")
                history_rel = row.get("history_file")
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")

    if history_rel and str(history_rel).strip():
        history_path = Path(history_rel)
        if not history_path.is_absolute():
            history_path = BASE_DIR / history_path
        try:
            if history_path.is_file():
                history_path.unlink()
        except OSError:
            pass


def _ensure_bot_exists(bot_id):
    if not fetch_bot_by_id(bot_id):
        raise HTTPException(status_code=404, detail="Bot not found")


def pause_bot_in_database(bot_id):
    """Disables a bot and marks bot_runtime paused with a fresh last_stopped_utc."""
    _ensure_bot_exists(bot_id)
    now_utc = datetime.now(timezone.utc)
    url = get_database_url()
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    SET_BOT_ENABLED_SQL,
                    {"bot_id": bot_id, "enabled": False, "now": now_utc},
                )
                cur.execute(
                    PAUSE_BOT_RUNTIME_SQL,
                    {"bot_id": bot_id, "now": now_utc},
                )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
    return fetch_bot_by_id(bot_id)


def resume_bot_in_database(bot_id):
    """Enables a bot and sets bot_runtime to waiting (scraper picks it up on the next cycle)."""
    _ensure_bot_exists(bot_id)
    now_utc = datetime.now(timezone.utc)
    url = get_database_url()
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    SET_BOT_ENABLED_SQL,
                    {"bot_id": bot_id, "enabled": True, "now": now_utc},
                )
                cur.execute(
                    RESUME_BOT_RUNTIME_SQL,
                    {"bot_id": bot_id},
                )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")
    return fetch_bot_by_id(bot_id)


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
def status() -> dict[str, str | bool | int | list[str] | None]:
    """Returns scraper process status and bot/history summary from Postgres."""
    scraper_running, scraper_status_message = get_scraper_running_status(BOT_STATUS_STALE_SECONDS)
    worker_snapshot, _ = get_scraper_worker_snapshot()

    total_bots = 0
    enabled_bots_count = 0
    history_entries_count = 0
    missing_history_files = []

    try:
        bots = fetch_bots_from_database()
        total_bots = len(bots)
        enabled_bots_count = sum(1 for bot in bots if bot.get("enabled"))
        history_entries_count, missing_history_files = collect_history_stats(bots)
    except HTTPException:
        pass

    scraper_last_heartbeat = None
    scraper_last_started = None
    scraper_last_stopped = None
    if worker_snapshot:
        scraper_last_heartbeat = to_iso_string(worker_snapshot.get("last_heartbeat_utc"))
        scraper_last_started = to_iso_string(worker_snapshot.get("last_started_utc"))
        scraper_last_stopped = to_iso_string(worker_snapshot.get("last_stopped_utc"))

    return {
        "botRunning": scraper_running,
        "botStatusMessage": scraper_status_message,
        "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        "totalBots": total_bots,
        "enabledBotsCount": enabled_bots_count,
        "historyEntriesCount": history_entries_count,
        "missingHistoryFiles": missing_history_files,
        "scraperLastHeartbeatUtc": scraper_last_heartbeat,
        "scraperLastStartedUtc": scraper_last_started,
        "scraperLastStoppedUtc": scraper_last_stopped,
    }


@app.post("/api/bots", status_code=201)
def create_bot(body: CreateBotBody):
    """Creates a new bot in Postgres (bots + bot_runtime) and returns it in API shape."""
    return create_bot_in_database(body)


@app.patch("/api/bots/{bot_id}")
def update_bot(bot_id: str, body: UpdateBotBody):
    """Updates bot configuration in Postgres."""
    return update_bot_in_database(bot_id.strip(), body)


@app.delete("/api/bots/{bot_id}", status_code=204)
def delete_bot(bot_id: str):
    """Deletes a bot and its runtime row."""
    delete_bot_in_database(bot_id.strip())


@app.post("/api/bots/{bot_id}/pause")
def pause_bot(bot_id: str):
    """Pauses a bot (sets enabled=false; scraper updates runtime status)."""
    return pause_bot_in_database(bot_id.strip())


@app.post("/api/bots/{bot_id}/resume")
def resume_bot(bot_id: str):
    """Resumes a bot (sets enabled=true; scraper updates runtime status)."""
    return resume_bot_in_database(bot_id.strip())


@app.get("/api/bots")
def list_bots(page: int = Query(default=1, ge=1), pageSize: int = Query(default=6, ge=1, le=24)):
    """Lists bots with pagination and runtime status."""
    merged_bots_data = fetch_bots_from_database()
    active_bots_count = 0
    total_items_found = 0
    for bot in merged_bots_data:
        if bot.get("enabled"):
            active_bots_count += 1
        runtime = bot.get("runtime") or {}
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