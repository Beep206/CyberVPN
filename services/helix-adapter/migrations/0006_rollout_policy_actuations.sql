CREATE TABLE IF NOT EXISTS helix.rollout_policy_actuations (
    rollout_id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    reaction TEXT NOT NULL,
    target_transport_profile_id TEXT NULL,
    trigger_reason TEXT NULL,
    applied BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cleared_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_rollout_policy_actuations_active
    ON helix.rollout_policy_actuations (channel, reaction)
    WHERE applied = TRUE AND cleared_at IS NULL;
