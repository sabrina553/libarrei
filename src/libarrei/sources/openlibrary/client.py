"""Open Library REST client: https://openlibrary.org/developers/api"""

from urllib.parse import urlencode

import requests

from libarrei.cache import NoCache
from libarrei.ratelimit import INTERVALS, RateLimiter

BASE_URL = "https://openlibrary.org"
# Open Library asks API clients to identify themselves so heavy users can be contacted.
USER_AGENT = "libarrei (book metadata aggregator)"


class OpenLibrary:
    def __init__(self, session: requests.Session | None = None, cache=None, limiter: RateLimiter | None = None):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.cache = cache or NoCache()
        self.limiter = limiter or RateLimiter(INTERVALS["openlibrary"])

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        url = f"{BASE_URL}{path}"
        # Sorted params give one cache key per logical request, whatever the dict order.
        key = f"{url}?{urlencode(sorted(params.items()))}" if params else url

        def load():
            # Only real requests are throttled; cache hits cost Open Library nothing.
            self.limiter.wait()
            res = self.session.get(url, params=params, timeout=20)
            if res.status_code == 404:
                return None
            res.raise_for_status()
            return res.json()

        return self.cache.fetch("openlibrary", key, load)

    def edition_by_isbn(self, isbn: str) -> dict | None:
        return self._get(f"/isbn/{isbn}.json")

    def document(self, key: str) -> dict | None:
        """Fetches any keyed document, e.g. "/works/OL28723763W" or "/authors/OL1515577A"."""
        return self._get(f"{key}.json")

    def search(self, title: str, author: str | None = None, limit: int = 5) -> list[dict]:
        params = {"title": title, "limit": limit, "fields": "key,title,author_name,first_publish_year,isbn"}
        if author:
            params["author"] = author
        return (self._get("/search.json", params) or {}).get("docs", [])

    def author_names(self, keys: list[str]) -> dict[str, str]:
        names = {}
        for key in keys:
            if (doc := self.document(key)) and doc.get("name"):
                names[key] = doc["name"]
        return names
