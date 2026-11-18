"""Goodreads title parsing, shared by the scraper and the GraphQL mapping."""

import re

from libarrei.sources.formats import FORMATS

# Some edition listings append the binding: "Dungeon Crawler Carl (Dungeon Crawler Carl, #1) - Paperback".
_FORMAT_SUFFIX = re.compile(r"\s+[-–—]\s+([^-–—]+)$")


def _strip_format_suffix(title: str) -> str:
    m = _FORMAT_SUFFIX.search(title)
    return title[: m.start()] if m and m.group(1).strip().lower() in FORMATS else title


def parse_title_and_series(raw_title):
    """
    Splits a Goodreads edition title into (title, subtitle, series_name, series_position).

    e.g. "How to Cheat Your Own Death (Castle Knoll Files, #3)"
      -> title="How to Cheat Your Own Death", subtitle=None,
         series_name="Castle Knoll Files", series_position="3"

    The trailing "(...)" on an edition title isn't always a series - Goodreads
    sometimes puts a format/edition note there instead (e.g. "(Hardcover)",
    "(Audible Audio)", "(LA)"). There's no reliable way to tell those apart
    from a real series name by text alone, so we only trust it as a series
    when it ends in "#<number>"; otherwise we discard it (both series_name
    and series_position come back None) and just strip it off the title.
    """
    raw_title = _strip_format_suffix(" ".join(raw_title.split()))
    series_name = None
    series_position = None

    series_match = re.search(r"\(([^()]+)\)\s*$", raw_title)
    if series_match:
        series_text = series_match.group(1).strip()
        title = raw_title[: series_match.start()].strip()

        pos_match = re.search(r"#([\w.\-]+)\s*$", series_text)
        if pos_match:
            series_position = pos_match.group(1)
            series_name = series_text[: pos_match.start()].rstrip(", ").strip()
        # else: no "#N" order present -> discard, not a trustworthy series name
    else:
        title = raw_title

    subtitle = None
    if ":" in title:
        main, sub = title.split(":", 1)
        title, subtitle = main.strip(), sub.strip()

    return title, subtitle, series_name, series_position


def split_title(raw_title: str | None) -> tuple[str | None, str | None]:
    """Just the (title, subtitle) part of parse_title_and_series, tolerating None."""
    if not raw_title:
        return None, None
    title, subtitle, _, _ = parse_title_and_series(raw_title)
    return title, subtitle
