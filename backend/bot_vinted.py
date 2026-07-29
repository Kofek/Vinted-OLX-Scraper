import logging
import random
import time

import requests as req_http
from bs4 import BeautifulSoup
from curl_cffi import requests as req_vinted

from bot_ai import analyze_ai
from bot_history import save_link
from bot_notify import build_notification_payload, is_worth_buying
import bot_state

logger = logging.getLogger("bot")

VINTED_BROWSERS = [
    "chrome120",
    "chrome124",
    "chrome131",
    "chrome136",
    "safari17_0",
]

VINTED_WARMUP_URLS = [
    "https://www.vinted.pl/help/15-polityka-prywatnosci",
    "https://www.vinted.pl/help",
]

VINTED_403_PAUSE_SECONDS = (240, 360)
VINTED_PROFILE_RETRY_DELAY_SECONDS = (4, 8)
VINTED_MAX_PROFILE_RETRIES = 3

# Tracks consecutive "all profiles blocked by 403" events per bot.
VINTED_CONSECUTIVE_403_BLOCKS = {}
VINTED_403_SERIES_THRESHOLD = 2
VINTED_403_SERIES_PAUSE_SECONDS = 3600


def warmup_vinted_session(session, bot_name):
    """Visits static Vinted pages to collect cookies before catalog requests."""
    for warmup_url in VINTED_WARMUP_URLS:
        try:
            session.get(warmup_url, timeout=10)
            time.sleep(random.uniform(1.5, 2.5))
        except Exception as exc:
            logger.warning(f"Vinted Warmup Error [{bot_name}] ({warmup_url}): {exc}")


def open_vinted_session(browser, bot_name):
    session = req_vinted.Session(impersonate=browser)
    warmup_vinted_session(session, bot_name)
    return session


def pause_after_vinted_block(last_browser, bot_name):
    consecutive_blocks = VINTED_CONSECUTIVE_403_BLOCKS.get(bot_name, 0)

    if consecutive_blocks >= VINTED_403_SERIES_THRESHOLD:
        pause_seconds = VINTED_403_SERIES_PAUSE_SECONDS
        logger.warning(
            f"Vinted 403 ERROR ({last_browser})! Repeated 403 blocks for [{bot_name}] "
            f"(series {consecutive_blocks}), pausing {int(pause_seconds)}s."
        )
        # Reset after the long cooldown so the bot can try again.
        VINTED_CONSECUTIVE_403_BLOCKS[bot_name] = 0
    else:
        pause_seconds = random.uniform(*VINTED_403_PAUSE_SECONDS)
        logger.warning(
            f"Vinted 403 ERROR ({last_browser})! All profiles blocked for [{bot_name}], "
            f"pausing {int(pause_seconds)}s (series {consecutive_blocks}/{VINTED_403_SERIES_THRESHOLD})."
        )

    time.sleep(pause_seconds)


def fetch_vinted_catalog(url, bot_name):
    """
    Tries several browser profiles for one catalog URL.
    Returns (session, browser, response) on success, or None when all profiles get 403.
    """
    browsers = VINTED_BROWSERS[:]
    random.shuffle(browsers)
    last_browser = browsers[0]

    saw_403 = False

    for attempt, browser in enumerate(browsers[:VINTED_MAX_PROFILE_RETRIES], start=1):
        last_browser = browser
        session = open_vinted_session(browser, bot_name)

        try:
            resp = session.get(url, timeout=10)
        except Exception as exc:
            logger.warning(f"Vinted Request Error [{bot_name}] ({browser}): {exc}")
            session.close()
            continue

        if resp.status_code == 200:
            if attempt > 1:
                logger.info(f"Vinted OK with {browser} after {attempt} profile attempt(s).")
            VINTED_CONSECUTIVE_403_BLOCKS[bot_name] = 0
            return session, browser, resp

        if resp.status_code == 403:
            saw_403 = True
            logger.warning(
                f"Vinted 403 ({browser}) [{bot_name}] attempt {attempt}/{VINTED_MAX_PROFILE_RETRIES}, "
                "trying another profile..."
            )
            session.close()
            if attempt < VINTED_MAX_PROFILE_RETRIES:
                time.sleep(random.uniform(*VINTED_PROFILE_RETRY_DELAY_SECONDS))
            continue

        logger.warning(f"Vinted HTTP {resp.status_code} ({browser}) [{bot_name}] on catalog URL.")
        VINTED_CONSECUTIVE_403_BLOCKS[bot_name] = 0
        session.close()
        return None

    if saw_403:
        VINTED_CONSECUTIVE_403_BLOCKS[bot_name] = VINTED_CONSECUTIVE_403_BLOCKS.get(bot_name, 0) + 1
        pause_after_vinted_block(last_browser, bot_name)
    return None


def fetch_vinted_details(session, url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        resp = session.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_div = soup.find("div", {"itemprop": "description"})
        return desc_div.text.strip() if desc_div else "No description"
    except Exception:
        return "No description (Error)"


def check_vinted(history, bot):
    bot_name = bot.get("name", "Unknown")
    webhook_url = bot.get("webhook_url")
    history_file = bot.get("history_file")
    ai_prompt = bot.get("prompt_text", "")

    logger.info(f"🔴 [VINTED - {bot_name}] Scanning...")
    browser = random.choice(VINTED_BROWSERS)
    session = req_vinted.Session(impersonate=browser)

    try:
        session.get("https://www.vinted.pl/help/15-polityka-prywatnosci", timeout=10)
        time.sleep(random.uniform(2.5, 4.0))
    except Exception as e:
        logger.warning(f"Vinted Warmup Error [{bot_name}]: {e}")

    for url in bot.get("urls_vinted", []):
        session = None
        try:
            catalog_result = fetch_vinted_catalog(url, bot_name)
            if not catalog_result:
                return history

            session, browser, resp = catalog_result

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.find_all("div", {"data-testid": "grid-item"})

            for item in items[:15]:
                try:
                    a_tag = item.find("a")
                    if not a_tag:
                        continue
                    link = a_tag.get("href")
                    if not link.startswith("http"):
                        link = "https://www.vinted.pl" + link
                    if link in history:
                        continue

                    price = "???"
                    for s in item.stripped_strings:
                        if "zł" in s:
                            price = s
                            break

                    owner_div = item.find("div", {"data-testid": "box-user-login"})
                    owner = owner_div.text.strip() if owner_div else "Hidden"
                    img_tag = item.find("img")
                    img = img_tag.get("src") if img_tag else ""
                    title = img_tag.get("alt")[:60] if img_tag and img_tag.get("alt") else "Vinted Item"

                    history.add(link)
                    save_link(link, history_file)
                    logger.info(f"VINTED [NEW in {bot_name}]: {price} | {title}")

                    if not bot_state.is_first_run:
                        full_desc = fetch_vinted_details(session, link)
                        ai_verdict = analyze_ai(title, price, full_desc, img, ai_prompt)

                        if not is_worth_buying(ai_verdict):
                            continue

                        payload = build_notification_payload(
                            title,
                            link,
                            price,
                            f"**Sprzedawca:** {owner}",
                            img,
                            ai_verdict,
                            bot_name,
                            "Vinted",
                        )

                        if webhook_url:
                            logger.info(f"SENDING NOTIFICATION -> {bot_name}!")
                            req_http.post(webhook_url, json=payload)
                            time.sleep(3)
                except Exception as e:
                    logger.warning(f"Vinted Item Error [{bot_name}]: {e}")
                    continue
            time.sleep(random.uniform(5, 10))
        except Exception as e:
            logger.warning(f"Vinted Error: {e}")
        finally:
            if session is not None:
                session.close()
    return history
