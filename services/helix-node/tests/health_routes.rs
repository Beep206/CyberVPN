use axum::{
    body::{to_bytes, Body},
    http::{Request, StatusCode},
};
use tower::ServiceExt;

use helix_node::{build_app, build_test_state};

#[tokio::test]
async fn healthz_returns_runtime_snapshot() {
    let app = build_app(build_test_state().await.expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/healthz")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let body = String::from_utf8(body.to_vec()).unwrap();
    assert!(body.contains("\"status\":\"degraded\""));
    assert!(body.contains("\"service\":\"helix-node\""));
    assert!(body.contains("\"environment\":\"development\""));
    assert!(body.contains("\"node_id\":\"node-test-01\""));
}

#[tokio::test]
async fn sentry_contract_probe_rejects_missing_secret() {
    let app = build_app(build_test_state().await.expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/observability/sentry-contract")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::FORBIDDEN);
}

#[tokio::test]
async fn sentry_contract_probe_returns_runtime_snapshot() {
    let app = build_app(build_test_state().await.expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/observability/sentry-contract")
                .header("x-observability-secret", "helix-node-test-secret")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let body = String::from_utf8(body.to_vec()).unwrap();
    assert!(body.contains("\"runtime_surface\":\"helix-node\""));
    assert!(body.contains("\"service\":\"helix-node\""));
    assert!(body.contains("\"environment\":\"development\""));
    assert!(body.contains("\"release\":\"helix-node@0.1.0+local\""));
    assert!(body.contains("\"dsn_configured\":true"));
    assert!(body.contains("\"node_id\":\"node-test-01\""));
    assert!(body.contains("\"daemon_version\":\"v0.1.0\""));
}
