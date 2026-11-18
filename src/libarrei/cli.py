"""Command-line entry point: `libarrei lookup`."""

import argparse
import json
import shutil
import textwrap

from dotenv import load_dotenv

from libarrei.lookup import LookupResult, lookup
from libarrei.match import align
from libarrei.merge import MergedWork, merge
from libarrei.model import Candidate, Contributor, SeriesEntry, Work

COMPARED_FIELDS = ["title", "subtitle", "contributors", "series", "genres", "original_release_date", "description"]


def show(value) -> str:
    if isinstance(value, list):
        return ", ".join(show(v) for v in value)
    if isinstance(value, Contributor):
        return value.name if value.role == "author" else f"{value.name} ({value.role})"
    if isinstance(value, SeriesEntry):
        return f"{value.name} #{value.position}" if value.position else value.name
    return " ".join(str(value).split())


def first(candidates: list[Candidate]) -> str:
    return show(candidates[0].value) if candidates else "-"


def edition_summary(work: Work) -> str:
    isbns = sorted({c.value for e in work.editions for c in e.isbn13})
    return f"{len(work.editions)} fetched; ISBN-13: {', '.join(isbns) or '-'}"


def print_table(result: LookupResult) -> None:
    width = shutil.get_terminal_size((100, 20)).columns
    for name in COMPARED_FIELDS + ["editions"]:
        print(f"\n{name}")
        for source, work in result.works.items():
            value = edition_summary(work) if name == "editions" else first(getattr(work, name))
            prefix = f"  {source.value:<12} "
            print(prefix + textwrap.shorten(value, width=max(width - len(prefix), 20), placeholder=" ..."))
    for source, note in result.notes.items():
        print(f"\n{source.value}: {note}")


def print_editions(result: LookupResult) -> None:
    groups = sorted(align(result.works), key=lambda g: (-len(g.sources), g.reason or "~"))
    for g in groups:
        source, e = g.members[0]
        cells = [first(e.isbn13), first(e.format), first(e.language), first(e.release_date)]
        tags = ",".join(sorted(s.value for s in g.sources))
        how = f"{g.reason} {g.confidence:g}" if g.reason == "fuzzy" else g.reason or "-"
        dup = f"  DUPLICATE in {','.join(s.value for s in g.duplicates)}" if g.duplicates else ""
        print("  ".join(f"{c:<14}" for c in cells) + f"{how:<12}{tags}{dup}")

    print(f"\n{len(groups)} edition groups")
    for n in range(len(result.works), 0, -1):
        print(f"  in {n} source(s): {sum(len(g.sources) == n for g in groups)}")
    print(f"  fuzzy-matched: {sum(g.reason == 'fuzzy' for g in groups)}")
    print(f"  with duplicates: {sum(bool(g.duplicates) for g in groups)}")
    for source, note in result.notes.items():
        print(f"\n{source.value}: {note}")


def print_merged(merged: MergedWork, with_editions: bool) -> None:
    width = shutil.get_terminal_size((100, 20)).columns
    for name, r in merged.fields.items():
        # Tags go before the value so truncating a long description never hides them.
        tags = f"[{r.source.value}]" + (f" ({r.licence})" if r.licence else "") + (" CONFLICT" if r.conflict else "")
        head = f"{name:<22}{tags} "
        print(head + textwrap.shorten(show(r.value), max(width - len(head), 20), placeholder=" ..."))
        for a in r.alternatives:
            alt = f"{'':<24}[{a.source.value}] "
            print(alt + textwrap.shorten(show(a.value), max(width - len(alt), 20), placeholder=" ..."))

    editions = merged.editions
    multi = [e for e in editions if len(e.ids) > 1]
    print(f"\n{len(editions)} editions, {len(multi)} found in more than one source")
    counts = {}
    for e in multi:
        for name, r in e.fields.items():
            counts[name] = counts.get(name, 0) + r.conflict
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n:
            print(f"  {name:<14} conflicts in {n}")
    if with_editions:
        print()
        for e in editions:
            value = lambda f: show(e.fields[f].value) if f in e.fields else "-"
            cells = [value("isbn13"), value("format"), value("language"), value("release_date")]
            conflicts = ",".join(n for n, r in e.fields.items() if r.conflict)
            sources = ",".join(sorted(s.value for s in e.ids))
            print("  ".join(f"{c:<14}" for c in cells) + f"{sources:<34}{conflicts}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="libarrei", description="Compare book metadata across sources.")
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("lookup", help="find a book by ISBN or by title and author")
    find.add_argument("title", nargs="?", help="book title")
    find.add_argument("--author", help="author name, narrows a title search")
    find.add_argument("--isbn", help="ISBN-10 or ISBN-13")
    find.add_argument("--no-cache", action="store_true", help="ignore cached responses and refetch")
    find.add_argument("--editions", action="store_true", help="fetch and list every edition, aligned across sources (slow when uncached)")
    find.add_argument("--merged", action="store_true", help="pick one value per field and flag conflicts")
    find.add_argument("--json", action="store_true", help="print the full model as JSON")
    serve = commands.add_parser("serve", help="run the HTTP API")
    # Loopback by default so the API is only reachable from this machine unless asked.
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    commands.add_parser("openapi", help="print the API's OpenAPI schema (used to generate GUI types)")
    args = parser.parse_args()

    if args.command == "openapi":
        from libarrei.api import app

        print(json.dumps(app.openapi(), indent=2))
        return

    load_dotenv()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("libarrei.api:app", host=args.host, port=args.port)
        return

    if not args.isbn and not args.title:
        parser.error("give a title or --isbn")

    result = lookup(isbn=args.isbn, title=args.title, author=args.author, use_cache=not args.no_cache,
                    all_editions=args.editions)
    if args.merged:
        merged = merge(result.works)
        if args.json:
            print(merged.model_dump_json(indent=2, exclude_defaults=True))
        else:
            print_merged(merged, args.editions)
        for source, note in result.notes.items():
            print(f"\n{source.value}: {note}")
    elif args.json:
        works = {s.value: w.model_dump(mode="json", exclude_defaults=True) for s, w in result.works.items()}
        print(json.dumps({"works": works, "notes": {s.value: n for s, n in result.notes.items()}}, indent=2))
    elif args.editions:
        print_editions(result)
    else:
        print_table(result)
