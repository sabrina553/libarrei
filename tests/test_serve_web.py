import importlib

from fastapi.testclient import TestClient


def test_gui_routes_fall_back_to_index_and_api_still_wins(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>gui</html>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "secret.txt").write_text("nope")
    monkeypatch.setenv("LIBARREI_WEB_DIR", str(tmp_path))

    from libarrei import api
    client = TestClient(importlib.reload(api).app)

    assert client.get("/book?isbn=1").text == "<html>gui</html>"
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/health").json() == {"status": "ok"}
    # Paths escaping the build folder get the GUI, never the file.
    assert "nope" not in client.get("/..%2Fsecret.txt").text

    monkeypatch.delenv("LIBARREI_WEB_DIR")
    importlib.reload(api)
