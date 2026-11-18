"""Aligns editions across sources so each group is one real-world edition.

Shared identifiers decide most groups. Editions without one are paired only when
every available signal agrees and the pair is each other's clear best match:
in a correction tool a wrong merge spreads one edition's data onto another,
while a missed match merely shows up as "missing from source X".
"""

from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from libarrei.model import Edition, Source, Work

KEYS = ("isbn13", "asin")


@dataclass
class EditionGroup:
    members: list[tuple[Source, Edition]] = field(default_factory=list)
    # How the group was formed: "isbn13", "asin", "fuzzy", or None for a lone edition.
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


def align(works: dict[Source, Work]) -> list[EditionGroup]:
    editions = [(source, e) for source, work in works.items() for e in work.editions]
    groups = _by_identifier(editions)
    return _fuzzy_pairs(groups)


def _by_identifier(editions: list[tuple[Source, Edition]]) -> list[EditionGroup]:
    parent = list(range(len(editions)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    reasons: dict[int, str] = {}
    owner: dict[tuple[str, str], int] = {}
    for i, (_, edition) in enumerate(editions):
        for key in KEYS:
            for c in getattr(edition, key):
                if (key, c.value) in owner:
                    a, b = root(owner[(key, c.value)]), root(i)
                    if a != b:
                        parent[b] = a
                        # ISBN outranks ASIN as the reason when both linked the group.
                        reasons[a] = min(reasons.get(a, key), reasons.pop(b, key), key, key=KEYS.index)
                else:
                    owner[(key, c.value)] = i

    members = defaultdict(list)
    for i, pair in enumerate(editions):
        members[root(i)].append(pair)
    return [EditionGroup(m, reasons.get(r)) for r, m in members.items()]


def _value(candidates: list):
    return candidates[0].value if candidates else None


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def pair_score(a: Edition, b: Edition) -> int | None:
    """None if any signal disagrees; otherwise how many optional signals agree."""
    for name in ("format", "language"):
        if not _value(getattr(a, name)) or _value(getattr(a, name)) != _value(getattr(b, name)):
            return None
    year_a, year_b = _value(a.release_date), _value(b.release_date)
    if not year_a or not year_b or year_a[:4] != year_b[:4]:
        return None
    title_a, title_b = _value(a.title), _value(b.title)
    if title_a and title_b and _similar(title_a, title_b) < 0.6:
        return None

    score = 0
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
        merged.append(EditionGroup(lone[i].members + lone[j].members, "fuzzy", round(0.5 + 0.25 * score, 2)))

    kept = [g for g in groups if len(g.members) > 1] + [g for k, g in enumerate(lone) if k not in used]
    return kept + merged
