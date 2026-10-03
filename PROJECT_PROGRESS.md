# Followup Voice Agent — Project Progress

This document tracks the work completed so far. It is intentionally a progress log, not the final project README.

## Current architecture

```mermaid
flowchart LR
    User[Client / Future UI] --> API[FastAPI Backend]
    API --> SQLA[SQLAlchemy 2.x]
    SQLA --> PG[(PostgreSQL 16 in Docker)]
    API --> Health[/health and /health/db]
    API --> Customers[/customers endpoints]
```

## Phase 1 — Database foundation

Completed:
- PostgreSQL 16 was set up in Docker via `docker-compose.yml`.
- Database schema was created for the banking / payment follow-up domain.
- Seed data was added with fictional Indian banking examples.
- Core tables created:
  - `customers`
  - `loans`
  - `payments`
  - `calls`
  - `conversation_turns`
  - `call_events`
  - `call_outcomes`
  - `call_metrics`
- Data is persisted through the Docker volume `postgres_data`.

Files involved:
- `database/migrations/001_create_schema.sql`
- `database/seeds/002_seed_fictional_data.sql`
- `database/README.md` (project-local DB reference)

## Phase 2 — Minimal FastAPI backend

Completed:
- Created a minimal FastAPI app under `backend/app/`.
- Added database connectivity using SQLAlchemy 2.x and `psycopg`.
- Used environment variables to configure PostgreSQL credentials.
- Added the health endpoints:
  - `GET /health`
  - `GET /health/db`
- Added clear error handling when PostgreSQL is unavailable.

Files involved:
- `backend/app/main.py`
- `backend/app/db.py`
- `backend/app/__init__.py`
- `backend/.env.example`
- `backend/requirements.txt`

## Phase 3 — Read-only customer API layer

Completed:
- Added customer list pagination via `GET /customers`.
- Added single-customer retrieval via `GET /customers/{customer_id}`.
- Added consolidated customer context via `GET /customers/{customer_id}/context`.
- Used SQLAlchemy queries instead of raw SQL.
- Used Pydantic response models.
- Kept database models and API schemas separate.
- Added basic FastAPI tests for:
  - customer list
  - customer detail
  - customer context
  - 404 for missing customer

Files involved:
- `backend/app/models/customer_models.py`
- `backend/app/schemas/customer.py`
- `backend/app/services/customer_service.py`
- `backend/app/routers/customer_router.py`
- `backend/tests/test_customers_api.py`

## Scope still intentionally out of scope

The following remain intentionally unimplemented for now:
- voice agent orchestration
- Gemini / LLM integration
- STT / TTS
- LiveKit
- frontend UI
- authentication
- business workflow automation beyond read-only customer data access

## Current status

The system now includes:
- relational banking schema
- seeded fictional financial data
- FastAPI service layer
- PostgreSQL connectivity
- read-only customer APIs

This is a solid backend foundation for the next phase, when we begin richer workflow and agent-driven behavior.

## Next likely step

The next planned step is to extend the backend with service logic and endpoints for loan/payment operations and call workflows, still without introducing voice or agent tooling.
