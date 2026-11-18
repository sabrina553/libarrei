"""Turns each source's description into one safe, structured form.

Goodreads sends HTML; Hardcover and Open Library send Markdown, sometimes with
inline HTML such as <i>. Everything becomes blocks of styled text runs, keeping
only bold, italic, paragraphs, line breaks and list items. Nothing else
survives: unknown tags are unwrapped to their text, scripts and styles are
dropped with their contents, and links are reduced to their text, so the GUI
can render the result as plain elements with no HTML injection.
"""

import re
from html.parser import HTMLParser
from typing import Literal

from pydantic import BaseModel


class Run(BaseModel):
    # May contain "\n" for a line break inside a block.
    text: str
    bold: bool = False
    italic: bool = False


class Block(BaseModel):
    kind: Literal["paragraph", "item"] = "paragraph"
    runs: list[Run] = []


BOLD_TAGS = {"b", "strong"}
ITALIC_TAGS = {"i", "em", "cite"}
BLOCK_TAGS = {"p", "div", "blockquote", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "section", "article"}
# Their text is code or styling, never prose.
DROPPED_TAGS = {"script", "style", "template", "noscript", "iframe", "object", "svg", "math", "title", "head"}

PROMO = re.compile(r"^\s*brought to you by\b", re.IGNORECASE)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.current = Block()
        self.bold = self.italic = self.dropped = 0

    def end_block(self, kind: str = "paragraph") -> None:
        if any(r.text.strip() for r in self.current.runs):
            self.blocks.append(self.current)
        self.current = Block(kind=kind)

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_TAGS:
            self.dropped += 1
        elif tag in BOLD_TAGS:
            self.bold += 1
        elif tag in ITALIC_TAGS:
            self.italic += 1
        elif tag == "br":
            self.add("\n")
        elif tag == "li":
            self.end_block("item")
        elif tag in BLOCK_TAGS:
            self.end_block()

    def handle_startendtag(self, tag, attrs):
        # A self-closing <b/> or <script/> opens nothing, so only breaks matter.
        if tag == "br":
            self.add("\n")
        elif tag in BLOCK_TAGS:
            self.end_block()

    def handle_endtag(self, tag):
        if tag in DROPPED_TAGS:
            self.dropped = max(0, self.dropped - 1)
        elif tag in BOLD_TAGS:
            self.bold = max(0, self.bold - 1)
        elif tag in ITALIC_TAGS:
            self.italic = max(0, self.italic - 1)
        elif tag == "li" or tag in BLOCK_TAGS:
            self.end_block()

    def handle_data(self, data):
        # Source newlines are layout, as in a browser; only <br> breaks a line.
        self.add(re.sub(r"\s+", " ", data))

    def add(self, text: str) -> None:
        if self.dropped or not text:
            return
        run = Run(text=text, bold=self.bold > 0, italic=self.italic > 0)
        runs = self.current.runs
        if runs and (runs[-1].bold, runs[-1].italic) == (run.bold, run.italic):
            runs[-1].text += text
        else:
            runs.append(run)


def _tidy(block: Block) -> Block | None:
    """Collapses whitespace like a browser would, keeping explicit line breaks."""
    runs: list[Run] = []
    for run in block.runs:
        lines = [re.sub(r"[ \t\r\f\v ]+", " ", line) for line in run.text.split("\n")]
        text = "\n".join(lines)
        if runs and runs[-1].text.endswith((" ", "\n")):
            text = text.lstrip(" ")
        if text:
            runs.append(run.model_copy(update={"text": text}))
    if runs:
        runs[0].text = runs[0].text.lstrip(" \n")
        runs[-1].text = runs[-1].text.rstrip(" \n")
    for run in runs:
        run.text = re.sub(r" ?\n ?", "\n", run.text)
        run.text = re.sub(r"\n{2,}", "\n", run.text)
    runs = [r for r in runs if r.text]
    return Block(kind=block.kind, runs=runs) if runs else None


# Markdown seen in Hardcover and Open Library descriptions.
_MD_LINK_DEFINITION = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*\S+.*$", re.MULTILINE)
_MD_SOURCE_FOOTER = re.compile(r"\(\s*\[(?:source|from)[^\]]*\]\s*(?:\[[^\]]*\]|\([^)]*\))\s*\)", re.IGNORECASE)
_MD_LINK = re.compile(r"(?<!\\)\[((?:\\.|[^\]\\])*)\]\s?(?:\((?:[^()\s]|\([^()\s]*\))*(?:\s+\"[^\"]*\")?\)|\[[^\]]*\])")
_MD_RULE = re.compile(r"^[ \t]*([-*_])([ \t]*\1){2,}[ \t]*$", re.MULTILINE)
_MD_QUOTE = re.compile(r"^[ \t]{0,3}>\s?", re.MULTILINE)
_MD_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}\s+", re.MULTILINE)
_MD_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])\s+(.*)$")
_MD_BOLD = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
_MD_ITALIC = re.compile(r"(?<![\w*])([*_])(?=\S)(.+?)(?<=\S)\1(?![\w*])")
_MD_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>])")


def markdown_to_html(text: str) -> str:
    """Rewrites the Markdown subset sources use as the HTML tags the builder understands.

    The output is parsed by the same allow-listing HTML parser as Goodreads HTML,
    so anything this misses is reduced to text rather than passed through.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MD_LINK_DEFINITION.sub("", text)
    text = _MD_SOURCE_FOOTER.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_RULE.sub("\n", text)
    text = _MD_QUOTE.sub("", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_BOLD.sub(r"<b>\2</b>", text)
    text = _MD_ITALIC.sub(r"<i>\2</i>", text)
    text = _MD_ESCAPE.sub(r"\1", text)
    out = []
    for paragraph in re.split(r"\n\s*\n", text):
        lines, prose = paragraph.split("\n"), []
        for line in lines:
            if item := _MD_ITEM.match(line):
                if prose:
                    out.append("<p>" + "<br>".join(prose) + "</p>")
                    prose = []
                out.append(f"<li>{item.group(1)}</li>")
            else:
                prose.append(line)
        if prose:
            out.append("<p>" + "<br>".join(prose) + "</p>")
    return "".join(out)


def parse_description(raw: str, markdown: bool = False) -> list[Block]:
    """Safe blocks from a source's description, without publisher promo lines."""
    builder = _Builder()
    builder.feed(markdown_to_html(raw) if markdown else raw)
    builder.close()
    builder.end_block()
    blocks = []
    for block in builder.blocks:
        # A promo line can share a block with prose when only <br> separates them.
        lines = plain_text([block]).split("\n")
        if any(PROMO.match(line) for line in lines):
            block = _without_promo(block)
        if block and (tidy := _tidy(block)):
            blocks.append(tidy)
    return blocks


def _without_promo(block: Block) -> Block | None:
    """Drops each line that starts like a promo, even when it spans several runs."""
    runs, line_start, skipping = [], True, False
    for run in block.runs:
        kept = []
        for i, part in enumerate(run.text.split("\n")):
            if i:
                line_start, skipping = True, False
            if line_start and PROMO.match(part):
                skipping = True
            if not skipping:
                kept.append(part)
            line_start = line_start and not part.strip()
        if kept:
            runs.append(run.model_copy(update={"text": "\n".join(kept)}))
    return Block(kind=block.kind, runs=runs) if runs else None


def plain_text(blocks: list[Block]) -> str:
    """Formatting-free text: blocks on separate lines, paragraphs a blank line apart."""
    out = ""
    for i, block in enumerate(blocks):
        text = "".join(r.text for r in block.runs)
        if i:
            out += "\n" if block.kind == "item" and blocks[i - 1].kind == "item" else "\n\n"
        out += text
    return out
