"""Translates Goodreads data into Libarrei's Work/Edition model.

Two inputs: the GraphQL getBookByLegacyId result (one edition plus its work,
see client.py) and the per-edition dicts produced by scraper.py.
Goodreads' public IDs are the numeric "legacyId"s, so those are used as
source IDs rather than the internal kca:// IDs.
"""

from datetime import UTC, datetime

from libarrei.model import Contributor, Edition, SeriesEntry, Source, Work
from libarrei.sources.formats import detail, normalise_format
from libarrei.sources.goodreads.titles import split_title

GR = Source.GOODREADS


def date_from_millis(millis: float | None) -> str | None:
    if millis is None:
        return None
    return datetime.fromtimestamp(millis / 1000, UTC).date().isoformat()


def contributor(node: dict, role: str) -> Contributor:
    return Contributor(name=node["name"], role=role, ids={GR: str(node["legacyId"])})


def contributors(book: dict) -> list[Contributor]:
    people = []
    edge = book.get("primaryContributorEdge") or {}
    if primary := edge.get("node"):
        people.append(contributor(primary, (edge.get("role") or "author").lower()))
    for edge in book.get("secondaryContributorEdges") or []:
        people.append(contributor(edge["node"], (edge.get("role") or "contributor").lower()))
    return people


def series(book: dict) -> list[SeriesEntry]:
    return [
        SeriesEntry(name=s["series"]["title"], position=s.get("userPosition") or None)
        for s in book.get("bookSeries") or []
        if (s.get("series") or {}).get("title")
    ]


def edition_from_graphql(book: dict) -> Edition:
    details = book.get("details") or {}
    edition = Edition()
    sid = str(book["legacyId"])
    title, subtitle = split_title(book.get("title"))
    edition.add("title", title, GR, sid)
    edition.add("subtitle", subtitle, GR, sid)
    edition.add("contributors", contributors(book), GR, sid)
    edition.add("isbn13", details.get("isbn13"), GR, sid)
    edition.add("isbn10", details.get("isbn"), GR, sid)
    edition.add("asin", details.get("asin"), GR, sid)
    edition.add("publisher", details.get("publisher"), GR, sid)
    edition.add("release_date", date_from_millis(details.get("publicationTime")), GR, sid)
    edition.add("pages", details.get("numPages"), GR, sid)
    edition.add("format", normalise_format(details.get("format")), GR, sid)
    edition.add("format_detail", detail(details.get("format")), GR, sid)
    edition.add("language", (details.get("language") or {}).get("name"), GR, sid)
    edition.add("cover_url", book.get("imageUrl"), GR, sid)
    return edition


def work_from_graphql(book: dict) -> Work:
    raw_work = book.get("work") or {}
    work_details = raw_work.get("details") or {}
    work = Work()
    sid = str(raw_work.get("legacyId") or book["legacyId"])
    title, subtitle = split_title(work_details.get("originalTitle") or book.get("title"))
    work.add("title", title, GR, sid)
    work.add("subtitle", subtitle, GR, sid)
    work.add("contributors", contributors(book), GR, sid)
    work.add("description", book.get("description"), GR, sid)
    work.add("series", series(book), GR, sid)
    work.add("genres", [g["genre"]["name"] for g in book.get("bookGenres") or []], GR, sid)
    work.add("original_release_date", date_from_millis(work_details.get("publicationTime")), GR, sid)
    work.editions = [edition_from_graphql(book)]
    return work


def edition_from_scrape(scraped: dict) -> Edition:
    edition = Edition()
    sid = scraped.get("goodreads_id") or ""
    edition.add("title", scraped.get("title"), GR, sid)
    edition.add("subtitle", scraped.get("subtitle"), GR, sid)
    edition.add("contributors", [Contributor(name=n) for n in scraped.get("authors") or []], GR, sid)
    edition.add("isbn13", scraped.get("isbn13"), GR, sid)
    edition.add("isbn10", scraped.get("isbn10"), GR, sid)
    edition.add("asin", scraped.get("asin"), GR, sid)
    edition.add("publisher", scraped.get("publisher"), GR, sid)
    edition.add("release_date", scraped.get("publish_date"), GR, sid)
    edition.add("pages", scraped.get("pages"), GR, sid)
    edition.add("format", normalise_format(scraped.get("book_type")), GR, sid)
    edition.add("format_detail", detail(scraped.get("book_type")), GR, sid)
    edition.add("language", scraped.get("language"), GR, sid)
    return edition


def edition_from_editions_page(scraped: dict) -> Edition:
    """An edition from the /work/editions listing: the scrape fields plus the cover."""
    edition = edition_from_scrape(scraped)
    edition.add("cover_url", scraped.get("cover_url"), GR, scraped.get("goodreads_id") or "")
    return edition
