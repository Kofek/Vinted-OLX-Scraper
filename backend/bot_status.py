import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATUS_PATH = BASE_DIR / "data" / "state" / "bot_status.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_bot_status(
    running: bool,
    last_started_utc: str | None = None,
    last_stopped_utc: str | None = None,
) -> None:
    status_dir = STATUS_PATH.parent
    status_dir.mkdir(parents=True, exist_ok=True)

    current_data: dict = {}
    if STATUS_PATH.exists():
        try:
            with STATUS_PATH.open("r", encoding="utf-8") as status_file:
                current_data = json.load(status_file)
        except Exception:
            current_data = {}

    now_utc = utc_now_iso()
    payload = {
        "running": running,
        "last_heartbeat_utc": now_utc,
        "last_started_utc": last_started_utc or current_data.get("last_started_utc"),
        "last_stopped_utc": last_stopped_utc or current_data.get("last_stopped_utc"),
    }

    with STATUS_PATH.open("w", encoding="utf-8") as status_file:
        json.dump(payload, status_file, ensure_ascii=False, indent=2)
