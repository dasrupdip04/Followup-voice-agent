# Banking Follow-up Voice Agent Database

This directory contains the Phase 1 database schema and deterministic seed data for a fictional banking/payment follow-up voice agent.

## What each table represents

- `customers`: master customer records for the fictional bank. Each customer has a unique customer number, contact details, preferred language, and bank profile.
- `loans`: every loan associated with a customer. A single customer can have multiple loans. This table stores principal, outstanding amount, EMI, due date, and current status.
- `payments`: one-to-many payment history per loan. It stores payment amount, method, date, and transaction reference.
- `calls`: each voice-agent call associated with a customer. This table tracks call lifecycle metadata, without storing raw audio.
- `conversation_turns`: textual conversation turns within a call, split into `AGENT` and `CUSTOMER` speaker categories.
- `call_events`: event-level observability for the call lifecycle, including tool execution and interruptions.
- `call_outcomes`: business outcome from the call, such as a promise to pay or callback request.
- `call_metrics`: aggregated technical and operational performance metrics for each call.

## Relationships

The schema is intentionally simple but realistic:

- `customers` -> `loans` : one-to-many
- `loans` -> `payments` : one-to-many
- `customers` -> `calls` : one-to-many
- `calls` -> `conversation_turns` : one-to-many
- `calls` -> `call_events` : one-to-many
- `calls` -> `call_outcomes` : one-to-one
- `calls` -> `call_metrics` : one-to-one

The important design choice is that the call tables are children of `calls`, not of `customers` directly, so each call can have a distinct outcome, event stream, and metric summary.

## Schema initialization

Make sure Docker is running and the PostgreSQL 16 service is up:

```bash
docker compose up -d postgres
```

Apply the schema:

```bash
docker exec -i followup-postgres psql -U followup_user -d followup -v ON_ERROR_STOP=1 < database/migrations/001_create_schema.sql
```

This creates the tables, constraints, indexes, and comments.

## Seeding the database

Run the deterministic seed script:

```bash
docker exec -i followup-postgres psql -U followup_user -d followup -v ON_ERROR_STOP=1 < database/seeds/002_seed_fictional_data.sql
```

The seed script is built to be rerunnable. It uses a transaction plus `TRUNCATE ... RESTART IDENTITY CASCADE` so the database is reset to a clean state before inserting the fictional data.

## Example SQL queries

Inspect customers:

```sql
SELECT id, customer_number, full_name, city, preferred_language
FROM customers
ORDER BY id;
```

Inspect loans for a specific customer:

```sql
SELECT l.id, l.loan_number, l.loan_type, l.status, l.outstanding_amount, l.due_date
FROM loans l
JOIN customers c ON c.id = l.customer_id
WHERE c.customer_number = 'CUST001'
ORDER BY l.due_date;
```

Inspect payments for a loan:

```sql
SELECT p.id, p.loan_id, p.amount, p.payment_date, p.payment_method, p.status,
       p.transaction_reference
FROM payments p
JOIN loans l ON l.id = p.loan_id
WHERE l.loan_number = 'LN-2024-001'
ORDER BY p.payment_date DESC;
```

Inspect recent calls and their outcomes:

```sql
SELECT c.id, cu.customer_number, c.started_at, c.status, co.outcome_type
FROM calls c
JOIN customers cu ON cu.id = c.customer_id
LEFT JOIN call_outcomes co ON co.call_id = c.id
ORDER BY c.started_at DESC;
```

## Notes

- No raw audio is stored in PostgreSQL.
- Monetary values are stored as `NUMERIC` to avoid floating-point issues.
- The project intentionally does not include ORM configuration or backend code yet; this phase focuses on the database layer only.
