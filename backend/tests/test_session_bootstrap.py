from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_bootstrap_creates_session():
    payload = {
        "summary": {"duration_s": 1234, "max_altitude_m": 120.5},
        "signals": {"ALT": [[0, 0], [1, 10]]},
    }
    r = client.post("/api/session/bootstrap", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "session_id" in data
    assert isinstance(data["session_id"], str)


def test_bootstrap_idempotent_with_client_session_id():
    payload = {
        "client_session_id": "abc123",
        "summary": {"duration_s": 5},
    }
    r1 = client.post("/api/session/bootstrap", json=payload)
    r2 = client.post("/api/session/bootstrap", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["session_id"] == r2.json()["session_id"]


