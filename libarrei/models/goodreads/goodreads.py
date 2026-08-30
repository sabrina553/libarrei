from gql import gql

class Goodreads:
    def __init__(self, transport_layer):
        self.transport_layer = transport_layer
        # Provide a GraphQL query
        self.legacyBookId = gql(
        """
        query GetBookByLegacyId($legacyId: Int!) {
          getBookByLegacyId(legacyId: $legacyId) {
            id
            legacyId
            title
            titleComplete
            webUrl
            imageUrl
            description
            primaryContributorEdge {
              node {
                id
                legacyId
                name
                isGrAuthor
              }
            }
            secondaryContributorEdges {
              node {
                id
                legacyId
                name
                isGrAuthor
              }
            }
            bookSeries {
              userPosition
              series {
                title
              }
            }
            bookGenres {
              genre {
                name
              }
            }
            details {
              asin
              format
              numPages
              publicationTime
              publisher
              isbn
              isbn13
              language {
                name
              }
            }
            work {
              id
              legacyId
              details {
                webUrl
                publicationTime
                originalTitle
              }
              stats {
                averageRating
                ratingsCount
              }
              editions {
                totalCount
              }
            }
            links {
              overflowPageUrl
            }
          }
        }
        """
        )

        self.search = gql(
            """
            query GetSearchSuggestions($query: String!) {
              getSearchSuggestions(query: $query) {
                edges {
                  ... on SearchBookEdge {
                    node {
                      title
                      primaryContributorEdge {
                        node {
                          name
                        }
                      }
                      webUrl
                    }
                  }
                }
              }
            }"""
        )

    def search(self, variable_values):
        return self.transport_layer.execute(self.search, variable_values)

    def legacy_id(self, variable_values):
        return self.transport_layer.execute(self.legacyBookId, variable_values)