"""SQLite cache of raw source responses, so repeat lookups cost no requests.

Raw responses are stored rather than mapped Works, so improving a mapping never
needs a refetch. Keys are (source, request) where request is any stable string
such as a URL or a GraphQL query name plus its variables.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path

DEFAULT_PATH = Path.home() / ".cache" / "libarrei" / "cache.sqlite3"
# Book metadata changes slowly; a week keeps corrections reasonably fresh.
DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 3600


class Cache:
    def __init__(self, path: Path | str = DEFAULT_PATH, max_age: float = DEFAULT_MAX_AGE_SECONDS, clock=time.time):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.max_age = max_age
        self.clock = clock
        # sqlite3 connections can't cross threads, and sources are fetched in parallel.
        self._local = threading.local()
        # Schema and journal mode are set once here: changing them from several
        # threads at once fails with "database is locked" despite the timeout.
        setup = self._connect()
        if path != ":memory:":
            # WAL lets one source write while another reads.
            setup.execute("PRAGMA journal_mode=WAL")
        setup.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            "source TEXT, request TEXT, body TEXT, fetched_at REAL, PRIMARY KEY (source, request))"
        )
        setup.commit()
        # An in-memory database exists per connection, so it must stay shared.
        self._shared = setup if path == ":memory:" else None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30, check_same_thread=self.path != ":memory:")

    @property
    def db(self) -> sqlite3.Connection:
        if self._shared:
            return self._shared
        if not hasattr(self._local, "db"):
            self._local.db = self._connect()
        return self._local.db

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
