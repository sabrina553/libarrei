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
