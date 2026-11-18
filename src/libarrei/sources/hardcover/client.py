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
    """Also compares the main title alone ("The Hobbit, or There and Back Again", "Dune: Deluxe")
    and the part after a series prefix ("Mistborn: The Final Empire")."""
    variants = [title, re.split(r"[:,(]", title, maxsplit=1)[0]]
    if ":" in title:
        variants.append(re.sub(r"\s*\(.*?\)", "", title.split(":", 1)[1]))
    return max(SequenceMatcher(None, wanted.lower(), t.lower().strip()).ratio() for t in variants)


def rank_hits(hits: list[dict], title: str, author: str | None = None) -> list[int]:
    """Orders search hits by title match, plus a bonus for the author, then popularity."""
    def score(document: dict) -> tuple[float, int]:
        found = document.get("title") or ""
        points = title_similarity(title, found)
        # Without this, split volumes such as "The Final Empire (2 of 3)" tie with
        # the real book on their main title and win on popularity.
        if found.strip().lower() == title.strip().lower():
            points += 0.1
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
              book_series {
                position
                series {
                  name
                }
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
                edition_information
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

        # Fields mirror BookSearch's editions so mapping.to_edition works unchanged.
        # A stable order is needed so offset pages neither skip nor repeat editions.
        self._editions_query = gql(
        """
          query BookEditions($id: Int!, $limit: Int!, $offset: Int!) {
            editions(where: {book_id: {_eq: $id}}, limit: $limit, offset: $offset, order_by: {id: asc}) {
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
              edition_information
              score
            }
          }
        """
        )

    def all_editions(self, book_id: int, page_size: int = 100) -> list[dict]:
        """Every edition of a book in any language, paged until a short page."""
        editions, offset = [], 0
        while True:
            variables = {"id": book_id, "limit": page_size, "offset": offset}
            page = self.transport_layer.execute(self._editions_query, variables).get("editions") or []
            editions.extend(page)
            if len(page) < page_size:
                return editions
            offset += page_size

    def search_titles(self, title: str, author: str | None = None, limit: int = 5) -> list[int]:
        weights, fields = TITLE_AUTHOR_WEIGHTS if author else TITLE_ONLY_WEIGHTS
        query = f"{title} {author}" if author else title
        variables = {"q": query.strip(), "limit": CANDIDATES_PER_SEARCH, "weights": weights, "fields": fields}
        hits = hits_from_search(self.transport_layer.execute(self._title_search_query, variables))
        return rank_hits(hits, title, author)[:limit]

    def search(self, variable_values):
        return self.transport_layer.execute(self.BookSearch, variable_values)