use chrono::{Duration, Utc};
use sqlx::{types::Json, PgPool};

use crate::{
    error::AppError,
    manifests::{
        model::{
            ClientCapabilityDefaults, ManifestRenderInput, ManifestRoute, ManifestSubject,
            ManifestVersionRecord, ResolveManifestRequest, ResolveManifestResponse,
            SupportedTransportProfile,
        },
        renderer::ManifestRenderer,
        signer::ManifestSigner,
    },
    node_registry::{model::RolloutChannel, repository::NodeRegistryRepository},
    session_credentials::derive_rollout_session_token,
    transport_profiles::service::{ProfileSelectionTarget, TransportProfileService},
};

#[derive(Debug, Clone)]
pub struct ManifestStore {
    pool: PgPool,
    node_repository: NodeRegistryRepository,
    transport_profile_service: TransportProfileService,
    renderer: ManifestRenderer,
    signer: ManifestSigner,
}

impl ManifestStore {
    pub fn new(
        pool: PgPool,
        node_repository: NodeRegistryRepository,
        transport_profile_service: TransportProfileService,
        renderer: ManifestRenderer,
        signer: ManifestSigner,
    ) -> Self {
        Self {
            pool,
            node_repository,
            transport_profile_service,
            renderer,
            signer,
        }
    }

    pub async fn resolve_manifest(
        &self,
        request: ResolveManifestRequest,
        default_channel: RolloutChannel,
        ttl_seconds: i64,
    ) -> Result<ResolveManifestResponse, AppError> {
        validate_resolve_request(&request)?;

        let channel = request.channel.unwrap_or(default_channel);
        let rollout = self
            .node_repository
            .find_active_rollout_by_channel(channel.as_str())
            .await?;
        let active_actuation = self
            .node_repository
            .fetch_active_rollout_actuation(&rollout.rollout_id)
            .await?;
        let nodes = self
            .node_repository
            .list_transport_enabled_nodes_for_channel(channel.as_str())
            .await?;

        if nodes.is_empty() {
            return Err(AppError::NotFound(format!(
                "no transport-enabled nodes available for channel: {channel}"
            )));
        }

        let selected_profile = self
            .transport_profile_service
            .resolve_compatible_profile_for_target(
                &rollout.rollout_id,
                channel,
                request.supported_protocol_versions.as_deref(),
                request.supported_transport_profiles.as_deref(),
                ProfileSelectionTarget::DesktopNewSession,
                active_actuation
                    .as_ref()
                    .and_then(|actuation| {
                        (actuation.reaction == "rotate-profile-now")
                            .then_some(actuation.target_transport_profile_id.as_deref())
                    })
                    .flatten(),
            )
            .await?;
        if selected_profile
            .policy
            .as_ref()
            .is_some_and(|policy| !policy.new_session_issuable)
        {
            return Err(AppError::NotFound(format!(
                "no Helix transport profile is currently eligible for new desktop sessions on channel: {channel}"
            )));
        }
        let effective_fallback_core = request
            .preferred_fallback_core
            .unwrap_or_else(|| selected_profile.fallback_core.clone());
        let routes = nodes
            .iter()
            .filter_map(|node| {
                node.hostname.as_ref().map(|hostname| ManifestRoute {
                    endpoint_ref: node.adapter_node_label.clone(),
                    dial_host: hostname.clone(),
                    dial_port: route_port(node.transport_port, &selected_profile, channel),
                    server_name: Some(hostname.clone()),
                    preference: 0,
                    policy_tag: String::new(),
                })
            })
            .enumerate()
            .map(|(index, mut route)| {
                route.preference = ((index as i32) + 1) * 10;
                route.policy_tag = if index == 0 {
                    "primary".to_string()
                } else {
                    "secondary".to_string()
                };
                route
            })
            .collect::<Vec<_>>();

        if routes.is_empty() {
            return Err(AppError::BadRequest(format!(
                "no routable transport-enabled nodes with hostname are available for channel: {channel}"
            )));
        }

        let now = Utc::now();
        let unsigned_manifest = self.renderer.render(ManifestRenderInput {
            rollout_id: rollout.rollout_id.clone(),
            issued_at: now,
            expires_at: now + Duration::seconds(ttl_seconds),
            subject: ManifestSubject {
                user_id: request.user_id.clone(),
                desktop_client_id: request.desktop_client_id.clone(),
                entitlement_id: request.entitlement_id.clone(),
                channel,
            },
            trace_id: request.trace_id.clone(),
            routes,
            effective_fallback_core,
            key_id: self.signer.key_id().to_string(),
            session_token: derive_rollout_session_token(
                &rollout.rollout_id,
                &selected_profile.transport_profile_id,
                self.signer.key_id(),
            ),
            selected_profile: selected_profile.clone(),
        })?;
        let manifest = self.signer.sign_manifest(unsigned_manifest)?;
        self.signer.verify_manifest(&manifest)?;

        let manifest_version_id = uuid::Uuid::new_v4();
        let manifest_value = serde_json::to_value(&manifest)?;

        sqlx::query(
            r#"
            INSERT INTO helix.manifest_versions (
                manifest_version_id,
                manifest_id,
                rollout_id,
                manifest_template_version,
                transport_profile_id,
                profile_family,
                profile_version,
                policy_version,
                subject_user_id,
                desktop_client_id,
                entitlement_id,
                channel,
                protocol_version,
                manifest_json,
                manifest_hash,
                signature_alg,
                signature_key_id,
                signature,
                created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW())
            "#,
        )
        .bind(manifest_version_id)
        .bind(manifest.manifest_id)
        .bind(&manifest.rollout_id)
        .bind(&rollout.manifest_version)
        .bind(&manifest.transport_profile.transport_profile_id)
        .bind(&manifest.transport_profile.profile_family)
        .bind(manifest.transport_profile.profile_version)
        .bind(manifest.transport_profile.policy_version)
        .bind(&manifest.subject.user_id)
        .bind(&manifest.subject.desktop_client_id)
        .bind(&manifest.subject.entitlement_id)
        .bind(channel.as_str())
        .bind(manifest.transport.protocol_version)
        .bind(Json(manifest_value))
        .bind(&manifest.integrity.manifest_hash)
        .bind(manifest.integrity.signature.alg)
        .bind(&manifest.integrity.signature.key_id)
        .bind(&manifest.integrity.signature.sig)
        .execute(&self.pool)
        .await?;

        Ok(ResolveManifestResponse {
            manifest_version_id,
            manifest,
            selected_profile_policy: selected_profile.policy.clone(),
        })
    }

    pub async fn revoke_manifest(
        &self,
        manifest_version_id: uuid::Uuid,
    ) -> Result<ManifestVersionRecord, AppError> {
        let record = sqlx::query_as::<_, ManifestVersionRecord>(
            r#"
            UPDATE helix.manifest_versions
            SET revoked_at = NOW()
            WHERE manifest_version_id = $1
            RETURNING
                manifest_version_id,
                manifest_id,
                rollout_id,
                manifest_template_version,
                transport_profile_id,
                profile_family,
                profile_version,
                policy_version,
                subject_user_id,
                desktop_client_id,
                entitlement_id,
                channel,
                protocol_version,
                manifest_hash,
                signature_alg,
                signature_key_id,
                signature,
                revoked_at,
                created_at
            "#,
        )
        .bind(manifest_version_id)
        .fetch_optional(&self.pool)
        .await?
        .ok_or_else(|| {
            AppError::NotFound(format!("manifest version not found: {manifest_version_id}"))
        })?;

        Ok(record)
    }

    pub fn client_capability_defaults(
        &self,
        default_channel: RolloutChannel,
    ) -> ClientCapabilityDefaults {
        ClientCapabilityDefaults {
            schema_version: "1.1",
            client_family: "desktop-tauri",
            default_channel,
            supported_protocol_versions: vec![1],
            supported_transport_profiles: vec![
                SupportedTransportProfile {
                    profile_family: "edge-hybrid".to_string(),
                    min_transport_profile_version: 1,
                    max_transport_profile_version: 4,
                    supported_policy_versions: vec![4, 5, 6, 7],
                },
                SupportedTransportProfile {
                    profile_family: "edge-stateful".to_string(),
                    min_transport_profile_version: 1,
                    max_transport_profile_version: 2,
                    supported_policy_versions: vec![2, 3],
                },
            ],
            required_capabilities: vec![
                "protocol.v1".to_string(),
                "fallback.auto".to_string(),
                "sidecar.sigverify".to_string(),
            ],
            fallback_cores: vec!["sing-box".to_string(), "xray".to_string()],
            rollout_channels: vec![
                RolloutChannel::Lab,
                RolloutChannel::Canary,
                RolloutChannel::Stable,
            ],
        }
    }
}

fn route_port(
    transport_port: Option<i32>,
    profile: &crate::transport_profiles::model::TransportProfileRecord,
    channel: RolloutChannel,
) -> u16 {
    if let Some(transport_port) = transport_port {
        if let Ok(transport_port) = u16::try_from(transport_port) {
            return transport_port;
        }
    }

    if channel == RolloutChannel::Lab {
        return 9443;
    }

    if profile.profile_family == "edge-hybrid" {
        return 8443;
    }

    443
}

fn validate_resolve_request(request: &ResolveManifestRequest) -> Result<(), AppError> {
    if request.user_id.trim().is_empty() {
        return Err(AppError::BadRequest(
            "user_id must not be empty".to_string(),
        ));
    }

    if request.desktop_client_id.trim().is_empty() {
        return Err(AppError::BadRequest(
            "desktop_client_id must not be empty".to_string(),
        ));
    }

    if request.entitlement_id.trim().is_empty() {
        return Err(AppError::BadRequest(
            "entitlement_id must not be empty".to_string(),
        ));
    }

    if request.trace_id.trim().is_empty() {
        return Err(AppError::BadRequest(
            "trace_id must not be empty".to_string(),
        ));
    }

    if let Some(protocol_versions) = &request.supported_protocol_versions {
        if protocol_versions.is_empty() || !protocol_versions.iter().all(|version| *version >= 1) {
            return Err(AppError::BadRequest(
                "supported_protocol_versions must contain protocol versions >= 1".to_string(),
            ));
        }
    }

    if let Some(supported_profiles) = &request.supported_transport_profiles {
        if supported_profiles.is_empty() {
            return Err(AppError::BadRequest(
                "supported_transport_profiles must not be empty when provided".to_string(),
            ));
        }

        for supported_profile in supported_profiles {
            if supported_profile.profile_family.trim().is_empty() {
                return Err(AppError::BadRequest(
                    "supported transport profile family must not be empty".to_string(),
                ));
            }

            if supported_profile.min_transport_profile_version
                > supported_profile.max_transport_profile_version
            {
                return Err(AppError::BadRequest(
                    "supported transport profile min version must be <= max version".to_string(),
                ));
            }

            if supported_profile.supported_policy_versions.is_empty() {
                return Err(AppError::BadRequest(
                    "supported policy versions must not be empty".to_string(),
                ));
            }
        }
    }

    if let Some(fallback_core) = &request.preferred_fallback_core {
        if !matches!(fallback_core.as_str(), "sing-box" | "xray") {
            return Err(AppError::BadRequest(format!(
                "unsupported preferred fallback core: {fallback_core}"
            )));
        }
    }

    Ok(())
}
