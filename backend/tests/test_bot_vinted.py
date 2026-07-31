from bs4 import BeautifulSoup

from bot_vinted import (
    extract_vinted_image,
    extract_vinted_listing_link,
    extract_vinted_owner,
    extract_vinted_price,
    extract_vinted_title,
    parse_vinted_listings,
)

SAMPLE_VINTED_ITEM = """
<div data-testid="grid-item">
  <a href="/items/1234567890-test-manga">Link</a>
  <div data-testid="box-user-login">seller123</div>
  <img alt="Manga Naruto tom 1 - bardzo długi tytuł który powinien zostać obcięty" src="https://img.vinted.pl/thumb.jpg" />
  <span>25 zł</span>
</div>
"""


def make_vinted_item(html=SAMPLE_VINTED_ITEM):
    return BeautifulSoup(html, "html.parser").find("div")


# --- parse_vinted_listings ---

def test_parse_vinted_listings_finds_two_items():
    html = '<div data-testid="grid-item">a</div><div data-testid="grid-item">b</div>'
    assert len(parse_vinted_listings(html)) == 2


def test_parse_vinted_listings_empty_page():
    assert parse_vinted_listings("<html></html>") == []


# --- extract_vinted_listing_link ---

def test_extract_vinted_listing_link_from_relative_href():
    item = make_vinted_item()
    assert extract_vinted_listing_link(item) == "https://www.vinted.pl/items/1234567890-test-manga"


def test_extract_vinted_listing_link_from_absolute_href():
    item = make_vinted_item(
        '<div data-testid="grid-item"><a href="https://www.vinted.pl/items/99">x</a></div>'
    )
    assert extract_vinted_listing_link(item) == "https://www.vinted.pl/items/99"


def test_extract_vinted_listing_link_missing_anchor():
    item = make_vinted_item('<div data-testid="grid-item"><span>no link</span></div>')
    assert extract_vinted_listing_link(item) is None


# --- extract_vinted_price ---

def test_extract_vinted_price_finds_zl_text():
    item = make_vinted_item()
    assert extract_vinted_price(item) == "25 zł"


def test_extract_vinted_price_missing_returns_placeholder():
    item = make_vinted_item('<div data-testid="grid-item"><span>no price</span></div>')
    assert extract_vinted_price(item) == "???"


# --- extract_vinted_owner ---

def test_extract_vinted_owner_reads_login():
    item = make_vinted_item()
    assert extract_vinted_owner(item) == "seller123"


def test_extract_vinted_owner_missing_returns_hidden():
    item = make_vinted_item('<div data-testid="grid-item"></div>')
    assert extract_vinted_owner(item) == "Hidden"


# --- extract_vinted_title ---

def test_extract_vinted_title_from_img_alt():
    item = make_vinted_item()
    alt = "Manga Naruto tom 1 - bardzo długi tytuł który powinien zostać obcięty"
    assert extract_vinted_title(item) == alt[:60]


def test_extract_vinted_title_missing_returns_default():
    item = make_vinted_item('<div data-testid="grid-item"></div>')
    assert extract_vinted_title(item) == "Vinted Item"


# --- extract_vinted_image ---

def test_extract_vinted_image_reads_src():
    item = make_vinted_item()
    assert extract_vinted_image(item) == "https://img.vinted.pl/thumb.jpg"


def test_extract_vinted_image_missing_returns_empty():
    item = make_vinted_item('<div data-testid="grid-item"></div>')
    assert extract_vinted_image(item) == ""
