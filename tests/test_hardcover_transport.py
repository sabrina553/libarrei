import pytest
from gql.transport.exceptions import TransportServerError

from libarrei.sources.hardcover.transport import MAX_RETRIES, TransportLayer


class FakeClient:
    def __init__(self, failures, code=429):
        self.failures, self.code, self.calls = failures, code, 0

    def execute(self, query, variable_values=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise TransportServerError("throttled", self.code)
        return {"ok": True}


def transport_with(client):
    waits = []
    transport = TransportLayer("token", sleep=waits.append)
    transport.client = client
    return transport, waits


def test_retries_429_with_doubling_backoff():
    transport, waits = transport_with(FakeClient(failures=2))
    assert transport.execute("query") == {"ok": True}
    assert waits == [1.0, 2.0]


def test_gives_up_after_max_retries():
    transport, waits = transport_with(FakeClient(failures=MAX_RETRIES + 1))
    with pytest.raises(TransportServerError):
        transport.execute("query")
    assert len(waits) == MAX_RETRIES


def test_other_errors_are_not_retried():
    transport, waits = transport_with(FakeClient(failures=1, code=401))
    with pytest.raises(TransportServerError):
        transport.execute("query")
    assert waits == []


class CountingLimiter:
    def __init__(self):
        self.calls = 0

    def wait(self):
        self.calls += 1


def test_cache_hit_skips_network_and_rate_limit():
    from libarrei.cache import Cache

    limiter = CountingLimiter()
    transport = TransportLayer("token", cache=Cache(":memory:"), limiter=limiter)
    transport.client = client = FakeClient(failures=0)
    assert transport.execute("query", {"b": 1, "a": 2}) == {"ok": True}
    assert transport.execute("query", {"a": 2, "b": 1}) == {"ok": True}
    assert client.calls == 1 and limiter.calls == 1
