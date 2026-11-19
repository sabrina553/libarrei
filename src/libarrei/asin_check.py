"""Checks catalogue ASINs that differ from the store's own ASIN for the same edition.

A store's ASIN is authoritative for its own listing, but a catalogue may cite
another one that is still valid: a regional or older listing of the same
product. Looking it up on the store tells that apart from a typo or a
different product.
"""

from collections.abc import Callable
from enum import StrEnum

from libarrei.merge import MergedEdition, text_key
from libarrei.model import Source
from libarrei.normalise import strip_language_label

STORES = (Source.AUDIBLE, Source.AMAZON)
# Each check may cost a store request, so a work with many editions is capped.
MAX_CHECKS = 10


class AsinStatus(StrEnum):
    SAME_PRODUCT = "same_product"
    OTHER_PRODUCT = "other_product"
    NOT_FOUND = "not_found"


class Unavailable(Exception):
    """The store could not be asked (no cookie, or blocked), so nothing can be said."""


# (store, asin) -> {"title": ..., "authors": [...]}, None when the store has no such product.
# Amazon adds "found_on" (the store domain that had it), or answers {"missing_from": [domains]} when none did.
Probe = Callable[[Source, str], dict | None]


def same_product(a: dict, b: dict) -> bool:
    """Same title (one may carry a subtitle the other lacks) and a shared author word."""
    ta, tb = (text_key(strip_language_label(p.get("title") or "") or "") for p in (a, b))
    if not ta or not tb or not (ta.startswith(tb) or tb.startswith(ta)):
        return False
    words = [{w for name in p.get("authors") or [] for w in name.casefold().replace(".", " ").split()} for p in (a, b)]
    return not words[0] or not words[1] or bool(words[0] & words[1])


def _found(product: dict | None) -> dict | None:
    return None if product is None or "missing_from" in product else product


def check_edition(edition: MergedEdition, probe: Probe, budget: list[int] | None = None) -> dict[str, AsinStatus]:
    resolved = edition.fields.get("asin")
    if not resolved:
        return {}
    store_asins = {s: [v.value for v in resolved.values if v.source == s] for s in STORES}
    known = {a for asins in store_asins.values() for a in asins}
    others = {v.value for v in resolved.values if v.source not in STORES and v.value not in known}
    store = next((s for s in STORES if store_asins[s]), None)
    if not store or not others:
        return {}
    checks = {}
    try:
        reference = _found(probe(store, store_asins[store][0])) or _edition_summary(edition)
        for asin in sorted(others):
            if budget is not None:
                if budget[0] <= 0:
                    break
                budget[0] -= 1
            answer = probe(store, asin)
            if answer and (stores := answer.get("missing_from") or [answer.get("found_on")]) and all(stores):
                edition.asin_stores[asin] = stores
            found = _found(answer)
            if found is None:
                checks[asin] = AsinStatus.NOT_FOUND
            else:
                checks[asin] = AsinStatus.SAME_PRODUCT if same_product(found, reference) else AsinStatus.OTHER_PRODUCT
    except Unavailable:
        pass
    return checks


def _edition_summary(edition: MergedEdition) -> dict:
    title = edition.fields.get("title")
    people = edition.fields.get("contributors")
    return {"title": title.value if title else "",
            "authors": [c.name for c in people.value if c.role == "author"] if people else []}


def check_all(editions: list[MergedEdition], probe: Probe) -> None:
    """Fills in each edition's asin_checks, within the request budget."""
    budget = [MAX_CHECKS]
    for edition in editions:
        edition.asin_checks = check_edition(edition, probe, budget)
