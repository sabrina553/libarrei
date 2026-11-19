from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
#    // Located in Goodreads _app JS chunk, visible in DevTools → Network → GraphQL requests
class TransportLayer:
    def __init__(self, token):
        transport = AIOHTTPTransport(
            url="https://kxbwmqov6jgg3daaamb744ycu4.appsync-api.us-east-1.amazonaws.com/graphql",
            headers = {
                "x-api-key": f"{token}", # make this dynamic
                "Content-Type": "application/json"
            }
        )
        self.client = Client(transport=transport)

    def execute(self, query, variables=None):
        # query is already a parsed gql() request, built once by the caller
        try:
            return self.client.execute(query, variable_values=variables)
        except TransportQueryError as error:
            if missing_items_only(error):
                return error.data
            raise


def missing_items_only(error: TransportQueryError) -> bool:
    """A search listing a deleted book answers with that one item null and an error for it;
    the rest of the data is still good, so only those errors are tolerated."""
    errors = error.errors or []
    return error.data is not None and bool(errors) and all(e.get("errorType") == "RESOURCE_NOT_FOUND" for e in errors)