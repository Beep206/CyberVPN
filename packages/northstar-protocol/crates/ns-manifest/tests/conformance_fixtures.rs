use ed25519_dalek::SigningKey;
use ns_manifest::{ManifestDocument, ManifestError, ManifestTrustStore};
use std::fs;
use std::path::PathBuf;
use time::OffsetDateTime;

fn verification_now() -> OffsetDateTime {
    OffsetDateTime::parse(
        "2026-04-01T00:20:00Z",
        &time::format_description::well_known::Rfc3339,
    )
    .expect("fixture timestamp should parse")
}

fn load_fixture_text(relative: &str) -> String {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    fs::read_to_string(root.join("fixtures").join(relative))
        .expect("manifest fixture should be readable")
}

fn fixture_manifest_trust_store() -> ManifestTrustStore {
    let signing_key = SigningKey::from_bytes(&[41_u8; 32]);
    let mut trust_store = ManifestTrustStore::default();
    trust_store.insert("fixture-manifest-key-1", signing_key.verifying_key());
    trust_store
}

#[test]
fn accepts_valid_signed_manifest_fixture() {
    let manifest_json = load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json");
    let manifest = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &fixture_manifest_trust_store(),
        verification_now(),
    )
    .expect("valid signed manifest fixture should verify");

    assert_eq!(manifest.manifest_id, "man-2026-04-01-001");
    assert_eq!(manifest.signature.key_id, "fixture-manifest-key-1");
}

#[test]
fn rejects_tampered_manifest_fixture() {
    let manifest_json = load_fixture_text("manifest/v1/invalid/MF-MANIFEST-BADSIG-002.json");
    let error = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &fixture_manifest_trust_store(),
        verification_now(),
    )
    .expect_err("tampered manifest fixture should be rejected");

    assert!(matches!(error, ManifestError::SignatureVerificationFailed));
}

#[test]
fn rejects_expired_manifest_fixture() {
    let manifest_json = load_fixture_text("manifest/v1/invalid/MF-MANIFEST-EXPIRED-003.json");
    let error = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &fixture_manifest_trust_store(),
        verification_now(),
    )
    .expect_err("expired manifest fixture should be rejected");

    assert!(matches!(error, ManifestError::ExpiredManifest));
}

#[test]
fn rejects_wrong_schema_manifest_fixture() {
    let manifest_json = load_fixture_text("manifest/v1/invalid/MF-MANIFEST-SCHEMA-004.json");
    let error = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &fixture_manifest_trust_store(),
        verification_now(),
    )
    .expect_err("wrong-schema manifest fixture should be rejected");

    assert!(matches!(error, ManifestError::UnsupportedSchemaVersion(2)));
}

#[test]
fn rejects_manifest_with_unknown_signature_key() {
    let manifest_json = load_fixture_text("manifest/v1/valid/MF-MANIFEST-VALID-001.json");
    let error = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &ManifestTrustStore::default(),
        verification_now(),
    )
    .expect_err("manifest signed by an unknown key should be rejected");

    assert!(matches!(error, ManifestError::UnknownSignatureKey(_)));
}

#[test]
fn accepts_disabled_profile_fixture_as_a_signed_but_context_sensitive_manifest() {
    let manifest_json = load_fixture_text("manifest/v1/valid/MF-DISABLEDPROFILE-006.json");
    let manifest = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &fixture_manifest_trust_store(),
        verification_now(),
    )
    .expect("disabled-profile manifest should still be structurally valid");

    assert!(
        manifest
            .carrier_profiles
            .iter()
            .any(|profile| profile.id == "carrier-primary")
    );
}

#[test]
fn rejects_empty_inventory_manifest_fixture() {
    let manifest_json = load_fixture_text("manifest/v1/invalid/MF-EMPTYINVENTORY-007.json");
    let error = ManifestDocument::parse_and_verify_json(
        &manifest_json,
        &fixture_manifest_trust_store(),
        verification_now(),
    )
    .expect_err("empty-inventory manifest should be rejected");

    assert!(matches!(error, ManifestError::NoEndpoints));
}
