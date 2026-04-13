# Remnawave Integration Notes

## Status

Implementation packet for the initial non-fork Bridge path.
This note is operational guidance for the Rust workspace. Normative behavior remains in:

- `docs/spec/northstar_remnawave_bridge_spec_v0_1.md`
- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_implementation_spec_rust_workspace_plan_v0_1.md`

## Hard Rules

- Do not fork Remnawave.
- Do not put the Bridge in the data path.
- Do not let Remnawave-specific logic leak into session-core or carrier crates.
- Do not let gateways accept bootstrap inputs, refresh credentials, or raw `shortUuid`.
- Do not treat Remnawave payloads as trusted runtime state until normalized.
- Do not invent new public Bridge fields or credential formats without checking the frozen `/v0` contract first.

## Authority Split

| Domain | Authority | Initial implementation note |
|---|---|---|
| User lifecycle, subscription identifier, entitlement | Remnawave | Read through adapter only |
| Gateway inventory, carrier profiles, manifest compilation | Bridge | Bridge-owned state |
| Device bindings, refresh credentials, session tokens | Bridge | Bridge-owned state |
| Gateway session admission | Gateway + Bridge-issued token | No Remnawave calls at session start |
| Transport behavior | Session/core + carrier crates | Must stay outside Bridge |

## Initial Crate Ownership

| Crate | Owns | Must not own |
|---|---|---|
| `crates/ns-bridge-api` | `/v0/*` request and response models, HTTP handlers, error envelope mapping | Remnawave polling, session/core logic |
| `crates/ns-bridge-domain` | normalized account state, device registry logic, manifest compile inputs, token issuance orchestration | raw upstream JSON, HTTP framework details |
| `crates/ns-remnawave-adapter` | fake and HTTP-backed Remnawave API clients, webhook normalization, schema-drift detection, retry/backoff | session/core, carrier logic |
| `apps/ns-bridge` | process composition, config, runtime wiring, adapter/store selection | domain logic hidden in handlers |

## Initial Public Contract Models

The Bridge public API shape is already frozen under `/v0/*`. The implementation should map directly onto the documented request and response bodies.

### Stable error envelope

```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BridgeErrorEnvelope {
    pub error: BridgeErrorBody,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BridgeErrorBody {
    pub code: BridgeErrorCode,
    pub message: String,
    pub retryable: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub policy_epoch: Option<u64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum BridgeErrorCode {
    InvalidBootstrapSubject,
    BootstrapExpired,
    AccountNotFound,
    AccountDisabled,
    AccountRevoked,
    AccountExpired,
    AccountLimited,
    ManifestNotAvailable,
    DeviceBindingRequired,
    DeviceLimitReached,
    DeviceRevoked,
    InvalidRefreshCredential,
    RefreshCredentialExpired,
    ProfileNotAllowed,
    CoreVersionNotAllowed,
    ClientVersionTooOld,
    RateLimited,
    UpstreamControlPlaneUnavailable,
    TemporaryReconciliationInProgress,
}
```

### `POST /v0/device/register`

```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeviceRegisterRequest {
    pub manifest_id: String,
    pub device_id: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub device_name: Option<String>,
    pub platform: String,
    pub client_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub install_channel: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub requested_capabilities: Vec<u16>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeviceRegisterResponse {
    pub device_id: String,
    pub binding_required: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub refresh_credential: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub warnings: Vec<String>,
}
```

### `POST /v0/token/exchange`

```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TokenExchangeRequest {
    pub manifest_id: String,
    pub device_id: String,
    pub client_version: String,
    pub core_version: u16,
    pub carrier_profile_id: String,
    pub requested_capabilities: Vec<u16>,
    pub refresh_credential: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TokenExchangeResponse {
    pub session_token: String,
    pub expires_at: String,
    pub policy_epoch: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub recommended_endpoints: Vec<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub warnings: Vec<String>,
}
```

### `GET /v0/manifest`

HTTP shape is frozen already:

- bootstrap mode: `GET /v0/manifest?subscription_token=<bootstrap-subject>`
- steady-state mode: `GET /v0/manifest` with `Authorization: Bearer <refresh-credential>`
- conditional fetch: optional `If-None-Match`

Implementation rule:

- bootstrap mode and refresh mode must map into different auth contexts internally
- bootstrap mode must be stricter about upstream freshness than steady-state refresh mode
- `ETag` handling belongs in `ns-bridge-api`, but manifest hash generation belongs in `ns-bridge-domain`

## Milestone 9 Runtime Composition Notes

Milestone 9 keeps the public bridge contract unchanged and expands only runtime wiring:

- `apps/ns-bridge` can now compose either the fake adapter or the initial `HttpRemnawaveAdapter`
- the bridge-store path can now sit behind an authenticated semantic HTTP service instead of only a local SQLite-backed store
- remote/shared store startup still fails closed unless health reports `SharedDurable`
- store-service auth is intentionally internal and does not change the frozen public `/v0/*` bridge surface

This keeps upstream Remnawave integration injectable at process-composition time without widening `ns-bridge-domain` or `ns-bridge-api` contracts.

## Milestone 10 Deployment Notes

Milestone 10 keeps the same non-fork bridge contract and tightens deployment posture:

- internal store-service auth is now mandatory in app-level remote/shared bridge-store mode
- internal store-service `500` responses are now redacted to a generic failure body instead of echoing backend details
- `apps/ns-bridge` now exposes a deployment-shaped `serve-topology` path that runs a separate internal store-service runtime plus a public bridge runtime over the authenticated service-backed store path
- the public runtime can still host either the fake adapter or the initial HTTP Remnawave adapter without widening bridge-domain contracts

This milestone does not change the frozen public `/v0/*` surface.
It changes only deployment composition, remote-store hardening, and test coverage.

## Milestone 11 Operator Notes

Milestone 11 keeps the same non-fork bridge contract and extends the operator-facing deployment shape:

- the authenticated remote/shared bridge-store path now supports ordered fallback endpoints for health checks and command traffic
- unauthorized primary endpoints remain terminal and do not trigger failover
- `apps/ns-bridge` now has explicit topology runtime composition coverage for startup, health, shutdown, and remote-store auth mismatch
- the topology path now exercises the real `HttpRemnawaveAdapter` against a realistic upstream test server for manifest fetch, device register, and token exchange flows

This milestone still does not widen the frozen public `/v0/*` surface or the bridge-domain contract.

## Milestone 47 Supported-Upstream Verification Notes

Milestone 47 advances `Phase I` with the first supported-upstream verification harness over the maintained non-fork Remnawave path.

- the harness lives in `crates/ns-testkit/examples/remnawave_supported_upstream_verification.rs`
- the Windows-first and Bash wrappers are `scripts/remnawave-supported-upstream-verify.ps1` and `scripts/remnawave-supported-upstream-verify.sh`
- the default machine-readable summary path is `target/northstar/remnawave-supported-upstream-summary.json`
- the maintained environment variables are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE`
  - optional: `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_REQUEST_TIMEOUT_MS`
  - optional: `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_SNAPSHOT_AGE_SECONDS`
  - optional: `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID`
  - optional: `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_EVENT_TYPE`
  - optional: `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH`

The supported-upstream harness proves:

- the current `HttpRemnawaveAdapter` can resolve a configured supported upstream environment
- the observed upstream version meets the current supported floor of `2.7.0+`
- the maintained bridge path can complete manifest bootstrap, device registration, token exchange, refresh manifest fetch, and verified webhook ingress over that adapter boundary
- operator-facing failures are explicit for missing environment, unsupported version, auth failure, timeout, response-shape drift, webhook-signature failure, stale snapshot state, and incompatible-contract conditions

The supported-upstream harness does **not** yet prove:

- full revoke or disable or entitlement-change propagation against a real upstream environment
- full reconciliation and retry behavior under partial upstream inconsistency
- deployment-grade remote/shared-store validation against a supported upstream environment
- every production webhook signing-format detail beyond the current configured bridge-side signature and timestamp gate

Milestone 47 therefore moves `Phase I` materially forward, but it does not by itself complete `Phase I`.

## Milestone 48 Supported-Upstream Lifecycle Verification Notes

Milestone 48 advances `Phase I` with the first real lifecycle and reconciliation lane over the maintained supported-upstream path.

- the lifecycle harness lives in `crates/ns-testkit/examples/remnawave_supported_upstream_lifecycle_verification.rs`
- the Windows-first and Bash wrappers are `scripts/remnawave-supported-upstream-lifecycle-verify.ps1` and `scripts/remnawave-supported-upstream-lifecycle-verify.sh`
- the default machine-readable summary path is `target/northstar/remnawave-supported-upstream-lifecycle-summary.json`
- the maintained required environment variables are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID`
- the maintained optional environment variables are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_LIFECYCLE`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_EVENT_TYPE`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_REQUEST_TIMEOUT_MS`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_SNAPSHOT_AGE_SECONDS`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_RECONCILE_LAG_SECONDS`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_WAIT_TIMEOUT_SECONDS`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_POLL_INTERVAL_MS`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH`

The lifecycle harness is intentionally operator-driven:

1. start with a supported upstream account that is currently `active`
2. let the harness complete the active bootstrap, device-register, token-exchange, and refresh-manifest pass on the maintained bridge path
3. while the harness is polling, disable or revoke or expire or limit that same upstream account in Remnawave
4. let the harness observe the authoritative lifecycle transition, replay a verified webhook delivery into the maintained bridge path, and then verify that new bootstrap, refresh, and token issuance all fail closed with the expected stable Bridge error code

The lifecycle harness proves:

- the maintained bridge path can start from a real supported upstream account in an active state
- a real operator-driven lifecycle transition can be observed through the maintained HTTP adapter
- verified webhook ingress rejects bad signatures and duplicate deliveries during the lifecycle pass
- bootstrap manifest fetch, refresh manifest fetch, and token exchange fail closed after the lifecycle transition on that same bridge runtime path
- operator-facing failures are explicit for missing environment, unsupported version, auth failure, timeout, response-shape drift, lifecycle drift, reconcile lag, stale snapshot state, replay-sensitive inconsistency, webhook-signature failure, and incompatible-contract conditions

The lifecycle harness still does **not** prove:

- deployment-grade remote/shared-store bridge reality against a supported upstream environment
- every production deployment detail of upstream webhook delivery beyond the current bridge-side signature and timestamp gate
- a Northstar-owned lifecycle mutation path; Remnawave remains the external lifecycle and entitlement authority

## Milestone 49 Supported-Upstream Deployment Reality Notes

Milestone 49 advances `Phase I` with the deployment-reality decision gate over the maintained supported-upstream path.

- the deployment-reality harness lives in `crates/ns-testkit/examples/remnawave_supported_upstream_deployment_reality_verification.rs`
- the Windows-first and Bash wrappers are `scripts/remnawave-supported-upstream-deployment-reality-verify.ps1` and `scripts/remnawave-supported-upstream-deployment-reality-verify.sh`
- the default machine-readable summary path is `target/northstar/remnawave-supported-upstream-deployment-reality-summary.json`
- the maintained required environment variables are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_INPUT_PATH`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_INPUT_PATH`
- the maintained optional environment variables are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_REQUEST_TIMEOUT_MS`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_MAX_SNAPSHOT_AGE_SECONDS`

The deployment-reality harness is intentionally a `Phase I` decision gate:

1. it loads milestone-47's supported-upstream summary and milestone-48's lifecycle summary as required inputs and fails closed if either one is missing, drifted, or unready
2. it resolves the configured supported upstream account again through the maintained `HttpRemnawaveAdapter`
3. it starts the maintained deployment-shaped bridge runtime over the shared-durable service-backed store path
4. it checks internal store health and shared-durable scope before exercising the public Bridge runtime
5. it runs manifest bootstrap, device register, token exchange, refresh-manifest, remote-store auth-mismatch, unauthorized-primary-no-failover, and shutdown checks and emits one fail-closed deployment-reality summary

The deployment-reality harness proves:

- the maintained deployment-shaped bridge runtime can sit over the shared-durable service-backed store path while talking to a supported upstream adapter
- the internal store-service health path remains authenticated and must report `SharedDurable`
- wrong remote-store auth fails closed instead of silently widening the deployment path
- unauthorized primary store endpoints do not fail over to secondary endpoints
- the deployment-reality summary stays explicitly control-plane only; it does **not** claim transport or datagram readiness

The deployment-reality harness still does **not** prove:

- that a real supported deployment has already passed this lane in the current repository history; milestone 49 adds the decision gate, but an operator still has to run it against a real environment
- WAN-grade or transport-grade readiness; the summary intentionally stops at control-plane issuance and deployment truth
- every remote/shared backend variant beyond the maintained shared-durable service-backed topology path

Milestone 49 therefore gives `Phase I` the last planned gate, but `Phase I` is only honestly complete after a real supported deployment actually passes that gate.

## Milestone 50 Supported-Upstream Phase I Signoff Notes

Milestone 50 advances `Phase I` with the operator-facing signoff lane that consumes milestones 47, 48, and 49 together.

- the signoff harness lives in `crates/ns-testkit/examples/remnawave_supported_upstream_phase_i_signoff.rs`
- the Windows-first and Bash wrappers are `scripts/remnawave-supported-upstream-phase-i-signoff.ps1` and `scripts/remnawave-supported-upstream-phase-i-signoff.sh`
- the default machine-readable summary path is `target/northstar/remnawave-supported-upstream-phase-i-signoff-summary.json`
- the maintained required environment variables for honest closure are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL`
- the maintained optional environment variables are:
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH`
  - `NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH`

The signoff wrapper runs the maintained chain in order:

1. milestone-47 supported-upstream verification
2. milestone-48 lifecycle and reconciliation verification
3. milestone-49 deployment-reality verification
4. milestone-50 Phase I signoff

The wrapper now deletes the expected summary artifact before each lane runs, so a non-ready lane cannot silently reuse a stale summary from an older invocation.

The signoff lane proves:

- the maintained supported-upstream chain can now produce one final operator-facing `Phase I` summary
- closure is only recommended when prior-lane evidence passes together and stays consistent on base URL, expected account identity, upstream version, and control-plane-only scope
- local missing-environment or missing-deployment-identity runs fail closed with explicit blockers instead of simulating completion

The signoff lane still does **not** prove:

- that this repository run exercised a real supported deployment if the required environment variables are absent
- transport or datagram readiness
- WAN-grade interoperability

Milestone 50 therefore adds the honest `Phase I` signoff call, but `Phase I` is still only complete after a real supported deployment actually passes the chain.

## Milestone 12 Datagram Notes

Milestone 12 does not change the non-fork bridge contract.
The first datagram slice stays entirely inside:

- `ns-session`
- `ns-carrier-h3`
- `ns-gateway-runtime`
- transport-facing tests and observability

Bridge implications are intentionally limited to "no change":

- no new `/v0/*` fields
- no store-schema widening for datagram state
- no Remnawave adapter contract widening
- no bridge-domain datagram policy surface

This keeps datagram startup transport-scoped and prevents bridge/control-plane drift while the first live UDP path is still being hardened.

## Domain Models For The Initial Bridge Path

These models are internal to the Bridge crates. They are intentionally narrower than raw Remnawave payloads.

### Bootstrap and auth context

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum BootstrapSubject {
    ShortUuid(String),
    BridgeAlias(String),
    SignedEnvelope(String),
}

#[derive(Debug, Clone)]
pub enum ManifestAuthContext {
    Bootstrap(BootstrapSubject),
    Refresh(RefreshCredentialRef),
}

#[derive(Debug, Clone)]
pub enum DeviceRegistrationAuth {
    BootstrapGrant(BootstrapGrantRef),
    Refresh(RefreshCredentialRef),
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct RefreshCredentialRef(pub String);

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BootstrapGrantRef(pub String);
```

Initial safety rule:

- `BootstrapSubject::ShortUuid` is the only required active bootstrap subject in v0.1
- raw `shortUuid` should be accepted only at `GET /v0/manifest`
- state-changing operations should use a short-lived Bridge-issued bootstrap grant, not the raw `shortUuid`

### Normalized account and policy state

```rust
#[derive(Debug, Clone)]
pub struct AccountSnapshot {
    pub account_id: String,
    pub bootstrap_subjects: Vec<BootstrapSubject>,
    pub lifecycle: AccountLifecycle,
    pub northstar_access: NorthstarAccess,
    pub metadata: Option<serde_json::Value>,
    pub observed_at_unix: i64,
    pub source_version: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AccountLifecycle {
    Active,
    Disabled,
    Revoked,
    Expired,
    Limited,
}

#[derive(Debug, Clone)]
pub struct NorthstarAccess {
    pub northstar_enabled: bool,
    pub policy_epoch: u64,
    pub device_limit: Option<u32>,
    pub allowed_core_versions: Vec<u16>,
    pub allowed_carrier_profiles: Vec<String>,
    pub allowed_capabilities: Vec<u16>,
    pub rollout_cohort: Option<String>,
    pub preferred_regions: Vec<String>,
}
```

### Device and refresh state

```rust
#[derive(Debug, Clone)]
pub struct DeviceRecord {
    pub device_id: String,
    pub account_id: String,
    pub status: DeviceStatus,
    pub platform: String,
    pub client_version: String,
    pub install_channel: Option<String>,
    pub device_name: Option<String>,
    pub hwid_claim_hash: Option<String>,
    pub first_seen_at_unix: i64,
    pub last_seen_at_unix: i64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DeviceStatus {
    Active,
    Revoked,
}

#[derive(Debug, Clone)]
pub struct RefreshCredentialRecord {
    pub credential_id: String,
    pub account_id: String,
    pub device_id: String,
    pub status: RefreshCredentialStatus,
    pub secret_hash: String,
    pub issued_at_unix: i64,
    pub expires_at_unix: i64,
    pub last_used_at_unix: Option<i64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RefreshCredentialStatus {
    Active,
    Revoked,
    Expired,
}
```

Recommended initial implementation choice:

- make refresh credentials opaque and device-scoped
- store only hashed secret material at rest
- do not expose internal refresh credential structure to gateways or Remnawave

This is safe because refresh credential encoding is Bridge-internal, not a frozen on-wire protocol field.

Milestone-5 implementation note:

- the repository now includes `InMemoryBridgeStore`, `FileBackedBridgeStore`, and `SqliteBridgeStore` in `ns-storage`
- the SQLite-backed store is the first shared durable coordination path for bridge replay markers, device records, refresh-credential records, webhook replay fingerprints, and bridge metadata
- the SQLite store is configured for WAL mode and bounded busy waiting so multiple bridge instances can coordinate through the same backing file
- all durable backends store digested lookup keys rather than plaintext refresh credentials
- `apps/ns-bridge` now defaults to the SQLite-backed store, while the file-backed and in-memory stores remain available for tests and isolated local runs
- this is still not the final remote or service-backed multi-node bridge-store architecture

Milestone-6 implementation note:

- `ns-storage` now exposes `BridgeStoreBackend`, `BridgeStoreDeploymentScope`, and `SharedBridgeStore` so bridge composition can swap concrete storage backends without widening the domain contract
- the backend boundary is designed for future service-backed durable stores while keeping current `InMemoryBridgeStore`, `FileBackedBridgeStore`, and `SqliteBridgeStore` implementations intact
- bootstrap grants are now stored and redeemed through that bridge-store contract rather than remaining an implicit in-memory bridge concern
- `ns-bridge-api` now exposes an initial `axum` service composition for `GET /v0/manifest`, `POST /v0/device/register`, `POST /v0/token/exchange`, `GET /.well-known/jwks.json`, and `POST /internal/remnawave/webhook`
- the initial bridge HTTP composition applies explicit body budgets of `16 KiB` for JSON endpoints and `64 KiB` for verified webhook bodies
- `apps/ns-bridge serve` now wires the fake adapter, shared bridge store, token JWKS, and webhook authenticator into that thin service boundary

Milestone-7 implementation note:

- `ns-storage` now includes `ServiceBackedBridgeStoreConfig`, `ServiceBackedBridgeStoreAdapter`, and `ServiceBackedBridgeStore` as the first semantic adapter seam for future remote or service-backed durable bridge coordination
- the current service-backed store path is intentionally fail-closed and reports backend unavailability instead of pretending a remote store exists when it does not
- `apps/ns-bridge` now builds an explicit bridge runtime/config object for public serve mode instead of calling a demo-only serve helper directly
- public serve mode now requires a `SharedDurable` bridge-store backend, so local-only backends remain limited to isolated runs and tests
- route-scoped HTTP body limits now keep JSON bridge endpoints on the tighter public ingress budget while webhook ingress keeps its larger verified-body budget

Milestone-8 implementation note:

- `ns-storage` now includes `HttpServiceBackedBridgeStoreAdapter` plus a semantic internal store-service router for real remote bridge-store coordination over HTTP without widening bridge-domain contracts
- service-backed bridge-store startup now performs a health check and only passes when the remote backend reports `SharedDurable`
- the fail-closed service-backed store stub remains available for tests and isolated fallback paths, but the public bridge app now uses the real HTTP-backed service adapter when `--store-backend service` is selected
- `apps/ns-bridge` now composes adapter, store, signers, manifest template, and webhook verification as explicit runtime dependencies so the same service boundary can host either the fake adapter or a future real Remnawave adapter
- public bridge-app integration tests now run against the composed runtime over a shared durable backend instead of only helper-built routers

### Manifest compile input and token mint input

```rust
#[derive(Debug, Clone)]
pub struct ManifestCompileInput {
    pub account: AccountSnapshot,
    pub device: Option<DeviceRecord>,
    pub context: BridgeManifestContext,
    pub carrier_profiles: Vec<CarrierProfile>,
    pub endpoints: Vec<GatewayEndpoint>,
    pub manifest_ttl: time::Duration,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BridgeManifestContext {
    pub device_policy: Option<DevicePolicy>,
    pub client_constraints: ClientConstraints,
    pub token_service: TokenService,
    pub refresh: Option<RefreshPolicy>,
    pub routing: RoutingPolicy,
    pub retry_policy: RetryPolicy,
    pub telemetry: TelemetryPolicy,
}

pub type CarrierProfile = ns_manifest::CarrierProfile;
pub type GatewayEndpoint = ns_manifest::GatewayEndpoint;

#[derive(Debug, Clone)]
pub struct SessionTokenMintRequest {
    pub account: AccountSnapshot,
    pub device: DeviceRecord,
    pub manifest_id: String,
    pub client_version: String,
    pub core_version: u16,
    pub carrier_profile_id: String,
    pub requested_capabilities: Vec<u16>,
}
```

## Adapter Boundary

The adapter trait in the Bridge spec should be used directly as the initial boundary:

```rust
#[async_trait::async_trait]
pub trait RemnawaveAdapter {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError>;

    async fn fetch_account_snapshot(
        &self,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError>;

    async fn fetch_user_metadata(
        &self,
        account_id: &str,
    ) -> Result<Option<serde_json::Value>, AdapterError>;

    async fn upsert_user_metadata(
        &self,
        account_id: &str,
        patch: serde_json::Value,
    ) -> Result<(), AdapterError>;

    async fn ingest_verified_webhook(
        &self,
        payload: VerifiedWebhookPayload,
    ) -> Result<AdapterWebhookEffect, AdapterError>;
}
```

Required supporting types:

```rust
#[derive(Debug, Clone)]
pub struct VerifiedWebhookPayload {
    pub event_id: String,
    pub event_type: String,
    pub account_id: Option<String>,
    pub occurred_at_unix: i64,
    pub payload: serde_json::Value,
}

#[derive(Debug, Clone)]
pub enum AdapterWebhookEffect {
    Noop,
    InvalidateAccount { account_id: String },
    ReconcileAccount { account_id: String, reason: String },
    ReconcileAll { reason: String },
    Snapshot(AccountSnapshot),
}

#[derive(Debug, thiserror::Error)]
pub enum AdapterError {
    #[error("not found")]
    NotFound,
    #[error("unauthorized")]
    Unauthorized,
    #[error("rate limited")]
    RateLimited,
    #[error("schema drift")]
    SchemaDrift,
    #[error("unavailable")]
    Unavailable,
    #[error("timeout")]
    Timeout,
    #[error("invalid data")]
    InvalidData,
    #[error("conflict")]
    Conflict,
}
```

Adapter rules:

- normalize and validate upstream data before returning it
- classify schema drift explicitly and fail closed
- own retry and backoff for Remnawave API calls
- never leak raw upstream JSON past the adapter boundary except as optional metadata payloads already accepted by the domain model

## Mock And Fake Adapter Shape

The first fake adapter should live in `ns-testkit` or `ns-remnawave-adapter/tests` and implement the real trait.

```rust
pub struct FakeRemnawaveAdapter {
    pub accounts_by_subject: std::collections::HashMap<BootstrapSubject, AccountSnapshot>,
    pub accounts_by_id: std::collections::HashMap<String, AccountSnapshot>,
    pub metadata_by_account: std::collections::HashMap<String, serde_json::Value>,
    pub next_error: Option<AdapterError>,
    pub webhook_effects: std::collections::VecDeque<AdapterWebhookEffect>,
    pub calls: Vec<FakeAdapterCall>,
}

pub enum FakeAdapterCall {
    ResolveBootstrap { subject: BootstrapSubject },
    FetchAccount { account_id: String },
    FetchMetadata { account_id: String },
    UpsertMetadata { account_id: String },
    IngestWebhook { event_type: String, account_id: Option<String> },
}
```

The fake must support:

- happy-path account resolution
- disabled, revoked, expired, and limited account states
- missing account
- schema-drift failure
- rate-limited and upstream-unavailable failure injection
- webhook reorder and duplicate delivery tests

The fake should operate on normalized `AccountSnapshot` values, not raw Remnawave fixture blobs. Raw fixture coverage belongs in adapter normalization tests.

## Initial Flow Skeleton

### Flow 1: first import via Remnawave subscription page

1. User lands on a Bridge-controlled import URL from the Remnawave subscription UX.
2. Client calls `GET /v0/manifest?subscription_token=<bootstrap-subject>`.
3. `ns-bridge-api` parses bootstrap mode and hashes the subject for logs.
4. `ns-remnawave-adapter` resolves the subject to `AccountSnapshot`.
5. `ns-bridge-domain` enforces lifecycle and Northstar access policy.
6. `ns-bridge-domain` compiles and signs a manifest from normalized account state, bridge-owned inventory, and frozen-schema carrier profiles.
7. Bridge returns the signed manifest with `ETag`.
8. Client proceeds to `POST /v0/device/register` using a short-lived Bridge bootstrap grant.
9. Bridge registers or reuses the device binding, enforces device limit, and returns a device-scoped refresh credential.
10. Client calls `POST /v0/token/exchange` with the refresh credential and requested runtime parameters.
11. Bridge mints a short-lived EdDSA session token for gateway use.

### Flow 2: steady-state reconnect

1. Client calls `GET /v0/manifest` with `Authorization: Bearer <refresh-credential>`.
2. Bridge validates the refresh credential and resolves the current device and account state from Bridge-owned durable state plus normalized control-plane data.
3. Bridge returns `304 Not Modified` if the manifest hash is unchanged, otherwise a newly signed manifest.
4. Client calls `POST /v0/token/exchange`.
5. Bridge validates:
   - refresh credential state
   - refresh credential to manifest binding
   - account lifecycle state
   - device state
   - device-limit and revocation policy
   - requested core version
   - requested carrier profile
   - requested capability subset
   - current policy epoch
6. Bridge returns a short-lived session token plus current `policy_epoch`.

### Flow 3: revoke or disable in Remnawave

1. Remnawave webhook arrives or reconcile detects new account state.
2. Adapter verifies webhook authenticity before normalization.
3. Domain layer marks the account or device as denied for new issuance.
4. Future `GET /v0/manifest` and `POST /v0/token/exchange` fail with stable Bridge error codes.
5. Existing session tokens expire naturally on their short TTL.

### Flow 4: webhook and reconcile

1. Public webhook receiver verifies signature and timestamp freshness.
2. Payload is deduplicated with a fingerprint built from body hash, event, timestamp, and scope, then turned into `VerifiedWebhookPayload`.
3. In the milestone-5 baseline, that dedupe fingerprint survives restart and can be rejected across bridge instances that share the SQLite-backed bridge store.
4. Adapter converts it into `AdapterWebhookEffect`.
5. Domain layer invalidates cached manifest state or triggers reconciliation.
6. A periodic reconcile path still exists as a safety net for missed or reordered events.

## HTTP Status Guidance

Use the Bridge spec guidance directly:

| Situation | Recommended status |
|---|---:|
| malformed request | 400 |
| invalid or expired credential | 401 |
| account exists but is not allowed | 403 |
| bootstrap subject unknown | 404 |
| device conflict or device limit exceeded | 409 |
| bootstrap one-time token already spent | 410 |
| client version too old | 426 |
| rate limited | 429 |
| upstream unavailable | 503 |

Implementation rule:

- stable `error.code` is the compatibility surface
- HTTP status is important, but client logic should key primarily on stable Bridge error code

## Security Gates For The Initial Bridge Path

- verify webhook signatures and timestamp freshness before parsing business content
- reject duplicate verified webhook deliveries before adapter-side reconciliation
- keep replay/dedupe state durable in the selected bridge-store backend, and reject duplicate verified webhook deliveries across bridge instances when they share the same SQLite store
- require a `SharedDurable` backend for public bridge service mode so replay and device-policy guarantees are not silently downgraded by local-only storage choices
- redact raw bootstrap subject, raw refresh credential, and raw HWID-like material from logs
- separate token signing keys from manifest signing keys
- reject bootstrap-only credentials at `POST /v0/token/exchange`
- fail closed on adapter schema drift
- keep bootstrap and token issuance rate limits separate
- keep refresh credentials device-scoped
- audit device registration and token issuance
- keep Bridge stale-read policy stricter for token exchange than for manifest refresh

## What Must Stay Deferred Instead Of Guessed

### Exact bootstrap grant wire format

The docs allow plain `shortUuid` bootstrap for v0.1 and mention future signed bootstrap envelopes, but they do not freeze the final serialized shape of the Bridge-issued bootstrap grant used after the initial manifest fetch.

Do not hard-code this prematurely.

Safe implementation posture:

- keep `BootstrapGrantRef` as an internal Bridge concept
- accept raw `shortUuid` only at manifest bootstrap
- require a short-lived Bridge grant for device registration
- confirm where that grant lives in the manifest or auth instructions before freezing a client-visible field

### Signed bootstrap envelope format

Deferred.
The Bridge spec lists it as a future-safe path, but v0.1 only requires support for at least one bootstrap subject form.
Do not invent an envelope schema now.

### Refresh credential self-describing format

Deferred.
Use opaque random credentials initially.
If the project later wants signed or self-describing refresh credentials, record that as an ADR and keep it behind the Bridge boundary.

### Remnawave metadata write-back policy

Deferred.
`upsert_user_metadata` exists in the adapter contract, but the exact write-back strategy is not required for the initial non-fork baseline.
Do not make Bridge correctness depend on Remnawave metadata round-trips.

### Bridge admin and operator API surface

Deferred.
The public client-facing `/v0/*` API is in scope.
Operator and admin surfaces should remain separate and are not required to bootstrap the first end-to-end path.

### Shared remote bridge-store architecture beyond SQLite

Deferred.
Milestone 5 intentionally stopped at a shared SQLite-backed store so replay, device, and refresh state could be coordinated across bridge instances without pulling database concerns into gateway admission or carrier code.
Milestone 6 adds the backend-wrapped `SharedBridgeStore` composition seam so future multi-host or service-backed bridge coordination can stay inside `ns-storage` and bridge composition code rather than leaking into session-core or transport crates.
Milestone 7 adds the first semantic service-backed store interface and fail-closed stub so that future remote coordination can be implemented without changing bridge-domain contracts.
Milestone 11 extends that service-backed path with ordered authenticated endpoint failover for transport and availability failures while keeping unauthorized outcomes fail-closed.

## Immediate Implementation Order

1. Add public API models and error envelope types in `ns-bridge-api`.
2. Add normalized domain models and policy guards in `ns-bridge-domain`.
3. Add the `RemnawaveAdapter` trait and normalization error types in `ns-remnawave-adapter`.
4. Build the fake adapter and Bridge-path integration tests first.
5. Implement manifest bootstrap fetch with strict redaction and typed errors.
6. Implement device registration with Bridge-owned device limits and opaque refresh credentials.
7. Implement token exchange and JWT minting against the frozen token profile.
8. Add webhook verification, durable local dedupe, and reconcile invalidation.

## Minimum Test Matrix

- bootstrap subject resolves to active account
- bootstrap subject unknown returns `INVALID_BOOTSTRAP_SUBJECT`
- disabled, revoked, expired, and limited accounts map to stable error codes
- device limit reached returns `DEVICE_LIMIT_REACHED`
- revoked device cannot mint a new session token
- refresh credential expiry and revocation are enforced
- duplicate verified webhook delivery is rejected as a no-op
- requested carrier profile mismatch returns `PROFILE_NOT_ALLOWED`
- requested core version mismatch returns `CORE_VERSION_NOT_ALLOWED`
- webhook signature failure is rejected before normalization
- adapter schema drift fails closed
- manifest refresh returns `304` when unchanged
- token exchange never accepts raw bootstrap subject

## Summary

The initial Bridge path should be built as:

- a stable `/v0/*` public API in `ns-bridge-api`
- a typed normalization and policy layer in `ns-bridge-domain`
- an isolated Remnawave adapter in `ns-remnawave-adapter`
- a fake adapter and fixture-driven tests before real upstream integration
- a bridge-owned durable state layer that can start with SQLite-backed coordination without requiring a Remnawave fork

The Bridge remains the Northstar control-plane boundary.
Remnawave remains the external lifecycle and entitlement source.
Gateways see only Bridge-issued session authority.
