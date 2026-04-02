use reqwest::header::{AUTHORIZATION, CONTENT_TYPE};
use serde::{Deserialize, Serialize};

use crate::{config::AdapterConfig, error::AppError};

#[derive(Debug, Clone)]
pub struct RemnawaveClient {
    base_url: String,
    token: String,
    client: reqwest::Client,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeInventoryItem {
    pub id: String,
    pub name: String,
    pub hostname: Option<String>,
    pub enabled: Option<bool>,
}

impl RemnawaveClient {
    pub fn new(config: &AdapterConfig) -> Result<Self, AppError> {
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()?;

        Ok(Self {
            base_url: config.remnawave_url.trim_end_matches('/').to_string(),
            token: config.remnawave_token.clone(),
            client,
        })
    }

    pub async fn list_nodes(&self) -> Result<Vec<NodeInventoryItem>, AppError> {
        let response = self
            .client
            .get(format!("{}/api/nodes", self.base_url))
            .header(AUTHORIZATION, format!("Bearer {}", self.token))
            .header(CONTENT_TYPE, "application/json")
            .send()
            .await?
            .error_for_status()?;

        let nodes = response.json::<Vec<NodeInventoryItem>>().await?;
        Ok(nodes)
    }
}
