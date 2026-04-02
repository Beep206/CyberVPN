use tokio::signal;
use tracing::info;
use tracing_subscriber::EnvFilter;

use helix_node::{build_app, build_state, config::NodeConfig, spawn_control_loop};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = NodeConfig::from_env()?;

    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new(config.log_level.clone())),
        )
        .init();

    let state = build_state(config.clone()).await?;
    let app = build_app(state.clone());
    let listener = tokio::net::TcpListener::bind(&config.bind_addr).await?;

    spawn_control_loop(state.clone());

    info!(
        "helix-node starting on {} for node {}",
        config.bind_addr, config.node_id
    );

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal(state))
        .await?;

    Ok(())
}

async fn shutdown_signal(state: helix_node::state::AppState) {
    let _ = signal::ctrl_c().await;
    state.set_ready(false);
    info!("shutdown signal received");
}
