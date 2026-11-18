"""Command-line entry point: `libarrei lookup`."""

import argparse
import json
import shutil
import textwrap

from dotenv import load_dotenv

from libarrei.lookup import LookupResult, lookup
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="libarrei", description="Compare book metadata across sources.")
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("lookup", help="find a book by ISBN or by title and author")
    find.add_argument("title", nargs="?", help="book title")
    find.add_argument("--author", help="author name, narrows a title search")
    find.add_argument("--isbn", help="ISBN-10 or ISBN-13")
    find.add_argument("--json", action="store_true", help="print the full model as JSON")
    args = parser.parse_args()

    if not args.isbn and not args.title:
        parser.error("give a title or --isbn")

    load_dotenv()
    result = lookup(isbn=args.isbn, title=args.title, author=args.author)
    if args.json:
        works = {s.value: w.model_dump(mode="json", exclude_defaults=True) for s, w in result.works.items()}
        print(json.dumps({"works": works, "notes": {s.value: n for s, n in result.notes.items()}}, indent=2))
    else:
        print_table(result)
