"""How complete each source's record of an edition is, as a score from 0 to 100.

Only fields the source can ever provide count, so a store is not marked down
for lacking fields it never has. Identifiers weigh most: without one a record
cannot be matched or corrected reliably.
"""

from libarrei.capabilities import EDITION
from libarrei.merge import MergedEdition, MergedWork, text_key
from libarrei.model import Source

WEIGHTS = {
    "isbn13": 14, "isbn10": 6, "asin": 10,
    "contributors": 12, "publisher": 8, "release_date": 8,
    "pages": 8, "duration_seconds": 8,
    "format": 6, "language": 6, "cover_url": 4, "title": 5,
}
IDENTIFIERS = ("isbn13", "isbn10", "asin")
# Below this a record is "sparse" in the GUI and a candidate stub.
SPARSE = 40


def _relevant(field: str, audiobook: bool) -> bool:
    # Page counts mean nothing for audio, and durations nothing for print.
    return field != ("pages" if audiobook else "duration_seconds")


def is_audiobook(edition: MergedEdition) -> bool:
    fmt = edition.fields.get("format")
    return bool(fmt) and fmt.value == "audiobook"


def record_fields(edition: MergedEdition) -> dict[tuple[Source, str], set[str]]:
    """Which fields each (source, record id) filled."""
    filled: dict[tuple[Source, str], set[str]] = {(s, i): set() for s, ids in edition.ids.items() for i in ids}
    for name, resolved in edition.fields.items():
        for v in resolved.values:
            filled.setdefault((v.source, v.source_id), set()).add(name)
    return filled


def score(source: Source, fields: set[str], audiobook: bool) -> int:
    counted = [f for f in WEIGHTS if f in EDITION[source] and _relevant(f, audiobook)]
    total = sum(WEIGHTS[f] for f in counted)
    value = round(100 * sum(WEIGHTS[f] for f in counted if f in fields) / total) if total else 0
    # However full, a record with no identifier cannot be matched or corrected reliably, so it stays sparse.
    if any(f in counted for f in IDENTIFIERS) and not any(f in fields for f in IDENTIFIERS):
        value = min(value, SPARSE - 1)
    return value


def edition_quality(edition: MergedEdition) -> dict[Source, int]:
    """Each source's best record here: a duplicate does not drag down a good one."""
    audiobook = is_audiobook(edition)
    best: dict[Source, int] = {}
    for (source, _), fields in record_fields(edition).items():
        best[source] = max(best.get(source, 0), score(source, fields, audiobook))
    return best


def work_quality(editions: list[MergedEdition]) -> dict[Source, int]:
    """Each source's mean score over the editions it has a record of."""
    scores: dict[Source, list[int]] = {}
    for edition in editions:
        for source, value in edition.quality.items():
            scores.setdefault(source, []).append(value)
    return {s: round(sum(v) / len(v)) for s, v in scores.items()}


def _has_identifier(edition: MergedEdition) -> bool:
    return any(edition.fields.get(f) for f in IDENTIFIERS)


def _value_key(edition: MergedEdition, field: str):
    resolved = edition.fields.get(field)
    return text_key(str(resolved.value)) if resolved else None


def _year(edition: MergedEdition) -> str | None:
    resolved = edition.fields.get("release_date")
    return str(resolved.value)[:4] if resolved else None


def looks_like(stub: MergedEdition, full: MergedEdition) -> bool:
    same = all(_value_key(stub, f) and _value_key(stub, f) == _value_key(full, f) for f in ("title", "format", "language"))
    publisher = _value_key(stub, "publisher")
    year = _year(stub)
    return same and ((publisher and publisher == _value_key(full, "publisher")) or (year and year == _year(full)))


def find_stubs(editions: list[MergedEdition]) -> None:
    """Links sparse editions without identifiers to a fuller one they likely duplicate.

    Only a hint for the librarian: merging on so little evidence could spread one
    edition's data onto another, so the editions stay separate.
    """
    full = [e for e in editions if _has_identifier(e)]
    for edition in editions:
        if _has_identifier(edition) or not edition.quality or max(edition.quality.values()) >= SPARSE:
            continue
        matches = [f for f in full if looks_like(edition, f)]
        # The fullest candidate is the likeliest original.
        if matches:
            edition.stub_of = max(matches, key=lambda f: max(f.quality.values(), default=0)).ids


def score_work(work: MergedWork) -> MergedWork:
    for edition in work.editions:
        edition.quality = edition_quality(edition)
    work.quality = work_quality(work.editions)
    find_stubs(work.editions)
    return work
