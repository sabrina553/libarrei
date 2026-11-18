import json
from pathlib import Path

from graphql import print_ast

from libarrei import normalise
from libarrei.model import Contributor
from libarrei.sources.goodreads.client import Goodreads
from libarrei.sources.goodreads.mapping import work_from_graphql
from libarrei.sources.openlibrary.mapping import other_contributors, to_work

FIXTURES = Path(__file__).parent / "fixtures"
GR_BOOK = json.loads((FIXTURES / "goodreads_book.json").read_text())
OL_WORK = json.loads((FIXTURES / "openlibrary_work.json").read_text())
OL_EDITION = json.loads((FIXTURES / "openlibrary_edition.json").read_text())


def roles(people):
    return [(c.name, c.role) for c in people]


def test_roles_are_canonical_and_ordered():
    raw = [Contributor(name="Reader", role="Reading"), Contributor(name="Lead", role="author"),
           Contributor(name="Artist", role="Cover Art"), Contributor(name="Trans", role="Translation"),
           Contributor(name="Odd", role="printer"), Contributor(name="Co", role="Author"),
           Contributor(name="Ed", role="Editor")]
    assert roles(normalise.contributors(raw)) == [
        ("Lead", "author"), ("Co", "author"), ("Ed", "editor"), ("Trans", "translator"),
        ("Artist", "cover artist"), ("Reader", "narrator"), ("Odd", "printer")]


def test_goodreads_roles_come_from_edges():
    book = {**GR_BOOK,
            "primaryContributorEdge": {"role": "Author", "node": {"legacyId": 1, "name": "A"}},
            "secondaryContributorEdges": [{"role": "Narrator", "node": {"legacyId": 2, "name": "N"}},
                                          {"node": {"legacyId": 3, "name": "C"}}]}
    assert roles(work_from_graphql(book).contributors[0].value) == [
        ("A", "author"), ("N", "narrator"), ("C", "contributor")]


def test_goodreads_query_requests_roles():
    query = print_ast(Goodreads(None)._book_by_legacy_id_query.document)
    assert "primaryContributorEdge {\n      role" in query
    assert "secondaryContributorEdges {\n      role" in query


def test_openlibrary_structured_contributors():
    doc = {"contributors": [{"role": "Translator", "name": "T One"}, {"role": "Cover Art", "name": "C"}]}
    assert roles(other_contributors(doc)) == [("T One", "translator"), ("C", "cover art")]


def test_openlibrary_contributions_need_a_role():
    doc = {"contributions": ["Rob Inglis (Narrator)", "Lee, Alan, 1947-", "Author (Illustrator)"]}
    assert roles(other_contributors(doc)) == [("Rob Inglis", "narrator")]
    edition = to_work(OL_WORK, [{**OL_EDITION, **doc}], {"/authors/OL1515577A": "Ann Napolitano"}).editions[0]
    assert [c.name for c in edition.contributors[0].value] == ["Ann Napolitano", "Rob Inglis"]
