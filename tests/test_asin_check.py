import pytest

from libarrei.asin_check import MAX_CHECKS, AsinStatus, Unavailable, check_all, check_edition, same_product
from libarrei.lookup import make_probe
from libarrei.merge import merge
from libarrei.model import Contributor, Edition, Source, Work

HC, AU, AZ = Source.HARDCOVER, Source.AUDIBLE, Source.AMAZON
CARL = {"title": "Dungeon Crawler Carl", "authors": ["Matt Dinniman"]}


def audiobook(source: Source, asin: str, isbn: str = "9780000000002") -> Work:
    edition = Edition()
    edition.add("title", "Dungeon Crawler Carl", source, asin)
    edition.add("contributors", [Contributor(name="Matt Dinniman")], source, asin)
    edition.add("asin", asin, source, asin)
    edition.add("isbn13", isbn, source, asin)
    edition.add("format", "audiobook", source, asin)
    return Work(editions=[edition])


def merged_edition(hc_asin: str, store: Source = AU, store_asin: str = "B0DM68J1PP"):
    [edition] = merge({HC: audiobook(HC, hc_asin), store: audiobook(store, store_asin)}).editions
    return edition


def fake_store(products: dict):
    calls = []

    def probe(store, asin):
        calls.append((store, asin))
        return products.get(asin)
    return probe, calls


def test_unknown_asin_is_not_found():
    # Mirrors Hardcover edition 32146161, whose B0DM64FRQW is not on Audible.
    probe, _ = fake_store({"B0DM68J1PP": CARL})
    assert check_edition(merged_edition("B0DM64FRQW"), probe) == {"B0DM64FRQW": AsinStatus.NOT_FOUND}


def test_same_product_listing_is_valid():
    probe, _ = fake_store({"B0DM68J1PP": CARL, "B0OTHER001": {**CARL, "title": "Dungeon Crawler Carl: A LitRPG"}})
    assert check_edition(merged_edition("B0OTHER001"), probe) == {"B0OTHER001": AsinStatus.SAME_PRODUCT}


def test_other_product():
    probe, _ = fake_store({"B0DM68J1PP": CARL, "B0OTHER001": {"title": "Carl's Doomsday Scenario", "authors": ["Matt Dinniman"]}})
    assert check_edition(merged_edition("B0OTHER001"), probe) == {"B0OTHER001": AsinStatus.OTHER_PRODUCT}


def test_agreeing_asin_is_not_checked():
    probe, calls = fake_store({})
    assert check_edition(merged_edition("B0DM68J1PP"), probe) == {} and calls == []


def test_unavailable_store_reports_nothing():
    def probe(store, asin):
        raise Unavailable()
    assert check_edition(merged_edition("B0X", store=AZ), probe) == {}


def test_check_all_respects_budget():
    editions = [merged_edition(f"B0HC{i:06}") for i in range(MAX_CHECKS + 3)]
    probe, _ = fake_store({"B0DM68J1PP": CARL})
    check_all(editions, probe)
    assert sum(len(e.asin_checks) for e in editions) == MAX_CHECKS


@pytest.mark.parametrize("a, b, same", [
    (CARL, {"title": "Dungeon Crawler Carl (French Edition)", "authors": ["Matt Dinniman"]}, True),
    (CARL, {"title": "Dungeon Crawler Carl", "authors": ["Someone Else"]}, False),
    (CARL, {"title": "Dungeon Crawler Carl", "authors": []}, True),
])
def test_same_product(a, b, same):
    assert same_product(a, b) is same


def test_lookup_api_reports_asin_checks(monkeypatch):
    from fastapi.testclient import TestClient

    from libarrei import api
    from libarrei.lookup import LookupResult
    works = {HC: audiobook(HC, "B0DM64FRQW"), AU: audiobook(AU, "B0DM68J1PP")}
    probe, _ = fake_store({"B0DM68J1PP": CARL})
    monkeypatch.setattr(api, "lookup", lambda **_: LookupResult(works=works, probe=probe))
    body = TestClient(api.app).get("/v1/lookup", params={"title": "carl"}).json()
    assert body["work"]["editions"][0]["asin_checks"] == {"B0DM64FRQW": "not_found"}


class FakeAudible:
    def __init__(self):
        self.calls = 0

    def product(self, asin):
        self.calls += 1
        return {"title": "T", "authors": [{"name": "A"}]} if asin == "B1" else None


def test_probe_memoises_and_needs_cookie_for_amazon():
    audible = FakeAudible()
    probe = make_probe(audible, None)
    assert probe(AU, "B1") == {"title": "T", "authors": ["A"]}
    assert probe(AU, "B1") and audible.calls == 1
    assert probe(AU, "B2") is None
    with pytest.raises(Unavailable):
        probe(AZ, "B1")


def test_stores_that_lacked_the_asin_are_recorded():
    edition = merged_edition("B0DT38PQYW", AZ, "B08BKGYQXW")
    answers = {"B08BKGYQXW": {**CARL, "found_on": "co.uk"}, "B0DT38PQYW": {"missing_from": ["co.uk", "com", "ca"]}}
    assert check_edition(edition, lambda store, asin: answers[asin]) == {"B0DT38PQYW": AsinStatus.NOT_FOUND}
    assert edition.asin_stores == {"B0DT38PQYW": ["co.uk", "com", "ca"]}


def test_asin_found_on_another_store_is_the_same_product():
    edition = merged_edition("B0USONLY01", AZ, "B08BKGYQXW")
    answers = {"B08BKGYQXW": {**CARL, "found_on": "co.uk"}, "B0USONLY01": {**CARL, "found_on": "com"}}
    assert check_edition(edition, lambda store, asin: answers[asin]) == {"B0USONLY01": AsinStatus.SAME_PRODUCT}
    assert edition.asin_stores == {"B0USONLY01": ["com"]}
