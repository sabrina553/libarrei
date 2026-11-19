import json
from pathlib import Path

from libarrei.model import Source
from libarrei.sources.openlibrary.mapping import cover, pages, to_work

FIXTURES = Path(__file__).parent / "fixtures"
WORK = json.loads((FIXTURES / "openlibrary_work.json").read_text())
EDITION = json.loads((FIXTURES / "openlibrary_edition.json").read_text())
NAMES = {"/authors/OL1515577A": "Ann Napolitano"}


def values(candidates):
    return [c.value for c in candidates]


def test_work_fields():
    work = to_work(WORK, [EDITION], NAMES)

    assert work.ids == {Source.OPENLIBRARY: "OL28723763W"}
    assert values(work.description) == ["Test description."]
    assert work.contributors[0].value[0].ids == {Source.OPENLIBRARY: "OL1515577A"}


def test_edition_fields():
    edition = to_work(WORK, [EDITION], NAMES).editions[0]

    assert edition.ids == {Source.OPENLIBRARY: "OL39420471M"}
    assert values(edition.pages) == [416]
    assert values(edition.language) == ["eng"]
    assert values(edition.format) == ["physical"]
    assert values(edition.cover_url) == ["https://covers.openlibrary.org/b/id/13348203-L.jpg"]


def test_unknown_author_key_is_skipped():
    assert to_work(WORK, [], {}).contributors == []


def test_page_and_cover_fallbacks():
    assert pages({"number_of_pages": 300, "pagination": "xii, 416 p."}) == 300
    assert pages({"pagination": "xii, 416 p."}) == 416
    assert cover({"covers": [-1]}) is None
