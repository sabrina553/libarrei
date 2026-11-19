"""Looks up every book in a list and prints one summary line each, as a regression check.

The list is "Author | Title" per line; blank lines and "#" comments are skipped.
Run before and after a matching change and diff the two outputs:

    uv run python scripts/sweep.py local/library-sample.txt > local/sweep-before.tsv
    uv run python scripts/sweep.py local/library-sample.txt --all > local/sweep-all.tsv

Lookups use the response cache, so a re-run only fetches what is new.
"""

import argparse
import sys
from difflib import SequenceMatcher
from pathlib import Path

from dotenv import load_dotenv

from libarrei.asin_check import check_all
from libarrei.lookup import lookup
from libarrei.merge import merge
from libarrei.model import Source

COLUMNS = ["author", "title", "found_title", "title_match", "sources", "editions", "conflicted", "duplicates",
           "stubs", "fuzzy", "isbn_clashes", "asin_not_found", "notes"]
# Below this the found work is probably not the book that was asked for.
TITLE_MATCH = 0.6


def books(path: Path) -> list[tuple[str, str]]:
    pairs = []
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "|" in line:
            author, title = (part.strip() for part in line.split("|", 1))
            pairs.append((author, title))
    return pairs


def summary(author: str, title: str, all_editions: bool) -> list[str]:
    result = lookup(title=title, author=author, all_editions=all_editions)
    work = merge(result.works)
    if result.probe:
        check_all(work.editions, result.probe)
    found = work.fields.get("title")
    found_title = str(found.value) if found else ""
    # Compared without the subtitle, so "Atomic Habits" matches "Atomic Habits: An Easy & Proven Way…".
    main_title = found_title.split(":", 1)[0]
    similarity = SequenceMatcher(None, title.lower(), main_title.lower()).ratio() if found_title else 0.0
    editions = work.editions
    return [
        author, title, found_title, f"{similarity:.2f}{'' if similarity >= TITLE_MATCH else ' ?'}",
        ",".join(sorted(s.value[:2] for s in result.works)),
        str(len(editions)),
        str(sum(any(r.conflict for r in e.fields.values()) for e in editions)),
        str(sum(bool(e.duplicates) for e in editions)),
        str(sum(e.stub_of is not None for e in editions)),
        str(sum(e.match_reason == "fuzzy" for e in editions)),
        str(sum(bool(e.format_clash_isbns) for e in editions)),
        str(sum(s == "not_found" for e in editions for s in e.asin_checks.values())),
        "; ".join(f"{s.value}: {n}" for s, n in sorted(result.notes.items()) if s != Source.AMAZON or "not set" not in n),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("list", type=Path)
    parser.add_argument("--all", action="store_true", help="fetch every edition, not only the matched ones (slow)")
    args = parser.parse_args()
    load_dotenv(Path.cwd() / ".env")
    print("\t".join(COLUMNS))
    for author, title in books(args.list):
        try:
            row = summary(author, title, args.all)
        except Exception as error:  # noqa: BLE001 - one bad lookup must not end the sweep
            row = [author, title, "", "", "", "", "", "", "", "", "", "", f"error: {error}"]
        print("\t".join(row), flush=True)
        print(f"{title}: done", file=sys.stderr)


if __name__ == "__main__":
    main()
