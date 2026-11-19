"""How complete each source's record of an edition is, as a score from 0 to 100.

Only fields the source can ever provide count, so a store is not marked down
for lacking fields it never has. Identifiers weigh most: without one a record
cannot be matched or corrected reliably.
"""

from datetime import date

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


# Store listings round a recording's length differently, so a minute or two apart is still one recording.
LISTING_SECONDS = 120
# Stores launch the same recording a few days apart.
LISTING_DAYS = 3


def _narrators(edition: MergedEdition) -> frozenset[str]:
    resolved = edition.fields.get("contributors")
    people = resolved.value if resolved and isinstance(resolved.value, list) else []
    def get(p, key):
        return p.get(key) if isinstance(p, dict) else getattr(p, key, None)
    return frozenset(text_key(get(p, "name") or "") for p in people if get(p, "role") == "narrator" and get(p, "name"))


def _seconds(edition: MergedEdition) -> int | None:
    resolved = edition.fields.get("duration_seconds")
    return int(resolved.value) if resolved and isinstance(resolved.value, int | float) else None


def _launch(edition: MergedEdition) -> str | None:
    resolved = edition.fields.get("release_date")
    return str(resolved.value) if resolved else None


def _dates_agree(a: str, b: str) -> bool:
    # 1 January is the usual placeholder when only the year is known, so it compares by year.
    if len(a) < 10 or len(b) < 10 or a[4:10] == "-01-01" or b[4:10] == "-01-01":
        return a[:4] == b[:4]
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days) <= LISTING_DAYS
    except ValueError:
        return False


def same_recording(a: MergedEdition, b: MergedEdition) -> bool:
    """Whether two audiobook editions are one recording listed separately, as each Audible store does."""
    if _value_key(a, "format") != "audiobook" or _value_key(b, "format") != "audiobook":
        return False
    voices, publisher = _narrators(a), _value_key(a, "publisher")
    seconds_a, seconds_b, launch_a, launch_b = _seconds(a), _seconds(b), _launch(a), _launch(b)
    return bool(voices and voices == _narrators(b) and publisher and publisher == _value_key(b, "publisher")
                and seconds_a and seconds_b and abs(seconds_a - seconds_b) <= LISTING_SECONDS
                and launch_a and launch_b and _dates_agree(launch_a, launch_b))


def find_listings(editions: list[MergedEdition]) -> None:
    """Links other stores' listings of one audiobook recording to its best-filled listing.

    A hint only: each store sells its own listing, so whether to keep them apart is the librarian's call.
    Heads are taken best first, so every listing points at a head and never at another listing.
    """
    books = [e for e in editions if not e.stub_of and _value_key(e, "format") == "audiobook"]
    books.sort(key=lambda e: (max(e.quality.values(), default=0), len(e.ids)), reverse=True)
    heads: list[MergedEdition] = []
    for edition in books:
        head = next((h for h in heads if same_recording(edition, h)), None)
        if head:
            edition.listing_of = head.ids
        else:
            heads.append(edition)


def score_work(work: MergedWork) -> MergedWork:
    for edition in work.editions:
        edition.quality = edition_quality(edition)
    work.quality = work_quality(work.editions)
    find_stubs(work.editions)
    find_listings(work.editions)
    return work
