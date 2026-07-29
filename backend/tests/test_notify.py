from datetime import datetime

from bot_notify import DISCORD_EMBED_COLOR, build_notification_payload


def test_build_notification_payload_olx_embed_structure():
    payload = build_notification_payload(
        "Manga Naruto",
        "https://www.olx.pl/d/oferta/test-123",
        "25 zł",
        "**Lokalizacja:** Kraków - Dzisiaj o 12:00",
        "https://img.olx.pl/thumb.jpg",
        "WARTO kupić",
        "BotManga",
        "OLX",
    )
    embed = payload["embeds"][0]

    assert embed["title"] == "💎 Manga Naruto"
    assert embed["url"] == "https://www.olx.pl/d/oferta/test-123"
    assert embed["color"] == DISCORD_EMBED_COLOR
    assert embed["thumbnail"] == {"url": "https://img.olx.pl/thumb.jpg"}
    assert "**Cena:** `25 zł`" in embed["description"]
    assert "**Lokalizacja:** Kraków - Dzisiaj o 12:00" in embed["description"]
    assert "🤖 **Gemini:**" in embed["description"]
    assert "WARTO kupić" in embed["description"]
    assert "OLX Bot (BotManga)" in embed["footer"]["text"]


def test_build_notification_payload_vinted_extra_line_and_platform():
    payload = build_notification_payload(
        "Bluza Nike",
        "https://www.vinted.pl/items/999",
        "49 zł",
        "**Sprzedawca:** user123",
        "https://img.vinted.pl/item.jpg",
        "WARTO",
        "BotClothes",
        "Vinted",
    )
    embed = payload["embeds"][0]

    assert "**Sprzedawca:** user123" in embed["description"]
    assert "Vinted Bot (BotClothes)" in embed["footer"]["text"]


def test_build_notification_payload_has_single_embed():
    payload = build_notification_payload(
        "Test",
        "https://example.com",
        "10 zł",
        "**Lokalizacja:** Warszawa",
        "",
        "OK",
        "Bot",
        "OLX",
    )

    assert list(payload.keys()) == ["embeds"]
    assert len(payload["embeds"]) == 1


def test_build_notification_payload_footer_time(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 7, 29, 14, 30)

    # monkeypatch is a way to mock the datetime module, we use it to set the current time to a fixed value
    monkeypatch.setattr("bot_notify.datetime", FixedDatetime)

    payload = build_notification_payload(
        "Test",
        "https://example.com",
        "10 zł",
        "**Lokalizacja:** Gdańsk",
        "https://img.example.com/a.jpg",
        "WARTO",
        "BotTest",
        "OLX",
    )

    assert payload["embeds"][0]["footer"]["text"] == "OLX Bot (BotTest) • 14:30"
