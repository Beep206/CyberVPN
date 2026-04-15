#![forbid(unsafe_code)]

use ns_core::{DatagramMode, SessionLimits, SessionMode, StatsMode, ValidationError};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicyInput {
    pub policy_epoch: u64,
    pub manifest_limits: SessionLimits,
    pub token_max_relay_streams: Option<u64>,
    pub token_max_udp_flows: Option<u64>,
    pub token_max_udp_payload: Option<u64>,
    pub session_modes: Vec<SessionMode>,
    pub allow_client_reports: bool,
    pub telemetry_sample_rate_millis: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EffectiveSessionPolicy {
    pub policy_epoch: u64,
    pub limits: SessionLimits,
    pub session_modes: Vec<SessionMode>,
    pub allow_client_reports: bool,
    pub telemetry_sample_rate_millis: u16,
}

#[derive(Debug, Error)]
pub enum PolicyError {
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
    #[error("at least one session mode must be allowed")]
    NoSessionModes,
    #[error("telemetry sample rate must be between 0 and 1000 millis")]
    InvalidTelemetrySampleRate,
}

impl EffectiveSessionPolicy {
    pub fn derive(input: PolicyInput) -> Result<Self, PolicyError> {
        if input.session_modes.is_empty() {
            return Err(PolicyError::NoSessionModes);
        }
        if input.telemetry_sample_rate_millis > 1000 {
            return Err(PolicyError::InvalidTelemetrySampleRate);
        }

        let mut limits = input.manifest_limits;
        limits.policy_epoch = input.policy_epoch;
        limits.max_concurrent_relay_streams = input
            .token_max_relay_streams
            .unwrap_or(limits.max_concurrent_relay_streams);
        limits.max_udp_flows = input.token_max_udp_flows.unwrap_or(limits.max_udp_flows);
        limits.max_udp_payload = input
            .token_max_udp_payload
            .unwrap_or(limits.max_udp_payload);
        limits.validate()?;

        Ok(Self {
            policy_epoch: input.policy_epoch,
            limits,
            session_modes: input.session_modes,
            allow_client_reports: input.allow_client_reports,
            telemetry_sample_rate_millis: input.telemetry_sample_rate_millis,
        })
    }

    pub fn tcp_and_udp_defaults(policy_epoch: u64) -> Self {
        Self {
            policy_epoch,
            limits: SessionLimits {
                policy_epoch,
                idle_timeout_ms: 30_000,
                session_lifetime_ms: 300_000,
                max_concurrent_relay_streams: 32,
                max_udp_flows: 8,
                max_udp_payload: 1_200,
                datagram_mode: DatagramMode::AvailableAndEnabled,
                stats_mode: StatsMode::Off,
            },
            session_modes: vec![SessionMode::Tcp, SessionMode::Udp],
            allow_client_reports: false,
            telemetry_sample_rate_millis: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn token_overrides_tighten_manifest_limits() {
        let policy = EffectiveSessionPolicy::derive(PolicyInput {
            policy_epoch: 5,
            manifest_limits: EffectiveSessionPolicy::tcp_and_udp_defaults(5).limits,
            token_max_relay_streams: Some(4),
            token_max_udp_flows: Some(2),
            token_max_udp_payload: Some(900),
            session_modes: vec![SessionMode::Tcp],
            allow_client_reports: true,
            telemetry_sample_rate_millis: 250,
        })
        .expect("policy derivation should accept tighter token limits");

        assert_eq!(policy.limits.max_concurrent_relay_streams, 4);
        assert_eq!(policy.limits.max_udp_flows, 2);
        assert_eq!(policy.limits.max_udp_payload, 900);
        assert_eq!(policy.session_modes, vec![SessionMode::Tcp]);
    }
}
