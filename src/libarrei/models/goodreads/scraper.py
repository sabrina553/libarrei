import requests
import random
import re
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0",
]

def parse_title_and_series(raw_title):
    """
    Splits a Goodreads edition title into (title, subtitle, series_name, series_position).

    e.g. "How to Cheat Your Own Death (Castle Knoll Files, #3)"
      -> title="How to Cheat Your Own Death", subtitle=None,
         series_name="Castle Knoll Files", series_position="3"

    The trailing "(...)" on an edition title isn't always a series - Goodreads
    sometimes puts a format/edition note there instead (e.g. "(Hardcover)",
    "(Audible Audio)", "(LA)"). There's no reliable way to tell those apart
    from a real series name by text alone, so we only trust it as a series
    when it ends in "#<number>"; otherwise we discard it (both series_name
    and series_position come back None) and just strip it off the title.
    """
    raw_title = " ".join(raw_title.split())
    series_name = None
    series_position = None

    series_match = re.search(r"\(([^()]+)\)\s*$", raw_title)
    if series_match:
        series_text = series_match.group(1).strip()
        title = raw_title[: series_match.start()].strip()

        pos_match = re.search(r"#([\w.\-]+)\s*$", series_text)
        if pos_match:
            series_position = pos_match.group(1)
            series_name = series_text[: pos_match.start()].rstrip(", ").strip()
        # else: no "#N" order present -> discard, not a trustworthy series name
    else:
        title = raw_title

    subtitle = None
    if ":" in title:
        main, sub = title.split(":", 1)
        title, subtitle = main.strip(), sub.strip()

    return title, subtitle, series_name, series_position


def parse_publish_row(text):
    """Parses "Published April 28th 2026 by Dutton" -> (publish_date, publisher)."""
    text = " ".join(text.split())
    match = re.match(r"^Published\s+(.*?)(?:\s+by\s+(.*))?$", text)
    if not match:
        return None, None
    publish_date = match.group(1).strip() if match.group(1) else None
    publisher = match.group(2).strip() if match.group(2) else None
    return publish_date, publisher


def parse_format_row(text):
    """Parses "Hardcover, 336 pages" -> (book_type, pages). Either half may be missing."""
    text = " ".join(text.split())
    book_type, pages = None, None
    for part in (p.strip() for p in text.split(",")):
        page_match = re.match(r"^(\d+)\s+pages?$", part, re.IGNORECASE)
        if page_match:
            pages = int(page_match.group(1))
        elif part:
            book_type = part
    return book_type, pages


def parse_more_details(more_details_div):
    """
    Walks the hidden 'moreDetails' block (present in the static HTML even though
    it's toggled by JS) and returns (details_dict, authors_list).
    """
    details = {}
    authors = []

    if not more_details_div:
        return details, authors

    for row in more_details_div.find_all("div", class_="dataRow", recursive=False):
        title_el = row.find("div", class_="dataTitle")
        value_el = row.find("div", class_="dataValue")
        if not title_el or not value_el:
            continue

        key = title_el.get_text(strip=True).rstrip(":")

        if key.lower().startswith("author"):
            authors = [a.get_text(strip=True) for a in value_el.find_all("a", class_="authorName")]
            continue

        details[key] = " ".join(value_el.get_text(strip=True).split())

    return details, authors


def parse_isbn(raw):
    """
    Parses a Goodreads ISBN value into (isbn13, isbn10).

    Goodreads always labels this field "ISBN:", but the value is either a
    bare 13-digit ISBN13 ("9798217047505") or a 13-digit ISBN13 followed by
    a parenthetical 10-digit ISBN10 ("9781529445701(ISBN10: 1529445701)").
    Distinguishes the two by length rather than position, so it still works
    if Goodreads ever swaps the order.
    """
    if not raw:
        return None, None

    candidates = re.findall(r"[\dXx]{9,13}", raw)
    isbn13, isbn10 = None, None
    for val in candidates:
        if len(val) == 13:
            isbn13 = isbn13 or val
        elif len(val) == 10:
            isbn10 = isbn10 or val
    return isbn13, isbn10


def parse_rating(rating_text):
    """Parses "4.06 (7,378 ratings)" -> (average_rating, ratings_count)."""
    if not rating_text:
        return None, None
    match = re.match(r"^([\d.]+)\s*(?:\(([\d,]+)\s*ratings?\))?", rating_text)
    if not match:
        return None, None
    avg = float(match.group(1)) if match.group(1) else None
    count = int(match.group(2).replace(",", "")) if match.group(2) else None
    return avg, count


def _absolute_goodreads_url(href):
    """
    hrefs are relative ("/book/show/...") when scraping live, but a saved-off
    HTML page (e.g. "Save Page As" from a browser) can have them rewritten to
    absolute URLs already - only prefix the domain when it isn't there yet.
    """
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"https://www.goodreads.com{href}"

def parse_id(url):
    """Pulls the numeric Goodreads book ID out of a /book/show/<id>-slug URL."""
    if not url:
        return None
    match = re.search(r"/book/show/(\d+)", url)
    return match.group(1) if match else None

def scrape_edition(book_el):
    edition_data = book_el.find("div", class_="editionData")
    if not edition_data:
        return None

    data_rows = edition_data.find_all("div", class_="dataRow", recursive=False)

    title_link = edition_data.find("a", class_="bookTitle")
    raw_title = title_link.get_text(strip=True) if title_link else ""
    book_url = title_link["href"] if title_link and title_link.has_attr("href") else None
    title, subtitle, series_name, series_position = parse_title_and_series(raw_title)

    # The publish-date row and the format/pages row aren't reliably in a fixed
    # position (either can be blank/absent), so identify them by content
    # rather than by index.
    publish_date, publisher, book_type, pages = None, None, None, None
    for row in data_rows:
        if row.find("a", class_="bookTitle") or row.find("div", class_="moreDetails") or row.find(
            "a", class_="detailsLink"
        ):
            continue
        text = row.get_text(" ", strip=True)
        if not text:
            continue
        if text.lower().startswith("published"):
            publish_date, publisher = parse_publish_row(text)
        else:
            book_type, pages = parse_format_row(text)

    more_details = edition_data.find("div", class_="moreDetails")
    details, authors = parse_more_details(more_details)

    average_rating, ratings_count = parse_rating(details.get("Average rating"))

    # Goodreads labels this row "ISBN:" (occasionally "ISBN13:"), and the
    # value can hold both an ISBN13 and a parenthetical ISBN10 - merge across
    # whichever label(s) are present rather than assuming one key.
    isbn13, isbn10 = None, None
    for key, value in details.items():
        if key.upper().startswith("ISBN"):
            i13, i10 = parse_isbn(value)
            isbn13 = isbn13 or i13
            isbn10 = isbn10 or i10

    return {
        "title": title,
        "subtitle": subtitle,
        "series_name": series_name,
        "series_position": series_position,
        "publish_date": publish_date,
        "publisher": publisher,
        "book_type": book_type,
        "pages": pages,
        "authors": authors,
        "isbn13": isbn13,
        "isbn10": isbn10,
        "asin": details.get("ASIN"),
        "language": details.get("Edition language"),
        "average_rating": average_rating,
        "ratings_count": ratings_count,
        "url": _absolute_goodreads_url(book_url),
        "goodreads_id": parse_id(book_url)
    }


def scrape_editions(work_id, per_page=1):
    url = f"https://www.goodreads.com/work/editions/{work_id}?utf8=%E2%9C%93&per_page={per_page}"
    res = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)})
    res.raise_for_status()

    soup = BeautifulSoup(res.content, "html.parser")
    book_elements = soup.find_all("div", class_="elementList clearFix")

    return [scrape_edition(book_el) for book_el in book_elements]



# todo
# remove this main function
# verifty data is good
# find how many editions total
if __name__ == "__main__":
    editions = scrape_editions(250135212, per_page=100)
    for edition in editions:
        for key, value in edition.items():
            print(f"{key}: {value}")
        print("-" * 40)