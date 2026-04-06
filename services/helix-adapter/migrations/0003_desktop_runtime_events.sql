CREATE TABLE IF NOT EXISTS helix.desktop_runtime_events (
    event_id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    desktop_client_id TEXT NOT NULL,
    manifest_version_id UUID NOT NULL,
    rollout_id TEXT NOT NULL REFERENCES helix.rollout_batches (rollout_id),
    transport_profile_id TEXT NOT NULL,
    event_kind TEXT NOT NULL
        CHECK (event_kind IN ('ready', 'fallback', 'disconnect')),
    active_core TEXT NOT NULL
        CHECK (active_core IN ('helix', 'sing-box', 'xray')),
    fallback_core TEXT
        CHECK (fallback_core IS NULL OR fallback_core IN ('sing-box', 'xray')),
    latency_ms INTEGER
        CHECK (latency_ms IS NULL OR latency_ms >= 0),
    route_count INTEGER
        CHECK (route_count IS NULL OR route_count >= 0),
    reason TEXT,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_helix_runtime_events_rollout_observed
    ON helix.desktop_runtime_events (rollout_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_helix_runtime_events_desktop_observed
    ON helix.desktop_runtime_events (desktop_client_id, observed_at DESC);
