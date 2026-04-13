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
pub struct NodeInventoryVersions {
    #[serde(default)]
    pub xray: Option<String>,
    #[serde(default)]
    pub node: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeInventoryItem {
    #[serde(alias = "uuid")]
    pub id: String,
    pub name: String,
    #[serde(default, alias = "address")]
    pub hostname: Option<String>,
    #[serde(default)]
    pub enabled: Option<bool>,
    #[serde(default, alias = "isDisabled")]
    pub is_disabled: Option<bool>,
    #[serde(default, alias = "isConnected")]
    pub is_connected: Option<bool>,
    #[serde(default, alias = "isConnecting")]
    pub is_connecting: Option<bool>,
    #[serde(default, alias = "countryCode")]
    pub country_code: Option<String>,
    #[serde(default, alias = "activePluginUuid")]
    pub active_plugin_uuid: Option<String>,
    #[serde(default, alias = "nodeVersion")]
    pub node_version: Option<String>,
    #[serde(default, alias = "xrayVersion")]
    pub xray_version: Option<String>,
    #[serde(default)]
    pub versions: Option<NodeInventoryVersions>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
enum ListNodesResponse {
    Bare(Vec<NodeInventoryItem>),
    Wrapped { response: Vec<NodeInventoryItem> },
}

impl NodeInventoryItem {
    pub fn effective_enabled(&self) -> Option<bool> {
        self.enabled
            .or_else(|| self.is_disabled.map(|is_disabled| !is_disabled))
    }

    pub fn effective_node_version(&self) -> Option<&str> {
        self.node_version.as_deref().or_else(|| {
            self.versions
                .as_ref()
                .and_then(|versions| versions.node.as_deref())
        })
    }

    pub fn effective_xray_version(&self) -> Option<&str> {
        self.xray_version.as_deref().or_else(|| {
            self.versions
                .as_ref()
                .and_then(|versions| versions.xray.as_deref())
        })
    }
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

        let payload = response.json::<ListNodesResponse>().await?;
        Ok(match payload {
            ListNodesResponse::Bare(nodes) => nodes,
            ListNodesResponse::Wrapped { response } => response,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::{ListNodesResponse, NodeInventoryItem};

    #[test]
    fn node_inventory_item_accepts_current_remnawave_shape() {
        let payload = include_str!("../../tests/fixtures/remnawave/node_inventory_item_2_7_4.json");
        let item: NodeInventoryItem =
            serde_json::from_str(payload).expect("current Remnawave inventory payload");

        assert_eq!(item.id, "550e8400-e29b-41d4-a716-446655440010");
        assert_eq!(item.hostname.as_deref(), Some("fra-01.example.com"));
        assert_eq!(item.country_code.as_deref(), Some("DE"));
        assert_eq!(
            item.active_plugin_uuid.as_deref(),
            Some("550e8400-e29b-41d4-a716-446655440099")
        );
        assert_eq!(item.effective_enabled(), Some(true));
        assert_eq!(item.effective_node_version(), Some("2.7.4"));
        assert_eq!(item.effective_xray_version(), Some("1.8.10"));
    }

    #[test]
    fn list_nodes_response_accepts_wrapped_payloads() {
        let payload =
            include_str!("../../tests/fixtures/remnawave/node_inventory_wrapped_2_7_4.json");
        let payload: ListNodesResponse =
            serde_json::from_str(payload).expect("wrapped Remnawave list response");

        match payload {
            ListNodesResponse::Bare(_) => panic!("expected wrapped node inventory payload"),
            ListNodesResponse::Wrapped { response } => {
                assert_eq!(response.len(), 1);
                assert_eq!(response[0].id, "550e8400-e29b-41d4-a716-446655440011");
                assert_eq!(response[0].hostname.as_deref(), Some("ams-01.example.com"));
            }
        }
    }
}
