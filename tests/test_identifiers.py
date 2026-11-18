from libarrei.match import align
from libarrei.merge import merge
from libarrei.model import Edition, Identifier, Source, Work
from libarrei.sources.hardcover.mapping import to_edition
from libarrei.sources.openlibrary.mapping import identifiers, to_work

GR, HC, OL = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY
OL_DOC = {
    "key": "/books/OL1M",
    "identifiers": {"goodreads": ["394406"], "librarything": ["3206242"], "amazon": ["B0079KT81G"]},
    "oclc_numbers": ["237889032"],
    "lccn": ["67029221"],
}


def edition(source, sid, **fields):
    e = Edition()
    for name, value in fields.items():
        e.add(name, value, source, sid)
    return e


def test_openlibrary_identifiers():
    assert identifiers(OL_DOC) == [
        Identifier(scheme="goodreads", value="394406"), Identifier(scheme="librarything", value="3206242"),
        Identifier(scheme="amazon", value="B0079KT81G"), Identifier(scheme="oclc", value="237889032"),
        Identifier(scheme="lccn", value="67029221")]
    mapped = to_work({"key": "/works/OL1W"}, [OL_DOC], {}).editions[0]
    assert [c.value for c in mapped.asin] == ["B0079KT81G"]
    assert len(mapped.identifiers[0].value) == 5


def test_hardcover_asin():
    assert [c.value for c in to_edition({"id": 1, "asin": "B0079KT81G"}).asin] == ["B0079KT81G"]


def test_openlibrary_goodreads_id_matches_goodreads_edition():
    ol = to_work({"key": "/works/OL1W"}, [{"key": "/books/OL1M", "identifiers": {"goodreads": ["394406"]}}], {})
    gr = Work(editions=[edition(GR, "394406", title="The Hobbit"), edition(GR, "1", title="The Hobbit")])
    groups = align({OL: ol, GR: gr})
    linked = next(g for g in groups if len(g.members) == 2)
    assert linked.sources == {GR, OL} and linked.reason == "goodreads_id"
    assert len(groups) == 2


def test_isbn_outranks_goodreads_id_as_reason():
    ol = edition(OL, "OL1M", isbn13="9780547951966",
                 identifiers=[Identifier(scheme="goodreads", value="5")])
    gr = edition(GR, "5", isbn13="9780547951966")
    [group] = align({OL: Work(editions=[ol]), GR: Work(editions=[gr])})
    assert group.reason == "isbn13"


def test_duplicate_asins_within_a_source_are_flagged():
    hc = Work(editions=[edition(HC, "1", asin="B0079KT81G"), edition(HC, "2", asin="B0079KT81G")])
    [merged] = merge({HC: hc}).editions
    assert merged.duplicates == [HC]
    assert merged.match_reason == "asin"


def test_identifiers_never_conflict():
    ol = edition(OL, "OL1M", isbn13="9780547951966", identifiers=[Identifier(scheme="oclc", value="1")])
    other = edition(OL, "OL2M", isbn13="9780547951966", identifiers=[Identifier(scheme="lccn", value="2")])
    [merged] = merge({OL: Work(editions=[ol, other])}).editions
    assert merged.fields["identifiers"].conflict is False
