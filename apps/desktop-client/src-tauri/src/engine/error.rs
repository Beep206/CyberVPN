use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Request error: {0}")]
    Reqwest(#[from] reqwest::Error),

    #[error("Zip error: {0}")]
    Zip(#[from] zip::result::ZipError),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Tauri error: {0}")]
    Tauri(#[from] tauri::Error),

    #[error("System error: {0}")]
    System(String),

    #[error("Elevation Required: {0}")]
    ElevationRequired(String),

    #[error("Firewall error: {0}")]
    FirewallError(String),

    #[error("Cloud Sync Conflict: {0}")]
    SyncConflict(String),

    #[error("Decryption Failed: {0}")]
    DecryptionFailed(String),

    #[error("Cloud Unreachable: {0}")]
    CloudUnreachable(String),
}

// Implement Serialize so we can return AppError to the frontend natively in Tauri commands
impl Serialize for AppError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}
