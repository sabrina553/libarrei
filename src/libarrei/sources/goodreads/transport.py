from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
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
        return self.client.execute(query, variable_values=variables)