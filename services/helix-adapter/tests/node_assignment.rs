use std::time::Duration;

use sqlx::{
    postgres::{PgConnectOptions, PgPoolOptions},
    query, ConnectOptions, PgPool,
};
use uuid::Uuid;

use helix_adapter::{
    assignments::store::NodeAssignmentStore,
    db::pool::run_migrations,
    manifests::signer::ManifestSigner,
    node_registry::{
        model::{
            DesktopRuntimeCore, DesktopRuntimeEventBenchmarkEvidence,
            DesktopRuntimeEventContinuityEvidence, DesktopRuntimeEventKind,
            DesktopRuntimeEventPayload, DesktopRuntimeEventRecoveryEvidence,
            DesktopRuntimeEventRequest, NodeUpsertInput, PublishRolloutBatchRequest,
            RolloutChannel,
        },
        repository::NodeRegistryRepository,
    },
    transport_profiles::{
        repository::TransportProfileRepository, service::TransportProfileService,
    },
};

#[tokio::test]
async fn node_assignment_resolves_from_same_profile_policy_as_manifests() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let node_id = format!("node-{}", Uuid::new_v4().simple());
    repository
        .upsert_nodes(&[NodeUpsertInput {
            remnawave_node_id: node_id.clone(),
            node_name: "PT Lab Node".to_string(),
            hostname: Some("pt-lab-node".to_string()),
            adapter_node_label: "pt-lab-node".to_string(),
            last_synced_at: chrono::Utc::now(),
        }])
        .await
        .expect("upsert node");

    query(
        r#"
        UPDATE helix.nodes
        SET transport_port = 9444
        WHERE remnawave_node_id = $1
        "#,
    )
    .bind(&node_id)
    .execute(&pool)
    .await
    .expect("set transport port");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v2".to_string(),
            target_node_ids: vec![node_id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    let store = NodeAssignmentStore::new(
        pool.clone(),
        repository.clone(),
        TransportProfileService::new(TransportProfileRepository::new(pool.clone())),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let assignment = store
        .resolve_node_assignment(&node_id)
        .await
        .expect("resolve node assignment");

    assert_eq!(assignment.rollout_id, rollout_id);
    assert_eq!(assignment.node_id, node_id);
    assert_eq!(assignment.channel, "lab");
    assert_eq!(assignment.desired_state, "active");
    assert_eq!(assignment.transport_profile.profile_family, "edge-hybrid");
    assert_eq!(assignment.transport_profile.profile_version, 2);
    assert_eq!(assignment.transport_profile.policy_version, 4);
    assert_eq!(
        assignment
            .transport_profile
            .compatibility_window
            .max_transport_profile_version,
        3
    );
    assert_eq!(assignment.runtime_profile.min_daemon_version, "v0.1.0");
    assert!(assignment.runtime_profile.ports.contains(&443));
    assert!(assignment.runtime_profile.ports.contains(&8443));
    assert!(assignment.runtime_profile.ports.contains(&9444));
    assert_eq!(
        assignment.recovery.last_known_good_bundle,
        "bundle-bootstrap"
    );
    assert_eq!(assignment.integrity.signature.alg, "ed25519");

    repository
        .touch_last_known_good_bundle(
            &assignment.node_id,
            assignment.assignment_id,
            "manifest-v2-ptp-lab-edge-v2",
        )
        .await
        .expect("touch last known good");

    let refreshed_assignment = store
        .resolve_node_assignment(&assignment.node_id)
        .await
        .expect("resolve assignment after lkg update");

    assert_eq!(
        refreshed_assignment.recovery.last_known_good_bundle,
        "manifest-v2-ptp-lab-edge-v2"
    );
}

#[tokio::test]
async fn node_assignment_prefers_healthier_profile_over_newer_degraded_candidate() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let node_id = format!("node-{}", Uuid::new_v4().simple());
    repository
        .upsert_nodes(&[NodeUpsertInput {
            remnawave_node_id: node_id.clone(),
            node_name: "PT Lab Node".to_string(),
            hostname: Some("pt-lab-node".to_string()),
            adapter_node_label: "pt-lab-node".to_string(),
            last_synced_at: chrono::Utc::now(),
        }])
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v3".to_string(),
            target_node_ids: vec![node_id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

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
            runtime_unhealthy_threshold,
            created_at,
            updated_at
        )
        VALUES (
            'ptp-lab-edge-v3',
            'lab',
            'edge-hybrid',
            3,
            5,
            1,
            'hybrid',
            'active',
            'sing-box',
            ARRAY['protocol.v1', 'fallback.auto', 'sidecar.sigverify', 'profile.edge-hybrid'],
            1,
            4,
            20,
            3,
            NOW(),
            NOW()
        )
        ON CONFLICT (transport_profile_id) DO NOTHING
        "#,
    )
    .execute(&pool)
    .await
    .expect("insert newer profile");

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-ready".to_string(),
            desktop_client_id: "desktop-ready".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            event_kind: DesktopRuntimeEventKind::Ready,
            active_core: DesktopRuntimeCore::Helix,
            fallback_core: None,
            latency_ms: Some(37),
            route_count: Some(2),
            reason: None,
            observed_at: chrono::Utc::now(),
            payload: DesktopRuntimeEventPayload {
                continuity: Some(DesktopRuntimeEventContinuityEvidence {
                    successful_continuity_recovers: Some(1),
                    successful_cross_route_recovers: Some(1),
                    ..Default::default()
                }),
                recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                    same_route_recovered: Some(true),
                    ready_recovery_latency_ms: Some(37),
                    successful_cross_route_recovers: Some(1),
                    ..Default::default()
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record healthy evidence");

    for latency_ms in [610, 640, 670, 690] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-fallback-{latency_ms}"),
                desktop_client_id: format!("desktop-fallback-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(latency_ms),
                route_count: Some(2),
                reason: Some("health gate timeout".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    reason_code: Some("health-gate-timeout".to_string()),
                    continuity: Some(DesktopRuntimeEventContinuityEvidence {
                        failed_continuity_recovers: Some(1),
                        ..Default::default()
                    }),
                    recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                        same_route_recovered: Some(false),
                        ready_recovery_latency_ms: Some(latency_ms),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record degraded evidence");
    }

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-benchmark".to_string(),
            desktop_client_id: "desktop-benchmark".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-lab-edge-v3".to_string(),
            event_kind: DesktopRuntimeEventKind::Benchmark,
            active_core: DesktopRuntimeCore::Helix,
            fallback_core: None,
            latency_ms: Some(89),
            route_count: Some(2),
            reason: Some("benchmark-comparison".to_string()),
            observed_at: chrono::Utc::now(),
            payload: DesktopRuntimeEventPayload {
                benchmark: Some(DesktopRuntimeEventBenchmarkEvidence {
                    benchmark_kind: Some("comparison".to_string()),
                    baseline_core: Some("sing-box".to_string()),
                    target_count: Some(4),
                    successful_targets: Some(4),
                    attempts: Some(5),
                    successes: Some(4),
                    failures: Some(1),
                    throughput_kbps: Some(7_812.0),
                    relative_throughput_ratio_vs_baseline: Some(1.19),
                    median_connect_latency_ms: Some(20),
                    median_first_byte_latency_ms: Some(90),
                    median_open_to_first_byte_gap_ms: Some(70),
                    p95_open_to_first_byte_gap_ms: Some(98),
                    relative_open_to_first_byte_gap_ratio_vs_baseline: Some(0.92),
                    frame_queue_peak: Some(11),
                    recent_rtt_p95_ms: Some(28),
                    active_streams: Some(4),
                    pending_open_streams: Some(1),
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record benchmark evidence");

    let store = NodeAssignmentStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool.clone())),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let assignment = store
        .resolve_node_assignment(&node_id)
        .await
        .expect("resolve node assignment");

    assert_eq!(
        assignment.transport_profile.transport_profile_id,
        "ptp-lab-edge-v2"
    );
}

#[tokio::test]
async fn node_assignment_can_still_resolve_degraded_profile_when_manifest_guardrails_block_new_sessions(
) {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let node_id = format!("node-{}", Uuid::new_v4().simple());
    repository
        .upsert_nodes(&[NodeUpsertInput {
            remnawave_node_id: node_id.clone(),
            node_name: "PT Lab Node".to_string(),
            hostname: Some("pt-lab-node".to_string()),
            adapter_node_label: "pt-lab-node".to_string(),
            last_synced_at: chrono::Utc::now(),
        }])
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v7".to_string(),
            target_node_ids: vec![node_id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

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
            runtime_unhealthy_threshold,
            created_at,
            updated_at
        )
        VALUES (
            'ptp-lab-edge-v3',
            'lab',
            'edge-hybrid',
            3,
            5,
            1,
            'hybrid',
            'active',
            'sing-box',
            ARRAY['protocol.v1', 'fallback.auto', 'sidecar.sigverify', 'profile.edge-hybrid'],
            1,
            4,
            20,
            3,
            NOW(),
            NOW()
        )
        ON CONFLICT (transport_profile_id) DO NOTHING
        "#,
    )
    .execute(&pool)
    .await
    .expect("insert newer profile");

    for latency_ms in [640, 660, 680, 700] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v2-fallback-{latency_ms}"),
                desktop_client_id: format!("desktop-v2-fallback-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v2".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(latency_ms),
                route_count: Some(2),
                reason: Some("health gate timeout".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    continuity: Some(DesktopRuntimeEventContinuityEvidence {
                        failed_continuity_recovers: Some(1),
                        ..Default::default()
                    }),
                    recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                        same_route_recovered: Some(false),
                        ready_recovery_latency_ms: Some(latency_ms),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record v2 avoid-new-sessions evidence");
    }

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v3-ready-{}", index + 1),
                desktop_client_id: format!("desktop-v3-ready-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(64 + (index * 5)),
                route_count: Some(2),
                reason: None,
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    continuity: Some(DesktopRuntimeEventContinuityEvidence {
                        successful_continuity_recovers: Some(1),
                        ..Default::default()
                    }),
                    recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                        same_route_recovered: Some(true),
                        ready_recovery_latency_ms: Some(64 + (index * 5)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record v3 ready evidence");
    }

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v3-fallback-{}", index + 1),
                desktop_client_id: format!("desktop-v3-fallback-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(460 + (index * 25)),
                route_count: Some(2),
                reason: Some("continuity drift".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    reason_code: Some("continuity-drift".to_string()),
                    continuity: Some(DesktopRuntimeEventContinuityEvidence {
                        failed_continuity_recovers: Some(1),
                        ..Default::default()
                    }),
                    recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                        same_route_recovered: Some(false),
                        ready_recovery_latency_ms: Some(460 + (index * 25)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record v3 degraded evidence");
    }

    let store = NodeAssignmentStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool.clone())),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let assignment = store
        .resolve_node_assignment(&node_id)
        .await
        .expect("resolve node assignment");

    assert_eq!(
        assignment.transport_profile.transport_profile_id,
        "ptp-lab-edge-v3"
    );
}

#[tokio::test]
async fn node_assignment_can_still_resolve_avoid_new_sessions_profile_for_existing_rollout_nodes() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let node_id = format!("node-{}", Uuid::new_v4().simple());
    repository
        .upsert_nodes(&[NodeUpsertInput {
            remnawave_node_id: node_id.clone(),
            node_name: "PT Lab Node".to_string(),
            hostname: Some("pt-lab-node".to_string()),
            adapter_node_label: "pt-lab-node".to_string(),
            last_synced_at: chrono::Utc::now(),
        }])
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v4".to_string(),
            target_node_ids: vec![node_id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    query(
        r#"
        UPDATE helix.transport_profiles
        SET status = 'revoked', updated_at = NOW()
        WHERE transport_profile_id = 'ptp-lab-edge-v2'
        "#,
    )
    .execute(&pool)
    .await
    .expect("revoke default profile");

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
            runtime_unhealthy_threshold,
            created_at,
            updated_at
        )
        VALUES (
            'ptp-lab-edge-v3',
            'lab',
            'edge-hybrid',
            3,
            5,
            1,
            'hybrid',
            'active',
            'sing-box',
            ARRAY['protocol.v1', 'fallback.auto', 'sidecar.sigverify', 'profile.edge-hybrid'],
            1,
            4,
            20,
            3,
            NOW(),
            NOW()
        )
        ON CONFLICT (transport_profile_id) DO NOTHING
        "#,
    )
    .execute(&pool)
    .await
    .expect("insert degraded candidate");

    for latency_ms in [620, 640, 660, 680] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-node-gated-{latency_ms}"),
                desktop_client_id: format!("desktop-node-gated-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(latency_ms),
                route_count: Some(2),
                reason: Some("health gate timeout".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    reason_code: Some("health-gate-timeout".to_string()),
                    continuity: Some(DesktopRuntimeEventContinuityEvidence {
                        failed_continuity_recovers: Some(1),
                        ..Default::default()
                    }),
                    recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                        same_route_recovered: Some(false),
                        ready_recovery_latency_ms: Some(latency_ms),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record avoid-new-sessions evidence");
    }

    let store = NodeAssignmentStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool.clone())),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let assignment = store
        .resolve_node_assignment(&node_id)
        .await
        .expect("resolve node assignment despite avoid-new-sessions policy");

    assert_eq!(
        assignment.transport_profile.transport_profile_id,
        "ptp-lab-edge-v3"
    );
}

async fn maybe_test_pool() -> Option<PgPool> {
    let database_url = std::env::var("TEST_DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://cybervpn:cybervpn@localhost:6767/cybervpn".to_string());
    let options = database_url.parse::<PgConnectOptions>().ok()?;
    let options = options
        .application_name("helix-adapter-node-assignment-tests")
        .disable_statement_logging();

    match PgPoolOptions::new()
        .max_connections(2)
        .acquire_timeout(Duration::from_secs(2))
        .connect_with(options)
        .await
    {
        Ok(pool) => Some(pool),
        Err(error) => {
            eprintln!("Skipping DB-backed node assignment test: {error}");
            None
        }
    }
}
