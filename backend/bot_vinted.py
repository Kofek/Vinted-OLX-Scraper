import logging
import random
import time
from datetime import datetime

import requests as req_http
from bs4 import BeautifulSoup
from curl_cffi import requests as req_vinted

from bot_ai import analyze_ai
from bot_history import save_link
from bot_state import is_first_run

logger = logging.getLogger("bot")


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
    browser = random.choice(["chrome124"])
    session = req_vinted.Session(impersonate=browser)

    try:
        session.get("https://www.vinted.pl/help/15-polityka-prywatnosci", timeout=10)
        time.sleep(random.uniform(2.5, 4.0))
    except Exception as e:
        logger.warning(f"Vinted Warmup Error [{bot_name}]: {e}")

    for url in bot.get("urls_vinted", []):
        try:
            resp = session.get(url, timeout=10)

            if resp.status_code == 403:
                logger.warning(f"Vinted 403 ERROR ({browser})! Session killed, pausing 2 mins.")
                session.close()
                time.sleep(120)
                return history

            if resp.status_code != 200:
                continue

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

                    if not is_first_run:
                        full_desc = fetch_vinted_details(session, link)
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
                                        f"**Cena:** `{price}`\n**Sprzedawca:** {owner}\n\n"
                                        f"🤖 **Gemini:**\n{ai_verdict}"
                                    ),
                                    "thumbnail": {"url": img},
                                    "footer": {
                                        "text": (
                                            f"Vinted Bot ({bot_name}) • "
                                            f"{datetime.now().strftime('%H:%M:%S')}"
                                        )
                                    },
                                }
                            ]
                        }

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
    return history
