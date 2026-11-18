import json
from pathlib import Path

from libarrei.model import Source
from libarrei.sources.formats import normalise_format
from libarrei.sources.goodreads.mapping import edition_from_scrape, work_from_graphql

RAW = json.loads((Path(__file__).parent / "fixtures" / "goodreads_book.json").read_text())


def values(candidates):
    return [c.value for c in candidates]


def test_work_from_graphql():
    work = work_from_graphql(RAW)

    assert work.ids == {Source.GOODREADS: "97397727"}
    assert values(work.genres) == [["Fiction", "Historical Fiction"]]
    assert values(work.original_release_date) == ["2023-03-14"]
    assert work.series[0].value[0].position == "2"
    assert work.contributors[0].value[0].ids == {Source.GOODREADS: "347770"}


def test_edition_from_graphql():
    edition = work_from_graphql(RAW).editions[0]

    assert edition.ids == {Source.GOODREADS: "61771675"}
    assert values(edition.format) == ["ebook"]
    assert values(edition.asin) == ["B0B7R4Q5DJ"]
    assert edition.isbn13 == []


def test_edition_from_scrape():
    edition = edition_from_scrape({
        "title": "How to Cheat Your Own Death", "authors": ["Kristen Perrin"],
        "isbn13": "9798217047505", "book_type": "Audible Audio", "pages": None,
        "goodreads_id": "239433112",
    })

    assert values(edition.format) == ["audiobook"]
    assert edition.pages == []
    assert edition.contributors[0].value[0].name == "Kristen Perrin"


def test_unknown_format_is_kept_lowercased():
    assert normalise_format("Leather Bound") == "leather bound"
