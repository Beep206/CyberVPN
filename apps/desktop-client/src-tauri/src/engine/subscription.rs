use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use base64::prelude::*;
use std::time::Duration;

pub async fn fetch_and_parse_subscription(url: &str) -> Result<Vec<ProxyNode>, AppError> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| AppError::System(format!("Failed to build HTTP client: {}", e)))?;

    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| AppError::System(format!("Failed to fetch subscription: {}", e)))?;

    if !response.status().is_success() {
        return Err(AppError::System(format!(
            "Subscription fetch failed with status: {}",
            response.status()
        )));
    }

    let body = response
        .text()
        .await
        .map_err(|e| AppError::System(format!("Failed to read subscription body: {}", e)))?;

    // Try decoding as Base64, fallback to treating it as raw text if all decodes fail
    let decoded_body = match BASE64_URL_SAFE_NO_PAD
        .decode(body.trim())
        .or_else(|_| BASE64_URL_SAFE.decode(body.trim()))
        .or_else(|_| BASE64_STANDARD_NO_PAD.decode(body.trim()))
        .or_else(|_| BASE64_STANDARD.decode(body.trim()))
    {
        Ok(bytes) => String::from_utf8_lossy(&bytes).to_string(),
        Err(_) => body, // Fallback to raw plaintext if not base64
    };

    let nodes: Vec<ProxyNode> = decoded_body
        .lines()
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
        .filter_map(|line| crate::engine::parser::parse_link(line).ok())
        .collect();

    Ok(nodes)
}
