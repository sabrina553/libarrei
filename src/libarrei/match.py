"""Aligns editions across sources so each group is one real-world edition.

Shared identifiers decide most groups. An ASIN links editions only when their
formats agree, since catalogues (Goodreads especially) often cite a Kindle ASIN
on a print edition. One that Amazon or Audible itself reported is as firm as an
ISBN ("store_asin"); one only catalogues cite is the weaker reason "asin".

Editions without an identifier are paired only when
every available signal agrees and the pair is each other's clear best match:
in a correction tool a wrong merge spreads one edition's data onto another,
while a missed match merely shows up as "missing from source X".
"""

import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from libarrei.model import Edition, Source, Work

# Strongest first: the order decides which reason a group reports.
KEYS = ("isbn13", "store_asin", "asin", "goodreads_id")
DUPLICATE_KEYS = ("isbn13", "isbn10", "store_asin", "asin")
# Stores whose own product ids are ASINs, so the ASINs they report are confirmed.
STORES = {Source.AMAZON, Source.AUDIBLE}
# A group joined only by an unconfirmed ASIN is likelier to be wrong than one joined by an ISBN.
WEAK_ASIN_CONFIDENCE = 0.8


def confirmed_asins(edition: Edition) -> set[str]:
    return {c.value for c in edition.asin if c.source in STORES}


def _shared_keys(edition: Edition, confirmed: set[str]) -> set[tuple[str, str]]:
    keys = {(kind, c.value) for kind in ("isbn13", "isbn10") for c in getattr(edition, kind)}
    return keys | {("store_asin" if c.value in confirmed else "asin", c.value) for c in edition.asin}


def _formats_agree(a: Edition, b: Edition) -> bool:
    formats_a, formats_b = {c.value for c in a.format}, {c.value for c in b.format}
    return not formats_a or not formats_b or bool(formats_a & formats_b)


def _keys(source: Source, edition: Edition) -> list[tuple[str, str]]:
    """Identifiers that mark the same real-world edition, wherever they were recorded."""
    keys = [(key, c.value) for key in ("isbn13", "asin") for c in getattr(edition, key)]
    # Open Library editions often cite their Goodreads edition, a link as firm as an ISBN.
    if source == Source.GOODREADS and source in edition.ids:
        keys.append(("goodreads_id", edition.ids[source]))
    keys += [("goodreads_id", i.value) for c in edition.identifiers for i in c.value if i.scheme == "goodreads"]
    return keys


@dataclass
class EditionGroup:
    members: list[tuple[Source, Edition]] = field(default_factory=list)
    # How the group was formed: "isbn13", "asin", "goodreads_id", "fuzzy", or None for a lone edition.
    reason: str | None = None
    confidence: float = 1.0

    @property
    def sources(self) -> set[Source]:
        return {source for source, _ in self.members}

    @property
    def duplicates(self) -> list[Source]:
        """Sources with more than one edition in the group: likely duplicate records."""
        counts = defaultdict(int)
        for source, _ in self.members:
            counts[source] += 1
        return sorted(s for s, n in counts.items() if n > 1)

    @property
    def duplicate_reasons(self) -> dict[Source, list[str]]:
        """For each duplicated source, the identifier kinds its records share.

        Empty when the records were only linked through other sources' editions.
        """
        reasons = {}
        confirmed = set().union(*(confirmed_asins(e) for _, e in self.members))
        for source in self.duplicates:
            seen: dict[tuple[str, str], int] = defaultdict(int)
            for s, edition in self.members:
                if s == source:
                    for key in _shared_keys(edition, confirmed):
                        seen[key] += 1
            reasons[source] = sorted({kind for (kind, _), n in seen.items() if n > 1}, key=DUPLICATE_KEYS.index)
        return reasons


def align(works: dict[Source, Work]) -> list[EditionGroup]:
    editions = [(source, e) for source, work in works.items() for e in work.editions]
    groups = _by_identifier(editions)
    return _fuzzy_pairs(_narrated_groups(groups))


def _by_identifier(editions: list[tuple[Source, Edition]]) -> list[EditionGroup]:
    parent = list(range(len(editions)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    reasons: dict[int, str] = {}
    owner: dict[tuple[str, str], int] = {}
    for i, (source, edition) in enumerate(editions):
        for key, value in _keys(source, edition):
            if (key, value) in owner:
                first = editions[owner[(key, value)]][1]
                reason = key
                if key == "asin":
                    # One ASIN is one product, so a clashing format means someone cited it wrongly.
                    if not _formats_agree(edition, first):
                        continue
                    if value in confirmed_asins(edition) | confirmed_asins(first):
                        reason = "store_asin"
                a, b = root(owner[(key, value)]), root(i)
                if a != b:
                    parent[b] = a
                    # ISBN outranks a store's ASIN, then a catalogue's ASIN, then a cross-source id.
                    reasons[a] = min(reasons.get(a, reason), reasons.pop(b, reason), reason, key=KEYS.index)
            else:
                owner[(key, value)] = i

    members = defaultdict(list)
    for i, pair in enumerate(editions):
        members[root(i)].append(pair)
    return [EditionGroup(m, reasons.get(r), WEAK_ASIN_CONFIDENCE if reasons.get(r) == "asin" else 1.0)
            for r, m in members.items()]


def _value(candidates: list):
    return candidates[0].value if candidates else None


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _fold(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().replace(".", " ").split())


def narrators(edition: Edition) -> frozenset[str]:
    people = _value(edition.contributors) or []
    return frozenset(_fold(p.name) for p in people if p.role == "narrator" and p.name)


# Release dates a few days apart are the same audiobook launch listed by different catalogues.
NARRATED_DAYS = 3


def _days_apart(a: str, b: str) -> int | None:
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days)
    except ValueError:
        return None


def pair_score(a: Edition, b: Edition) -> int | None:
    """None if any signal disagrees; otherwise how many optional signals agree."""
    for name in ("format", "language"):
        if not _value(getattr(a, name)) or _value(getattr(a, name)) != _value(getattr(b, name)):
            return None
    year_a, year_b = _value(a.release_date), _value(b.release_date)
    if not year_a or not year_b or year_a[:4] != year_b[:4]:
        return None

    score = 0
    # An audiobook's narrators and launch date identify it even when catalogues title it differently
    # (a translated title against the original); different narrators are a different recording.
    voices_a, voices_b = narrators(a), narrators(b)
    if _value(a.format) == "audiobook" and voices_a and voices_b:
        if voices_a != voices_b:
            return None
        days = _days_apart(year_a, year_b)
        if len(year_a) >= 10 and len(year_b) >= 10 and (days is None or days > NARRATED_DAYS):
            return None
        score += 2
    else:
        title_a, title_b = _value(a.title), _value(b.title)
        if title_a and title_b and _similar(title_a, title_b) < 0.6:
            return None

    pages_a, pages_b = _value(a.pages), _value(b.pages)
    if pages_a and pages_b:
        if abs(pages_a - pages_b) > max(2, 0.02 * max(pages_a, pages_b)):
            return None
        score += 1
    pub_a, pub_b = _value(a.publisher), _value(b.publisher)
    if pub_a and pub_b:
        similarity = _similar(pub_a, pub_b)
        if similarity < 0.5:
            return None
        score += similarity >= 0.8
    return score if score else None


def _narrated_groups(groups: list[EditionGroup]) -> list[EditionGroup]:
    """Joins lone audiobooks, one per source, that share language, narrators and launch date."""
    lone = [g for g in groups if len(g.members) == 1 and _value(g.members[0][1].format) == "audiobook"]
    buckets = defaultdict(list)
    for g in lone:
        e = g.members[0][1]
        if (voices := narrators(e)) and _value(e.language) and _value(e.release_date):
            buckets[(_value(e.language), voices)].append(g)

    joined = set()
    merged = []
    for bucket in buckets.values():
        sources = [g.members[0][0] for g in bucket]
        dates = [_value(g.members[0][1].release_date) for g in bucket]
        # Two records from one source would be ambiguous, so the bucket is left to pairwise matching.
        if len(bucket) < 3 or len(set(sources)) != len(sources):
            continue
        if any((_days_apart(a, b) or 0) > NARRATED_DAYS or (_days_apart(a, b) is None and a[:4] != b[:4])
               for a in dates for b in dates):
            continue
        joined |= {id(g) for g in bucket}
        merged.append(EditionGroup([m for g in bucket for m in g.members], "fuzzy", 1.0))
    return [g for g in groups if id(g) not in joined] + merged


def _fuzzy_pairs(groups: list[EditionGroup]) -> list[EditionGroup]:
    lone = [g for g in groups if len(g.members) == 1]
    # Format, language and year must agree anyway, so only compare within those buckets.
    buckets = defaultdict(list)
    for i, g in enumerate(lone):
        e = g.members[0][1]
        buckets[(_value(e.format), _value(e.language), (_value(e.release_date) or "")[:4])].append(i)

    best: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for bucket in buckets.values():
        for i in bucket:
            for j in bucket:
                source_a, edition_a = lone[i].members[0]
                source_b, edition_b = lone[j].members[0]
                if source_a != source_b and (score := pair_score(edition_a, edition_b)) is not None:
                    best[i].append((score, j))

    def clear_best(i: int) -> tuple[int, int] | None:
        ranked = sorted(best[i], reverse=True)
        if not ranked or (len(ranked) > 1 and ranked[1][0] == ranked[0][0]):
            return None
        return ranked[0]

    used, merged = set(), []
    for i in range(len(lone)):
        if i in used or not (pick := clear_best(i)):
            continue
        score, j = pick
        back = clear_best(j)
        if j in used or not back or back[1] != i:
            continue
        used |= {i, j}
        merged.append(EditionGroup(lone[i].members + lone[j].members, "fuzzy", min(1.0, round(0.5 + 0.25 * score, 2))))

    kept = [g for g in groups if len(g.members) > 1] + [g for k, g in enumerate(lone) if k not in used]
    return kept + merged
