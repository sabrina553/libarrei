import json
import time

from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportServerError

from libarrei.cache import NoCache
from libarrei.ratelimit import INTERVALS, RateLimiter

# Hardcover allows 60 requests a minute and answers 429 when exceeded:
# https://docs.hardcover.app/api/getting-started/
# Backoff values match Grimmory's HardcoverBookSearchService.
INITIAL_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 15.0
MAX_RETRIES = 3


def operation_name(query) -> str:
    """Names a parsed query by its operation (e.g. "BookSearch"), falling back to its text."""
    for definition in getattr(query, "definitions", []):
        if getattr(definition, "name", None):
            return definition.name.value
    return str(query)


class TransportLayer:
    def __init__(self, token, sleep=time.sleep, cache=None, limiter=None):
        transport = AIOHTTPTransport(
            url="https://api.hardcover.app/v1/graphql",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.client = Client(transport=transport)
        self.sleep = sleep
        self.cache = cache if cache is not None else NoCache()
        self.limiter = limiter or RateLimiter(INTERVALS["hardcover"])

    def execute(self, query, variables=None):
        # query is already a parsed gql() request, built once by the caller.
        # sort_keys keeps the key stable whatever order the variables were built in.
        request = f"{operation_name(query)} {json.dumps(variables or {}, sort_keys=True)}"
        return self.cache.fetch("hardcover", request, lambda: self._fetch(query, variables))

    def _fetch(self, query, variables):
        # Only real requests are spaced out; retries are already spaced by the backoff.
        self.limiter.wait()
        delay = INITIAL_DELAY_SECONDS
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self.client.execute(query, variable_values=variables)
            except TransportServerError as error:
                if error.code != 429 or attempt == MAX_RETRIES:
                    raise
                self.sleep(delay)
                delay = min(delay * 2, MAX_DELAY_SECONDS)
