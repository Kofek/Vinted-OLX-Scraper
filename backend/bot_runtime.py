import logging
import os
from datetime import datetime, timezone

import psycopg

logger = logging.getLogger(__name__)

SYNC_RUNTIME_WITH_ENABLED_SQL = """
UPDATE bot_runtime r
SET
    status = CASE
        WHEN b.enabled = false THEN 'paused'
        WHEN b.enabled = true AND r.status IN ('paused', 'unknown') THEN 'waiting'
        ELSE r.status
    END,
    last_stopped_utc = CASE
        WHEN b.enabled = false AND r.status <> 'paused' THEN %(now)s
        ELSE r.last_stopped_utc
    END
FROM bots b
WHERE r.bot_id = b.id
  AND (
    (b.enabled = false AND r.status <> 'paused')
    OR (b.enabled = true AND r.status IN ('paused', 'unknown'))
  )
"""

SET_RUNTIME_STATUS_SQL = """
INSERT INTO bot_runtime (
    bot_id, status, last_started_utc, last_heartbeat_utc, last_error
)
VALUES (%(bot_id)s, %(status)s, %(now)s, %(now)s, %(error)s)
ON CONFLICT (bot_id) DO UPDATE SET
    status = EXCLUDED.status,
    last_heartbeat_utc = EXCLUDED.last_heartbeat_utc,
    last_started_utc = CASE
        WHEN EXCLUDED.status = 'running'
        THEN COALESCE(bot_runtime.last_started_utc, EXCLUDED.last_started_utc)
        ELSE bot_runtime.last_started_utc
    END,
    last_error = EXCLUDED.last_error
"""


def _database_url():
    return (os.getenv("DATABASE_URL") or "").strip()


def mark_bot_running(bot_id):
    """Marks a bot as actively processed by the scraper."""
    _set_runtime_status(bot_id, "running")


def mark_bot_error(bot_id, error_message):
    """Stores scraper failure details on the bot runtime row."""
    _set_runtime_status(bot_id, "error", error_message)


def _set_runtime_status(bot_id, status, error_message=None):
    now_utc = datetime.now(timezone.utc)
    error_text = None
    if error_message is not None:
        error_text = str(error_message or "Unknown error")[:2000]

    params = {
        "bot_id": bot_id,
        "status": status,
        "now": now_utc,
        "error": error_text,
    }

    def execute(cur):
        cur.execute(SET_RUNTIME_STATUS_SQL, params)

    _run_runtime_write(f"Runtime status update ({status}) for {bot_id}", execute)


def sync_runtime_with_enabled_flags():
    """Aligns bot_runtime.status with bots.enabled before each scraper cycle."""
    now_utc = datetime.now(timezone.utc)

    def execute(cur):
        cur.execute(SYNC_RUNTIME_WITH_ENABLED_SQL, {"now": now_utc})

    _run_runtime_write("Runtime sync", execute)


def _run_runtime_write(log_message, execute):
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
