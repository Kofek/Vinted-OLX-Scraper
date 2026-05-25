import logging
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

ACTIVE_BOTS_SQL = """
SELECT id, name, source, urls_olx, urls_vinted, webhook_url, prompt_text,
       enabled, history_file
FROM bots
WHERE enabled = true
ORDER BY id
"""


def _as_str_list(value):
    """Returns a list of non-empty URL strings from a JSONB field."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _validate_bot_row(base_dir, row):
    """
    Checks one bots table row and returns it ready for bot.py.
    Only change vs DB: full history path on disk and cleaned URL lists.
    Returns (bot, errors). bot is None when validation fails.
    """
    bot_id = str(row.get("id", "")).strip()
    name = (row.get("name") or "Unnamed").strip()
    errors = []

    if not bot_id:
        return None, ["Bot row without id"]

    webhook_url = (row.get("webhook_url") or "").strip()
    if not webhook_url:
        errors.append(f"[{bot_id} {name}] missing webhook_url")

    prompt_text = (row.get("prompt_text") or "").strip()
    if not prompt_text:
        errors.append(f"[{bot_id} {name}] missing prompt_text")

    urls_olx = _as_str_list(row.get("urls_olx"))
    urls_vinted = _as_str_list(row.get("urls_vinted"))
    source = (row.get("source") or "mixed").strip().lower()

    if source == "olx" and not urls_olx:
        errors.append(f"[{bot_id} {name}] source=olx but urls_olx is empty")
    elif source == "vinted" and not urls_vinted:
        errors.append(f"[{bot_id} {name}] source=vinted but urls_vinted is empty")
    elif source == "mixed" and not urls_olx and not urls_vinted:
        errors.append(f"[{bot_id} {name}] no urls_olx or urls_vinted")

    history_rel = (row.get("history_file") or "").strip()
    if not history_rel:
        errors.append(f"[{bot_id} {name}] missing history_file")

    if errors:
        return None, errors

    history_path = (base_dir / history_rel).resolve()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    bot = dict(row)
    bot["id"] = bot_id
    bot["name"] = name
    bot["source"] = source
    bot["webhook_url"] = webhook_url
    bot["prompt_text"] = prompt_text
    bot["urls_olx"] = urls_olx
    bot["urls_vinted"] = urls_vinted
    bot["history_file"] = str(history_path)
    return bot, []


def load_active_bots_from_database(base_dir, allow_empty=False):
    """Fetches enabled bots from Postgres (same column names as the bots table)."""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        _fail_config("DATABASE_URL not set in .env — bot cannot load configuration from database")

    errors = []
    active_bots = []

    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(ACTIVE_BOTS_SQL)
                rows = cur.fetchall()
    except Exception as exc:
        _fail_config(f"Database connection failed: {exc}")

    if not rows:
        if allow_empty:
            return []
        _fail_config("No enabled bots in database (bots WHERE enabled = true).\n")

    for row in rows:
        bot, row_errors = _validate_bot_row(base_dir, row)
        if row_errors:
            errors.extend(row_errors)
            continue
        if bot:
            active_bots.append(bot)

    if errors:
        _fail_config("Invalid bot rows:\n" + "\n".join(errors))

    if not active_bots and not allow_empty:
        _fail_config("No valid enabled bots after validation")

    return active_bots


def _fail_config(message):
    """Logs a fatal config error and stops the process."""
    logger.critical("Configuration failed:\n%s\n%s", "!" * 40, message)
    raise SystemExit(1)


def load_ai_env_config():
    """Reads Gemini API keys and model list from environment variables."""
    api_keys = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
    models = [m.strip() for m in os.getenv("MODELS_POOL", "").split(",") if m.strip()]

    errors = []
    if not api_keys:
        errors.append("Missing GEMINI_API_KEYS in .env")
    if not models:
        errors.append("Missing MODELS_POOL in .env")
    if errors:
        _fail_config("\n".join(errors))

    return api_keys, models


def validate_scraper_startup(base_dir):
    """
    Validates .env (AI keys) and database connectivity for bot.py.
    Does not require enabled bots — the main loop reloads them each cycle.
    """
    api_keys, models = load_ai_env_config()
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        _fail_config("DATABASE_URL not set in .env — bot cannot load configuration from database")

    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as exc:
        _fail_config(f"Database connection failed: {exc}")

    sep = "-" * 35
    logger.info(
        "\n%s\n"
        "SCRAPER STARTUP OK (Postgres)\n"
        "API Keys:    %s\n"
        "AI Models:   %s\n"
        "%s",
        sep,
        len(api_keys),
        len(models),
        sep,
    )
    return api_keys, models

