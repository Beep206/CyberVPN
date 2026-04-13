
# Northstar Remnawave Bridge Spec v0.1

**Status:** Draft v0.1  
**Codename:** Northstar  
**Document type:** control-plane bridge, adapter, and operational integration specification  
**Audience:** protocol architects, Rust backend engineers, client engineers, security reviewers, SREs, AI coding agents  
**Companion documents:**  
- `Blueprint v0 — Adaptive Proxy/VPN Protocol Suite (Northstar)`  
- `Northstar Spec v0.1 — Wire Format Freeze Candidate`  

---

## 1. Why this document exists

The Blueprint defines **what Northstar is**.  
The Wire Format Freeze Candidate defines **what the on-wire contract looks like**.

This document defines the missing middle layer:

- how Northstar uses **Remnawave as the external control plane**
- how the **Bridge** translates Remnawave state into Northstar-native manifests and tokens
- how client bootstrap works without forking the panel
- how device binding, subscription imports, and policy updates behave
- which parts are **authoritative in Remnawave** and which parts stay **Bridge-owned**
- how to make the integration operationally safe, versioned, observable, and future-proof

This is the source of truth for the **non-fork Remnawave integration path**.

---

## 2. Executive summary

Northstar v0 uses **Remnawave for account and subscription authority**, while keeping the Northstar data plane entirely separate.

The architecture is:

```text
User / Client
   |
   | import / manifest / refresh / session bootstrap
   v
Northstar Bridge  ---------------------> Northstar Gateway fleet
   |
   | API + webhooks + optional metadata sync
   v
Remnawave Panel / Subscription Page
```

The central rule is simple:

- **Remnawave remains the authority for user lifecycle and subscription entitlement**
- **The Bridge becomes the authority for Northstar manifests, device bindings, refresh credentials, and session tokens**
- **Northstar Gateways remain fully outside Xray-core and do not require a panel fork**

This split is what makes the chosen path practical.

---

## 3. Document scope

### 3.1 In scope

This document specifies:

1. the Bridge architecture and trust boundaries
2. compatibility expectations with supported Remnawave versions
3. bootstrap/import flows from subscription link to Northstar client
4. public Bridge API behavior layered on top of the frozen `/v0/*` contract
5. the Remnawave-facing adapter boundary
6. webhook ingestion and reconciliation behavior
7. mapping of Remnawave users/subscriptions/metadata into Northstar manifests
8. device and HWID policy reconciliation
9. manifest compilation inputs and policy precedence
10. operational concerns: caching, audit logs, metrics, rollout, failure modes
11. a large deferred backlog so important ideas are not lost

### 3.2 Out of scope

This document does **not** define:

- Northstar session frames or control-stream encoding
- gateway transport implementation details beyond what the Bridge must know
- GUI design of the client
- a full operator/admin API for the Bridge
- an exact database migration toolchain
- a final RFC-style specification for third-party Bridge implementations
- a fork of the Remnawave panel or node stack
- a requirement to integrate Northstar into Xray-core

---

## 4. Relationship to the other Northstar documents

### 4.1 Blueprint v0

Blueprint v0 established:

- Bridge exists as an external service
- client receives a signed manifest
- client exchanges a refresh/bootstrap credential for a short-lived session token
- Bridge integrates with the control plane via polling/webhooks/API adapter

This Bridge spec turns that into concrete integration rules.

### 4.2 Wire Format Freeze Candidate v0.1

The freeze candidate already stabilizes the **public Bridge API names**:

- `POST /v0/device/register`
- `GET /v0/manifest`
- `POST /v0/token/exchange`
- `POST /v0/network/report`
- `GET /.well-known/jwks.json`

This document **does not rename those endpoints**.  
Instead, it adds the Remnawave-facing semantics, auth modes, state machine, and adapter obligations around them.

---

## 5. External assumptions validated against Remnawave

The Bridge design in this document assumes current Remnawave capabilities that are visible in official documentation and changelogs.

### 5.1 Assumptions we explicitly rely on

1. Remnawave is built around the Xray ecosystem and routes client subscription output by detected client type and template family.
2. Remnawave supports multiple subscription output families such as Mihomo, Base64, Xray-json, and Sing-box.
3. The raw subscription endpoint now exposes a typed `resolvedProxyConfigs` structure rather than legacy flat `rawHosts`.
4. Remnawave provides signed webhooks with `X-Remnawave-Signature` and `X-Remnawave-Timestamp`.
5. Remnawave supports a Subscription Page / Subpage Builder, dynamic app configuration, and featured apps.
6. Remnawave supports HWID-based device limiting for compatible clients during subscription fetches.
7. Remnawave exposes metadata endpoints for users and nodes in recent versions.

### 5.2 Important implication

Northstar Bridge integration is **not** a native transport plugin for Remnawave nodes.  
It is a **control-plane integration** that reuses:

- account lifecycle
- user status and subscription state
- subscription import UX
- optional metadata
- optional webhook signals

but not the Xray-core data plane.

### 5.3 Version compatibility floor

This spec recommends the following minimum versions:

- **Remnawave Panel 2.7.0+**: strongly recommended; introduces typed `resolvedProxyConfigs`, metadata endpoints, and `POST /api/users/resolve`
- **Remnawave Panel 2.7.4+**: preferred; adds `additionalExtendedClientsRegex`, useful for future compatibility experiments
- **Remnawave Panel 2.7.5+**: optional improvement if operator wants the newer HWID response headers
- **Remnawave Subscription Page 7.0.0+**: recommended for dynamic app config loading and API-token-based page integration

Older versions may still be usable with custom adapter logic, but they are outside the recommended baseline for v0.1.

---

## 6. Design goals

The Bridge MUST optimize for the following goals.

### 6.1 Primary goals

1. **No panel fork**
2. **Stable Northstar public API**
3. **Strict isolation between control plane and data plane**
4. **Fast revocation**
5. **Safe policy rollout**
6. **Deterministic manifest generation**
7. **Device-aware imports**
8. **Support for gradual improvement without breaking the client**

### 6.2 Secondary goals

1. Minimal operator friction
2. Easy auditability
3. Easy replay-safe automation
4. Good observability for blocked/failed/bootstrap flows
5. Low coupling to Remnawave internal schema churn

### 6.3 Anti-goals

The Bridge MUST NOT become:

- a traffic proxy
- an opaque policy engine with undocumented behavior
- a permanent stateful dependency in the data path
- a clone of Remnawave UI or billing logic
- a pseudo-Xray node adapter that pretends Rust gateways are Remnawave nodes

---

## 7. Terminology

### 7.1 Control-plane terms

- **Remnawave User**: the authoritative account/subscription record in Remnawave
- **Short UUID**: the user-facing subscription identifier used in subscription URLs
- **Subpage**: Remnawave’s subscription page for end-user imports
- **External Squad / Routing Rules / Templates**: Remnawave client-delivery mechanics outside Northstar’s public API

### 7.2 Northstar terms

- **Bridge**: public manifest/token service plus private Remnawave adapter
- **Gateway**: Rust Northstar data-plane server
- **Manifest**: signed client control document
- **Bootstrap credential**: bridge-only bootstrap secret derived from initial import
- **Refresh credential**: bridge-only credential used to mint short-lived session tokens
- **Session token**: short-lived gateway-facing credential used in the Northstar handshake
- **Policy epoch**: monotonically increasing policy generation number
- **Inventory provider**: source of gateway/endpoints/carrier-profile availability

### 7.3 Authority terms

- **Authoritative**: the system of record for a given piece of state
- **Derived**: computed or cached from authoritative data
- **Advisory**: useful hint, but not binding

---

## 8. Canonical authority model

This section is one of the most important in the document.

### 8.1 Authority split

| Domain | Authority | Notes |
|---|---|---|
| User creation / deletion / disable / revoke / expire | Remnawave | Canonical |
| Subscription identifier (`shortUuid`) | Remnawave | Canonical |
| User plan / traffic-lifecycle / subscription status | Remnawave | Canonical input into Bridge policy |
| Northstar gateway inventory | Bridge | Canonical; not stored as Remnawave Xray nodes |
| Carrier profiles | Bridge | Canonical |
| Manifest compilation | Bridge | Canonical |
| Device bindings for Northstar client | Bridge | Canonical |
| Refresh credentials | Bridge | Canonical |
| Session tokens | Bridge | Canonical |
| Gateway allow/deny checks | Bridge-issued token + Gateway local policy | Canonical at session start |
| Rollout cohorts / Northstar feature flags | Bridge, optionally enriched by Remnawave metadata | Bridge wins |
| User-facing import/discovery UX | Remnawave Subpage + Bridge import links | Shared responsibility |

### 8.2 Why this split is necessary

If the Bridge tried to use Remnawave as the canonical authority for every Northstar-specific field, the integration would become fragile and would require panel-native concepts that do not exist today.

If the Bridge ignored Remnawave lifecycle state, revocation and subscription management would diverge.

Therefore:

- **Remnawave is the identity and entitlement source**
- **Bridge is the Northstar runtime policy source**

### 8.3 Consequence for operators

Operators must accept that:

- disabling or revoking a user in Remnawave MUST disable Northstar access
- changing Northstar gateway inventory in the Bridge MUST NOT require panel changes
- a user can exist in Remnawave without having a Northstar-compatible manifest if the operator disables Northstar for that user or cohort

---

## 9. High-level architecture

```text
                   ┌────────────────────────────┐
                   │        Remnawave           │
                   │ Panel + Subscriptions +    │
                   │ Webhooks + Metadata        │
                   └──────────────┬─────────────┘
                                  │
                    API polling   │   signed webhooks
                                  │
                                  v
                   ┌────────────────────────────┐
                   │    Northstar Bridge        │
                   │                            │
                   │  - Remnawave Adapter       │
                   │  - Webhook Receiver        │
                   │  - Reconciler              │
                   │  - Manifest Compiler       │
                   │  - Device Registry         │
                   │  - Token Issuer            │
                   │  - Inventory Provider      │
                   │  - Public /v0 API          │
                   └──────────────┬─────────────┘
                                  │
                   manifest       │ session token
                   refresh        │
                   bootstrap       │
                                  v
                   ┌────────────────────────────┐
                   │     Northstar Client       │
                   └──────────────┬─────────────┘
                                  │
                                  │ Northstar session
                                  v
                   ┌────────────────────────────┐
                   │     Northstar Gateway      │
                   └────────────────────────────┘
```

### 9.1 Hard rule

The Bridge MUST NOT sit in the user data path.  
All data-plane traffic goes directly between client and gateway after bootstrap.

---

## 10. Supported Bridge deployment modes

### 10.1 Mode A — single-tenant operator deployment

The most practical v0.1 mode.

Characteristics:

- one Remnawave panel
- one Bridge cluster
- one Northstar gateway fleet
- one issuer namespace
- one manifest/public base URL

### 10.2 Mode B — multi-region Bridge for one operator

Supported if the Bridge uses:

- shared database or replicated metadata store
- shared signing key set or coordinated rotation
- region-local manifest caches
- stateless public API nodes

### 10.3 Mode C — multi-tenant Bridge

Explicitly deferred for production.  
Designing v0.1 so multi-tenancy is impossible later is a mistake, but implementing true multi-tenant isolation now is too much.

---

## 11. Bridge component breakdown

### 11.1 Public API service

Responsible for:

- `GET /v0/manifest`
- `POST /v0/device/register`
- `POST /v0/token/exchange`
- `POST /v0/network/report`
- `GET /.well-known/jwks.json`

### 11.2 Remnawave adapter

Responsible for:

- calling Remnawave API
- validating and normalizing Remnawave responses
- resolving bootstrap identifiers into account snapshots
- syncing user metadata if enabled

### 11.3 Webhook receiver

Responsible for:

- receiving signed Remnawave webhooks
- verifying signature
- deduplicating events
- invalidating cache / scheduling reconciliation

### 11.4 Reconciler

Responsible for:

- cold-start backfill
- eventual consistency repair
- periodic refresh of important records
- catching missed or reordered webhook events

### 11.5 Manifest compiler

Responsible for:

- selecting endpoints
- selecting carrier profiles
- merging policy layers
- producing manifest JSON
- signing the manifest
- computing `manifest_id`

### 11.6 Device registry

Responsible for:

- device records
- device status
- device limits for Northstar mode
- binding bootstrap credentials to device-aware refresh credentials

### 11.7 Token issuer

Responsible for:

- refresh-credential validation
- session-token minting
- revocation epoch checks
- key rotation

### 11.8 Inventory provider

Responsible for:

- Northstar gateway inventory
- health-based endpoint filtering
- region/provider/cohort filtering
- carrier-profile availability

---

## 12. Compatibility model with Remnawave

### 12.1 Minimal compatibility set for v0.1

To support the integration described here, the operator deployment SHOULD have:

1. API token access for the Bridge
2. access to subscription information by short UUID
3. access to user details or user resolution
4. optional webhook configuration
5. optional user metadata support
6. optional Subpage Builder configuration to expose Northstar install/import actions

### 12.2 Recommended compatibility set

Recommended extras:

- webhook ingestion enabled
- user metadata endpoints enabled and used
- Subscription Page 7.x dynamic app config
- clear install pages for each Northstar client platform
- Remnawave 2.7.4+ if future client detection adjustments are needed

### 12.3 Graceful degradation

If some Remnawave feature is unavailable, the Bridge SHOULD degrade in this order:

1. **webhooks missing** → rely on polling + reconciliation
2. **metadata unavailable** → keep all Northstar-only overrides in Bridge DB
3. **Subpage Builder unavailable** → use standalone import page / manual manifest URL
4. **typed raw subscription unavailable** → avoid host-derived hints; rely on Bridge inventory only

---

## 13. Remnawave data sources used by the Bridge

The Bridge MUST distinguish **required** and **optional** Remnawave sources.

### 13.1 Required API capabilities

At minimum, the Bridge needs a way to:

1. resolve a user/subscription from a bootstrap identifier (`shortUuid` or equivalent)
2. fetch enough lifecycle data to know whether the account is allowed
3. know when relevant user state changes

### 13.2 Strongly recommended API capabilities

Recommended API capabilities:

- `GET /api/subscriptions/by-short-uuid/{shortUuid}/raw`
- `POST /api/users/resolve`
- user lookup by short UUID, UUID, username, or equivalent
- metadata endpoints for users
- optional metadata endpoints for nodes

### 13.3 Required webhook capabilities for push-first mode

Recommended events to ingest:

- `user.created`
- `user.modified`
- `user.deleted`
- `user.revoked`
- `user.disabled`
- `user.enabled`
- `user.limited`
- `user.expired`
- `user.traffic_reset`
- `user_hwid_devices.added`
- `user_hwid_devices.deleted`
- `service.subpage_config_changed`

### 13.4 Optional webhook capabilities

Optional events for analytics/ops only:

- `node.connection_lost`
- `node.connection_restored`
- `node.traffic_notify`
- `torrent_blocker.report`
- `errors.bandwidth_usage_threshold_reached_max_notifications`

---

## 14. Bridge operating modes relative to Remnawave

### 14.1 Polling-only mode

Use when:

- operator cannot expose webhooks
- initial deployment simplicity matters
- low write volume and slower propagation are acceptable

Trade-offs:

- slower revocation propagation
- more API pressure
- more cache staleness

### 14.2 Push-first mode

Recommended mode.

Behavior:

- webhooks trigger cache invalidation and reconciliation
- authoritative API pull confirms state after each important event
- polling still runs as a safety net

### 14.3 Mirror-plus-override mode

Optional advanced mode.

Behavior:

- Remnawave supplies lifecycle authority
- Bridge stores extra Northstar-only per-user policy and device data
- selected Bridge-derived hints may optionally be written back into Remnawave metadata for visibility

This is the most useful long-term mode.

---

## 15. Public bootstrap and steady-state flows

This section defines the canonical client lifecycle.

### 15.1 Flow A — first import from Remnawave subscription page

1. User opens Remnawave subscription page using the standard subscription URL.
2. Subscription page shows Northstar as one of the supported apps or featured apps.
3. Northstar import action opens one of:
   - a deep link: `northstar://import?...`
   - a universal link hosted by the Bridge
   - a normal HTTPS install/import page hosted by the Bridge
4. Bridge-facing import URL carries a bootstrap input, usually derived from the Remnawave `shortUuid`.
5. Client fetches `GET /v0/manifest?subscription_token=<bootstrap>`
6. Bridge resolves the bootstrap subject against Remnawave, validates account status, compiles and signs the manifest
7. Manifest may include a bootstrap credential or bridge auth instructions
8. Client registers device if required
9. Client obtains refresh credential
10. Client exchanges refresh credential for short-lived session token
11. Client starts a Northstar session to a selected gateway

### 15.2 Flow B — steady-state reconnect

1. Client already has:
   - last known-good manifest
   - refresh credential
   - stable `device_id`
2. Client refreshes manifest via `GET /v0/manifest` with `Authorization: Bearer <refresh>`
3. Bridge validates refresh credential and returns either:
   - `304 Not Modified`, or
   - a new signed manifest
4. Client requests session token via `/v0/token/exchange`
5. Client connects to gateway

### 15.3 Flow C — user revoked in Remnawave

1. Remnawave emits `user.revoked` or equivalent event, or Bridge detects revoked state on reconcile
2. Bridge increments policy epoch and marks account disabled
3. Future manifest fetch and token exchange requests fail
4. Existing short-lived session tokens age out quickly
5. Optional gateway revocation cache invalidation may accelerate denial

### 15.4 Flow D — device limit reached

1. Device register or refresh exchange encounters binding/device policy failure
2. Bridge returns a structured error
3. Client shows a meaningful message
4. If operator wants user self-service later, Bridge may expose device management UI or redirect to operator support flow

---

## 16. Bootstrap credential model

### 16.1 Why this exists

Northstar import must start from a Remnawave user subscription link without requiring a panel fork.

The bootstrap model solves that.

### 16.2 Allowed bootstrap subject formats

The Bridge MUST support at least one bootstrap subject format.

Recommended formats:

1. **Plain `shortUuid`** (MVP compatibility mode)
2. **Bridge-signed bootstrap envelope** (preferred later)
3. **Bridge import alias** that resolves to one of the above

### 16.3 Plain `shortUuid` support

For v0.1, plain `shortUuid` support is allowed because:

- it matches the operator’s existing user import experience
- it avoids requiring a new minting service before the Bridge exists
- it is no worse than existing subscription URL exposure

However:

- the Bridge MUST treat plain `shortUuid` as bootstrap-only
- the Bridge MUST NOT log raw `shortUuid` values in plaintext at info level
- the Bridge SHOULD hash/redact bootstrap identifiers in logs and metrics
- the Bridge SHOULD migrate to signed bootstrap envelopes later

### 16.4 Bridge-signed bootstrap envelope

Deferred-but-recommended future format:

```json
{
  "typ": "northstar-bootstrap",
  "sub": "rw:shortuuid:abc123",
  "aud": "northstar-bridge",
  "exp": "2026-04-01T14:00:00Z",
  "nonce": "..."
}
```

Advantages:

- hides raw `shortUuid` outside the first trusted server hop
- allows short expiry
- allows one-time-use semantics
- supports replay controls and install-channel pinning

### 16.5 Bootstrap TTL guidance

Recommended bootstrap TTL:

- plain `shortUuid`: no explicit TTL beyond Remnawave subscription lifecycle
- bridge-signed bootstrap envelope: 5–30 minutes
- embedded one-time bootstrap credential inside initial manifest: 1–10 minutes

---

## 17. Auth context for public Bridge endpoints

The freeze-candidate public API intentionally stayed minimal.  
This section adds the auth context needed for a working Bridge.

### 17.1 `GET /v0/manifest`

Supported auth modes:

1. **Bootstrap mode**
   - query parameter: `subscription_token=<bootstrap subject>`
2. **Steady-state mode**
   - header: `Authorization: Bearer <refresh credential>`

Rules:

- exactly one auth mode SHOULD be supplied
- if both are supplied, Bridge SHOULD reject unless an operator policy explicitly allows precedence
- bootstrap mode MUST NOT be used as a long-term refresh mechanism
- Bridge MAY return a bootstrap credential inside the manifest for the first import

### 17.2 `POST /v0/device/register`

Required auth context:

- `Authorization: Bearer <bootstrap credential or refresh credential>`

Body still follows the frozen schema from the public API document.

Purpose by mode:

- bootstrap credential → create first device binding and mint device-bound refresh credential
- refresh credential → update device metadata or rotate device-bound refresh credential

### 17.3 `POST /v0/token/exchange`

Auth material:

- body field `refresh_credential` as already frozen in the public API document

The Bridge MUST reject:

- bootstrap-only credentials
- expired refresh credentials
- refresh credentials bound to another device if device binding is required
- incompatible carrier profile requests
- requests for unsupported core versions

### 17.4 `POST /v0/network/report`

Auth options:

- low-sensitivity mode: unauthenticated but rate-limited and sampled
- authenticated mode: `Authorization: Bearer <refresh credential>`

v0.1 SHOULD prefer authenticated mode when feasible.

### 17.5 `GET /.well-known/jwks.json`

Publicly accessible.  
No auth required.

---

## 18. Device identity and HWID reconciliation

This is a critical design area.

### 18.1 Fundamental mismatch to understand

Remnawave HWID enforcement works when a compatible client fetches subscription content directly from Remnawave while sending headers such as `x-hwid`.

In Northstar mode, the custom client usually fetches the manifest from the **Bridge**, not directly from Remnawave.

Therefore:

- Remnawave’s built-in HWID enforcement does **not automatically become the Northstar device limit**
- the Bridge MUST implement its own device binding and device limit logic
- any “HWID compatibility” in Northstar mode is **Bridge-enforced, not panel-enforced**

### 18.2 Northstar device identity requirements

Northstar client MUST generate a stable `device_id` that is:

- random
- opaque
- stable across normal restarts
- not derived from raw OS serial numbers
- rotatable by explicit device reset flow

### 18.3 Optional HWID claim

Northstar client MAY also generate an optional `hwid_claim` for operator policy purposes.

If implemented, it MUST be:

- privacy-reviewed
- normalized
- ideally salted/hashed client-side or Bridge-side
- never treated as the sole stable identity unless operator explicitly chooses this mode

### 18.4 Bridge device policy states

A device record MAY be in one of:

- `pending`
- `active`
- `revoked`
- `soft_blocked`
- `hard_blocked`
- `evicted`

### 18.5 Recommended device policy behavior

Default v0.1 behavior:

- one stable `device_id`
- Bridge-enforced max devices per account
- optional device metadata:
  - platform
  - client version
  - install channel
  - device name
  - hwid claim hash
  - last seen
  - first seen
  - latest manifest id
  - latest policy epoch

### 18.6 Remnawave HWID as advisory input

If Remnawave HWID data is available through user-facing operations or support workflows, the Bridge MAY use it as an advisory signal.

It MUST NOT assume:

- Remnawave device list equals Bridge device list
- Remnawave HWID deletion implies automatic Bridge device deletion
- missing Remnawave HWID support means Northstar cannot enforce device limits

### 18.7 UX consistency recommendation

If the operator wants consistent user messaging between Remnawave-compatible apps and Northstar client, the Bridge SHOULD use similar reason codes:

- `HWID_NOT_SUPPORTED`
- `DEVICE_LIMIT_REACHED`
- `DEVICE_REVOKED`
- `DEVICE_BINDING_REQUIRED`

but MUST clearly treat them as Bridge policy outcomes.

---

## 19. Remnawave-to-Northstar mapping model

### 19.1 Why mapping must be explicit

Remnawave’s models are built for Xray-oriented subscriptions and multiple template families.  
Northstar’s manifest model is built for a custom client and custom gateway.

The Bridge MUST therefore perform an explicit domain mapping instead of pretending the schemas are identical.

### 19.2 Primary mapping table

| Remnawave source | Northstar target | Status | Notes |
|---|---|---|---|
| User UUID | `account_id` | required | canonical stable account reference |
| `shortUuid` | bootstrap subject | required | used only for import/bootstrap |
| User status / revoked / expired / disabled / limited | account entitlement state | required | canonical allow/deny input |
| Traffic strategy / reset model | usage-policy hint | optional in v0.1 | Bridge may surface informationally |
| User metadata | per-account Northstar override bag | optional but recommended | stored under a namespaced key |
| Typed `resolvedProxyConfigs` | advisory host labels / route hints | optional | do not treat as Northstar endpoint inventory |
| Subscription page configuration | app-discovery UX | optional but recommended | used to expose Northstar client |
| HWID feature and events | advisory device signals | optional | Bridge still owns Northstar device limit |
| Node metadata | advisory region/provider hints | optional | only if operator intentionally maps them |
| Webhook events | invalidation/reconcile triggers | strongly recommended | push-first mode |

### 19.3 State normalization requirement

The Bridge MUST convert Remnawave data into a normalized internal model before any policy computation.

Example normalized account snapshot:

```json
{
  "source": "remnawave",
  "source_version": "2.7.x",
  "account_id": "rw:user:2a6627e6-....",
  "bootstrap_subject": "rw:shortuuid:QHc8Yk...",
  "status": "active",
  "flags": {
    "disabled": false,
    "revoked": false,
    "expired": false,
    "limited": false
  },
  "plan": {
    "name": "pro",
    "traffic_limit_strategy": "MONTH_ROLLING"
  },
  "metadata": {
    "northstar": {
      "rollout_cohort": "stable",
      "preferred_regions": ["eu-nl", "eu-de"]
    }
  },
  "observed_at": "2026-04-01T12:00:00Z"
}
```

### 19.4 Hard rule

No manifest compiler logic may run on raw, unnormalized Remnawave responses.

---

## 20. Remnawave user metadata strategy

### 20.1 Why metadata matters

Metadata endpoints give the operator a place to attach Northstar-specific overrides without changing the core Remnawave user model.

### 20.2 Recommended namespace

Bridge SHOULD store user metadata under a clearly namespaced object, for example:

```json
{
  "northstar": {
    "enabled": true,
    "rollout_cohort": "stable",
    "preferred_regions": ["eu-nl", "eu-de"],
    "carrier_profile_allowlist": ["h3-generic-v1", "h3-cdn-v1"],
    "carrier_profile_denylist": [],
    "device_limit_override": 5,
    "gateway_group_allowlist": ["europe", "fallback-global"],
    "notes": "Operator-only freeform text"
  }
}
```

### 20.3 Ownership model for metadata

- Remnawave remains the storage provider
- Bridge remains the semantic owner of the `northstar` metadata subtree
- other tools MUST NOT mutate that subtree unless they intentionally integrate with Northstar

### 20.4 Fallback if metadata endpoints are unavailable

Bridge MUST support a fallback mode where all Northstar-specific overrides live in Bridge DB only.

### 20.5 Write-back rules

The Bridge MAY write back metadata only for:

- explicit operator-controlled sync
- idempotent normalized values
- values that help support/ops visibility

The Bridge SHOULD NOT write:

- refresh credentials
- session tokens
- raw device secrets
- large ephemeral telemetry blobs

---

## 21. Use of `resolvedProxyConfigs`

### 21.1 Why it still matters even though Northstar has its own gateways

The typed raw subscription feed is still useful as a **control-plane signal**, even if Northstar does not reuse the Xray transport definitions.

Examples of advisory use:

- preserving host remarks as user-visible region names
- inferring operator region naming conventions
- mapping existing host tags to Bridge gateway groups
- deriving migration hints when operator gradually moves users from Xray-backed transports to Northstar-backed transports

### 21.2 Hard limit on advisory use

The Bridge MUST NOT directly convert `resolvedProxyConfigs` into Northstar endpoints unless the operator has explicitly configured a mapping layer.

Why:

- Remnawave hosts describe Xray-oriented subscription outputs
- Northstar endpoints describe Rust gateways and carrier profiles
- the data models are related operationally, not identical

### 21.3 Optional host-to-gateway mapping layer

Operators MAY define a static or dynamic mapping:

```yaml
host_group_mappings:
  - remnawave_host_tag: europe
    northstar_gateway_groups: [eu-primary, eu-fallback]
  - remnawave_host_tag: finland
    northstar_gateway_groups: [fi-primary]
```

This mapping is operator-defined, not inferred blindly.

---

## 22. Northstar gateway inventory model

### 22.1 Inventory ownership

The Bridge is the source of truth for Northstar gateway inventory.

Inventory source options:

1. static config file
2. Bridge admin API
3. service discovery backend
4. GitOps-generated config
5. future control-plane feed

### 22.2 Minimal inventory object

```json
{
  "endpoint_id": "gw-eu-nl-1",
  "region": "eu-nl",
  "country": "NL",
  "provider": "example-provider-a",
  "public_host": "gw-eu-nl-1.example.net",
  "public_port": 443,
  "carrier_profiles": ["h3-generic-v1", "h3-cdn-v1"],
  "gateway_key_set": "gw-main-2026q2",
  "status": "healthy"
}
```

### 22.3 Inventory filters applied during manifest generation

The compiler MUST filter by:

- enabled/healthy status
- rollout cohort compatibility
- account allowlist/denylist
- carrier profile compatibility
- region restrictions
- incident kill switches
- minimum client version if endpoint requires it

### 22.4 Future inventory extensions

Deferred but anticipated:

- capacity score
- latency class
- ASN affinity
- edge provider type
- protocol experiment cohort
- “known-bad under network X” blacklist signals

---

## 23. Carrier profile derivation

### 23.1 Bridge-owned profiles

Carrier profiles are fully Bridge-owned and are not read from Remnawave template families.

Examples:

- `h3-generic-v1`
- `h3-cdn-v1`
- `h3-low-memory-v1`
- `h3-strict-middlebox-v1`

### 23.2 Policy inputs for profile selection

The Bridge MAY use these inputs:

- client version
- platform
- rollout cohort
- operator incident state
- region
- network report history
- per-account allow/deny lists in metadata

### 23.3 Profile precedence

Profile selection precedence SHOULD be:

1. hard safety deny rules
2. operator incident overrides
3. account allowlist
4. account denylist
5. cohort defaults
6. client-platform defaults
7. bridge global defaults

---

## 24. Manifest compilation contract

### 24.1 Compilation inputs

Manifest compilation consumes:

- normalized account snapshot
- device policy snapshot
- inventory snapshot
- carrier profile catalog
- rollout policy snapshot
- compatibility matrix
- current signer key id
- bridge global policy

### 24.2 Required outputs

Manifest compiler MUST output:

- manifest body following schema version `1`
- deterministic `manifest_id`
- signature block
- expiry and generation timestamps
- endpoints list
- carrier profile list
- client constraints
- token-service metadata
- routing/retry/telemetry policy

### 24.3 Determinism requirement

Given identical inputs, the compiler SHOULD produce the same semantic manifest and stable `manifest_id`.

### 24.4 Policy precedence

Manifest policy layers SHOULD merge in this order:

1. protocol hard ceilings
2. bridge global defaults
3. environment/region overrides
4. rollout cohort policy
5. account metadata overrides
6. incident overrides / emergency kill switches

Later layers win unless they violate hard ceilings.

### 24.5 Manifest invalidation triggers

Any of the following MUST invalidate cached manifest results for affected accounts:

- Remnawave account entitlement change
- metadata change affecting Northstar subtree
- device policy change
- carrier profile catalog change
- endpoint inventory change affecting selected groups
- signer key rotation if manifest signatures change
- client compatibility matrix change
- Bridge version introducing stricter policy

---

## 25. Policy epoch model

### 25.1 Purpose

The policy epoch gives Bridge, client, and gateway a shared notion of policy freshness.

### 25.2 Epoch bump triggers

The Bridge SHOULD bump policy epoch when any account-affecting policy changes occur, such as:

- revoke / disable / expire / limit
- account rollout cohort change
- device binding change that affects token issuance
- endpoint eligibility change severe enough to alter routing
- emergency deny policy

### 25.3 Epoch semantics

- policy epoch is monotonically increasing per account
- session tokens SHOULD carry the epoch they were minted under
- gateways MAY enforce “minimum acceptable epoch” if revocation push is later added
- clients SHOULD surface epoch mismatches only as diagnostics, not as UX jargon

---

## 26. Webhook ingestion model

### 26.1 Verification rules

Bridge MUST:

- verify HMAC signature using the configured secret
- record receipt timestamp
- reject malformed payloads
- avoid trusting webhook ordering

### 26.2 Idempotency rules

The webhook processor MUST be idempotent.

Recommended dedupe key:

- body hash + event + timestamp + scope

If a more reliable provider event id appears in future Remnawave versions, Bridge SHOULD adopt it.

### 26.3 Event handling matrix

| Event | Bridge action |
|---|---|
| `user.created` | fetch authoritative account snapshot, prime caches |
| `user.modified` | invalidate manifest cache, reconcile policy |
| `user.deleted` | mark account deleted, revoke Bridge artifacts |
| `user.revoked` | deny new sessions, bump epoch |
| `user.disabled` | deny manifest/token issuance |
| `user.enabled` | allow issuance after reconcile |
| `user.limited` | update policy / user-facing warnings |
| `user.expired` | deny issuance |
| `user.traffic_reset` | optional analytics/policy note; usually not security-critical |
| `user_hwid_devices.added` | advisory only unless operator explicitly maps it |
| `user_hwid_devices.deleted` | advisory only unless operator explicitly maps it |
| `service.subpage_config_changed` | refresh import-app config cache if Bridge consumes it |
| `node.connection_lost` | only relevant if operator maps node metadata to gateway groups |

### 26.4 Reconciliation after webhook

For important events, the Bridge SHOULD not trust webhook payload alone.  
It SHOULD fetch fresh authoritative state from Remnawave API before committing the final new policy snapshot.

### 26.5 Missed-event recovery

A periodic reconciler MUST exist even when webhooks are enabled.

Recommended intervals:

- hot account reconciliation after event: immediate
- periodic light reconcile: every 2–10 minutes
- slower full consistency sweep: every 1–12 hours depending on scale

---

## 27. Polling and reconciliation model

### 27.1 Why polling still exists

Webhooks can be dropped, reordered, duplicated, or misconfigured.  
Polling is the correctness backstop.

### 27.2 Required reconciler behaviors

The reconciler MUST support:

- bootstrap subject resolution
- account snapshot refresh by user UUID
- metadata refresh
- stale-manifest invalidation
- stale-device cleanup
- signer health checks
- inventory snapshot refresh

### 27.3 Cold-start behavior

On Bridge startup, the system SHOULD:

1. load signer keys
2. verify database schema/version
3. warm critical caches
4. start webhook receiver
5. start public API
6. start async reconciler
7. lazily refresh accounts on demand

### 27.4 Avoiding thundering herds

Reconciliation jobs SHOULD use:

- jitter
- bounded concurrency
- per-account backoff
- API rate-limit awareness
- adaptive refresh under panel stress

---

## 28. Public Bridge API behavior details

This section refines the frozen public API without altering the endpoint names.

### 28.1 Common response headers

Public API responses SHOULD include:

- `Cache-Control`
- `Date`
- request correlation id header
- `ETag` for manifest responses when appropriate

### 28.2 Error envelope

Public Bridge errors SHOULD use a stable envelope:

```json
{
  "error": {
    "code": "DEVICE_LIMIT_REACHED",
    "message": "This account already reached the allowed number of devices.",
    "retryable": false,
    "policy_epoch": 42,
    "details": {
      "max_devices": 5
    }
  }
}
```

### 28.3 Stable error code registry

Recommended initial public error codes:

- `INVALID_BOOTSTRAP_SUBJECT`
- `BOOTSTRAP_EXPIRED`
- `ACCOUNT_NOT_FOUND`
- `ACCOUNT_DISABLED`
- `ACCOUNT_REVOKED`
- `ACCOUNT_EXPIRED`
- `ACCOUNT_LIMITED`
- `MANIFEST_NOT_AVAILABLE`
- `DEVICE_BINDING_REQUIRED`
- `DEVICE_LIMIT_REACHED`
- `DEVICE_REVOKED`
- `INVALID_REFRESH_CREDENTIAL`
- `REFRESH_CREDENTIAL_EXPIRED`
- `PROFILE_NOT_ALLOWED`
- `CORE_VERSION_NOT_ALLOWED`
- `CLIENT_VERSION_TOO_OLD`
- `RATE_LIMITED`
- `UPSTREAM_CONTROL_PLANE_UNAVAILABLE`
- `TEMPORARY_RECONCILIATION_IN_PROGRESS`

### 28.4 HTTP status guidance

| Situation | Recommended status |
|---|---:|
| malformed request | 400 |
| invalid/expired credential | 401 |
| account exists but not allowed | 403 |
| bootstrap subject unknown | 404 |
| device conflict / device limit exceeded | 409 |
| bootstrap one-time token already spent | 410 |
| client version too old | 426 |
| rate limited | 429 |
| upstream unavailable | 503 |

### 28.5 Manifest caching semantics

`GET /v0/manifest` SHOULD support:

- `ETag`
- conditional `If-None-Match`
- short server-side cache TTL
- instant invalidation on high-priority policy changes

### 28.6 JWKS semantics

The Bridge MUST support key overlap during rotation:

- old keys remain published while old manifests/tokens can still be valid
- new keys appear before they are relied on exclusively
- key ids MUST be stable and unique

---

## 29. Private Remnawave adapter contract

The public `/v0/*` API is frozen.  
The private adapter contract is not public, but it still needs discipline.

### 29.1 Internal adapter interface

Illustrative Rust trait:

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

### 29.2 Adapter responsibilities

The adapter MUST:

- normalize Remnawave responses
- hide upstream schema churn from the rest of the Bridge
- own retry/backoff policy for Remnawave requests
- classify upstream errors into a small internal error taxonomy
- avoid leaking raw upstream JSON into public responses

### 29.3 Internal adapter error classes

Suggested classes:

- `NotFound`
- `Unauthorized`
- `RateLimited`
- `SchemaDrift`
- `Unavailable`
- `Timeout`
- `InvalidData`
- `Conflict`

### 29.4 Schema drift rule

If the adapter sees an unexpected upstream schema drift, it MUST fail closed for affected operations rather than silently guessing.

---

## 30. Bridge database and state model

### 30.1 Why a database is required

Even in MVP form, the Bridge needs durable state for:

- device bindings
- refresh credentials or refresh-credential references
- audit logs
- webhook dedupe
- cached normalized account snapshots
- manifest cache metadata
- signer state references

### 30.2 Recommended logical tables

| Table | Purpose |
|---|---|
| `accounts` | normalized account snapshots and entitlement cache |
| `account_policy_state` | per-account policy epoch, last compile info |
| `devices` | device registry |
| `refresh_credentials` | bridge-only refresh credentials or references |
| `manifest_cache` | manifest metadata and ETags |
| `webhook_inbox` | verified webhook dedupe + processing journal |
| `audit_events` | security and operations audit log |
| `gateway_inventory` | Bridge-owned endpoint catalog |
| `carrier_profiles` | Bridge-owned profile definitions |
| `issuer_keys` | signing key metadata |
| `network_reports` | sampled client-side telemetry, if retained |

### 30.3 Secrets storage

Raw key material SHOULD live in:

- HSM / KMS if available
- otherwise encrypted secret store with restricted access

The Bridge SHOULD avoid storing raw signing secrets in application database rows.

### 30.4 Refresh credential storage

Preferred options:

1. store hashed opaque secrets
2. store reference ids for externally managed credentials
3. if using signed refresh tokens, store revocation references and rotation metadata

The Bridge SHOULD NOT store plaintext refresh credentials unless no safer option exists in the MVP.

---

## 31. Device registration and refresh lifecycle

### 31.1 Bootstrap registration

A newly imported client typically follows:

1. fetch manifest using bootstrap subject
2. obtain bootstrap credential in manifest or equivalent
3. call `POST /v0/device/register`
4. receive device-bound refresh credential
5. discard bootstrap credential

### 31.2 Rotation

Refresh credentials SHOULD be rotatable without changing device identity.

Rotation triggers MAY include:

- credential nearing expiry
- client upgrade requiring stronger binding
- device metadata change
- suspicious activity
- operator-initiated reset

### 31.3 Revocation

Device revocation MUST make future refresh and token exchange fail.

### 31.4 Lost device recovery

Deferred for public UX, but the data model SHOULD anticipate:

- deleting a device
- rotating all credentials for an account
- forcing re-import

---

## 32. Token issuance model

### 32.1 Session token minting requirements

Before minting a session token, the Bridge MUST validate:

1. account still allowed
2. refresh credential valid
3. device valid if binding required
4. requested core version allowed
5. requested carrier profile allowed
6. endpoint selection possible
7. policy epoch current

### 32.2 Token claims guidance

Suggested claims:

```json
{
  "iss": "bridge-main",
  "sub": "rw:user:2a6627e6-....",
  "aud": "northstar-gateway",
  "exp": 1775049600,
  "nbf": 1775049300,
  "device_id": "dev_9f13...",
  "manifest_id": "sha256:...",
  "policy_epoch": 42,
  "carrier_profile_id": "h3-generic-v1",
  "capabilities": [1, 2, 3],
  "allowed_endpoint_groups": ["eu-primary", "global-fallback"]
}
```

### 32.3 Token TTL guidance

Recommended default:

- 3–10 minutes

### 32.4 Bridge-to-gateway trust

Gateways MUST validate:

- signature
- expiry
- audience
- issuer
- core version compatibility if encoded
- account state claims needed at session start

---

## 33. Subpage and install UX integration

### 33.1 Why this matters

A technically correct Bridge with bad install UX will not be adopted.

Remnawave already supports a subscription page and configurable app presentation.  
Northstar should plug into that instead of inventing a second disconnected user flow.

### 33.2 Operator requirement

The operator SHOULD expose Northstar in the Subscription Page Builder as:

- a supported app
- optionally a featured app
- with per-platform install links
- with a custom import/open action pointing to the Bridge

### 33.3 Bridge-hosted import page

Recommended operator pattern:

- Remnawave Subpage button opens `https://bridge.example.net/import/<bootstrap>`
- Bridge import page detects platform and does one of:
  - open deep link into installed Northstar client
  - redirect to app download page
  - show QR/manual copy fallback
  - provide “copy manifest URL” fallback

### 33.4 Why a Bridge-hosted page is preferable

Advantages:

- keeps custom logic outside panel fork
- lets Bridge rotate bootstrap format without changing the Northstar client
- keeps install analytics and diagnostics under operator control
- allows platform-specific fallback behavior

### 33.5 Dynamic app config strategy

Because Remnawave Subscription Page supports dynamic app config loading and app customization, Bridge integration SHOULD assume:

- app presentation is operator-managed in Remnawave
- import semantics remain Bridge-managed
- exact app-config JSON structure is outside this spec and may evolve independently

### 33.6 Future optional optimization

If the operator later wants a tighter integration, the Bridge MAY generate app-config payload fragments for operator copy/paste or automated sync, but this is not required in v0.1.

---

## 34. Northstar client behavior requirements

### 34.1 Import behavior

Client MUST support:

- import by HTTPS URL
- import via deep link / universal link
- refresh credential storage
- stable device id persistence
- last known-good manifest caching

### 34.2 Manifest behavior

Client MUST:

- verify signature
- obey `expires_at`
- obey `client_constraints`
- reject unsupported schema/core versions
- tolerate extra unknown manifest fields

### 34.3 Bridge error handling

Client SHOULD map Bridge error codes to meaningful UI messages.

### 34.4 Device-limit UX

Client SHOULD clearly distinguish:

- account not allowed
- device limit reached
- app too old
- temporary upstream issue
- network issue

### 34.5 Privacy requirement

Client SHOULD avoid sending unnecessary device characteristics.  
Only required device data should be transmitted.

---

## 35. Gateway behavior requirements relevant to the Bridge

### 35.1 Gateway MUST trust only Bridge-issued session tokens

Gateways MUST NOT accept:

- refresh credentials
- bootstrap credentials
- Remnawave subscription identifiers
- raw `shortUuid`

### 35.2 Gateway config surface required by the Bridge

Gateways need at least:

- accepted issuers
- trusted key set / JWKS source
- accepted core version range
- allowed carrier profile ids
- local kill switch / denylist support

### 35.3 Token/JWKS fetch behavior

Gateways SHOULD cache JWKS safely with refresh strategy and overlap support.

---

## 36. Security requirements

### 36.1 General

The Bridge is security-sensitive.  
It gates all manifest and token issuance.

### 36.2 Mandatory controls

The Bridge MUST:

- serve public APIs over HTTPS only
- isolate public API from operator/admin API
- verify Remnawave webhook signatures
- audit token issuance
- rate-limit bootstrap, device registration, and token exchange
- support signer rotation with overlap
- fail closed on upstream schema drift
- redact secrets from logs
- protect raw API tokens and signer keys
- implement strict input validation
- implement replay resistance where credentials claim one-time or short-lived semantics

### 36.3 Recommended controls

The Bridge SHOULD:

- use separate credentials for Remnawave API access and public Bridge signing
- use request correlation ids
- implement per-IP and per-account rate limits
- implement abuse heuristics for bootstrap replay
- log security-relevant events in structured form
- support emergency account and global deny switches
- support limited forensic retention for audit events

### 36.4 Dangerous shortcuts to avoid

The Bridge MUST NOT:

- trust raw webhook bodies without signature verification
- expose Remnawave API token to the client
- accept `shortUuid` directly at gateways
- treat account status caches as permanently authoritative
- silently continue when required Remnawave fields disappear
- store refresh credentials in plaintext unless unavoidable

---

## 37. Privacy requirements

### 37.1 Data minimization

Store only what is needed for:

- account entitlement
- device policy
- token issuance
- debugging
- abuse prevention

### 37.2 Sensitive data examples

Sensitive data includes:

- refresh credentials
- signer private keys
- raw bootstrap subjects
- raw HWID-like values
- client network reports if they include detailed path data

### 37.3 Retention guidance

Suggested defaults:

- webhook journal: 7–30 days
- audit events: 30–180 days depending on policy
- network reports: sampled and short-lived
- stale device records: retained as policy requires, not indefinitely

---

## 38. Observability requirements

### 38.1 Metrics

Bridge SHOULD export metrics such as:

- manifest fetch count / latency / cache hit ratio
- device registration count / failures
- token exchange count / failures
- webhook verification failures
- reconcile duration / failures
- Remnawave upstream request latency / errors
- per-error-code response counts
- signer rotation age
- inventory size and health summaries

### 38.2 Logs

Structured logs SHOULD include:

- request id
- account hash/reference
- device id hash/reference
- endpoint id if relevant
- policy epoch
- error code
- upstream correlation markers where available

### 38.3 Traces

Distributed tracing SHOULD cover:

- public API request
- adapter calls to Remnawave
- manifest compile step
- token mint step
- database operations
- webhook processing

### 38.4 Debuggability principle

Operators must be able to answer:

- why a manifest was denied
- why a device was rejected
- why a carrier profile was not allowed
- why a specific account got a specific manifest
- whether the issue is Remnawave state, Bridge policy, or inventory health

---

## 39. Availability and performance requirements

### 39.1 Bridge latency targets

Indicative v0.1 targets:

- warm manifest fetch: p95 under 100 ms
- token exchange: p95 under 80 ms
- device registration: p95 under 120 ms
- webhook verification: p95 under 50 ms

These are design targets, not protocol guarantees.

### 39.2 Availability target

The Bridge SHOULD be deployable as a stateless horizontally scalable public API tier with durable shared state behind it.

### 39.3 Failure containment

If Remnawave upstream is briefly unavailable, the Bridge MAY serve:

- cached last known-good manifest for still-valid refresh-authenticated clients
- but MUST NOT mint new session tokens from stale entitlement data beyond configured safety bounds

### 39.4 Safe stale-read policy

Recommended stale-read hierarchy:

1. bootstrap manifest generation: strict; require recent upstream confirmation
2. steady-state manifest refresh: may use recent cached normalized account snapshot for a short bounded window
3. token exchange: stricter than manifest refresh, because it directly grants data-plane access

---

## 40. Rate limiting and abuse controls

### 40.1 Required rate-limit dimensions

The Bridge SHOULD rate-limit by:

- IP
- bootstrap subject
- account
- device id
- refresh credential
- user-agent / install channel where useful

### 40.2 High-risk endpoints

Most sensitive:

- `GET /v0/manifest` in bootstrap mode
- `POST /v0/device/register`
- `POST /v0/token/exchange`

### 40.3 Abuse scenarios

Examples:

- brute-force bootstrap subjects
- replaying bootstrap links
- farming refresh credentials
- forcing expensive reconciliations
- fake telemetry flooding `/v0/network/report`

---

## 41. Failure modes and operator behavior

### 41.1 Remnawave unavailable

Bridge SHOULD:

- fail closed for new bootstrap imports if account cannot be validated
- allow very short stale-window behavior only where policy says safe
- emit clear operator alerts

### 41.2 Metadata corruption

If `northstar` metadata subtree is malformed:

- ignore malformed override subtree
- keep baseline entitlement
- emit operator-visible error
- do not produce an ambiguous manifest

### 41.3 Inventory empty for eligible account

Bridge SHOULD return:

- `MANIFEST_NOT_AVAILABLE`
- retryable = true if likely temporary

### 41.4 Signer unavailable

Bridge MUST fail closed for new manifest signatures and token issuance.

### 41.5 Webhook secret mismatch

Bridge MUST reject webhook and alert operator.

---

## 42. Operational rollout plan for the Bridge

### 42.1 Recommended rollout stages

1. **Dry-run mode**
   - resolve accounts
   - compile manifests
   - do not expose to end users
2. **Internal canary**
   - limited operator/test accounts
3. **Small public cohort**
   - selected users via metadata or bridge override
4. **Regional expansion**
5. **General availability**
6. **Profile experimentation**
   - only after stable baseline exists

### 42.2 Cohort selection

Cohorts MAY be derived from:

- explicit user metadata
- bridge allowlist
- install channel
- platform
- geography
- support/test tags

### 42.3 Rollback rules

Operators MUST be able to:

- disable Northstar globally
- disable a carrier profile
- disable a gateway group
- disable Northstar for one account
- force recompile manifests
- rotate issuer keys safely

---

## 43. Testing requirements

### 43.1 Bridge-specific test categories

1. adapter normalization tests
2. webhook verification tests
3. webhook idempotency tests
4. manifest compilation tests
5. metadata merge precedence tests
6. bootstrap and refresh auth-flow tests
7. device-limit tests
8. stale-cache safety tests
9. rate-limit tests
10. failure-injection tests

### 43.2 Required fixtures

The Bridge test corpus SHOULD include fixtures for:

- active user
- disabled user
- revoked user
- expired user
- limited user
- malformed metadata
- user with no Northstar override
- user with allowlist override
- empty gateway inventory
- mixed healthy/unhealthy gateway groups
- webhook duplication and reorder cases

### 43.3 Integration tests with Remnawave sandbox

Strongly recommended:

- a disposable Remnawave environment
- test API token
- test webhook secret
- scripted user state transitions
- scripted subscription page import path

### 43.4 AI-agent guardrails for test generation

If AI agents write Bridge code, they MUST be instructed to:

- never bypass signature checks in production code
- treat adapter schema as unstable and validate it
- write explicit tests for every public error code
- write idempotency tests for webhook ingestion
- never couple manifest compilation directly to raw upstream JSON

---

## 44. Suggested implementation crate split

A possible Rust workspace layout:

```text
crates/
  ns-bridge-api/              # public /v0 HTTP models and handlers
  ns-bridge-domain/           # core entities, policy engine, manifest compiler
  ns-bridge-adapter-rw/       # Remnawave adapter
  ns-bridge-webhooks/         # webhook verification and ingestion
  ns-bridge-store/            # db layer and repositories
  ns-bridge-issuer/           # signer and token issuance
  ns-bridge-inventory/        # gateway inventory provider
  ns-bridge-config/           # config parsing and defaults
  ns-bridge-observability/    # metrics, tracing, logging helpers
  ns-bridge-bin/              # executable
```

### 44.1 Dependency direction

Preferred dependency direction:

```text
api -> domain
adapter-rw -> domain
webhooks -> domain
issuer -> domain
inventory -> domain
store -> domain
bin -> all runtime crates
```

### 44.2 Why this split matters

It keeps:

- Remnawave coupling isolated
- domain logic testable
- public Bridge contract separate from upstream integration churn

---

## 45. Suggested configuration surface

Illustrative operator config:

```yaml
bridge:
  public_base_url: https://bridge.example.net
  issuer: bridge-main
  bootstrap:
    allow_plain_short_uuid: true
    signed_bootstrap_enabled: false
  security:
    webhook_secret: env:RW_WEBHOOK_SECRET
    remnawave_api_token: env:RW_API_TOKEN
  manifest:
    ttl_seconds: 21600
    bootstrap_ttl_seconds: 600
    session_token_ttl_seconds: 300
  rate_limits:
    manifest_bootstrap_per_minute: 20
    token_exchange_per_minute: 60
remnawave:
  base_url: https://panel.example.net
  version_floor: 2.7.0
  polling:
    light_reconcile_seconds: 300
    full_reconcile_seconds: 14400
inventory:
  source: static
  endpoints:
    - endpoint_id: gw-eu-nl-1
      region: eu-nl
      public_host: gw-eu-nl-1.example.net
      public_port: 443
      gateway_group: eu-primary
      carrier_profiles: [h3-generic-v1, h3-cdn-v1]
    - endpoint_id: gw-eu-de-1
      region: eu-de
      public_host: gw-eu-de-1.example.net
      public_port: 443
      gateway_group: eu-primary
      carrier_profiles: [h3-generic-v1]
```

---

## 46. Suggested operator playbooks

### 46.1 Revoke one user

1. revoke/disable user in Remnawave
2. ensure webhook or reconcile updates Bridge
3. verify new token exchange fails
4. verify client sees correct error
5. optionally force-refresh gateway deny cache if such mechanism exists later

### 46.2 Remove a compromised device

1. revoke device in Bridge
2. rotate refresh credential for that device/account
3. verify future token exchange fails for that device
4. optionally notify user

### 46.3 Disable a broken carrier profile

1. mark profile unavailable in Bridge policy
2. bump policy epoch for affected users or global cohort
3. invalidate manifests
4. verify clients fall back to another profile

### 46.4 Remnawave outage mode

1. assess current Bridge stale-read policy
2. decide whether to disable bootstrap imports temporarily
3. keep session-token issuance strict
4. monitor error rate and operator alerts

---

## 47. Deferred backlog: useful but too much for now

This section is intentionally long so valuable ideas do not disappear.

### 47.1 Auth and bootstrap

- bridge-signed bootstrap envelopes as default
- one-time bootstrap redemption
- signed install bundles with platform-specific deep links
- QR bootstrap payload format
- refresh credential families by install channel

### 47.2 Device management

- end-user self-service device listing and revocation
- support portal device reset flow
- operator-visible bridge device inventory in Remnawave metadata mirror
- device trust scoring
- per-device policy experiments

### 47.3 Control-plane richness

- automatic subpage app-config sync if Remnawave exposes stable APIs for it
- richer write-back of Northstar status into Remnawave metadata
- bridge-side export feed for analytics dashboards
- audit-stream sink integration

### 47.4 Inventory and routing

- dynamic inventory from Consul/etcd/Kubernetes
- endpoint capacity-aware manifest generation
- ASN-aware endpoint recommendations
- incident-driven regional deny rules
- bridge-assisted path recommendations based on sampled reports

### 47.5 Security

- KMS/HSM signing
- remote attestation for Bridge nodes
- signed webhook nonce envelopes if provider ever adds them
- mTLS between Bridge and operator private services
- dedicated replay-prevention store for bootstrap redemption

### 47.6 Scalability

- multi-tenant bridge namespaces
- sharded device registry
- regional manifest signing replicas
- edge cache for manifest fetch with signed freshness proofs

### 47.7 UX

- better import diagnostics page
- platform-specific install docs
- “copy recovery link” mode
- multilingual error surface aligned with subscription page languages

### 47.8 Governance

- stable public Bridge API versioning policy
- formal migration guides across manifest schema revisions
- operator compatibility matrix by Remnawave version
- conformance kit for third-party Bridge implementations

---

## 48. Open questions

These are intentionally not resolved yet.

1. Should the initial bootstrap manifest carry a bootstrap credential directly, or should there be a separate bootstrap-exchange endpoint later?
2. Should refresh credentials be opaque database-backed secrets or signed self-describing tokens plus revocation handles?
3. How much Northstar policy should be mirrored into Remnawave metadata versus kept Bridge-only?
4. Should Bridge ever write device summaries back into Remnawave metadata for support visibility?
5. Should Northstar client emit a hashed HWID claim by default, or leave it entirely optional?
6. Should Bridge-hosted import pages be mandatory, or can operators use direct deep links only?
7. What is the final long-term replacement strategy for plain `shortUuid` bootstrap mode?

---

## 49. Acceptance criteria for v0.1

The Bridge spec is considered implemented well enough for v0.1 when all of the following are true:

1. a user with a valid Remnawave subscription can import Northstar through a no-fork path
2. the Bridge can resolve bootstrap input to authoritative Remnawave account state
3. the Bridge can compile and sign a valid manifest
4. the client can register a device and obtain a refresh credential
5. the client can exchange refresh credential for a valid short-lived session token
6. a revoked/disabled/expired user is denied promptly
7. Bridge device policy is enforced independently of direct Remnawave HWID fetch semantics
8. webhook verification and dedupe work correctly
9. periodic reconciliation heals missed webhook cases
10. operators can expose Northstar in the Remnawave subscription UX without forking the panel
11. all of the above are covered by automated tests

---

## 50. Implementation priorities

### 50.1 Must build first

1. public `/v0/manifest`
2. Remnawave adapter for account resolution
3. manifest compiler
4. signer and JWKS
5. `/v0/token/exchange`
6. minimal device registry
7. basic import page or deep-link handler
8. webhook verification
9. reconcile loop

### 50.2 Build second

1. metadata support
2. richer device UX/errors
3. inventory health weighting
4. structured audit log
5. network report ingestion
6. better subpage integration tooling

### 50.3 Build later

1. signed bootstrap envelopes
2. device self-service
3. operator write-back into metadata
4. advanced route recommendations
5. multi-tenant Bridge

---

## 51. References and operator notes

### 51.1 Northstar companion docs

This spec should be read together with:

- `northstar_blueprint_v0.md`
- `northstar_wire_format_freeze_candidate_v0_1.md`

### 51.2 Remnawave features this spec intentionally builds around

This spec assumes the operator can make use of documented Remnawave capabilities such as:

- multi-family client template delivery
- typed raw subscription output with `resolvedProxyConfigs`
- signed webhooks
- optional HWID subscription-device enforcement for compatible clients
- Subscription Page / Subpage Builder with configurable apps
- dynamic app config support in recent Subscription Page versions
- user and node metadata endpoints in recent panel versions

### 51.3 Operator warning

The Bridge is designed to keep Northstar independent from Xray-core.  
That independence is a feature, not a bug.

If a future project goal becomes “Northstar protocol imported directly into generic Xray clients without a custom client,” that is a different track and requires work in the relevant cores. This Bridge spec intentionally does not depend on that path.

---

## Appendix A — Example steady-state manifest fetch

```http
GET /v0/manifest HTTP/1.1
Host: bridge.example.net
Authorization: Bearer rfr_eyJ...
If-None-Match: "m:sha256:91db..."
User-Agent: Northstar/0.1.0 (windows; x64)
```

Example `304 Not Modified`:

```http
HTTP/1.1 304 Not Modified
ETag: "m:sha256:91db..."
Cache-Control: private, max-age=60
```

---

## Appendix B — Example Bridge error

```json
{
  "error": {
    "code": "ACCOUNT_REVOKED",
    "message": "This subscription is no longer active.",
    "retryable": false,
    "policy_epoch": 57
  }
}
```

---

## Appendix C — Example Bridge-side normalized device record

```json
{
  "device_id": "dev_bf3989d6f7",
  "account_id": "rw:user:2a6627e6-....",
  "status": "active",
  "platform": "windows",
  "client_version": "0.1.0",
  "install_channel": "stable",
  "device_name": "Main Laptop",
  "hwid_claim_hash": "sha256:...",
  "first_seen_at": "2026-04-01T12:03:00Z",
  "last_seen_at": "2026-04-01T12:44:00Z"
}
```

---

## Appendix D — Example namespaced user metadata patch

```json
{
  "northstar": {
    "enabled": true,
    "rollout_cohort": "canary-eu",
    "preferred_regions": ["eu-nl", "eu-de"],
    "carrier_profile_allowlist": ["h3-generic-v1"],
    "device_limit_override": 3
  }
}
```
