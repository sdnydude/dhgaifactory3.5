-- 006: done_gate_runs — Loop 4 done-gate verdict ledger (dhg-memreg client half).
-- One row per claim-bearing gate run (observe mode logs no_claim locally only).
-- adjudication is the human ratchet input: precision per check_version decides
-- when a check promotes from observe to enforce.

CREATE TABLE IF NOT EXISTS done_gate_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(128) NOT NULL,
    project VARCHAR(100) NOT NULL,
    verdict VARCHAR(16) NOT NULL CHECK (verdict IN ('pass', 'fail', 'no_claim')),
    claim JSONB,
    evidence JSONB,
    gate_mode VARCHAR(16) NOT NULL DEFAULT 'observe',
    check_version INTEGER NOT NULL DEFAULT 1,
    adjudication VARCHAR(16) CHECK (adjudication IN ('true_positive', 'false_positive', 'false_negative')),
    sampled BOOLEAN NOT NULL DEFAULT false,
    adjudicated_at TIMESTAMPTZ,
    meta_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_done_gate_runs_project_created
    ON done_gate_runs (project, created_at);
CREATE INDEX IF NOT EXISTS ix_done_gate_runs_verdict
    ON done_gate_runs (verdict);
