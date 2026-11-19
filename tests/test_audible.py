import json
from pathlib import Path

import pytest

from libarrei import normalise
from libarrei.cache import Cache
from libarrei.lookup import Clues, clues, from_audible, same_author
from libarrei.merge import merge
from libarrei.model import Candidate, Edition, Source, Work
from libarrei.ratelimit import RateLimiter
from libarrei.sources.audible.client import Audible, page_url
from libarrei.sources.audible.mapping import to_edition, to_work

FIXTURES = Path(__file__).parent / "fixtures"
SEARCH = json.loads((FIXTURES / "audible_search.json").read_text())
PRODUCT = json.loads((FIXTURES / "audible_product.json").read_text())
MISSING = json.loads((FIXTURES / "audible_missing.json").read_text())
AU = Source.AUDIBLE


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class FakeSession:
    """Answers searches with the recorded search and products by ASIN."""

    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if url.endswith("/products"):
            return FakeResponse(SEARCH)
        return FakeResponse(PRODUCT if url.endswith("/B004EW5KKU") else MISSING)


def client(session, cache=None):
    return Audible("co.uk", session, cache=cache, limiter=RateLimiter(0, sleep=lambda s: None))


def test_search_skips_podcasts_and_asks_for_relevance():
    session = FakeSession()
    products = client(session).search("The Hobbit", "Tolkien")

    assert [p["asin"] for p in products] == ["0008433844", "B004EW5KKU", "B004EWDDIQ"]
    url, params = session.calls[0]
    assert url == "https://api.audible.co.uk/1.0/catalog/products"
    assert params["keywords"] == "The Hobbit Tolkien"
    assert params["products_sort_by"] == "Relevance"
    assert params["image_sizes"] == "1000"


def test_product_missing_from_the_store_is_not_found():
    session = FakeSession()
    assert client(session).product("B0ZZZZZZZZ") is None
    assert client(session).product("B004EW5KKU")["title"] == "The Hobbit"


def test_cached_requests_skip_the_network():
    session, cache = FakeSession(), Cache(":memory:")
    client(session, cache).product("B004EW5KKU")
    client(session, cache).product("B004EW5KKU")
    assert len(session.calls) == 1


def test_unknown_region_is_refused():
    with pytest.raises(ValueError):
        Audible("moon")


def test_edition_mapping():
    edition = to_edition(PRODUCT["product"], "co.uk")
    work = Work(editions=[edition])
    normalise.work(work)

    assert edition.title[0].value == "The Hobbit"
    people = [(c.name, c.role) for c in edition.contributors[0].value]
    assert people == [("J. R. R. Tolkien", "author"), ("Rob Inglis", "narrator")]
    assert edition.asin[0].value == "B004EW5KKU"
    assert edition.format[0].value == "audiobook"
    assert edition.format_detail[0].value == "Audiobook"
    assert edition.edition_statement[0].value == "Unabridged"
    assert edition.duration_seconds[0].value == 662 * 60
    assert edition.release_date[0].value == "2008-12-28"
    assert edition.language[0].value == "en"
    assert edition.series[0].value[0].name == "The Lord of the Rings"
    assert edition.series[0].value[0].position == "0.5"
    assert edition.cover_url[0].value.endswith(".jpg")
    assert edition.slugs[AU] == "co.uk"


def test_isbn_shaped_audible_asin_is_kept():
    # Audible sells some titles under an ISBN-10 as their ASIN; it is still their product id.
    edition = to_edition(SEARCH["products"][0], "co.uk")
    work = Work(editions=[edition])
    normalise.work(work)
    assert edition.asin[0].value == "0008433844"


def test_abridged_detail():
    edition = to_edition(SEARCH["products"][2], "co.uk")
    assert edition.edition_statement[0].value == "Abridged"
    assert edition.format_detail[0].value == "Audiobook"


def test_work_description_parsed_as_html():
    work = to_work([PRODUCT["product"]], "co.uk")
    merged = merge({AU: work})
    description = merged.fields["description"].value
    assert "<p>" not in description and description.startswith("Bilbo Baggins")
    assert merged.fields["contributors"].value[0].name == "J. R. R. Tolkien"


def test_clues_take_title_author_and_audiobook_asins():
    audio = Edition(format=[Candidate(value="audiobook", source=Source.HARDCOVER, source_id="1")],
                    asin=[Candidate(value="B004EW5KKU", source=Source.HARDCOVER, source_id="1")])
    print_ = Edition(format=[Candidate(value="physical", source=Source.HARDCOVER, source_id="2")],
                     asin=[Candidate(value="B000PRINT1", source=Source.HARDCOVER, source_id="2")])
    work = Work(title=[Candidate(value="The Hobbit", source=Source.HARDCOVER, source_id="9")], editions=[audio, print_])
    found = clues({Source.HARDCOVER: work}, None, "Tolkien")
    assert (found.title, found.author) == ("The Hobbit", "Tolkien")
    assert found.asins[AU] == ["B004EW5KKU"]


def test_known_asin_wins_and_search_fills_in_all_editions(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr("libarrei.lookup.Audible", lambda region, cache: client(session))
    found = Clues("The Hobbit", "J.R.R. Tolkien", {AU: ["B004EW5KKU"], Source.AMAZON: []})

    matched = from_audible(None, "co.uk", found, all_editions=False)
    assert [e.ids[AU] for e in matched.editions] == ["B004EW5KKU"]

    full = from_audible(None, "co.uk", found, all_editions=True)
    assert [e.ids[AU] for e in full.editions] == ["B004EW5KKU", "0008433844", "B004EWDDIQ"]


def test_search_hits_by_other_authors_are_dropped():
    product = SEARCH["products"][1]
    assert same_author(product, "Tolkien")
    assert not same_author(product, "Ursula Le Guin")
    assert same_author(product, None)


def test_page_url():
    assert page_url("co.uk", "B004EW5KKU") == "https://www.audible.co.uk/pd/B004EW5KKU"


def test_search_hits_must_be_the_same_work_not_a_sequel():
    from libarrei.lookup import Clues, audible_is_work

    found = Clues(title="Dungeon Crawler Carl", author="Matt Dinniman", series_position="1")
    book = {"title": "Dungeon Crawler Carl", "series": [{"title": "Dungeon Crawler Carl", "sequence": "1"}]}
    sequel = {"title": "Carl's Doomsday Scenario", "series": [{"title": "Dungeon Crawler Carl", "sequence": "2"}]}
    translated = {"title": "Carl, o explorador de masmorras",
                  "series": [{"title": "Dungeon Crawler Carl (Portuguese Edition)", "sequence": "1"}]}
    novella = {"title": "Operation Bounce House", "series": []}
    assert audible_is_work(book, found)
    assert audible_is_work(translated, found)
    assert not audible_is_work(sequel, found)
    assert not audible_is_work(novella, found)


def test_spanish_series_note_is_not_a_subtitle():
    from libarrei.sources.audible.mapping import subtitle

    product = {"subtitle": "Dungeon Crawler Carl, Libro 1",
               "series": [{"title": "Dungeon Crawler Carl (edición en español)", "sequence": "1"}]}
    assert subtitle(product) is None
    assert subtitle({"subtitle": "Una aventura LitRPG", "series": []}) == "Una aventura LitRPG"
