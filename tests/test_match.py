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
