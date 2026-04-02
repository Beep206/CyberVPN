use crate::engine::error::AppError;
use axum::{
    extract::State,
    http::{header, HeaderMap, StatusCode},
    response::{Html, IntoResponse},
    routing::{get, post},
    Json, Router,
};
use rust_embed::RustEmbed;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tauri::AppHandle;
use tokio::sync::Mutex;
use tokio_util::sync::CancellationToken;
use tower_http::cors::CorsLayer;

#[derive(RustEmbed)]
#[folder = "assets/remote/"]
struct Assets;

#[derive(Clone)]
pub struct ServerState {
    pub app: AppHandle,
    pub secret: String,
}

lazy_static::lazy_static! {
    pub static ref REMOTE_TOKEN: Mutex<Option<CancellationToken>> = Mutex::new(None);
}

pub async fn start_remote_server(app: AppHandle) -> Result<String, AppError> {
    let mut token_guard = REMOTE_TOKEN.lock().await;

    if token_guard.is_some() {
        return Err(AppError::System("Remote server is already running".into()));
    }

    let ip = crate::engine::sys::net::get_local_ip().unwrap_or_else(|| "0.0.0.0".to_string());
    let secret = uuid::Uuid::new_v4().to_string();
    let port = 8080;

    let cancel_token = CancellationToken::new();
    *token_guard = Some(cancel_token.clone());

    let state = ServerState {
        app: app.clone(),
        secret: secret.clone(),
    };

    let app_router = Router::new()
        .route("/", get(serve_index))
        .route("/api/remote/status", get(api_status))
        .route("/api/remote/connect", post(api_connect))
        .route("/api/remote/disconnect", post(api_disconnect))
        .route("/api/remote/stats", get(api_stats))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .map_err(|e| AppError::System(format!("Failed to bind to {}: {}", addr, e)))?;

    println!("Axum LAN remote server listening on {}", addr);

    tokio::spawn(async move {
        axum::serve(listener, app_router)
            .with_graceful_shutdown(cancel_token.cancelled_owned())
            .await
            .unwrap();
        println!("Axum LAN remote server gracefully shut down.");
    });

    Ok(format!("http://{}:{}/?key={}", ip, port, secret))
}

pub async fn stop_remote_server() {
    let mut token_guard = REMOTE_TOKEN.lock().await;
    if let Some(token) = token_guard.take() {
        token.cancel();
    }
}

// Basic Middleware check
fn check_auth(headers: &HeaderMap, secret: &str) -> bool {
    if let Some(auth_header) = headers.get(header::AUTHORIZATION) {
        if let Ok(auth_str) = auth_header.to_str() {
            if auth_str == format!("Bearer {}", secret) {
                return true;
            }
        }
    }
    false
}

// ---------------------------------------------------------
// Endpoints
// ---------------------------------------------------------

async fn serve_index() -> impl IntoResponse {
    let index_file = Assets::get("index.html");
    match index_file {
        Some(file) => {
            let html_str = String::from_utf8(file.data.into_owned()).unwrap_or_else(|_| "Error decoding HTML".into());
            Html(html_str).into_response()
        }
        None => (
            StatusCode::NOT_FOUND,
            Html("<h1>404 Not Found</h1><p>Ensure Phase 31 React/HTML dashboard is compiled into assets/remote.</p>".to_string()),
        ).into_response(),
    }
}

#[derive(Serialize)]
struct StatusResponse {
    status: String,
    active_id: Option<String>,
}

async fn api_status(
    State(state): State<ServerState>,
    headers: HeaderMap,
) -> Result<Json<StatusResponse>, StatusCode> {
    if !check_auth(&headers, &state.secret) {
        return Err(StatusCode::UNAUTHORIZED);
    }

    use tauri::Manager;
    let app_state = state.app.state::<crate::ipc::AppState>();
    let status_lock = app_state.status.read().await;

    Ok(Json(StatusResponse {
        status: status_lock.status.clone(),
        active_id: status_lock.active_id.clone(),
    }))
}

#[derive(Deserialize)]
struct ConnectCommand {
    profile_id: String,
}

async fn api_connect(
    State(state): State<ServerState>,
    headers: HeaderMap,
    Json(payload): Json<ConnectCommand>,
) -> Result<&'static str, StatusCode> {
    if !check_auth(&headers, &state.secret) {
        return Err(StatusCode::UNAUTHORIZED);
    }

    // Call connect_profile asynchronously without awaiting its full completion
    // to instantly return 200 OK to the mobile device.
    use tauri::Manager;
    let app_clone1 = state.app.clone();
    let app_clone2 = state.app.clone();
    let profile_id = payload.profile_id;

    tokio::spawn(async move {
        let app_state = app_clone1.state::<crate::ipc::AppState>();
        // Using tun_mode=false, system_proxy=true by default for simplicity on remote,
        // or we could extract these from user preferences. For Phase 31, sticking to system_proxy.
        let _ = crate::ipc::connect_profile(profile_id, false, false, app_clone2, app_state).await;
    });

    Ok("Connecting...")
}

async fn api_disconnect(
    State(state): State<ServerState>,
    headers: HeaderMap,
) -> Result<&'static str, StatusCode> {
    if !check_auth(&headers, &state.secret) {
        return Err(StatusCode::UNAUTHORIZED);
    }

    use tauri::Manager;
    let app_clone1 = state.app.clone();
    let app_clone2 = state.app.clone();
    let app_state = app_clone1.state::<crate::ipc::AppState>();

    // This is safe because disconnect completes quickly
    let _ = crate::ipc::disconnect(app_clone2, app_state).await;
    Ok("Disconnected")
}

#[derive(Serialize)]
struct StatsResponse {
    up: u64,
    down: u64,
}

async fn api_stats(
    State(state): State<ServerState>,
    headers: HeaderMap,
) -> Result<Json<StatsResponse>, StatusCode> {
    if !check_auth(&headers, &state.secret) {
        return Err(StatusCode::UNAUTHORIZED);
    }
    // Pull the active buffered stats from Phase 30
    if let Ok(mut session) = crate::engine::sys::stats::ACTIVE_SESSION.lock() {
        if let Some(sess) = session.as_mut() {
            return Ok(Json(StatsResponse {
                up: sess.session_up,
                down: sess.session_down,
            }));
        }
    }
    Ok(Json(StatsResponse { up: 0, down: 0 }))
}
