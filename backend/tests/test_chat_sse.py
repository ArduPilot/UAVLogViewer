from fastapi.testclient import TestClient

from app.main import app
from app.models.memory import memory_store


client = TestClient(app)


def seed_session():
    return memory_store.create_or_get(None, {
        "meta": {"duration_s": 1100},
        "extrema": {"max_altitude_m": 121.4, "max_altitude_t": 482.3},
        "gps": {"loss_intervals": [{"start": 615.2, "end": 640.8}]},
        "series_opt": {
            "ALT": [[0,0],[120,30],[480,121.4]],
            "HDOP": [[600,1.8],[620,3.2]]
        }
    }, None)


def test_chat_sse_stream_basic():
    sid = seed_session()
    with client.stream("POST", "/api/chat", json={"session_id": sid, "message": "What is the max altitude?"}) as r:
        assert r.status_code == 200
        # consume a few events
        body = b"".join(list(r.iter_raw(chunk_size=1024))[:2])
        assert b"event: message" in body or b"event: tool_result" in body


def test_chat_sse_docs_lookup():
    with client.stream("POST", "/api/chat", json={"session_id": "noop", "message": "What is AHR2?"}) as r:
        # no session needed for docs
        assert r.status_code == 200
        raw = b"".join(list(r.iter_raw(chunk_size=1024))[:2])
        # We may not fetch network, but we should get at least a message back
        assert b"event: message" in raw or b"event: tool_result" in raw


