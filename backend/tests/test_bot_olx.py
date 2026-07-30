from bs4 import BeautifulSoup

import bot_state
from bot_olx import (
    extract_olx_date_location,
    extract_olx_image,
    extract_olx_listing_link,
    extract_olx_price,
    extract_olx_title,
    is_fresh_listing,
    parse_olx_listings,
    should_skip_old_listing,
)

SAMPLE_OLX_CARD = """
<div data-cy="l-card">
  <a href="/d/oferta/test-manga-123#gallery">Link</a>
  <h6>Manga Naruto tom 1</h6>
  <p data-testid="ad-price">25 zł</p>
  <p data-testid="location-date">Kraków - Dzisiaj o 12:00</p>
  <img src="https://img.olx.pl/thumb.jpg" />
</div>
"""


def make_olx_listing(html=SAMPLE_OLX_CARD):
    return BeautifulSoup(html, "html.parser").find("div")


# --- is_fresh_listing ---
def test_is_fresh_listing_accepts_today():
    assert is_fresh_listing("Kraków - Dzisiaj o 12:00") is True


def test_is_fresh_listing_accepts_minutes_ago():
    assert is_fresh_listing("5 minut temu") is True


def test_is_fresh_listing_rejects_yesterday():
    assert is_fresh_listing("wczoraj") is False


def test_is_fresh_listing_rejects_empty():
    assert is_fresh_listing("") is False


# --- should_skip_old_listing ---
def test_first_run_does_not_skip_stale():
    bot_state.is_first_run = True
    assert should_skip_old_listing("wczoraj") is False


def test_stale_listing_is_skipped_after_first_run():
    bot_state.is_first_run = False
    assert should_skip_old_listing("wczoraj") is True


def test_fresh_listing_not_skipped_after_first_run():
    bot_state.is_first_run = False
    assert should_skip_old_listing("Dzisiaj") is False


# --- parse_olx_listings ---
def test_parse_olx_listings_finds_two_cards():
    html = '<div data-cy="l-card">a</div><div data-cy="l-card">b</div>'
    assert len(parse_olx_listings(html)) == 2


def test_parse_olx_listings_empty_page():
    assert parse_olx_listings("<html></html>") == []


# --- extract_olx_listing_link ---
def test_extract_olx_listing_link_from_relative_href():
    listing = make_olx_listing()
    assert extract_olx_listing_link(listing) == "https://www.olx.pl/d/oferta/test-manga-123"


def test_extract_olx_listing_link_strips_hash():
    html = """
    <div data-cy="l-card">
      <a href="/d/oferta/test-123#gallery">Link</a>
    </div>
    """
    listing = make_olx_listing(html)
    assert extract_olx_listing_link(listing) == "https://www.olx.pl/d/oferta/test-123"


def test_extract_olx_listing_link_invalid_href():
    html = """
    <div data-cy="l-card">
      <a href="/profil/user">Link</a>
    </div>
    """
    listing = make_olx_listing(html)
    assert extract_olx_listing_link(listing) is None


def test_extract_olx_listing_link_no_anchor():
    html = '<div data-cy="l-card"><h6>No link</h6></div>'
    listing = make_olx_listing(html)
    assert extract_olx_listing_link(listing) is None


# --- extract_olx_title ---
def test_extract_olx_title():
    listing = make_olx_listing()
    assert extract_olx_title(listing) == "Manga Naruto tom 1"


def test_extract_olx_title_missing():
    html = '<div data-cy="l-card"><a href="/d/oferta/x">x</a></div>'
    listing = make_olx_listing(html)
    assert extract_olx_title(listing) == "No title"


# --- extract_olx_price ---
def test_extract_olx_price():
    listing = make_olx_listing()
    assert extract_olx_price(listing) == "25 zł"


def test_extract_olx_price_missing():
    html = '<div data-cy="l-card"><a href="/d/oferta/x">x</a></div>'
    listing = make_olx_listing(html)
    assert extract_olx_price(listing) == "???"


# --- extract_olx_date_location ---
def test_extract_olx_date_location():
    listing = make_olx_listing()
    assert extract_olx_date_location(listing) == "Kraków - Dzisiaj o 12:00"


def test_extract_olx_date_location_missing():
    html = '<div data-cy="l-card"><a href="/d/oferta/x">x</a></div>'
    listing = make_olx_listing(html)
    assert extract_olx_date_location(listing) == "No data"


# --- extract_olx_image ---
def test_extract_olx_image():
    listing = make_olx_listing()
    assert extract_olx_image(listing) == "https://img.olx.pl/thumb.jpg"


def test_extract_olx_image_missing():
    html = '<div data-cy="l-card"><a href="/d/oferta/x">x</a></div>'
    listing = make_olx_listing(html)
    assert extract_olx_image(listing) == ""

