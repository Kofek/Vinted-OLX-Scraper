import logging
import os
from datetime import datetime, timezone

import psycopg

logger = logging.getLogger(__name__)

WORKER_ID = "main"

UPSERT_SCRAPER_STARTED_SQL = """
INSERT INTO scraper_worker (id, running, last_started_utc, last_heartbeat_utc, last_stopped_utc)
VALUES (%(worker_id)s, true, %(now)s, %(now)s, NULL)
ON CONFLICT (id) DO UPDATE SET
    running = true,
    last_started_utc = %(now)s,
    last_heartbeat_utc = %(now)s,
    last_stopped_utc = NULL
"""

UPSERT_SCRAPER_STOPPED_SQL = """
INSERT INTO scraper_worker (id, running, last_stopped_utc, last_heartbeat_utc)
VALUES (%(worker_id)s, false, %(now)s, %(now)s)
ON CONFLICT (id) DO UPDATE SET
    running = false,
    last_stopped_utc = %(now)s,
    last_heartbeat_utc = %(now)s
"""

UPSERT_SCRAPER_HEARTBEAT_SQL = """
INSERT INTO scraper_worker (id, running, last_heartbeat_utc)
VALUES (%(worker_id)s, true, %(now)s)
ON CONFLICT (id) DO UPDATE SET
    running = true,
    last_heartbeat_utc = %(now)s
"""

SELECT_SCRAPER_WORKER_SQL = """
SELECT running, last_heartbeat_utc, last_started_utc, last_stopped_utc
FROM scraper_worker
WHERE id = %(worker_id)s
"""


def _database_url():
    return (os.getenv("DATABASE_URL") or "").strip()


def _run_status_write(log_message, execute):
    """Opens one DB connection, runs execute(cur), commits, logs warnings on failure."""
    url = _database_url()
    if not url:
        logger.warning("DATABASE_URL not set — skipping %s", log_message)
        return

    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                execute(cur)
            conn.commit()
    except Exception as exc:
        logger.warning("%s failed: %s", log_message, exc)


def _load_scraper_worker():
    """Reads the singleton scraper_worker row from Postgres."""
    url = _database_url()
    if not url:
        return None, "DATABASE_URL not set"

    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_SCRAPER_WORKER_SQL, {"worker_id": WORKER_ID})
                row = cur.fetchone()
    except Exception as exc:
        logger.warning("Could not read scraper worker: %s", exc)
        return None, f"database read error: {exc}"

    if not row:
        return None, "scraper worker row not found"

    return {
        "running": bool(row[0]),
        "last_heartbeat_utc": row[1],
        "last_started_utc": row[2],
        "last_stopped_utc": row[3],
    }, "loaded from database"


def apply_heartbeat_staleness(scraper_running, scraper_status_message, stale_seconds, heartbeat_utc):
    """
    Treats running=true as offline when the last heartbeat is too old.

    bot.py may crash without calling mark_scraper_stopped, so running can stay true
    in Postgres. This checks last_heartbeat_utc against stale_seconds and returns
    (False, reason) when the scraper looks dead.
    """
    if not scraper_running:
        return scraper_running, scraper_status_message

    if heartbeat_utc is None:
        return False, "status stale: missing last_heartbeat_utc"

    try:
        now_utc = datetime.now(timezone.utc)
        if heartbeat_utc.tzinfo is None:
            heartbeat_utc = heartbeat_utc.replace(tzinfo=timezone.utc)
        age_seconds = (now_utc - heartbeat_utc).total_seconds()
        if age_seconds > stale_seconds:
            return False, f"status stale: heartbeat older than {stale_seconds}s"
        return True, "heartbeat fresh"
    except Exception:
        return False, "status stale: invalid heartbeat timestamp"


def get_scraper_running_status(stale_seconds=90):
    """Returns whether the scraper process is alive with a fresh heartbeat."""
    worker, message = _load_scraper_worker()
    if worker is None:
        return False, message

    return apply_heartbeat_staleness(
        worker["running"],
        message,
        stale_seconds,
        worker["last_heartbeat_utc"],
    )


def get_scraper_worker_snapshot():
    """Returns scraper_worker timestamps for API diagnostics."""
    return _load_scraper_worker()


def mark_scraper_started():
    """Marks bot.py as running and clears the previous stop time."""
    now_utc = datetime.now(timezone.utc)
    params = {"worker_id": WORKER_ID, "now": now_utc}

    def execute(cur):
        cur.execute(UPSERT_SCRAPER_STARTED_SQL, params)

    _run_status_write("Scraper started", execute)


def mark_scraper_stopped():
    """Marks bot.py as stopped."""
    now_utc = datetime.now(timezone.utc)
    params = {"worker_id": WORKER_ID, "now": now_utc}

    def execute(cur):
        cur.execute(UPSERT_SCRAPER_STOPPED_SQL, params)

    _run_status_write("Scraper stopped", execute)


def mark_scraper_heartbeat():
    """Refreshes heartbeat while keeping start/stop timestamps unchanged."""
    now_utc = datetime.now(timezone.utc)
    params = {"worker_id": WORKER_ID, "now": now_utc}

    def execute(cur):
        cur.execute(UPSERT_SCRAPER_HEARTBEAT_SQL, params)

    _run_status_write("Scraper heartbeat", execute)
