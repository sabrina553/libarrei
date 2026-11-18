"""Finds a book in every configured source and returns one Work per source.

Matching across sources is not attempted here: each source's best guess is
returned side by side so the results can be compared.
"""

import os
from dataclasses import dataclass, field

from libarrei.model import Source, Work
from libarrei.sources.goodreads.client import Goodreads
from libarrei.sources.goodreads.mapping import work_from_graphql
from libarrei.sources.goodreads.scraper import parse_id
from libarrei.sources.goodreads.transport import TransportLayer as GoodreadsTransport
from libarrei.sources.hardcover.client import Hardcover
from libarrei.sources.hardcover.mapping import to_work as hardcover_work
from libarrei.sources.hardcover.transport import TransportLayer as HardcoverTransport
from libarrei.sources.openlibrary.client import OpenLibrary
from libarrei.sources.openlibrary.mapping import author_keys
from libarrei.sources.openlibrary.mapping import to_work as openlibrary_work


@dataclass
class LookupResult:
    works: dict[Source, Work] = field(default_factory=dict)
    # Why a source returned nothing: missing token, not found, or an error.
    notes: dict[Source, str] = field(default_factory=dict)


def from_openlibrary(isbn: str | None, title: str | None, author: str | None) -> tuple[Work | None, list[str]]:
    """Also returns ISBNs found, so title searches can be passed on to Hardcover."""
    ol = OpenLibrary()
    editions, isbns = [], [isbn] if isbn else []
    if isbn:
        edition = ol.edition_by_isbn(isbn)
        if not edition or not edition.get("works"):
            return None, isbns
        editions, work_key = [edition], edition["works"][0]["key"]
    else:
        docs = ol.search(title or "", author, limit=1)
        if not docs:
            return None, isbns
        work_key, isbns = docs[0]["key"], docs[0].get("isbn", [])
    work = ol.document(work_key)
    if not work:
        return None, isbns
    names = ol.author_names(list(dict.fromkeys(author_keys(work) + [k for e in editions for k in author_keys(e)])))
    return openlibrary_work(work, editions, names), isbns


def from_hardcover(token: str, isbns: list[str]) -> Work | None:
    books = Hardcover(HardcoverTransport(token)).search({"isbn": isbns, "hcid": []})["books"]
    return hardcover_work(books[0]) if books else None


def from_goodreads(token: str, query: str) -> Work | None:
    client = Goodreads(GoodreadsTransport(token))
    edges = client.search({"query": query})["getSearchSuggestions"]["edges"]
    urls = [e["node"]["webUrl"] for e in edges if e.get("node", {}).get("webUrl")]
    legacy_id = parse_id(urls[0]) if urls else None
    if not legacy_id:
        return None
    book = client.legacy_id({"legacyId": int(legacy_id)})["getBookByLegacyId"]
    return work_from_graphql(book) if book else None


def lookup(isbn: str | None = None, title: str | None = None, author: str | None = None) -> LookupResult:
    result = LookupResult()

    def attempt(source: Source, fetch) -> None:
        try:
            work = fetch()
        except Exception as error:  # one failing source must not hide the others
            result.notes[source] = f"error: {error}"
            return
        if work:
            result.works[source] = work
        else:
            result.notes.setdefault(source, "not found")

    isbns: list[str] = []

    def openlibrary() -> Work | None:
        work, found = from_openlibrary(isbn, title, author)
        isbns.extend(found)
        return work

    attempt(Source.OPENLIBRARY, openlibrary)

    if token := os.getenv("HARDCOVER_TOKEN"):
        if isbns:
            attempt(Source.HARDCOVER, lambda: from_hardcover(token, isbns))
        else:
            result.notes[Source.HARDCOVER] = "no ISBN to search with"
    else:
        result.notes[Source.HARDCOVER] = "HARDCOVER_TOKEN not set"

    if token := os.getenv("GOODREADS_TOKEN"):
        query = isbn or " ".join(filter(None, [title, author]))
        attempt(Source.GOODREADS, lambda: from_goodreads(token, query))
    else:
        result.notes[Source.GOODREADS] = "GOODREADS_TOKEN not set"

    return result
