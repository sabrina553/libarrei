"""Which fields each source can ever fill, taken from sources/*/mapping.py.

The GUI keeps the same map in web/src/components/capabilities.ts; a test
checks the two stay in step.
"""

from libarrei.model import Source

GR, HC, OL, AU, AZ = Source.GOODREADS, Source.HARDCOVER, Source.OPENLIBRARY, Source.AUDIBLE, Source.AMAZON

EDITION: dict[Source, frozenset[str]] = {
    HC: frozenset({"title", "subtitle", "edition_statement", "contributors", "isbn13", "isbn10", "asin", "publisher",
                   "release_date", "pages", "format", "format_detail", "duration_seconds", "language", "cover_url"}),
    GR: frozenset({"title", "subtitle", "contributors", "isbn13", "isbn10", "asin", "publisher",
                   "release_date", "pages", "format", "format_detail", "language", "cover_url"}),
    OL: frozenset({"title", "subtitle", "edition_statement", "contributors", "isbn13", "isbn10", "asin",
                   "identifiers", "publisher", "release_date", "pages", "format", "format_detail", "language",
                   "cover_url", "series"}),
    AU: frozenset({"title", "subtitle", "edition_statement", "contributors", "asin", "publisher", "release_date",
                   "format", "format_detail", "duration_seconds", "language", "cover_url", "series"}),
    AZ: frozenset({"title", "subtitle", "contributors", "isbn13", "isbn10", "asin", "publisher", "release_date",
                   "pages", "format", "format_detail", "language", "cover_url", "series"}),
}

WORK: dict[Source, frozenset[str]] = {
    HC: frozenset({"title", "subtitle", "contributors", "description", "series", "genres", "original_release_date"}),
    GR: frozenset({"title", "contributors", "description", "series", "genres", "original_release_date"}),
    OL: frozenset({"title", "subtitle", "contributors", "description", "series", "genres", "original_release_date"}),
    AU: frozenset({"title", "subtitle", "contributors", "description", "series"}),
    AZ: frozenset({"title", "subtitle", "contributors", "description", "series"}),
}
