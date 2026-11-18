import pytest
from fastapi.testclient import TestClient

from libarrei import api
from libarrei.golden import GOLDEN_DIR, load_works
from libarrei.lookup import LookupResult

client = TestClient(api.app)


@pytest.fixture
def hello_beautiful(monkeypatch):
    works = load_works(GOLDEN_DIR / "hello-beautiful")
    monkeypatch.setattr(api, "lookup", lambda **_: LookupResult(works=works))


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_metadata_uses_grimmory_field_names(hello_beautiful):
    body = client.get("/v1/metadata", params={"isbn": "978-0-593-24373-2"}).json()
    assert body["isbn13"] == "9780593243732"
    assert body["title"] == "Hello Beautiful"
    assert body["authors"] == ["Ann Napolitano"]
    assert body["publishedDate"].startswith("2023")
    assert {"goodreadsId", "hardcoverBookId", "openlibraryId", "categories"} <= body.keys()


def test_lookup_returns_merged_record(hello_beautiful):
    body = client.get("/v1/lookup", params={"title": "hello beautiful"}).json()
    assert body["work"]["fields"]["title"]["value"] == "Hello Beautiful"
    assert body["work"]["editions"]


def test_missing_query_is_rejected():
    assert client.get("/v1/metadata").status_code == 422


def test_not_found_is_404(monkeypatch):
    monkeypatch.setattr(api, "lookup", lambda **_: LookupResult(notes={}))
    assert client.get("/v1/metadata", params={"isbn": "0000000000"}).status_code == 404
