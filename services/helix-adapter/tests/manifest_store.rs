use std::time::Duration;

use sqlx::{
    postgres::{PgConnectOptions, PgPoolOptions},
    query, query_scalar, ConnectOptions, PgPool,
};
use uuid::Uuid;

use helix_adapter::{
    db::pool::run_migrations,
    manifests::{
        model::ResolveManifestRequest, renderer::ManifestRenderer, signer::ManifestSigner,
        store::ManifestStore,
    },
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
async fn manifest_store_versions_signs_and_revokes_payloads() {
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
            manifest_version: "manifest-v1".to_string(),
            target_node_ids: vec![node_id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    let store = ManifestStore::new(
        pool.clone(),
        repository.clone(),
        TransportProfileService::new(TransportProfileRepository::new(pool.clone())),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let response = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_1".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 1,
                        max_transport_profile_version: 3,
                        supported_policy_versions: vec![4],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect("resolve manifest");

    assert_eq!(response.manifest.rollout_id, rollout_id);
    assert_eq!(response.manifest.integrity.signature.alg, "ed25519");
    assert_eq!(
        response.manifest.transport_profile.profile_family,
        "edge-hybrid"
    );
    assert_eq!(response.manifest.transport_profile.profile_version, 2);
    assert_eq!(
        response
            .manifest
            .compatibility_window
            .max_transport_profile_version,
        3
    );

    let revoked = store
        .revoke_manifest(response.manifest_version_id)
        .await
        .expect("revoke manifest");
    assert!(revoked.revoked_at.is_some());

    let is_revoked = query_scalar::<_, bool>(
        r#"
        SELECT revoked_at IS NOT NULL
        FROM helix.manifest_versions
        WHERE manifest_version_id = $1
        "#,
    )
    .bind(response.manifest_version_id)
    .fetch_one(&pool)
    .await
    .expect("check revoked state");

    assert!(is_revoked);
}

#[tokio::test]
async fn manifest_store_rejects_incompatible_transport_profile_request() {
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

    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: format!("rollout-{}", Uuid::new_v4().simple()),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v1".to_string(),
            target_node_ids: vec![node_id],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let error = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_2".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 1,
                        max_transport_profile_version: 1,
                        supported_policy_versions: vec![1],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect_err("expected incompatible transport profile request to fail");

    assert!(matches!(error, helix_adapter::error::AppError::NotFound(_)));
}

#[tokio::test]
async fn manifest_store_prefers_node_specific_transport_ports_when_present() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let node_primary = format!("node-{}", Uuid::new_v4().simple());
    let node_secondary = format!("node-{}", Uuid::new_v4().simple());
    repository
        .upsert_nodes(&[
            NodeUpsertInput {
                remnawave_node_id: node_primary.clone(),
                node_name: "PT Lab Node Primary".to_string(),
                hostname: Some("127.0.0.1".to_string()),
                adapter_node_label: "pt-lab-node-primary".to_string(),
                last_synced_at: chrono::Utc::now(),
            },
            NodeUpsertInput {
                remnawave_node_id: node_secondary.clone(),
                node_name: "PT Lab Node Secondary".to_string(),
                hostname: Some("127.0.0.1".to_string()),
                adapter_node_label: "pt-lab-node-secondary".to_string(),
                last_synced_at: chrono::Utc::now(),
            },
        ])
        .await
        .expect("upsert nodes");

    query(
        r#"
        UPDATE helix.nodes
        SET transport_port = CASE remnawave_node_id
            WHEN $1 THEN 9443
            WHEN $2 THEN 9444
            ELSE transport_port
        END
        WHERE remnawave_node_id IN ($1, $2)
        "#,
    )
    .bind(&node_primary)
    .bind(&node_secondary)
    .execute(&pool)
    .await
    .expect("update transport ports");

    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: format!("rollout-{}", Uuid::new_v4().simple()),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v2".to_string(),
            target_node_ids: vec![node_primary, node_secondary],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let response = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_ports".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 1,
                        max_transport_profile_version: 3,
                        supported_policy_versions: vec![4],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect("resolve manifest");

    let mut ports = response
        .manifest
        .routes
        .iter()
        .map(|route| route.dial_port)
        .collect::<Vec<_>>();
    ports.sort_unstable();

    assert_eq!(ports, vec![9443, 9444]);
}

#[tokio::test]
async fn manifest_store_prefers_healthier_profile_over_newer_degraded_candidate() {
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
            target_node_ids: vec![node_id],
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
            latency_ms: Some(41),
            route_count: Some(2),
            reason: None,
            observed_at: chrono::Utc::now(),
            payload: DesktopRuntimeEventPayload {
                runtime: Some("embedded-sidecar".to_string()),
                continuity: Some(DesktopRuntimeEventContinuityEvidence {
                    successful_continuity_recovers: Some(1),
                    successful_cross_route_recovers: Some(1),
                    ..Default::default()
                }),
                recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                    same_route_recovered: Some(true),
                    ready_recovery_latency_ms: Some(41),
                    successful_cross_route_recovers: Some(1),
                    ..Default::default()
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record healthy policy evidence");

    for (index, latency_ms) in [620, 640, 660, 680].into_iter().enumerate() {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-fallback-{}", index + 1),
                desktop_client_id: format!("desktop-fallback-{}", index + 1),
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
            .expect("record degraded policy evidence");
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
            latency_ms: Some(92),
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
                    throughput_kbps: Some(7_845.0),
                    relative_throughput_ratio_vs_baseline: Some(1.22),
                    median_connect_latency_ms: Some(19),
                    median_first_byte_latency_ms: Some(88),
                    median_open_to_first_byte_gap_ms: Some(69),
                    p95_open_to_first_byte_gap_ms: Some(95),
                    relative_open_to_first_byte_gap_ratio_vs_baseline: Some(0.91),
                    frame_queue_peak: Some(10),
                    recent_rtt_p95_ms: Some(26),
                    active_streams: Some(4),
                    pending_open_streams: Some(1),
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record benchmark policy evidence");

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let response = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_policy".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 1,
                        max_transport_profile_version: 4,
                        supported_policy_versions: vec![4, 5],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect("resolve manifest");

    assert_eq!(
        response.manifest.transport_profile.transport_profile_id,
        "ptp-lab-edge-v2"
    );
    assert!(response.selected_profile_policy.is_some());
    assert_eq!(
        response
            .selected_profile_policy
            .as_ref()
            .expect("selected profile policy")
            .advisory_state,
        "healthy"
    );
    assert!(
        response
            .selected_profile_policy
            .as_ref()
            .expect("selected profile policy")
            .selection_eligible
    );
}

#[tokio::test]
async fn manifest_store_rejects_avoid_new_sessions_profile_for_new_desktop_sessions() {
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
            target_node_ids: vec![node_id],
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

    for (index, latency_ms) in [620, 640, 660, 680].into_iter().enumerate() {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-fallback-gated-{}", index + 1),
                desktop_client_id: format!("desktop-fallback-gated-{}", index + 1),
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
            .expect("record degraded policy evidence");
    }

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let error = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_policy_gate".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 3,
                        max_transport_profile_version: 4,
                        supported_policy_versions: vec![5],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect_err("expected avoid-new-sessions profile to be gated");

    assert!(matches!(error, helix_adapter::error::AppError::NotFound(_)));
}

#[tokio::test]
async fn manifest_store_allows_only_degraded_but_continuity_safe_profile_for_new_sessions() {
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
            manifest_version: "manifest-v5".to_string(),
            target_node_ids: vec![node_id],
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

    for index in 0..3 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-ready-safe-{}", index + 1),
                desktop_client_id: format!("desktop-ready-safe-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(44 + (index * 3)),
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
                        ready_recovery_latency_ms: Some(44 + (index * 3)),
                        successful_cross_route_recovers: Some(1),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record continuity-safe ready evidence");
    }

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-fallback-safe".to_string(),
            desktop_client_id: "desktop-fallback-safe".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-lab-edge-v3".to_string(),
            event_kind: DesktopRuntimeEventKind::Fallback,
            active_core: DesktopRuntimeCore::SingBox,
            fallback_core: Some(DesktopRuntimeCore::SingBox),
            latency_ms: Some(390),
            route_count: Some(2),
            reason: Some("probe degradation".to_string()),
            observed_at: chrono::Utc::now(),
            payload: DesktopRuntimeEventPayload {
                reason_code: Some("probe-degradation".to_string()),
                continuity: Some(DesktopRuntimeEventContinuityEvidence {
                    failed_continuity_recovers: Some(1),
                    ..Default::default()
                }),
                recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                    same_route_recovered: Some(false),
                    ready_recovery_latency_ms: Some(390),
                    ..Default::default()
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record continuity-safe degraded evidence");

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let response = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_policy_safe".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 3,
                        max_transport_profile_version: 4,
                        supported_policy_versions: vec![5],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect("resolve manifest for continuity-safe degraded profile");

    assert_eq!(
        response.manifest.transport_profile.transport_profile_id,
        "ptp-lab-edge-v3"
    );
    assert_eq!(
        response
            .selected_profile_policy
            .as_ref()
            .expect("selected profile policy")
            .advisory_state,
        "degraded"
    );
    assert!(
        response
            .selected_profile_policy
            .as_ref()
            .expect("selected profile policy")
            .selection_eligible
    );
}

#[tokio::test]
async fn manifest_store_rejects_degraded_profile_when_continuity_guardrails_fail() {
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
            manifest_version: "manifest-v6".to_string(),
            target_node_ids: vec![node_id],
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

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-ready-guard-{}", index + 1),
                desktop_client_id: format!("desktop-ready-guard-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(71 + (index * 4)),
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
                        ready_recovery_latency_ms: Some(71 + (index * 4)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record degraded ready evidence");
    }

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-fallback-guard-{}", index + 1),
                desktop_client_id: format!("desktop-fallback-guard-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(470 + (index * 20)),
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
                        ready_recovery_latency_ms: Some(470 + (index * 20)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record continuity-poor degraded evidence");
    }

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let error = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_policy_guard".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 3,
                        max_transport_profile_version: 4,
                        supported_policy_versions: vec![5],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect_err("expected degraded profile to fail new-session continuity guardrails");

    assert!(matches!(error, helix_adapter::error::AppError::NotFound(_)));
}

#[tokio::test]
async fn manifest_store_can_issue_degraded_profile_when_it_is_only_compatible_option_and_continuity_remains_stable(
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
            manifest_version: "manifest-v5".to_string(),
            target_node_ids: vec![node_id],
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
    .expect("insert degraded candidate");

    for index in 0..3 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-ready-stable-{}", index + 1),
                desktop_client_id: format!("desktop-ready-stable-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-lab-edge-v3".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(55 + index * 5),
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
                        ready_recovery_latency_ms: Some(55 + index * 5),
                        successful_cross_route_recovers: Some(1),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record continuity-preserving ready");
    }

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-fallback-stable".to_string(),
            desktop_client_id: "desktop-fallback-stable".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-lab-edge-v3".to_string(),
            event_kind: DesktopRuntimeEventKind::Fallback,
            active_core: DesktopRuntimeCore::SingBox,
            fallback_core: Some(DesktopRuntimeCore::SingBox),
            latency_ms: Some(320),
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
                    ready_recovery_latency_ms: Some(320),
                    ..Default::default()
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record single degraded fallback");

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let response = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_policy_degraded".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 3,
                        max_transport_profile_version: 4,
                        supported_policy_versions: vec![5],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect("resolve degraded-but-issuable manifest");

    assert_eq!(
        response.manifest.transport_profile.transport_profile_id,
        "ptp-lab-edge-v3"
    );
    assert_eq!(
        response
            .selected_profile_policy
            .as_ref()
            .expect("selected profile policy")
            .advisory_state,
        "degraded"
    );
}

#[tokio::test]
async fn manifest_store_honors_active_profile_suppression_window_for_new_sessions() {
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
            manifest_version: "manifest-v6".to_string(),
            target_node_ids: vec![node_id],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    query(
        r#"
        INSERT INTO helix.profile_suppression_windows (
            rollout_id,
            transport_profile_id,
            suppressed_until,
            suppression_reason,
            first_observed_at,
            last_observed_at,
            observation_count
        )
        VALUES (
            $1,
            'ptp-lab-edge-v2',
            NOW() + INTERVAL '30 minutes',
            'blocked-new-session-posture',
            NOW(),
            NOW(),
            1
        )
        ON CONFLICT (rollout_id, transport_profile_id) DO NOTHING
        "#,
    )
    .bind(&rollout_id)
    .execute(&pool)
    .await
    .expect("insert suppression window");

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let error = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_internal_suppressed".to_string(),
                desktop_client_id: "desktop_win11_primary".to_string(),
                entitlement_id: "ent_internal_canary".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Lab),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 1,
                        max_transport_profile_version: 3,
                        supported_policy_versions: vec![4],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Lab,
            3600,
        )
        .await
        .expect_err("expected active suppression window to block manifest issuance");

    assert!(matches!(error, helix_adapter::error::AppError::NotFound(_)));
}

#[tokio::test]
async fn manifest_store_rejects_new_sessions_after_pause_channel_actuation() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let node_id = format!("node-{}", Uuid::new_v4().simple());
    repository
        .upsert_nodes(&[NodeUpsertInput {
            remnawave_node_id: node_id.clone(),
            node_name: "PT Stable Node".to_string(),
            hostname: Some("stable-node".to_string()),
            adapter_node_label: "stable-node".to_string(),
            last_synced_at: chrono::Utc::now(),
        }])
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Stable,
            manifest_version: "manifest-v14".to_string(),
            target_node_ids: vec![node_id],
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
            'ptp-stable-edge-v9',
            'stable',
            'edge-hybrid',
            9,
            9,
            1,
            'hybrid',
            'active',
            'sing-box',
            ARRAY['protocol.v1'],
            1,
            9,
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
    .expect("insert stable profile");

    for latency_ms in [640, 660, 680, 700] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-stable-blocked-{latency_ms}"),
                desktop_client_id: format!("desktop-stable-blocked-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v9".to_string(),
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
            .expect("record blocked evidence");
    }

    let store = ManifestStore::new(
        pool.clone(),
        repository,
        TransportProfileService::new(TransportProfileRepository::new(pool)),
        ManifestRenderer::new("helix".to_string()),
        ManifestSigner::new(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "sig-key-test",
        )
        .expect("signer"),
    );

    let error = store
        .resolve_manifest(
            ResolveManifestRequest {
                user_id: "usr_pause_channel".to_string(),
                desktop_client_id: "desktop_pause_channel".to_string(),
                entitlement_id: "ent_pause_channel".to_string(),
                trace_id: format!("trace-{}", Uuid::new_v4().simple()),
                channel: Some(RolloutChannel::Stable),
                supported_protocol_versions: Some(vec![1]),
                supported_transport_profiles: Some(vec![
                    helix_adapter::manifests::model::SupportedTransportProfile {
                        profile_family: "edge-hybrid".to_string(),
                        min_transport_profile_version: 1,
                        max_transport_profile_version: 9,
                        supported_policy_versions: vec![9],
                    },
                ]),
                preferred_fallback_core: Some("sing-box".to_string()),
            },
            RolloutChannel::Stable,
            3600,
        )
        .await
        .expect_err("expected paused channel to refuse new manifest issuance");

    assert!(matches!(error, helix_adapter::error::AppError::NotFound(_)));
}

async fn maybe_test_pool() -> Option<PgPool> {
    let database_url = std::env::var("TEST_DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://cybervpn:cybervpn@localhost:6767/cybervpn".to_string());
    let options = database_url.parse::<PgConnectOptions>().ok()?;
    let options = options
        .application_name("helix-adapter-tests")
        .disable_statement_logging();

    match PgPoolOptions::new()
        .max_connections(2)
        .acquire_timeout(Duration::from_secs(2))
        .connect_with(options)
        .await
    {
        Ok(pool) => Some(pool),
        Err(error) => {
            eprintln!("Skipping DB-backed manifest store test: {error}");
            None
        }
    }
}
