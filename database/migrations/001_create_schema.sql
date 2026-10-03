BEGIN;

-- Core banking profile for each customer handled by the follow-up voice agent.
-- The customer record is intentionally kept separate from loan and call data so
-- we can trace multiple financial products and multiple call interactions over time.
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    customer_number VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    phone_number VARCHAR(30) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    date_of_birth DATE NOT NULL,
    city VARCHAR(100) NOT NULL,
    bank_name VARCHAR(150) NOT NULL,
    preferred_language VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE customers IS 'Primary customer master record for the follow-up voice-agent workflow.';
COMMENT ON COLUMN customers.customer_number IS 'Stable customer identifier shown in internal tooling and outbound communication, e.g. CUST001.';
COMMENT ON COLUMN customers.preferred_language IS 'Language preference used by the voice agent for personalization and routing.';

-- Loans are intentionally modeled as a child table of customers because one
-- customer may have multiple loans, and the follow-up agent needs to reason over
-- them independently instead of collapsing everything into a single account.
CREATE TABLE loans (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    loan_number VARCHAR(40) NOT NULL UNIQUE,
    loan_type VARCHAR(50) NOT NULL,
    principal_amount NUMERIC(14, 2) NOT NULL CHECK (principal_amount > 0),
    outstanding_amount NUMERIC(14, 2) NOT NULL CHECK (outstanding_amount >= 0),
    interest_rate NUMERIC(5, 2) NOT NULL CHECK (interest_rate >= 0),
    emi_amount NUMERIC(12, 2) NOT NULL CHECK (emi_amount > 0),
    due_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('CURRENT', 'OVERDUE', 'PAID_OFF', 'DELINQUENT', 'PENDING')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE loans IS 'Customer loan portfolio. Each loan is evaluated independently for follow-up calls and payment collection.';
COMMENT ON COLUMN loans.outstanding_amount IS 'Current open balance; stored as NUMERIC to avoid floating-point drift in financial calculations.';

-- Payment history is kept separate from loans so we can track multiple
-- successful and failed payment events per loan without mutating the original loan.
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    loan_id BIGINT NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    payment_date TIMESTAMPTZ NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('SUCCESS', 'PENDING', 'FAILED', 'REFUNDED')),
    transaction_reference VARCHAR(80) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE payments IS 'Every payment attempt or successful payment associated with a loan.';
COMMENT ON COLUMN payments.transaction_reference IS 'External or internal transaction reference used for reconciliation and audits.';

-- A call is the top-level interaction record. We intentionally keep raw audio out
-- of PostgreSQL, storing only conversation text, events, and derived metrics.
CREATE TABLE calls (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER CHECK (duration_seconds >= 0),
    status VARCHAR(30) NOT NULL CHECK (status IN ('INITIATED', 'IN_PROGRESS', 'COMPLETED', 'NO_ANSWER', 'FAILED', 'CANCELLED')),
    agent_id VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE calls IS 'Every voice-agent interaction with a customer. This table does not store audio.';

CREATE TABLE conversation_turns (
    id BIGSERIAL PRIMARY KEY,
    call_id BIGINT NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    speaker VARCHAR(10) NOT NULL CHECK (speaker IN ('AGENT', 'CUSTOMER')),
    text TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    latency_ms INTEGER CHECK (latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conversation_turns IS 'Textual conversation turns; this keeps the schema lightweight and avoids storing raw audio.';

CREATE TABLE call_events (
    id BIGSERIAL PRIMARY KEY,
    call_id BIGINT NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    event_type VARCHAR(60) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE call_events IS 'Event-level observability for call lifecycle and tool execution. Event types are constrained at application level when needed.';

CREATE TABLE call_outcomes (
    id BIGSERIAL PRIMARY KEY,
    call_id BIGINT NOT NULL UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    outcome_type VARCHAR(40) NOT NULL CHECK (outcome_type IN ('PROMISE_TO_PAY', 'PAYMENT_COMPLETED', 'CALLBACK_REQUESTED', 'REFUSED', 'NO_ANSWER', 'WRONG_NUMBER', 'DISPUTE', 'NEEDS_HUMAN')),
    promised_amount NUMERIC(14, 2) CHECK (promised_amount >= 0),
    promised_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE call_outcomes IS 'Business outcome of the call, such as a promise to pay or a human escalation.';

CREATE TABLE call_metrics (
    id BIGSERIAL PRIMARY KEY,
    call_id BIGINT NOT NULL UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    total_turns INTEGER NOT NULL CHECK (total_turns >= 0),
    user_turns INTEGER NOT NULL CHECK (user_turns >= 0),
    agent_turns INTEGER NOT NULL CHECK (agent_turns >= 0),
    avg_response_latency_ms NUMERIC(10, 2),
    avg_stt_latency_ms NUMERIC(10, 2),
    avg_llm_latency_ms NUMERIC(10, 2),
    avg_tts_latency_ms NUMERIC(10, 2),
    user_interruptions INTEGER NOT NULL DEFAULT 0 CHECK (user_interruptions >= 0),
    agent_interruptions INTEGER NOT NULL DEFAULT 0 CHECK (agent_interruptions >= 0),
    tool_calls INTEGER NOT NULL DEFAULT 0 CHECK (tool_calls >= 0),
    tool_failures INTEGER NOT NULL DEFAULT 0 CHECK (tool_failures >= 0),
    tokens_input BIGINT NOT NULL DEFAULT 0 CHECK (tokens_input >= 0),
    tokens_output BIGINT NOT NULL DEFAULT 0 CHECK (tokens_output >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE call_metrics IS 'Derived operational metrics for monitoring and dashboarding conversation quality and latency.';

-- Query-oriented indexes for the most common access patterns: parent-child lookups,
-- time ordering, and operational filtering by status or event type.
CREATE INDEX idx_loans_customer_id ON loans (customer_id);
CREATE INDEX idx_loans_status ON loans (status);
CREATE INDEX idx_loans_due_date ON loans (due_date);

CREATE INDEX idx_payments_loan_id ON payments (loan_id);
CREATE INDEX idx_payments_payment_date ON payments (loan_id, payment_date DESC);
CREATE INDEX idx_payments_status ON payments (status);

CREATE INDEX idx_calls_customer_id ON calls (customer_id);
CREATE INDEX idx_calls_started_at ON calls (started_at DESC);
CREATE INDEX idx_calls_status ON calls (status);

CREATE INDEX idx_conversation_turns_call_id ON conversation_turns (call_id, timestamp);
CREATE INDEX idx_conversation_turns_speaker ON conversation_turns (speaker);

CREATE INDEX idx_call_events_call_id ON call_events (call_id, timestamp);
CREATE INDEX idx_call_events_event_type ON call_events (event_type);

CREATE INDEX idx_call_outcomes_outcome_type ON call_outcomes (outcome_type);

COMMIT;
