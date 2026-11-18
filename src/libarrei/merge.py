"""Picks one value per field for a work and each aligned edition group.

Nothing is thrown away: every other distinct value is kept as an alternative,
and fields where sources genuinely disagree are flagged for review.
"""

import re

from bs4 import BeautifulSoup
from pydantic import BaseModel

from libarrei.match import EditionGroup, align
from libarrei.model import Candidate, Source, Work

GR, HC, OL = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY

# Goodreads carries the richest blurbs and reader-voted genres; Hardcover's
# librarian-edited structured data is the most reliable for everything else.
TEXT_PRIORITY = [GR, HC, OL]
DATA_PRIORITY = [HC, GR, OL]
TEXT_FIELDS = {"description", "genres"}

# Fields that legitimately differ between sources, so differences aren't conflicts.
NEVER_CONFLICT = {"genres", "cover_url", "identifiers"}

# Placeholders until each source's terms are confirmed.
LICENCES = {OL: "CC0-1.0", GR: "publisher copyright", HC: "see Hardcover terms"}

WORK_FIELDS = ["title", "subtitle", "contributors", "description", "series", "genres", "original_release_date"]
EDITION_FIELDS = ["title", "subtitle", "edition_statement", "contributors", "isbn13", "isbn10", "asin",
                  "identifiers", "publisher", "release_date", "pages", "format", "format_detail",
                  "duration_seconds", "language", "cover_url", "series"]
DATE_FIELDS = {"release_date", "original_release_date"}


class Alternative(BaseModel):
    value: object
    source: Source
    source_id: str


class Resolved(BaseModel):
    value: object
    source: Source
    source_id: str
    alternatives: list[Alternative] = []
    # Every source's value, agreeing or not, so a review grid can show each one.
    values: list[Alternative] = []
    conflict: bool = False
    licence: str | None = None


class MergedEdition(BaseModel):
    ids: dict[Source, list[str]]
    match_reason: str | None
    confidence: float
    duplicates: list[Source]
    fields: dict[str, Resolved]


class MergedWork(BaseModel):
    ids: dict[Source, str]
    fields: dict[str, Resolved]
    editions: list[MergedEdition]


def merge(works: dict[Source, Work]) -> MergedWork:
    work_fields = {}
    for name in WORK_FIELDS:
        candidates = [c for w in works.values() for c in getattr(w, name)]
        if resolved := resolve(name, candidates):
            work_fields[name] = resolved
    return MergedWork(
        ids={s: w.ids[s] for s, w in works.items() if s in w.ids},
        fields=work_fields,
        editions=[merge_group(g) for g in align(works)],
    )


def merge_group(group: EditionGroup) -> MergedEdition:
    ids: dict[Source, list[str]] = {}
    for source, edition in group.members:
        if source in edition.ids:
            ids.setdefault(source, []).append(edition.ids[source])
    fields = {}
    for name in EDITION_FIELDS:
        candidates = [c for _, e in group.members for c in getattr(e, name)]
        if resolved := resolve(name, candidates):
            fields[name] = resolved
    return MergedEdition(ids=ids, match_reason=group.reason, confidence=group.confidence,
                         duplicates=group.duplicates, fields=fields)


def resolve(name: str, candidates: list[Candidate]) -> Resolved | None:
    if name == "description":
        candidates = [c.model_copy(update={"value": v}) for c in candidates if (v := clean_description(c.value))]
    if not candidates:
        return None
    priority = TEXT_PRIORITY if name in TEXT_FIELDS else DATA_PRIORITY
    ranked = sorted(candidates, key=lambda c: priority.index(c.source))

    if name in DATE_FIELDS:
        chosen, conflict = _resolve_date(ranked)
    else:
        chosen = ranked[0]
        conflict = any(key(name, c.value) != key(name, chosen.value) for c in ranked)

    seen, alternatives = {key(name, chosen.value)}, []
    for c in ranked:
        if (k := key(name, c.value)) not in seen:
            seen.add(k)
            alternatives.append(Alternative(value=c.value, source=c.source, source_id=c.source_id))
    return Resolved(
        value=chosen.value, source=chosen.source, source_id=chosen.source_id, alternatives=alternatives,
        values=[Alternative(value=c.value, source=c.source, source_id=c.source_id) for c in ranked],
        conflict=conflict and name not in NEVER_CONFLICT,
        licence=LICENCES[chosen.source] if name == "description" else None,
    )


def text_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold())


def key(name: str, value):
    """What two values must share to count as agreeing."""
    if name == "contributors":
        return frozenset(text_key(c.name) for c in value)
    if name == "series":
        return frozenset((text_key(s.name), s.position) for s in value)
    if name == "identifiers":
        return frozenset((i.scheme, i.value) for i in value)
    if name == "genres":
        return frozenset(text_key(g) for g in value)
    if isinstance(value, str):
        return text_key(value)
    return value


def effective_date(c: Candidate) -> str:
    # Hardcover pads year-only dates to 1 January, which would otherwise look more precise.
    if c.source == HC and c.value.endswith("-01-01"):
        return c.value[:4]
    return c.value


def _resolve_date(ranked: list[Candidate]) -> tuple[Candidate, bool]:
    """The top-priority date, or a more precise one it is compatible with."""
    top = effective_date(ranked[0])
    compatible = [c for c in ranked if effective_date(c).startswith(top) or top.startswith(effective_date(c))]
    chosen = max(compatible, key=lambda c: len(effective_date(c)))
    best = effective_date(chosen)
    conflict = any(not best.startswith(effective_date(c)) for c in ranked)
    return chosen, conflict


PROMO = re.compile(r"^\s*brought to you by\b", re.IGNORECASE)


def clean_description(raw: str) -> str | None:
    """Plain text without HTML or publisher promo lines."""
    soup = BeautifulSoup(raw, "html.parser")
    # Only block-level breaks become newlines, so inline tags like <b> don't split sentences.
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li"]):
        block.append("\n")
    text = soup.get_text()
    lines = [line.strip() for line in text.splitlines()]
    kept = "\n".join(line for line in lines if not PROMO.match(line))
    return re.sub(r"\n{3,}", "\n\n", kept).strip() or None
