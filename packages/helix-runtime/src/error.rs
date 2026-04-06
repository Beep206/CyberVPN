use thiserror::Error;

#[derive(Debug, Error)]
pub enum TransportError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("codec error: {0}")]
    Codec(#[from] postcard::Error),

    #[error("protocol error: {0}")]
    Protocol(String),

    #[error("cryptography error: {0}")]
    Crypto(String),

    #[error("timeout: {0}")]
    Timeout(String),

    #[error("channel closed: {0}")]
    ChannelClosed(&'static str),
}
