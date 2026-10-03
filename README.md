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
