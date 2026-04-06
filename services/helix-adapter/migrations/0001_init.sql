CREATE SCHEMA IF NOT EXISTS helix;

CREATE TABLE IF NOT EXISTS helix.nodes (
    service_node_id UUID PRIMARY KEY,
    remnawave_node_id TEXT NOT NULL UNIQUE,
    node_name TEXT NOT NULL,
    hostname TEXT,
    transport_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    rollout_channel TEXT NOT NULL DEFAULT 'lab'
        CHECK (rollout_channel IN ('lab', 'canary', 'stable')),
    node_group TEXT NOT NULL DEFAULT 'regional',
    adapter_node_label TEXT NOT NULL,
    last_heartbeat_at TIMESTAMPTZ,
    daemon_version TEXT,
    active_rollout_id TEXT,
    last_synced_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS helix.rollout_batches (
    rollout_id TEXT PRIMARY KEY
        CHECK (rollout_id ~ '^rollout-[a-z0-9-]+$'),
    channel TEXT NOT NULL
        CHECK (channel IN ('lab', 'canary', 'stable')),
    desired_state TEXT NOT NULL
        CHECK (desired_state IN ('running', 'paused', 'revoked', 'completed')),
    batch_id TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    target_nodes INTEGER NOT NULL DEFAULT 0,
    completed_nodes INTEGER NOT NULL DEFAULT 0,
    failed_nodes INTEGER NOT NULL DEFAULT 0,
    desktop_connect_success_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    desktop_fallback_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    pause_on_rollback_spike BOOLEAN NOT NULL DEFAULT TRUE,
    revoke_on_manifest_error BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS helix.manifest_versions (
    manifest_version_id UUID PRIMARY KEY,
    manifest_id UUID NOT NULL,
    rollout_id TEXT NOT NULL REFERENCES helix.rollout_batches (rollout_id),
    manifest_template_version TEXT NOT NULL,
    subject_user_id TEXT NOT NULL,
    desktop_client_id TEXT NOT NULL,
    entitlement_id TEXT NOT NULL,
    channel TEXT NOT NULL
        CHECK (channel IN ('lab', 'canary', 'stable')),
    protocol_version INTEGER NOT NULL CHECK (protocol_version >= 1),
    manifest_json JSONB NOT NULL,
    manifest_hash TEXT NOT NULL,
    signature_alg TEXT NOT NULL,
    signature_key_id TEXT NOT NULL,
    signature TEXT NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS helix.node_heartbeat_snapshots (
    heartbeat_id UUID PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES helix.nodes (remnawave_node_id),
    rollout_id TEXT NOT NULL REFERENCES helix.rollout_batches (rollout_id),
    observed_at TIMESTAMPTZ NOT NULL,
    daemon_version TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    daemon_status TEXT NOT NULL
        CHECK (daemon_status IN ('ready', 'degraded', 'rollback', 'starting')),
    active_bundle_version TEXT NOT NULL,
    pending_bundle_version TEXT,
    last_known_good_version TEXT NOT NULL,
    ready BOOLEAN NOT NULL,
    runtime_healthy BOOLEAN NOT NULL,
    apply_state TEXT NOT NULL
        CHECK (apply_state IN ('idle', 'applying', 'failed', 'rolled-back')),
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    reason TEXT,
    rollback_total INTEGER NOT NULL DEFAULT 0,
    apply_fail_total INTEGER NOT NULL DEFAULT 0,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS helix.last_known_good_bundles (
    node_id TEXT PRIMARY KEY REFERENCES helix.nodes (remnawave_node_id),
    assignment_id UUID NOT NULL,
    bundle_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_helix_nodes_channel
    ON helix.nodes (rollout_channel, transport_enabled);

CREATE INDEX IF NOT EXISTS idx_helix_nodes_active_rollout
    ON helix.nodes (active_rollout_id);

CREATE INDEX IF NOT EXISTS idx_helix_manifest_versions_rollout
    ON helix.manifest_versions (rollout_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_helix_heartbeat_node_observed
    ON helix.node_heartbeat_snapshots (node_id, observed_at DESC);
