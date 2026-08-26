import logging
import time

from scraper.history import load_history
from scraper.olx import check_olx
from scraper.runtime import mark_bot_error, mark_bot_running
from scraper.vinted import check_vinted

logger = logging.getLogger(__name__)


def scan_bot(bot):
    """Runs OLX/Vinted checks for one bot and updates runtime status."""
    bot_id = bot.get("id")
    bot_name = bot.get("name", "Unknown")
    history_file = bot.get("history_file")

    mark_bot_running(bot_id)
    logger.info(f"📂 --- Processing bot: {bot_name} ---")

    try:
        history = load_history(history_file)

        if bot.get("urls_olx"):
            history = check_olx(history, bot)
            time.sleep(3)

        if bot.get("urls_vinted"):
            history = check_vinted(history, bot)
            time.sleep(3)
    except Exception as exc:
        logger.warning(f"Bot processing error [{bot_name}]: {exc}")
        mark_bot_error(bot_id, exc)
