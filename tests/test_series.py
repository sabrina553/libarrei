import json
from pathlib import Path

from libarrei.model import SeriesEntry
from libarrei.sources.hardcover import mapping as hardcover
from libarrei.sources.openlibrary import mapping as openlibrary

FIXTURES = Path(__file__).parent / "fixtures"
OL_WORK = json.loads((FIXTURES / "openlibrary_work.json").read_text())
OL_EDITION = json.loads((FIXTURES / "openlibrary_edition.json").read_text())


def test_hardcover_maps_every_series_featured_first():
    featured = {"series": {"name": "Cosmere"}, "position": 3}
    every = [{"series": {"name": "Mistborn"}, "position": 1}, featured, {"series": None, "position": 2}]
    assert hardcover.series(featured, every) == [
        SeriesEntry(name="Cosmere", position="3"), SeriesEntry(name="Mistborn", position="1")]


def test_hardcover_series_without_featured():
    assert hardcover.series(None, [{"series": {"name": "Discworld"}, "position": None}]) == [
        SeriesEntry(name="Discworld")]


def test_openlibrary_series_positions():
    doc = {"series": ["Mistborn ; 3", "Dungeon Crawler Carl #1", "El senor de los anillos, 2",
                      "The Sandman, #2", "Narrativa Rusconi", {"series": {"key": "/series/OL1L"}, "position": "1-3"}]}
    assert openlibrary.series(doc) == [
        SeriesEntry(name="Mistborn", position="3"), SeriesEntry(name="Dungeon Crawler Carl", position="1"),
        SeriesEntry(name="El senor de los anillos", position="2"), SeriesEntry(name="The Sandman", position="2"),
        SeriesEntry(name="Narrativa Rusconi")]


def test_openlibrary_series_on_work_and_edition():
    work = openlibrary.to_work({**OL_WORK, "series": ["Saga ; 1"]}, [{**OL_EDITION, "series": ["Line #4"]}], {})
    assert work.series[0].value == [SeriesEntry(name="Saga", position="1")]
    assert work.editions[0].series[0].value == [SeriesEntry(name="Line", position="4")]
