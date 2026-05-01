from fastapi import FastAPI
from datetime import datetime, timezone
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json


app = FastAPI(title="BotVinted API")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

load_dotenv(BASE_DIR / ".env")

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