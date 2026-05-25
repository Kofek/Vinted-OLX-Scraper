import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATUS_PATH = BASE_DIR / "data" / "state" / "bot_status.json"
_UNSET = object()


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_status_data():
    if not STATUS_PATH.exists():
        return {}
    try:
        with STATUS_PATH.open("r", encoding="utf-8") as status_file:
            return json.load(status_file)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid bot status JSON: %s", exc)
        return {}
    except OSError as exc:
        logger.warning("Could not read bot status file: %s", exc)
        return {}


def _save_status_data(payload):
    status_dir = STATUS_PATH.parent
    status_dir.mkdir(parents=True, exist_ok=True)
    temp_path = STATUS_PATH.with_suffix(".json.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as status_file:
            json.dump(payload, status_file, ensure_ascii=False, indent=2)
        temp_path.replace(STATUS_PATH)
    except OSError as exc:
        logger.warning("Could not write bot status file: %s", exc)
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def write_bot_status(running: bool,last_started_utc=_UNSET,last_stopped_utc=_UNSET,):
    """Writes global scraper process status. Use _UNSET to keep an existing timestamp."""
    current_data = _load_status_data()
    now_utc = utc_now_iso()

    if last_started_utc is _UNSET:
        started_value = current_data.get("last_started_utc")
    else:
        started_value = last_started_utc

    if last_stopped_utc is _UNSET:
        stopped_value = current_data.get("last_stopped_utc")
    else:
        stopped_value = last_stopped_utc

    payload = {
        "running": running,
        "last_heartbeat_utc": now_utc,
        "last_started_utc": started_value,
        "last_stopped_utc": stopped_value,
    }
    _save_status_data(payload)


def read_bot_running_status():
    if not STATUS_PATH.exists():
        return False, "status file not found"
    try:
        data = _load_status_data()
        if not data and STATUS_PATH.exists():
            return False, "status file has invalid JSON"
        running_value = data.get("running", False)
        return bool(running_value), "status file loaded"
    except Exception:
        return False, "status file read error"


def apply_heartbeat_staleness(bot_running, bot_status_message, stale_seconds):
    if not STATUS_PATH.exists() or not bot_running:
        return bot_running, bot_status_message

    try:
        data = _load_status_data()
        heartbeat_raw = data.get("last_heartbeat_utc")
        if not heartbeat_raw:
            return False, "status stale: missing last_heartbeat_utc"

        heartbeat_dt = datetime.fromisoformat(heartbeat_raw.replace("Z", "+00:00"))
        now_utc = datetime.now(timezone.utc)
        age_seconds = (now_utc - heartbeat_dt).total_seconds()

        if age_seconds > stale_seconds:
            return False, f"status stale: heartbeat older than {stale_seconds}s"

        return True, "status file loaded (heartbeat fresh)"
    except Exception:
        return False, "status stale: invalid heartbeat timestamp"


def get_scraper_running_status(stale_seconds=90):
    """Returns whether the scraper process is alive with a fresh heartbeat."""
    scraper_running, scraper_status_message = read_scraper_running_status()
    return apply_heartbeat_staleness(bot_running, bot_status_message, stale_seconds)


def mark_scraper_started():
    """Marks bot.py as running and clears the previous stop time."""
    write_bot_status(running=True, last_started_utc=utc_now_iso(), last_stopped_utc=None)


def mark_scraper_stopped():
    """Marks bot.py as stopped."""
    write_bot_status(running=False, last_stopped_utc=utc_now_iso())


def mark_scraper_heartbeat():
    """Refreshes heartbeat while keeping start/stop timestamps unchanged."""
    write_bot_status(running=True)
