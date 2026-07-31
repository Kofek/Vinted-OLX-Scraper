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

VINTED_MAX_LISTINGS_PER_PAGE = 15
VINTED_BASE_URL = "https://www.vinted.pl"
VINTED_TITLE_MAX_LENGTH = 60

VINTED_CATALOG_TIMEOUT_SECONDS = 10
VINTED_WARMUP_TIMEOUT_SECONDS = 10
VINTED_WARMUP_DELAY_SECONDS = (1.5, 2.5)
VINTED_DETAILS_TIMEOUT_SECONDS = 5
VINTED_DELAY_BEFORE_DETAILS_SECONDS = (1.0, 2.0)
VINTED_DELAY_BETWEEN_URLS_SECONDS = (5, 10)
DISCORD_DELAY_AFTER_POST_SECONDS = 3

VINTED_BROWSERS = [
    "chrome120",
    "chrome124",
    "chrome131",
    "chrome136",
    "safari17_0",
]

VINTED_WARMUP_URLS = [
    f"{VINTED_BASE_URL}/help/15-polityka-prywatnosci",
    f"{VINTED_BASE_URL}/help",
]

VINTED_403_PAUSE_SECONDS = (240, 360)
VINTED_PROFILE_RETRY_DELAY_SECONDS = (4, 8)
VINTED_MAX_PROFILE_RETRIES = 3

# Tracks consecutive "all profiles blocked by 403" events per bot.
VINTED_CONSECUTIVE_403_BLOCKS = {}
VINTED_403_SERIES_THRESHOLD = 2
VINTED_403_SERIES_PAUSE_SECONDS = 3600


# session and catalog HTTP (curl_cffi, browser impersonation)

def warmup_vinted_session(session, bot_name):
    """Visits static Vinted pages to collect cookies before catalog requests."""
    for warmup_url in VINTED_WARMUP_URLS:
        try:
            session.get(warmup_url, timeout=VINTED_WARMUP_TIMEOUT_SECONDS)
            time.sleep(random.uniform(*VINTED_WARMUP_DELAY_SECONDS))
        except Exception as exc:
            logger.warning(f"Vinted Warmup Error [{bot_name}] ({warmup_url}): {exc}")


def open_vinted_session(browser, bot_name):
    """Opens a curl_cffi session with the given browser profile and warms it up."""
    session = req_vinted.Session(impersonate=browser)
    warmup_vinted_session(session, bot_name)
    return session


def pause_after_vinted_block(last_browser, bot_name):
    """Pauses the bot after repeated 403 blocks from all browser profiles."""
    consecutive_blocks = VINTED_CONSECUTIVE_403_BLOCKS.get(bot_name, 0)

    if consecutive_blocks >= VINTED_403_SERIES_THRESHOLD:
        pause_seconds = VINTED_403_SERIES_PAUSE_SECONDS
        logger.warning(
            f"Vinted 403 ERROR ({last_browser})! Repeated 403 blocks for [{bot_name}] "
            f"(series {consecutive_blocks}), pausing {int(pause_seconds)}s."
        )
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
            resp = session.get(url, timeout=VINTED_CATALOG_TIMEOUT_SECONDS)
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


# parsing listings

def parse_vinted_listings(html):
    """Returns all Vinted listing blocks from a catalog page."""
    return BeautifulSoup(html, "html.parser").find_all("div", {"data-testid": "grid-item"})


# extracting data from listings

def extract_vinted_listing_link(item):
    """Returns full Vinted listing URL from one grid item, or None."""
    a_tag = item.find("a")
    if not a_tag:
        return None

    link = a_tag.get("href")
    if not link:
        return None

    if not link.startswith("http"):
        link = VINTED_BASE_URL + link

    return link


def extract_vinted_price(item):
    """Returns the listing price text, or a placeholder when it is missing."""
    for text in item.stripped_strings:
        if "zł" in text:
            return text
    return "???"


def extract_vinted_owner(item):
    """Returns the seller login from one grid item."""
    owner_div = item.find("div", {"data-testid": "box-user-login"})
    return owner_div.text.strip() if owner_div else "Hidden"


def extract_vinted_title(item):
    """Returns the listing title from one grid item."""
    img_tag = item.find("img")
    if img_tag and img_tag.get("alt"):
        return img_tag.get("alt")[:VINTED_TITLE_MAX_LENGTH]
    return "Vinted Item"


def extract_vinted_image(item):
    """Returns the thumbnail URL from one grid item, or an empty string."""
    img_tag = item.find("img")
    return img_tag.get("src") if img_tag else ""


# listing details

def fetch_vinted_details(session, url):
    """Returns the full description from a single Vinted listing page."""
    try:
        time.sleep(random.uniform(*VINTED_DELAY_BEFORE_DETAILS_SECONDS))
        resp = session.get(url, timeout=VINTED_DETAILS_TIMEOUT_SECONDS)

        if resp.status_code != 200:
            logger.warning(f"Vinted details HTTP {resp.status_code} on {url}")
            return "No description (Error)"

        soup = BeautifulSoup(resp.text, "html.parser")
        desc_div = soup.find("div", {"itemprop": "description"})
        return desc_div.text.strip() if desc_div else "No description"

    except Exception as exc:
        logger.warning(f"Vinted details request error on {url}: {exc}")
        return "No description (Error)"


# main function

def check_vinted(history, bot):
    """Scans all Vinted URLs of one bot and notifies Discord about new deals."""
    bot_name = bot.get("name", "Unknown")
    webhook_url = bot.get("webhook_url")
    history_file = bot.get("history_file")
    ai_prompt = bot.get("prompt_text", "")

    logger.info(f"🔴 [VINTED - {bot_name}] Scanning...")

    for url in bot.get("urls_vinted", []):
        session = None
        try:
            catalog_result = fetch_vinted_catalog(url, bot_name)
            if not catalog_result:
                return history

            session, browser, resp = catalog_result
            items = parse_vinted_listings(resp.text)

            for item in items[:VINTED_MAX_LISTINGS_PER_PAGE]:
                try:
                    link = extract_vinted_listing_link(item)
                    if not link or link in history:
                        continue

                    title = extract_vinted_title(item)
                    price = extract_vinted_price(item)
                    owner = extract_vinted_owner(item)
                    img = extract_vinted_image(item)

                    history.add(link)
                    save_link(link, history_file)
                    logger.info(f"VINTED [NEW in {bot_name}]: {price} | {title}")

                    if not bot_state.is_first_run:
                        full_desc = fetch_vinted_details(session, link)
                        ai_verdict = analyze_ai(title, price, full_desc, img, ai_prompt)

                        if not is_worth_buying(ai_verdict):
                            continue

                        if webhook_url:
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
                            logger.info(f"SENDING NOTIFICATION -> {bot_name}!")
                            req_http.post(webhook_url, json=payload)
                            time.sleep(DISCORD_DELAY_AFTER_POST_SECONDS)

                except Exception as exc:
                    logger.warning(f"Vinted Item Error [{bot_name}]: {exc}")
                    continue

            time.sleep(random.uniform(*VINTED_DELAY_BETWEEN_URLS_SECONDS))

        except Exception as exc:
            logger.warning(f"Vinted Error: {exc}")
        finally:
            if session is not None:
                session.close()

    return history
