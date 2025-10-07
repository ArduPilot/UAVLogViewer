# UAV Logger Backend (FastAPI)

Minimal backend to support an agentic chatbot for UAV flight logs. MVP endpoints:
- GET `/api/health` – health check
- POST `/api/session/bootstrap` – cache client-parsed flight summary and receive a `session_id`

SSE chat and agent wiring will follow in subsequent steps.

## Prerequisites
- Python 3.11+ (recommended)
- macOS/Linux: bash/zsh shell
- Optional: Docker

## Quick Start (Local)
1) Create and activate a virtual environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies
```bash
pip install -r requirements.txt
```

3) Run the server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4) Verify it’s up
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{"status":"ok","version":"0.1.0","model":"gpt-4o-mini"}
```

## Endpoints
### Health
```http
GET /api/health
```
Response 200:
```json
{"status":"ok","version":"0.1.0","model":"gpt-4o-mini"}
```

### Session Bootstrap
Cache a compact, client-parsed flight summary to associate with a chat `session_id`.
```http
POST /api/session/bootstrap
Content-Type: application/json
```
Example request:
```json
{
  "summary": {
    "meta": { "start_time": "2025-10-05T10:00:00Z", "end_time": "2025-10-05T10:18:20Z", "duration_s": 1100, "vehicle": "quadcopter" },
    "extrema": { "max_altitude_m": 121.4, "max_altitude_t": 482.3, "min_voltage_v": 10.7, "min_voltage_t": 910.2 },
    "gps": { "first_fix_t": 12.4, "loss_intervals": [{ "start": 615.2, "end": 640.8 }], "worst_hdop": { "value": 3.2, "t": 618.9 } },
    "battery": { "max_temp_c": 48.0, "max_temp_t": 780.5 },
    "errors": [{ "t": 742.1, "severity": "CRITICAL", "code": "EKF", "msg": "EKF variance increased" }],
    "timeline": [{ "t": 95.0, "from": "STABILIZE", "to": "ALT_HOLD" }],
    "series_opt": {
      "ALT": [[0,0],[120,30],[480,121.4],[960,12]],
      "VOLT": [[0,12.3],[800,10.9],[900,10.7],[1000,11.0]],
      "HDOP": [[580,1.1],[620,3.2],[640,1.4]]
    }
  }
}
```
Response 200:
```json
{"session_id":"<uuid>"}
```

Notes:
- No raw `.bin` files are uploaded for the MVP.
- The summary should be compact; include only essential metrics and small downsampled series.

## Environment Variables
Add a `.env` file in `backend/` (optional for now):
```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```
- These will be used when the chat agent is introduced.

## Run Tests
From repo root (or `backend/`), using the venv:
```bash
# From repo root
source backend/.venv/bin/activate
PYTHONPATH=backend python -m pytest -q backend/tests

# Or from backend directory
cd backend
source .venv/bin/activate
pytest -q tests
```

## Docker
Build and run the backend with Docker:
```bash
# From repo root
docker build -t uav-backend ./backend

# Run
docker run --rm -p 8000:8000 --env-file backend/.env uav-backend
```

Then hit `http://localhost:8000/api/health`.

## Roadmap (MVP)
- SSE `/api/chat` and LangGraph agent tooling
- Tools: `telemetry_query`, `anomaly_scan` (already implemented server-side), `docs_lookup`
- Minimal frontend chat panel with SSE
