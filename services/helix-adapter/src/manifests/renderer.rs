use uuid::Uuid;

use crate::{
    error::AppError,
    manifests::model::{
        ManifestCapabilityProfile, ManifestCompatibilityWindow, ManifestCredentials,
        ManifestHealthPolicy, ManifestObservability, ManifestRenderInput, ManifestTransport,
        ManifestTransportProfile, UnsignedManifestDocument,
    },
};

#[derive(Debug, Clone)]
pub struct ManifestRenderer {
    metrics_namespace: String,
}

impl ManifestRenderer {
    pub fn new(metrics_namespace: String) -> Self {
        Self { metrics_namespace }
    }

    pub fn render(&self, input: ManifestRenderInput) -> Result<UnsignedManifestDocument, AppError> {
        if input.routes.is_empty() {
            return Err(AppError::BadRequest(
                "cannot render a manifest without at least one route".to_string(),
            ));
        }

        if !matches!(input.effective_fallback_core.as_str(), "sing-box" | "xray") {
            return Err(AppError::BadRequest(format!(
                "unsupported fallback core: {}",
                input.effective_fallback_core
            )));
        }

        let routes = input.routes;

        Ok(UnsignedManifestDocument {
            schema_version: "1.1",
            manifest_id: Uuid::new_v4(),
            rollout_id: input.rollout_id,
            issued_at: input.issued_at,
            expires_at: input.expires_at,
            subject: input.subject,
            transport: ManifestTransport {
                transport_family: "helix",
                protocol_version: input.selected_profile.protocol_version,
                session_mode: input.selected_profile.session_mode.clone(),
            },
            transport_profile: ManifestTransportProfile {
                transport_profile_id: input.selected_profile.transport_profile_id.clone(),
                profile_family: input.selected_profile.profile_family.clone(),
                profile_version: input.selected_profile.profile_version,
                policy_version: input.selected_profile.policy_version,
                deprecation_state: input.selected_profile.status.clone(),
            },
            compatibility_window: ManifestCompatibilityWindow {
                profile_family: input.selected_profile.profile_family.clone(),
                min_transport_profile_version: input
                    .selected_profile
                    .compatibility_min_profile_version,
                max_transport_profile_version: input
                    .selected_profile
                    .compatibility_max_profile_version,
            },
            capability_profile: ManifestCapabilityProfile {
                required_capabilities: input.selected_profile.required_capabilities.clone(),
                fallback_core: input.effective_fallback_core,
                health_policy: ManifestHealthPolicy {
                    startup_timeout_seconds: input.selected_profile.startup_timeout_seconds,
                    runtime_unhealthy_threshold: input.selected_profile.runtime_unhealthy_threshold,
                },
            },
            routes,
            credentials: ManifestCredentials {
                key_id: input.key_id,
                token: input.session_token,
            },
            observability: ManifestObservability {
                trace_id: input.trace_id,
                metrics_namespace: self.metrics_namespace.clone(),
            },
        })
    }
}
