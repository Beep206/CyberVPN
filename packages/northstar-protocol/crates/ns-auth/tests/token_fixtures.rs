use base64::Engine as _;
use ed25519_dalek::SigningKey;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use jsonwebtoken::jwk::{
    AlgorithmParameters, CommonParameters, Jwk, JwkSet, OctetKeyPairParameters, OctetKeyPairType,
};
use ns_auth::{
    AuthError, MintedTokenRequest, RequestedAccess, SessionTokenSigner, SessionTokenVerifier,
    TokenAudience, TrustedKeySet, VerifierConfig,
};
use ns_core::{Capability, CarrierProfileId, DeviceBindingId, ManifestId, SessionMode};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;
use time::{Duration, OffsetDateTime};

const FIXTURE_TOKEN_KEY_ID: &str = "fixture-token-key-1";

#[derive(Debug, Deserialize)]
struct ValidTokenFixture {
    capabilities: Vec<u64>,
    carrier_profiles: Vec<String>,
    core_versions: Vec<u64>,
    device_id: String,
    issuer: String,
    manifest_id: String,
    policy_epoch: u64,
    region_scope: Option<String>,
    session_modes: Vec<String>,
    subject: String,
    ttl_seconds: i64,
}

#[derive(Debug, Deserialize)]
struct StaleJwksFixture {
    #[serde(rename = "token")]
    _token: String,
    jwks: JwkSet,
}

#[derive(Debug, Deserialize)]
struct RevokedSubjectFixture {
    #[serde(rename = "token")]
    _token: String,
    revoked_subjects: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct StalePolicyFixture {
    #[serde(rename = "token")]
    _token: String,
    minimum_policy_epoch: u64,
}

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

fn build_jwk(kid: &str) -> Jwk {
    let public = SigningKey::from_bytes(&[42_u8; 32])
        .verifying_key()
        .to_bytes();
    let x = base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(public);

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

fn load_fixture_text(relative: &str) -> String {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    fs::read_to_string(root.join("fixtures").join(relative))
        .expect("token fixture should be readable")
}

fn load_valid_fixture(relative: &str) -> ValidTokenFixture {
    serde_json::from_str(&load_fixture_text(relative))
        .expect("valid token fixture json should parse")
}

fn load_json_fixture<T: for<'de> Deserialize<'de>>(relative: &str) -> T {
    serde_json::from_str(&load_fixture_text(relative)).expect("json token fixture should parse")
}

fn mint_valid_fixture_token(now: OffsetDateTime) -> String {
    let fixture = load_valid_fixture("token/jws/valid/AU-TOKEN-VALID-001.json");
    let signing_key = SigningKey::from_bytes(&[42_u8; 32]);
    let pem = signing_key
        .to_pkcs8_pem(Default::default())
        .expect("fixture token signing key should encode");
    let signer = SessionTokenSigner::from_ed_pem(
        &fixture.issuer,
        "northstar-gateway",
        FIXTURE_TOKEN_KEY_ID,
        pem.as_bytes(),
    )
    .expect("fixture token signer should initialize");

    signer
        .mint(
            MintedTokenRequest {
                subject: fixture.subject,
                device_id: DeviceBindingId::new(fixture.device_id)
                    .expect("fixture device binding id should be valid"),
                manifest_id: ManifestId::new(fixture.manifest_id)
                    .expect("fixture manifest id should be valid"),
                policy_epoch: fixture.policy_epoch,
                core_versions: fixture.core_versions,
                carrier_profiles: fixture.carrier_profiles,
                capabilities: fixture.capabilities,
                session_modes: fixture.session_modes,
                region_scope: fixture.region_scope,
                token_max_relay_streams: Some(8),
                token_max_udp_flows: Some(4),
                token_max_udp_payload: Some(1200),
            },
            now,
            Duration::seconds(fixture.ttl_seconds),
        )
        .expect("valid token fixture should mint successfully")
        .token
}

fn verifier() -> SessionTokenVerifier {
    SessionTokenVerifier::new(
        VerifierConfig {
            trusted_issuers: vec!["bridge.example".to_owned()],
            audience: "northstar-gateway".to_owned(),
            clock_skew: Duration::seconds(5),
            revoked_subjects: Vec::new(),
            minimum_policy_epoch: None,
        },
        TrustedKeySet::from_jwks(&JwkSet {
            keys: vec![build_jwk(FIXTURE_TOKEN_KEY_ID)],
        })
        .expect("fixture jwks should load"),
    )
}

#[test]
fn accepts_valid_token_fixture() {
    let fixture = load_valid_fixture("token/jws/valid/AU-TOKEN-VALID-001.json");
    let signing_key = SigningKey::from_bytes(&[42_u8; 32]);
    let pem = signing_key
        .to_pkcs8_pem(Default::default())
        .expect("fixture token signing key should encode");
    let signer = SessionTokenSigner::from_ed_pem(
        &fixture.issuer,
        "northstar-gateway",
        FIXTURE_TOKEN_KEY_ID,
        pem.as_bytes(),
    )
    .expect("fixture token signer should initialize");
    let minted = signer
        .mint(
            MintedTokenRequest {
                subject: fixture.subject,
                device_id: DeviceBindingId::new(fixture.device_id)
                    .expect("fixture device binding id should be valid"),
                manifest_id: ManifestId::new(fixture.manifest_id)
                    .expect("fixture manifest id should be valid"),
                policy_epoch: fixture.policy_epoch,
                core_versions: fixture.core_versions,
                carrier_profiles: fixture.carrier_profiles,
                capabilities: fixture.capabilities,
                session_modes: fixture.session_modes,
                region_scope: fixture.region_scope,
                token_max_relay_streams: Some(8),
                token_max_udp_flows: Some(4),
                token_max_udp_payload: Some(1200),
            },
            OffsetDateTime::now_utc(),
            Duration::seconds(fixture.ttl_seconds),
        )
        .expect("valid token fixture should mint successfully");
    let verified = verifier()
        .verify(&minted.token, &request())
        .expect("valid token fixture should verify");

    assert!(matches!(verified.claims.aud, TokenAudience::One(_)));
    assert_eq!(verified.claims.manifest_id, "man-2026-04-01-001");
}

#[test]
fn rejects_expired_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-EXPIRED-002.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("expired token fixture should be rejected");
    assert!(matches!(error, AuthError::Jwt(_)));
}

#[test]
fn rejects_future_nbf_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-NBF-FUTURE-003.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("future-nbf token fixture should be rejected");
    assert!(matches!(error, AuthError::Jwt(_)));
}

#[test]
fn rejects_wrong_issuer_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-WRONGISS-004.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("wrong-issuer token fixture should be rejected");
    assert!(matches!(error, AuthError::Jwt(_)));
}

#[test]
fn rejects_wrong_audience_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-WRONGAUD-005.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("wrong-audience token fixture should be rejected");
    assert!(matches!(
        error,
        AuthError::Jwt(_) | AuthError::AudienceMismatch
    ));
}

#[test]
fn rejects_wrong_algorithm_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-WRONGALG-006.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("wrong-algorithm token fixture should be rejected");
    assert!(matches!(error, AuthError::UnsupportedAlgorithm));
}

#[test]
fn rejects_unknown_kid_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-UNKNOWNKID-007.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("unknown-kid token fixture should be rejected");
    assert!(matches!(error, AuthError::UnknownKeyId));
}

#[test]
fn rejects_wrong_type_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-WRONGTYP-008.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("wrong-typ token fixture should be rejected");
    assert!(matches!(error, AuthError::InvalidTokenType));
}

#[test]
fn rejects_missing_type_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-NOTYP-010.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("missing-typ token fixture should be rejected");
    assert!(matches!(error, AuthError::InvalidTokenType));
}

#[test]
fn rejects_malformed_token_fixture() {
    let token = load_fixture_text("token/jws/invalid/AU-TOKEN-MALFORMED-009.jwt");
    let error = verifier()
        .verify(token.trim(), &request())
        .expect_err("malformed token fixture should be rejected");
    assert!(matches!(error, AuthError::Jwt(_)));
}

#[test]
fn rejects_duplicate_kid_jwks() {
    let error = TrustedKeySet::from_jwks(&JwkSet {
        keys: vec![
            build_jwk(FIXTURE_TOKEN_KEY_ID),
            build_jwk(FIXTURE_TOKEN_KEY_ID),
        ],
    })
    .expect_err("duplicate kid JWKS should be rejected");

    assert!(matches!(error, AuthError::DuplicateKeyId(_)));
}

#[test]
fn rejects_stale_jwks_fixture() {
    let fixture: StaleJwksFixture =
        load_json_fixture("token/jws/invalid/AU-TOKEN-STALEJWKS-011.json");
    let token = mint_valid_fixture_token(OffsetDateTime::now_utc());
    let verifier = SessionTokenVerifier::new(
        VerifierConfig {
            trusted_issuers: vec!["bridge.example".to_owned()],
            audience: "northstar-gateway".to_owned(),
            clock_skew: Duration::seconds(5),
            revoked_subjects: Vec::new(),
            minimum_policy_epoch: None,
        },
        TrustedKeySet::from_jwks(&fixture.jwks).expect("stale fixture JWKS should parse"),
    );

    let error = verifier
        .verify(&token, &request())
        .expect_err("stale-JWKS fixture should be rejected");
    assert!(matches!(error, AuthError::Jwt(_)));
}

#[test]
fn rejects_revoked_subject_fixture() {
    let fixture: RevokedSubjectFixture =
        load_json_fixture("token/jws/invalid/AU-TOKEN-REVOKEDSUB-012.json");
    let token = mint_valid_fixture_token(OffsetDateTime::now_utc());
    let verifier = SessionTokenVerifier::new(
        VerifierConfig {
            trusted_issuers: vec!["bridge.example".to_owned()],
            audience: "northstar-gateway".to_owned(),
            clock_skew: Duration::seconds(5),
            revoked_subjects: fixture.revoked_subjects,
            minimum_policy_epoch: None,
        },
        TrustedKeySet::from_jwks(&JwkSet {
            keys: vec![build_jwk(FIXTURE_TOKEN_KEY_ID)],
        })
        .expect("fixture jwks should load"),
    );

    let error = verifier
        .verify(&token, &request())
        .expect_err("revoked-subject fixture should be rejected");
    assert!(matches!(error, AuthError::SubjectRevoked(subject) if subject == "acct-1"));
}

#[test]
fn rejects_stale_policy_epoch_fixture() {
    let fixture: StalePolicyFixture =
        load_json_fixture("token/jws/invalid/AU-TOKEN-STALEPOLICY-013.json");
    let token = mint_valid_fixture_token(OffsetDateTime::now_utc());
    let verifier = SessionTokenVerifier::new(
        VerifierConfig {
            trusted_issuers: vec!["bridge.example".to_owned()],
            audience: "northstar-gateway".to_owned(),
            clock_skew: Duration::seconds(5),
            revoked_subjects: Vec::new(),
            minimum_policy_epoch: Some(fixture.minimum_policy_epoch),
        },
        TrustedKeySet::from_jwks(&JwkSet {
            keys: vec![build_jwk(FIXTURE_TOKEN_KEY_ID)],
        })
        .expect("fixture jwks should load"),
    );

    let error = verifier
        .verify(&token, &request())
        .expect_err("stale-policy fixture should be rejected");
    assert!(matches!(
        error,
        AuthError::StalePolicyEpoch {
            token_policy_epoch: 7,
            minimum_policy_epoch: 8
        }
    ));
}
