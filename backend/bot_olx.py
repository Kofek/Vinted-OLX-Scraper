import logging
import random
import time
from datetime import datetime

import requests as req_olx
from bs4 import BeautifulSoup

from bot_ai import analyze_ai
from bot_history import save_link
import bot_state

logger = logging.getLogger("bot")

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
    if not date_text:
        return False
    date_text = date_text.lower()
    fresh_words = ["dzisiaj", "minut", "godz", "sekund", "teraz", "chwil"]
    return any(word in date_text for word in fresh_words)


def fetch_olx_details(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.0))
        resp = session.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_div = soup.find("div", {"data-cy": "ad_description"})
        return desc_div.text.strip() if desc_div else "No description"
    except Exception:
        return "No description (Error)"


def check_olx(history, bot):
    bot_name = bot.get("name", "Unknown")
    webhook_url = bot.get("webhook_url")
    history_file = bot.get("history_file")
    ai_prompt = bot.get("prompt_text", "")

    logger.info(f"🔵 [OLX - {bot_name}] Scanning...")
    session = req_olx.Session()
    session.headers.update({"User-Agent": random.choice(OLX_AGENTS)})

    for url in bot.get("urls_olx", []):
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", {"data-cy": "l-card"})

            for card in cards[:15]:
                try:
                    a_tag = card.find("a")
                    if not a_tag:
                        continue
                    href = a_tag["href"]
                    link = "https://www.olx.pl" + href if href.startswith("/") else href
                    link = link.split("#")[0]

                    if link in history:
                        continue

                    date_loc = "No data"
                    date_tag = card.find("p", {"data-testid": "location-date"})
                    if date_tag:
                        date_loc = date_tag.text.strip()

                    if not bot_state.is_first_run and not is_fresh_listing(date_loc):
                        continue

                    title = card.find("h6").text.strip() if card.find("h6") else (
                        card.find("h4").text.strip() if card.find("h4") else "No title"
                    )
                    price = (
                        card.find("p", {"data-testid": "ad-price"}).text.strip()
                        if card.find("p", {"data-testid": "ad-price"})
                        else "???"
                    )
                    img = card.find("img").get("src") if card.find("img") else ""

                    history.add(link)
                    save_link(link, history_file)
                    logger.info(f"OLX [NEW in {bot_name}]: {price} | {title[:30]}")

                    if not bot_state.is_first_run:
                        full_desc = fetch_olx_details(session, link)
                        ai_verdict = analyze_ai(title, price, full_desc, img, ai_prompt)
                        ai_verdict_upper = ai_verdict.upper()

                        if (
                            "NIE WARTO" in ai_verdict_upper
                            or "RYZYKO" in ai_verdict_upper
                            or "WARTO" not in ai_verdict_upper
                        ):
                            continue

                        payload = {
                            "embeds": [
                                {
                                    "title": f"💎 {title}",
                                    "url": link,
                                    "color": 5763719,
                                    "description": (
                                        f"**Cena:** `{price}`\n**Lokalizacja:** {date_loc}\n\n"
                                        f"🤖 **Gemini:**\n{ai_verdict}"
                                    ),
                                    "thumbnail": {"url": img},
                                    "footer": {
                                        "text": f"OLX Bot ({bot_name}) • {datetime.now().strftime('%H:%M')}"
                                    },
                                }
                            ]
                        }

                        if webhook_url:
                            logger.info(f"SENDING NOTIFICATION -> {bot_name}!")
                            req_olx.post(webhook_url, json=payload)
                            time.sleep(2)

                except Exception as e:
                    logger.warning(f"OLX Item Error [{bot_name}]: {e}")
                    continue
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            logger.warning(f"OLX URL Error: {e}")
    return history
