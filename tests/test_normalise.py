import pytest

from libarrei import normalise


@pytest.mark.parametrize("raw, expected", [
    ("1937-09-21", "1937-09-21"),
    ("2002", "2002"),
    ("February 15th 2012", "2012-02-15"),
    ("January 1st 2014", "2014-01-01"),
    ("December 2001", "2001-12"),
    ("Sep 21, 1937", "1937-09-21"),
    ("21 September 1937", "1937-09-21"),
    ("15 julho 2019", "2019"),
    ("2001?", "2001"),
    ("by Adelphi", None),
    ("", None),
])
def test_release_date(raw, expected):
    assert normalise.release_date(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("en", "en"), ("fre", "fr"), ("ger", "de"), ("chi", "zh"), ("eng", "en"),
    ("English", "en"), ("Greek, Modern (1453-)", "el"), ("Catalan; Valencian", "ca"),
    ("Bokmål, Norwegian; Norwegian Bokmål", "nb"), ("Lule Sami", "smj"), ("Slavic (Other)", "slavic (other)"),
])
def test_language(raw, expected):
    assert normalise.language(raw) == expected


def test_isbn_cleans_and_validates():
    assert normalise.isbn("978-0-547-95196-6") == "9780547951966"
    assert normalise.isbn("0-618-00221-9") == "0618002219"
    assert normalise.isbn("9780547951967") is None
    assert normalise.isbn10_to_13("0547951965") == "9780547951966"


def test_asin_drops_isbn10_lookalikes():
    assert normalise.asin("9505470630") is None
    assert normalise.asin("b0079kt81g") == "B0079KT81G"


def test_work_normalises_editions_and_derives_isbn13():
    from libarrei.model import Edition, Source, Work

    work = Work()
    edition = Edition()
    edition.add("isbn10", "0-547-95196-5", Source.GOODREADS, "1")
    edition.add("asin", "0547951965", Source.GOODREADS, "1")
    edition.add("release_date", "by Adelphi", Source.GOODREADS, "1")
    edition.add("language", "English", Source.GOODREADS, "1")
    work.editions.append(edition)

    normalise.work(work)

    assert [c.value for c in edition.isbn13] == ["9780547951966"]
    assert edition.asin == [] and edition.release_date == []
    assert edition.language[0].value == "en"


def test_zero_pages_count_as_unknown():
    assert normalise.pages(0) is None and normalise.pages(310) == 310


def test_audiobook_pages_are_dropped():
    from libarrei.model import Edition, Source, Work

    work, audio = Work(), Edition()
    audio.add("format", "audiobook", Source.GOODREADS, "1")
    audio.add("pages", 15, Source.GOODREADS, "1")
    work.editions.append(audio)

    normalise.work(work)

    assert audio.pages == []


def test_genres_drop_shelves_and_machine_tags():
    raw = ["Fiction", "Audiobook", "Book Club", "nyt:combined-print-and-e-book-fiction=2023-04-02", "Romance"]
    assert normalise.genres(raw) == ["Fiction", "Romance"]
    assert normalise.genres(["Audiobook"]) is None


def test_spanish_narration_label_is_stripped():
    from libarrei.normalise import strip_language_label
    assert strip_language_label("Carl el mazmorrero [Narración en español castellano]") == "Carl el mazmorrero"
