from libarrei.cache import Cache


def test_cache_returns_stored_body_until_it_expires():
    now = [0.0]
    cache = Cache(":memory:", max_age=10, clock=lambda: now[0])
    calls = []
    load = lambda: calls.append(1) or {"a": 1}

    assert cache.fetch("hardcover", "q", load) == {"a": 1}
    assert cache.fetch("hardcover", "q", load) == {"a": 1}
    assert len(calls) == 1
    now[0] = 11
    cache.fetch("hardcover", "q", load)
    assert len(calls) == 2


def test_cache_does_not_store_missing_results():
    cache = Cache(":memory:")
    cache.fetch("openlibrary", "x", lambda: None)
    assert cache.get("openlibrary", "x") is None

