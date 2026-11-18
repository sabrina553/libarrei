import json
from pathlib import Path

from libarrei.cache import Cache
from libarrei.ratelimit import RateLimiter
from libarrei.sources.openlibrary.client import OpenLibrary
from libarrei.sources.openlibrary.mapping import to_edition

PAGES = json.loads((Path(__file__).parent / "fixtures" / "openlibrary_editions_pages.json").read_text())


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class FakeSession:
    """Serves editions pages by offset and records each request made."""

    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return FakeResponse(PAGES[params["offset"] // params["limit"]])


def client(session, cache=None):
    return OpenLibrary(session, cache=cache, limiter=RateLimiter(0, sleep=lambda s: None))


def test_all_editions_pages_until_size():
    session = FakeSession()
    editions = client(session).all_editions("/works/OL27482W", page_size=2)

    assert [e["key"] for e in editions] == ["/books/OL1M", "/books/OL2M", "/books/OL3M"]
    assert session.calls == [{"limit": 2, "offset": 0}, {"limit": 2, "offset": 2}]
    assert [to_edition(e, {}).language[0].value for e in editions] == ["eng", "ger", "slv"]


def test_cached_pages_skip_the_network():
    session, cache = FakeSession(), Cache(":memory:")
    client(session, cache).all_editions("/works/OL27482W", page_size=2)
    client(session, cache).all_editions("/works/OL27482W", page_size=2)

    assert len(session.calls) == 2
