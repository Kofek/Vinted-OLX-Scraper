import logging
import random
import time
import requests
from bs4 import BeautifulSoup

from bot_ai import analyze_ai
from bot_history import save_link
from bot_notify import build_notification_payload, is_worth_buying
import bot_state

logger = logging.getLogger("bot")

OLX_MAX_LISTINGS_PER_PAGE = 15
OLX_REQUEST_TIMEOUT_SECONDS = 10
OLX_DELAY_BETWEEN_URLS_SECONDS = (2, 4)
OLX_DETAILS_TIMEOUT_SECONDS = 5
OLX_DELAY_BEFORE_DETAILS_SECONDS = (0.5, 1.0)
DISCORD_DELAY_AFTER_POST_SECONDS = 2
FRESH_LISTING_KEYWORDS = ["dzisiaj", "minut", "godz", "sekund", "teraz", "chwil"]


OLX_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
]


def is_fresh_listing(date_text):
    """Returns True if listing is fresh, False otherwise."""
    if not date_text:
        return False
    date_text = date_text.lower()
    return any(word in date_text for word in FRESH_LISTING_KEYWORDS)


def fetch_olx_details(session, url):
    """Returns the full description from a single OLX listing page."""
    try:
        time.sleep(random.uniform(*OLX_DELAY_BEFORE_DETAILS_SECONDS))
        resp = session.get(url, timeout=OLX_DETAILS_TIMEOUT_SECONDS)

        if resp.status_code != 200:
            logger.warning(f"OLX details HTTP {resp.status_code} on {url}")
            return "No description (Error)"

        soup = BeautifulSoup(resp.text, "html.parser")
        desc_div = soup.find("div", {"data-cy": "ad_description"})
        return desc_div.text.strip() if desc_div else "No description"

    except Exception as exc:
        logger.warning(f"OLX details request error on {url}: {exc}")
        return "No description (Error)"


def parse_olx_listings(html):
    """Returns all OLX listing blocks from search results page."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("div", {"data-cy": "l-card"})


def extract_olx_listing_link(listing):
    """Returns full OLX listing URL from one search result block, or None."""
    a_tag = listing.find("a", href=True)
    if not a_tag:
        return None

    href = a_tag["href"].strip()

    if not href or "/d/oferta/" not in href:
        return None

    link = "https://www.olx.pl" + href if href.startswith("/") else href

    return link.split("#")[0]


def extract_olx_date_location(listing):
    """Returns the location and posting time text from one listing block."""
    date_tag = listing.find("p", {"data-testid": "location-date"})
    return date_tag.text.strip() if date_tag else "No data"


def should_skip_old_listing(date_loc):
    """Returns True for stale listings, but keeps everything during the first run."""
    if bot_state.is_first_run:
        return False
    return not is_fresh_listing(date_loc)


def extract_olx_title(listing):
    """Returns the listing title, or a placeholder when no heading is found."""
    title_tag = listing.find("h6") or listing.find("h4")
    return title_tag.text.strip() if title_tag else "No title"


def extract_olx_price(listing):
    """Returns the listing price text, or a placeholder when it is missing."""
    price_tag = listing.find("p", {"data-testid": "ad-price"})
    return price_tag.text.strip() if price_tag else "???"


def extract_olx_image(listing):
    """Returns the thumbnail URL from one listing block, or an empty string."""
    img_tag = listing.find("img")
    return img_tag.get("src") if img_tag else ""


def check_olx(history, bot):
    """Scans all OLX URLs of one bot and notifies Discord about new deals."""
    bot_name = bot.get("name", "Unknown")
    webhook_url = bot.get("webhook_url")
    history_file = bot.get("history_file")
    ai_prompt = bot.get("prompt_text", "")

    logger.info(f"🔵 [OLX - {bot_name}] Scanning...")
    olx_http_session = requests.Session()
    olx_http_session.headers.update({"User-Agent": random.choice(OLX_AGENTS)})

    for url in bot.get("urls_olx", []):
        try:
            resp = olx_http_session.get(url, timeout=OLX_REQUEST_TIMEOUT_SECONDS)
            if resp.status_code != 200:
                logger.warning(f"OLX HTTP {resp.status_code} [{bot_name}] on {url}")
                continue

            listings = parse_olx_listings(resp.text)

            for listing in listings[:OLX_MAX_LISTINGS_PER_PAGE]:
                try:
                    link = extract_olx_listing_link(listing)
                    if not link or link in history:
                        continue

                    date_loc = extract_olx_date_location(listing)

                    if should_skip_old_listing(date_loc):
                        continue

                    # first run extract currently ussless data, it will be used in the future updates
                    title = extract_olx_title(listing)
                    price = extract_olx_price(listing)
                    img = extract_olx_image(listing)

                    # history is a set object, we use this object to avoid re-reading the history file on every listing
                    history.add(link)
                    save_link(link, history_file)
                    logger.info(f"OLX [NEW in {bot_name}]: {price} | {title[:30]}")

                    if not bot_state.is_first_run:
                        full_desc = fetch_olx_details(olx_http_session, link)
                        ai_verdict = analyze_ai(title, price, full_desc, img, ai_prompt)

                        if not is_worth_buying(ai_verdict):
                            continue

                        if webhook_url:
                            payload = build_notification_payload(
                                title,
                                link,
                                price,
                                f"**Lokalizacja:** {date_loc}",
                                img,
                                ai_verdict,
                                bot_name,
                                "OLX",
                            )
                            logger.info(f"SENDING NOTIFICATION -> {bot_name}!")
                            requests.post(webhook_url, json=payload)
                            time.sleep(DISCORD_DELAY_AFTER_POST_SECONDS)

                except Exception as e:
                    logger.warning(f"OLX Item Error [{bot_name}]: {e}")
                    continue
            time.sleep(random.uniform(*OLX_DELAY_BETWEEN_URLS_SECONDS))
        except Exception as e:
            logger.warning(f"OLX URL Error: {e}")
    return history
