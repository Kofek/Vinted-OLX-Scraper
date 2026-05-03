from fastapi import FastAPI, Query
from datetime import datetime, timezone
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
from logging_config import configure_logging

app = FastAPI(title="BotVinted API")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

BOTS_PATH = BASE_DIR / "data" / "bots" / "bots.json"
RUNTIME_PATH = BASE_DIR / "data" / "bots" / "runtime.json"

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
def list_bots(page: int = Query(default=1, ge=1),pageSize: int = Query(default=6, ge=1, le=24),):
    bots_json = read_json_file(BOTS_PATH, {"items": []})
    bots_data = bots_json.get("items", [])
    runtime_data = read_json_file(RUNTIME_PATH, {})
    if not isinstance(bots_data, list):
        bots_data = []
    merged_bots_data = []
    active_bots_count = 0
    total_items_found = 0
    for bot in bots_data:
        bot_id = str(bot.get("id", "")).strip()
        if not bot_id:
            continue

        runtime = runtime_data.get(bot_id, {}) if isinstance(runtime_data, dict) else {}
        status = runtime.get("status", "unknown")
        items_found = int(runtime.get("itemsFound", 0) or 0)
        success_rate = runtime.get("successRate")
        if status == "running":
            active_bots_count += 1
        total_items_found += items_found
        merged_bots_data.append(
            {
                "id": bot_id,
                "name": bot.get("name", "Unnamed bot"),
                "source": bot.get("source", "mixed"),
                "urlsOlx": bot.get("urlsOlx", []),
                "urlsVinted": bot.get("urlsVinted", []),
                "webhookUrl": bot.get("webhookUrl"),
                "enabled": bool(bot.get("enabled", False)),
                "promptText": bot.get("promptText", ""),
                "createdAtUtc": bot.get("createdAtUtc"),
                "updatedAtUtc": bot.get("updatedAtUtc"),
                "runtime": {
                    "status": status,
                    "lastHeartbeatUtc": runtime.get("lastHeartbeatUtc"),
                    "lastStartedUtc": runtime.get("lastStartedUtc"),
                    "lastStoppedUtc": runtime.get("lastStoppedUtc"),
                    "itemsFound": items_found,
                    "successRate": success_rate,
                    "lastError": runtime.get("lastError"),
                },
            }
        )
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