from libarrei import lookup as lookup_module
from libarrei.model import Candidate, Contributor, Edition, Source, Work


def test_found_work_must_carry_a_close_title():
    from libarrei.lookup import titled_like

    def work(*titles):
        e = Edition(title=[Candidate(value=t, source=Source.HARDCOVER, source_id="1") for t in titles[1:]])
        return Work(title=[Candidate(value=titles[0], source=Source.HARDCOVER, source_id="1")], editions=[e])

    assert titled_like(work("Atomic Habits: An Easy & Proven Way"), "Atomic Habits")
    assert titled_like(work("Dune: The Butlerian Jihad"), "Dune")
    assert titled_like(work("三体", "The Three-Body Problem"), "The Three-Body Problem")
    assert not titled_like(work("Delphi Collected Works of Thomas Hobbes"), "The Complete Collection [The Iliad & The Odyssey]")
    assert not titled_like(work("One More for the Road"), "Fahrenheit 451")



HC, GR, OL = Source.HARDCOVER, Source.GOODREADS, Source.OPENLIBRARY


def found(source: Source, title: str, author: str = "Homer", isbn: str | None = None) -> Work:
    edition = Edition()
    edition.add("title", title, source, "1")
    edition.add("isbn13", isbn, source, "1")
    work = Work(editions=[edition])
    work.add("title", title, source, "1")
    work.add("contributors", [Contributor(name=author)], source, "1")
    return work


def test_original_script_titles_are_compared_transliterated():
    from libarrei.lookup import titled_like
    assert titled_like(found(GR, "Ἰλιάς"), "The Iliad")
    assert titled_like(found(GR, "Ὀδύσσεια"), "The Odyssey")
    assert not titled_like(found(GR, "Преступление и наказание"), "Crime and Punishment")


def test_alternative_titles_count():
    from libarrei.lookup import titled_like
    work = found(HC, "Преступление и наказание", "Fyodor Dostoevsky")
    work._aliases = ["Crime and Punishment"]
    assert titled_like(work, "Crime and Punishment")
    assert "_aliases" not in work.model_dump()


def test_a_shared_identifier_and_author_vouch_for_a_translated_title():
    from libarrei.lookup import vouched_for
    original = found(GR, "三体", "Liu Cixin", isbn="9780765382030")
    english = found(HC, "The Three-Body Problem", "Cixin Liu", isbn="9780765382030")
    assert vouched_for(GR, original, {HC: english})
    # Neither an identifier nor an author is enough alone.
    assert not vouched_for(GR, found(GR, "三体", "Liu Cixin", isbn="9780000000002"), {HC: english})
    assert not vouched_for(GR, found(GR, "Leviathan", "Thomas Hobbes", isbn="9780765382030"), {HC: english})


def run_lookup(monkeypatch, works: dict[Source, Work], title: str):
    for name in ("HARDCOVER_TOKEN", "GOODREADS_TOKEN"):
        monkeypatch.setenv(name, "x")
    monkeypatch.delenv("AMAZON_COOKIE", raising=False)
    monkeypatch.setattr(lookup_module, "from_openlibrary", lambda *a: works.get(OL))
    monkeypatch.setattr(lookup_module, "from_hardcover", lambda *a: works.get(HC))
    monkeypatch.setattr(lookup_module, "from_goodreads", lambda *a: works.get(GR))
    monkeypatch.setattr(lookup_module, "from_audible", lambda *a: None)
    return lookup_module.lookup(title=title, use_cache=False)


def test_lookup_keeps_a_vouched_result_and_drops_an_unlinked_one(monkeypatch):
    english = found(HC, "The Three-Body Problem", "Cixin Liu", isbn="9780765382030")
    original = found(GR, "三体", "Liu Cixin", isbn="9780765382030")
    hobbes = found(OL, "Delphi Collected Works of Thomas Hobbes", "Thomas Hobbes", isbn="9781786560000")
    result = run_lookup(monkeypatch, {HC: english, GR: original, OL: hobbes}, "The Three-Body Problem")
    assert set(result.works) == {HC, GR}
    assert GR not in result.notes and result.notes[OL].startswith("no close title match")


def test_a_bracketed_part_of_the_searched_title_can_match():
    from libarrei.lookup import titled_like
    wanted = "The Complete Collection [The Iliad & The Odyssey]"
    assert titled_like(found(GR, "Ἰλιάς / Ὀδύσσεια"), wanted)
    assert not titled_like(found(HC, "Delphi Collected Works of Thomas Hobbes"), wanted)
    assert not titled_like(found(HC, "Illustrated Atlas"), "Middlemarch [Illustrated]")
