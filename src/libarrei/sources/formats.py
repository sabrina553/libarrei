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
    "audible audiobook": "audiobook",
    "audiobook": "audiobook",
    "audio cd": "audiobook",
    "mp3 cd": "audiobook",
    # Seen across all editions of The Hobbit, including non-English labels.
    "hardback": "physical",
    "trade paperback": "physical",
    "pocket book": "physical",
    "library binding": "physical",
    "school & library binding": "physical",
    "turtleback": "physical",
    "flexibound": "physical",
    "staple bound": "physical",
    "unbound": "physical",
    "leather": "physical",
    "leather bound": "physical",
    "leather-bound": "physical",
    "vinyl bound": "physical",
    "vinyl cover": "physical",
    "hardcover (dust jacket)": "physical",
    "book club (bce/bomc)": "physical",
    "comic": "physical",
    "gebundene ausgabe": "physical",
    "capa dura": "physical",
    "capa comum": "physical",
    "tapa dura": "physical",
    "tapa dura (hardcober)": "physical",
    "rústica": "physical",
    "epub": "ebook",
    "nook": "ebook",
    "electronic resource": "ebook",
    "audio cassette": "audiobook",
    "digital audio": "audiobook",
    "audio drama": "audiobook",
    "preloaded digital audio player": "audiobook",
}

# Labels that say nothing about the edition's format.
UNKNOWN = {"unknown binding"}


def normalise_format(raw: str | None) -> str | None:
    """Unknown formats are kept, lowercased, so no information is lost."""
    if not raw or not raw.strip():
        return None
    key = raw.strip().lower()
    if key in UNKNOWN:
        return None
    return FORMATS.get(key, key)


def detail(raw: str | None) -> str | None:
    """The source's own format wording, tidied but otherwise as given."""
    text = " ".join((raw or "").split())
    return None if not text or text.lower() in UNKNOWN else text
