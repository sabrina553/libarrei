"""Maps sources' free-text format names onto Libarrei's shared vocabulary."""

FORMATS = {
    "hardcover": "physical",
    "paperback": "physical",
    "mass market paperback": "physical",
    "board book": "physical",
    "kindle edition": "ebook",
    "ebook": "ebook",
    "e-book": "ebook",
    "audible audio": "audiobook",
    "audiobook": "audiobook",
    "audio cd": "audiobook",
    "mp3 cd": "audiobook",
}


def normalise_format(raw: str | None) -> str | None:
    """Unknown formats are kept, lowercased, so no information is lost."""
    if not raw or not raw.strip():
        return None
    return FORMATS.get(raw.strip().lower(), raw.strip().lower())
