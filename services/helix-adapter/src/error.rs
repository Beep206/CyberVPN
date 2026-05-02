use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::Serialize;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("unauthorized")]
    Unauthorized,
    #[error("bad request: {0}")]
    BadRequest(String),
    #[error("configuration error: {0}")]
    Config(String),
    #[error("resource not found: {0}")]
    NotFound(String),
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("upstream request failed: {0}")]
    Upstream(#[from] reqwest::Error),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("internal error: {0}")]
    Internal(String),
}

impl AppError {
    pub fn kind(&self) -> &'static str {
        match self {
            AppError::Unauthorized => "unauthorized",
            AppError::BadRequest(_) => "bad_request",
            AppError::Config(_) => "config",
            AppError::NotFound(_) => "not_found",
            AppError::Database(_) => "database",
            AppError::Upstream(_) => "upstream",
            AppError::Serialization(_) => "serialization",
            AppError::Internal(_) => "internal",
        }
    }

    pub fn should_capture(&self) -> bool {
        matches!(
            self,
            AppError::Database(_)
                | AppError::Upstream(_)
                | AppError::Serialization(_)
                | AppError::Internal(_)
        )
    }
}

#[derive(Debug, Serialize)]
struct ErrorBody {
    error: String,
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let status = match &self {
            AppError::Unauthorized => StatusCode::UNAUTHORIZED,
            AppError::BadRequest(_) | AppError::Config(_) => StatusCode::BAD_REQUEST,
            AppError::NotFound(_) => StatusCode::NOT_FOUND,
            AppError::Database(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Upstream(_) => StatusCode::BAD_GATEWAY,
            AppError::Serialization(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };

        crate::observability::capture_app_error(&self, status.as_u16());

        let body = Json(ErrorBody {
            error: self.to_string(),
        });

        (status, body).into_response()
    }
}
