"""SQLite cache of raw source responses, so repeat lookups cost no requests.

Raw responses are stored rather than mapped Works, so improving a mapping never
needs a refetch. Keys are (source, request) where request is any stable string
such as a URL or a GraphQL query name plus its variables.
"""

import json
import sqlite3
import time
from pathlib import Path

DEFAULT_PATH = Path.home() / ".cache" / "libarrei" / "cache.sqlite3"
# Book metadata changes slowly; a week keeps corrections reasonably fresh.
DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 3600


class Cache:
    def __init__(self, path: Path | str = DEFAULT_PATH, max_age: float = DEFAULT_MAX_AGE_SECONDS, clock=time.time):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            "source TEXT, request TEXT, body TEXT, fetched_at REAL, PRIMARY KEY (source, request))"
        )
        self.max_age = max_age
        self.clock = clock

    def get(self, source: str, request: str):
        row = self.db.execute(
            "SELECT body, fetched_at FROM responses WHERE source = ? AND request = ?", (source, request)
        ).fetchone()
        if row is None or self.clock() - row[1] > self.max_age:
            return None
        return json.loads(row[0])

    def put(self, source: str, request: str, body) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO responses VALUES (?, ?, ?, ?)",
            (source, request, json.dumps(body), self.clock()),
        )
        self.db.commit()

    def fetch(self, source: str, request: str, load):
        """Returns the cached body, or calls load() and caches its result."""
        if (body := self.get(source, request)) is not None:
            return body
        body = load()
        if body is not None:
            self.put(source, request, body)
        return body


class NoCache:
    """Drop-in for Cache when --no-cache is given."""

    def fetch(self, source: str, request: str, load):
        return load()
