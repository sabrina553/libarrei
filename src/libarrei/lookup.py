"""Finds a book in every configured source and returns one Work per source.

Matching across sources is not attempted here: each source's best guess is
returned side by side so the results can be compared.
"""

import os
from dataclasses import dataclass, field

from libarrei.cache import Cache, NoCache
from libarrei.model import Source, Work
from libarrei.ratelimit import INTERVALS, RateLimiter
from libarrei.sources.goodreads.client import Goodreads
from libarrei.sources.goodreads.mapping import edition_from_editions_page, work_from_graphql
from libarrei.sources.goodreads.scraper import fetch_editions, parse_id
from libarrei.sources.goodreads.transport import TransportLayer as GoodreadsTransport
from libarrei.sources.hardcover.client import Hardcover
from libarrei.sources.hardcover.mapping import to_edition as hardcover_edition
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


def from_openlibrary(cache, isbn: str | None, title: str | None, author: str | None) -> Work | None:
    ol = OpenLibrary(cache=cache)
    editions = []
    if isbn:
        edition = ol.edition_by_isbn(isbn)
        if not edition or not edition.get("works"):
            return None
        editions, work_key = [edition], edition["works"][0]["key"]
    else:
        docs = ol.search(title or "", author, limit=1)
        if not docs:
            return None
        work_key = docs[0]["key"]
    work = ol.document(work_key)
    if not work:
        return None
    # The ISBN's own edition stays first so it remains the best match.
    seen = {e["key"] for e in editions}
    editions += [e for e in ol.all_editions(work_key) if e["key"] not in seen]
    # Only the work's authors: edition-level keys across hundreds of editions
    # would cost one request each on a cold cache.
    names = ol.author_names(author_keys(work))
    return openlibrary_work(work, editions, names)


def from_hardcover(cache, token: str, isbn: str | None, title: str | None, author: str | None) -> Work | None:
    client = Hardcover(HardcoverTransport(token, cache=cache))
    if isbn:
        books = client.search({"isbn": [isbn], "hcid": []})["books"]
    else:
        ids = client.search_titles(title or "", author, limit=1)
        books = client.search({"isbn": [], "hcid": ids})["books"] if ids else []
    if not books:
        return None
    work = hardcover_work(books[0])
    # The searched edition stays first so it remains the best match.
    seen = {e.ids[Source.HARDCOVER] for e in work.editions}
    work.editions += [
        hardcover_edition(e) for e in client.all_editions(books[0]["id"]) if str(e["id"]) not in seen
    ]
    return work


def from_goodreads(cache, token: str, query: str) -> Work | None:
    client = Goodreads(GoodreadsTransport(token))
    edges = client.search({"query": query})["getSearchSuggestions"]["edges"]
    urls = [e["node"]["webUrl"] for e in edges if e.get("node", {}).get("webUrl")]
    legacy_id = parse_id(urls[0]) if urls else None
    if not legacy_id:
        return None
    book = client.legacy_id({"legacyId": int(legacy_id)})["getBookByLegacyId"]
    if not book:
        return None
    work = work_from_graphql(book)
    if work_id := work.ids.get(Source.GOODREADS):
        limiter = RateLimiter(INTERVALS["goodreads"])
        seen = {e.ids.get(Source.GOODREADS) for e in work.editions}
        scraped = [edition_from_editions_page(e) for e in fetch_editions(work_id, cache, limiter)]
        work.editions += [e for e in scraped if e.ids.get(Source.GOODREADS) not in seen]
    return work


def lookup(
    isbn: str | None = None, title: str | None = None, author: str | None = None, use_cache: bool = True
) -> LookupResult:
    result = LookupResult()
    cache = Cache() if use_cache else NoCache()

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

    attempt(Source.OPENLIBRARY, lambda: from_openlibrary(cache, isbn, title, author))

    if token := os.getenv("HARDCOVER_TOKEN"):
        attempt(Source.HARDCOVER, lambda: from_hardcover(cache, token, isbn, title, author))
    else:
        result.notes[Source.HARDCOVER] = "HARDCOVER_TOKEN not set"

    if token := os.getenv("GOODREADS_TOKEN"):
        query = isbn or " ".join(filter(None, [title, author]))
        attempt(Source.GOODREADS, lambda: from_goodreads(cache, token, query))
    else:
        result.notes[Source.GOODREADS] = "GOODREADS_TOKEN not set"

    return result
