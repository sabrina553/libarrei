from pathlib import Path

from libarrei.cache import Cache
from libarrei.sources.goodreads import scraper
from libarrei.sources.goodreads.mapping import edition_from_editions_page

HTML = (Path(__file__).parent / "fixtures" / "goodreads_editions.html").read_text()


def values(candidates):
    return [c.value for c in candidates]


def test_parse_editions():
    editions = scraper.parse_editions(HTML)

    assert [e["goodreads_id"] for e in editions] == ["5907", "16053513", "227221"]
    first, kindle, spanish = editions
    assert first["title"] == "The Hobbit, or There and Back Again"
    assert first["cover_url"].endswith("/5907.jpg")
    assert (first["pages"], first["publisher"]) == (366, "Houghton Mifflin")
    assert (kindle["isbn13"], kindle["isbn10"]) == ("9780547951966", "0547951965")
    assert spanish["language"] == "Spanish"


def test_next_page_url():
    assert scraper.next_page_url(HTML).endswith("?page=2&per_page=100")
    assert scraper.next_page_url("<html></html>") is None


def test_edition_from_editions_page():
    edition = edition_from_editions_page(scraper.parse_editions(HTML)[1])

    assert values(edition.format) == ["ebook"]
    assert values(edition.cover_url)[0].endswith("/16053513.jpg")
    assert edition.ids["goodreads"] == "16053513"


class FakeLimiter:
    def __init__(self):
        self.waits = 0

    def wait(self):
        self.waits += 1


def test_fetch_editions_uses_cache_and_follows_pages(monkeypatch):
    # Page 1 links to page 2; page 2 has no "next" link, which ends the loop.
    last_page = HTML.replace('class="next_page"', 'class="other"')
    pages = {
        scraper.editions_url(1540236): HTML,
        "https://www.goodreads.com/work/editions/1540236-the-hobbit?page=2&per_page=100": last_page,
    }
    requested = []

    class Response:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        requested.append(url)
        return Response(pages[url])

    monkeypatch.setattr(scraper.requests, "get", fake_get)
    cache, limiter = Cache(":memory:"), FakeLimiter()

    assert len(scraper.fetch_editions(1540236, cache, limiter)) == 6
    assert len(scraper.fetch_editions(1540236, cache, limiter)) == 6
    # The second run is served from the cache, so no extra requests or waits.
    assert len(requested) == 2 and limiter.waits == 2
