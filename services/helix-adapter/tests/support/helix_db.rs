use std::{
    sync::{Arc, OnceLock},
    time::Duration,
};

use helix_adapter::db::pool::run_migrations;
use sqlx::{
    postgres::{PgConnectOptions, PgPoolOptions},
    query, ConnectOptions, PgPool,
};
use tokio::sync::{Mutex, OwnedMutexGuard};

static TEST_DB_LOCK: OnceLock<Arc<Mutex<()>>> = OnceLock::new();

pub struct IsolatedTestPool {
    pool: PgPool,
    _guard: OwnedMutexGuard<()>,
}

impl IsolatedTestPool {
    pub fn pool(&self) -> PgPool {
        self.pool.clone()
    }
}

pub async fn maybe_test_pool(application_name: &str) -> Option<IsolatedTestPool> {
    let guard = TEST_DB_LOCK
        .get_or_init(|| Arc::new(Mutex::new(())))
        .clone()
        .lock_owned()
        .await;
    let database_url = std::env::var("TEST_DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://cybervpn:cybervpn@localhost:6767/cybervpn".to_string());
    let options = database_url.parse::<PgConnectOptions>().ok()?;
    let options = options
        .application_name(application_name)
        .disable_statement_logging();

    match PgPoolOptions::new()
        .max_connections(2)
        .acquire_timeout(Duration::from_secs(2))
        .connect_with(options)
        .await
    {
        Ok(pool) => {
            run_migrations(&pool).await.expect("migrations");
            reset_helix_test_data(&pool)
                .await
                .expect("reset helix test data");
            Some(IsolatedTestPool {
                pool,
                _guard: guard,
            })
        }
        Err(error) => {
            eprintln!("Skipping DB-backed Helix adapter test: {error}");
            None
        }
    }
}

async fn reset_helix_test_data(pool: &PgPool) -> Result<(), sqlx::Error> {
    query(
        r#"
        TRUNCATE TABLE
            helix.profile_suppression_windows,
            helix.rollout_policy_actuations,
            helix.node_heartbeat_snapshots,
            helix.last_known_good_bundles,
            helix.manifest_versions,
            helix.rollout_batches,
            helix.nodes
        RESTART IDENTITY CASCADE
        "#,
    )
    .execute(pool)
    .await?;

    query(
        r#"
        DELETE FROM helix.transport_profiles
        WHERE transport_profile_id NOT IN (
            'ptp-lab-edge-v2',
            'ptp-canary-edge-v3',
            'ptp-stable-edge-v2'
        )
        "#,
    )
    .execute(pool)
    .await?;

    query(
        r#"
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
        ON CONFLICT (transport_profile_id) DO UPDATE
        SET
            channel = EXCLUDED.channel,
            profile_family = EXCLUDED.profile_family,
            profile_version = EXCLUDED.profile_version,
            policy_version = EXCLUDED.policy_version,
            protocol_version = EXCLUDED.protocol_version,
            session_mode = EXCLUDED.session_mode,
            status = EXCLUDED.status,
            fallback_core = EXCLUDED.fallback_core,
            required_capabilities = EXCLUDED.required_capabilities,
            compatibility_min_profile_version = EXCLUDED.compatibility_min_profile_version,
            compatibility_max_profile_version = EXCLUDED.compatibility_max_profile_version,
            startup_timeout_seconds = EXCLUDED.startup_timeout_seconds,
            runtime_unhealthy_threshold = EXCLUDED.runtime_unhealthy_threshold,
            updated_at = NOW()
        "#,
    )
    .execute(pool)
    .await?;

    Ok(())
}
