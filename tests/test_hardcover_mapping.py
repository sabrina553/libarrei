import json
from pathlib import Path

from libarrei.model import Source
from libarrei.sources.hardcover.mapping import to_work

RAW = json.loads((Path(__file__).parent / "fixtures" / "hardcover_book.json").read_text())


def values(candidates):
    return [c.value for c in candidates]


def test_work_fields():
    work = to_work(RAW)

    assert values(work.title) == ["Salt Lakes: An Unnatural History"]
    assert work.description == []
    assert values(work.genres) == [["Nature"]]
    assert work.series[0].value[0].position == "1.5"
    assert [(c.name, c.role) for c in work.contributors[0].value] == [
        ("Caroline Tracey", "author"),
        ("Test Translator", "translator"),
    ]
    assert work.ids == {Source.HARDCOVER: "2243188"}
    assert work.slugs == {Source.HARDCOVER: "salt-lakes-an-unnatural-history"}


def test_edition_fields():
    edition = to_work(RAW).editions[0]

    assert values(edition.isbn13) == ["9781324089025"]
    assert edition.isbn10 == []
    assert values(edition.format) == ["physical"]
    assert values(edition.publisher) == ["W. W. Norton"]
    assert values(edition.pages) == [272]
    assert edition.contributors[0].value[0].role == "author"
    assert edition.ids == {Source.HARDCOVER: "32475686"}
    # Edition pages live under their book's slug.
    assert edition.slugs == {Source.HARDCOVER: "salt-lakes-an-unnatural-history"}
