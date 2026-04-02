use helix_node::{
    control_plane::client::{
        NodeAssignmentCompatibilityWindow, NodeAssignmentCredentials, NodeAssignmentDocument,
        NodeAssignmentIntegrity, NodeAssignmentRecovery, NodeAssignmentRuntimeProfile,
        NodeAssignmentTransportProfile, Signature,
    },
    metrics::Metrics,
    runtime::RuntimeCoordinator,
};

fn sample_assignment(
    bundle_version: &str,
    last_known_good_bundle: &str,
    ports: [u16; 2],
) -> NodeAssignmentDocument {
    NodeAssignmentDocument {
        schema_version: "1.1".to_string(),
        assignment_id: format!("assignment-{bundle_version}"),
        rollout_id: "rollout-canary-2026-03-31-b".to_string(),
        node_id: "node-canary-01".to_string(),
        channel: "canary".to_string(),
        issued_at: chrono::Utc::now(),
        expires_at: chrono::Utc::now() + chrono::Duration::minutes(15),
        desired_state: "active".to_string(),
        transport_profile: NodeAssignmentTransportProfile {
            transport_profile_id: "ptp-canary-edge-v3".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 3,
            policy_version: 7,
            compatibility_window: NodeAssignmentCompatibilityWindow {
                min_transport_profile_version: 2,
                max_transport_profile_version: 4,
            },
        },
        runtime_profile: NodeAssignmentRuntimeProfile {
            bundle_version: bundle_version.to_string(),
            min_daemon_version: "v0.1.0".to_string(),
            ports: ports.to_vec(),
            health_check_interval_seconds: 15,
        },
        credentials: NodeAssignmentCredentials {
            key_id: "sig-key-local-dev".to_string(),
            token: "pts_test_canary_token".to_string(),
        },
        recovery: NodeAssignmentRecovery {
            last_known_good_bundle: last_known_good_bundle.to_string(),
            rollback_timeout_seconds: 90,
        },
        integrity: NodeAssignmentIntegrity {
            assignment_hash:
                "sha256:3333333333333333333333333333333333333333333333333333333333333333"
                    .to_string(),
            signature: Signature {
                alg: "ed25519".to_string(),
                key_id: "sig-key-local-dev".to_string(),
                sig: "ed25519signodeassignmentabcdefghijklmnopqrstuvwxyz".to_string(),
            },
        },
    }
}

#[tokio::test]
async fn unhealthy_assignment_restores_last_known_good_bundle() {
    let tempdir = tempfile::tempdir().expect("tempdir");
    let metrics = Metrics::new("helix_node_rollback_test").expect("metrics");

    let runtime = RuntimeCoordinator::new(
        tempdir.path().to_path_buf(),
        "node-canary-01".to_string(),
        "instance-b".to_string(),
        "v0.1.0".to_string(),
        false,
    )
    .await
    .expect("runtime");

    runtime.restore_state().await.expect("restore bootstrap");
    runtime
        .sync_assignment(
            &sample_assignment("bundle-good", "bundle-bootstrap", [17443, 20443]),
            &metrics,
            1,
        )
        .await
        .expect("apply healthy bundle");

    runtime
        .supervisor()
        .force_unhealthy_bundle_for_tests("bundle-bad")
        .await;

    let snapshot = runtime
        .sync_assignment(
            &sample_assignment("bundle-bad", "bundle-good", [17443, 20443]),
            &metrics,
            1,
        )
        .await
        .expect("roll back after unhealthy bundle");

    assert_eq!(
        snapshot.active_bundle_version.as_deref(),
        Some("bundle-good")
    );
    assert_eq!(
        snapshot.last_known_good_bundle.as_deref(),
        Some("bundle-good")
    );
    assert_eq!(snapshot.apply_state, "rolled-back");
    assert_eq!(snapshot.rollback_total, 1);
    assert!(snapshot.last_error.is_some());
}
