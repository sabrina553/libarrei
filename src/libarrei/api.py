"""HTTP API: the parser front-end that Grimmory and other apps call.

Versioned under /v1 so the response shape can change without breaking callers.
Source tokens come from the server's environment for now.
"""

import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from libarrei import normalise
from libarrei.jobs import Job, JobStore
from libarrei.lookup import LookupResult, lookup
from libarrei.merge import MergedEdition, MergedWork, merge
from libarrei.model import Source

app = FastAPI(title="libarrei", version="0.1.0")

# Only the Vite dev server needs cross-origin access; the built GUI is served same-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("LIBARREI_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["X-Hardcover-Token", "Content-Type"],
)

# A librarian's own Hardcover token, sent per request and never stored or logged.
TokenHeader = Header(None, alias="X-Hardcover-Token")

# Which source's first edition is "the" matched edition for a title search:
# Hardcover's search re-ranks by title and author, so it is the most reliable.
MATCH_PRIORITY = [Source.HARDCOVER, Source.GOODREADS, Source.OPENLIBRARY]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _lookup(
    isbn: str | None, title: str | None, author: str | None, all_editions: bool, token: str | None = None
) -> LookupResult:
    if not isbn and not title:
        raise HTTPException(422, "give isbn or title")
    result = lookup(isbn=isbn, title=title, author=author, all_editions=all_editions, hardcover_token=token)
    if not result.works:
        raise HTTPException(404, {"message": "not found in any source", "notes": result.notes})
    return result


class LookupResponse(BaseModel):
    work: MergedWork
    # Why a source returned nothing, keyed by source name.
    notes: dict[str, str] = {}


@app.get("/v1/lookup", response_model=LookupResponse, response_model_exclude_defaults=True)
def lookup_merged(
    isbn: str | None = None,
    title: str | None = None,
    author: str | None = None,
    editions: str = Query("matched", pattern="^(matched|all)$"),
    x_hardcover_token: str | None = TokenHeader,
) -> LookupResponse:
    """The full merged record: chosen values, alternatives and conflicts."""
    result = _lookup(isbn, title, author, all_editions=editions == "all", token=x_hardcover_token)
    return LookupResponse(work=merge(result.works), notes={s.value: n for s, n in result.notes.items()})


class JobRequest(BaseModel):
    isbn: str | None = None
    title: str | None = None
    author: str | None = None


def _full_lookup(isbn: str | None, title: str | None, author: str | None, token: str | None = None) -> dict:
    response = lookup_merged(isbn=isbn, title=title, author=author, editions="all", x_hardcover_token=token)
    return response.model_dump(mode="json", exclude_defaults=True)


jobs = JobStore(lambda **query: _full_lookup(**query))


class JobView(BaseModel):
    id: str
    status: Literal["queued", "running", "done", "failed"]
    query: JobRequest
    result: LookupResponse | None = None
    error: str | None = None


def _job_view(job: Job) -> JobView:
    return JobView(id=job.id, status=job.status, query=JobRequest(**job.query),
                   result=job.result if job.status == "done" else None,
                   error=job.error if job.status == "failed" else None)


@app.post("/v1/jobs", status_code=202, response_model=JobView, response_model_exclude_defaults=True)
def start_job(request: JobRequest, x_hardcover_token: str | None = TokenHeader) -> JobView:
    """Fetches every edition in the background; poll GET /v1/jobs/{id} for the result."""
    if not request.isbn and not request.title:
        raise HTTPException(422, "give isbn or title")
    secrets = {"token": x_hardcover_token} if x_hardcover_token else {}
    return _job_view(jobs.submit(request.model_dump(), secrets))


@app.get("/v1/jobs/{job_id}", response_model=JobView, response_model_exclude_defaults=True)
def job_status(job_id: str) -> JobView:
    if not (job := jobs.get(job_id)):
        raise HTTPException(404, "no such job, or it expired")
    return _job_view(job)


@app.get("/v1/metadata")
def metadata(
    isbn: str | None = None, title: str | None = None, author: str | None = None,
    x_hardcover_token: str | None = TokenHeader,
) -> dict:
    """One flat record in Grimmory's BookMetadata field names."""
    result = _lookup(isbn, title, author, all_editions=False, token=x_hardcover_token)
    merged = merge(result.works)
    return to_grimmory(merged, matched_edition(result, merged, isbn))


def matched_edition(result: LookupResult, merged: MergedWork, isbn: str | None) -> MergedEdition | None:
    """The merged edition the caller asked about."""
    if isbn and (wanted := normalise.isbn(isbn)):
        wanted13 = normalise.isbn10_to_13(wanted) if len(wanted) == 10 else wanted
        for edition in merged.editions:
            resolved = edition.fields.get("isbn13")
            values = [resolved.value, *(a.value for a in resolved.alternatives)] if resolved else []
            if wanted13 in values:
                return edition
    for source in MATCH_PRIORITY:
        work = result.works.get(source)
        if work and work.editions and source in work.editions[0].ids:
            first_id = work.editions[0].ids[source]
            for edition in merged.editions:
                if first_id in edition.ids.get(source, []):
                    return edition
    return None


def to_grimmory(work: MergedWork, edition: MergedEdition | None) -> dict:
    def pick(name: str):
        # Edition values describe the exact book in hand, so they win over the work's.
        for fields in (edition.fields if edition else {}, work.fields):
            if name in fields:
                return fields[name].value
        return None

    contributors = pick("contributors") or []
    series = (work.fields["series"].value if "series" in work.fields else None) or []
    ids = edition.ids if edition else {}
    position = series[0].position if series else None
    record = {
        "title": pick("title"),
        "subtitle": pick("subtitle"),
        "authors": [c.name for c in contributors if c.role == "author"],
        "narrator": next((c.name for c in contributors if c.role == "narrator"), None),
        "description": work.fields["description"].value if "description" in work.fields else None,
        "publisher": pick("publisher"),
        # May be partial ("1976" or "1976-08"); padding it would invent precision.
        "publishedDate": pick("release_date") or pick("original_release_date"),
        "seriesName": series[0].name if series else None,
        "seriesNumber": _float(position),
        "isbn13": pick("isbn13"),
        "isbn10": pick("isbn10"),
        "asin": pick("asin"),
        "pageCount": pick("pages"),
        "language": pick("language"),
        "categories": pick("genres") or [],
        "thumbnailUrl": pick("cover_url"),
        "goodreadsId": _first(ids, Source.GOODREADS) or work.ids.get(Source.GOODREADS),
        "hardcoverId": _first(ids, Source.HARDCOVER),
        "hardcoverBookId": work.ids.get(Source.HARDCOVER),
        "openlibraryId": _first(ids, Source.OPENLIBRARY) or work.ids.get(Source.OPENLIBRARY),
        # Not in Grimmory's model: which fields sources disagreed on, for review.
        "conflicts": sorted({n for n, r in (edition.fields if edition else {}).items() if r.conflict}
                            | {n for n, r in work.fields.items() if r.conflict}),
    }
    return {k: v for k, v in record.items() if v not in (None, [], "")}


def _first(ids: dict, source: Source) -> str | None:
    return ids[source][0] if ids.get(source) else None


def _float(position: str | None) -> float | None:
    try:
        return float(position) if position else None
    except ValueError:
        return None
