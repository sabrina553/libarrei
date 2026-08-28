from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

class TransportLayer:
    def __init__(self, token):
        transport = AIOHTTPTransport(
            url="https://api.hardcover.app/v1/graphql",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.client = Client(transport=transport)

    def execute(self, query, variables=None):
        return self.client.execute(gql(query), variable_values=variables)