"""Picks one value per field for a work and each aligned edition group.

Nothing is thrown away: every other distinct value is kept as an alternative,
and fields where sources genuinely disagree are flagged for review.
"""

import re

from pydantic import BaseModel

from libarrei.description import Block, parse_description, plain_text
from libarrei.match import EditionGroup, align
from libarrei.model import Candidate, Source, Work
from libarrei.normalise import is_edition_statement

GR, HC, OL, AU, AZ = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY, Source.AUDIBLE, Source.AMAZON

# Goodreads carries the richest blurbs and reader-voted genres; Hardcover's
# librarian-edited structured data is the most reliable for everything else.
TEXT_PRIORITY = [GR, HC, OL, AU, AZ]
DATA_PRIORITY = [HC, GR, OL, AU, AZ]
TEXT_FIELDS = {"description", "genres"}

# Fields that legitimately differ between sources, so differences aren't conflicts.
NEVER_CONFLICT = {"genres", "cover_url", "identifiers"}

# Placeholders until each source's terms are confirmed.
LICENCES = {OL: "CC0-1.0", GR: "publisher copyright", HC: "see Hardcover terms", AU: "publisher copyright", AZ: "publisher copyright"}

WORK_FIELDS = ["title", "subtitle", "contributors", "description", "series", "genres", "original_release_date"]
EDITION_FIELDS = ["title", "subtitle", "edition_statement", "contributors", "isbn13", "isbn10", "asin",
                  "identifiers", "publisher", "release_date", "pages", "format", "format_detail",
                  "duration_seconds", "language", "cover_url", "series"]
# Sources whose descriptions are HTML; the others send Markdown with the odd inline HTML tag.
HTML_DESCRIPTIONS = {GR, AU, AZ}
DATE_FIELDS = {"release_date", "original_release_date"}


class Alternative(BaseModel):
    value: object
    source: Source
    source_id: str
    # Descriptions only: the value's safe formatting, whose plain text is the value.
    formatted: list[Block] | None = None


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
    # Which identifiers each duplicated source's records share, e.g. {"openlibrary": ["isbn13"]}.
    duplicate_reasons: dict[Source, list[str]] = {}
    fields: dict[str, Resolved]
    # Catalogue ASINs checked against the store: same_product, other_product or not_found.
    asin_checks: dict[str, str] = {}
    # Each source's record completeness, 0 to 100 (see quality.py).
    quality: dict[Source, int] = {}
    # The ids of a fuller edition this sparse, identifier-less one probably duplicates.
    stub_of: dict[Source, list[str]] | None = None
    # ISBNs joining records that disagree on format, publisher and year: one probably cites the other's ISBN.
    format_clash_isbns: list[str] = []
    # Page slugs for sources that address records by slug, such as Hardcover's book slug.
    slugs: dict[Source, str] = {}


class MergedWork(BaseModel):
    ids: dict[Source, str]
    fields: dict[str, Resolved]
    editions: list[MergedEdition]
    # Each source's mean edition completeness.
    quality: dict[Source, int] = {}
    slugs: dict[Source, str] = {}


def merge(works: dict[Source, Work]) -> MergedWork:
    work_fields = {}
    for name in WORK_FIELDS:
        candidates = work_candidates(name, [c for w in works.values() for c in getattr(w, name)])
        if resolved := resolve(name, candidates):
            work_fields[name] = resolved
    # Imported here because scoring reads the merged models defined in this module.
    from libarrei.quality import score_work
    return score_work(MergedWork(
        ids={s: w.ids[s] for s, w in works.items() if s in w.ids},
        fields=work_fields,
        editions=[merge_group(g) for g in align(works)],
        slugs={s: w.slugs[s] for s, w in works.items() if s in w.slugs},
    ))


def work_candidates(name: str, candidates: list[Candidate]) -> list[Candidate]:
    """Drops what belongs to an edition rather than the work.

    Done here rather than in each source's mapping so every source, present and
    future, is treated alike. Translators, narrators, illustrators and the like
    belong to a particular edition, so the work keeps its authors only. A
    "subtitle" such as "Deluxe Edition" is an edition statement, not the work's.
    """
    if name == "contributors":
        kept = []
        for c in candidates:
            authors = [p for p in c.value if p.role == "author"]
            if authors:
                kept.append(c.model_copy(update={"value": authors}))
        return kept
    if name == "subtitle":
        return [c for c in candidates if not is_edition_statement(c.value)]
    return candidates


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
                         duplicates=group.duplicates, duplicate_reasons=group.duplicate_reasons,
                         format_clash_isbns=group.format_clashes,
                         fields=fields, slugs={s: slug for _, e in group.members for s, slug in e.slugs.items()})


def resolve(name: str, candidates: list[Candidate]) -> Resolved | None:
    formatted: dict[int, list[Block]] = {}
    if name == "description":
        parsed = [(c, b) for c in candidates if (b := description_blocks(c.source, c.value))]
        candidates = [c.model_copy(update={"value": plain_text(b)}) for c, b in parsed]
        formatted = {id(c): b for c, (_, b) in zip(candidates, parsed)}
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
            alternatives.append(_alternative(c, formatted))
    return Resolved(
        value=chosen.value, source=chosen.source, source_id=chosen.source_id, alternatives=alternatives,
        values=[_alternative(c, formatted) for c in ranked],
        conflict=conflict and name not in NEVER_CONFLICT,
        licence=LICENCES[chosen.source] if name == "description" else None,
    )


def _alternative(c: Candidate, formatted: dict[int, list[Block]]) -> Alternative:
    return Alternative(value=c.value, source=c.source, source_id=c.source_id, formatted=formatted.get(id(c)))


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


def description_blocks(source: Source, raw: str) -> list[Block]:
    return parse_description(raw, markdown=source not in HTML_DESCRIPTIONS)


def clean_description(raw: str, source: Source = GR) -> str | None:
    """Plain text without markup or publisher promo lines."""
    return plain_text(description_blocks(source, raw)) or None
