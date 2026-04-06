pub mod app_state;
pub mod assignments;
pub mod config;
pub mod db;
pub mod error;
pub mod http;
pub mod manifests;
pub mod metrics;
pub mod node_registry;
pub mod remnawave;
pub mod session_credentials;
pub mod transport_profiles;

use sqlx::postgres::PgPoolOptions;

use crate::{
    app_state::AppState,
    assignments::store::NodeAssignmentStore,
    config::AdapterConfig,
    error::AppError,
    manifests::{renderer::ManifestRenderer, signer::ManifestSigner, store::ManifestStore},
    metrics::Metrics,
    node_registry::{repository::NodeRegistryRepository, service::NodeRegistryService},
    remnawave::client::RemnawaveClient,
    transport_profiles::{
        repository::TransportProfileRepository, service::TransportProfileService,
    },
};

pub async fn build_state(config: AdapterConfig) -> Result<AppState, AppError> {
    let metrics = Metrics::new(&config.metrics_prefix)?;
    let pool = db::pool::new_pool(&config).await?;
    db::pool::run_migrations(&pool).await?;

    let remnawave_client = RemnawaveClient::new(&config)?;
    let node_registry_repository = NodeRegistryRepository::new(pool.clone());
    let transport_profile_repository = TransportProfileRepository::new(pool.clone());
    let node_registry_service =
        NodeRegistryService::new(node_registry_repository.clone(), remnawave_client);
    let transport_profile_service = TransportProfileService::new(transport_profile_repository);
    let manifest_signer = ManifestSigner::new(
        &config.manifest_signing_key,
        &config.manifest_signing_key_id,
    )?;
    let manifest_store = ManifestStore::new(
        pool.clone(),
        node_registry_repository.clone(),
        transport_profile_service.clone(),
        ManifestRenderer::new(config.metrics_prefix.clone()),
        manifest_signer.clone(),
    );
    let assignment_store = NodeAssignmentStore::new(
        pool,
        node_registry_repository,
        transport_profile_service.clone(),
        manifest_signer,
    );

    Ok(AppState::new(
        config,
        metrics,
        node_registry_service,
        transport_profile_service,
        manifest_store,
        assignment_store,
    ))
}

pub fn build_app(state: AppState) -> axum::Router {
    http::build_router(state)
}

pub fn build_test_state() -> Result<AppState, AppError> {
    let config = AdapterConfig::test_default();
    let metrics = Metrics::new(&config.metrics_prefix)?;
    let pool = PgPoolOptions::new()
        .max_connections(1)
        .connect_lazy(&config.database_url)
        .map_err(AppError::Database)?;
    let remnawave_client = RemnawaveClient::new(&config)?;
    let node_registry_repository = NodeRegistryRepository::new(pool.clone());
    let transport_profile_repository = TransportProfileRepository::new(pool.clone());
    let node_registry_service =
        NodeRegistryService::new(node_registry_repository.clone(), remnawave_client);
    let transport_profile_service = TransportProfileService::new(transport_profile_repository);
    let manifest_signer = ManifestSigner::new(
        &config.manifest_signing_key,
        &config.manifest_signing_key_id,
    )?;
    let manifest_store = ManifestStore::new(
        pool.clone(),
        node_registry_repository.clone(),
        transport_profile_service.clone(),
        ManifestRenderer::new(config.metrics_prefix.clone()),
        manifest_signer.clone(),
    );
    let assignment_store = NodeAssignmentStore::new(
        pool,
        node_registry_repository,
        transport_profile_service.clone(),
        manifest_signer,
    );

    Ok(AppState::new(
        config,
        metrics,
        node_registry_service,
        transport_profile_service,
        manifest_store,
        assignment_store,
    ))
}
