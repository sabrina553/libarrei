"""Fetches Amazon search and product pages with the user's own cookie.

Amazon has no public book API and blocks obvious robots: it answers Python's
own HTTP client with a "continue shopping" check whatever headers it sends, as
it recognises the TLS handshake. curl_cffi reproduces a real browser's
handshake and headers, so requests carry a signed-in user's cookie, look like
that browser's, and are spaced out with jitter.
The cookie is a credential: it never reaches cache keys, errors or reprs.
"""

import random
import time
from urllib.parse import quote_plus

from curl_cffi import requests

from libarrei.cache import NoCache
from libarrei.ratelimit import INTERVALS, RateLimiter
from libarrei.sources.amazon.scraper import is_captcha

DOMAINS = ("com", "co.uk", "de", "fr", "it", "es", "ca", "com.au", "co.jp", "in", "nl", "se", "com.mx", "com.br")
DEFAULT_DOMAIN = "co.uk"
BLOCKED_NOTE = "Amazon blocked the request; update your cookie"
# The browser whose handshake and default headers curl_cffi copies; its own User-Agent must
# not be overridden, or the headers and the handshake would disagree.
IMPERSONATE = "chrome"
HEADERS = {"Accept-Language": "en-GB,en;q=0.9"}


class AmazonBlocked(Exception):
    def __init__(self):
        super().__init__(BLOCKED_NOTE)


def product_url(domain: str, asin: str) -> str:
    return f"https://www.amazon.{domain}/dp/{asin}"


class Amazon:
    def __init__(self, cookie: str, domain: str = DEFAULT_DOMAIN, session: requests.Session | None = None,
                 cache=None, limiter: RateLimiter | None = None, jitter=lambda: random.uniform(0.5, 1.5),
                 sleep=time.sleep):
        if domain not in DOMAINS:
            raise ValueError(f"unknown Amazon domain {domain!r}; use one of {', '.join(DOMAINS)}")
        cookie = cookie.strip()
        # A line break would let the value smuggle in extra headers.
        if not cookie or "\r" in cookie or "\n" in cookie:
            raise ValueError("the Amazon cookie must be one non-empty line")
        self.domain = domain
        self.base = f"https://www.amazon.{domain}"
        self.session = session or requests.Session(impersonate=IMPERSONATE)
        self.session.headers.update(HEADERS)
        self.session.headers["Cookie"] = cookie
        self.cache = cache or NoCache()
        self.limiter = limiter or RateLimiter(INTERVALS["amazon"])
        self.jitter = jitter
        self.sleep = sleep
        # Once Amazon pushes back, every further request this run would only dig deeper.
        self.blocked = False

    def __repr__(self) -> str:
        return f"Amazon(domain={self.domain!r}, cookie=<redacted>)"

    def _page(self, url: str) -> str | None:
        def load():
            if self.blocked:
                raise AmazonBlocked()
            self.limiter.wait()
            # Evenly spaced requests look robotic, so each gets a random extra pause.
            self.sleep(self.jitter())
            res = self.session.get(url, timeout=20)
            if res.status_code == 404:
                return None
            if res.status_code in (500, 503) or is_captcha(res.text):
                self.blocked = True
                raise AmazonBlocked()
            res.raise_for_status()
            return res.text

        # Keyed by URL alone: pages are the same whoever's cookie fetched them.
        return self.cache.fetch("amazon", url, load)

    def search(self, query: str) -> str | None:
        return self._page(f"{self.base}/s?k={quote_plus(query)}")

    def product(self, asin: str) -> str | None:
        return self._page(product_url(self.domain, quote_plus(asin)))
