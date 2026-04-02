use std::time::Duration;

use sqlx::{
    postgres::{PgConnectOptions, PgPoolOptions},
    query_as, query_scalar, ConnectOptions, PgPool,
};
use uuid::Uuid;

use helix_adapter::{
    config::AdapterConfig,
    db::pool::run_migrations,
    node_registry::{
        model::{
            DesktopRuntimeCore, DesktopRuntimeEventBenchmarkEvidence,
            DesktopRuntimeEventContinuityEvidence, DesktopRuntimeEventKind,
            DesktopRuntimeEventPayload, DesktopRuntimeEventRecoveryEvidence,
            DesktopRuntimeEventRequest, NodeHeartbeatBundle, NodeHeartbeatCounters,
            NodeHeartbeatDaemon, NodeHeartbeatHealth, NodeHeartbeatRequest,
            NodeHeartbeatTransportProfile, NodeUpsertInput, PublishRolloutBatchRequest,
            RolloutChannel,
        },
        repository::NodeRegistryRepository,
        service::NodeRegistryService,
    },
    remnawave::client::{NodeInventoryItem, RemnawaveClient},
    transport_profiles::{
        model::{TransportProfileStatus, UpsertTransportProfileRequest},
        repository::TransportProfileRepository,
    },
};

#[tokio::test]
async fn node_registry_persists_rollout_assignments() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let inventory_item = NodeInventoryItem {
        id: format!("node-{}", Uuid::new_v4().simple()),
        name: "PT Edge EU West".to_string(),
        hostname: Some("pt-edge-eu-west-01".to_string()),
        enabled: Some(true),
    };
    let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);
    repository
        .upsert_nodes(std::slice::from_ref(&upsert))
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    let batch = repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Lab,
            manifest_version: "manifest-v1".to_string(),
            target_node_ids: vec![inventory_item.id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    assert_eq!(batch.rollout_id, rollout_id);
    assert_eq!(batch.channel, "lab");

    let nodes = repository.list_nodes().await.expect("list nodes");
    let node = nodes
        .into_iter()
        .find(|record| record.remnawave_node_id == inventory_item.id)
        .expect("persisted node");

    assert!(node.transport_enabled);
    assert_eq!(node.rollout_channel, "lab");
    assert_eq!(node.active_rollout_id.as_deref(), Some(rollout_id.as_str()));
}

#[tokio::test]
async fn node_registry_records_heartbeat_snapshots() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let inventory_item = NodeInventoryItem {
        id: format!("node-{}", Uuid::new_v4().simple()),
        name: "PT Edge Canary".to_string(),
        hostname: Some("pt-edge-canary-01".to_string()),
        enabled: Some(true),
    };
    let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);
    repository
        .upsert_nodes(std::slice::from_ref(&upsert))
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Canary,
            manifest_version: "manifest-v2".to_string(),
            target_node_ids: vec![inventory_item.id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    repository
        .record_heartbeat(&NodeHeartbeatRequest {
            schema_version: "1.0".to_string(),
            heartbeat_id: Uuid::new_v4(),
            node_id: inventory_item.id.clone(),
            rollout_id: rollout_id.clone(),
            observed_at: chrono::Utc::now(),
            transport_profile: NodeHeartbeatTransportProfile {
                transport_profile_id: "ptp-canary-edge-v3".to_string(),
                profile_family: "edge-hybrid".to_string(),
                profile_version: 3,
                policy_version: 7,
            },
            daemon: NodeHeartbeatDaemon {
                version: "v0.1.0".to_string(),
                instance_id: "ptnd-canary-1".to_string(),
                status: "ready".to_string(),
            },
            bundle: NodeHeartbeatBundle {
                active_version: "bundle-2026-03-31-01".to_string(),
                pending_version: None,
                last_known_good_version: "bundle-2026-03-24-02".to_string(),
            },
            health: NodeHeartbeatHealth {
                ready: true,
                runtime_healthy: true,
                apply_state: "idle".to_string(),
                latency_ms: 42,
                reason: None,
            },
            counters: NodeHeartbeatCounters {
                rollback_total: 0,
                apply_fail_total: 0,
            },
            capabilities: vec![
                "protocol.v1".to_string(),
                "runtime.rollback".to_string(),
                "metrics.prometheus".to_string(),
                "profile.edge-hybrid".to_string(),
            ],
        })
        .await
        .expect("record heartbeat");

    let nodes = repository.list_nodes().await.expect("list nodes");
    let node = nodes
        .into_iter()
        .find(|record| record.remnawave_node_id == inventory_item.id)
        .expect("persisted node");

    assert!(node.last_heartbeat_at.is_some());
    assert_eq!(node.daemon_version.as_deref(), Some("v0.1.0"));
    assert_eq!(node.active_rollout_id.as_deref(), Some(rollout_id.as_str()));
}

#[tokio::test]
async fn node_registry_updates_rollout_desktop_rates_from_runtime_events() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let inventory_item = NodeInventoryItem {
        id: format!("node-{}", Uuid::new_v4().simple()),
        name: "PT Edge Stable".to_string(),
        hostname: Some("pt-edge-stable-01".to_string()),
        enabled: Some(true),
    };
    let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);
    repository
        .upsert_nodes(std::slice::from_ref(&upsert))
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Stable,
            manifest_version: "manifest-v3".to_string(),
            target_node_ids: vec![inventory_item.id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-1".to_string(),
            desktop_client_id: "desktop-alpha".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-stable-edge-v4".to_string(),
            event_kind: DesktopRuntimeEventKind::Ready,
            active_core: DesktopRuntimeCore::Helix,
            fallback_core: None,
            latency_ms: Some(120),
            route_count: Some(2),
            reason: None,
            observed_at: chrono::Utc::now(),
            payload: DesktopRuntimeEventPayload {
                runtime: Some("embedded-sidecar".to_string()),
                continuity: Some(DesktopRuntimeEventContinuityEvidence {
                    active_streams: Some(3),
                    pending_open_streams: Some(0),
                    continuity_grace_active: Some(false),
                    continuity_grace_entries: Some(1),
                    successful_continuity_recovers: Some(1),
                    failed_continuity_recovers: Some(0),
                    successful_cross_route_recovers: Some(1),
                    last_cross_route_recovery_ms: Some(44),
                    ..Default::default()
                }),
                recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                    same_route_recovered: Some(true),
                    ready_recovery_latency_ms: Some(41),
                    proxy_ready_latency_ms: Some(59),
                    successful_cross_route_recovers: Some(1),
                    last_cross_route_recovery_ms: Some(44),
                    ..Default::default()
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record ready");

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-2".to_string(),
            desktop_client_id: "desktop-beta".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-stable-edge-v4".to_string(),
            event_kind: DesktopRuntimeEventKind::Fallback,
            active_core: DesktopRuntimeCore::SingBox,
            fallback_core: Some(DesktopRuntimeCore::SingBox),
            latency_ms: Some(640),
            route_count: Some(2),
            reason: Some("health gate timeout".to_string()),
            observed_at: chrono::Utc::now(),
            payload: DesktopRuntimeEventPayload {
                reason_code: Some("startup-timeout".to_string()),
                continuity: Some(DesktopRuntimeEventContinuityEvidence {
                    active_streams: Some(1),
                    pending_open_streams: Some(1),
                    continuity_grace_active: Some(true),
                    continuity_grace_entries: Some(1),
                    successful_continuity_recovers: Some(0),
                    failed_continuity_recovers: Some(1),
                    ..Default::default()
                }),
                recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                    same_route_recovered: Some(false),
                    ready_recovery_latency_ms: Some(640),
                    proxy_ready_latency_ms: Some(712),
                    ..Default::default()
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record fallback");

    repository
        .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
            schema_version: "1.0".to_string(),
            event_id: Uuid::new_v4(),
            user_id: "user-benchmark".to_string(),
            desktop_client_id: "desktop-gamma".to_string(),
            manifest_version_id: Uuid::new_v4(),
            rollout_id: rollout_id.clone(),
            transport_profile_id: "ptp-stable-edge-v4".to_string(),
            event_kind: DesktopRuntimeEventKind::Benchmark,
            active_core: DesktopRuntimeCore::Helix,
            fallback_core: None,
            latency_ms: Some(84),
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
                    throughput_kbps: Some(7_512.5),
                    relative_throughput_ratio_vs_baseline: Some(1.18),
                    median_connect_latency_ms: Some(18),
                    median_first_byte_latency_ms: Some(86),
                    median_open_to_first_byte_gap_ms: Some(68),
                    p95_open_to_first_byte_gap_ms: Some(91),
                    relative_open_to_first_byte_gap_ratio_vs_baseline: Some(0.89),
                    frame_queue_peak: Some(12),
                    recent_rtt_p95_ms: Some(29),
                    active_streams: Some(5),
                    pending_open_streams: Some(1),
                }),
                ..Default::default()
            },
        })
        .await
        .expect("record benchmark");

    let rollout = repository
        .find_rollout_by_id(&rollout_id)
        .await
        .expect("rollout state");
    let rollout_state = repository
        .fetch_rollout_state(&rollout_id)
        .await
        .expect("rollout status response");
    assert!((rollout.desktop_connect_success_rate - 0.5).abs() < f64::EPSILON);
    assert!((rollout.desktop_fallback_rate - 0.5).abs() < f64::EPSILON);
    assert!((rollout_state.desktop.connect_success_rate - 0.5).abs() < f64::EPSILON);
    assert!((rollout_state.desktop.fallback_rate - 0.5).abs() < f64::EPSILON);
    assert_eq!(rollout_state.desktop.continuity_observed_events, 2);
    assert!((rollout_state.desktop.continuity_success_rate - 0.5).abs() < f64::EPSILON);
    assert!((rollout_state.desktop.cross_route_recovery_rate - 0.5).abs() < f64::EPSILON);
    assert_eq!(rollout_state.desktop.benchmark_observed_events, 1);
    assert_eq!(rollout_state.desktop.throughput_evidence_observed_events, 1);
    assert!(
        (rollout_state.desktop.average_benchmark_throughput_kbps.unwrap() - 7_512.5).abs()
            < f64::EPSILON
    );
    assert!(
        (rollout_state.desktop.average_relative_throughput_ratio.unwrap() - 1.18).abs()
            < f64::EPSILON
    );
    assert!(
        (rollout_state
            .desktop
            .average_relative_open_to_first_byte_gap_ratio
            .unwrap()
            - 0.89)
            .abs()
            < f64::EPSILON
    );
    assert_eq!(rollout_state.policy.channel_posture, "watch");
    assert_eq!(rollout_state.policy.automatic_reaction, "observe");
}

#[tokio::test]
async fn node_registry_rollout_canary_evidence_reports_watch_when_throughput_evidence_is_missing()
{
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let service = NodeRegistryService::new(
        repository.clone(),
        RemnawaveClient::new(&AdapterConfig::test_default()).expect("remnawave client"),
    );
    let inventory_item = NodeInventoryItem {
        id: format!("node-{}", Uuid::new_v4().simple()),
        name: "PT Edge Canary".to_string(),
        hostname: Some("pt-edge-canary-watch-01".to_string()),
        enabled: Some(true),
    };
    let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);
    repository
        .upsert_nodes(std::slice::from_ref(&upsert))
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Canary,
            manifest_version: "manifest-v-canary-watch".to_string(),
            target_node_ids: vec![inventory_item.id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-canary-ready-{}", index + 1),
                desktop_client_id: format!("desktop-canary-ready-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-canary-edge-v1".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(66 + index * 4),
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
                        ready_recovery_latency_ms: Some(66 + index * 4),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record ready");
    }

    let evidence = service
        .rollout_canary_evidence(&rollout_id, &AdapterConfig::test_default())
        .await
        .expect("rollout canary evidence");

    assert_eq!(evidence.channel, "canary");
    assert_eq!(evidence.decision, "watch");
    assert_eq!(
        evidence.recommended_follow_up_action.as_deref(),
        Some("collect-more-evidence")
    );
    assert!(evidence
        .evidence_gaps
        .iter()
        .any(|gap| gap == "throughput evidence observations=0"));
}

#[tokio::test]
async fn node_registry_rollout_canary_evidence_reports_no_go_for_poor_relative_throughput() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let service = NodeRegistryService::new(
        repository.clone(),
        RemnawaveClient::new(&AdapterConfig::test_default()).expect("remnawave client"),
    );
    let inventory_item = NodeInventoryItem {
        id: format!("node-{}", Uuid::new_v4().simple()),
        name: "PT Edge Canary".to_string(),
        hostname: Some("pt-edge-canary-nogo-01".to_string()),
        enabled: Some(true),
    };
    let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);
    repository
        .upsert_nodes(std::slice::from_ref(&upsert))
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Canary,
            manifest_version: "manifest-v-canary-nogo".to_string(),
            target_node_ids: vec![inventory_item.id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    for index in 0..5 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-canary-benchmark-{}", index + 1),
                desktop_client_id: format!("desktop-canary-benchmark-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-canary-edge-v2".to_string(),
                event_kind: DesktopRuntimeEventKind::Benchmark,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(94),
                route_count: Some(2),
                reason: Some("comparison benchmark evidence".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    benchmark: Some(DesktopRuntimeEventBenchmarkEvidence {
                        benchmark_kind: Some("comparison".to_string()),
                        baseline_core: Some("sing-box".to_string()),
                        target_count: Some(4),
                        successful_targets: Some(4),
                        attempts: Some(4),
                        successes: Some(4),
                        failures: Some(0),
                        throughput_kbps: Some(18_000.0),
                        relative_throughput_ratio_vs_baseline: Some(0.81),
                        median_connect_latency_ms: Some(18),
                        median_first_byte_latency_ms: Some(96),
                        median_open_to_first_byte_gap_ms: Some(78),
                        p95_open_to_first_byte_gap_ms: Some(104),
                        relative_open_to_first_byte_gap_ratio_vs_baseline: Some(1.05),
                        frame_queue_peak: Some(11),
                        recent_rtt_p95_ms: Some(28),
                        active_streams: Some(4),
                        pending_open_streams: Some(1),
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record benchmark");
    }

    let evidence = service
        .rollout_canary_evidence(&rollout_id, &AdapterConfig::test_default())
        .await
        .expect("rollout canary evidence");

    assert_eq!(evidence.decision, "no-go");
    assert_eq!(
        evidence.recommended_follow_up_action.as_deref(),
        Some("review-canary-blockers")
    );
    assert!(evidence
        .reasons
        .iter()
        .any(|reason| reason == "relative throughput ratio=0.81"));
}

#[tokio::test]
async fn node_registry_rollout_state_recommends_pause_for_avoid_new_sessions_profile() {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let transport_profiles = TransportProfileRepository::new(pool.clone());
    let inventory_item = NodeInventoryItem {
        id: format!("node-{}", Uuid::new_v4().simple()),
        name: "PT Edge Advisory".to_string(),
        hostname: Some("pt-edge-advisory-01".to_string()),
        enabled: Some(true),
    };
    let upsert = NodeRegistryService::inventory_to_upsert(&inventory_item);
    repository
        .upsert_nodes(std::slice::from_ref(&upsert))
        .await
        .expect("upsert node");

    let rollout_id = format!("rollout-{}", Uuid::new_v4().simple());
    repository
        .publish_rollout(&PublishRolloutBatchRequest {
            rollout_id: rollout_id.clone(),
            batch_id: format!("batch-{}", Uuid::new_v4().simple()),
            channel: RolloutChannel::Stable,
            manifest_version: "manifest-v9".to_string(),
            target_node_ids: vec![inventory_item.id.clone()],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    transport_profiles
        .upsert_profile(&UpsertTransportProfileRequest {
            transport_profile_id: "ptp-stable-edge-v9".to_string(),
            channel: RolloutChannel::Stable,
            profile_family: "edge-hybrid".to_string(),
            profile_version: 9,
            policy_version: 9,
            protocol_version: 1,
            session_mode: "hybrid".to_string(),
            status: TransportProfileStatus::Active,
            fallback_core: "sing-box".to_string(),
            required_capabilities: vec!["protocol.v1".to_string()],
            compatibility_min_profile_version: 1,
            compatibility_max_profile_version: 9,
            startup_timeout_seconds: 20,
            runtime_unhealthy_threshold: 3,
        })
        .await
        .expect("upsert profile");

    for _ in 0..4 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: "user-advisory".to_string(),
                desktop_client_id: format!("desktop-{}", Uuid::new_v4().simple()),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v9".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(800),
                route_count: Some(2),
                reason: Some("health gate timeout".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload::default(),
            })
            .await
            .expect("record fallback");
    }

    let rollout_state = repository
        .fetch_rollout_state(&rollout_id)
        .await
        .expect("rollout status response");
    let rollout_record = repository
        .find_rollout_by_id(&rollout_id)
        .await
        .expect("rollout record");

    assert_eq!(
        rollout_state.policy.active_transport_profile_id.as_deref(),
        Some("ptp-stable-edge-v9")
    );
    assert_eq!(rollout_state.policy.healthy_candidate_count, 0);
    assert_eq!(rollout_state.policy.eligible_candidate_count, 0);
    assert_eq!(rollout_state.policy.suppressed_candidate_count, 1);
    assert!(rollout_state.policy.active_profile_suppressed);
    assert!(!rollout_state.policy.profile_rotation_recommended);
    assert!(rollout_state.policy.pause_recommended);
    assert_eq!(rollout_state.policy.channel_posture, "critical");
    assert_eq!(rollout_state.policy.automatic_reaction, "pause-channel");
    assert_eq!(
        rollout_state.policy.applied_automatic_reaction.as_deref(),
        Some("pause-channel")
    );
    assert_eq!(rollout_state.desired_state, "paused");
    assert_eq!(rollout_record.desired_state, "paused");
    assert!(rollout_state
        .policy
        .recommended_transport_profile_id
        .is_none());
    assert_eq!(
        rollout_state
            .policy
            .active_profile_policy
            .as_ref()
            .map(|policy| policy.advisory_state.as_str()),
        Some("avoid-new-sessions")
    );
    assert!(rollout_state
        .policy
        .active_profile_policy
        .as_ref()
        .is_some_and(|policy| policy.suppression_window_active));
    assert!(rollout_state
        .policy
        .recommended_action
        .as_deref()
        .is_some_and(|message| message.contains("Pause Helix rollout")));
}

#[tokio::test]
async fn node_registry_rollout_state_pauses_when_degraded_profile_fails_new_session_guardrails() {
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
            manifest_version: "manifest-v10".to_string(),
            target_node_ids: vec![node_id],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    let transport_profiles = TransportProfileRepository::new(pool.clone());
    transport_profiles
        .upsert_profile(&UpsertTransportProfileRequest {
            transport_profile_id: "ptp-stable-edge-v9".to_string(),
            channel: RolloutChannel::Stable,
            profile_family: "edge-hybrid".to_string(),
            profile_version: 9,
            policy_version: 9,
            protocol_version: 1,
            session_mode: "hybrid".to_string(),
            status: TransportProfileStatus::Active,
            fallback_core: "sing-box".to_string(),
            required_capabilities: vec!["protocol.v1".to_string()],
            compatibility_min_profile_version: 1,
            compatibility_max_profile_version: 9,
            startup_timeout_seconds: 20,
            runtime_unhealthy_threshold: 3,
        })
        .await
        .expect("upsert v9 profile");

    for latency_ms in [640, 660, 680, 700] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v8-fallback-{latency_ms}"),
                desktop_client_id: format!("desktop-v8-fallback-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v8".to_string(),
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
            .expect("record v8 avoid evidence");
    }

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v9-ready-{}", index + 1),
                desktop_client_id: format!("desktop-v9-ready-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v9".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(69 + (index * 6)),
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
                        ready_recovery_latency_ms: Some(69 + (index * 6)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record v9 ready evidence");
    }

    for index in 0..2 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v9-fallback-{}", index + 1),
                desktop_client_id: format!("desktop-v9-fallback-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v9".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(480 + (index * 25)),
                route_count: Some(2),
                reason: Some("continuity drift".to_string()),
                observed_at: chrono::Utc::now(),
                payload: DesktopRuntimeEventPayload {
                    continuity: Some(DesktopRuntimeEventContinuityEvidence {
                        failed_continuity_recovers: Some(1),
                        ..Default::default()
                    }),
                    recovery: Some(DesktopRuntimeEventRecoveryEvidence {
                        same_route_recovered: Some(false),
                        ready_recovery_latency_ms: Some(480 + (index * 25)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record v9 degraded evidence");
    }

    let rollout_state = repository
        .fetch_rollout_state(&rollout_id)
        .await
        .expect("rollout state");

    assert_eq!(
        rollout_state.policy.active_transport_profile_id.as_deref(),
        Some("ptp-stable-edge-v9")
    );
    assert_eq!(
        rollout_state
            .policy
            .active_profile_policy
            .as_ref()
            .map(|policy| policy.advisory_state.as_str()),
        Some("degraded")
    );
    assert_eq!(rollout_state.policy.suppressed_candidate_count, 1);
    assert!(rollout_state.policy.active_profile_suppressed);
    assert!(!rollout_state.policy.profile_rotation_recommended);
    assert!(rollout_state.policy.pause_recommended);
    assert_eq!(rollout_state.policy.channel_posture, "critical");
    assert_eq!(rollout_state.policy.automatic_reaction, "pause-channel");
    assert!(rollout_state
        .policy
        .recommended_transport_profile_id
        .is_none());
    assert!(rollout_state
        .policy
        .active_profile_policy
        .as_ref()
        .is_some_and(|policy| policy.suppression_window_active));
    assert!(rollout_state
        .policy
        .recommended_action
        .as_deref()
        .is_some_and(|message| message.contains("Pause Helix rollout")));
}

#[tokio::test]
async fn node_registry_persists_suppression_window_for_blocked_profile_posture() {
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
            manifest_version: "manifest-v11".to_string(),
            target_node_ids: vec![node_id],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    for latency_ms in [640, 660, 680, 700] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-blocked-{latency_ms}"),
                desktop_client_id: format!("desktop-blocked-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v8".to_string(),
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
            .expect("record blocked profile evidence");
    }

    let suppression_count = query_scalar::<_, i64>(
        r#"
        SELECT COUNT(*)
        FROM helix.profile_suppression_windows
        WHERE rollout_id = $1
          AND transport_profile_id = 'ptp-stable-edge-v8'
          AND suppressed_until > NOW()
        "#,
    )
    .bind(&rollout_id)
    .fetch_one(&pool)
    .await
    .expect("query suppression windows");

    assert_eq!(suppression_count, 1);
}

#[tokio::test]
async fn node_registry_extends_suppression_window_for_repeat_blocked_profile_offenses() {
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
            manifest_version: "manifest-v13".to_string(),
            target_node_ids: vec![node_id],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    for latency_ms in [640, 660, 680, 700, 720] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-repeat-blocked-{latency_ms}"),
                desktop_client_id: format!("desktop-repeat-blocked-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v8".to_string(),
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
            .expect("record blocked profile evidence");
    }

    #[derive(sqlx::FromRow)]
    struct SuppressionWindowRow {
        observation_count: i32,
        remaining_minutes: i64,
    }

    let suppression = query_as::<_, SuppressionWindowRow>(
        r#"
        SELECT
            observation_count,
            GREATEST(
                EXTRACT(EPOCH FROM (suppressed_until - NOW())) / 60,
                0
            )::BIGINT AS remaining_minutes
        FROM helix.profile_suppression_windows
        WHERE rollout_id = $1
          AND transport_profile_id = 'ptp-stable-edge-v8'
        "#,
    )
    .bind(&rollout_id)
    .fetch_one(&pool)
    .await
    .expect("query suppression window");

    assert_eq!(suppression.observation_count, 2);
    assert!(suppression.remaining_minutes >= 59);
}

#[tokio::test]
async fn node_registry_rollout_state_rotates_immediately_when_suppressed_profile_has_healthier_alternative(
) {
    let Some(pool) = maybe_test_pool().await else {
        return;
    };

    run_migrations(&pool).await.expect("migrations");

    let repository = NodeRegistryRepository::new(pool.clone());
    let transport_profiles = TransportProfileRepository::new(pool.clone());
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
            manifest_version: "manifest-v12".to_string(),
            target_node_ids: vec![node_id],
            pause_on_rollback_spike: true,
            revoke_on_manifest_error: true,
        })
        .await
        .expect("publish rollout");

    for (transport_profile_id, profile_version) in
        [("ptp-stable-edge-v8", 8), ("ptp-stable-edge-v9", 9)]
    {
        transport_profiles
            .upsert_profile(&UpsertTransportProfileRequest {
                transport_profile_id: transport_profile_id.to_string(),
                channel: RolloutChannel::Stable,
                profile_family: "edge-hybrid".to_string(),
                profile_version,
                policy_version: profile_version,
                protocol_version: 1,
                session_mode: "hybrid".to_string(),
                status: TransportProfileStatus::Active,
                fallback_core: "sing-box".to_string(),
                required_capabilities: vec!["protocol.v1".to_string()],
                compatibility_min_profile_version: 1,
                compatibility_max_profile_version: 9,
                startup_timeout_seconds: 20,
                runtime_unhealthy_threshold: 3,
            })
            .await
            .expect("upsert profile");
    }

    for index in 0..3 {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v8-ready-{}", index + 1),
                desktop_client_id: format!("desktop-v8-ready-{}", index + 1),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v8".to_string(),
                event_kind: DesktopRuntimeEventKind::Ready,
                active_core: DesktopRuntimeCore::Helix,
                fallback_core: None,
                latency_ms: Some(70 + (index * 5)),
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
                        ready_recovery_latency_ms: Some(70 + (index * 5)),
                        ..Default::default()
                    }),
                    ..Default::default()
                },
            })
            .await
            .expect("record v8 ready evidence");
    }

    for latency_ms in [620, 640, 660, 680] {
        repository
            .record_desktop_runtime_event(&DesktopRuntimeEventRequest {
                schema_version: "1.0".to_string(),
                event_id: Uuid::new_v4(),
                user_id: format!("user-v9-fallback-{latency_ms}"),
                desktop_client_id: format!("desktop-v9-fallback-{latency_ms}"),
                manifest_version_id: Uuid::new_v4(),
                rollout_id: rollout_id.clone(),
                transport_profile_id: "ptp-stable-edge-v9".to_string(),
                event_kind: DesktopRuntimeEventKind::Fallback,
                active_core: DesktopRuntimeCore::SingBox,
                fallback_core: Some(DesktopRuntimeCore::SingBox),
                latency_ms: Some(latency_ms),
                route_count: Some(2),
                reason: Some("continuity drift".to_string()),
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
            .expect("record v9 blocked evidence");
    }

    let rollout_state = repository
        .fetch_rollout_state(&rollout_id)
        .await
        .expect("rollout state");

    assert_eq!(
        rollout_state.policy.active_transport_profile_id.as_deref(),
        Some("ptp-stable-edge-v9")
    );
    assert_eq!(
        rollout_state
            .policy
            .recommended_transport_profile_id
            .as_deref(),
        Some("ptp-stable-edge-v8")
    );
    assert_eq!(rollout_state.policy.suppressed_candidate_count, 1);
    assert!(rollout_state.policy.active_profile_suppressed);
    assert_eq!(rollout_state.policy.channel_posture, "critical");
    assert_eq!(
        rollout_state.policy.automatic_reaction,
        "rotate-profile-now"
    );
    assert_eq!(
        rollout_state.policy.applied_automatic_reaction.as_deref(),
        Some("rotate-profile-now")
    );
    assert_eq!(
        rollout_state.policy.applied_transport_profile_id.as_deref(),
        Some("ptp-stable-edge-v8")
    );
    assert!(rollout_state.policy.profile_rotation_recommended);
    assert!(!rollout_state.policy.pause_recommended);
    assert!(rollout_state
        .policy
        .recommended_action
        .as_deref()
        .is_some_and(|message| message.contains("Rotate Helix rollout")));
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
            eprintln!("Skipping DB-backed node registry test: {error}");
            None
        }
    }
}
