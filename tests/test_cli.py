from libarrei.cli import show
from libarrei.model import Contributor, SeriesEntry


def test_show_formats_model_values():
    assert show([Contributor(name="A"), Contributor(name="B", role="narrator")]) == "A, B (narrator)"
    assert show([SeriesEntry(name="Castle Knoll Files", position="3")]) == "Castle Knoll Files #3"
    assert show("line one\n  line two") == "line one line two"
