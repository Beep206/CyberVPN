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
        rollout_id: "rollout-lab-2026-03-31-a".to_string(),
        node_id: "node-lab-01".to_string(),
        channel: "lab".to_string(),
        issued_at: chrono::Utc::now(),
        expires_at: chrono::Utc::now() + chrono::Duration::minutes(15),
        desired_state: "active".to_string(),
        transport_profile: NodeAssignmentTransportProfile {
            transport_profile_id: "ptp-lab-edge-v2".to_string(),
            profile_family: "edge-hybrid".to_string(),
            profile_version: 2,
            policy_version: 4,
            compatibility_window: NodeAssignmentCompatibilityWindow {
                min_transport_profile_version: 1,
                max_transport_profile_version: 3,
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
            token: "pts_test_lab_token".to_string(),
        },
        recovery: NodeAssignmentRecovery {
            last_known_good_bundle: last_known_good_bundle.to_string(),
            rollback_timeout_seconds: 90,
        },
        integrity: NodeAssignmentIntegrity {
            assignment_hash:
                "sha256:2222222222222222222222222222222222222222222222222222222222222222"
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
async fn runtime_state_restores_after_restart() {
    let tempdir = tempfile::tempdir().expect("tempdir");
    let metrics = Metrics::new("helix_node_test").expect("metrics");
    let assignment = sample_assignment("bundle-good", "bundle-bootstrap", [15443, 18443]);

    let runtime = RuntimeCoordinator::new(
        tempdir.path().to_path_buf(),
        "node-lab-01".to_string(),
        "instance-a".to_string(),
        "v0.1.0".to_string(),
        false,
    )
    .await
    .expect("runtime");

    runtime.restore_state().await.expect("restore bootstrap");
    runtime
        .sync_assignment(&assignment, &metrics, 1)
        .await
        .expect("apply assignment");
    runtime.supervisor().shutdown().await;

    let restored = RuntimeCoordinator::new(
        tempdir.path().to_path_buf(),
        "node-lab-01".to_string(),
        "instance-a".to_string(),
        "v0.1.0".to_string(),
        false,
    )
    .await
    .expect("runtime after restart");

    let snapshot = restored.restore_state().await.expect("restore snapshot");

    assert_eq!(
        snapshot.active_bundle_version.as_deref(),
        Some("bundle-good")
    );
    assert_eq!(
        snapshot.last_known_good_bundle.as_deref(),
        Some("bundle-good")
    );
    assert!(snapshot.ready);
    assert!(snapshot.runtime_healthy);

    let reapplied = restored
        .sync_assignment(&assignment, &metrics, 1)
        .await
        .expect("re-apply restored assignment to supervisor");
    assert_eq!(reapplied.active_bundle_version.as_deref(), Some("bundle-good"));
    assert_eq!(
        restored.supervisor().current_bundle().await.as_deref(),
        Some("bundle-good")
    );
}

#[tokio::test]
async fn repeated_semantically_identical_assignment_does_not_reapply_runtime() {
    let tempdir = tempfile::tempdir().expect("tempdir");
    let metrics = Metrics::new("helix_node_idempotency_test").expect("metrics");

    let runtime = RuntimeCoordinator::new(
        tempdir.path().to_path_buf(),
        "node-lab-01".to_string(),
        "instance-a".to_string(),
        "v0.1.0".to_string(),
        false,
    )
    .await
    .expect("runtime");

    runtime.restore_state().await.expect("restore bootstrap");

    let first_assignment =
        sample_assignment("bundle-good", "bundle-bootstrap", [16443, 19443]);
    runtime
        .sync_assignment(&first_assignment, &metrics, 1)
        .await
        .expect("apply initial assignment");

    runtime
        .supervisor()
        .force_unhealthy_bundle_for_tests("bundle-good")
        .await;

    let mut repeated_assignment = sample_assignment("bundle-good", "bundle-good", [16443, 19443]);
    repeated_assignment.assignment_id = "assignment-bundle-good-rotated".to_string();

    let snapshot = runtime
        .sync_assignment(&repeated_assignment, &metrics, 1)
        .await
        .expect("skip reapply for rotated assignment id");

    assert_eq!(
        snapshot.active_bundle_version.as_deref(),
        Some("bundle-good")
    );
    assert_eq!(snapshot.apply_state, "idle");
    assert_eq!(snapshot.rollback_total, 0);
    assert!(snapshot.ready);
    assert!(snapshot.runtime_healthy);
    assert!(snapshot.last_error.is_none());
}
