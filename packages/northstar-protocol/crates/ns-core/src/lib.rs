#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

pub const SESSION_CORE_VERSION: u16 = 1;
pub const MANIFEST_SCHEMA_VERSION: u16 = 1;
pub const BRIDGE_API_PREFIX: &str = "/v0";
pub const CONTROL_FRAME_MAX_PAYLOAD: usize = 65_535;
pub const MAX_METADATA_TLVS: usize = 16;
pub const MAX_REQUESTED_CAPABILITIES: usize = 64;
pub const DEFAULT_TOKEN_CLOCK_SKEW_SECONDS: i64 = 120;
pub const UDP_VALIDATION_COMPARISON_FAMILY: &str = "udp_rollout_validation";
pub const UDP_VALIDATION_COMPARISON_SCHEMA: &str = "udp_rollout_validation_surface";
pub const UDP_VALIDATION_COMPARISON_SCHEMA_VERSION: u8 = 1;
pub const UDP_VALIDATION_COMPARISON_SCOPE: &str = "surface";
pub const UDP_VALIDATION_COMPARISON_PROFILE: &str = "validation_surface";

pub type CoreVersion = u64;
pub type RelayId = u64;
pub type FlowId = u64;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ManifestId(String);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CarrierProfileId(String);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceBindingId(String);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeviceId(String);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionId([u8; 16]);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Capability {
    TcpRelay,
    UdpRelay,
    DgramPacingHints,
    PathSignals,
    TlsFragmentHints,
    TelemetrySampled,
    QuicDatagram,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CarrierKind {
    H3,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DatagramMode {
    Unavailable,
    AvailableAndEnabled,
    DisabledByPolicy,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StatsMode {
    Off,
    SampledClientPushAllowed,
    SampledBidirectional,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TargetType {
    Domain,
    Ipv4,
    Ipv6,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SessionMode {
    Tcp,
    Udp,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProtocolErrorCode {
    NoError,
    ProtocolViolation,
    UnsupportedVersion,
    AuthFailed,
    TokenExpired,
    PolicyDenied,
    RateLimited,
    TargetDenied,
    FlowLimitReached,
    InternalError,
    CarrierUnsupported,
    ProfileMismatch,
    ReplaySuspected,
    IdleTimeout,
    Draining,
    ResolutionFailed,
    ConnectFailed,
    NetworkUnreachable,
    FrameTooLarge,
    UnsupportedTargetType,
    UdpDatagramUnavailable,
}

pub type ErrorCode = ProtocolErrorCode;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransportMode {
    Datagram,
    StreamFallback,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PathEventType {
    NetworkChanged,
    SuspectedBlocking,
    Recovered,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionLimits {
    pub policy_epoch: u64,
    pub idle_timeout_ms: u64,
    pub session_lifetime_ms: u64,
    pub max_concurrent_relay_streams: u64,
    pub max_udp_flows: u64,
    pub max_udp_payload: u64,
    pub datagram_mode: DatagramMode,
    pub stats_mode: StatsMode,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TransportSelection {
    pub carrier_kind: CarrierKind,
    pub carrier_profile_id: CarrierProfileId,
    pub requested_capabilities: Vec<Capability>,
}

#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum ValidationError {
    #[error("{field} must not be empty")]
    Empty { field: &'static str },
    #[error("{field} must be between {min} and {max} bytes")]
    Length {
        field: &'static str,
        min: usize,
        max: usize,
    },
    #[error("registry value {value} is reserved for future use")]
    ReservedRegistryValue { value: u64 },
    #[error("registry value {value} is not defined for v0.1")]
    UnknownRegistryValue { value: u64 },
    #[error("{field} must not be zero")]
    Zero { field: &'static str },
}

impl ManifestId {
    pub fn new(value: impl Into<String>) -> Result<Self, ValidationError> {
        let value = value.into();
        validate_bounded_string("manifest_id", &value, 8, 256)?;
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl CarrierProfileId {
    pub fn new(value: impl Into<String>) -> Result<Self, ValidationError> {
        let value = value.into();
        validate_bounded_string("carrier_profile_id", &value, 1, 128)?;
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl DeviceBindingId {
    pub fn new(value: impl Into<String>) -> Result<Self, ValidationError> {
        let value = value.into();
        validate_bounded_string("device_binding_id", &value, 1, 128)?;
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl DeviceId {
    pub fn new(value: impl Into<String>) -> Result<Self, ValidationError> {
        let value = value.into();
        validate_bounded_string("device_id", &value, 1, 128)?;
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl SessionId {
    pub fn new(bytes: [u8; 16]) -> Self {
        Self(bytes)
    }

    pub fn random() -> Self {
        Self(*Uuid::new_v4().as_bytes())
    }

    pub fn from_slice(value: &[u8]) -> Result<Self, ValidationError> {
        if value.len() != 16 {
            return Err(ValidationError::Length {
                field: "session_id",
                min: 16,
                max: 16,
            });
        }

        let mut bytes = [0_u8; 16];
        bytes.copy_from_slice(value);
        Ok(Self(bytes))
    }

    pub fn as_bytes(&self) -> &[u8; 16] {
        &self.0
    }
}

impl Capability {
    pub fn id(self) -> u64 {
        match self {
            Self::TcpRelay => 1,
            Self::UdpRelay => 2,
            Self::DgramPacingHints => 3,
            Self::PathSignals => 4,
            Self::TlsFragmentHints => 6,
            Self::TelemetrySampled => 8,
            Self::QuicDatagram => 10,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            1 => Ok(Self::TcpRelay),
            2 => Ok(Self::UdpRelay),
            3 => Ok(Self::DgramPacingHints),
            4 => Ok(Self::PathSignals),
            6 => Ok(Self::TlsFragmentHints),
            8 => Ok(Self::TelemetrySampled),
            10 => Ok(Self::QuicDatagram),
            5 | 7 | 9 => Err(ValidationError::ReservedRegistryValue { value }),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl CarrierKind {
    pub fn id(self) -> u64 {
        match self {
            Self::H3 => 1,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            1 => Ok(Self::H3),
            2..=5 => Err(ValidationError::ReservedRegistryValue { value }),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl DatagramMode {
    pub fn id(self) -> u64 {
        match self {
            Self::Unavailable => 0,
            Self::AvailableAndEnabled => 1,
            Self::DisabledByPolicy => 2,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            0 => Ok(Self::Unavailable),
            1 => Ok(Self::AvailableAndEnabled),
            2 => Ok(Self::DisabledByPolicy),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl StatsMode {
    pub fn id(self) -> u64 {
        match self {
            Self::Off => 0,
            Self::SampledClientPushAllowed => 1,
            Self::SampledBidirectional => 2,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            0 => Ok(Self::Off),
            1 => Ok(Self::SampledClientPushAllowed),
            2 => Ok(Self::SampledBidirectional),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl TargetType {
    pub fn id(self) -> u64 {
        match self {
            Self::Domain => 1,
            Self::Ipv4 => 2,
            Self::Ipv6 => 3,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            1 => Ok(Self::Domain),
            2 => Ok(Self::Ipv4),
            3 => Ok(Self::Ipv6),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl ProtocolErrorCode {
    pub fn id(self) -> u64 {
        match self {
            Self::NoError => 0,
            Self::ProtocolViolation => 1,
            Self::UnsupportedVersion => 2,
            Self::AuthFailed => 3,
            Self::TokenExpired => 4,
            Self::PolicyDenied => 5,
            Self::RateLimited => 6,
            Self::TargetDenied => 7,
            Self::FlowLimitReached => 8,
            Self::InternalError => 9,
            Self::CarrierUnsupported => 10,
            Self::ProfileMismatch => 11,
            Self::ReplaySuspected => 12,
            Self::IdleTimeout => 13,
            Self::Draining => 14,
            Self::ResolutionFailed => 15,
            Self::ConnectFailed => 16,
            Self::NetworkUnreachable => 17,
            Self::FrameTooLarge => 18,
            Self::UnsupportedTargetType => 19,
            Self::UdpDatagramUnavailable => 20,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            0 => Ok(Self::NoError),
            1 => Ok(Self::ProtocolViolation),
            2 => Ok(Self::UnsupportedVersion),
            3 => Ok(Self::AuthFailed),
            4 => Ok(Self::TokenExpired),
            5 => Ok(Self::PolicyDenied),
            6 => Ok(Self::RateLimited),
            7 => Ok(Self::TargetDenied),
            8 => Ok(Self::FlowLimitReached),
            9 => Ok(Self::InternalError),
            10 => Ok(Self::CarrierUnsupported),
            11 => Ok(Self::ProfileMismatch),
            12 => Ok(Self::ReplaySuspected),
            13 => Ok(Self::IdleTimeout),
            14 => Ok(Self::Draining),
            15 => Ok(Self::ResolutionFailed),
            16 => Ok(Self::ConnectFailed),
            17 => Ok(Self::NetworkUnreachable),
            18 => Ok(Self::FrameTooLarge),
            19 => Ok(Self::UnsupportedTargetType),
            20 => Ok(Self::UdpDatagramUnavailable),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl TransportMode {
    pub fn id(self) -> u64 {
        match self {
            Self::Datagram => 1,
            Self::StreamFallback => 2,
        }
    }

    pub fn from_id(value: u64) -> Result<Self, ValidationError> {
        match value {
            1 => Ok(Self::Datagram),
            2 => Ok(Self::StreamFallback),
            _ => Err(ValidationError::UnknownRegistryValue { value }),
        }
    }
}

impl SessionLimits {
    pub fn validate(&self) -> Result<(), ValidationError> {
        for (field, value) in [
            ("idle_timeout_ms", self.idle_timeout_ms),
            ("session_lifetime_ms", self.session_lifetime_ms),
            (
                "max_concurrent_relay_streams",
                self.max_concurrent_relay_streams,
            ),
            ("max_udp_flows", self.max_udp_flows),
            ("max_udp_payload", self.max_udp_payload),
        ] {
            if value == 0 {
                return Err(ValidationError::Zero { field });
            }
        }

        Ok(())
    }
}

fn validate_bounded_string(
    field: &'static str,
    value: &str,
    min: usize,
    max: usize,
) -> Result<(), ValidationError> {
    if value.is_empty() {
        return Err(ValidationError::Empty { field });
    }

    let len = value.len();
    if len < min || len > max {
        return Err(ValidationError::Length { field, min, max });
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reserved_capability_values_are_not_accepted() {
        assert!(matches!(
            Capability::from_id(5),
            Err(ValidationError::ReservedRegistryValue { value: 5 })
        ));
    }

    #[test]
    fn supported_carrier_kind_round_trips() {
        assert_eq!(
            CarrierKind::from_id(CarrierKind::H3.id()),
            Ok(CarrierKind::H3)
        );
    }

    #[test]
    fn protocol_error_codes_round_trip_against_the_frozen_registry() {
        let expected = [
            (0, ProtocolErrorCode::NoError),
            (1, ProtocolErrorCode::ProtocolViolation),
            (2, ProtocolErrorCode::UnsupportedVersion),
            (3, ProtocolErrorCode::AuthFailed),
            (4, ProtocolErrorCode::TokenExpired),
            (5, ProtocolErrorCode::PolicyDenied),
            (6, ProtocolErrorCode::RateLimited),
            (7, ProtocolErrorCode::TargetDenied),
            (8, ProtocolErrorCode::FlowLimitReached),
            (9, ProtocolErrorCode::InternalError),
            (10, ProtocolErrorCode::CarrierUnsupported),
            (11, ProtocolErrorCode::ProfileMismatch),
            (12, ProtocolErrorCode::ReplaySuspected),
            (13, ProtocolErrorCode::IdleTimeout),
            (14, ProtocolErrorCode::Draining),
            (15, ProtocolErrorCode::ResolutionFailed),
            (16, ProtocolErrorCode::ConnectFailed),
            (17, ProtocolErrorCode::NetworkUnreachable),
            (18, ProtocolErrorCode::FrameTooLarge),
            (19, ProtocolErrorCode::UnsupportedTargetType),
            (20, ProtocolErrorCode::UdpDatagramUnavailable),
        ];

        for (id, code) in expected {
            assert_eq!(code.id(), id, "unexpected registry id for {code:?}");
            assert_eq!(
                ProtocolErrorCode::from_id(id),
                Ok(code),
                "protocol error registry should round-trip id {id}"
            );
        }
    }

    #[test]
    fn transport_mode_round_trips_against_the_frozen_registry() {
        assert_eq!(TransportMode::Datagram.id(), 1);
        assert_eq!(TransportMode::StreamFallback.id(), 2);
        assert_eq!(TransportMode::from_id(1), Ok(TransportMode::Datagram));
        assert_eq!(TransportMode::from_id(2), Ok(TransportMode::StreamFallback));
        assert!(matches!(
            TransportMode::from_id(3),
            Err(ValidationError::UnknownRegistryValue { value: 3 })
        ));
    }

    #[test]
    fn manifest_id_requires_frozen_bounds() {
        assert!(ManifestId::new("short").is_err());
        assert!(ManifestId::new("man-2026-04-01-001").is_ok());
    }

    #[test]
    fn session_id_requires_sixteen_bytes() {
        assert!(SessionId::from_slice(&[0_u8; 15]).is_err());
        assert!(SessionId::from_slice(&[0_u8; 16]).is_ok());
    }

    #[test]
    fn session_limits_require_non_zero_values() {
        let limits = SessionLimits {
            policy_epoch: 7,
            idle_timeout_ms: 30_000,
            session_lifetime_ms: 300_000,
            max_concurrent_relay_streams: 32,
            max_udp_flows: 16,
            max_udp_payload: 1_200,
            datagram_mode: DatagramMode::AvailableAndEnabled,
            stats_mode: StatsMode::Off,
        };

        assert!(limits.validate().is_ok());
    }
}
