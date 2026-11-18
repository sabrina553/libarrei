from libarrei.cli import show
from libarrei.model import Contributor, SeriesEntry


def test_show_formats_model_values():
    assert show([Contributor(name="A"), Contributor(name="B", role="narrator")]) == "A, B (narrator)"
    assert show([SeriesEntry(name="Castle Knoll Files", position="3")]) == "Castle Knoll Files #3"
    assert show("line one\n  line two") == "line one line two"


def test_print_merged_shows_source_conflict_and_alternatives(capsys):
    from libarrei.cli import print_merged
    from libarrei.merge import merge
    from libarrei.model import Source, Work

    hc, gr = Work(), Work()
    hc.add("original_release_date", "1937-09-21", Source.HARDCOVER, "1")
    gr.add("original_release_date", "1966", Source.GOODREADS, "2")

    print_merged(merge({Source.HARDCOVER: hc, Source.GOODREADS: gr}), with_editions=False)

    out = capsys.readouterr().out
    assert "[hardcover] CONFLICT 1937-09-21" in out and "[goodreads] 1966" in out
