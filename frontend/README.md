Followup Agent Frontend

Development:

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to your backend (default: http://localhost:8000)

New files and integration notes:

- `src/components/LiveKitConnector.tsx`: an integration boundary / placeholder for LiveKit. Replace with a real `livekit-client` implementation and call a server-side token endpoint to join a room. Do NOT embed LiveKit secrets in the frontend.
- `src/pages/CallScreen.tsx`: enhanced call UI, transcript, tool event display, elapsed timer, and uses `LiveKitConnector`.
- `src/pages/CustomerDetail.tsx`: now generates a "Call Brief" by calling the backend StartCall endpoint once and surfaces the returned `strategy`. The console is opened only after the brief is generated.
- `src/pages/Dashboard.tsx`: search/filter for customers and wiring to call console.

Environment variables:
- `VITE_API_BASE_URL` — base URL for backend API (e.g. http://localhost:8000)
- LiveKit tokens and secrets must be obtained server-side and not stored in the client.

Run checklist performed locally by developer:
1. Start backend (FastAPI) with `.venv` and environment variables set.
2. Start frontend with `npm run dev` in `frontend/` and confirm customer list loads.

If you need me to wire actual LiveKit token endpoints or improve visual polish, I can continue.
