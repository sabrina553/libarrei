

def test_found_work_must_carry_a_close_title():
    from libarrei.lookup import titled_like
    from libarrei.model import Candidate, Edition, Source, Work

    def work(*titles):
        e = Edition(title=[Candidate(value=t, source=Source.HARDCOVER, source_id="1") for t in titles[1:]])
        return Work(title=[Candidate(value=titles[0], source=Source.HARDCOVER, source_id="1")], editions=[e])

    assert titled_like(work("Atomic Habits: An Easy & Proven Way"), "Atomic Habits")
    assert titled_like(work("Dune: The Butlerian Jihad"), "Dune")
    assert titled_like(work("三体", "The Three-Body Problem"), "The Three-Body Problem")
    assert not titled_like(work("Delphi Collected Works of Thomas Hobbes"), "The Complete Collection [The Iliad & The Odyssey]")
    assert not titled_like(work("One More for the Road"), "Fahrenheit 451")
