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



def test_file_cache_works_across_threads(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    cache = Cache(tmp_path / "c.sqlite3")
    with ThreadPoolExecutor(3) as pool:
        list(pool.map(lambda i: cache.put("s", str(i), {"i": i}), range(9)))
    assert [cache.get("s", str(i)) for i in range(9)] == [{"i": i} for i in range(9)]
