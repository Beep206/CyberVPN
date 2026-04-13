#![forbid(unsafe_code)]

use ed25519_dalek::pkcs8::DecodePrivateKey;
use jsonwebtoken::jwk::{
    AlgorithmParameters, CommonParameters, Jwk, JwkSet, OctetKeyPairParameters, OctetKeyPairType,
};
use jsonwebtoken::{
    Algorithm, DecodingKey, EncodingKey, Header, Validation, decode, decode_header, encode,
};
use ns_core::{
    Capability, CarrierProfileId, DEFAULT_TOKEN_CLOCK_SKEW_SECONDS, DeviceBindingId, ManifestId,
    SessionLimits, SessionMode, ValidationError,
};
use ns_policy::{EffectiveSessionPolicy, PolicyInput};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use time::{Duration, OffsetDateTime};
use tracing::debug;

const GATEWAY_AUDIENCE: &str = "northstar-gateway";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum TokenAudience {
    One(String),
    Many(Vec<String>),
}

impl TokenAudience {
    fn contains(&self, audience: &str) -> bool {
        match self {
            Self::One(value) => value == audience,
            Self::Many(values) => values.iter().any(|value| value == audience),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionTokenClaims {
    pub iss: String,
    pub aud: TokenAudience,
    pub sub: String,
    pub jti: String,
    pub iat: i64,
    pub nbf: i64,
    pub exp: i64,
    pub device_id: String,
    pub manifest_id: String,
    pub policy_epoch: u64,
    pub core_versions: Vec<u64>,
    pub carrier_profiles: Vec<String>,
    pub capabilities: Vec<u64>,
    pub session_modes: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub region_scope: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token_max_relay_streams: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token_max_udp_flows: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub token_max_udp_payload: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RequestedAccess {
    pub core_version: u64,
    pub carrier_profile_id: CarrierProfileId,
    pub requested_capabilities: Vec<Capability>,
    pub manifest_id: ManifestId,
    pub device_binding_id: DeviceBindingId,
    pub session_mode: SessionMode,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VerifiedSessionToken {
    pub claims: SessionTokenClaims,
    pub kid: String,
}

#[derive(Debug, Clone)]
pub struct VerifierConfig {
    pub trusted_issuers: Vec<String>,
    pub audience: String,
    pub clock_skew: Duration,
    pub revoked_subjects: Vec<String>,
    pub minimum_policy_epoch: Option<u64>,
}

impl Default for VerifierConfig {
    fn default() -> Self {
        Self {
            trusted_issuers: Vec::new(),
            audience: GATEWAY_AUDIENCE.to_owned(),
            clock_skew: Duration::seconds(DEFAULT_TOKEN_CLOCK_SKEW_SECONDS),
            revoked_subjects: Vec::new(),
            minimum_policy_epoch: None,
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct TrustedKeySet {
    keys_by_id: HashMap<String, Jwk>,
}

impl TrustedKeySet {
    pub fn from_jwks(jwks: &JwkSet) -> Result<Self, AuthError> {
        let mut keys_by_id = HashMap::new();
        for key in &jwks.keys {
            let kid = key.common.key_id.clone().ok_or(AuthError::MissingKid)?;
            if keys_by_id.insert(kid.clone(), key.clone()).is_some() {
                return Err(AuthError::DuplicateKeyId(kid));
            }
        }
        Ok(Self { keys_by_id })
    }

    pub fn insert(&mut self, kid: impl Into<String>, jwk: Jwk) {
        self.keys_by_id.insert(kid.into(), jwk);
    }

    fn decoding_key(&self, kid: &str) -> Result<DecodingKey, AuthError> {
        let jwk = self.keys_by_id.get(kid).ok_or(AuthError::UnknownKeyId)?;
        DecodingKey::from_jwk(jwk).map_err(AuthError::Jwt)
    }
}

pub struct SessionTokenVerifier {
    config: VerifierConfig,
    trusted_keys: TrustedKeySet,
}

impl SessionTokenVerifier {
    pub fn new(config: VerifierConfig, trusted_keys: TrustedKeySet) -> Self {
        Self {
            config,
            trusted_keys,
        }
    }

    pub fn verify(
        &self,
        token: &str,
        access: &RequestedAccess,
    ) -> Result<VerifiedSessionToken, AuthError> {
        let header = decode_header(token).map_err(AuthError::Jwt)?;
        if header.alg != Algorithm::EdDSA {
            return Err(AuthError::UnsupportedAlgorithm);
        }
        match header.typ.as_deref() {
            Some("JWT") => {}
            _ => return Err(AuthError::InvalidTokenType),
        }

        let kid = header.kid.clone().ok_or(AuthError::MissingKid)?;
        let decoding_key = self.trusted_keys.decoding_key(&kid)?;

        let mut validation = Validation::new(Algorithm::EdDSA);
        validation.validate_nbf = true;
        validation.leeway = self.config.clock_skew.whole_seconds().unsigned_abs();
        validation.set_required_spec_claims(&["exp", "nbf", "iat", "iss", "aud", "sub"]);
        validation.set_audience(&[self.config.audience.as_str()]);
        if !self.config.trusted_issuers.is_empty() {
            validation.set_issuer(&self.config.trusted_issuers);
        }

        let data = decode::<SessionTokenClaims>(token, &decoding_key, &validation)
            .map_err(AuthError::Jwt)?;
        debug!(target: "ns_auth", kid = %kid, policy_epoch = data.claims.policy_epoch, "validated session token signature");

        Self::validate_claims(&data.claims, access)?;
        self.validate_runtime_policy(&data.claims)?;

        Ok(VerifiedSessionToken {
            claims: data.claims,
            kid,
        })
    }

    fn validate_runtime_policy(&self, claims: &SessionTokenClaims) -> Result<(), AuthError> {
        if self
            .config
            .revoked_subjects
            .iter()
            .any(|subject| subject == &claims.sub)
        {
            return Err(AuthError::SubjectRevoked(claims.sub.clone()));
        }
        if let Some(minimum_policy_epoch) = self.config.minimum_policy_epoch
            && claims.policy_epoch < minimum_policy_epoch
        {
            return Err(AuthError::StalePolicyEpoch {
                token_policy_epoch: claims.policy_epoch,
                minimum_policy_epoch,
            });
        }

        Ok(())
    }

    pub fn validate_claims(
        claims: &SessionTokenClaims,
        access: &RequestedAccess,
    ) -> Result<(), AuthError> {
        if claims.jti.trim().is_empty() {
            return Err(AuthError::MissingClaim("jti"));
        }
        if !claims.aud.contains(GATEWAY_AUDIENCE) {
            return Err(AuthError::AudienceMismatch);
        }
        if claims.manifest_id != access.manifest_id.as_str() {
            return Err(AuthError::ManifestMismatch);
        }
        if claims.device_id != access.device_binding_id.as_str() {
            return Err(AuthError::DeviceBindingMismatch);
        }
        if !claims.core_versions.contains(&access.core_version) {
            return Err(AuthError::CoreVersionNotAllowed(access.core_version));
        }
        if !claims
            .carrier_profiles
            .iter()
            .any(|profile| profile == access.carrier_profile_id.as_str())
        {
            return Err(AuthError::CarrierProfileNotAllowed(
                access.carrier_profile_id.as_str().to_owned(),
            ));
        }
        if access.requested_capabilities.iter().any(|capability| {
            !claims
                .capabilities
                .iter()
                .any(|value| *value == capability.id())
        }) {
            return Err(AuthError::CapabilityNotAllowed);
        }
        let requested_mode = match access.session_mode {
            SessionMode::Tcp => "tcp",
            SessionMode::Udp => "udp",
        };
        if !claims
            .session_modes
            .iter()
            .any(|mode| mode == requested_mode)
        {
            return Err(AuthError::SessionModeNotAllowed(requested_mode.to_owned()));
        }

        Ok(())
    }
}

impl VerifiedSessionToken {
    pub fn to_policy(
        &self,
        manifest_limits: SessionLimits,
    ) -> Result<EffectiveSessionPolicy, AuthError> {
        let session_modes = self
            .claims
            .session_modes
            .iter()
            .map(|mode| match mode.as_str() {
                "tcp" => Ok(SessionMode::Tcp),
                "udp" => Ok(SessionMode::Udp),
                _ => Err(AuthError::SessionModeNotAllowed(mode.clone())),
            })
            .collect::<Result<Vec<_>, _>>()?;

        EffectiveSessionPolicy::derive(PolicyInput {
            policy_epoch: self.claims.policy_epoch,
            manifest_limits,
            token_max_relay_streams: self.claims.token_max_relay_streams,
            token_max_udp_flows: self.claims.token_max_udp_flows,
            token_max_udp_payload: self.claims.token_max_udp_payload,
            session_modes,
            allow_client_reports: false,
            telemetry_sample_rate_millis: 0,
        })
        .map_err(AuthError::Policy)
    }
}

pub struct SessionTokenSigner {
    issuer: String,
    audience: String,
    key_id: String,
    encoding_key: EncodingKey,
    verifying_key: ed25519_dalek::VerifyingKey,
}

#[derive(Debug, Clone)]
pub struct MintedTokenRequest {
    pub subject: String,
    pub device_id: DeviceBindingId,
    pub manifest_id: ManifestId,
    pub policy_epoch: u64,
    pub core_versions: Vec<u64>,
    pub carrier_profiles: Vec<String>,
    pub capabilities: Vec<u64>,
    pub session_modes: Vec<String>,
    pub region_scope: Option<String>,
    pub token_max_relay_streams: Option<u64>,
    pub token_max_udp_flows: Option<u64>,
    pub token_max_udp_payload: Option<u64>,
}

#[derive(Debug, Clone)]
pub struct MintedToken {
    pub token: String,
    pub expires_at: OffsetDateTime,
}

impl SessionTokenSigner {
    pub fn from_ed_pem(
        issuer: impl Into<String>,
        audience: impl Into<String>,
        key_id: impl Into<String>,
        pem: &[u8],
    ) -> Result<Self, AuthError> {
        let pem_text = std::str::from_utf8(pem).map_err(|_| AuthError::SigningKeyPem)?;
        let signing_key = ed25519_dalek::SigningKey::from_pkcs8_pem(pem_text)
            .map_err(|_| AuthError::SigningKeyPem)?;
        Ok(Self {
            issuer: issuer.into(),
            audience: audience.into(),
            key_id: key_id.into(),
            encoding_key: EncodingKey::from_ed_pem(pem).map_err(AuthError::Jwt)?,
            verifying_key: signing_key.verifying_key(),
        })
    }

    pub fn issuer(&self) -> &str {
        &self.issuer
    }

    pub fn audience(&self) -> &str {
        &self.audience
    }

    pub fn key_id(&self) -> &str {
        &self.key_id
    }

    pub fn public_jwk(&self) -> Jwk {
        build_ed25519_jwk(&self.key_id, &self.verifying_key)
    }

    pub fn jwks(&self) -> JwkSet {
        JwkSet {
            keys: vec![self.public_jwk()],
        }
    }

    pub fn mint(
        &self,
        request: MintedTokenRequest,
        now: OffsetDateTime,
        ttl: Duration,
    ) -> Result<MintedToken, AuthError> {
        let expires_at = now + ttl;
        let claims = SessionTokenClaims {
            iss: self.issuer.clone(),
            aud: TokenAudience::One(self.audience.clone()),
            sub: request.subject,
            jti: format!("ns-{}", now.unix_timestamp_nanos()),
            iat: now.unix_timestamp(),
            nbf: now.unix_timestamp(),
            exp: expires_at.unix_timestamp(),
            device_id: request.device_id.as_str().to_owned(),
            manifest_id: request.manifest_id.as_str().to_owned(),
            policy_epoch: request.policy_epoch,
            core_versions: request.core_versions,
            carrier_profiles: request.carrier_profiles,
            capabilities: request.capabilities,
            session_modes: request.session_modes,
            region_scope: request.region_scope,
            token_max_relay_streams: request.token_max_relay_streams,
            token_max_udp_flows: request.token_max_udp_flows,
            token_max_udp_payload: request.token_max_udp_payload,
        };

        let mut header = Header::new(Algorithm::EdDSA);
        header.kid = Some(self.key_id.clone());
        header.typ = Some("JWT".to_owned());
        let token = encode(&header, &claims, &self.encoding_key).map_err(AuthError::Jwt)?;

        Ok(MintedToken { token, expires_at })
    }
}

#[derive(Debug, Error)]
pub enum AuthError {
    #[error("validation failed: {0}")]
    Validation(#[from] ValidationError),
    #[error("token verification failed: {0}")]
    Jwt(#[from] jsonwebtoken::errors::Error),
    #[error("bridge policy derivation failed: {0}")]
    Policy(#[from] ns_policy::PolicyError),
    #[error("token must use EdDSA")]
    UnsupportedAlgorithm,
    #[error("token header must contain kid")]
    MissingKid,
    #[error("token header typ must be JWT when present")]
    InvalidTokenType,
    #[error("signing key PEM was not a valid Ed25519 PKCS#8 document")]
    SigningKeyPem,
    #[error("signing key id is not trusted")]
    UnknownKeyId,
    #[error("duplicate signing key id {0} was present in the JWKS")]
    DuplicateKeyId(String),
    #[error("required claim {0} was missing or empty")]
    MissingClaim(&'static str),
    #[error("token audience does not include northstar-gateway")]
    AudienceMismatch,
    #[error("token manifest_id does not match the session request")]
    ManifestMismatch,
    #[error("token device_id does not match the device binding")]
    DeviceBindingMismatch,
    #[error("requested core version {0} is not allowed by the token")]
    CoreVersionNotAllowed(u64),
    #[error("requested carrier profile {0} is not allowed by the token")]
    CarrierProfileNotAllowed(String),
    #[error("requested capabilities exceed the token allowance")]
    CapabilityNotAllowed,
    #[error("requested session mode {0} is not allowed by the token")]
    SessionModeNotAllowed(String),
    #[error("token subject {0} is revoked")]
    SubjectRevoked(String),
    #[error(
        "token policy_epoch {token_policy_epoch} is below the required minimum {minimum_policy_epoch}"
    )]
    StalePolicyEpoch {
        token_policy_epoch: u64,
        minimum_policy_epoch: u64,
    },
}

fn build_ed25519_jwk(kid: &str, verifying_key: &ed25519_dalek::VerifyingKey) -> Jwk {
    let public = verifying_key.to_bytes();
    let x = {
        use base64::Engine as _;
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(public)
    };

    Jwk {
        common: CommonParameters {
            key_id: Some(kid.to_owned()),
            key_algorithm: Some(jsonwebtoken::jwk::KeyAlgorithm::EdDSA),
            ..Default::default()
        },
        algorithm: AlgorithmParameters::OctetKeyPair(OctetKeyPairParameters {
            key_type: OctetKeyPairType::OctetKeyPair,
            curve: jsonwebtoken::jwk::EllipticCurve::Ed25519,
            x,
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::SigningKey;
    use ed25519_dalek::pkcs8::{EncodePrivateKey, EncodePublicKey};
    use jsonwebtoken::jwk::{
        AlgorithmParameters, CommonParameters, OctetKeyPairParameters, OctetKeyPairType,
    };

    fn request() -> RequestedAccess {
        RequestedAccess {
            core_version: 1,
            carrier_profile_id: CarrierProfileId::new("carrier-primary")
                .expect("fixture carrier profile should be valid"),
            requested_capabilities: vec![Capability::TcpRelay, Capability::UdpRelay],
            manifest_id: ManifestId::new("man-2026-04-01-001")
                .expect("fixture manifest id should be valid"),
            device_binding_id: DeviceBindingId::new("device-1")
                .expect("fixture device binding id should be valid"),
            session_mode: SessionMode::Tcp,
        }
    }

    fn build_jwk(kid: &str, signing_key: &SigningKey) -> Jwk {
        let public = signing_key.verifying_key().to_bytes();
        let x = {
            use base64::Engine as _;
            base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(public)
        };

        Jwk {
            common: CommonParameters {
                key_id: Some(kid.to_owned()),
                key_algorithm: Some(jsonwebtoken::jwk::KeyAlgorithm::EdDSA),
                ..Default::default()
            },
            algorithm: AlgorithmParameters::OctetKeyPair(OctetKeyPairParameters {
                key_type: OctetKeyPairType::OctetKeyPair,
                curve: jsonwebtoken::jwk::EllipticCurve::Ed25519,
                x,
            }),
        }
    }

    #[test]
    fn claims_validation_rejects_manifest_drift() {
        let claims = SessionTokenClaims {
            iss: "bridge".to_owned(),
            aud: TokenAudience::Many(vec![GATEWAY_AUDIENCE.to_owned()]),
            sub: "acct-1".to_owned(),
            jti: "jti-1".to_owned(),
            iat: 1,
            nbf: 1,
            exp: 2,
            device_id: "device-1".to_owned(),
            manifest_id: "man-other".to_owned(),
            policy_epoch: 7,
            core_versions: vec![1],
            carrier_profiles: vec!["carrier-primary".to_owned()],
            capabilities: vec![1, 2],
            session_modes: vec!["tcp".to_owned()],
            region_scope: None,
            token_max_relay_streams: None,
            token_max_udp_flows: None,
            token_max_udp_payload: None,
        };

        let error = SessionTokenVerifier::validate_claims(&claims, &request())
            .expect_err("claims with the wrong manifest id should be rejected");
        assert!(matches!(error, AuthError::ManifestMismatch));
    }

    #[test]
    fn signer_and_verifier_round_trip() {
        let signing_key = SigningKey::from_bytes(&[9_u8; 32]);
        let private_pem = signing_key
            .to_pkcs8_pem(Default::default())
            .expect("test signing key should encode to PKCS#8 PEM")
            .to_string();
        let _public_pem = signing_key
            .verifying_key()
            .to_public_key_pem(Default::default())
            .expect("test verifying key should encode to PEM");

        let signer = SessionTokenSigner::from_ed_pem(
            "bridge.example",
            GATEWAY_AUDIENCE,
            "kid-1",
            private_pem.as_bytes(),
        )
        .expect("PEM signing key should initialize a token signer");
        let now = OffsetDateTime::now_utc();

        let minted = signer
            .mint(
                MintedTokenRequest {
                    subject: "acct-1".to_owned(),
                    device_id: DeviceBindingId::new("device-1")
                        .expect("fixture device binding id should be valid"),
                    manifest_id: ManifestId::new("man-2026-04-01-001")
                        .expect("fixture manifest id should be valid"),
                    policy_epoch: 11,
                    core_versions: vec![1],
                    carrier_profiles: vec!["carrier-primary".to_owned()],
                    capabilities: vec![1, 2],
                    session_modes: vec!["tcp".to_owned()],
                    region_scope: None,
                    token_max_relay_streams: Some(8),
                    token_max_udp_flows: Some(4),
                    token_max_udp_payload: Some(1200),
                },
                now,
                Duration::seconds(300),
            )
            .expect("token minting should succeed for the happy-path fixture");

        let verifier = SessionTokenVerifier::new(
            VerifierConfig {
                trusted_issuers: vec!["bridge.example".to_owned()],
                audience: GATEWAY_AUDIENCE.to_owned(),
                clock_skew: Duration::seconds(5),
                revoked_subjects: Vec::new(),
                minimum_policy_epoch: None,
            },
            TrustedKeySet::from_jwks(&JwkSet {
                keys: vec![build_jwk("kid-1", &signing_key)],
            })
            .expect("fixture JWKS should load into the verifier"),
        );

        let verified = verifier
            .verify(&minted.token, &request())
            .expect("signed test token should verify successfully");
        assert_eq!(verified.claims.policy_epoch, 11);
        assert_eq!(verified.claims.token_max_udp_payload, Some(1200));
    }
}
