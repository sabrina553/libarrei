"""Golden set: real books frozen as fixtures, with merged-output snapshots.

Fixtures hold each source's mapped Work, not raw responses, so scraped HTML
stays out of git; description text is replaced by a placeholder because it is
publisher copyright. Snapshots are plain text so any change in normalising,
matching or merging shows up as a reviewable diff.

    uv run python -m libarrei.golden record hobbit --title "the hobbit" --author tolkien
    uv run python -m libarrei.golden update
    uv run python -m libarrei.golden rerecord   # fetch every set again with its saved query
"""

import argparse
import gzip
import json
from pathlib import Path

from dotenv import load_dotenv

from libarrei import normalise
from libarrei.cli import show
from libarrei.lookup import lookup
from libarrei.merge import MergedWork, merge
from libarrei.model import Source, Work

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "tests" / "golden"
SNAPSHOT_FIELDS = ["isbn13", "format", "language", "release_date", "pages", "publisher", "title"]


def scrub(work: Work) -> None:
    work.description = [
        c.model_copy(update={"value": f"[{c.source.value} description]"}) for c in work.description
    ]


def record(name: str, **query) -> None:
    result = lookup(**query, all_editions=True)
    folder = GOLDEN_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    for work in result.works.values():
        scrub(work)
    data = {s.value: w.model_dump(mode="json", exclude={"__all__": {"fetched_at"}}) for s, w in result.works.items()}
    payload = {"query": query, "works": data}
    # mtime=0 keeps the gzip bytes identical across re-records of unchanged data.
    with gzip.GzipFile(folder / "works.json.gz", "wb", mtime=0) as f:
        f.write(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())
    write_snapshot(folder)


def load_works(folder: Path) -> dict[Source, Work]:
    payload = json.loads(gzip.decompress((folder / "works.json.gz").read_bytes()))
    works = {Source(s): Work.model_validate(w) for s, w in payload["works"].items()}
    for work in works.values():
        # Re-normalising runs today's rules on the frozen data.
        normalise.work(work)
    return works


def render(merged: MergedWork) -> str:
    def cell(fields, name):
        if name not in fields:
            return "-"
        r = fields[name]
        value = show(r.value)
        return f"{value}!" if r.conflict else value

    lines = ["# work"]
    for name, r in merged.fields.items():
        flag = " CONFLICT" if r.conflict else ""
        lines.append(f"{name}: {show(r.value)} [{r.source.value}]{flag}")
    lines.append(f"\n# editions ({len(merged.editions)}); ! marks a conflict")
    rows = []
    for e in merged.editions:
        ids = " ".join(f"{s.value}:{','.join(sorted(v))}" for s, v in sorted(e.ids.items()))
        how = e.match_reason or "-"
        dup = " DUP" if e.duplicates else ""
        rows.append(f"{ids} | {how}{dup} | " + " | ".join(cell(e.fields, n) for n in SNAPSHOT_FIELDS))
    return "\n".join(lines + sorted(rows)) + "\n"


def snapshot(folder: Path) -> str:
    return render(merge(load_works(folder)))


def write_snapshot(folder: Path) -> None:
    (folder / "merged.txt").write_text(snapshot(folder))


def main() -> None:
    parser = argparse.ArgumentParser(prog="libarrei.golden")
    commands = parser.add_subparsers(dest="command", required=True)
    rec = commands.add_parser("record", help="fetch a book and freeze it as a golden fixture")
    rec.add_argument("name")
    rec.add_argument("--title")
    rec.add_argument("--author")
    rec.add_argument("--isbn")
    commands.add_parser("update", help="rewrite every snapshot from the frozen fixtures")
    commands.add_parser("rerecord", help="fetch every golden book again, with the query it was recorded with")
    args = parser.parse_args()

    if args.command == "record":
        load_dotenv(Path.cwd() / ".env")
        record(args.name, title=args.title, author=args.author, isbn=args.isbn)
    elif args.command == "rerecord":
        load_dotenv(Path.cwd() / ".env")
        for folder in sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir()):
            query = json.loads(gzip.decompress((folder / "works.json.gz").read_bytes()))["query"]
            record(folder.name, **query)
            print(f"re-recorded {folder.name}")
    else:
        for folder in sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir()):
            write_snapshot(folder)
            print(f"updated {folder.name}")


if __name__ == "__main__":
    main()
