import re
from pathlib import Path

from libarrei.capabilities import EDITION, WORK
from libarrei.merge import merge
from libarrei.model import Contributor, Edition, Source, Work
from libarrei.quality import SPARSE, score

HC, GR, AU = Source.HARDCOVER, Source.GOODREADS, Source.AUDIBLE
TS = Path(__file__).resolve().parents[1] / "web" / "src" / "components" / "capabilities.ts"


def edition(source: Source, sid: str, **fields) -> Edition:
    e = Edition()
    for name, value in fields.items():
        e.add(name, value, source, sid)
    return e


FULL = dict(title="Dungeon Crawler Carl", contributors=[Contributor(name="Matt Dinniman")], isbn13="9780593820247",
            isbn10="0593820242", asin="0593820242", publisher="Ace", release_date="2024-08-20", pages=464,
            format="physical", language="en", cover_url="https://example.org/c.jpg")
# Like Hardcover editions 32478399 and 32911147: no identifiers, little else.
STUB = dict(title="Dungeon Crawler Carl", publisher="Ace", release_date="2024", format="physical", language="en")


def test_full_record_scores_100_and_stub_is_sparse():
    assert score(HC, set(FULL), audiobook=False) == 100
    assert score(HC, set(STUB), audiobook=False) < SPARSE


def test_sources_are_not_punished_for_fields_they_never_have():
    # Audible has no ISBNs or page counts; a complete Audible record still scores 100.
    fields = {"title", "contributors", "asin", "publisher", "release_date", "duration_seconds", "format",
              "language", "cover_url"}
    assert score(AU, fields, audiobook=True) == 100


def test_audiobooks_count_duration_not_pages():
    with_pages = set(FULL) - {"isbn13", "isbn10"}
    assert score(HC, with_pages, audiobook=True) < score(HC, with_pages | {"duration_seconds"}, audiobook=True)


def test_quality_exposed_per_edition_and_work_with_stub_hint():
    works = {HC: Work(editions=[edition(HC, "1", **FULL), edition(HC, "32478399", **STUB)]),
             GR: Work(editions=[edition(GR, "9", **FULL)])}
    merged = merge(works)
    full = next(e for e in merged.editions if HC in e.ids and "1" in e.ids[HC])
    stub = next(e for e in merged.editions if "32478399" in e.ids.get(HC, []))
    assert full.quality == {HC: 100, GR: 100}
    assert stub.quality[HC] < SPARSE
    assert stub.stub_of == full.ids
    assert full.stub_of is None
    assert merged.quality[GR] == 100 and merged.quality[HC] < 100


def test_stub_needs_matching_publisher_or_year():
    other = {**STUB, "publisher": "Other", "release_date": "1999"}
    merged = merge({HC: Work(editions=[edition(HC, "1", **FULL), edition(HC, "2", **other)])})
    assert all(e.stub_of is None for e in merged.editions)


def test_sparse_record_with_identifier_is_not_a_stub():
    # Like Goodreads 255420518: a junk title, an author and an ASIN on a "Paperback".
    junk = dict(title="Dungeon Crawler Carl", contributors=[Contributor(name="Matt Dinniman")], asin="B0H8V4BRJD",
                format="physical")
    merged = merge({HC: Work(editions=[edition(HC, "1", **FULL)]), GR: Work(editions=[edition(GR, "255420518", **junk)])})
    gr = next(e for e in merged.editions if GR in e.ids)
    assert gr.quality[GR] < SPARSE and gr.stub_of is None


def test_well_filled_copies_without_identifiers_point_at_their_original():
    # Like Hardcover 33335690 and 33335689: everything but an identifier, beside the real Dandy House ebook.
    dandy = {**FULL, "publisher": "Dandy House", "release_date": "2020-10-02", "format": "ebook",
             "isbn13": "9781405989411", "isbn10": "1405989416", "asin": "B08BKGYQXW"}
    copy = {k: v for k, v in dandy.items() if k not in ("isbn13", "isbn10", "asin")} | {"pages": 447}
    copies = [edition(HC, sid, **copy) for sid in ("33335690", "33335689", "33250543")]
    merged = merge({HC: Work(editions=[edition(HC, "30407789", **dandy), *copies])})
    original = next(e for e in merged.editions if "30407789" in e.ids[HC])
    assert [e.stub_of for e in merged.editions if e is not original] == [original.ids] * 3


def _ts_sets(level: str) -> dict[str, set[str]]:
    block = re.search(rf"\b{level}: \{{(.*?)\n  \}}", TS.read_text(), re.S).group(1)
    return {m.group(1): set(re.findall(r"'([a-z_0-9]+)'", m.group(2)))
            for m in re.finditer(r"(\w+): new Set\(\[(.*?)\]\)", block, re.S)}


def test_gui_capabilities_match_backend():
    assert _ts_sets("edition") == {s.value: set(f) for s, f in EDITION.items()}
    assert _ts_sets("work") == {s.value: set(f) for s, f in WORK.items()}


def test_a_full_record_without_identifiers_stays_sparse():
    rich = {"title", "contributors", "publisher", "release_date", "pages", "format", "language", "cover_url"}
    assert score(HC, rich, audiobook=False) == SPARSE - 1
    assert score(HC, rich | {"asin"}, audiobook=False) > SPARSE


CARL_AUDIO = dict(title="Dungeon Crawler Carl", format="audiobook", language="en", publisher="Audible Studios",
                  contributors=[Contributor(name="Matt Dinniman"), Contributor(name="Jeff Hays", role="narrator")])


def test_other_store_listings_of_one_recording_point_at_the_best():
    # Like Hardcover 32126720, 31923605, 32757508 and 32895787: one Audible Studios recording, one ASIN per store.
    best = {**CARL_AUDIO, "asin": "B08V8B2CGV", "isbn13": "9783748087328", "release_date": "2021-01-28",
            "duration_seconds": 48660, "cover_url": "https://example.org/c.jpg"}
    listings = [{**CARL_AUDIO, "asin": asin, "release_date": day, "duration_seconds": seconds}
                for asin, day, seconds in (("B08V8877BY", "2021-01-28", 48660), ("B08V7VS8H2", "2021-01-26", 48700),
                                           ("B08V893CH7", "2021-01-01", 48720))]
    other = {**CARL_AUDIO, "asin": "B0OTHER001", "release_date": "2021-01-28", "duration_seconds": 30000}
    records = [edition(HC, "1", **best), *(edition(HC, str(i), **l) for i, l in enumerate(listings, 2)), edition(HC, "9", **other)]
    merged = merge({HC: Work(editions=records)})
    head = next(e for e in merged.editions if "1" in e.ids[HC])
    assert sorted(e.ids[HC][0] for e in merged.editions if e.listing_of == head.ids) == ["2", "3", "4"]
    assert head.listing_of is None
    assert next(e for e in merged.editions if "9" in e.ids[HC]).listing_of is None
