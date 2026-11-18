"""Reads Amazon's search and product pages, which have no public book API.

Parsing only: no network here, so the selectors can be tested on saved HTML.
Book details sit in a carousel of "rpi-attribute" cards on newer pages and in
a "Product details" bullet list on older ones, so both are read.
"""

import re

from bs4 import BeautifulSoup, Tag

# Amazon pads detail labels with direction marks and colons: "ISBN-13 \u200f : \u200e".
LABEL_JUNK = re.compile(r"[\u200e\u200f:\s]+")
# The carousel cards' ids, by the detail they hold.
CARDS = {
    "isbn10": "book_details-isbn10",
    "isbn13": "book_details-isbn13",
    "publisher": "book_details-publisher",
    "publication_date": "book_details-publication_date",
    "pages": "book_details-fiona_pages",
    "ebook_pages": "book_details-ebook_pages",
    "series": "book_details-series",
    "language": "language",
}
# The bullet list's labels, lowercased, by the same names.
BULLETS = {
    "isbn-10": "isbn10",
    "isbn-13": "isbn13",
    "publisher": "publisher",
    "publication date": "publication_date",
    "language": "language",
    "print length": "pages",
    "paperback": "pages",
    "hardcover": "pages",
}
# "Book 1 of 4: Mistborn" or "Part of: Mistborn (4 books)".
# Older pages read "Book 1 of 8: Name"; current ones put the name on its own line, giving "Book 1 of 8 Name".
SERIES_OF = re.compile(r"^Book\s+(\S+)\s+of\s+\d+\s*:?\s*(.+)$", re.IGNORECASE)
SERIES_PART = re.compile(r"^Part of\s*:\s*(.+?)(?:\s*\(\d+ books?\))?$", re.IGNORECASE)
# The publisher bullet can carry the date: "Gollancz (1 Sept. 2011)".
PUBLISHER_DATE = re.compile(r"^(.+?)\s*\(([^()]*\d{4})\)\s*$")
# A captcha page is served with 200, so its wording is the only sign.
CAPTCHA_MARKERS = ("/errors/validateCaptcha", "Type the characters you see", "api-services-support@amazon.com")


def text(el: Tag | None) -> str | None:
    if el is None:
        return None
    value = " ".join(el.get_text(" ", strip=True).split())
    return value or None


def is_captcha(html: str) -> bool:
    return any(marker in html for marker in CAPTCHA_MARKERS)


def parse_search(html: str) -> list[str]:
    """ASINs of the organic results, in page order; sponsored results are skipped."""
    soup = BeautifulSoup(html, "html.parser")
    asins = []
    for result in soup.select('div[data-component-type="s-search-result"][data-asin]'):
        asin = result["data-asin"].strip()
        sponsored = "AdHolder" in (result.get("class") or []) or result.select_one(".puis-sponsored-label-text")
        if asin and not sponsored and asin not in asins:
            asins.append(asin)
    return asins


def _authors(soup: BeautifulSoup) -> list[tuple[str, str]]:
    people = []
    for author in soup.select("#bylineInfo .author"):
        name = text(author.select_one("a"))
        role = text(author.select_one(".contribution")) or ""
        # "(Author)", or "(Author, Narrator)" for someone credited twice.
        for part in role.strip("() ,").split(",") or ["Author"]:
            if name:
                people.append((name, part.strip() or "Author"))
    return people


def _description(soup: BeautifulSoup) -> str | None:
    content = soup.select_one("[data-a-expander-name=book_description_expander] .a-expander-content")
    if content is None:
        noscript = soup.select_one("#bookDescription_feature_div noscript")
        # noscript content is not parsed as markup, so it is parsed on its own.
        content = BeautifulSoup(noscript.decode_contents(), "html.parser") if noscript else None
    if content is None:
        return None
    # Amazon styles emphasis with classes on spans, which the description parser would drop as unknown tags.
    for span in content.select("span.a-text-bold, span.a-text-italic"):
        classes = span.get("class") or []
        span.name = "b" if "a-text-bold" in classes else "i"
        if "a-text-bold" in classes and "a-text-italic" in classes:
            span.wrap(BeautifulSoup("", "html.parser").new_tag("i"))
        span.attrs = {}
    html = content.decode_contents().strip()
    return html or None


def _cards(soup: BeautifulSoup) -> dict[str, str]:
    found = {}
    for name, card in CARDS.items():
        # The series card carries "Book 1 of 8" as its label and only the name as its value.
        part = "" if name == "series" else " .rpi-attribute-value"
        if value := text(soup.select_one(f"#rpi-attribute-{card}{part}")):
            found[name] = value
    return found


def _bullets(soup: BeautifulSoup) -> dict[str, str]:
    found = {}
    for item in soup.select("#detailBullets_feature_div li"):
        label = item.select_one(".a-text-bold")
        if label is None:
            continue
        key = LABEL_JUNK.sub(" ", label.get_text()).strip().lower()
        label.extract()
        if (name := BULLETS.get(key)) and (value := text(item)):
            found.setdefault(name, value)
    if (publisher := found.get("publisher")) and (m := PUBLISHER_DATE.match(publisher)):
        found["publisher"] = m.group(1)
        found.setdefault("publication_date", m.group(2))
    return found


def _series(raw: str | None) -> tuple[str, str | None] | None:
    if not raw:
        return None
    if m := SERIES_OF.match(raw):
        return m.group(2).strip(), m.group(1)
    if m := SERIES_PART.match(raw):
        return m.group(1).strip(), None
    return raw, None


def _pages(raw: str | None) -> int | None:
    match = re.search(r"\d[\d,]*", raw or "")
    return int(match.group().replace(",", "")) if match else None


def _format(soup: BeautifulSoup) -> str | None:
    # "Paperback – 1 Sept. 2011": the format comes before the dash.
    subtitle = text(soup.select_one("#productSubtitle"))
    if subtitle:
        return re.split(r"\s+[–-]\s+", subtitle, maxsplit=1)[0]
    return text(soup.select_one("#tmmSwatches .selected .slot-title")) or text(
        soup.select_one("#tmmSwatches .selected a span"))


def _cover(soup: BeautifulSoup) -> str | None:
    for selector in ("#landingImage", "#ebooksImgBlkFront", "#imgBlkFront"):
        if (image := soup.select_one(selector)) is not None:
            # data-old-hires is the full-size image; src can be a low-resolution placeholder.
            if url := image.get("data-old-hires") or image.get("src"):
                return url
    return None


def parse_product(html: str) -> dict | None:
    """The book's details from a /dp/ page, or None when the page holds no product."""
    soup = BeautifulSoup(html, "html.parser")
    title = text(soup.select_one("#productTitle")) or text(soup.select_one("#ebooksProductTitle"))
    if not title:
        return None
    details = _bullets(soup) | _cards(soup)
    series = _series(details.get("series"))
    return {
        "title": title,
        "authors": _authors(soup),
        "description": _description(soup),
        "isbn10": details.get("isbn10"),
        "isbn13": details.get("isbn13"),
        "publisher": details.get("publisher"),
        "publication_date": details.get("publication_date"),
        "pages": _pages(details.get("pages") or details.get("ebook_pages")),
        "language": details.get("language"),
        "series": series,
        "format": _format(soup),
        "cover_url": _cover(soup),
    }
