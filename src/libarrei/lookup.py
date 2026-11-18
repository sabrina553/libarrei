"""Finds a book in every configured source and returns one Work per source.

Matching across sources is not attempted here: each source's best guess is
returned side by side so the results can be compared. Stores that cannot be
searched by ISBN (Audible) run in a second round, on the title, author and
ASINs the catalogue sources found; Amazon, scraped only with the user's own
cookie, runs in that round too.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from libarrei import normalise
from libarrei.cache import Cache, NoCache
from libarrei.merge import text_key
from libarrei.model import Edition, Source, Work
from libarrei.ratelimit import INTERVALS, RateLimiter
from libarrei.sources.amazon.client import DEFAULT_DOMAIN as AMAZON_DEFAULT_DOMAIN
from libarrei.sources.amazon.client import Amazon, AmazonBlocked
from libarrei.sources.amazon.mapping import to_work as amazon_work
from libarrei.sources.amazon.scraper import parse_product, parse_search
from libarrei.sources.audible.client import DEFAULT_REGION as AUDIBLE_DEFAULT_REGION
from libarrei.sources.audible.client import Audible
from libarrei.sources.audible.mapping import to_work as audible_work
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

# Each known ASIN costs one request, so a work with many audiobook editions is capped.
MAX_KNOWN_ASINS = 10
# Each Amazon page risks a block, so few are fetched however many editions exist.
MAX_AMAZON_PAGES = 3
# Catalogue sources, best first, for the title and author that later stores search by.
CATALOGUE_ORDER = [Source.HARDCOVER, Source.GOODREADS, Source.OPENLIBRARY]


@dataclass
class LookupResult:
    works: dict[Source, Work] = field(default_factory=dict)
    # Why a source returned nothing: missing token, not found, or an error.
    notes: dict[Source, str] = field(default_factory=dict)


@dataclass
class Clues:
    """What the first round of sources learnt, for stores that search by title or ASIN."""
    title: str | None = None
    author: str | None = None
    # Known ASINs, routed to the store that sells that format.
    asins: dict[Source, list[str]] = field(default_factory=lambda: {Source.AUDIBLE: [], Source.AMAZON: []})
    # The work's place in its series, which tells it apart from sequels that share the series name.
    series_position: str | None = None


def stores_for(edition: Edition) -> set[Source]:
    """Audiobooks are Audible's, print and ebooks Amazon's; an unknown or mixed format asks both."""
    formats = {c.value for c in edition.format}
    if formats == {"audiobook"}:
        return {Source.AUDIBLE}
    if formats and "audiobook" not in formats:
        return {Source.AMAZON}
    return {Source.AUDIBLE, Source.AMAZON}


def clues(works: dict[Source, Work], title: str | None, author: str | None) -> Clues:
    found = Clues(title, author)
    for source in CATALOGUE_ORDER:
        if not (work := works.get(source)):
            continue
        if not found.title and work.title:
            found.title = work.title[0].value
        if not found.author and work.contributors:
            found.author = next((c.name for c in work.contributors[0].value if c.role == "author"), None)
        if not found.series_position and work.series:
            found.series_position = next((s.position for s in work.series[0].value if s.position), None)
        for edition in work.editions:
            for store in stores_for(edition):
                found.asins[store] += [c.value for c in edition.asin if c.value not in found.asins[store]]
    found.asins = {store: asins[:MAX_KNOWN_ASINS] for store, asins in found.asins.items()}
    return found


def _name_words(name: str) -> set[str]:
    return set(name.casefold().replace(".", " ").split())


def same_author(product: dict, author: str | None) -> bool:
    # Keyword search ranks loosely, so a hit must share a word with the wanted author's name.
    if not author:
        return True
    return any(_name_words(author) & _name_words(a.get("name") or "") for a in product.get("authors") or [])


def same_work(title: str | None, positions: set[str], found: Clues) -> bool:
    """Keyword search also returns sequels and other books by the author, so a hit must be this work.

    A series number decides when both sides have one, which also keeps translated editions whose
    titles differ. Otherwise the hit's title must start with the work's title.
    """
    if found.series_position and positions:
        return found.series_position in positions
    return bool(found.title) and text_key(title or "").startswith(text_key(found.title))


def audible_is_work(product: dict, found: Clues) -> bool:
    positions = {s["sequence"] for s in product.get("series") or [] if s.get("sequence")}
    return same_work(product.get("title"), positions, found)


def amazon_is_work(product: dict, found: Clues) -> bool:
    series = product.get("series")
    return same_work(product.get("title"), {series[1]} if series and series[1] else set(), found)


def from_audible(cache, region: str, found: Clues, all_editions: bool) -> Work | None:
    client = Audible(region, cache=cache)
    products = [p for asin in found.asins[Source.AUDIBLE] if (p := client.product(asin))]
    if found.title and (all_editions or not products):
        seen = {p["asin"] for p in products}
        hits = client.search(found.title, found.author, limit=20 if all_editions else 5)
        products += [p for p in hits if p["asin"] not in seen and same_author(p, found.author) and audible_is_work(p, found)]
    if not products:
        return None
    return audible_work(products if all_editions else products[:1], region)


def from_amazon(client: Amazon, isbn: str | None, found: Clues, all_editions: bool, note) -> Work | None:
    """Stops at the first sign of a block, keeping whatever was already read."""
    products: list[tuple[str, dict]] = []
    wanted = MAX_AMAZON_PAGES if all_editions else 1
    try:
        # Known ASINs come first and may save the search altogether.
        known = found.asins[Source.AMAZON][:wanted]
        asins = list(known)
        query = isbn or " ".join(filter(None, [found.title, found.author]))
        if query and len(asins) < wanted:
            asins += [a for a in parse_search(client.search(query) or "") if a not in asins]
        for asin in asins[:wanted]:
            if (html := client.product(asin)) and (product := parse_product(html)):
                # An ISBN or a known ASIN names this edition; a title search can land on a sequel.
                if isbn or asin in known or amazon_is_work(product, found):
                    products.append((asin, product))
    except AmazonBlocked as blocked:
        note(str(blocked))
    return amazon_work(products, client.domain) if products else None


def from_openlibrary(
    cache, isbn: str | None, title: str | None, author: str | None, all_editions: bool
) -> Work | None:
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
    if all_editions:
        seen = {e["key"] for e in editions}
        editions += [e for e in ol.all_editions(work_key) if e["key"] not in seen]
    # Only the work's authors: edition-level keys across hundreds of editions
    # would cost one request each on a cold cache.
    names = ol.author_names(author_keys(work))
    return openlibrary_work(work, editions, names)


def from_hardcover(
    cache, token: str, isbn: str | None, title: str | None, author: str | None, all_editions: bool
) -> Work | None:
    client = Hardcover(HardcoverTransport(token, cache=cache))
    if isbn:
        books = client.search({"isbn": [isbn], "hcid": []})["books"]
    else:
        ids = client.search_titles(title or "", author, limit=1)
        books = client.search({"isbn": [], "hcid": ids})["books"] if ids else []
    if not books:
        return None
    work = hardcover_work(books[0])
    if not all_editions:
        return work
    # The searched edition stays first so it remains the best match.
    seen = {e.ids[Source.HARDCOVER] for e in work.editions}
    work.editions += [
        hardcover_edition(e, books[0].get("slug")) for e in client.all_editions(books[0]["id"]) if str(e["id"]) not in seen
    ]
    return work


def from_goodreads(cache, token: str, query: str, all_editions: bool) -> Work | None:
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
    if all_editions and (work_id := work.ids.get(Source.GOODREADS)):
        limiter = RateLimiter(INTERVALS["goodreads"])
        seen = {e.ids.get(Source.GOODREADS) for e in work.editions}
        scraped = [edition_from_editions_page(e) for e in fetch_editions(work_id, cache, limiter)]
        work.editions += [e for e in scraped if e.ids.get(Source.GOODREADS) not in seen]
    return work


def run_parallel(jobs: dict, attempt) -> None:
    # Sources are independent and network-bound, so a round takes as long as
    # the slowest source rather than all of them added up.
    with ThreadPoolExecutor(max_workers=max(len(jobs), 1)) as pool:
        for source, job in jobs.items():
            pool.submit(attempt, source, job)


def lookup(
    isbn: str | None = None, title: str | None = None, author: str | None = None, use_cache: bool = True,
    all_editions: bool = False, hardcover_token: str | None = None, amazon_cookie: str | None = None,
) -> LookupResult:
    """Without all_editions only the matched edition per source is fetched: a few
    requests, rather than minutes for a book with hundreds of editions."""
    result = LookupResult()
    cache = Cache() if use_cache else NoCache()

    def attempt(source: Source, fetch) -> None:
        try:
            work = fetch()
        except Exception as error:  # one failing source must not hide the others
            result.notes[source] = f"error: {error}"
            return
        if work:
            normalise.work(work)
            result.works[source] = work
        else:
            result.notes.setdefault(source, "not found")

    jobs = {Source.OPENLIBRARY: lambda: from_openlibrary(cache, isbn, title, author, all_editions)}
    # A caller's own token (a librarian's, via the API) wins over the server's.
    if token := hardcover_token or os.getenv("HARDCOVER_TOKEN"):
        jobs[Source.HARDCOVER] = lambda: from_hardcover(cache, token, isbn, title, author, all_editions)
    else:
        result.notes[Source.HARDCOVER] = "HARDCOVER_TOKEN not set"
    if gr_token := os.getenv("GOODREADS_TOKEN"):
        query = isbn or " ".join(filter(None, [title, author]))
        jobs[Source.GOODREADS] = lambda: from_goodreads(cache, gr_token, query, all_editions)
    else:
        result.notes[Source.GOODREADS] = "GOODREADS_TOKEN not set"
    run_parallel(jobs, attempt)

    found = clues(result.works, title, author)
    region = os.getenv("AUDIBLE_REGION") or AUDIBLE_DEFAULT_REGION
    later = {Source.AUDIBLE: lambda: from_audible(cache, region, found, all_editions)}
    # Off unless someone supplies a cookie: scraping Amazon is opt-in.
    if cookie := amazon_cookie or os.getenv("AMAZON_COOKIE"):
        domain = os.getenv("AMAZON_DOMAIN") or AMAZON_DEFAULT_DOMAIN
        # Built inside the job so a bad domain or cookie becomes a note, not a failed lookup.
        later[Source.AMAZON] = lambda: from_amazon(
            Amazon(cookie, domain, cache=cache), isbn, found, all_editions,
            lambda note: result.notes.__setitem__(Source.AMAZON, note))
    else:
        result.notes[Source.AMAZON] = "AMAZON_COOKIE not set"
    run_parallel(later, attempt)

    # Fixed source order keeps output stable whichever source finished first.
    result.works = {s: result.works[s] for s in Source if s in result.works}
    return result
