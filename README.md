<img width="1920" height="1080" alt="ss2" src="https://github.com/user-attachments/assets/852e3cbf-d7d3-4e73-9029-e0b338ccba11" />
<img width="1920" height="1080" alt="ss1" src="https://github.com/user-attachments/assets/b2dd3eec-e05e-404c-9236-e48a562375ef" />
# Followup Voice Agent

This project is a phased prototype for a banking/payment follow-up voice agent.

## Goals

- Build a realistic banking data model in PostgreSQL.
- Expose a simple FastAPI backend.
- Connect to a PostgreSQL database using SQLAlchemy and psycopg.
- Add a read-only customer API layer.
- Integrate Google Gemini for basic agent response generation.

## Project structure

```text
Followup-voice-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   └── services/
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   └── .venv/
├── database/
│   ├── migrations/
│   └── seeds/
├── docker-compose.yml
├── PROJECT_PROGRESS.md
└── README.md
```

## Installation

From the backend directory:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Set the frontend environment variable `VITE_API_BASE_URL` to point to the backend, e.g. `http://localhost:8000`.

## Environment variables

The backend expects these variables in `backend/.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=followup
POSTGRES_USER=followup_user
POSTGRES_PASSWORD=followup_password
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## Start FastAPI

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH=.
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Health checks

```bash
curl http://localhost:8001/health
curl http://localhost:8001/health/db
curl http://localhost:8001/health/gemini
```

Expected:

```json
{"status": "ok"}
```

```json
{"status": "ok", "database": "connected"}
```

```json
{"status": "ok", "configured": true, "model": "gemini-2.5-flash"}
```

## Test the Gemini route

Example request:

```bash
curl -X POST http://localhost:8001/api/v1/agent/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I won't be able to pay this month"
  }'
```

Example response:

```json
{
  "response": "I understand this is difficult...",
  "model": "gemini-2.5-flash",
  "status": "ok"
}
```

## Notes

- The database schema and seeds are intentionally not modified in this phase.
- The Gemini integration is intentionally minimal and modular for future tool/function-calling work.
- This phase does not include STT, TTS, LiveKit, or voice infrastructure.

## Phase 7 — LiveKit + Deepgram + Cartesia (Voice agent)

This repository now contains a minimal LiveKit agent package (Phase 7) that
connects real-time LiveKit sessions with Deepgram for streaming STT and
Cartesia Sonic 3 for streaming TTS. The implementation intentionally keeps
the existing Phase 5/6 backend architecture unchanged and reuses the
GeminiService, tool registry, and call lifecycle services.

Required environment variables (add to `backend/.env`):

```
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
DEEPGRAM_API_KEY=
DEEPGRAM_MODEL=flux-general-multi
CARTESIA_API_KEY=
CARTESIA_MODEL=sonic-3
CARTESIA_LANGUAGE=en
CARTESIA_VOICE_ID=<voice-id>
```

Install additional dependencies in the backend virtualenv:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

Running the LiveKit agent (example smoke test):

```bash
# from the backend directory
python -c "from app.livekit_agent.agent import LiveKitAgent; print(LiveKitAgent().smoke_test())"
```

The LiveKit agent package lives at `backend/app/livekit_agent` and provides:
- `LiveKitAgent`: initialization and provider bindings (no network I/O on import)
- `LiveSession`: in-memory session state for an active room/call
- lightweight wrappers in `tools.py` that call existing Phase 6 lifecycle services

Notes:
- The LiveKit agent does not start or join rooms automatically — it exposes
  the hooks and initialization needed to attach Deepgram and Cartesia plugins
  to a LiveKit Agents runtime. Implement joining/room event wiring in a
  deployment-specific runner.
- The design minimizes Gemini calls: one Gemini generation per user turn, and
  calls to Phase 5 tools only when explicitly required by Gemini.

