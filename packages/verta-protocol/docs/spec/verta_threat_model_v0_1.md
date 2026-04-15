# Verta Threat Model v0.1

**Status:** Draft v0.1  
**Codename:** Verta  
**Canonical filename:** `verta_threat_model_v0_1.md`  
**Compatibility note:** stable technical identifiers and compatibility surfaces may still use legacy lowercase `verta` or env aliases such as `VERTA_*` below.  
**Document type:** security threat model, risk register, and control requirements  
**Audience:** protocol architects, Rust engineers, client engineers, security reviewers, SREs, release engineers, AI coding agents  
**Companion documents:**  
- `Adaptive Proxy/VPN Protocol Master Plan`
- `Blueprint v0 — Adaptive Proxy/VPN Protocol Suite (Verta)`
- `Verta Spec v0.1 — Wire Format Freeze Candidate`
- `Verta Remnawave Bridge Spec v0.1`

---

## 1. Why this document exists

The Master Plan explains **how the project will be built over time**.  
Blueprint v0 explains **what the architecture looks like**.  
The Wire Format Freeze Candidate explains **what is frozen enough to implement on the wire**.  
The Bridge Spec explains **how Verta integrates with Remnawave without forking it**.

This document explains something different:

- what can go wrong
- who can attack which part of the system
- which failures are merely operational and which are security failures
- which risks Verta must reduce now
- which risks Verta can only contain, not eliminate
- which controls are mandatory before alpha, beta, and public release

This is the source of truth for **security reasoning** across the protocol, the Bridge, the gateway, the client, the build pipeline, and operations.

---

## 2. Executive security posture

Verta is a **high-risk networking system** because it combines:

- remote account bootstrap
- token issuance
- encrypted transport
- censorship-adaptive transport profiles
- multi-device subscription handling
- public Internet-facing gateways
- an external control-plane dependency (Remnawave)

The project therefore treats security as a first-class protocol concern, not a later hardening step.

### 2.1 Core security thesis

Verta v0.1 does **not** try to achieve magical invisibility.

It tries to achieve:

1. **strong control-plane integrity**  
2. **strict token and manifest authenticity**  
3. **damage containment when credentials leak**  
4. **fast rollback and profile rotation when a transport persona is fingerprinted**  
5. **resource-exhaustion resistance at the gateway edge**  
6. **privacy-preserving logging and observability**  
7. **clear authority boundaries between Remnawave, Bridge, client, and gateway**

### 2.2 Honest statement about censorship resistance

No protocol can honestly promise to be permanently unfingerprintable or permanently unblockable.

Verta therefore defines success as:

- reducing unique protocol surface
- minimizing static identifiers
- enabling rapid profile rotation
- keeping the session core stable while transport personas change
- making fingerprinting expensive and brittle
- reducing the blast radius when a profile is burned

This is a realistic security posture. It is not a fantasy promise.

---

## 3. Scope

### 3.1 In scope

This threat model covers:

- client bootstrap from Remnawave-linked UX into the Verta Bridge
- Bridge public API and private Remnawave adapter behavior
- manifest generation and signed distribution
- session token minting and verification
- gateway session establishment and steady-state forwarding
- transport-profile selection and profile rotation
- device registration and optional HWID reconciliation
- logging, metrics, tracing, and operational telemetry
- build/release/update chain for client, gateway, and Bridge
- operator controls and incident response

### 3.2 Out of scope for v0.1

The following are explicitly out of scope for this version, though many are listed later as deferred work:

- formal cryptographic proofs
- perfect anonymity against a global passive adversary
- malware-resistant clients on fully compromised endpoints
- secure enclave / attested execution requirements
- post-quantum migration requirements
- multi-party anonymity architectures
- advanced pluggable transports not yet in the frozen carrier set
- legal or policy analysis by jurisdiction

---

## 4. System summary

Verta v0.1 follows the non-fork path:

- **Remnawave** remains the external account and subscription authority
- **Verta Bridge** translates external subscription state into Verta-native manifests and tokens
- **Verta Client** imports, registers, fetches manifests, and obtains session tokens
- **Verta Gateway** validates session tokens and carries the data plane
- **Verta Signer/JWKS** anchors manifest and token authenticity
- **Transport personas** determine the network-facing behavior of the gateway and client

### 4.1 Simplified architecture

```text
Operator
   |
   +--> Remnawave Panel / API / Webhooks
   |
   +--> Verta Bridge
           |
           +--> Remnawave Adapter
           +--> Manifest Compiler
           +--> Device Registry
           +--> Token Issuer / JWKS
           +--> Policy Store / Inventory
           |
           +--> Public API
                    |
                    +--> Verta Client
                               |
                               +--> Verta Gateway
```

### 4.2 Security-critical trust boundaries

The primary trust boundaries are:

1. **Internet boundary** — all network paths are hostile
2. **Bridge public API boundary** — bootstrap, manifest, token exchange
3. **Bridge private adapter boundary** — Bridge to Remnawave API/webhooks
4. **Gateway ingress boundary** — session establishment and forwarding
5. **Client device boundary** — local storage, keychain, logs, updates
6. **Operator boundary** — CI/CD, secrets, dashboards, observability backends
7. **Third-party network boundary** — CDN, reverse proxy, load balancer, DNS, TLS termination assumptions if used

### 4.3 Security invariants

The following invariants are non-negotiable:

- the gateway MUST trust only Bridge-issued session authority
- the client MUST treat transport profiles as signed policy, not local guesswork
- the Bridge MUST never trust unsigned webhook payloads
- the Bridge MUST never treat raw HWID as a strong identity primitive
- the protocol MUST never rely on obscurity of wire format as the primary defense
- the system MUST never require long-lived bearer credentials at the gateway edge
- control-plane integrity failures MUST be detectable and recoverable
- downgrade to weaker behavior MUST require explicit, signed, policy-driven authorization

---

## 5. Security goals

Verta v0.1 aims to satisfy these goals.

### 5.1 Authentication and authorization

- only authorized subscriptions may obtain manifests
- only registered devices may obtain refresh/session credentials
- only Bridge-issued session tokens may open sessions on a gateway
- revoked or disabled users must lose new-session access quickly
- policy changes must converge across Bridge and gateways without silent drift

### 5.2 Confidentiality and integrity

- transport confidentiality and integrity must rely on standard, modern cryptographic primitives
- manifest authenticity must be verifiable by clients
- token authenticity must be verifiable by gateways
- control messages must be transcript-bound where applicable
- unauthenticated inputs must never influence security-sensitive gateway state beyond tightly bounded pre-auth handling

### 5.3 Availability and abuse containment

- the system must resist obvious DoS, replay, and resource-exhaustion attacks
- the gateway must bound memory, CPU, and per-device concurrency
- Bridge endpoints must be rate-limited and cache-aware
- costly operations must occur only after cheap validation gates

### 5.4 Privacy and unlinkability

- raw HWID should not become a global correlator across the system
- logs must minimize sensitive identifiers
- manifests must contain only necessary per-device information
- telemetry must not leak more user metadata than required for operations

### 5.5 Adaptation under censorship pressure

- transport personas must be rotatable without breaking the session core
- probing responses must avoid expensive or unique behavior before authorization
- profile rollout must be canary-based and reversible

---

## 6. Explicit non-goals and impossibility statements

The project deliberately does **not** claim the following:

- permanent immunity from fingerprinting
- perfect indistinguishability from any arbitrary third-party protocol
- protection when the user endpoint is fully compromised
- secrecy after Bridge signing keys are fully exfiltrated and remain valid
- safety if operators disable required checks to “make things work”
- infinite scalability without admission control
- zero metadata leakage on the public Internet
- perfect resistance against a state-level adversary with broad observation, active probing, and endpoint compromise

These non-goals matter because vague promises create insecure designs.

---

## 7. Assets to protect

The most important assets are:

### 7.1 Control-plane assets

- Remnawave admin credentials
- Remnawave API tokens used by the Bridge
- webhook secret material
- subscription identifiers and user mapping data
- Bridge operator accounts and deployment credentials

### 7.2 Bridge security assets

- manifest signing keys
- token signing keys
- refresh credential material
- Bridge database contents
- policy epochs and device registry state
- gateway inventory and carrier-profile policy

### 7.3 Gateway assets

- gateway private key material
- accepted JWKS state / trust roots
- session admission budgets
- runtime config including active personas and policy epochs

### 7.4 Client assets

- bootstrap link or bootstrap envelope
- refresh credential
- local configuration state
- device key material if introduced
- cached manifests
- update channel trust anchors

### 7.5 Privacy-sensitive assets

- IP addresses
- approximate location and ASN-derived routing hints
- usage patterns
- device metadata
- network quality reports
- cross-device correlation identifiers
- subscription request history

### 7.6 Software supply chain assets

- CI signing keys
- release artifacts
- package repository credentials
- container registry credentials
- dependency lockfiles and verification policies

---

## 8. Assumptions validated against current Remnawave capabilities

Verta v0.1 depends on a few current Remnawave behaviors that affect threat exposure.

### 8.1 Assumption A — webhook signatures exist

Remnawave currently documents signed webhooks with `X-Remnawave-Signature` and `X-Remnawave-Timestamp`.

**Threat implication:** the Bridge MUST verify signature, timestamp freshness, and replay windows.  
**Operational implication:** losing clock sync or misconfiguring the secret can create security failures or availability failures.

### 8.2 Assumption B — typed raw subscription data exists

Recent Remnawave releases expose typed `resolvedProxyConfigs` in raw subscription flows.

**Threat implication:** typed structures reduce parser ambiguity, but the Bridge MUST still treat Remnawave transport information as advisory, not authoritative for Verta session security.

### 8.3 Assumption C — HWID can be enforced and can reject absent headers

Current HWID device-limit behavior can return `404` if a client does not send `x-hwid` while the limit is enabled.

**Threat implication:** Verta MUST avoid assuming that panel-side HWID behavior maps cleanly to Bridge-side device registration.  
**Security implication:** raw HWID MUST be treated as weak/advisory identity input, never as a cryptographic identity root.

### 8.4 Assumption D — Subscription Page and dynamic app-config exist

Remnawave’s subscription page and builder can steer users toward selected apps and app-config variants.

**Threat implication:** if the import UX points directly to panel endpoints instead of the Bridge-owned bootstrap flow, users can bypass Bridge policy and weaken security guarantees.

### 8.5 Hard conclusion

Verta must treat Remnawave as:

- authoritative for **account and subscription lifecycle**
- advisory for **legacy protocol host inventory**
- useful for **webhook-triggered state changes**
- **not** authoritative for Verta device identity, token issuance, or gateway admission

---

## 9. Threat actors and attacker classes

Verta must assume multiple attacker classes operating simultaneously.

### 9.1 A1 — opportunistic Internet attacker

Capabilities:

- scans public endpoints
- replays observed links
- brute-forces weak paths
- exploits missing rate limits
- exploits default credentials and obvious misconfigurations

### 9.2 A2 — malicious or abusive subscribed user

Capabilities:

- has a valid subscription or obtained one from someone else
- can script bootstrap and token refresh
- can reverse engineer the client
- can resell access
- can share import links and refresh credentials
- can attempt concurrency abuse, bandwidth abuse, and policy evasion

### 9.3 A3 — on-path network attacker

Capabilities:

- can observe packet timing and metadata
- can block, delay, reorder, and inject traffic
- can force retries and path changes
- can attempt TLS interception where trust is already compromised
- cannot break modern cryptography directly

### 9.4 A4 — active probing censor / DPI operator

Capabilities:

- performs repeated connection attempts
- classifies traffic by timing, headers, ALPN, packet sizes, retry behavior, and failure behavior
- can block IPs, ports, ASNs, SNI values, ALPN patterns, HTTP paths, and protocol behaviors
- can cause selective degradation and partial blocking
- may obtain real client binaries for reverse engineering

### 9.5 A5 — botnet / DDoS adversary

Capabilities:

- floods bootstrap endpoints
- floods token exchange
- floods gateway handshake paths
- exploits expensive cryptographic paths
- uses many source IPs and rotating ASNs

### 9.6 A6 — compromised client host

Capabilities:

- reads local config and cached manifests
- steals refresh credentials
- tampers with client binaries
- exfiltrates logs and reports
- impersonates the user until credentials are rotated or revoked

### 9.7 A7 — compromised operator, admin, or insider

Capabilities:

- reads logs and databases
- changes deployment config
- injects malicious profiles
- steals keys if secrets handling is weak
- weakens policies intentionally or by mistake

### 9.8 A8 — supply-chain attacker

Capabilities:

- compromises a dependency, build agent, or release pipeline
- injects malicious code into client, Bridge, or gateway
- tampers with update metadata or signing keys

### 9.9 A9 — third-party infrastructure failure or misbehavior

Capabilities:

- stale DNS
- broken CDN caching rules
- incorrect TLS termination
- header normalization
- request replay across regions
- cache leakage across authenticated users

---

## 10. Entry points and attack surfaces

The main attack surfaces are:

1. Remnawave-facing webhook receiver  
2. Bridge public API:
   - `GET /v0/manifest`
   - `POST /v0/device/register`
   - `POST /v0/token/exchange`
   - `POST /v0/network/report`
   - `GET /.well-known/jwks.json`
3. client import/bootstrap URLs
4. refresh credential storage on client devices
5. gateway session ingress and pre-auth state
6. token/JWKS distribution and cache behavior
7. transport-profile updates and policy-epoch transitions
8. observability pipelines, logs, traces, metrics backends
9. deployment secrets and CI/CD infrastructure
10. Bridge database and internal service-to-service auth

---

## 11. Threat analysis methodology

Verta v0.1 uses a practical hybrid model:

- **STRIDE-style thinking** for spoofing, tampering, repudiation, information disclosure, denial of service, and privilege escalation
- **protocol-specific analysis** for replay, downgrade, probing, fingerprinting, abuse, and linkability
- **operational analysis** for multi-region consistency, deployment error, stale state, and secret handling
- **supply-chain analysis** for build/update compromise

Threat priority labels in this document:

- **P0 / Critical** — can directly break trust boundaries or cause system-wide compromise
- **P1 / High** — serious user impact or realistic large-scale abuse
- **P2 / Medium** — meaningful but containable
- **P3 / Deferred/Low** — record now, solve later, or accept with monitoring

---

## 12. Design principles derived from the threat model

These principles must guide implementation.

### 12.1 Cryptography principles

- use only standard, well-reviewed cryptographic constructions
- do not invent custom encryption or MAC schemes
- separate token signing keys from manifest signing keys
- prefer asymmetric verification at gateways
- maintain key rotation procedures from day one

### 12.2 Protocol design principles

- minimize unauthenticated protocol surface
- minimize static identifiers visible to the network
- keep rejection behavior cheap, bounded, and consistent
- bind negotiated features to authenticated state where possible
- require explicit versioning and downgrade protection

### 12.3 Operational design principles

- every critical policy change must be observable
- every revocation path must have a bounded convergence target
- stale reads may be acceptable for availability, but only under explicit policy
- deployment defaults must bias toward safety over convenience

### 12.4 Privacy principles

- store only what is needed
- avoid raw device identity propagation to gateways
- scrub tokens and subscription identifiers from logs
- make debug logging opt-in and time-bounded

---

## 13. Detailed threat register

---

## 13.1 Control-plane and bootstrap threats

### TM-CP-01 — bootstrap URL leakage  
**Priority:** P0

A bootstrap link or bootstrap envelope may leak via:

- screenshots
- browser history
- chat forwarding
- support tickets
- proxy logs
- analytics or referrer leakage
- client debug logs

**Impact:**

- unauthorized device registration
- subscription hijacking
- accidental or malicious sharing
- support burden and user lockout
- policy bypass if bootstrap remains valid too long

**Required controls:**

- bootstrap credentials MUST be short-lived
- bootstrap credentials MUST be single-use or strictly use-limited
- bootstrap credentials MUST NOT become long-lived refresh credentials by themselves
- Bridge MUST bind bootstrap redemption to an explicit registration step
- import pages SHOULD avoid exposing full secrets in browser-visible URLs when possible
- clients MUST scrub bootstrap strings from logs and crash reports
- operators SHOULD prefer Bridge-hosted import flows over direct raw panel URLs

**Residual risk:**

Bootstrap leakage cannot be fully prevented if the endpoint is compromised or the user shares the link intentionally. The goal is to sharply limit replay value.

---

### TM-CP-02 — direct panel endpoint bypass  
**Priority:** P1

A user may import a Remnawave subscription directly into a legacy-compatible path instead of using the Bridge-owned bootstrap flow.

**Impact:**

- Verta device policy bypass
- inconsistent revocation behavior
- inconsistent telemetry and support flows
- weaker security guarantees than the documented Verta model

**Required controls:**

- operator-facing setup MUST make the Bridge import path the canonical path
- Subscription Page config SHOULD feature the Verta client and hide or de-emphasize incompatible import patterns for Verta cohorts
- Bridge SHOULD detect and warn about user state divergence where possible
- documentation MUST clearly state that direct panel subscription import is out of policy for Verta mode

**Residual risk:**

An operator can still intentionally expose conflicting flows. This becomes an operational misconfiguration risk, not a protocol failure.

---

### TM-CP-03 — unauthorized device registration via race or replay  
**Priority:** P0

An attacker who observes a bootstrap credential may race the legitimate user to redeem it first.

**Impact:**

- attacker obtains the first registered device slot
- legitimate user becomes blocked or sees confusing device-limit errors
- account takeover at the device layer

**Required controls:**

- bootstrap redemption MUST be atomic
- the Bridge MUST record bootstrap state transitions transactionally
- the Bridge MUST expose explicit error states for already-redeemed bootstrap credentials
- device registration SHOULD require a client-generated nonce/challenge to reduce naive replay
- suspicious bootstrap contention SHOULD be logged and surfaced to operators

**Residual risk:**

Real-time theft remains possible if the device or import channel is already compromised.

---

### TM-CP-04 — account state drift between Remnawave and Bridge  
**Priority:** P1

Revocation, disablement, or quota changes may reach the Bridge late or inconsistently.

**Impact:**

- revoked users continue to access new sessions longer than intended
- device-limit state diverges
- user sees inconsistent policy outcomes across regions

**Required controls:**

- Bridge MUST support both webhook-triggered and polling reconciliation
- revocation events MUST bump policy epoch
- token TTL MUST be short enough to bound stale authorization
- gateways MUST reject expired session tokens without consulting stale local user state
- Bridge MUST define a maximum revocation convergence target and monitor it

**Residual risk:**

Already-issued short-lived session tokens remain valid until expiry unless explicit revocation infrastructure is added later.

---

## 13.2 Webhook and reconciliation threats

### TM-WH-01 — forged webhook payloads  
**Priority:** P0

An attacker sends fake webhook events to the Bridge to create, revoke, or alter user state.

**Impact:**

- incorrect user enable/disable events
- forced device cleanup
- confusion, denial of service, or shadow authorization changes

**Required controls:**

- Bridge MUST verify `X-Remnawave-Signature`
- Bridge MUST verify freshness of `X-Remnawave-Timestamp`
- Bridge MUST reject missing signature or excessive clock skew
- Bridge MUST use constant-time comparison for signature checks
- Bridge MUST log signature failures without logging secrets

**Residual risk:**

If the webhook secret is fully compromised, forged events become possible until secret rotation.

---

### TM-WH-02 — webhook replay  
**Priority:** P1

A previously valid webhook is replayed later.

**Impact:**

- old revocation or modification state may be re-applied unexpectedly
- event processing loops
- state churn or partial rollback

**Required controls:**

- Bridge MUST keep a replay cache keyed by signature/timestamp/body digest or event identity
- Bridge MUST define and enforce a narrow freshness window
- handlers MUST be idempotent
- Bridge MUST reconcile from source-of-truth after critical events

**Residual risk:**

Replay within the accepted time window is still possible if deduplication is weak or storage is unavailable.

---

### TM-WH-03 — out-of-order delivery and missed events  
**Priority:** P1

Webhooks may arrive late, duplicated, or out of order.

**Impact:**

- stale state
- accidental re-enablement
- confusing policy-epoch churn
- user lockouts or over-permission

**Required controls:**

- all event handlers MUST be idempotent
- event timestamps MUST NOT be blindly trusted as the sole ordering mechanism
- the Bridge MUST periodically reconcile from Remnawave even in push-first mode
- destructive state transitions SHOULD be confirmed by fresh source reads when possible

**Residual risk:**

Temporary inconsistency is inevitable under distributed failure; the design goal is bounded inconsistency, not impossible perfection.

---

## 13.3 Token, key, and signature threats

### TM-KM-01 — Bridge signing key compromise  
**Priority:** P0

An attacker obtains manifest signing keys or session token signing keys.

**Impact:**

- forged manifests
- forged session tokens
- gateway trust collapse
- large-scale unauthorized access
- silent malicious transport-profile injection

**Required controls:**

- manifest signing and token signing MUST use separate keys
- production keys MUST be stored in a hardened secret system, not plain environment files
- key access MUST be narrowly scoped by service role
- key rotation MUST be documented and tested
- JWKS must support overlap during rotation
- emergency revocation playbooks MUST exist before public launch

**Residual risk:**

Full signer compromise is existential. The main defense is reducing blast radius and speeding recovery.

---

### TM-KM-02 — weak JWT verification behavior  
**Priority:** P0

Common JWT implementation errors include algorithm confusion, typ confusion, audience confusion, accepting unsigned tokens, or skipping issuer checks.

**Impact:**

- gateway accepts forged or mis-scoped tokens
- cross-environment token confusion
- session hijacking

**Required controls:**

- gateways MUST enforce explicit allowlists for `alg`, `typ`, `iss`, and `aud`
- unsigned or unexpected-token-type inputs MUST be rejected
- token purpose MUST be explicit and typed
- verification libraries MUST be wrapped in strict local policy code, not used with permissive defaults
- negative test vectors MUST cover algorithm confusion and issuer/audience mismatch

**Residual risk:**

Library misuse remains possible unless verification code is centrally owned and highly tested.

---

### TM-KM-03 — refresh credential theft from the client  
**Priority:** P0

A compromised endpoint steals a refresh credential or equivalent long-lived device credential.

**Impact:**

- persistent unauthorized manifest refresh
- repeated session token issuance
- account abuse from another device or region

**Required controls:**

- refresh credentials MUST be stored in platform keychain/credential storage where available
- refresh credentials MUST be device-scoped
- the Bridge MUST support device-specific revocation
- refresh credentials SHOULD be rotatable on successful use
- Bridge SHOULD track anomalous refresh patterns by ASN, region, and concurrency
- debug export tools MUST redact refresh credentials by default

**Residual risk:**

A fully compromised endpoint can impersonate the device until revocation completes.

---

### TM-KM-04 — JWKS cache poisoning or stale key acceptance  
**Priority:** P1

Gateways or clients accept stale or incorrect JWKS content due to caching bugs, proxy behavior, or DNS misrouting.

**Impact:**

- rejected valid tokens during rotation
- accepted invalid tokens if stale keys linger incorrectly
- partial region outages

**Required controls:**

- JWKS responses MUST have explicit cache policy
- gateways MUST pin expected issuer and JWKS origin
- key IDs MUST be globally unique within an issuer
- rotation MUST include overlap windows and explicit retirement
- gateways SHOULD fail closed on unverifiable tokens but fail with observable error classes

**Residual risk:**

Caching infrastructure can still behave badly; rollout testing and observability are critical.

---

## 13.4 Manifest and profile-distribution threats

### TM-MF-01 — unsigned or weakly validated manifest acceptance  
**Priority:** P0

A client accepts a tampered or spoofed manifest.

**Impact:**

- malicious gateways inserted into inventory
- forced profile downgrade
- user traffic steered to attacker infrastructure
- denial of service or deanonymization

**Required controls:**

- manifests MUST be signed
- clients MUST verify issuer, signature, schema version, and profile compatibility
- manifest parsing MUST be strict for security-relevant fields
- unknown critical extensions MUST fail closed
- clients MUST ignore unsigned local overrides in release mode unless explicitly in developer mode

**Residual risk:**

Users running modified clients can still defeat local checks on their own device.

---

### TM-MF-02 — profile downgrade injection  
**Priority:** P1

An attacker or insider tries to force weaker or more fingerprintable personas than policy intended.

**Impact:**

- easier fingerprinting
- more stable block signatures
- user-visible connection failures
- erosion of “adaptive” promises

**Required controls:**

- manifests MUST carry explicit policy epoch and profile priority
- clients MUST require signed authorization for downgrade-sensitive changes
- “safe mode” or “fallback mode” MUST be explicit policy states, not silent local heuristics
- Bridge admin actions affecting personas SHOULD be auditable

**Residual risk:**

A malicious operator can still choose bad profiles intentionally. That is governance risk, not pure protocol risk.

---

### TM-MF-03 — cross-user manifest caching leakage  
**Priority:** P1

A CDN, reverse proxy, or misconfigured cache serves one user’s manifest to another user.

**Impact:**

- privacy leakage
- wrong device policy
- wrong gateway inventory
- accidental cross-account access if secrets are embedded

**Required controls:**

- authenticated manifest responses MUST use cache directives appropriate for private content
- caches MUST vary on `Authorization` or other auth context where applicable
- Bridge MUST avoid placing long-lived secrets in URLs
- Bridge-hosted bootstrap pages SHOULD minimize sensitive query-string exposure

**Residual risk:**

Third-party infrastructure bugs can still cause leakage; integration testing against chosen infrastructure is required.

---

## 13.5 Gateway admission and session threats

### TM-GW-01 — gateway accepts user-controlled policy  
**Priority:** P0

A gateway trusts user-supplied hints, headers, or unsigned manifest-like data to decide policy.

**Impact:**

- privilege escalation
- profile confusion
- unauthorized session classes
- bypass of Bridge policy

**Required controls:**

- gateways MUST trust only Bridge-issued session tokens and local config
- user-supplied routing or profile hints MUST be treated as advisory at most
- claims used for authorization MUST come only from verified tokens
- gateways MUST not fetch user-specific policy from arbitrary URLs

**Residual risk:**

None acceptable. This is a hard design rule.

---

### TM-GW-02 — expensive pre-auth work enables DoS  
**Priority:** P0

An attacker triggers expensive cryptography, parsing, or upstream allocation before cheap validation.

**Impact:**

- CPU exhaustion
- memory pressure
- connection table saturation
- regional outage

**Required controls:**

- gateways MUST bound pre-auth allocation
- the earliest possible validation step MUST be cheap and constant-space
- admission control MUST exist per source IP / per token / per device / per ASN as appropriate
- QUIC anti-amplification and retry strategies SHOULD be used appropriately under attack
- expensive downstream setup MUST happen only after verified authorization where possible

**Residual risk:**

Sufficiently large botnets can still cause pressure; layered defenses remain required.

---

### TM-GW-03 — replay of session establishment tokens  
**Priority:** P1

A short-lived session token is replayed within its validity window.

**Impact:**

- duplicate or parallel sessions
- concurrency abuse
- resource consumption
- confusion in accounting

**Required controls:**

- session tokens MUST be short-lived
- gateways SHOULD enforce jti/nonce replay controls where practical for high-risk cohorts
- concurrency limits MUST exist per device and/or user
- Bridge SHOULD be able to issue narrower tokens for sensitive cohorts

**Residual risk:**

Some replay within a small window may be tolerated if bounded by concurrency and TTL.

---

### TM-GW-04 — path migration abuse and rebinding confusion  
**Priority:** P2

A QUIC-based carrier may see NAT rebinding or malicious path changes.

**Impact:**

- unauthorized amplification
- session confusion
- false disconnects
- evade simplistic rate limits

**Required controls:**

- path validation MUST occur before significant amplification on a new path
- per-connection migration budgets SHOULD be bounded
- gateway telemetry SHOULD distinguish expected NAT rebinding from suspicious migration patterns

**Residual risk:**

Mobile networks and hostile paths can still create ambiguity.

---

## 13.6 Active probing, fingerprinting, and censorship threats

### TM-DPI-01 — active probe identifies unauthenticated handshake behavior  
**Priority:** P0

A censor can probe public endpoints repeatedly and classify them by handshake sequence, ALPN, response timing, status codes, or error content.

**Impact:**

- infrastructure blocks
- profile burn
- cascading blocklists across IPs or regions

**Required controls:**

- unauthenticated behavior MUST be minimal, bounded, and non-distinctive where feasible
- failure behavior MUST avoid rich protocol errors before authorization
- transport personas MUST be remotely rotatable
- Bridge/gateway rollout MUST support canary cohorts and fast rollback
- operators MUST be able to disable or de-prioritize burned personas quickly

**Residual risk:**

A determined censor with binaries and live probing can still fingerprint a profile eventually. The realistic goal is fast adaptation, not invulnerability.

---

### TM-DPI-02 — static identifiers create long-lived fingerprints  
**Priority:** P1

Stable ALPNs, paths, header orders, packet-size patterns, or timing signatures make a persona easy to classify.

**Impact:**

- faster fingerprinting
- broad blocking with low false positives
- inability to rotate cheaply

**Required controls:**

- session core and carrier persona MUST be separated architecturally
- personas MUST be versioned and replaceable
- profile definitions MUST avoid unnecessary static markers
- rollouts SHOULD test diversity and detect over-concentration on one persona

**Residual risk:**

Some wire-image properties of the chosen carrier remain externally visible by design.

---

### TM-DPI-03 — downgrade to a more detectable fallback  
**Priority:** P1

Under network failure, the client silently falls back to a weaker or more detectable transport.

**Impact:**

- involuntary exposure to a burned profile
- privacy regression
- user confusion about “it worked, then got blocked”

**Required controls:**

- fallback order MUST come from signed policy
- clients MUST surface major profile-class changes in diagnostics
- “silent fallback” across risk tiers MUST be prohibited by default
- Bridge SHOULD be able to disable a persona globally by policy epoch

**Residual risk:**

Some operators may intentionally prefer availability over stealth. That tradeoff must be explicit.

---

## 13.7 Device identity and HWID threats

### TM-DV-01 — treating HWID as strong identity  
**Priority:** P1

Raw HWID values can be spoofed, collide, or be unavailable.

**Impact:**

- false positives in abuse control
- false lockouts
- easier impersonation if HWID becomes the sole key
- privacy harm if reused across systems

**Required controls:**

- HWID MUST be advisory only
- device registration MUST use Bridge-issued device identity and refresh credentials
- raw HWID MUST NOT be forwarded to gateways as a primary identity claim
- operators SHOULD be able to disable HWID-derived heuristics independently of device registration

**Residual risk:**

Some cohorts may still rely on weak client ecosystems; support tooling must expect ambiguity.

---

### TM-DV-02 — device slot exhaustion by attacker  
**Priority:** P1

An attacker registers many devices or races registration to consume a user’s allowed device count.

**Impact:**

- user denial of service
- support burden
- coercive account hijacking patterns

**Required controls:**

- device registration MUST be rate-limited
- bootstrap redemption MUST be atomic
- device-management UI/workflow MUST support recovery and revocation
- Bridge SHOULD surface suspicious device churn
- device limits SHOULD be configurable per cohort

**Residual risk:**

An attacker with repeated access to new bootstrap credentials can continue abuse until the root leak is fixed.

---

## 13.8 Privacy and observability threats

### TM-PR-01 — sensitive data in logs  
**Priority:** P0

Tokens, bootstrap URLs, raw HWID, or full IP-history end up in logs, traces, or error payloads.

**Impact:**

- credential leakage
- internal privacy violations
- easier insider abuse
- broader compromise during incident response

**Required controls:**

- structured logging MUST redact tokens, secrets, bootstrap materials, and raw HWID
- debug mode MUST be explicit and time-limited
- crash reports MUST be scrubbed
- observability pipelines MUST be treated as sensitive systems
- support bundles MUST require affirmative export steps

**Residual risk:**

Human error remains possible; log-scrubbing tests and review gates are necessary.

---

### TM-PR-02 — cross-gateway linkability through stable identifiers  
**Priority:** P1

A stable user or device identifier appears at many gateways.

**Impact:**

- stronger cross-session correlation
- privacy degradation
- easier abuse of leaked logs

**Required controls:**

- tokens SHOULD use pseudonymous device claims rather than raw global identifiers
- gateways SHOULD receive only the minimum identity surface needed for admission and accounting
- log schema SHOULD separate stable operator identifiers from user-visible identifiers

**Residual risk:**

Some stable identity is needed for quotas and abuse handling; complete unlinkability is not compatible with all operational goals.

---

### TM-PR-03 — network quality reports leak sensitive environment data  
**Priority:** P2

Clients may report too much diagnostic context in `/v0/network/report`.

**Impact:**

- device fingerprinting by the operator or intruder
- excessive metadata retention
- privacy-law complications

**Required controls:**

- telemetry schema MUST be minimal
- reports MUST avoid raw destination history and unrelated local-network information
- retention MUST be short and configurable
- clients SHOULD allow privacy-reduced modes where product requirements permit

**Residual risk:**

Useful operations data and minimal metadata are in tension; the schema must be reviewed repeatedly.

---

## 13.9 Client compromise and local tampering threats

### TM-CL-01 — reverse engineering exposes protocol details and profile logic  
**Priority:** P2

Attackers reverse engineer the client and learn persona rules, endpoints, and validation behavior.

**Impact:**

- faster active probing
- profile burn
- abuse automation

**Required controls:**

- security MUST NOT rely on secrecy of the client binary
- sensitive trust decisions MUST remain server-verifiable
- profile rotation MUST assume eventual reverse engineering
- release and debug builds MUST be clearly separated

**Residual risk:**

Reverse engineering is expected. The architecture must remain secure anyway.

---

### TM-CL-02 — modified client disables verification  
**Priority:** P1

A user runs a custom or patched client that ignores manifest signatures, device limits, or policy warnings.

**Impact:**

- local bypass of safety checks
- greater support burden
- potentially easier resale or abuse

**Required controls:**

- gateways MUST independently verify authorization
- Bridge MUST not assume honest client enforcement
- unsupported-client behavior SHOULD be observable at the server side where practical
- developer mode features MUST be isolated from release configuration

**Residual risk:**

Users can always run modified software on their own devices; server-side trust boundaries must absorb this.

---

## 13.10 Supply-chain and release threats

### TM-SC-01 — malicious dependency or compromised build worker  
**Priority:** P0

A dependency update or CI worker injects malicious code into Bridge, client, or gateway artifacts.

**Impact:**

- credential exfiltration
- silent backdoors
- mass compromise

**Required controls:**

- reproducible or near-reproducible builds SHOULD be pursued
- lockfiles MUST be committed and reviewed
- artifact signing MUST exist
- build provenance SHOULD be generated
- release signing keys MUST be isolated from general CI workers
- dependency update workflows SHOULD be gated and reviewable

**Residual risk:**

Supply chain remains a major modern attack surface; layered controls are mandatory.

---

### TM-SC-02 — update metadata compromise  
**Priority:** P0

An attacker compromises the channel that tells clients to install a new version.

**Impact:**

- malicious client rollout
- persistence on endpoints
- stolen refresh credentials and user traffic exposure

**Required controls:**

- update metadata MUST be signed
- clients MUST verify update signatures
- rollback protection SHOULD be defined
- emergency revocation of release signing keys MUST be planned

**Residual risk:**

Users who manually install unsigned community builds remain outside the core trust model.

---

## 13.11 Operator and insider threats

### TM-OP-01 — dangerous emergency changes under pressure  
**Priority:** P1

During an outage or block event, an operator disables verification, extends TTLs too far, exposes debug logs, or bypasses the Bridge to “restore service”.

**Impact:**

- hidden security regression
- lingering insecure state
- large attack windows after the emergency ends

**Required controls:**

- dangerous flags MUST be explicit, auditable, and time-bounded
- break-glass procedures MUST be documented
- insecure overrides SHOULD auto-expire
- admin operations affecting security posture SHOULD generate alerts

**Residual risk:**

Human pressure during incidents cannot be eliminated; guardrails reduce the chance of lasting damage.

---

### TM-OP-02 — over-privileged observability and support access  
**Priority:** P1

Support staff or internal tools can view excessive user data.

**Impact:**

- privacy violations
- insider abuse
- unnecessary credential exposure

**Required controls:**

- role-based access MUST separate support, SRE, and security roles
- sensitive fields SHOULD be masked in normal dashboards
- incident-only access SHOULD be auditable
- query access to raw logs SHOULD be minimized

**Residual risk:**

Insider threat remains possible; audit trails and least privilege are required.

---

## 13.12 Denial-of-service and capacity threats

### TM-DS-01 — manifest endpoint flooding  
**Priority:** P1

Attackers flood `GET /v0/manifest` using guessed or stolen bootstrap/refresh contexts.

**Impact:**

- Bridge saturation
- user-visible slow imports and reconnects
- cache stampedes

**Required controls:**

- rate limits MUST exist per IP and per auth context
- bootstrap paths SHOULD be more tightly limited than steady-state refresh paths
- manifest responses SHOULD use ETags or equivalent cache validators where safe
- expensive upstream calls to Remnawave MUST be shielded by local caches and reconciliation state

**Residual risk:**

Large-scale attacks can still force shedding and degraded service.

---

### TM-DS-02 — token exchange flood  
**Priority:** P1

Attackers hammer `POST /v0/token/exchange` to force signing and policy lookups.

**Impact:**

- signing service saturation
- delayed user reconnects
- possible cascading failures into gateway admission

**Required controls:**

- token issuance MUST be rate-limited
- Bridge SHOULD re-use validated manifest/policy context for a short window where safe
- signer health and queue depth MUST be monitored
- Bridge SHOULD separate public API from signer infrastructure with bounded queues

**Residual risk:**

Attackers with many valid refresh credentials remain difficult; per-device quotas help.

---

### TM-DS-03 — gateway handshake flood  
**Priority:** P0

Gateways are flooded with incomplete or repeated session attempts.

**Impact:**

- admission collapse
- excessive per-connection state
- collateral impact on legitimate users

**Required controls:**

- gateway pre-auth state MUST be bounded
- source reputation, token checks, and concurrency limits MUST work together
- transport-level anti-amplification protections SHOULD be enabled where relevant
- region-level admission shedding MUST be possible
- observability MUST separate network-level drops from token/policy failures

**Residual risk:**

Very large volumetric attacks still require infrastructure-level mitigation beyond the protocol.

---

## 13.13 Data integrity and persistence threats

### TM-DI-01 — Bridge database corruption or partial restore  
**Priority:** P1

The Bridge database is rolled back, corrupted, or restored from an inconsistent snapshot.

**Impact:**

- revoked devices reappear
- replay caches reset
- epoch state diverges
- refresh credentials become inconsistent

**Required controls:**

- critical state changes MUST be versioned
- backups MUST be encrypted and tested
- restore procedures MUST include post-restore reconciliation with Remnawave
- replay-sensitive stores SHOULD be reconstructed conservatively
- operator docs MUST state which artifacts are recoverable and which require forced re-registration

**Residual risk:**

Disaster recovery often reintroduces stale state; recovery playbooks must assume it.

---

### TM-DI-02 — inconsistent multi-region policy epoch  
**Priority:** P1

Different Bridge regions serve different policy epochs too long.

**Impact:**

- clients oscillate
- token exchange inconsistencies
- gateway acceptance mismatches

**Required controls:**

- policy epochs MUST be monotonic
- epoch propagation lag MUST be measured
- clients and gateways SHOULD tolerate short overlap windows but reject impossible regressions
- region failover testing MUST include policy-epoch transitions

**Residual risk:**

Short-lived inconsistency is expected; long-lived inconsistency is a release-blocking bug.

---

## 14. Cross-cutting mandatory controls

This section converts the threat register into concrete project requirements.

### 14.1 Identity and token controls

Verta v0.1 MUST have:

- separate key roles for manifest signing and token signing
- explicit token typing
- strict `iss`, `aud`, `alg`, and `typ` verification
- short-lived session tokens
- device-scoped refresh credentials
- device-level revocation
- explicit issuer/JWKS pinning behavior in gateways

### 14.2 Bridge API controls

The Bridge MUST have:

- request authentication on all non-public endpoints
- strong rate limiting on bootstrap, registration, and token exchange
- replay protection on webhook and bootstrap-sensitive paths
- structured, redacted error envelopes
- clear cache semantics
- no silent acceptance of malformed security-critical input

### 14.3 Gateway controls

Gateways MUST have:

- bounded pre-auth state
- concurrency quotas
- per-user or per-device session budgets
- strict token verification before expensive allocation where practical
- policy-epoch awareness
- observability that distinguishes auth failures from network failures

### 14.4 Client controls

Clients MUST have:

- manifest signature verification
- secure local storage for refresh credentials
- token/secret redaction in logs
- explicit handling for profile-risk-tier changes
- no silent disabling of verification in release builds

### 14.5 Operational controls

Operations MUST have:

- secret rotation playbooks
- incident response playbooks
- deployment environment separation
- signed artifacts
- dependency review policy
- access-control separation for support vs admin vs security responders

---

## 15. Security requirements by component

### 15.1 Verta Bridge

The Bridge is the highest-consequence component after the signing infrastructure.

It MUST:

- verify webhook authenticity and freshness
- maintain replay and idempotency protections
- reconcile against Remnawave periodically
- generate signed manifests only from normalized internal state
- issue session tokens only from current policy state
- avoid embedding long-lived secrets in returned content
- keep an auditable trail of security-relevant admin actions

### 15.2 Remnawave adapter

The adapter MUST:

- use least-privileged credentials where possible
- treat external data as input to normalization, not direct trusted runtime state
- survive API schema drift safely
- fail with explicit operator-visible errors if the external contract changes incompatibly

### 15.3 Signer / JWKS service

The signer MUST:

- isolate key roles
- support planned and emergency rotation
- expose stable JWKS behavior
- never log signing secrets
- separate signing errors from public-facing error detail

### 15.4 Verta client

The client MUST:

- verify signed manifests
- store refresh secrets securely
- protect the user from accidental unsafe import flows
- surface device registration or limit issues clearly
- avoid leaking secrets in diagnostics

### 15.5 Verta gateway

The gateway MUST:

- trust only Bridge-issued session authority
- reject unverifiable or stale tokens
- keep pre-auth resource use bounded
- isolate admission failure from core runtime health
- avoid verbose unauthenticated errors

### 15.6 CI/CD and release pipeline

The pipeline MUST:

- sign artifacts
- isolate release keys
- pin and review dependencies
- scan for secret leakage
- preserve build logs without leaking secrets
- support rollback to known-good releases

---

## 16. Detection, monitoring, and incident response

Security design without detection is incomplete.

### 16.1 Detection objectives

The system must detect:

- repeated invalid bootstrap redemption
- repeated invalid token verification attempts
- webhook signature failures and timestamp skew
- sudden transport-profile failure spikes by region/ASN
- rapid device churn or slot exhaustion attacks
- abnormal token-exchange volume
- unusual refresh reuse patterns
- signer key-rotation anomalies
- cache anomalies causing wrong-manifest delivery

### 16.2 Minimum security telemetry

Verta SHOULD emit at least:

- counters for manifest requests by auth class and outcome
- counters for token exchange by device and outcome
- webhook verification outcome counters
- replay/cache hit rates for sensitive paths
- gateway auth-failure classifications
- region-by-region policy epoch propagation lag
- profile success/failure by cohort
- device registration contention events

### 16.3 Incident classes

Verta should classify incidents into at least:

1. **Credential leak**  
2. **Signing-key compromise**  
3. **Manifest forgery / token forgery suspicion**  
4. **Transport-profile burn / fingerprinting event**  
5. **Webhook integrity failure**  
6. **Mass abuse / resale**  
7. **Sensitive log leakage**  
8. **Supply-chain compromise suspicion**  

### 16.4 Response expectations

For each class there MUST be an operator playbook that includes:

- who is paged
- what is revoked or rotated
- what traffic or cohort is disabled
- what user-facing notice is needed
- how to collect forensics without leaking more secrets
- how to roll forward or roll back safely

---

## 17. Verification and testing plan driven by this threat model

This document is not complete unless it drives real tests.

### 17.1 Required test categories

Verta MUST implement tests for:

- forged and replayed webhooks
- bootstrap replay and race conditions
- malformed or tampered manifests
- token algorithm/issuer/audience confusion
- stale JWKS rotation windows
- gateway pre-auth flood behavior
- device-slot exhaustion logic
- log redaction
- direct-panel-bypass detection where applicable
- multi-region policy-epoch drift
- downgrade/fallback policy enforcement
- cache misconfiguration around manifest delivery

### 17.2 Fuzzing requirements

At minimum:

- manifest parsers
- token claim parsing wrappers
- control-stream parsers
- Bridge request decoding
- any binary frame decoder in the session core

### 17.3 Chaos and fault-injection requirements

Before public beta, the team SHOULD exercise:

- webhook delivery loss
- Remnawave API unavailability
- signer unavailability
- DB rollback/restore
- stale cache serving old JWKS
- regional policy-epoch lag
- aggressive gateway handshake flooding
- profile disable/rollback under simulated fingerprint burn

### 17.4 Red-team style exercises

Before wider release, the project SHOULD run exercises covering:

- client reverse engineering
- bootstrap theft and race
- refresh-credential theft from a simulated compromised endpoint
- operator console abuse
- malicious transport-profile rollout
- log exfiltration from observability tooling

---

## 18. Deferred security work

These items are intentionally recorded now so they are not forgotten later.

### 18.1 Advanced anti-abuse and attribution

- stronger per-device attestation
- abuse-economics modeling
- reseller graph detection
- ASN reputation scoring
- account-sharing heuristics with privacy review

### 18.2 Advanced privacy work

- privacy budgets for telemetry
- pseudonymous accounting models
- optional privacy-preserving relay splits
- improved unlinkability between regions or gateway cohorts

### 18.3 Advanced cryptographic hardening

- hardware-backed signing
- key transparency style audit logs
- selective disclosure credentials if product goals justify the complexity
- post-quantum migration planning

### 18.4 Formal methods and stronger protocol assurance

- formal state-machine models
- symbolic protocol analysis
- verified parser subsets
- stronger conformance suites shared with external implementers

### 18.5 Endpoint hardening

- auto-update transparency logs
- signed config bundles with rollback counters
- stronger local anti-tamper measures
- mobile-OS-specific secure storage hardening profiles

---

## 19. Residual-risk statement

Even after all required controls are implemented, Verta still accepts the following realities:

- a compromised endpoint can leak refresh credentials
- a compromised operator can do significant damage
- a determined censor can eventually burn some transport personas
- some metadata leakage is unavoidable on public networks
- DDoS at sufficient scale remains an infrastructure problem, not purely a protocol problem
- reverse engineering of the client is expected
- distributed systems can only bound, not eliminate, state lag

These are not failures of the threat model. They are the reality the design must live within.

---

## 20. Launch security gates

### 20.1 Minimum gates before private alpha

The project MUST have:

- signed manifests
- strict token verification policy
- short-lived session tokens
- device-scoped refresh credentials
- webhook verification
- replay-safe bootstrap redemption
- secret redaction in logs
- basic rate limiting
- signer key-rotation playbook
- incident classification and on-call ownership

### 20.2 Minimum gates before beta

The project MUST additionally have:

- multi-region policy-epoch testing
- cache/JWKS rotation testing
- gateway flood testing
- manifest tamper tests
- downgrade-policy tests
- supply-chain signing and provenance controls
- support-safe debug bundle rules
- audit trails for high-risk admin actions

### 20.3 Minimum gates before broad public release

The project SHOULD additionally have:

- red-team exercise results
- chaos testing around Remnawave dependency outages
- emergency profile-burn rollback drills
- compromise recovery rehearsals
- dependency review automation and artifact-verification enforcement
- published security policy and disclosure channel

---

## 21. Implementation guardrails for AI coding agents

If AI agents are used to build Verta, they MUST follow these guardrails.

### 21.1 Prohibited behavior

AI agents MUST NOT:

- invent cryptographic constructions
- weaken verification to “make tests pass”
- log tokens, bootstrap strings, or raw HWID
- bypass signature checks behind silent feature flags
- treat external Remnawave payloads as directly trusted internal state
- add permissive JWT verification options
- auto-accept unknown critical fields
- expand fallback behavior without signed policy

### 21.2 Required behavior

AI agents SHOULD:

- implement strict parsers
- write negative tests first for security-sensitive code
- centralize verification logic
- preserve typed error classes
- add redaction tests for logging changes
- document security rationale in code comments for complex verification code
- route security-critical config through explicit types, not stringly typed maps

### 21.3 Mandatory human review areas

Human review is mandatory for:

- token verification code
- signing code
- manifest validation
- device registration logic
- rate-limit logic
- gateway admission control
- secret handling
- logging/tracing changes affecting security-relevant fields

---

## 22. Open questions to resolve after v0.1

These are not blockers for the document, but they should stay visible:

1. whether session-token replay protection needs stronger `jti` state for premium or high-risk cohorts  
2. whether Bridge-issued device credentials should become proof-of-possession rather than bearer-style refresh credentials in later versions  
3. whether profile-risk tiers need explicit client UX categories beyond current manifest policy  
4. whether the project should require hardware-backed signing before public scale  
5. whether optional VPN-mode / CONNECT-IP style tunnel operation changes the privacy and DoS model enough to warrant a split threat model  
6. how much telemetry can be removed without harming profile-rotation decisions  
7. whether stronger operator safety rails are needed around emergency “break glass” flags  

---

## 23. Final conclusion

Verta’s real security problem is not just “encrypt traffic”.

It is the combination of:

- bootstrap trust
- device registration
- token issuance
- gateway admission
- transport adaptation
- operator safety
- privacy-preserving observability
- external control-plane dependency

The protocol suite becomes credible only if these are designed together.

This threat model therefore establishes the governing rule for Verta v0.1:

> **The system must assume that transport personas can burn, clients can be reverse engineered, links can leak, webhooks can be replayed, operators can make mistakes, and endpoints can be compromised. The architecture must remain controllable and recoverable anyway.**

That is the standard Verta should build to.

---

## 24. Reference points used while drafting this document

These references informed assumptions and operational constraints for v0.1:

- Remnawave Panel changelog and API behavior around raw subscription structure and feature evolution
- Remnawave webhook documentation, including signature and timestamp headers
- Remnawave HWID device-limit documentation and HWID-related response/header behavior
- Remnawave Subscription Page documentation and dynamic app-config capability
- RFC 9000 — QUIC: A UDP-Based Multiplexed and Secure Transport
- RFC 9114 — HTTP/3
- RFC 9221 — QUIC DATAGRAM
- RFC 9297 — HTTP Datagrams and Capsule Protocol
- RFC 9298 — Proxying UDP in HTTP
- RFC 9484 — Proxying IP in HTTP
- RFC 8725 — JSON Web Token Best Current Practices
- RFC 9308 — Applicability of the QUIC Transport Protocol
- RFC 9312 — Manageability of the QUIC Transport Protocol
