use ns_remnawave_adapter::{
    WebhookAuthenticator, WebhookVerificationConfig, WebhookVerificationError,
    WebhookVerificationInput, verify_webhook_input,
};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;
use time::{Duration, OffsetDateTime};

#[derive(Debug, Deserialize)]
struct WebhookFixture {
    body: String,
    signature_header: String,
    timestamp_header: String,
}

struct FixtureAuthenticator;

impl WebhookAuthenticator for FixtureAuthenticator {
    fn verify(
        &self,
        _timestamp_header: &str,
        signature_header: &str,
        _body: &[u8],
    ) -> Result<(), WebhookVerificationError> {
        match signature_header {
            "sig-ok" => Ok(()),
            _ => Err(WebhookVerificationError::InvalidSignature),
        }
    }
}

fn now() -> OffsetDateTime {
    OffsetDateTime::from_unix_timestamp(1_775_002_200).expect("fixture timestamp should be valid")
}

fn load_fixture(path: &str) -> WebhookFixture {
    serde_json::from_str(&load_fixture_text(path)).expect("webhook fixture json should parse")
}

fn load_fixture_text(relative: &str) -> String {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    fs::read_to_string(root.join("fixtures").join(relative))
        .expect("webhook fixture should be readable")
}

#[test]
fn accepts_valid_webhook_fixture() {
    let fixture = load_fixture("remnawave/webhook/BG-WEBHOOK-VALID-001.json");
    verify_webhook_input(
        WebhookVerificationInput {
            signature_header: &fixture.signature_header,
            timestamp_header: &fixture.timestamp_header,
            body: fixture.body.as_bytes(),
        },
        &FixtureAuthenticator,
        now(),
        WebhookVerificationConfig {
            max_skew: Duration::seconds(30),
        },
    )
    .expect("valid webhook fixture should verify");
}

#[test]
fn rejects_stale_webhook_fixture() {
    let fixture = load_fixture("remnawave/webhook/BG-WEBHOOK-STALE-002.json");
    let error = verify_webhook_input(
        WebhookVerificationInput {
            signature_header: &fixture.signature_header,
            timestamp_header: &fixture.timestamp_header,
            body: fixture.body.as_bytes(),
        },
        &FixtureAuthenticator,
        now(),
        WebhookVerificationConfig {
            max_skew: Duration::seconds(30),
        },
    )
    .expect_err("stale webhook fixture should be rejected");

    assert!(matches!(error, WebhookVerificationError::StaleTimestamp));
}

#[test]
fn rejects_bad_signature_webhook_fixture() {
    let fixture = load_fixture("remnawave/webhook/BG-WEBHOOK-BADSIG-003.json");
    let error = verify_webhook_input(
        WebhookVerificationInput {
            signature_header: &fixture.signature_header,
            timestamp_header: &fixture.timestamp_header,
            body: fixture.body.as_bytes(),
        },
        &FixtureAuthenticator,
        now(),
        WebhookVerificationConfig {
            max_skew: Duration::seconds(30),
        },
    )
    .expect_err("bad-signature webhook fixture should be rejected");

    assert!(matches!(error, WebhookVerificationError::InvalidSignature));
}

#[test]
fn rejects_missing_signature_webhook_fixture() {
    let fixture = load_fixture("remnawave/webhook/BG-WEBHOOK-MISSINGSIG-004.json");
    let error = verify_webhook_input(
        WebhookVerificationInput {
            signature_header: &fixture.signature_header,
            timestamp_header: &fixture.timestamp_header,
            body: fixture.body.as_bytes(),
        },
        &FixtureAuthenticator,
        now(),
        WebhookVerificationConfig {
            max_skew: Duration::seconds(30),
        },
    )
    .expect_err("missing-signature webhook fixture should be rejected");

    assert!(matches!(error, WebhookVerificationError::MissingSignature));
}

#[test]
fn rejects_invalid_timestamp_webhook_fixture() {
    let fixture = load_fixture("remnawave/webhook/BG-WEBHOOK-BADTIMESTAMP-005.json");
    let error = verify_webhook_input(
        WebhookVerificationInput {
            signature_header: &fixture.signature_header,
            timestamp_header: &fixture.timestamp_header,
            body: fixture.body.as_bytes(),
        },
        &FixtureAuthenticator,
        now(),
        WebhookVerificationConfig {
            max_skew: Duration::seconds(30),
        },
    )
    .expect_err("invalid-timestamp webhook fixture should be rejected");

    assert!(matches!(error, WebhookVerificationError::InvalidTimestamp));
}
