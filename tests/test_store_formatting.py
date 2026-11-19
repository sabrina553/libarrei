import pytest

from libarrei import normalise
from libarrei.model import Contributor
from libarrei.sources.amazon.mapping import to_edition as amazon_edition
from libarrei.sources.audible.mapping import to_edition as audible_edition
from libarrei.sources.goodreads.titles import parse_title_and_series


@pytest.mark.parametrize("raw, expected", [
    ("Le Hobbit (French Edition)", "Le Hobbit"),
    ("El Hobbit [Spanish Edition]", "El Hobbit"),
    ("Der Hobbit (German Edition)", "Der Hobbit"),
    ("El Hobbit (Narración en Español Neutro)", "El Hobbit"),
    ("Lo Hobbit (Italian Edition)", "Lo Hobbit"),
    ("The Hobbit (Deluxe Edition)", "The Hobbit (Deluxe Edition)"),
    ("Poems (Edition of 500)", "Poems (Edition of 500)"),
    ("Dune (A Novel)", "Dune (A Novel)"),
])
def test_strip_language_label(raw, expected):
    assert normalise.strip_language_label(raw) == expected


@pytest.mark.parametrize("name, role, expected", [
    ("Chloé Atangana - traducteur", "author", ("Chloé Atangana", "translator")),
    ("Jane Doe - translator", "author", ("Jane Doe", "translator")),
    ("Hans Muster – Übersetzer", "author", ("Hans Muster", "translator")),
    ("Jean-Paul Sartre", "author", ("Jean-Paul Sartre", "author")),
    ("Smith - Jones", "author", ("Smith - Jones", "author")),
    ("Ann Lee - traductrice", "narrator", ("Ann Lee", "narrator")),
])
def test_role_suffix_split(name, role, expected):
    [person] = normalise.contributors([Contributor(name=name, role=role)])
    assert (person.name, person.role) == expected


def test_audible_mapping_cleans_titles_and_format():
    product = {"asin": "B0TEST0001", "title": "Le Hobbit (French Edition)", "format_type": "Abridged",
               "series": [{"title": "Le Seigneur des Anneaux (French Edition)", "sequence": "1"}]}
    edition = audible_edition(product, "fr")
    assert edition.title[0].value == "Le Hobbit"
    assert edition.series[0].value[0].name == "Le Seigneur des Anneaux"
    assert edition.format_detail[0].value == "Audiobook"
    assert edition.edition_statement[0].value == "Abridged"


def test_amazon_mapping_strips_language_label():
    product = {"title": "El Hobbit [Spanish Edition]", "series": ("Tierra Media (Spanish Edition)", "1")}
    edition = amazon_edition("B0TEST0002", product, "es")
    assert edition.title[0].value == "El Hobbit"
    assert edition.series[0].value[0].name == "Tierra Media"


def test_goodreads_format_suffix_and_series_note_stripped():
    parsed = parse_title_and_series("Dungeon Crawler Carl (Dungeon Crawler Carl, #1) - Paperback")
    assert parsed == ("Dungeon Crawler Carl", None, "Dungeon Crawler Carl", "1")


def test_goodreads_keeps_dashed_title():
    assert parse_title_and_series("Rain - A Memoir")[0] == "Rain - A Memoir"
