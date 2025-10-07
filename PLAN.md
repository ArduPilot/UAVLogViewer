## Plan: Extend UAV Log Viewer with an Agentic Chatbot Backend

### MVP Scope (5–6 hours)
- Backend: FastAPI with `/api/health`, `/api/session/bootstrap`, and SSE `/api/chat` only.
- Chatbot: LangGraph agent using OpenAI (default `gpt-4o-mini`), with two tools:
  - `telemetry_query` (answer max altitude, GPS loss time, flight time, basic stats)
  - `anomaly_scan` (simple z-score/change-rate checks on altitude, GPS fix/HDOP, battery voltage)
- Frontend: Minimal `ChatPanel` with SSE streaming; send client-parsed summary via `bootstrap`.
- Docs: Optional link out; skip full retrieval/indexing for MVP.
- Stretch (time permitting): richer anomaly analytics, jump-to-time links, docs retrieval.

### Goals
- Add a backend service that enables an agentic chatbot to answer questions about uploaded ArduPilot DataFlash `.bin` flight logs and reason about anomalies.
- Keep the existing app flow (upload → parse → visualize) intact and add a chat experience to the UI.
- Use OpenAI SDK directly; prefer low-cost models (e.g., `gpt-4o-mini`).
- Avoid persisting user-uploaded telemetry data in the repository; use ephemeral storage in-memory or `/tmp` with TTL.
- Ship with clear run instructions and a short demo flow; optimize for ease of review (install, run, test).

### Architecture Overview
- Frontend (existing): Vue app in this repository. We'll add a chat panel integrated with the existing uploader and flight context.
- Backend (new): Python FastAPI app exposing:
  - Session bootstrap endpoint that accepts client-parsed summaries (no backend file upload for MVP).
  - Chat endpoint (SSE) that hosts an agent which can call tools to query telemetry and detect anomalies.
  - Ephemeral session state for conversation memory and cached summaries.
- LLM and Retrieval:
  - OpenAI SDK directly (configurable model, default `gpt-4o-mini`).
  - Lightweight docs retrieval at runtime: fetch and cache relevant sections from `https://ardupilot.org/plane/docs/logmessages.html`; optional small in-memory embeddings via LangChain for snippet selection; do not commit any prebuilt index.

### Key Frameworks and Libraries
- Backend: FastAPI, Uvicorn, Pydantic
- Agent/LLM: LangChain + LangGraph for tool orchestration; models via OpenAI SDK
- Parsing: `pymavlink` (DataFlash `.bin` parsing)
- Data/Math: `numpy`, `pandas` (summaries), optional `scipy`; optional `ruptures` for change-point detection
- Streaming: Server-Sent Events via `sse-starlette`
- Storage: In-memory + `/tmp` filesystem with TTL cleanup; optional Redis for sessions (stretch)
- DevOps: Dockerfile for backend; combined dev run (frontend + backend) via npm scripts or `make`

### Proposed Backend API
- POST `/api/session/bootstrap`
  - Body: `{ client_session_id?, summary, signals? }` where `summary` is the client-parsed overview (duration, extrema, key events) and optional lightweight downsampled series for fast queries.
  - Caches flight context server-side under a new `session_id` (or reuses provided `client_session_id`).
  - Returns: `{ session_id }`.

- GET `/api/telemetry/summary?file_id=...`
  - Returns computed overview: duration, altitude stats, GPS lock events, battery stats, RC loss events, error codes.

- GET `/api/telemetry/timeseries?file_id=...&signals=ALT,GPS_HDOP,...&downsample=2`
  - Returns selected time series for visualization or agent tooling. Downsampled for bandwidth.

- POST `/api/chat` (SSE stream)
  - Body: `{ session_id, message }`.
  - Streams assistant tokens. The agent can call tools:
    - `telemetry_query`: compute metrics from the parsed log (max altitude, GPS loss time, etc.).
    - `anomaly_scan`: run lightweight analytics and summarize suspected anomalies.
    - `docs_lookup`: retrieve relevant ArduPilot log message docs.
  - Maintains conversation state keyed by `session_id`.

- GET `/api/health`
  - Returns `{ status: 'ok' }`.

### Data Model and Session Lifecycle
- `session_id` identifies a chat session and its memory plus cached flight context.
- No backend file storage in MVP; the frontend parses `.bin` and sends summaries (and optionally downsampled series) via `/api/session/bootstrap`.
- Cached artifacts live in-memory (and optionally temp disk) with a TTL (e.g., 24 hours) and periodic cleanup.
- In-memory maps store: conversation history (compact), flight summaries, optional time series, and indexes.

### Telemetry Parsing Strategy (ArduPilot DataFlash)
- Use `pymavlink` DataFlash log reader to parse key message types:
  - `GPS`: fix status, HDOP, NSats, time of first fix, loss events
  - `BARO` / `AHR2` / `ALT`/`POS` (as available): altitude, climb rate
  - `BAT` or `CURR`: voltage, current, temperature (if present), energy consumption
  - `ERR`: error codes, severities, times
  - `MODE`: mode changes and timestamps
  - `RCIN`/`RCOU`: link/signal anomalies
  - `EV`, `MSG`: general events/messages
- Build a normalized frame with timestamps and keys. Cache both a compact summary (stats, extrema, events) and access to downsampled time series.
- Ensure parsing is resilient to missing fields across firmware variants; prefer feature detection.

### Agent Design
- Orchestrator: LangGraph-based tool-using agent that:
  1) Reads user intent, 2) Calls `telemetry_query` and/or `anomaly_scan` as needed, 3) Optionally cites relevant docs via `docs_lookup`, 4) Responds succinctly with structured findings and human-readable explanation.
- Memory: Conversation buffer per `session_id`, compacted to fit context windows.
- Tooling Contracts:
  - `telemetry_query(params)` → metrics like max altitude, GPS loss intervals, battery max temperature, total flight time, error list, first RC loss time, etc.
  - `anomaly_scan(params)` → runs hybrid detection: change-point detection for sharp deltas, low-voltage sags, GPS inconsistencies, EKF variance spikes (if present), inconsistent altitude vs baro, etc.; returns scored findings with timestamps.
  - `docs_lookup(query)` → short excerpts + URLs from ArduPilot docs for message meanings and fields.
- Prompting Principles:
  - Encourage reasoning over rigid thresholds: “Look for sudden changes and inconsistent patterns” rather than hardcoded rules.
  - Ask clarifying questions when file context is missing or when multiple interpretations exist.
  - Include citations to telemetry events (timestamps, message types) in answers when possible.

### Frontend Integration
- UI: Add a Chat panel (right-docked drawer or tab) in the existing app.
  - When a `.bin` is uploaded, show “Flight loaded” context (file name, duration, takeoff time), and enable chat.
  - Stream assistant responses (SSE) with typing indicator.
  - Add quick suggestions (chips) for common questions.
  - Show inline metrics snippets (e.g., max altitude) with timestamps and links to jump the plot to that time.
- Data Flow:
  - On upload: existing app parses the `.bin`; send `{ summary, signals? }` to `/api/session/bootstrap` and keep `session_id`.
  - For chat: send `{ session_id, message }` to `/api/chat` and render streamed tokens.
  - Optional: Use `/api/telemetry/summary` to pre-populate context cards (or rely on client copy).

### Anomaly Detection Approach (Hybrid)
- Lightweight server-side analytics to surface candidate anomalies without rigid rules:
  - Robust z-scores on rate-of-change (altitude, voltage, current, speed).
  - Change-point detection on key series (altitude, voltage) via `ruptures` (if included) or custom segmented variance checks.
  - GPS health: detect large jumps in position, prolonged HDOP degradation, loss/reacquisition periods.
  - Battery health: voltage sags under load, temperature spikes.
- The agent converts findings to user-facing explanations and may ask for confirmation or additional queries.

### Privacy and Security
- Do not store uploaded files in the repository. Add `/tmp/uav-uploads/` to `.gitignore`.
- Enforce upload limits and type checks on the backend.
- Redact personally identifiable info in logs. Disable verbose logs in production.
- Provide env vars for API keys; do not hardcode secrets.

### Project Structure (to be added)
```
backend/
  app/
    main.py                # FastAPI app entrypoint
    routers/
      session.py           # /api/session/* (bootstrap)
      telemetry.py         # /api/telemetry/*
      chat.py              # /api/chat (SSE)
    services/
      telemetry_parser.py  # pymavlink parsing + summaries
      anomaly.py           # analytics and anomaly detection
      agent.py             # agent orchestration, tools
      docs.py              # lightweight retrieval/caching for docs
    models/
      memory.py            # session memory store
    schemas.py             # pydantic models
  requirements.txt
  Dockerfile

frontend/ (existing)
  src/components/ChatPanel.vue (new)
  src/services/chat.ts (new)
```

### Milestones
1) Backend scaffold (FastAPI, health, config, Dockerfile)
2) `/api/session/bootstrap` to accept client-parsed summary (no backend upload)
3) SSE `/api/chat` using OpenAI + LangGraph agent with `telemetry_query` and `anomaly_scan`
4) Frontend `ChatPanel` + SSE integration; wire `bootstrap`
5) README updates; demo instructions
6) Stretch: telemetry endpoints, docs retrieval, jump-to-time links, tests

### Testing Strategy
- Unit tests for telemetry parsing on small, anonymized `.bin` snippets.
- Golden answers for known logs (max altitude, GPS loss times).
- Contract tests for API responses.
- Manual E2E: upload a sample bin, ask exemplar questions, verify answers + timestamps.

### Local Development and Env
- Backend: `uvicorn backend.app.main:app --reload` (or via `make dev`)
- Frontend: existing dev server; add `.env` with `VITE_BACKEND_URL`.
- Env vars:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL=gpt-4o-mini`

### Deliverables
- Working backend integrated with the existing app.
- Clear README updates with setup and run instructions.
- Short demo video showing: upload, chatbot Q&A, anomaly reasoning.

### Stretch Ideas (time-permitting)
- Visual anomaly overlays on plots with hover details.
- Multi-log comparison: “Compare this flight to the previous one”.
- Vector search over user’s past flights (with opt-in persistence), anonymized.
- Exportable chat transcript with citations to timestamps.

### Decisions
- Transport: SSE-only for streaming assistant tokens.
- Session context: Client-side parsing; backend caches compact summary via `/api/session/bootstrap` (no backend file storage for MVP).
- Agent framework: LangChain + LangGraph for tool orchestration and control flow.
- Docs retrieval: Lightweight runtime fetch + cache of ArduPilot docs; optional in-memory embeddings; no prebuilt FAISS committed.

### Implementation Checklist
- [x] Scaffold FastAPI backend with `/api/health`, config, and Dockerfile
- [x] Implement `/api/session/bootstrap` to cache client-parsed summary; return `{ session_id }`
- [ ] Add minimal `telemetry_query` over cached summary (max altitude, GPS loss, flight time)
- [ ] Add minimal `anomaly_scan` (z-score/change-rate on altitude, GPS fix/HDOP, battery)I
- [ ] Add SSE `/api/chat` and wire LangGraph agent (OpenAI `gpt-4o-mini`)
- [ ] Frontend `ChatPanel.vue` and `src/services/chat.ts` with SSE; wire bootstrap
- [ ] README updates and `.env` guidance
- [ ] Stretch: telemetry endpoints, docs retrieval, jump-to-time links, tests

## MVP+ Phase: Robust Telemetry Aggregation and Agent Context (v0.2)

Goal: Make answers reliable across DataFlash (.bin) and MAVLink tlog by normalizing signals, computing features once, and exposing a stable schema for the agent tools. Keep prompts small; send only structured results.

Architecture changes
- Canonical telemetry representation
  - Introduce a source-agnostic adapter that produces a RawTelemetry map:
    - keys are canonical signal names (ALT, VOLT, HDOP, SPEED, RC_RSSI)
    - each value is `{ time_s: number[], values: number[] }`
    - unify time keys across inputs (time_boot_ms, TimeUS, timeMS, etc.)
- Signal registry (extraction map)
  - For each canonical signal, define an ordered fallback chain per source type:
    - ALT: AHR2.Alt → GPS.Alt (DF) → GLOBAL_POSITION_INT.relative_alt → VFR_HUD.alt (tlog)
    - VOLT: POWER_STATUS.Vcc (tlog) → BATTERY_STATUS.voltages → DF power fields (e.g., BAT.Volt)
    - HDOP: GPS.Hdop (DF) → GPS_RAW_INT.eph (approx) → other GPS quality fields
    - SPEED: VFR_HUD.groundspeed → GPS.Spd → POS.Spd (DF)
    - RC_RSSI: RC_CHANNELS RSSI or failsafe indicators (STATUSTEXT/EV/PM); also derive loss intervals
  - Each extractor returns `{ time_s[], values[] }` or `null` if not found

Feature library (computed once)
- Per-signal features: min/max, times of extrema, mean/median, slope stats, peaks
- Intervals: GPS fix-loss (<3), RC failsafe, voltage sag segments (below threshold), mode change timeline
- Anomaly candidates: altitude rate spikes, low voltage windows, high HDOP, each with score/span

Summary schema v0.2 (cached per session)
- `schema_version: "0.2"`
- `meta`: duration_s, vehicle, start_time
- `extrema`: `max_altitude_m`, `max_altitude_t`, `min_voltage_v`, `min_voltage_t`
- `stats`: small aggregates per signal (mean, min, max)
- `timeline`: mode change events
- `gps`: `loss_intervals: [{start,end}]`, worst_hdop
- `rc`: `loss_intervals: [{start,end}]` (if derivable)
- `battery`: `min_voltage_v`, sags count
- `series_opt`: downsampled ALT, VOLT, HDOP, SPEED, RC_RSSI (≤300 pts each)
- `coverage`: which signals/fields were found (for UI/tool confidence)

Tool updates
- `telemetry_query` reads `extrema`/`stats` first, then computes from `series_opt` with optional `{from_t,to_t}` windows; returns `confidence` and `coverage` hints.
- `anomaly_scan` uses the feature library; supports `{signals:[], window_s, sensitivity}`; returns findings with spans and scores.

Observability & dev UX
- Debug flag (localStorage `uav.debug=true`) to emit coverage, counts, and first/last timestamps per signal during bootstrap.
- Optional `/api/session/debug` to return current cached summary for inspection.

Acceptance criteria
- On both sample tlog and typical DataFlash .bin:
  - max altitude, flight time, GPS first loss are non-null when signals exist.
  - Voltage anomalies appear when VOLT exists; otherwise empty with coverage reason.
  - RC loss intervals populated when derivable; otherwise explicit null.

Next steps
1) Add `src/services/telemetryRegistry.js` with ALT/VOLT/HDOP/SPEED/RC_RSSI extractors (DF + tlog fallbacks).
2) Add `src/services/telemetryAggregator.js` to build RawTelemetry, compute features, compose schema v0.2.
3) Swap Home.vue auto-bootstrap to use the aggregator; include `coverage` in logs.
4) Extend backend `telemetry_tools.py` to support new fields while keeping backward compatibility.
5) Add unit tests for registry/aggregator outputs and tool responses on seeded fixtures.
