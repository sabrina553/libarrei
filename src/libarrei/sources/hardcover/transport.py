from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

class TransportLayer:
    def __init__(self, token):
        transport = AIOHTTPTransport(
            url="https://api.hardcover.app/v1/graphql",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.client = Client(transport=transport)

    def execute(self, query, variables=None):
        # query is already a parsed gql() request, built once by the caller
        return self.client.execute(query, variable_values=variables)