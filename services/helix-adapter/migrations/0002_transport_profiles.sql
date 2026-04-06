CREATE TABLE IF NOT EXISTS helix.transport_profiles (
    transport_profile_id TEXT PRIMARY KEY
        CHECK (transport_profile_id ~ '^ptp-[a-z0-9-]+$'),
    channel TEXT NOT NULL
        CHECK (channel IN ('lab', 'canary', 'stable')),
    profile_family TEXT NOT NULL,
    profile_version INTEGER NOT NULL CHECK (profile_version >= 1),
    policy_version INTEGER NOT NULL CHECK (policy_version >= 1),
    protocol_version INTEGER NOT NULL CHECK (protocol_version >= 1),
    session_mode TEXT NOT NULL
        CHECK (session_mode IN ('stateful', 'hybrid')),
    status TEXT NOT NULL
        CHECK (status IN ('active', 'deprecated', 'revoked')),
    fallback_core TEXT NOT NULL
        CHECK (fallback_core IN ('sing-box', 'xray')),
    required_capabilities TEXT[] NOT NULL,
    compatibility_min_profile_version INTEGER NOT NULL
        CHECK (compatibility_min_profile_version >= 1),
    compatibility_max_profile_version INTEGER NOT NULL
        CHECK (compatibility_max_profile_version >= compatibility_min_profile_version),
    startup_timeout_seconds INTEGER NOT NULL CHECK (startup_timeout_seconds BETWEEN 5 AND 120),
    runtime_unhealthy_threshold INTEGER NOT NULL CHECK (runtime_unhealthy_threshold BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (channel, profile_family, profile_version, policy_version)
);

INSERT INTO helix.transport_profiles (
    transport_profile_id,
    channel,
    profile_family,
    profile_version,
    policy_version,
    protocol_version,
    session_mode,
    status,
    fallback_core,
    required_capabilities,
    compatibility_min_profile_version,
    compatibility_max_profile_version,
    startup_timeout_seconds,
    runtime_unhealthy_threshold
)
VALUES
    (
        'ptp-lab-edge-v2',
        'lab',
        'edge-hybrid',
        2,
        4,
        1,
        'hybrid',
        'active',
        'sing-box',
        ARRAY['protocol.v1', 'fallback.auto', 'sidecar.sigverify', 'profile.edge-hybrid'],
        1,
        3,
        20,
        3
    ),
    (
        'ptp-canary-edge-v3',
        'canary',
        'edge-hybrid',
        3,
        7,
        1,
        'hybrid',
        'active',
        'sing-box',
        ARRAY['protocol.v1', 'fallback.auto', 'sidecar.sigverify', 'profile.edge-hybrid'],
        2,
        4,
        20,
        3
    ),
    (
        'ptp-stable-edge-v2',
        'stable',
        'edge-hybrid',
        2,
        5,
        1,
        'hybrid',
        'active',
        'sing-box',
        ARRAY['protocol.v1', 'fallback.auto', 'sidecar.sigverify', 'profile.edge-hybrid'],
        1,
        3,
        20,
        3
    )
ON CONFLICT (transport_profile_id) DO NOTHING;

ALTER TABLE helix.manifest_versions
    ADD COLUMN IF NOT EXISTS transport_profile_id TEXT,
    ADD COLUMN IF NOT EXISTS profile_family TEXT,
    ADD COLUMN IF NOT EXISTS profile_version INTEGER,
    ADD COLUMN IF NOT EXISTS policy_version INTEGER;

CREATE INDEX IF NOT EXISTS idx_helix_profiles_channel_status
    ON helix.transport_profiles (channel, status, profile_family, profile_version DESC);
