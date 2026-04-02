use std::{str::FromStr, time::Duration};

use sqlx::{
    migrate::Migrator,
    postgres::{PgConnectOptions, PgPoolOptions},
    ConnectOptions, PgPool,
};
use tracing::info;

use crate::{config::AdapterConfig, error::AppError};

static MIGRATOR: Migrator = sqlx::migrate!();

pub async fn new_pool(config: &AdapterConfig) -> Result<PgPool, AppError> {
    let options = PgConnectOptions::from_str(&config.database_url)
        .map_err(|error| AppError::Config(format!("invalid DATABASE_URL: {error}")))?
        .application_name("helix-adapter")
        .disable_statement_logging();

    let pool = PgPoolOptions::new()
        .max_connections(config.database_max_connections)
        .acquire_timeout(Duration::from_secs(config.database_acquire_timeout_seconds))
        .connect_with(options)
        .await?;

    Ok(pool)
}

pub async fn run_migrations(pool: &PgPool) -> Result<(), AppError> {
    MIGRATOR
        .run(pool)
        .await
        .map_err(|error| AppError::Internal(error.to_string()))?;
    info!("Helix adapter migrations applied");
    Ok(())
}
