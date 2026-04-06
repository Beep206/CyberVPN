use std::time::Duration;

use keyring::Entry;
use reqwest::Client;

use crate::engine::{
    error::AppError,
    helix::config::{
        HelixCapabilityDefaults, HelixResolveManifestRequest, HelixResolvedManifest,
        HelixRuntimeEventRequest,
    },
};

const HELIX_KEYRING_SERVICE: &str = "CyberVPN_Helix";
const HELIX_BACKEND_TOKEN_ACCOUNT: &str = "backend_access_token";

fn build_client() -> Result<Client, AppError> {
    Client::builder()
        .timeout(Duration::from_secs(10))
        .user_agent(format!(
            "{}/{}",
            env!("CARGO_PKG_NAME"),
            env!("CARGO_PKG_VERSION")
        ))
        .build()
        .map_err(AppError::Reqwest)
}

fn build_event_client() -> Result<Client, AppError> {
    Client::builder()
        .timeout(Duration::from_secs(3))
        .user_agent(format!(
            "{}/{}",
            env!("CARGO_PKG_NAME"),
            env!("CARGO_PKG_VERSION")
        ))
        .build()
        .map_err(AppError::Reqwest)
}

fn backend_access_token_entry() -> Result<Entry, AppError> {
    Entry::new(HELIX_KEYRING_SERVICE, HELIX_BACKEND_TOKEN_ACCOUNT)
        .map_err(|error| AppError::System(format!("Failed to access Helix keyring: {error}")))
}

pub fn save_backend_access_token(access_token: &str) -> Result<(), AppError> {
    backend_access_token_entry()?
        .set_password(access_token)
        .map_err(|error| {
            AppError::System(format!(
                "Failed to save Helix backend access token: {error}"
            ))
        })
}

pub fn load_backend_access_token() -> Result<String, AppError> {
    backend_access_token_entry()?
        .get_password()
        .map_err(|error| {
            AppError::System(format!(
                "Helix backend access token is unavailable: {error}"
            ))
        })
}

pub async fn fetch_capability_defaults(
    base_url: &str,
    access_token: &str,
) -> Result<HelixCapabilityDefaults, AppError> {
    let response = build_client()?
        .get(format!(
            "{}/api/v1/helix/capabilities",
            base_url.trim_end_matches('/')
        ))
        .bearer_auth(access_token)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Helix capability fetch failed with status: {}",
            response.status()
        )));
    }

    response.json().await.map_err(AppError::Reqwest)
}

pub async fn report_runtime_event(
    base_url: &str,
    access_token: &str,
    request: &HelixRuntimeEventRequest,
) -> Result<(), AppError> {
    let response = build_event_client()?
        .post(format!(
            "{}/api/v1/helix/events/runtime",
            base_url.trim_end_matches('/')
        ))
        .bearer_auth(access_token)
        .json(request)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Helix runtime event report failed with status: {}",
            response.status()
        )));
    }

    Ok(())
}

pub async fn resolve_manifest(
    base_url: &str,
    access_token: &str,
    request: &HelixResolveManifestRequest,
) -> Result<HelixResolvedManifest, AppError> {
    let response = build_client()?
        .post(format!(
            "{}/api/v1/helix/manifest",
            base_url.trim_end_matches('/')
        ))
        .bearer_auth(access_token)
        .json(request)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Helix manifest resolve failed with status: {}",
            response.status()
        )));
    }

    response.json().await.map_err(AppError::Reqwest)
}
