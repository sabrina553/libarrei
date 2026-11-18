from pathlib import Path

import pytest

from libarrei import normalise
from libarrei.cache import Cache
from libarrei.lookup import Clues, from_amazon, lookup
from libarrei.merge import merge
from libarrei.model import Source, Work
from libarrei.ratelimit import RateLimiter
from libarrei.sources.amazon.client import BLOCKED_NOTE, Amazon, AmazonBlocked
from libarrei.sources.amazon.mapping import to_edition, to_work
from libarrei.sources.amazon.scraper import is_captcha, parse_product, parse_search

FIXTURES = Path(__file__).parent / "fixtures" / "amazon"
SEARCH, PAPERBACK, KINDLE, CAPTCHA = ((FIXTURES / f"{n}.html").read_text() for n in ("search", "paperback", "kindle", "captcha"))
AZ = Source.AMAZON
SECRET = "session-id=123-SECRET; ubid-acbuk=456-SECRET"


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, pages):
        self.headers = {}
        self.pages = pages
        self.urls = []

    def get(self, url, timeout=None):
        self.urls.append(url)
        page = self.pages.get(url.rsplit("/", 1)[-1], (CAPTCHA, 200))
        return FakeResponse(*page)


PAGES = {"s?k=mistborn+sanderson": (SEARCH, 200), "0575089911": (PAPERBACK, 200), "B002GYI9C4": (KINDLE, 200)}


def client(session, cache=None, sleeps=None):
    return Amazon(SECRET, "co.uk", session, cache=cache, limiter=RateLimiter(0, sleep=lambda s: None),
                  jitter=lambda: 0.7, sleep=(sleeps.append if sleeps is not None else lambda s: None))


def mapped(html, asin):
    edition = to_edition(asin, parse_product(html), "co.uk")
    normalise.work(Work(editions=[edition]))
    return edition


def test_search_keeps_organic_results_once():
    assert parse_search(SEARCH) == ["0575089911", "B002GYI9C4"]


def test_paperback_from_the_details_carousel():
    edition = mapped(PAPERBACK, "0575089911")
    assert edition.title[0].value == "Mistborn"
    assert edition.subtitle[0].value == "The Final Empire"
    assert [(c.name, c.role) for c in edition.contributors[0].value] == [("Brandon Sanderson", "author")]
    assert edition.isbn13[0].value == "9780575089914"
    assert edition.isbn10[0].value == "0575089911"
    assert edition.asin[0].value == "0575089911"
    assert edition.publisher[0].value == "Gollancz"
    assert edition.release_date[0].value == "2011-09-01"
    assert edition.pages[0].value == 672
    assert edition.language[0].value == "en"
    assert (edition.series[0].value[0].name, edition.series[0].value[0].position) == ("Mistborn", "1")
    assert edition.format[0].value == "physical"
    assert edition.format_detail[0].value == "Paperback"
    assert edition.cover_url[0].value.endswith("full.jpg")
    assert edition.slugs[AZ] == "co.uk"


def test_kindle_from_the_detail_bullets_with_a_narrator():
    edition = mapped(KINDLE, "B002GYI9C4")
    assert edition.title[0].value == "The Final Empire"
    assert [(c.name, c.role) for c in edition.contributors[0].value] == [
        ("Brandon Sanderson", "author"), ("Michael Kramer", "narrator")]
    assert edition.publisher[0].value == "Gollancz"
    assert edition.release_date[0].value == "2009-07-17"
    assert edition.pages[0].value == 1000
    assert edition.format[0].value == "ebook"
    assert edition.format_detail[0].value == "Kindle Edition"
    assert edition.cover_url[0].value.endswith("kindle.jpg")


def test_description_is_parsed_as_html():
    work = to_work([("B002GYI9C4", parse_product(KINDLE))], "co.uk")
    description = merge({AZ: work}).fields["description"].value
    assert description == "For a thousand years the ash fell.\n\nPlaceholder paragraph."
    assert [c.name for c in work.contributors[0].value] == ["Brandon Sanderson"]


def test_page_without_a_product_is_none():
    assert parse_product(CAPTCHA) is None
    assert is_captcha(CAPTCHA) and not is_captcha(PAPERBACK)


def test_requests_look_like_a_browser_and_are_jittered():
    session, sleeps = FakeSession(PAGES), []
    amazon = client(session, sleeps=sleeps)
    amazon.product("0575089911")
    assert session.headers["Cookie"] == SECRET
    assert "Mozilla" in session.headers["User-Agent"]
    assert sleeps == [0.7]


@pytest.mark.parametrize("page", [(CAPTCHA, 200), ("", 503), ("", 500)])
def test_block_stops_amazon_for_the_rest_of_the_run(page):
    session = FakeSession({"X": page, "0575089911": (PAPERBACK, 200)})
    amazon = client(session)
    with pytest.raises(AmazonBlocked) as blocked:
        amazon.product("X")
    with pytest.raises(AmazonBlocked):
        amazon.product("0575089911")
    assert len(session.urls) == 1
    assert str(blocked.value) == BLOCKED_NOTE


def test_cookie_never_reaches_reprs_errors_or_cache_keys():
    cache = Cache(":memory:")
    amazon = client(FakeSession(PAGES), cache=cache)
    amazon.product("0575089911")
    assert "SECRET" not in repr(amazon)
    keys = [row[0] for row in cache.db.execute("SELECT request FROM responses")]
    assert keys == ["https://www.amazon.co.uk/dp/0575089911"]
    with pytest.raises(ValueError) as error:
        Amazon("a=b\r\nX-Evil: 1")
    assert "Evil" not in str(error.value)


def test_cached_pages_skip_the_network():
    session, cache = FakeSession(PAGES), Cache(":memory:")
    client(session, cache).product("0575089911")
    client(session, cache).product("0575089911")
    assert len(session.urls) == 1


def test_from_amazon_keeps_pages_read_before_a_block():
    pages = dict(PAGES)
    del pages["B002GYI9C4"]  # served the captcha instead
    notes = []
    work = from_amazon(client(FakeSession(pages)), None, Clues("mistborn", "sanderson"), True, notes.append)
    assert [e.ids[AZ] for e in work.editions] == ["0575089911"]
    assert notes == [BLOCKED_NOTE]


def test_from_amazon_matched_edition_reads_one_product_page():
    session = FakeSession(PAGES)
    work = from_amazon(client(session), None, Clues("mistborn", "sanderson"), False, lambda n: None)
    assert [e.ids[AZ] for e in work.editions] == ["0575089911"]
    assert len(session.urls) == 2


def test_amazon_is_off_without_a_cookie(monkeypatch):
    for name in ("AMAZON_COOKIE", "HARDCOVER_TOKEN", "GOODREADS_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("libarrei.lookup.from_openlibrary", lambda *a: None)
    monkeypatch.setattr("libarrei.lookup.from_audible", lambda *a: None)
    result = lookup(title="mistborn", use_cache=False)
    assert result.notes[AZ] == "AMAZON_COOKIE not set"
