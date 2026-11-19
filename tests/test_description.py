from libarrei.description import Block, Run, parse_description, plain_text
from libarrei.merge import resolve
from libarrei.model import Candidate, Source

GR, HC, OL = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY


def runs(blocks):
    return [[(r.text, r.bold, r.italic) for r in b.runs] for b in blocks]


def test_goodreads_html_keeps_bold_italic_breaks_and_lists():
    blocks = parse_description("<b>Bold</b> and <i>italic</i><br>next line<p>Para</p><ul><li>One</li><li>Two</li></ul>")
    assert runs(blocks) == [
        [("Bold", True, False), (" and ", False, False), ("italic", False, True), ("\nnext line", False, False)],
        [("Para", False, False)],
        [("One", False, False)],
        [("Two", False, False)],
    ]
    assert [b.kind for b in blocks] == ["paragraph", "paragraph", "item", "item"]


def test_html_source_newlines_are_spaces():
    assert plain_text(parse_description("one\ntwo   three")) == "one two three"


def test_markdown_from_open_library():
    raw = ("**The apocalypse will be televised!**\r\n\r\nThey call it *Dungeon Crawler World*.\r\n\r\n"
           "----------\r\n\r\n**Contains**\r\n\r\n- [The Two Towers](https://openlibrary.org/works/OL27479W)\r\n"
           "- [The Lord of the Rings \\[1/6\\]](https://openlibrary.org/works/OL1W)\r\n\r\n"
           "([source][1])\r\n\r\n  [1]: https://example.org/")
    blocks = parse_description(raw, markdown=True)
    assert runs(blocks) == [
        [("The apocalypse will be televised!", True, False)],
        [("They call it ", False, False), ("Dungeon Crawler World", False, True), (".", False, False)],
        [("Contains", True, False)],
        [("The Two Towers", False, False)],
        [("The Lord of the Rings [1/6]", False, False)],
    ]


def test_markdown_from_hardcover_with_inline_html_and_quotes():
    raw = ('<i>"In a hole."</i> So begins.\r\n\r\n[Comment][1]:\r\nNext line\r\n\r\n> Quoted [Crash][3] text.'
           "\r\n\r\n  [1]: http://example.org\r\n  [3]: http://example.org/3")
    blocks = parse_description(raw, markdown=True)
    assert runs(blocks) == [
        [('"In a hole."', False, True), (" So begins.", False, False)],
        [("Comment:\nNext line", False, False)],
        [("Quoted Crash text.", False, False)],
    ]


def test_unsafe_markup_is_stripped():
    raw = ('<script>alert(1)</script><img src=x onerror="alert(2)"><a href="javascript:alert(3)">click</a>'
           '<b onclick="alert(4)">safe</b><style>p{}</style><iframe src="//evil">x</iframe>')
    blocks = parse_description(raw)
    assert runs(blocks) == [[("click", False, False), ("safe", True, False)]]
    dumped = str([b.model_dump() for b in blocks])
    assert "alert" not in dumped and "javascript" not in dumped and "onerror" not in dumped
    md = parse_description("[click](javascript:alert(1)) <script>alert(2)</script>", markdown=True)
    assert plain_text(md) == "click"


def test_promo_lines_are_dropped():
    assert plain_text(parse_description("<p>A novel.</p>Brought to you by Penguin.")) == "A novel."
    assert plain_text(parse_description("A novel.<br>Brought to you by Penguin.")) == "A novel."


def test_plain_text_separates_paragraphs_and_lists():
    blocks = [Block(runs=[Run(text="Intro")]), Block(kind="item", runs=[Run(text="a")]),
              Block(kind="item", runs=[Run(text="b")])]
    assert plain_text(blocks) == "Intro\n\na\nb"


def test_formatting_alone_is_not_a_conflict():
    r = resolve("description", [
        Candidate(value="<p><b>Big</b> news.</p><p>More  text.</p>", source=GR, source_id="1"),
        Candidate(value="**Big** news.\r\n\r\nMore text.", source=HC, source_id="2"),
        Candidate(value="Big news.\n\nMore text.", source=OL, source_id="3"),
    ])
    assert not r.conflict and r.value == "Big news.\n\nMore text."
    assert [v.formatted[0].runs[0].bold for v in r.values] == [True, True, False]


def test_different_wording_is_a_conflict():
    r = resolve("description", [Candidate(value="One.", source=GR, source_id="1"),
                                Candidate(value="Two.", source=OL, source_id="3")])
    assert r.conflict


def test_other_fields_carry_no_formatting():
    r = resolve("publisher", [Candidate(value="Allen", source=OL, source_id="3")])
    assert r.values[0].formatted is None
