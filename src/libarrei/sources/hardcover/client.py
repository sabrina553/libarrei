from gql import gql

class Hardcover:
    def __init__(self, transport_layer):
        self.transport_layer = transport_layer
        # Provide a GraphQL query
        self.BookSearch = gql(
        """
          query BookSearch($isbn: [String!]!, $hcid: [Int!]!) {
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

    def search(self, variable_values):
        return self.transport_layer.execute(self.BookSearch, variable_values)