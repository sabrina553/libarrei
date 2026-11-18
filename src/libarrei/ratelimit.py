"""Spaces out requests to one source; the 429 backoff stays as a fallback."""

import time

# Seconds between requests per source. Hardcover allows 60 a minute; Open Library
# asks for about one a second; Goodreads is scraped, so it gets more breathing room.
INTERVALS = {"hardcover": 1.0, "openlibrary": 1.0, "goodreads": 2.0}


class RateLimiter:
    def __init__(self, interval: float, clock=time.monotonic, sleep=time.sleep):
        self.interval = interval
        self.clock = clock
        self.sleep = sleep
        self.last = None

    def wait(self) -> None:
        now = self.clock()
        if self.last is not None and (gap := self.interval - (now - self.last)) > 0:
            self.sleep(gap)
            now += gap
        self.last = now
