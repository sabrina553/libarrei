from libarrei.sources.formats import detail
from libarrei.sources.goodreads.mapping import edition_from_scrape
from libarrei.sources.hardcover.mapping import to_edition
from libarrei.sources.openlibrary.mapping import to_work


def values(candidates):
    return [c.value for c in candidates]


def test_hardcover_detail_and_duration():
    edition = to_edition({"id": 1, "reading_format_id": 2, "edition_format": "Audible Audio", "audio_seconds": 37800})
    assert values(edition.format) == ["audiobook"]
    assert values(edition.format_detail) == ["Audible Audio"]
    assert values(edition.duration_seconds) == [37800]


def test_hardcover_edition_format_fills_missing_reading_format():
    edition = to_edition({"id": 1, "reading_format_id": 3, "edition_format": "Mass Market Paperback"})
    assert values(edition.format) == ["physical"]
    assert values(edition.format_detail) == ["Mass Market Paperback"]
    assert to_edition({"id": 1, "audio_seconds": 0}).duration_seconds == []


def test_openlibrary_and_goodreads_keep_raw_format():
    work = to_work({"key": "/works/OL1W"}, [{"key": "/books/OL1M", "physical_format": "mass market paperback"}], {})
    assert values(work.editions[0].format_detail) == ["mass market paperback"]
    assert values(edition_from_scrape({"goodreads_id": "1", "book_type": "Kindle Edition"}).format_detail) == [
        "Kindle Edition"]


def test_detail_drops_unknown_binding():
    assert detail(" Unknown  Binding ") is None
    assert detail("Board  book") == "Board book"
