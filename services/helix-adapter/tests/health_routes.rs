use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use tower::ServiceExt;

use helix_adapter::{build_app, build_test_state};

#[tokio::test]
async fn healthz_returns_ok() {
    let app = build_app(build_test_state().expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/healthz")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body = String::from_utf8(body.to_vec()).unwrap();
    assert!(body.contains("\"status\":\"ok\""));
    assert!(body.contains("\"environment\":\"development\""));
}

#[tokio::test]
async fn readyz_returns_ready() {
    let app = build_app(build_test_state().expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/readyz")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body = String::from_utf8(body.to_vec()).unwrap();
    assert!(body.contains("\"status\":\"ready\""));
    assert!(body.contains("\"environment\":\"development\""));
}

#[tokio::test]
async fn sentry_contract_probe_rejects_missing_secret() {
    let app = build_app(build_test_state().expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/observability/sentry-contract")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::FORBIDDEN);
}

#[tokio::test]
async fn sentry_contract_probe_returns_runtime_snapshot() {
    let app = build_app(build_test_state().expect("state"));

    let response = app
        .oneshot(
            Request::builder()
                .uri("/observability/sentry-contract")
                .header("x-observability-secret", "helix-adapter-test-secret")
                .body(axum::body::Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body = String::from_utf8(body.to_vec()).unwrap();
    assert!(body.contains("\"runtime_surface\":\"helix-adapter\""));
    assert!(body.contains("\"service\":\"helix-adapter\""));
    assert!(body.contains("\"environment\":\"development\""));
    assert!(body.contains("\"release\":\"helix-adapter@0.1.0+local\""));
    assert!(body.contains("\"dsn_configured\":true"));
}
