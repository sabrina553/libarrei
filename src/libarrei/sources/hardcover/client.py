import re
from difflib import SequenceMatcher

from gql import gql

# Search ranking from Grimmory's HardcoverBookSearchService: weights pair up
# with fields in order, so author names count most when an author is given.
TITLE_AUTHOR_WEIGHTS = ("5,3,10,5", "title,alternative_titles,author_names,description")
TITLE_ONLY_WEIGHTS = ("10,5,3", "title,alternative_titles,description")


# Hardcover sorts by popularity, which buries exact matches for niche books, so a
# wider page of candidates is fetched and re-ranked by title and author match.
CANDIDATES_PER_SEARCH = 10


def title_similarity(wanted: str, title: str) -> float:
    """Also compares the main title alone ("The Hobbit, or There and Back Again", "Dune: Deluxe")."""
    main_title = re.split(r"[:,(]", title, maxsplit=1)[0]
    return max(SequenceMatcher(None, wanted.lower(), t.lower().strip()).ratio() for t in (title, main_title))


def rank_hits(hits: list[dict], title: str, author: str | None = None) -> list[int]:
    """Orders search hits by title match, plus a bonus for the author, then popularity."""
    def score(document: dict) -> tuple[float, int]:
        points = title_similarity(title, document.get("title") or "")
        if author and any(author.lower() in name.lower() for name in document.get("author_names") or []):
            points += 0.5
        return round(points, 2), document.get("users_count") or 0

    documents = [h["document"] for h in hits if h.get("document", {}).get("id")]
    return [int(d["id"]) for d in sorted(documents, key=score, reverse=True)]


def hits_from_search(response: dict) -> list[dict]:
    return (((response.get("search") or {}).get("results") or {}).get("hits")) or []


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

        self._title_search_query = gql(
        """
          query TitleSearch($q: String!, $limit: Int, $weights: String, $fields: String) {
            search(query: $q, weights: $weights, fields: $fields, sort: "users_count:desc",
                   typos: "2", query_type: "Book", per_page: $limit, page: 1) {
              results
            }
          }
        """
        )

    def search_titles(self, title: str, author: str | None = None, limit: int = 5) -> list[int]:
        weights, fields = TITLE_AUTHOR_WEIGHTS if author else TITLE_ONLY_WEIGHTS
        query = f"{title} {author}" if author else title
        variables = {"q": query.strip(), "limit": CANDIDATES_PER_SEARCH, "weights": weights, "fields": fields}
        hits = hits_from_search(self.transport_layer.execute(self._title_search_query, variables))
        return rank_hits(hits, title, author)[:limit]

    def search(self, variable_values):
        return self.transport_layer.execute(self.BookSearch, variable_values)