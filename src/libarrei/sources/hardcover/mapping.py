"""Translates Hardcover GraphQL book results into Libarrei's Work/Edition model.

Field names follow the BookSearch query in client.py.
"""

from libarrei.model import Contributor, Edition, SeriesEntry, Source, Work
from libarrei.sources.formats import detail, normalise_format

# Hardcover's reading_formats table: 1 Read, 2 Listened, 3 Both, 4 Ebook.
# "Both" says nothing about the edition itself, so it maps to no format.
READING_FORMATS = {1: "physical", 2: "audiobook", 4: "ebook"}

HC = Source.HARDCOVER


def contributors(cached: list[dict] | None) -> list[Contributor]:
    return [
        Contributor(
            name=c["author"]["name"],
            role=(c.get("contribution") or "Author").lower(),
            ids={HC: str(c["author"]["id"])},
        )
        for c in cached or []
        if c.get("author", {}).get("name")
    ]


def genres(cached_tags: dict | None) -> list[str]:
    return [t["tag"] for t in (cached_tags or {}).get("Genre", [])]


def series(featured: dict | None, every: list[dict] | None = None) -> list[SeriesEntry]:
    """Every series the book is in, the featured one first."""
    entries: list[SeriesEntry] = []
    for link in [featured or {}, *(every or [])]:
        name = (link.get("series") or {}).get("name")
        position = link.get("position")
        entry = SeriesEntry(name=name, position=None if position is None else f"{position:g}") if name else None
        if entry and entry not in entries:
            entries.append(entry)
    return entries


def to_edition(raw: dict) -> Edition:
    edition = Edition()
    sid = str(raw["id"])
    edition.add("title", raw.get("title"), HC, sid)
    edition.add("subtitle", raw.get("subtitle"), HC, sid)
    edition.add("edition_statement", raw.get("edition_information"), HC, sid)
    edition.add("contributors", contributors(raw.get("cached_contributors")), HC, sid)
    edition.add("isbn13", raw.get("isbn_13"), HC, sid)
    edition.add("isbn10", raw.get("isbn_10"), HC, sid)
    edition.add("asin", raw.get("asin"), HC, sid)
    edition.add("publisher", (raw.get("publisher") or {}).get("name"), HC, sid)
    edition.add("release_date", raw.get("release_date"), HC, sid)
    edition.add("pages", raw.get("pages"), HC, sid)
    # The reading format is curated; the free-text edition format only fills in when it is missing.
    coarse = READING_FORMATS.get(raw.get("reading_format_id")) or normalise_format(raw.get("edition_format"))
    edition.add("format", coarse, HC, sid)
    edition.add("format_detail", detail(raw.get("edition_format")), HC, sid)
    edition.add("duration_seconds", raw.get("audio_seconds") or None, HC, sid)
    edition.add("language", (raw.get("language") or {}).get("code2"), HC, sid)
    edition.add("cover_url", (raw.get("image") or {}).get("url"), HC, sid)
    return edition


def to_work(raw: dict) -> Work:
    work = Work()
    sid = str(raw["id"])
    work.add("title", raw.get("title"), HC, sid)
    work.add("subtitle", raw.get("subtitle"), HC, sid)
    work.add("contributors", contributors(raw.get("cached_contributors")), HC, sid)
    work.add("description", raw.get("description"), HC, sid)
    work.add("series", series(raw.get("featured_book_series"), raw.get("book_series")), HC, sid)
    work.add("genres", genres(raw.get("cached_tags")), HC, sid)
    work.add("original_release_date", raw.get("release_date"), HC, sid)
    work.editions = [to_edition(e) for e in raw.get("editions") or []]
    return work
