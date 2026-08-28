import os

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from dotenv import load_dotenv, dotenv_values 

load_dotenv()
api_key = os.getenv("HARDCOVER_TOKEN")

transport = AIOHTTPTransport(
    url="https://api.hardcover.app/v1/graphql",
    headers={"Authorization": f"Bearer {api_key}"},
)

# Create a GraphQL client using the defined transport
client = Client(transport=transport)

# Provide a GraphQL query
query = gql(
"""
  query BookSearchByIsbn($isbn: [String!]!, $hcid: [Int!]!) {
  books(
      where: {editions: {_or: [{isbn_13: {_in: $isbn}}, {isbn_10: {_in: $isbn}}, {book_id: {_in: $hcid}} ]}}
  ) {
      id
      slug
      title
      subtitle
      description
      cached_contributors
      featured_book_series {
        series {
          name
          books_count
          primary_books_count
        }
        position
      }
      rating
      ratings_count
      reviews_count
      pages
      release_date
      release_year
      image {
        url
      }
      cached_tags
      editions(where: {_or: [{isbn_13: {_in: $isbn}}, {isbn_10: {_in: $isbn}}, {book_id: {_in: $hcid}}]}, order_by: [{score: desc}]) {
        id
        title
        subtitle
        cached_contributors
        pages
        release_date
        release_year
        image {
          url
        }
        publisher {
          name
        }
        isbn_10
        isbn_13
        language {
          code2
        }
        reading_format_id
        score
      }
    }
  }
"""
)

# Execute the query on the transport
result = client.execute(
  query,
  variable_values={
      "isbn": ["9781324089025"],
      "hcid": [],
  },
)

print(result)
