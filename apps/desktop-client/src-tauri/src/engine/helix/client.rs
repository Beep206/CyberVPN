use std::time::Duration;

use keyring::Entry;
use reqwest::Client;
use serde::{de::DeserializeOwned, Serialize};

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

async fn ensure_success(
    response: reqwest::Response,
    failure_message: &str,
) -> Result<reqwest::Response, AppError> {
    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(AppError::System(format!(
            "{failure_message} with status {status}: {body}"
        )));
    }

    Ok(response)
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
    let response = ensure_success(
        build_client()?
            .get(format!(
                "{}/api/v1/helix/capabilities",
                base_url.trim_end_matches('/')
            ))
            .bearer_auth(access_token)
            .send()
            .await?,
        "Helix capability fetch failed",
    )
    .await?;

    response.json().await.map_err(AppError::Reqwest)
}

pub async fn fetch_authenticated_get<T>(
    base_url: &str,
    access_token: &str,
    path: &str,
) -> Result<T, AppError>
where
    T: DeserializeOwned,
{
    let response = ensure_success(
        build_client()?
            .get(format!("{}{}", base_url.trim_end_matches('/'), path))
            .bearer_auth(access_token)
            .send()
            .await?,
        "Canonical backend GET failed",
    )
    .await?;

    response.json().await.map_err(AppError::Reqwest)
}

pub async fn fetch_authenticated_post_json<T, P>(
    base_url: &str,
    access_token: &str,
    path: &str,
    payload: &P,
) -> Result<T, AppError>
where
    T: DeserializeOwned,
    P: Serialize + ?Sized,
{
    let response = ensure_success(
        build_client()?
            .post(format!("{}{}", base_url.trim_end_matches('/'), path))
            .bearer_auth(access_token)
            .json(payload)
            .send()
            .await?,
        "Canonical backend POST failed",
    )
    .await?;

    response.json().await.map_err(AppError::Reqwest)
}

pub async fn report_runtime_event(
    base_url: &str,
    access_token: &str,
    request: &HelixRuntimeEventRequest,
) -> Result<(), AppError> {
    ensure_success(
        build_event_client()?
            .post(format!(
                "{}/api/v1/helix/events/runtime",
                base_url.trim_end_matches('/')
            ))
            .bearer_auth(access_token)
            .json(request)
            .send()
            .await?,
        "Helix runtime event report failed",
    )
    .await?;

    Ok(())
}

pub async fn resolve_manifest(
    base_url: &str,
    access_token: &str,
    request: &HelixResolveManifestRequest,
) -> Result<HelixResolvedManifest, AppError> {
    let response = ensure_success(
        build_client()?
            .post(format!(
                "{}/api/v1/helix/manifest",
                base_url.trim_end_matches('/')
            ))
            .bearer_auth(access_token)
            .json(request)
            .send()
            .await?,
        "Helix manifest resolve failed",
    )
    .await?;

    response.json().await.map_err(AppError::Reqwest)
}
