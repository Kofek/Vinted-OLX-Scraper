from fastapi import FastAPI
from datetime import datetime, timezone
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI(title="BotVinted API")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
CORS_ORIGINS_RAW = os.getenv("BACKEND_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        "botRunning": False,
        "serverTimeUtc": datetime.now(timezone.utc).isoformat(),
        "configLoaded": config_loaded,
        "categoriesCount": len(categories),
        "historyEntriesCount": total_history_entries,
        "missingHistoryFiles": missing_history_files,
        "message": "Status endpoint is connected to config and history files",
    }