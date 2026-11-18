"""Puts each source's values into one shape so editions can be compared.

Unrecognised values are kept (lowercased where that helps) rather than dropped,
so nothing a source said is lost; only values that are clearly not of the
field's type, such as a publisher scraped into a date, are discarded.
"""

import re
from datetime import date

import pycountry

from libarrei.model import Edition, Work

MONTH_NAMES = ["january", "february", "march", "april", "may", "june",
               "july", "august", "september", "october", "november", "december"]
# Full English names or three-letter abbreviations; "julho" must not read as July.
MONTHS = {name: i for i, full in enumerate(MONTH_NAMES, start=1) for name in (full, full[:3], "sept")
          if name != "sept" or i == 9}
YEAR = r"(1[5-9]\d\d|20\d\d)"


def release_date(raw: str | None) -> str | None:
    """ISO 8601 at whatever precision the source gave: YYYY, YYYY-MM or YYYY-MM-DD."""
    if not raw:
        return None
    text = raw.strip().lower()
    if m := re.fullmatch(rf"{YEAR}(?:-(\d\d))?(?:-(\d\d))?", text):
        return _iso(*m.groups())
    month = next((n for name, n in MONTHS.items() if re.search(rf"\b{name}\b", text)), None)
    year = re.search(rf"\b{YEAR}\b", text)
    if not year:
        return None
    if month is None:
        # Non-English month names ("15 julho 2019") still give a reliable year.
        return year.group(1)
    day = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\b(?!\d)", text.replace(year.group(1), ""))
    return _iso(year.group(1), f"{month:02}", f"{int(day.group(1)):02}" if day else None)


def _iso(year: str, month: str | None, day: str | None) -> str | None:
    if month and day:
        try:
            return date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            return f"{year}-{month}"
    return f"{year}-{month}" if month else year


def language(raw: str | None) -> str | None:
    """ISO 639-1 where one exists (en, fr), else ISO 639-3; unknown names lowercased."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    for name in _language_names(text):
        if record := (pycountry.languages.get(alpha_2=name.lower()) if len(name) == 2 else None) \
                or (pycountry.languages.get(alpha_3=name.lower()) if len(name) == 3 else None) \
                or (pycountry.languages.get(bibliographic=name.lower()) if len(name) == 3 else None) \
                or pycountry.languages.get(name=name):
            return getattr(record, "alpha_2", record.alpha_3)
    return text.lower()


def _language_names(text: str) -> list[str]:
    # Goodreads uses ISO 639-2 English names such as "Catalan; Valencian" and
    # "Greek, Modern (1453-)", which pycountry lists as "Catalan" and "Modern Greek (1453-)".
    names = []
    for part in (p.strip() for p in text.split(";")):
        names.append(part)
        if m := re.fullmatch(r"([^,]+), ([^(]+?)(\s*\(.*\))?", part):
            names.append(f"{m.group(2)} {m.group(1)}{m.group(3) or ''}")
    return names


def isbn(raw: str | None) -> str | None:
    """Digits (and a trailing X) only, if the checksum is valid."""
    if not raw:
        return None
    digits = re.sub(r"[^0-9X]", "", raw.upper())
    if len(digits) == 10 and _isbn10_valid(digits):
        return digits
    if len(digits) == 13 and digits.isdigit() and _isbn13_check(digits[:12]) == digits[12]:
        return digits
    return None


def isbn10_to_13(isbn10: str) -> str:
    stem = "978" + isbn10[:9]
    return stem + _isbn13_check(stem)


def _isbn10_valid(digits: str) -> bool:
    if not digits[:9].isdigit() or not (digits[9].isdigit() or digits[9] == "X"):
        return False
    values = [int(d) for d in digits[:9]] + [10 if digits[9] == "X" else int(digits[9])]
    return sum((10 - i) * v for i, v in enumerate(values)) % 11 == 0


def _isbn13_check(stem: str) -> str:
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(stem))
    return str((10 - total % 10) % 10)


def asin(raw: str | None) -> str | None:
    """Drops "ASINs" that are really ISBN-10s, as Goodreads shows for print books."""
    if not raw or not raw.strip():
        return None
    value = raw.strip().upper()
    return None if isbn(value) else value


EDITION_FIELDS = {"release_date": release_date, "language": language, "isbn13": isbn, "isbn10": isbn, "asin": asin}


def work(record: Work) -> None:
    """Normalises a mapped Work and its editions in place."""
    record.original_release_date = _apply(record.original_release_date, release_date)
    for edition in record.editions:
        for name, normaliser in EDITION_FIELDS.items():
            setattr(edition, name, _apply(getattr(edition, name), normaliser))
        _derive_isbn13(edition)


def _apply(candidates: list, normaliser) -> list:
    kept = []
    for c in candidates:
        if (value := normaliser(c.value)) is not None:
            kept.append(c.model_copy(update={"value": value}))
    return kept


def _derive_isbn13(edition: Edition) -> None:
    # Every ISBN-10 has an ISBN-13 twin, which gives the matcher one key to align on.
    known = {c.value for c in edition.isbn13}
    for c in edition.isbn10:
        if (twin := isbn10_to_13(c.value)) not in known:
            edition.isbn13.append(c.model_copy(update={"value": twin}))
            known.add(twin)
