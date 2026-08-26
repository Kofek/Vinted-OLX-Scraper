from datetime import datetime

DISCORD_EMBED_COLOR = 5763719


def is_worth_buying(ai_verdict):
    """Returns True when the AI verdict recommends the deal."""
    verdict = ai_verdict.upper()
    if "NIE WARTO" in verdict or "RYZYKO" in verdict:
        return False
    return "WARTO" in verdict


def build_notification_payload(title, link, price, extra_line, img, ai_verdict, bot_name, platform):
    """Builds a Discord embed for a matched listing (OLX or Vinted)."""
    return {
        "embeds": [
            {
                "title": f"💎 {title}",
                "url": link,
                "color": DISCORD_EMBED_COLOR,
                "description": (
                    f"**Cena:** `{price}`\n{extra_line}\n\n"
                    f"🤖 **Gemini:**\n{ai_verdict}"
                ),
                "thumbnail": {"url": img},
                "footer": {
                    "text": (
                        f"{platform} Bot ({bot_name}) • "
                        f"{datetime.now().strftime('%H:%M')}"
                    )
                },
            }
        ]
    }
