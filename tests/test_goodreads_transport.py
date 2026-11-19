from gql.transport.exceptions import TransportQueryError

from libarrei.sources.goodreads.transport import TransportLayer, missing_items_only

DELETED = {"errorType": "RESOURCE_NOT_FOUND", "message": "book not found (maybe deleted, and no replacement exists)."}
PARTIAL = {"getSearchSuggestions": {"edges": [{"node": {"webUrl": "https://www.goodreads.com/book/show/1"}}, None, {"node": None}]}}


class FailingClient:
    def __init__(self, error):
        self.error = error

    def execute(self, query, variable_values=None):
        raise self.error


def layer(error) -> TransportLayer:
    transport = TransportLayer.__new__(TransportLayer)
    transport.client = FailingClient(error)
    return transport


def test_search_with_a_deleted_book_keeps_the_other_results():
    assert layer(TransportQueryError("x", errors=[DELETED], data=PARTIAL)).execute("q") == PARTIAL


def test_other_errors_still_raise():
    import pytest

    with pytest.raises(TransportQueryError):
        layer(TransportQueryError("x", errors=[{"errorType": "Unauthorized"}], data=PARTIAL)).execute("q")
    assert not missing_items_only(TransportQueryError("x", errors=[DELETED], data=None))
