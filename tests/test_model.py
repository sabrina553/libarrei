from libarrei.model import Edition, Source, Work


def test_add_keeps_every_source_value():
    work = Work()
    work.add("title", "How to Cheat Your Own Death", Source.GOODREADS, "239433112")
    work.add("title", "How To Cheat Your Own Death", Source.HARDCOVER, "1234")

    assert [c.value for c in work.title] == ["How to Cheat Your Own Death", "How To Cheat Your Own Death"]
    assert work.ids == {Source.GOODREADS: "239433112", Source.HARDCOVER: "1234"}


def test_add_skips_empty_values():
    edition = Edition()
    for empty in (None, "", []):
        edition.add("subtitle", empty, Source.OPENLIBRARY, "OL1M")

    assert edition.subtitle == []
    assert edition.ids == {}


def test_round_trips_through_json():
    work = Work()
    work.add("genres", ["Mystery", "Fiction"], Source.GOODREADS, "1")
    work.editions.append(Edition())
    work.editions[0].add("pages", 336, Source.HARDCOVER, "9")

    assert Work.model_validate_json(work.model_dump_json()) == work
