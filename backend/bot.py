import logging
import random
import time
from pathlib import Path

from dotenv import load_dotenv

from bot_ai import init_ai
from bot_config import load_active_bots_from_database, validate_scraper_startup
from bot_scan import scan_bot
from bot_runtime import sync_runtime_with_enabled_flags
import bot_state
from bot_status import mark_scraper_heartbeat, mark_scraper_started, mark_scraper_stopped
from logging_config import configure_logging

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
configure_logging()
logger = logging.getLogger(Path(__file__).stem)

API_KEYS_POOL, MODELS_POOL = validate_scraper_startup(BASE_DIR)
init_ai(API_KEYS_POOL, MODELS_POOL)


def main():
    logger.info("🚀 BOT STARTING...")
    mark_scraper_started()

    while True:
        mark_scraper_heartbeat()
        sync_runtime_with_enabled_flags()

        active_bots = load_active_bots_from_database(BASE_DIR, allow_empty=True)
        if not active_bots:
            logger.info("💤 No enabled bots — waiting for user to enable one…")
            time.sleep(15)
            continue

        for bot in active_bots:
            scan_bot(bot)

        if bot_state.is_first_run:
            logger.info("\n✅ Initial databases loaded. Waiting for new items.")
            bot_state.finish_initial_scan()

        wait_time = random.uniform(30, 60)
        logger.info(f"\n💤 Waiting {int(wait_time)}s...\n")
        time.sleep(wait_time)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        mark_scraper_stopped()
        logger.info("\n🛑 Stopped by user.")
    except Exception:
        mark_scraper_stopped()
        logger.exception("Bot terminated with an error")
        raise
