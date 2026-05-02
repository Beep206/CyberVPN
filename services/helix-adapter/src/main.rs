use tokio::signal;
use tracing::info;
use tracing_subscriber::prelude::*;
use tracing_subscriber::EnvFilter;

use helix_adapter::{
    app_state::AppState, build_app, build_smoke_state, build_state, config::AdapterConfig,
    observability::init_sentry,
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = AdapterConfig::from_env()?;
    let _sentry = init_sentry(&config)?;

    tracing_subscriber::registry()
        .with(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new(config.log_level.clone())),
        )
        .with(tracing_subscriber::fmt::layer())
        .with(sentry::integrations::tracing::layer())
        .init();

    let state = if config.smoke_mode {
        info!("helix-adapter smoke mode enabled; using lazy runtime dependencies");
        build_smoke_state(config.clone())?
    } else {
        build_state(config.clone()).await?
    };
    let app = build_app(state.clone());
    let listener = tokio::net::TcpListener::bind(&config.bind_addr).await?;

    info!("helix-adapter starting on {}", config.bind_addr);

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal(state))
        .await?;

    Ok(())
}

async fn shutdown_signal(state: AppState) {
    let _ = signal::ctrl_c().await;
    state.set_ready(false);
    info!("shutdown signal received");
}
