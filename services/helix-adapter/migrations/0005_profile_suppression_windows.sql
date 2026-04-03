CREATE TABLE IF NOT EXISTS helix.profile_suppression_windows (
    rollout_id TEXT NOT NULL,
    transport_profile_id TEXT NOT NULL REFERENCES helix.transport_profiles(transport_profile_id) ON DELETE CASCADE,
    suppressed_until TIMESTAMPTZ NOT NULL,
    suppression_reason TEXT NOT NULL,
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observation_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (rollout_id, transport_profile_id)
);

CREATE INDEX IF NOT EXISTS idx_helix_profile_suppression_active
    ON helix.profile_suppression_windows (rollout_id, suppressed_until DESC);
