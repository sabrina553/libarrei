from libarrei.match import align
from libarrei.model import Edition, Source, Work

GR, HC, OL = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY


def edition(source, sid, **fields):
    e = Edition()
    for name, value in fields.items():
        e.add(name, value, source, sid)
    return e


def works(**by_source):
    return {Source(s): Work(editions=e) for s, e in by_source.items()}


def test_isbn_chains_join_into_one_group():
    groups = align(works(
        goodreads=[edition(GR, "1", isbn13="9780547951966")],
        hardcover=[edition(HC, "2", isbn13="9780547951966", asin="B0079KT81G")],
        openlibrary=[edition(OL, "3", asin="B0079KT81G")],
    ))
    assert len(groups) == 1
    assert groups[0].sources == {GR, HC, OL} and groups[0].reason == "isbn13"


AUDIO = dict(format="audiobook", language="en", release_date="2012-09-18", pages=11, publisher="HarperAudio")


def test_identifierless_editions_pair_when_everything_agrees():
    groups = align(works(
        goodreads=[edition(GR, "1", title="The Hobbit", **AUDIO)],
        hardcover=[edition(HC, "2", title="The Hobbit", **AUDIO)],
    ))
    assert len(groups) == 1 and groups[0].reason == "fuzzy"


def test_ambiguous_fuzzy_match_stays_apart():
    groups = align(works(
        goodreads=[edition(GR, "1", **AUDIO)],
        hardcover=[edition(HC, "2", **AUDIO), edition(HC, "3", **AUDIO)],
    ))
    assert all(len(g.members) == 1 for g in groups)


def test_disagreeing_signal_blocks_a_fuzzy_match():
    groups = align(works(
        goodreads=[edition(GR, "1", **AUDIO)],
        hardcover=[edition(HC, "2", **AUDIO | {"pages": 300})],
    ))
    assert len(groups) == 2


def test_same_source_twice_is_flagged_as_duplicate():
    groups = align(works(hardcover=[
        edition(HC, "2", isbn13="9780547951966"),
        edition(HC, "5", isbn13="9780547951966"),
    ]))
    assert groups[0].duplicates == [HC]
    assert groups[0].duplicate_reasons == {HC: ["isbn13"]}


def test_duplicate_reasons_name_every_shared_identifier():
    groups = align(works(openlibrary=[
        edition(OL, "OL1M", isbn13="9780547951966", isbn10="0547951965", asin="B007978NPG"),
        edition(OL, "OL2M", isbn13="9780547951966", isbn10="0547951965", asin="B007978NPG"),
    ]))
    assert groups[0].duplicate_reasons == {OL: ["isbn13", "isbn10", "asin"]}


def test_duplicates_joined_only_through_another_source_share_nothing():
    [group] = align(works(openlibrary=[
        edition(OL, "OL1M", isbn13="9780547951966"),
        edition(OL, "OL2M", asin="B007978NPG"),
    ], hardcover=[edition(HC, "9", isbn13="9780547951966", asin="B007978NPG")]))
    assert group.duplicate_reasons == {OL: []}


AU, AZ = Source.AUDIBLE, Source.AMAZON


def test_a_store_confirmed_asin_is_strong_evidence():
    [group] = align(works(
        goodreads=[edition(GR, "1", asin="B004EW5KKU", format="audiobook")],
        audible=[edition(AU, "B004EW5KKU", asin="B004EW5KKU", format="audiobook")],
    ))
    assert group.reason == "store_asin" and group.confidence == 1.0


def test_a_catalogue_only_asin_is_weaker():
    [group] = align(works(
        goodreads=[edition(GR, "1", asin="B002GYI9C4", format="ebook")],
        hardcover=[edition(HC, "2", asin="B002GYI9C4", format="ebook")],
    ))
    assert group.reason == "asin" and group.confidence < 1.0


def test_a_catalogue_only_asin_cannot_join_clashing_formats():
    # Goodreads often shows the Kindle ASIN on a paperback edition.
    groups = align(works(
        goodreads=[edition(GR, "1", asin="B002GYI9C4", format="physical")],
        hardcover=[edition(HC, "2", asin="B002GYI9C4", format="ebook")],
    ))
    assert len(groups) == 2


def test_a_store_confirmed_asin_still_refuses_a_misattributed_print_edition():
    groups = align(works(
        goodreads=[edition(GR, "1", asin="B002GYI9C4", format="physical")],
        amazon=[edition(AZ, "B002GYI9C4", asin="B002GYI9C4", format="ebook")],
    ))
    assert len(groups) == 2


def test_duplicates_sharing_a_store_confirmed_asin_say_so():
    [group] = align(works(
        goodreads=[edition(GR, "1", asin="B002GYI9C4"), edition(GR, "2", asin="B002GYI9C4")],
        amazon=[edition(AZ, "B002GYI9C4", asin="B002GYI9C4")],
    ))
    assert group.duplicate_reasons == {GR: ["store_asin"]}


CASTILIAN = {"format": "audiobook", "language": "es"}
CASTILIAN_VOICES = [("Íñigo Álvarez de Lara", "narrator"), ("Ana Fernández", "narrator")]
NEUTRAL_VOICES = [("Paris Roa", "narrator"), ("Cristina Tenorio", "narrator")]


def people(*named):
    from libarrei.model import Contributor
    return [Contributor(name="Matt Dinniman", role="author")] + [Contributor(name=n, role=r) for n, r in named]


def test_spanish_audiobooks_group_by_narrators_despite_different_titles():
    groups = align(works(
        goodreads=[
            edition(GR, "238401580", title="Carl el mazmorrero", release_date="2025-07-10", asin="B0FG35DPWV",
                    contributors=people(*CASTILIAN_VOICES), **CASTILIAN),
            edition(GR, "239829094", title="Carl el mazmorrero", release_date="2025-08-19", asin="B0FLFCNBRP",
                    contributors=people(*NEUTRAL_VOICES), **CASTILIAN),
        ],
        hardcover=[edition(HC, "33108868", title="Dungeon Crawler Carl", release_date="2025-07-10",
                           contributors=people(("Inigo Alvarez de Lara", "narrator"), ("Ana Fernandez", "narrator")),
                           **CASTILIAN)],
        audible=[
            edition(Source.AUDIBLE, "B0FG35CZN3", title="Dungeon Crawler Carl", release_date="2025-07-11",
                    asin="B0FG35CZN3", contributors=people(*CASTILIAN_VOICES), **CASTILIAN),
            edition(Source.AUDIBLE, "B0FLFCTJ2V", title="Dungeon Crawler Carl", release_date="2025-08-19",
                    asin="B0FLFCTJ2V", contributors=people(*NEUTRAL_VOICES), **CASTILIAN),
        ],
    ))
    assert sorted(sorted(m[1].ids.get(m[0]) or "" for m in g.members) for g in groups) == [
        ["238401580", "33108868", "B0FG35CZN3"], ["239829094", "B0FLFCTJ2V"]]


def test_same_narrators_on_another_book_stay_apart():
    groups = align(works(
        goodreads=[edition(GR, "1", title="Book One", release_date="2025-07-10",
                           contributors=people(*CASTILIAN_VOICES), **CASTILIAN)],
        hardcover=[edition(HC, "2", title="Book Two", release_date="2025-11-02",
                           contributors=people(*CASTILIAN_VOICES), **CASTILIAN)],
    ))
    assert len(groups) == 2


def test_different_narrators_are_different_recordings():
    groups = align(works(
        goodreads=[edition(GR, "1", title="Dungeon Crawler Carl", release_date="2025-07-10",
                           contributors=people(*CASTILIAN_VOICES), **CASTILIAN)],
        hardcover=[edition(HC, "2", title="Dungeon Crawler Carl", release_date="2025-07-10",
                           contributors=people(*NEUTRAL_VOICES), **CASTILIAN)],
    ))
    assert len(groups) == 2


DANDY = {"publisher": "Dandy House", "release_date": "2020-10-02"}


def test_format_alone_does_not_split_an_isbn_group():
    # Hardcover often records audiobooks as "physical"; same publisher and year means the same edition.
    groups = align(works(
        hardcover=[edition(HC, "1", isbn13="9781538555606", format="physical", publisher="Blackstone Audio", release_date="2018-06-12")],
        goodreads=[edition(GR, "2", isbn13="9781538555606", format="audiobook", publisher="Blackstone Audiobooks", release_date="2018-06-12")],
    ))
    assert len(groups) == 1 and groups[0].format_clashes == []


def test_isbn_shared_by_unrelated_looking_records_is_flagged_not_split():
    groups = align(works(
        hardcover=[edition(HC, "1", isbn13="9781405989411", format="ebook", **DANDY)],
        goodreads=[edition(GR, "2", isbn13="9781405989411", format="physical", publisher="Penguin", release_date="2026-10-01")],
    ))
    assert len(groups) == 1 and groups[0].format_clashes == ["9781405989411"]
