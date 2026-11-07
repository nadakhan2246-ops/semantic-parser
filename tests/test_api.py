import pytest
from database import database as db

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    from app import app
    return app.test_client()

def test_empty_input(client):
    r = client.post("/api/analyze", json={"text": "   "})
    assert r.status_code == 400 and r.get_json()["success"] is False

def test_analyze_and_history(client):
    r = client.post("/api/analyze", json={"text": "Show me the weather in Hyderabad."})
    d = r.get_json()
    assert d["success"] and d["result"]["intent"]["intent"] == "GET_WEATHER"
    assert len(client.get("/api/history").get_json()["history"]) == 1
    assert client.get(f"/api/history/{d['history_id']}").get_json()["success"]
    client.delete("/api/history")
    assert client.get("/api/history").get_json()["history"] == []

def test_missing_entry(client):
    assert client.get("/api/history/999").status_code == 404


def test_homepage_and_static_assets(client):
    assert client.get("/").status_code == 200
    for path in ["/static/style.css", "/static/script.js", "/static/assets/logo.svg"]:
        assert client.get(path).status_code == 200


def test_health_and_examples(client):
    assert client.get("/api/health").get_json()["status"] == "ok"
    d = client.get("/api/examples").get_json()
    assert len(d["examples"]) >= 6 and len(d["pipeline"]) == 8


def test_invalid_requests_are_handled(client):
    assert client.post("/api/analyze", data="not json", content_type="application/json").status_code == 400
    assert client.post("/api/analyze", json=[1, 2]).status_code == 400
    assert client.post("/api/analyze", json={"text": 123}).status_code == 400
    assert client.post("/api/analyze", json={}).status_code == 400
    assert client.post("/api/analyze", json={"text": "x" * 501}).status_code == 400
    assert client.get("/api/analyze").status_code == 405
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json()["success"] is False


def test_odd_inputs_do_not_crash(client):
    for text in ["<script>alert(1)</script>", "'; DROP TABLE history; --", "😀 emoji ✓", "a\nb\tc", "?"]:
        assert client.post("/api/analyze", json={"text": text}).status_code == 200
    assert len(client.get("/api/history").get_json()["history"]) == 5


def test_history_order_newest_first(client):
    client.post("/api/analyze", json={"text": "Hello"})
    client.post("/api/analyze", json={"text": "Show me the weather in Delhi"})
    h = client.get("/api/history").get_json()["history"]
    assert h[0]["sentence"].startswith("Show me") and h[1]["sentence"] == "Hello"


def test_history_total_counts_everything_not_just_the_page(client):
    for i in range(55):
        db.insert(f"sentence {i}", "UNKNOWN", {"original": f"sentence {i}", "intent": {"intent": "UNKNOWN"}})
    d = client.get("/api/history").get_json()
    assert d["total"] == 55 and len(d["history"]) == 50 and d["history"][0]["sentence"] == "sentence 54"


def test_history_survives_an_application_restart(client, tmp_path, monkeypatch):
    client.post("/api/analyze", json={"text": "Show me the weather in Delhi"})
    db.init_db()                                   # what app start-up does again after a restart (must not wipe data)
    h = client.get("/api/history").get_json()["history"]
    assert len(h) == 1 and h[0]["sentence"] == "Show me the weather in Delhi"


def test_analysis_is_returned_even_if_saving_history_fails(client, monkeypatch):
    import sqlite3
    from backend import history_manager

    def broken(_result): raise sqlite3.OperationalError("disk full")
    monkeypatch.setattr(history_manager, "save_analysis", broken)
    r = client.post("/api/analyze", json={"text": "Hello"})
    d = r.get_json()
    assert r.status_code == 200 and d["success"] and d["history_id"] is None and "could not be saved" in d["warning"]


def test_history_routes_report_database_failure_as_json(client, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path))          # a folder is not a database file
    for r in (client.get("/api/history"), client.get("/api/history/1"), client.delete("/api/history")):
        assert r.status_code == 500 and r.get_json()["success"] is False
