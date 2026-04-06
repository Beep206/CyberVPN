use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("configuration error: {0}")]
    Config(String),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("request error: {0}")]
    Reqwest(#[from] reqwest::Error),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("metrics error: {0}")]
    Metrics(String),

    #[error("system error: {0}")]
    System(String),
}

impl From<helix_runtime::TransportError> for AppError {
    fn from(value: helix_runtime::TransportError) -> Self {
        Self::System(value.to_string())
    }
}
