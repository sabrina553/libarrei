"""Libarrei's own data model: a Work (the abstract book) with many Editions.

Every field holds a list of candidate values, one per source that supplied it,
rather than a single answer. Choosing the best value is left to the merger, so
nothing a source said is lost and the review GUI can show sources side by side.
Shape follows OPDS 2.0 publication metadata: https://drafts.opds.io/opds-2.0
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Source(StrEnum):
    GOODREADS = "goodreads"
    HARDCOVER = "hardcover"
    OPENLIBRARY = "openlibrary"
    AUDIBLE = "audible"
    AMAZON = "amazon"


class Candidate[T](BaseModel):
    value: T
    source: Source
    source_id: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Contributor(BaseModel):
    name: str
    role: str = "author"
    ids: dict[Source, str] = {}


class SeriesEntry(BaseModel):
    name: str
    # A string because positions such as "1.5" or "0" (prequel) are common.
    position: str | None = None


class Identifier(BaseModel):
    # Open Library's names: "goodreads", "librarything", "oclc", "lccn", ...
    scheme: str
    value: str


class Record(BaseModel):
    ids: dict[Source, str] = {}
    # For sources whose pages are addressed by slug rather than id: Hardcover's book slug,
    # or the store domain ("co.uk") for stores whose pages differ per region, such as Audible.
    slugs: dict[Source, str] = {}

    def add(self, field: str, value, source: Source, source_id: str) -> None:
        """Records one source's value for a field; empty values are skipped."""
        if value is None or value == "" or value == []:
            return
        getattr(self, field).append(Candidate(value=value, source=source, source_id=source_id))
        self.ids.setdefault(source, source_id)


class Edition(Record):
    title: list[Candidate[str]] = []
    subtitle: list[Candidate[str]] = []
    edition_statement: list[Candidate[str]] = []
    contributors: list[Candidate[list[Contributor]]] = []
    isbn13: list[Candidate[str]] = []
    isbn10: list[Candidate[str]] = []
    asin: list[Candidate[str]] = []
    # Other catalogues' ids for this edition, which also let editions be matched across sources.
    identifiers: list[Candidate[list[Identifier]]] = []
    publisher: list[Candidate[str]] = []
    # Free text, because sources disagree on precision ("2026", "April 28th 2026").
    release_date: list[Candidate[str]] = []
    pages: list[Candidate[int]] = []
    # Coarse bucket for matching: physical, ebook or audiobook.
    format: list[Candidate[str]] = []
    # The source's own wording, such as "Mass Market Paperback".
    format_detail: list[Candidate[str]] = []
    duration_seconds: list[Candidate[int]] = []
    language: list[Candidate[str]] = []
    cover_url: list[Candidate[str]] = []
    # Some series exist only for one edition, such as a publisher's numbered imprint line.
    series: list[Candidate[list[SeriesEntry]]] = []


class Work(Record):
    title: list[Candidate[str]] = []
    subtitle: list[Candidate[str]] = []
    contributors: list[Candidate[list[Contributor]]] = []
    description: list[Candidate[str]] = []
    series: list[Candidate[list[SeriesEntry]]] = []
    genres: list[Candidate[list[str]]] = []
    original_release_date: list[Candidate[str]] = []
    editions: list[Edition] = []
