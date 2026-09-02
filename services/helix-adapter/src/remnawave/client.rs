use std::net::IpAddr;

use reqwest::header::{AUTHORIZATION, CONTENT_TYPE};
use serde::{Deserialize, Deserializer, Serialize};
use uuid::Uuid;

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
    #[serde(deserialize_with = "deserialize_positive_node_id")]
    pub id: i64,
    pub uuid: Uuid,
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
    #[serde(deserialize_with = "deserialize_node_ips")]
    pub ips: Vec<NodeInventoryIp>,
    #[serde(
        rename = "integrationUuids",
        deserialize_with = "deserialize_integration_uuids"
    )]
    pub integration_uuids: Vec<Uuid>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NodeIpStatus {
    Inbound,
    Outbound,
    Management,
    Transit,
    Monitoring,
    Reserve,
    Blocked,
    Flagged,
    Deprecated,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct NodeInventoryIp {
    pub ip: IpAddr,
    pub status: NodeIpStatus,
}

fn deserialize_node_ips<'de, D>(deserializer: D) -> Result<Vec<NodeInventoryIp>, D::Error>
where
    D: Deserializer<'de>,
{
    let ips = Vec::<NodeInventoryIp>::deserialize(deserializer)?;
    if ips.len() > 64 {
        return Err(serde::de::Error::custom(
            "Remnawave node ips must contain no more than 64 entries",
        ));
    }
    Ok(ips)
}

fn deserialize_positive_node_id<'de, D>(deserializer: D) -> Result<i64, D::Error>
where
    D: Deserializer<'de>,
{
    let node_id = i64::deserialize(deserializer)?;
    if node_id <= 0 {
        return Err(serde::de::Error::custom(
            "Remnawave node id must be a positive integer",
        ));
    }
    Ok(node_id)
}

fn deserialize_integration_uuids<'de, D>(deserializer: D) -> Result<Vec<Uuid>, D::Error>
where
    D: Deserializer<'de>,
{
    let integration_uuids = Vec::<Uuid>::deserialize(deserializer)?;
    if integration_uuids.len() > 20 {
        return Err(serde::de::Error::custom(
            "Remnawave node integrationUuids must contain no more than 20 entries",
        ));
    }
    Ok(integration_uuids)
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
    use uuid::Uuid;

    #[test]
    fn node_inventory_item_accepts_current_remnawave_shape() {
        let payload = include_str!("../../tests/fixtures/remnawave/node_inventory_item_3_4_1.json");
        let item: NodeInventoryItem =
            serde_json::from_str(payload).expect("current Remnawave inventory payload");

        assert_eq!(item.id, 17);
        assert_eq!(
            item.uuid,
            Uuid::parse_str("550e8400-e29b-41d4-a716-446655440010").expect("fixture uuid")
        );
        assert_eq!(item.hostname.as_deref(), Some("fra-01.example.com"));
        assert_eq!(item.country_code.as_deref(), Some("DE"));
        assert_eq!(
            item.active_plugin_uuid.as_deref(),
            Some("550e8400-e29b-41d4-a716-446655440099")
        );
        assert_eq!(item.effective_enabled(), Some(true));
        assert_eq!(item.effective_node_version(), Some("3.4.1"));
        assert_eq!(item.effective_xray_version(), Some("26.7.31"));
        assert_eq!(item.ips.len(), 2);
        assert_eq!(item.integration_uuids.len(), 1);
    }

    #[test]
    fn list_nodes_response_accepts_wrapped_payloads() {
        let payload =
            include_str!("../../tests/fixtures/remnawave/node_inventory_wrapped_3_4_1.json");
        let payload: ListNodesResponse =
            serde_json::from_str(payload).expect("wrapped Remnawave list response");

        match payload {
            ListNodesResponse::Bare(_) => panic!("expected wrapped node inventory payload"),
            ListNodesResponse::Wrapped { response } => {
                assert_eq!(response.len(), 1);
                assert_eq!(response[0].id, 18);
                assert_eq!(response[0].hostname.as_deref(), Some("ams-01.example.com"));
            }
        }
    }

    #[test]
    fn node_inventory_rejects_more_than_64_ips() {
        let ips = (0..65)
            .map(|index| {
                serde_json::json!({
                    "ip": format!("192.0.2.{}", (index % 254) + 1),
                    "status": "INBOUND"
                })
            })
            .collect::<Vec<_>>();
        let payload = serde_json::json!({
            "id": 17,
            "uuid": "550e8400-e29b-41d4-a716-446655440010",
            "name": "too-many-ips",
            "ips": ips,
            "integrationUuids": []
        });

        let error = serde_json::from_value::<NodeInventoryItem>(payload)
            .expect_err("65 IPs must violate the Remnawave 3.4 contract");

        assert!(error.to_string().contains("no more than 64"));
    }

    #[test]
    fn node_inventory_rejects_non_positive_numeric_id() {
        let payload = serde_json::json!({
            "id": 0,
            "uuid": "550e8400-e29b-41d4-a716-446655440010",
            "name": "invalid-id",
            "ips": [],
            "integrationUuids": []
        });

        let error = serde_json::from_value::<NodeInventoryItem>(payload)
            .expect_err("zero must violate the Remnawave 3.4 node id contract");

        assert!(error.to_string().contains("positive integer"));
    }

    #[test]
    fn node_inventory_rejects_more_than_20_integrations() {
        let integration_uuids = (1..=21)
            .map(|index| format!("550e8400-e29b-41d4-a716-{index:012}"))
            .collect::<Vec<_>>();
        let payload = serde_json::json!({
            "id": 17,
            "uuid": "550e8400-e29b-41d4-a716-446655440010",
            "name": "too-many-integrations",
            "ips": [],
            "integrationUuids": integration_uuids
        });

        let error = serde_json::from_value::<NodeInventoryItem>(payload)
            .expect_err("21 integrations must violate the Remnawave 3.4 contract");

        assert!(error.to_string().contains("no more than 20"));
    }
}
