"""Audible's public catalogue API, which needs no account or key.

The same API serves every Audible store; only the domain changes, and a store
answers 200 with an empty product for titles it does not sell.
"""

from urllib.parse import urlencode

import requests

from libarrei.cache import NoCache
from libarrei.ratelimit import INTERVALS, RateLimiter

# Audible's store domains, which double as region names in AUDIBLE_REGION.
REGIONS = ("com", "co.uk", "de", "fr", "it", "es", "ca", "com.au", "co.jp", "in")
DEFAULT_REGION = "co.uk"
# Everything the mapping reads, and nothing more, keeps responses (and the cache) small.
RESPONSE_GROUPS = "contributors,media,product_desc,product_attrs,product_extended_attrs,series,category_ladders,rating"
IMAGE_SIZE = "1000"
USER_AGENT = "libarrei (book metadata aggregator)"


def page_url(region: str, asin: str) -> str:
    return f"https://www.audible.{region}/pd/{asin}"


def is_book(product: dict | None) -> bool:
    # A product without a title is one this store does not sell; podcasts are not books.
    return bool(product and product.get("title")) and product.get("content_type") != "Podcast"


class Audible:
    def __init__(self, region: str = DEFAULT_REGION, session: requests.Session | None = None, cache=None,
                 limiter: RateLimiter | None = None):
        if region not in REGIONS:
            raise ValueError(f"unknown Audible region {region!r}; use one of {', '.join(REGIONS)}")
        self.region = region
        self.base = f"https://api.audible.{region}/1.0/catalog/products"
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.cache = cache or NoCache()
        self.limiter = limiter or RateLimiter(INTERVALS["audible"])

    def _get(self, path: str, params: dict) -> dict | None:
        url = f"{self.base}{path}"
        params = {**params, "response_groups": RESPONSE_GROUPS, "image_sizes": IMAGE_SIZE}
        key = f"{url}?{urlencode(sorted(params.items()))}"

        def load():
            self.limiter.wait()
            res = self.session.get(url, params=params, timeout=20)
            if res.status_code == 404:
                return None
            res.raise_for_status()
            return res.json()

        return self.cache.fetch("audible", key, load)

    def product(self, asin: str) -> dict | None:
        product = (self._get(f"/{asin}", {}) or {}).get("product")
        return product if is_book(product) else None

    def search(self, title: str, author: str | None = None, limit: int = 10) -> list[dict]:
        keywords = " ".join(filter(None, [title, author]))
        params = {"keywords": keywords, "num_results": limit, "products_sort_by": "Relevance"}
        return [p for p in (self._get("", params) or {}).get("products") or [] if is_book(p)]
