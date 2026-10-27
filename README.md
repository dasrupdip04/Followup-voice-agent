<img width="1920" height="1080" alt="ss2" src="https://github.com/user-attachments/assets/852e3cbf-d7d3-4e73-9029-e0b338ccba11" />
<img width="1920" height="1080" alt="ss1" src="https://github.com/user-attachments/assets/b2dd3eec-e05e-404c-9236-e48a562375ef" />

# Followup Voice Agent

An autonomous Voice AI agent for banking and loan repayment follow-ups. Built with **FastAPI**, **PostgreSQL**, **LiveKit WebRTC**, **Deepgram (Streaming STT)**, **Google Gemini 3.5 Flash Lite (LLM + Dynamic Tool Calling)**, and **Cartesia Sonic 3 (Ultra-low latency TTS)**.

---

## Architecture Overview

```text
       ┌───────────────┐
       │ React Client  │ (Browser WebRTC + Audio)
       └───────┬───────┘
               │ WebRTC Audio stream
               ▼
       ┌───────────────┐
       │ LiveKit Cloud │
       └───────┬───────┘
               │
    ┌──────────┴─────────────────────────┐
    │                                    ▼
┌───┴───────────────┐           ┌────────────────┐
│   Deepgram STT    │           │ Cartesia TTS   │
│  (Realtime Audio  │           │ (Realtime Voice│
│   Transcription)  │           │   Synthesis)   │
└───┬───────────────┘           └────────▲───────┘
    │ Transcript                         │ Audio
    ▼                                    │
┌────────────────────────────────────────┴───────┐
│ LiveKit Voice Worker (runner.py)               │
│ - VoicePipelineAgent session management        │
│ - Adaptive interruption & turn detection       │
└───────────────────┬────────────────────────────┘
                    │ User turn completed
                    ▼
┌────────────────────────────────────────────────┐
│ FastAPI Backend & Tool Calling Engine          │
│ - CallLifecycleService (state & db persistence)│
│ - GeminiService (Gemini 3.5 Flash Lite)        │
│ - Structured Database Tools (DB queries)       │
└───────────────────┬────────────────────────────┘
                    ▼
┌────────────────────────────────────────────────┐
│ PostgreSQL 16 (Customer, Loan, Outcome DB)     │
└────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.11+** (Python 3.11 - 3.13 supported)
- **Node.js 18+** & npm
- **Docker & Docker Compose** (for PostgreSQL)
- API Keys:
  - **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))
  - **LiveKit Cloud Project** ([LiveKit Cloud](https://cloud.livekit.io/))
  - **Deepgram API Key** ([Deepgram Console](https://console.deepgram.com/))
  - **Cartesia API Key** ([Cartesia](https://play.cartesia.ai/))

---

## Quick Start Guide

### 1. Clone the Repository

```bash
git clone https://github.com/dasrupdip04/Followup-voice-agent.git
cd Followup-voice-agent
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` in both the root and `backend/` directory:

```bash
cp .env.example .env
cp .env.example backend/.env
```

Open `.env` and fill in your credentials:

```env
# PostgreSQL Configuration (Matches docker-compose.yml)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=followup
POSTGRES_USER=followup_user
POSTGRES_PASSWORD=followup_password

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# Deepgram Speech-to-Text
DEEPGRAM_API_KEY=your_deepgram_api_key_here
DEEPGRAM_MODEL=flux-general-multi

# LiveKit Cloud
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here

# Cartesia Text-to-Speech
CARTESIA_API_KEY=your_cartesia_api_key_here
CARTESIA_MODEL=sonic-3
CARTESIA_LANGUAGE=en
CARTESIA_VOICE_ID=f786b574-daa5-4673-aa0c-cbe3e8534c02
```

---

### 3. Start PostgreSQL Database

Start the database container using Docker Compose:

```bash
docker compose up -d
```

The database container automatically initializes the schema and seeds sample customers, loans, and banking records from `database/seeds/`.

To verify the database is up:

```bash
docker compose ps
```

---

### 4. Setup and Run the Backend

Create a Python virtual environment and install backend dependencies:

```bash
# Create and activate virtual environment
python3 -m venv backend/.venv
source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the FastAPI server on port 8000
PYTHONPATH=backend uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

FastAPI will start listening at `http://localhost:8000`. You can verify health:
- `http://localhost:8000/health`
- `http://localhost:8000/health/db`
- `http://localhost:8000/api/v1/health/gemini`
- API documentation: `http://localhost:8000/docs`

---

### 5. Start the LiveKit Voice Agent Worker

In a separate terminal window, activate the virtual environment and start the LiveKit worker:

```bash
cd Followup-voice-agent
source backend/.venv/bin/activate

PYTHONPATH=backend python -m backend.app.livekit_agent.run_agent dev
```

You should see log output indicating the worker registered successfully:
```text
INFO livekit.agents - registered worker {"agent_name": "followup-voice-agent", "url": "wss://..."}
```

---

### 6. Setup and Run the Frontend

In a third terminal window:

```bash
cd Followup-voice-agent/frontend

# Install dependencies (only needed once)
npm install

# Start Vite dev server
npm run dev
```

Open your browser at **`http://localhost:5173`**.

---

## Testing a Voice Call

1. In the web dashboard (`http://localhost:5173`), select any customer from the list (e.g., **Aarav Mehta** or **Kabir Singh**).
2. Click **Start Call**.
3. Allow microphone permissions in your browser.
4. The AI recovery agent will greet you with your account and outstanding loan balance.
5. Speak naturally into the microphone (e.g., *"I can't pay right now, can I pay next week?"* or *"Sorry, I don't remember taking any loan"*).
6. The agent dynamically queries database tools, reasons with Gemini 3.5 Flash Lite, responds via Cartesia TTS in real-time, and saves the outcome summary and metrics upon call completion.

---

## Project Structure

```text
Followup-voice-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── db.py                    # Database connection & session setup
│   │   ├── models/
│   │   │   └── customer_models.py   # SQLAlchemy models (Customer, Loan, Call, etc.)
│   │   ├── routers/
│   │   │   ├── agent.py             # Call lifecycle & LiveKit room dispatch routes
│   │   │   ├── customer_router.py   # Customer data endpoints
│   │   │   └── health.py            # System health checks
│   │   ├── schemas/                 # Pydantic validation schemas
│   │   ├── services/
│   │   │   ├── call_lifecycle_service.py # Turn orchestration & analysis
│   │   │   ├── call_strategy_service.py  # Personalized call opening & goal generator
│   │   │   └── gemini_service.py         # Google Gemini integration & tool executor
│   │   ├── tools/                   # Registered DB tools callable by Gemini
│   │   └── livekit_agent/
│   │       ├── runner.py            # LiveKit Agent runner (STT + LLM + TTS pipeline)
│   │       └── run_agent.py         # CLI entry point for LiveKit worker
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Example backend environment variables
├── frontend/                        # React + Vite + TailwindCSS frontend
│   ├── src/
│   │   ├── components/              # Call controls, transcript view, analytics
│   │   └── App.jsx
│   └── package.json
├── database/
│   ├── migrations/                  # SQL schema definitions
│   └── seeds/                       # Demo seed records
├── docker-compose.yml               # PostgreSQL service definition
├── .env.example                     # Root example environment variables
├── .gitignore                       # Ignored secrets and dependencies
└── README.md
```

---

## License

MIT License. Designed for demonstration and production voice follow-up workflows.
