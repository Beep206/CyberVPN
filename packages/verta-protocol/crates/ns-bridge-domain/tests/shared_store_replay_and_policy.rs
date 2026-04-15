#![forbid(unsafe_code)]

use ed25519_dalek::SigningKey;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use ns_auth::SessionTokenSigner;
use ns_bridge_domain::{
    BridgeDomain, BridgeDomainError, DeviceRegistrationRequest, TokenExchangeInput,
};
use ns_core::{Capability, DeviceBindingId, ManifestId};
use ns_manifest::ManifestSigner;
use ns_remnawave_adapter::{
    AccountLifecycle, AccountSnapshot, AdapterWebhookEffect, BootstrapSubject, FakeAdapterCall,
    FakeRemnawaveAdapter, VerifiedWebhookPayload, VertaAccess, WebhookAuthenticator,
    WebhookVerificationConfig, WebhookVerificationError, WebhookVerificationInput,
};
use ns_storage::{
    BridgeStore, RefreshCredentialRecord, SqliteBridgeStore, StoredDeviceRecord, StoredDeviceStatus,
};
use serde::Deserialize;
use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};
use time::{Duration, OffsetDateTime};

static SQLITE_TEST_PATH_COUNTER: AtomicU64 = AtomicU64::new(0);

struct AcceptAllWebhookAuthenticator;

impl WebhookAuthenticator for AcceptAllWebhookAuthenticator {
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

#[derive(Debug, Deserialize)]
struct DuplicateWebhookFixture {
    body: String,
    payload: VerifiedWebhookPayload,
    signature_header: String,
    timestamp_header: String,
}

fn temporary_sqlite_store_path() -> PathBuf {
    let mut path = std::env::temp_dir();
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock should be after the unix epoch")
        .as_nanos();
    let counter = SQLITE_TEST_PATH_COUNTER.fetch_add(1, Ordering::Relaxed);
    let pid = std::process::id();
    path.push(format!(
        "verta-bridge-domain-{pid}-{nonce}-{counter}.sqlite3"
    ));
    path
}

fn cleanup_sqlite_store_path(path: &Path) {
    let candidates = [
        path.to_path_buf(),
        PathBuf::from(format!("{}-wal", path.display())),
        PathBuf::from(format!("{}-shm", path.display())),
    ];

    for _ in 0..10 {
        let mut busy = false;
        let mut remaining = false;

        for candidate in &candidates {
            if !candidate.exists() {
                continue;
            }
            remaining = true;
            match fs::remove_file(candidate) {
                Ok(()) => {}
                Err(error)
                    if error.kind() == ErrorKind::NotFound || error.raw_os_error() == Some(2) => {}
                Err(error)
                    if error.kind() == ErrorKind::PermissionDenied
                        || error.raw_os_error() == Some(32) =>
                {
                    busy = true;
                    break;
                }
                Err(error) => panic!(
                    "sqlite test store artifact should be removable ({}): {error}",
                    candidate.display()
                ),
            }
        }

        if !busy && (!remaining || candidates.iter().all(|candidate| !candidate.exists())) {
            return;
        }

        std::thread::sleep(std::time::Duration::from_millis(25));
    }

    let remaining: Vec<String> = candidates
        .iter()
        .filter(|candidate| candidate.exists())
        .map(|candidate| candidate.display().to_string())
        .collect();
    panic!(
        "sqlite test store artifacts should be removable after retries: {}",
        remaining.join(", ")
    );
}

fn active_snapshot() -> AccountSnapshot {
    AccountSnapshot {
        account_id: "acct-1".to_owned(),
        bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
        lifecycle: AccountLifecycle::Active,
        verta_access: VertaAccess {
            verta_enabled: true,
            policy_epoch: 7,
            device_limit: Some(2),
            allowed_core_versions: vec![1],
            allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
            allowed_capabilities: vec![Capability::TcpRelay.id(), Capability::UdpRelay.id()],
            rollout_cohort: Some("alpha".to_owned()),
            preferred_regions: vec!["eu-central".to_owned()],
        },
        metadata: None,
        observed_at_unix: 1_700_000_000,
        source_version: Some("2.7.4".to_owned()),
    }
}

fn bridge_with_adapter_and_store(
    adapter: FakeRemnawaveAdapter,
    store: SqliteBridgeStore,
) -> BridgeDomain<FakeRemnawaveAdapter, SqliteBridgeStore> {
    let token_signing_key = SigningKey::from_bytes(&[12_u8; 32]);
    let pem = token_signing_key
        .to_pkcs8_pem(Default::default())
        .expect("test signing key should encode");
    let signer =
        SessionTokenSigner::from_ed_pem("bridge.example", "verta-gateway", "kid-1", pem.as_bytes())
            .expect("test bridge signer should initialize");
    let manifest_signer =
        ManifestSigner::new("bridge-manifest-key", SigningKey::from_bytes(&[14_u8; 32]));

    BridgeDomain::new(
        adapter,
        store,
        manifest_signer,
        signer,
        Duration::seconds(300),
    )
}

fn load_duplicate_webhook_fixture() -> DuplicateWebhookFixture {
    let mut root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    root.pop();
    root.pop();
    let fixture =
        fs::read_to_string(root.join("fixtures/remnawave/webhook/BG-WEBHOOK-DUPLICATE-006.json"))
            .expect("duplicate-webhook fixture should be readable");

    serde_json::from_str(&fixture).expect("duplicate-webhook fixture should parse")
}

#[tokio::test]
async fn duplicate_verified_webhook_is_rejected_across_bridge_instances() {
    let fixture = load_duplicate_webhook_fixture();
    let path = temporary_sqlite_store_path();
    let adapter = FakeRemnawaveAdapter::with_account(
        BootstrapSubject::ShortUuid("sub-1".to_owned()),
        active_snapshot(),
    );
    adapter.push_webhook_effect(AdapterWebhookEffect::ReconcileAccount {
        account_id: "acct-1".to_owned(),
        reason: "duplicate-check".to_owned(),
    });

    let domain_a = bridge_with_adapter_and_store(
        adapter.clone(),
        SqliteBridgeStore::open(&path).expect("first sqlite store should initialize"),
    );
    let domain_b = bridge_with_adapter_and_store(
        adapter.clone(),
        SqliteBridgeStore::open(&path).expect("second sqlite store should initialize"),
    );
    let now = OffsetDateTime::from_unix_timestamp(1_775_002_200)
        .expect("fixture timestamp should be valid");

    let effect = domain_a
        .ingest_verified_webhook(
            WebhookVerificationInput {
                signature_header: &fixture.signature_header,
                timestamp_header: &fixture.timestamp_header,
                body: fixture.body.as_bytes(),
            },
            &AcceptAllWebhookAuthenticator,
            fixture.payload.clone(),
            now,
            WebhookVerificationConfig {
                max_skew: Duration::seconds(30),
            },
        )
        .await
        .expect("first verified webhook delivery should succeed");
    assert!(matches!(
        effect,
        AdapterWebhookEffect::ReconcileAccount { .. }
    ));

    let error = domain_b
        .ingest_verified_webhook(
            WebhookVerificationInput {
                signature_header: &fixture.signature_header,
                timestamp_header: &fixture.timestamp_header,
                body: fixture.body.as_bytes(),
            },
            &AcceptAllWebhookAuthenticator,
            fixture.payload,
            now,
            WebhookVerificationConfig {
                max_skew: Duration::seconds(30),
            },
        )
        .await
        .expect_err("duplicate verified webhook delivery should be rejected across instances");

    assert!(matches!(error, BridgeDomainError::DuplicateWebhookDelivery));
    assert_eq!(
        adapter
            .calls()
            .into_iter()
            .filter(|call| matches!(call, FakeAdapterCall::IngestWebhook { .. }))
            .count(),
        1
    );

    drop(domain_a);
    drop(domain_b);
    cleanup_sqlite_store_path(path.as_path());
}

#[tokio::test]
async fn device_limit_is_enforced_across_bridge_instances() {
    let path = temporary_sqlite_store_path();
    let manifest_id =
        ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");
    let mut snapshot = active_snapshot();
    snapshot.verta_access.device_limit = Some(1);
    let adapter = FakeRemnawaveAdapter::with_account(
        BootstrapSubject::ShortUuid("sub-1".to_owned()),
        snapshot.clone(),
    );
    let domain_a = bridge_with_adapter_and_store(
        adapter.clone(),
        SqliteBridgeStore::open(&path).expect("first sqlite store should initialize"),
    );
    let domain_b = bridge_with_adapter_and_store(
        adapter,
        SqliteBridgeStore::open(&path).expect("second sqlite store should initialize"),
    );

    domain_a
        .register_device(
            &snapshot,
            DeviceRegistrationRequest {
                manifest_id: manifest_id.clone(),
                device_id: DeviceBindingId::new("device-1")
                    .expect("fixture device binding id should be valid"),
                device_name: Some("Device 1".to_owned()),
                platform: "windows".to_owned(),
                client_version: "0.1.0".to_owned(),
                install_channel: Some("stable".to_owned()),
            },
            OffsetDateTime::from_unix_timestamp(1_700_000_000)
                .expect("fixture timestamp should be valid"),
        )
        .await
        .expect("first device registration should succeed");

    let error = domain_b
        .register_device(
            &snapshot,
            DeviceRegistrationRequest {
                manifest_id,
                device_id: DeviceBindingId::new("device-2")
                    .expect("fixture device binding id should be valid"),
                device_name: Some("Device 2".to_owned()),
                platform: "windows".to_owned(),
                client_version: "0.1.0".to_owned(),
                install_channel: Some("stable".to_owned()),
            },
            OffsetDateTime::from_unix_timestamp(1_700_000_100)
                .expect("fixture timestamp should be valid"),
        )
        .await
        .expect_err("second device registration should observe the shared device limit");

    assert!(matches!(
        error,
        BridgeDomainError::DeviceLimitReached { max_devices: 1 }
    ));

    drop(domain_a);
    drop(domain_b);
    cleanup_sqlite_store_path(path.as_path());
}

#[tokio::test]
async fn revoked_device_blocks_token_exchange_after_reopen() {
    let path = temporary_sqlite_store_path();
    let manifest_id =
        ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");
    let device_id =
        DeviceBindingId::new("device-2").expect("fixture device binding id should be valid");

    let store = SqliteBridgeStore::open(&path).expect("sqlite bridge store should initialize");
    store
        .upsert_device(StoredDeviceRecord {
            account_id: "acct-1".to_owned(),
            device_id: device_id.clone(),
            status: StoredDeviceStatus::Revoked,
        })
        .await
        .expect("revoked device should store");
    store
        .store_refresh_credential(
            "rfr_revoked_device",
            RefreshCredentialRecord {
                account_id: "acct-1".to_owned(),
                device_id: device_id.clone(),
                manifest_id: manifest_id.clone(),
                revoked: false,
            },
        )
        .await
        .expect("refresh credential should store");

    let domain = bridge_with_adapter_and_store(
        FakeRemnawaveAdapter::with_account(
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
            active_snapshot(),
        ),
        SqliteBridgeStore::open(&path).expect("sqlite bridge store should reopen"),
    );

    let error = domain
        .exchange_token(
            &active_snapshot(),
            TokenExchangeInput {
                manifest_id,
                device_id,
                client_version: "0.1.0".to_owned(),
                core_version: 1,
                carrier_profile_id: "carrier-primary".to_owned(),
                requested_capabilities: vec![Capability::TcpRelay.id()],
                refresh_credential: "rfr_revoked_device".to_owned(),
            },
            OffsetDateTime::from_unix_timestamp(1_700_000_010)
                .expect("fixture timestamp should be valid"),
        )
        .await
        .expect_err("revoked device should still be rejected after reopen");

    assert!(matches!(error, BridgeDomainError::DeviceRevoked));

    drop(store);
    drop(domain);
    cleanup_sqlite_store_path(path.as_path());
}

#[tokio::test]
async fn refresh_credential_manifest_binding_survives_reopen() {
    let path = temporary_sqlite_store_path();
    let stored_manifest_id =
        ManifestId::new("man-2026-04-01-001").expect("fixture manifest id should be valid");
    let wrong_manifest_id =
        ManifestId::new("man-2026-04-01-002").expect("fixture manifest id should be valid");
    let device_id =
        DeviceBindingId::new("device-3").expect("fixture device binding id should be valid");

    let store = SqliteBridgeStore::open(&path).expect("sqlite bridge store should initialize");
    store
        .upsert_device(StoredDeviceRecord {
            account_id: "acct-1".to_owned(),
            device_id: device_id.clone(),
            status: StoredDeviceStatus::Active,
        })
        .await
        .expect("active device should store");
    store
        .store_refresh_credential(
            "rfr_manifest_bound",
            RefreshCredentialRecord {
                account_id: "acct-1".to_owned(),
                device_id: device_id.clone(),
                manifest_id: stored_manifest_id,
                revoked: false,
            },
        )
        .await
        .expect("refresh credential should store");

    let domain = bridge_with_adapter_and_store(
        FakeRemnawaveAdapter::with_account(
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
            active_snapshot(),
        ),
        SqliteBridgeStore::open(&path).expect("sqlite bridge store should reopen"),
    );

    let error = domain
        .exchange_token(
            &active_snapshot(),
            TokenExchangeInput {
                manifest_id: wrong_manifest_id,
                device_id,
                client_version: "0.1.0".to_owned(),
                core_version: 1,
                carrier_profile_id: "carrier-primary".to_owned(),
                requested_capabilities: vec![Capability::TcpRelay.id()],
                refresh_credential: "rfr_manifest_bound".to_owned(),
            },
            OffsetDateTime::from_unix_timestamp(1_700_000_010)
                .expect("fixture timestamp should be valid"),
        )
        .await
        .expect_err("persisted refresh credentials should stay bound to their manifest");

    assert!(matches!(
        error,
        BridgeDomainError::RefreshCredentialManifestMismatch
    ));

    drop(store);
    drop(domain);
    cleanup_sqlite_store_path(path.as_path());
}
