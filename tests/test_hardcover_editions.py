import json
from pathlib import Path

from libarrei.sources.hardcover.client import Hardcover
from libarrei.sources.hardcover.mapping import to_edition

PAGES = json.loads((Path(__file__).parent / "fixtures" / "hardcover_editions_pages.json").read_text())


class FakeTransport:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def execute(self, query, variables=None):
        self.calls.append(variables)
        return self.pages[variables["offset"] // variables["limit"]]


def test_all_editions_pages_until_short_page():
    transport = FakeTransport(PAGES)
    editions = Hardcover(transport).all_editions(42, page_size=2)
    assert [e["id"] for e in editions] == [101, 102, 103]
    assert transport.calls == [{"id": 42, "limit": 2, "offset": 0}, {"id": 42, "limit": 2, "offset": 2}]


def test_paged_editions_map_with_to_edition():
    languages = [to_edition(e).language[0].value for e in Hardcover(FakeTransport(PAGES)).all_editions(42, page_size=2)]
    assert languages == ["en", "de", "fr"]
