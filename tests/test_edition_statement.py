from libarrei.merge import merge
from libarrei.model import Source, Work
from libarrei.sources.hardcover.mapping import to_edition
from libarrei.sources.openlibrary.mapping import to_work


def test_hardcover_edition_information():
    edition = to_edition({"id": 1, "edition_information": "Deluxe Edition"})
    assert [c.value for c in edition.edition_statement] == ["Deluxe Edition"]


def test_openlibrary_edition_name_is_merged():
    work = to_work({"key": "/works/OL1W"}, [{"key": "/books/OL1M", "edition_name": "2nd ed."}], {})
    merged = merge({Source.OPENLIBRARY: work})
    assert merged.editions[0].fields["edition_statement"].value == "2nd ed."


def test_edition_statement_is_edition_only():
    assert "edition_statement" not in Work.model_fields


def test_is_edition_statement():
    from libarrei.normalise import is_edition_statement

    for text in ["Deluxe Edition", "2nd ed.", "50th Anniversary Edition", "Collector\u2019s Edition", "Revised"]:
        assert is_edition_statement(text), text
    for text in ["The Last Edition", "A Novel", "", "Book"]:
        assert not is_edition_statement(text), text
