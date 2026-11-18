"""Translates Open Library work and edition documents into Libarrei's model.

Open Library stores authors as keys, so callers pass a key -> name lookup
(see OpenLibrary.author_names) to keep these functions free of network calls.
Field reference: https://openlibrary.org/dev/docs/api/books
"""

import re

from libarrei.model import Contributor, Edition, SeriesEntry, Source, Work
from libarrei.sources.formats import normalise_format

OL = Source.OPENLIBRARY
COVER_URL = "https://covers.openlibrary.org/b/id/{}-L.jpg"


def text(value: str | dict | None) -> str | None:
    """Descriptions are either a plain string or {"type": "/type/text", "value": ...}."""
    if isinstance(value, dict):
        return value.get("value")
    return value


def short_key(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def author_keys(doc: dict) -> list[str]:
    # Editions list {"key": ...}; works nest it as {"author": {"key": ...}}.
    return [(a.get("author") or a)["key"] for a in doc.get("authors") or []]


def contributors(doc: dict, names: dict[str, str]) -> list[Contributor]:
    return [
        Contributor(name=names[key], ids={OL: short_key(key)})
        for key in author_keys(doc)
        if key in names
    ]


# "Rob Inglis (Narrator)"; catalogue headings such as "Lee, Alan, 1947-" carry no role and are skipped.
CONTRIBUTION = re.compile(r"^(.+?)\s*\(([^()]+)\)\s*$")


def other_contributors(doc: dict) -> list[Contributor]:
    """Editions' non-author credits: structured `contributors`, else role-tagged `contributions`."""
    people = [
        Contributor(name=c["name"].strip(), role=c["role"].strip().lower())
        for c in doc.get("contributors") or []
        if (c.get("name") or "").strip() and (c.get("role") or "").strip()
    ]
    if people:
        # The two fields usually repeat each other, so the structured one wins.
        return people
    for raw in doc.get("contributions") or []:
        if (m := CONTRIBUTION.match(raw.strip())) and m.group(1).lower() != "author":
            people.append(Contributor(name=m.group(1), role=m.group(2).strip().lower()))
    return people


# "Name ; 3", "Name, #3", "Name #3" or "Name, 3"; anything else is kept whole as the name.
SERIES_POSITION = re.compile(r"^(.+?)\s*(?:;|,\s*#?|#)\s*(\d+(?:\.\d+)?)\s*$")


def series(doc: dict) -> list[SeriesEntry]:
    # Entries shaped {"series": {"key": ...}} carry no name, only a key, so are skipped.
    entries = []
    for raw in doc.get("series") or []:
        if not isinstance(raw, str) or not raw.strip():
            continue
        text = raw.strip()
        if m := SERIES_POSITION.match(text):
            entries.append(SeriesEntry(name=m.group(1).strip(), position=m.group(2)))
        else:
            entries.append(SeriesEntry(name=text))
    return entries


def pages(doc: dict) -> int | None:
    if doc.get("number_of_pages"):
        return doc["number_of_pages"]
    match = re.search(r"\d+", doc.get("pagination") or "")
    return int(match.group()) if match else None


def cover(doc: dict) -> str | None:
    # -1 is Open Library's placeholder for a deleted cover.
    ids = [c for c in doc.get("covers") or [] if c > 0]
    return COVER_URL.format(ids[0]) if ids else None


def to_edition(doc: dict, names: dict[str, str]) -> Edition:
    edition = Edition()
    sid = short_key(doc["key"])
    edition.add("title", doc.get("title"), OL, sid)
    edition.add("subtitle", doc.get("subtitle"), OL, sid)
    edition.add("edition_statement", doc.get("edition_name"), OL, sid)
    edition.add("contributors", contributors(doc, names) + other_contributors(doc), OL, sid)
    for isbn in doc.get("isbn_13") or []:
        edition.add("isbn13", isbn, OL, sid)
    for isbn in doc.get("isbn_10") or []:
        edition.add("isbn10", isbn, OL, sid)
    for publisher in doc.get("publishers") or []:
        edition.add("publisher", publisher, OL, sid)
    edition.add("release_date", doc.get("publish_date"), OL, sid)
    edition.add("pages", pages(doc), OL, sid)
    edition.add("format", normalise_format(doc.get("physical_format")), OL, sid)
    for language in doc.get("languages") or []:
        edition.add("language", short_key(language["key"]), OL, sid)
    edition.add("cover_url", cover(doc), OL, sid)
    edition.add("series", series(doc), OL, sid)
    return edition


def to_work(work: dict, editions: list[dict], names: dict[str, str]) -> Work:
    result = Work()
    sid = short_key(work["key"])
    result.add("title", work.get("title"), OL, sid)
    result.add("subtitle", work.get("subtitle"), OL, sid)
    result.add("contributors", contributors(work, names), OL, sid)
    result.add("description", text(work.get("description")), OL, sid)
    result.add("series", series(work), OL, sid)
    result.add("genres", work.get("subjects"), OL, sid)
    result.add("original_release_date", work.get("first_publish_date"), OL, sid)
    result.editions = [to_edition(e, names) for e in editions]
    return result
