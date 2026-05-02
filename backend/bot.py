# ================= IMPORTY =================
import logging
import time
import os # wbudowana biblioteka os
import random
import urllib.parse
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from logging_config import configure_logging

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
configure_logging()
logger = logging.getLogger(__name__)

# Biblioteki sieciowe
import requests as req_olx
from curl_cffi import requests as req_vinted

from bot_ai import analyze_ai, init_ai
from bot_config import validate_config
from bot_history import load_history, save_link
from bot_status import utc_now_iso, write_bot_status

API_KEYS_POOL, MODELS_POOL, CATEGORIES = validate_config(BASE_DIR)
init_ai(API_KEYS_POOL, MODELS_POOL)

OLX_AGENTS = [
    # Windows - Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Windows - Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    # Windows - Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Mac - Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # Mac - Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Linux - Firefox
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

is_first_run = True

def is_fresh_listing(date_text):
    if not date_text: return False
    date_text = date_text.lower()
    fresh_words = ['dzisiaj', 'minut', 'godz', 'sekund', 'teraz', 'chwil']
    return any(word in date_text for word in fresh_words)

# ================= SCRAPING DETALI =================
def fetch_olx_details(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.0))
        resp = session.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        desc_div = soup.find('div', {'data-cy': 'ad_description'})
        return desc_div.text.strip() if desc_div else "No description"
    except Exception:
        return "No description (Error)"

def fetch_vinted_details(session, url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        resp = session.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        desc_div = soup.find('div', {'itemprop': 'description'})
        return desc_div.text.strip() if desc_div else "No description"
    except Exception:
        return "No description (Error)"


# ================= OLX LOGIC =================
def check_olx(history, category):
    cat_name = category.get("name", "Unknown")
    webhook_url = category.get("webhook")
    history_file = category.get("history_file")
    ai_prompt = category.get("system_instruction", "")

    logger.info(f"🔵 [OLX - {cat_name}] Scanning...")
    session = req_olx.Session()
    session.headers.update({"User-Agent": random.choice(OLX_AGENTS)})

    for url in category.get("urls_olx", []):
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code != 200: continue
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.find_all('div', {'data-cy': 'l-card'})

            for card in cards[:15]:
                try:
                    a_tag = card.find('a')
                    if not a_tag: continue
                    href = a_tag['href']
                    link = "https://www.olx.pl" + href if href.startswith('/') else href
                    link = link.split("#")[0]

                    if link in history: continue

                    date_loc = "No data"
                    date_tag = card.find('p', {'data-testid': 'location-date'})
                    if date_tag: date_loc = date_tag.text.strip()

                    if not is_first_run and not is_fresh_listing(date_loc):
                        continue

                    title = card.find('h6').text.strip() if card.find('h6') else (
                        card.find('h4').text.strip() if card.find('h4') else "No title")
                    price = card.find('p', {'data-testid': 'ad-price'}).text.strip() if card.find('p', {
                        'data-testid': 'ad-price'}) else "???"
                    img = card.find('img').get('src') if card.find('img') else ""

                    history.add(link)
                    save_link(link, history_file)
                    logger.info(f"OLX [NEW in {cat_name}]: {price} | {title[:30]}")

                    if not is_first_run:
                        full_desc = fetch_olx_details(session, link)
                        ai_verdict = analyze_ai(title, price, full_desc, img, ai_prompt)
                        ai_verdict_upper = ai_verdict.upper()

                        if "NIE WARTO" in ai_verdict_upper or "RYZYKO" in ai_verdict_upper or "WARTO" not in ai_verdict_upper:
                            continue

                        payload = {
                            "embeds": [{
                                "title": f"💎 {title}",
                                "url": link,
                                "color": 5763719,
                                "description": f"**Cena:** `{price}`\n**Lokalizacja:** {date_loc}\n\n🤖 **Gemini:**\n{ai_verdict}",
                                "thumbnail": {"url": img},
                                "footer": {"text": f"OLX Bot ({cat_name}) • {datetime.now().strftime('%H:%M')}"}
                            }]
                        }

                        if webhook_url:
                            logger.info(f"SENDING NOTIFICATION -> {cat_name}!")
                            req_olx.post(webhook_url, json=payload)
                            time.sleep(2)

                except Exception as e:
                    logger.warning(f"OLX Item Error [{cat_name}]: {e}")
                    continue
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            logger.warning(f"OLX URL Error: {e}")
    return history


# ================= VINTED LOGIC =================
def check_vinted(history, category):
    cat_name = category.get("name", "Unknown")
    webhook_url = category.get("webhook")
    history_file = category.get("history_file")
    ai_prompt = category.get("system_instruction", "")

    logger.info(f"🔴 [VINTED - {cat_name}] Scanning...")
    browser = random.choice(["chrome124"])
    session = req_vinted.Session(impersonate=browser)

    try:
        session.get("https://www.vinted.pl/help/15-polityka-prywatnosci", timeout=10)
        time.sleep(random.uniform(2.5, 4.0))
    except Exception as e:
        logger.warning(f"Vinted Warmup Error [{cat_name}]: {e}")

    for url in category.get("urls_vinted", []):
        try:
            resp = session.get(url, timeout=10)

            if resp.status_code == 403:
                logger.warning(f"Vinted 403 ERROR ({browser})! Session killed, pausing 2 mins.")
                session.close()
                time.sleep(120)
                return history

            if resp.status_code != 200: continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('div', {'data-testid': 'grid-item'})

            for item in items[:15]:
                try:
                    a_tag = item.find('a')
                    if not a_tag: continue
                    link = a_tag.get('href')
                    if not link.startswith("http"): link = "https://www.vinted.pl" + link
                    if link in history: continue

                    price = "???"
                    for s in item.stripped_strings:
                        if "zł" in s: price = s; break

                    owner_div = item.find('div', {'data-testid': 'box-user-login'})
                    owner = owner_div.text.strip() if owner_div else "Hidden"
                    img_tag = item.find('img')
                    img = img_tag.get('src') if img_tag else ""
                    title = img_tag.get('alt')[:60] if img_tag and img_tag.get('alt') else "Vinted Item"

                    history.add(link)
                    save_link(link, history_file)
                    logger.info(f"VINTED [NEW in {cat_name}]: {price} | {title}")

                    if not is_first_run:
                        full_desc = fetch_vinted_details(session, link)
                        ai_verdict = analyze_ai(title, price, full_desc, img, ai_prompt)
                        ai_verdict_upper = ai_verdict.upper()

                        if "NIE WARTO" in ai_verdict_upper or "RYZYKO" in ai_verdict_upper or "WARTO" not in ai_verdict_upper:
                            continue

                        payload = {
                            "embeds": [{
                                "title": f"💎 {title}",
                                "url": link,
                                "color": 5763719,
                                "description": f"**Cena:** `{price}`\n**Sprzedawca:** {owner}\n\n🤖 **Gemini:**\n{ai_verdict}",
                                "thumbnail": {"url": img},
                                "footer": {"text": f"Vinted Bot ({cat_name}) • {datetime.now().strftime('%H:%M:%S')}"}
                            }]
                        }

                        if webhook_url:
                            logger.info(f"SENDING NOTIFICATION -> {cat_name}!")
                            req_olx.post(webhook_url, json=payload)
                            time.sleep(3)
                except Exception as e:
                    logger.warning(f"Vinted Item Error [{cat_name}]: {e}")
                    continue
            time.sleep(random.uniform(5, 10))
        except Exception as e:
            logger.warning(f"Vinted Error: {e}")
    return history


# ================= MAIN LOOP =================
def main():
    global is_first_run
    logger.info("🚀 BOT STARTING...")
    write_bot_status(running=True, last_started_utc=utc_now_iso(), last_stopped_utc=None)

    while True:
        write_bot_status(running=True)
        for cat in CATEGORIES:
            cat_name = cat.get("name", "Unknown")
            history_file = cat.get("history_file")

            logger.info(f"\n📂 --- Processing Category: {cat_name} ---")
            history = load_history(history_file)

            if cat.get("urls_olx"):
                history = check_olx(history, cat)
                time.sleep(3)

            if cat.get("urls_vinted"):
                history = check_vinted(history, cat)
                time.sleep(3)

        if is_first_run:
            logger.info("\n✅ Initial databases loaded. Waiting for new items.")
            is_first_run = False

        wait_time = random.uniform(30, 60)
        logger.info(f"\n💤 Waiting {int(wait_time)}s...\n")
        time.sleep(wait_time)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        write_bot_status(running=False, last_stopped_utc=utc_now_iso())
        logger.info("\n🛑 Stopped by user.")
    except Exception:
        write_bot_status(running=False, last_stopped_utc=utc_now_iso())
        logger.exception("Bot terminated with an error")
        raise

