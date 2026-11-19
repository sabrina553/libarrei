"""Translates scraped Amazon product details into Libarrei's model.

Amazon has no notion of a work, so each product page becomes one edition and
the best-matching one also supplies the work-level fields.
Descriptions stay as Amazon's HTML; the merger parses them like Goodreads'.
"""

from libarrei.model import Contributor, Edition, SeriesEntry, Source, Work
from libarrei.normalise import is_series_note, strip_language_label
from libarrei.sources.formats import detail, normalise_format
from libarrei.sources.goodreads.titles import split_title

AZ = Source.AMAZON


def contributors(product: dict) -> list[Contributor]:
    return [Contributor(name=name, role=role.lower()) for name, role in product.get("authors") or []]


def series(product: dict) -> list[SeriesEntry]:
    if not product.get("series"):
        return []
    name, position = product["series"]
    return [SeriesEntry(name=strip_language_label(name), position=position)]


def title_and_subtitle(product: dict) -> tuple[str | None, str | None]:
    """Kindle titles often end in a series note ("Title: Series Book 1"), which is not a subtitle."""
    title, subtitle = split_title(strip_language_label(product.get("title")))
    if subtitle and product.get("series") and is_series_note(subtitle, [product["series"][0]]):
        subtitle = None
    return title, subtitle


def to_edition(asin: str, product: dict, domain: str) -> Edition:
    edition = Edition()
    title, subtitle = title_and_subtitle(product)
    edition.add("title", title, AZ, asin)
    edition.add("subtitle", subtitle, AZ, asin)
    edition.add("contributors", contributors(product), AZ, asin)
    edition.add("isbn13", product.get("isbn13"), AZ, asin)
    edition.add("isbn10", product.get("isbn10"), AZ, asin)
    edition.add("asin", asin, AZ, asin)
    edition.add("publisher", product.get("publisher"), AZ, asin)
    edition.add("release_date", product.get("publication_date"), AZ, asin)
    edition.add("pages", product.get("pages"), AZ, asin)
    edition.add("format", normalise_format(product.get("format")), AZ, asin)
    edition.add("format_detail", detail(product.get("format")), AZ, asin)
    edition.add("language", product.get("language"), AZ, asin)
    edition.add("cover_url", product.get("cover_url"), AZ, asin)
    edition.add("series", series(product), AZ, asin)
    # Amazon pages differ per store, so the record keeps which store it came from.
    edition.slugs[AZ] = domain
    return edition


def to_work(products: list[tuple[str, dict]], domain: str) -> Work:
    """The first (asin, product) pair is the best match and speaks for the work."""
    work = Work()
    asin, first = products[0]
    title, subtitle = title_and_subtitle(first)
    work.add("title", title, AZ, asin)
    work.add("subtitle", subtitle, AZ, asin)
    work.add("contributors", [c for c in contributors(first) if c.role == "author"], AZ, asin)
    work.add("series", series(first), AZ, asin)
    work.add("description", first.get("description"), AZ, asin)
    work.slugs[AZ] = domain
    work.editions = [to_edition(a, p, domain) for a, p in products]
    return work
