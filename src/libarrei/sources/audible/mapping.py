"""Translates Audible catalogue products into Libarrei's model.

Audible has no notion of a work, so each product becomes one audiobook edition
and the best-matching product also supplies the work-level fields.
Descriptions stay as Audible's HTML; the merger parses them like Goodreads'.
"""

from libarrei.model import Contributor, Edition, SeriesEntry, Source, Work

AU = Source.AUDIBLE
FORMAT_DETAILS = {"unabridged": "Unabridged audiobook", "abridged": "Abridged audiobook"}


def authors(product: dict) -> list[Contributor]:
    return [Contributor(name=a["name"], ids={AU: a["asin"]} if a.get("asin") else {})
            for a in product.get("authors") or [] if a.get("name")]


def narrators(product: dict) -> list[Contributor]:
    return [Contributor(name=n["name"], role="narrator") for n in product.get("narrators") or [] if n.get("name")]


def series(product: dict) -> list[SeriesEntry]:
    return [SeriesEntry(name=s["title"], position=s.get("sequence") or None)
            for s in product.get("series") or [] if s.get("title")]


def description(product: dict) -> str | None:
    # The merchandising summary is a shortened plain-text teaser, so only a fallback.
    return product.get("publisher_summary") or product.get("merchandising_summary")


def duration(product: dict) -> int | None:
    minutes = product.get("runtime_length_min")
    return minutes * 60 if minutes else None


def to_edition(product: dict, region: str) -> Edition:
    edition = Edition()
    sid = product["asin"]
    edition.add("title", product.get("title"), AU, sid)
    edition.add("subtitle", product.get("subtitle"), AU, sid)
    edition.add("contributors", authors(product) + narrators(product), AU, sid)
    edition.add("asin", sid, AU, sid)
    edition.add("publisher", product.get("publisher_name"), AU, sid)
    edition.add("release_date", product.get("release_date") or product.get("issue_date"), AU, sid)
    edition.add("format", "audiobook", AU, sid)
    edition.add("format_detail", FORMAT_DETAILS.get((product.get("format_type") or "").lower()), AU, sid)
    edition.add("duration_seconds", duration(product), AU, sid)
    edition.add("language", product.get("language"), AU, sid)
    edition.add("cover_url", (product.get("product_images") or {}).get("1000"), AU, sid)
    edition.add("series", series(product), AU, sid)
    # Audible pages differ per store, so the record keeps which store it came from.
    edition.slugs[AU] = region
    return edition


def to_work(products: list[dict], region: str) -> Work:
    """The first product is the best match and speaks for the work."""
    work = Work()
    first = products[0]
    sid = first["asin"]
    work.add("title", first.get("title"), AU, sid)
    work.add("subtitle", first.get("subtitle"), AU, sid)
    work.add("contributors", authors(first), AU, sid)
    work.add("series", series(first), AU, sid)
    work.add("description", description(first), AU, sid)
    work.slugs[AU] = region
    work.editions = [to_edition(p, region) for p in products]
    return work
