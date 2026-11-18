# libarrei
/ˈlaɪ.bə.ræɪ/

A book metadata engine. It fetches every edition of a book from Goodreads,
Hardcover and Open Library, aligns the editions across sources, and merges them
into one record per field while keeping every alternative and flagging conflicts.

Planned front-ends: an HTTP API for apps such as Grimmory, and a review GUI for
Hardcover and Open Library librarians to fix bad metadata.

## Install
Needs [uv](https://docs.astral.sh/uv/) and Python 3.14+.

```sh
uv sync
cp .env.example .env   # then add your tokens
```

- `HARDCOVER_TOKEN`: from Settings → API on hardcover.app.
- `GOODREADS_TOKEN`: the public AppSync key used by the Goodreads web app.

A source without a token is skipped; Open Library needs none.

## Usage
```sh
uv run libarrei lookup --isbn 9780593243732                 # each source side by side
uv run libarrei lookup "the hobbit" --author tolkien --editions   # every edition, aligned
uv run libarrei lookup "the hobbit" --author tolkien --merged     # one value per field, conflicts flagged
uv run libarrei lookup --isbn 9780593243732 --merged --json       # the merged record as JSON
```

| Flag | Effect |
|---|---|
| `--author` | Narrows a title search. |
| `--isbn` | Looks up by ISBN-10 or ISBN-13 instead of title. |
| `--editions` | Lists every edition, grouped across sources, with match reason and duplicates. |
| `--merged` | Picks one value per field; add `--editions` for every merged edition. |
| `--json` | Machine-readable output (raw per-source, or merged with `--merged`). |
| `--no-cache` | Refetches instead of using the cache. |

Responses are cached for a week in `~/.cache/libarrei/` and requests are
rate-limited per source, so a book with hundreds of editions takes a minute or
two the first time and seconds afterwards.

## Tests
```sh
uv run pytest -q
```

The golden set in `tests/golden/` freezes real books and snapshots their merged
output, so any change to normalising, matching or merging shows up as a diff.

```sh
uv run python -m libarrei.golden record hobbit --title "the hobbit" --author tolkien
uv run python -m libarrei.golden update   # accept intended changes, then review the diff
```

## Licence
GPL-3.0-or-later.
