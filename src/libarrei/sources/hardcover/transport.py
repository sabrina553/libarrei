import time

from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportServerError

# Hardcover allows 60 requests a minute and answers 429 when exceeded:
# https://docs.hardcover.app/api/getting-started/
# Backoff values match Grimmory's HardcoverBookSearchService.
INITIAL_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 15.0
MAX_RETRIES = 3


class TransportLayer:
    def __init__(self, token, sleep=time.sleep):
        transport = AIOHTTPTransport(
            url="https://api.hardcover.app/v1/graphql",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.client = Client(transport=transport)
        self.sleep = sleep

    def execute(self, query, variables=None):
        # query is already a parsed gql() request, built once by the caller
        delay = INITIAL_DELAY_SECONDS
        for attempt in range(MAX_RETRIES + 1):
            try:
                return self.client.execute(query, variable_values=variables)
            except TransportServerError as error:
                if error.code != 429 or attempt == MAX_RETRIES:
                    raise
                self.sleep(delay)
                delay = min(delay * 2, MAX_DELAY_SECONDS)
