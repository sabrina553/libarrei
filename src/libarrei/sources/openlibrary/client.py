"""Open Library REST client: https://openlibrary.org/developers/api"""

import requests

BASE_URL = "https://openlibrary.org"
# Open Library asks API clients to identify themselves so heavy users can be contacted.
USER_AGENT = "libarrei (book metadata aggregator)"


class OpenLibrary:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def _get(self, path: str, params: dict | None = None) -> dict | None:
        res = self.session.get(f"{BASE_URL}{path}", params=params, timeout=20)
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()

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
