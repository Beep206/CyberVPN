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
}
