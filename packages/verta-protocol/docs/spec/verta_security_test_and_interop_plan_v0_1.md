# Verta Security Test & Interop Plan v0.1

**Status:** Draft v0.1  
**Codename:** Verta  
**Canonical filename:** `verta_security_test_and_interop_plan_v0_1.md`  
**Compatibility note:** stable technical identifiers and compatibility surfaces may still use legacy lowercase `verta` or env aliases such as `VERTA_*` below.  
**Document type:** security validation, interoperability, conformance, and release-gating plan  
**Audience:** protocol architects, Rust implementers, QA engineers, security reviewers, SREs, release engineers, Remnawave-Bridge implementers, AI coding agents  
**Companion documents:**  
- `Adaptive Proxy/VPN Protocol Master Plan`  
- `Blueprint v0 — Adaptive Proxy/VPN Protocol Suite (Verta)`  
- `Verta Spec v0.1 — Wire Format Freeze Candidate`  
- `Verta Remnawave Bridge Spec v0.1`  
- `Verta Threat Model v0.1`  

---

## 1. Why this document exists

The Verta document set already answers several different questions:

- the **Master Plan** explains what should be built over time
- **Blueprint v0** explains the architectural shape
- the **Wire Format Freeze Candidate** defines what is stable enough to implement on the wire
- the **Bridge Spec** defines how Verta integrates with Remnawave without forking it
- the **Threat Model** explains what can go wrong and which controls are required

This document answers a different question:

**How do we prove that the implementation is secure enough, interoperable enough, and operationally stable enough to deserve release?**

That requires more than “run some tests.” Verta is a protocol suite with:

- a custom client
- a custom gateway
- a Remnawave-connected Bridge
- signed manifests and session tokens
- adaptive carrier profiles
- censorship-pressure assumptions
- Internet-facing admission paths

For a system like this, validation must be treated as a first-class engineering program.

This document therefore defines:

- the test taxonomy
- the conformance suites
- the interoperability matrix
- the security validation program
- the network-chaos and abuse-resistance program
- the release gates for alpha, beta, and public availability
- the artifacts that must be produced and preserved

This is the source of truth for **how correctness, safety, compatibility, and readiness are judged**.

---

## 2. Executive summary

Verta v0.1 MUST NOT be considered ready merely because:

- the reference client can connect to the reference gateway once
- a happy-path manifest can be fetched
- benchmark numbers look fast in a clean lab
- the code “seems to work” under manual testing

Verta v0.1 is only acceptable when all of the following are true:

1. **Wire conformance is deterministic**  
   Independent implementations of the v0.1 wire contract produce compatible behavior for all frozen frames, limits, and sequencing rules.

2. **Bridge and control-plane behavior is robust**  
   The Bridge handles Remnawave state, signed webhooks, polling, cache staleness, and device state transitions safely and predictably.

3. **Security controls hold under hostile input**  
   Malformed frames, forged tokens, replay attempts, tampered manifests, webhook abuse, and pre-auth floods are rejected safely and cheaply.

4. **Interoperability is proven, not assumed**  
   Client, gateway, and Bridge builds from different commits or teams remain compatible within the same frozen version contract.

5. **Observability is useful without leaking too much**  
   Metrics, traces, and logs support debugging and incident response without turning into a privacy or secret-exposure hazard.

6. **Operational rollback is real**  
   Carrier profiles, gateway cohorts, and signing material can be rolled or disabled safely under adverse network conditions.

### 2.1 Core testing thesis

Verta should be validated in layers:

1. **static validation** — schemas, linters, code review, dependency review  
2. **deterministic correctness** — unit tests, property tests, fixture tests  
3. **wire conformance** — frozen binary fixtures, parser rules, sequencing rules  
4. **integration correctness** — client/gateway/Bridge end-to-end flows  
5. **interop correctness** — different builds and permutations remain compatible  
6. **security validation** — hostile inputs, replay, confusion, abuse, boundary failures  
7. **network realism** — loss, jitter, reorder, MTU stress, NAT rebinding, poor UDP  
8. **operational realism** — key rotation, stale cache, partial outages, rollback, profile burn  
9. **release gates** — alpha, beta, public-readiness criteria

### 2.2 Honest statement about limits

No test plan can prove permanent unblockability or permanent resistance to fingerprinting.

This plan therefore measures something more realistic:

- protocol correctness
- compatibility discipline
- adaptation safety
- resource-exhaustion resistance
- rollback readiness
- failure containment

---

## 3. Scope

### 3.1 In scope

This plan covers testing for:

- the Verta client
- the Verta gateway
- the Verta Bridge
- the Remnawave adapter used by the Bridge
- the signed manifest flow
- the session-token issuance and validation flow
- the v0.1 wire contract defined in the Freeze Candidate
- the primary carrier binding (`CarrierKind = 1`, `h3`)
- TCP relay mode
- UDP relay mode via datagram when available
- UDP relay via stream fallback
- observability, rate limiting, and rollback behavior
- CI/CD release gates
- incident-driven validation and chaos tests

### 3.2 Out of scope for v0.1

The following are important, but they are not required for declaring v0.1 complete:

- formal verification of the protocol
- post-quantum migration test suites
- multi-carrier parity with `raw_quic`, `h2_tls`, or `ws_tls`
- full Layer-3 IP tunnel mode
- mobile-OS-specific deep battery and radio optimization studies
- multi-language independent implementations beyond the Rust reference stack
- third-party Xray-core integration
- cover-traffic research
- global anonymity/privacy research beyond operational privacy controls

These deferred items are listed again later so they are not forgotten.

---

## 4. Normative language and interpretation

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

When this document says:

- **pass**: the observed implementation behavior matches the expected behavior
- **fail closed**: the implementation rejects input without entering an unsafe or undefined state
- **cheap rejection**: the implementation rejects invalid or unauthorized input with bounded CPU, memory, and allocation cost
- **interop pass**: two or more independently built artifacts behave compatibly according to the v0.1 contract
- **release blocker**: a defect class that stops promotion to the next release phase

---

## 5. Version baseline under test

All required test suites in this document are scoped to the following baseline unless explicitly stated otherwise:

- **Session core version:** `1`
- **Manifest schema version:** `1`
- **Bridge public API:** `/v0/*`
- **Primary carrier:** `h3`
- **Required capabilities:**
  - `tcp_relay`
  - `udp_relay_stream_fallback`
- **Optional but strongly recommended capability for v0.1:**
  - `udp_relay_datagram`

The test program MUST detect any silent drift away from these versioned assumptions.

---

## 6. Design principles for the validation program

### 6.1 Test the contract, not just the implementation details

The highest-priority tests are the ones that prove adherence to the frozen public contract:

- frame layout
- sequencing rules
- manifest schema
- token validation profile
- Bridge endpoint behavior

### 6.2 Prefer deterministic fixtures before large random test harnesses

Property testing and fuzzing are required, but deterministic fixture coverage comes first. Verta needs reproducible failures, not only high-volume random signal.

### 6.3 Failures must be diagnosable

Every required suite MUST produce artifacts that allow root-cause analysis:

- logs
- sanitized traces
- qlog where applicable
- binary fixture diffs
- CPU/memory snapshots for abuse scenarios where feasible

### 6.4 Security testing starts before release hardening

Security validation is not a separate future phase. Token confusion, parser robustness, resource bounds, webhook signature enforcement, and manifest verification MUST be tested continuously from the first implementation milestone.

### 6.5 Interop must be explicit and scheduled

Interop drift is common when one team changes a frame parser or endpoint assumption “just a little.” Verta MUST run scheduled interop suites across client, gateway, and Bridge permutations.

### 6.6 Release gates must include rollback drills

A protocol intended to survive adverse network conditions must prove not only forward deployment but also rollback and profile disable behavior.

---

## 7. Terminology used in this document

- **Reference client**: the canonical Rust client implementation for v0.1
- **Reference gateway**: the canonical Rust server/data-plane implementation for v0.1
- **Reference Bridge**: the canonical Rust Bridge implementation for v0.1
- **RW sandbox**: disposable Remnawave environment used for adapter and end-to-end integration testing
- **fixture**: a stable input/output artifact stored under version control
- **golden vector**: a known-good fixture used to assert compatibility over time
- **negative fixture**: malformed, tampered, or policy-invalid input that must be rejected
- **profile burn drill**: a controlled exercise in which a carrier persona/profile is assumed compromised or fingerprinted and must be withdrawn or rotated
- **policy epoch drift**: mismatch between Bridge/gateway/client understanding of the latest authoritative policy generation
- **steady-state flow**: normal operation after bootstrap and registration are complete

---

## 8. Test objectives

Verta v0.1 validation has nine primary objectives.

### 8.1 Objective A — protocol correctness

Prove that the implementation obeys the frozen wire and sequencing rules for:

- `CLIENT_HELLO`
- `SERVER_HELLO`
- `PING` / `PONG`
- `ERROR`
- `GOAWAY`
- `POLICY_UPDATE`
- `UDP_FLOW_OPEN` / `UDP_FLOW_OK` / `UDP_FLOW_CLOSE`
- `SESSION_STATS`
- `PATH_EVENT`
- `SESSION_CLOSE`
- `STREAM_OPEN` / `STREAM_ACCEPT` / `STREAM_REJECT`
- `UDP_STREAM_OPEN` / `UDP_STREAM_ACCEPT` / `UDP_STREAM_PACKET` / `UDP_STREAM_CLOSE`

### 8.2 Objective B — authorization correctness

Prove that only correctly signed and policy-valid manifests/tokens produce successful sessions, and that revoked or expired authorization is denied quickly and predictably.

### 8.3 Objective C — Bridge integrity

Prove that the Bridge:

- verifies webhook authenticity
- survives replay and reorder
- compiles manifests deterministically
- reconciles stale and fresh control-plane state safely
- applies metadata precedence correctly

### 8.4 Objective D — network resilience

Prove that the system remains functional or degrades safely under:

- packet loss
- jitter
- reorder
- MTU pressure
- UDP impairment
- NAT rebinding
- endpoint churn

### 8.5 Objective E — abuse containment

Prove that pre-auth floods, malformed inputs, over-sized frames, token spray, and device-slot abuse are bounded and observable.

### 8.6 Objective F — interoperability discipline

Prove that independently built artifacts remain compatible within the same version contract and reject incompatible inputs predictably.

### 8.7 Objective G — privacy-preserving observability

Prove that security and operational telemetry help diagnose incidents without leaking raw secrets or creating unnecessary stable identifiers.

### 8.8 Objective H — rollback readiness

Prove that operators can:

- revoke or rotate keys
- disable a profile
- drain a gateway cohort
- force manifest refresh
- recover from stale policy or stale JWKS conditions

### 8.9 Objective I — release readiness

Prove that alpha, beta, and public release phases have objective entry and exit criteria.

---

## 9. Traceability model

This plan MUST be traceable to earlier Verta documents.

### 9.1 Requirement source prefixes

The validation corpus SHOULD tag each test or suite with the source it protects.

Suggested prefix mapping:

- `WF-*` → Wire Format Freeze Candidate requirements
- `BR-*` → Bridge Spec requirements
- `TM-*` → Threat Model driven requirements
- `BP-*` → Blueprint architectural assumptions
- `OP-*` → operator and rollout requirements

### 9.2 Test case prefixes

Suggested test-id namespaces:

- `WC-*` → wire conformance
- `SM-*` → state machine and sequencing
- `AU-*` → authentication and token validation
- `MF-*` → manifest verification and policy logic
- `BG-*` → Bridge public API and domain logic
- `RW-*` → Remnawave adapter and sandbox integration
- `NT-*` → network adversity and transport tests
- `FP-*` → probing, fingerprinting, and profile adaptation drills
- `AB-*` → abuse, rate-limit, and resource containment
- `OB-*` → observability and privacy tests
- `PF-*` → performance and scalability tests
- `RL-*` → release gates and rollback drills
- `SC-*` → supply-chain and build integrity checks

### 9.3 Traceability requirement

Every high-severity threat or frozen wire rule MUST have at least one automated test or one explicitly scheduled manual exercise. If a risk cannot yet be automated, the gap MUST be documented with:

- why it is not automated yet
- what temporary control exists
- by which release phase automation is expected

---

## 10. Test pyramid and execution layers

Verta validation MUST run at multiple layers.

### 10.1 Layer 0 — static verification

Runs on every pull request.

Includes:

- formatting and linting
- compiler warnings as errors where practical
- unsafe-code review gates
- dependency vulnerability checks
- license checks
- API/schema diff checks for frozen public contracts
- generated-code drift checks if codegen is used

### 10.2 Layer 1 — deterministic local correctness

Runs on every pull request and every merge to main.

Includes:

- unit tests
- serializer/deserializer tests
- golden fixture tests
- property tests for canonical encodings
- signature-verification tests
- deterministic manifest compilation tests

### 10.3 Layer 2 — component integration

Runs on main and release branches, and optionally on selected pull requests.

Includes:

- client ↔ gateway handshake integration
- Bridge ↔ store integration
- Bridge ↔ signer integration
- Bridge ↔ Remnawave adapter integration with mocks
- session-token validation end-to-end

### 10.4 Layer 3 — end-to-end system tests

Runs in dedicated CI jobs and before releases.

Includes:

- full bootstrap/import flow
- device registration
- manifest fetch
- session establishment
- TCP relay
- UDP datagram relay when enabled
- UDP stream fallback
- session close and reconnect

### 10.5 Layer 4 — interoperability matrix

Runs on release candidates and nightly scheduled jobs.

Includes cross-version and cross-build combinations such as:

- client `main` vs gateway `release/*`
- client `release/*` vs gateway `main`
- Bridge `main` vs gateway `release/*`
- gateway with previous manifest compiler vs new client
- gateway with new signer keyset vs old cached JWKS client behavior

### 10.6 Layer 5 — security and abuse validation

Runs on scheduled CI, dedicated lab environments, and before phase promotion.

Includes:

- malformed frame storms
- token confusion tests
- replay attempts
- stale JWKS scenarios
- webhook forgery/replay
- bootstrap and refresh race conditions
- resource-exhaustion drills

### 10.7 Layer 6 — network chaos and operational drills

Runs in lab and staging environments, not only in conventional CI.

Includes:

- `tc netem` or equivalent impairment scenarios
- NAT rebinding drills
- profile disable/rollback drills
- key rotation drills
- regional policy-epoch lag simulations
- gateway draining and failover

### 10.8 Layer 7 — extended soak and canary validation

Runs for release candidates and production-like staging.

Includes:

- long-lived sessions
- repeated reconnect cycles
- concurrent TCP/UDP load
- memory leak detection
- descriptor leak detection
- log volume validation
- recovery after transient downstream outages

---

## 11. Required environments

Verta should use separate environments with clear purpose.

### 11.1 `ns-lab-unit`

Purpose:

- fast deterministic tests
- property tests
- parser tests

Characteristics:

- local or CI containerized
- no external dependencies required
- maximum reproducibility

### 11.2 `ns-lab-integration`

Purpose:

- component integration
- local signer/store integration
- token and manifest flow validation

Characteristics:

- ephemeral database
- local JWKS issuer
- deterministic fixture seeding

### 11.3 `ns-lab-rw-sandbox`

Purpose:

- disposable Remnawave integration tests
- webhook verification and reconciliation tests
- subscription import path tests

Characteristics:

- dedicated Remnawave sandbox instance
- sandbox API token
- sandbox webhook secret
- scripted user state transitions

### 11.4 `ns-lab-net-chaos`

Purpose:

- loss/jitter/reorder/MTU/NAT impairment tests
- path-change and UDP impairment studies

Characteristics:

- network namespaces, containers, or VM-based topology
- controlled impairment tooling
- packet capture/qlog support

### 11.5 `ns-lab-soak`

Purpose:

- long-running stability tests
- concurrency and resource leak detection

Characteristics:

- stable hardware and repeatable config
- runtime observability collection
- artifact retention for post-mortems

### 11.6 `ns-lab-redteam`

Purpose:

- adversarial and reverse-engineering exercises
- client tampering drills
- credential theft simulations

Characteristics:

- isolated from production secrets
- synthetic identities only
- controlled attack instrumentation

---

## 12. Canonical test artifacts

Verta MUST preserve a stable corpus of test artifacts.

### 12.1 Required artifact classes

1. **binary frame fixtures**  
   Frozen valid and invalid frame examples.

2. **manifest fixtures**  
   Valid, tampered, expired, malformed, and policy-conflicting manifests.

3. **token fixtures**  
   Valid, expired, wrong issuer, wrong audience, wrong algorithm, stale key, future `nbf`, replay-window edge cases.

4. **webhook fixtures**  
   Valid signed payloads, duplicate deliveries, reordered deliveries, forged payloads, wrong secret, truncated body, encoding edge cases.

5. **inventory fixtures**  
   Empty inventory, mixed health inventory, policy-epoch mismatch, drained cohort, disabled profile.

6. **network traces**  
   qlog, packet captures, impairment metadata, admission-flood metrics.

7. **observability snapshots**  
   sanitized logs, metrics exports, dashboard screenshots or serialized metric snapshots where practical.

### 12.2 Fixture namespace policy

The existing fixture namespace in the Freeze Candidate remains authoritative. Example already-frozen fixture ids include:

- `NS-FX-HELLO-001`
- `NS-FX-HELLO-ACK-001`

New fixtures SHOULD follow a stable namespace scheme such as:

- `NS-FX-WIRE-*`
- `NS-FX-MANIFEST-*`
- `NS-FX-TOKEN-*`
- `NS-FX-WEBHOOK-*`
- `NS-FX-RW-*`
- `NS-FX-NETCHAOS-*`

### 12.3 Artifact retention policy

For all failed release-gating runs, the system SHOULD retain at minimum:

- test logs
- qlog where applicable
- sanitized packet metadata or captures if enabled in lab
- CPU and memory summaries
- exact git revision and build metadata
- config digest / manifest digest / JWKS version used in the run

### 12.4 Privacy requirement for artifacts

Artifacts MUST NOT contain production secrets or unredacted personally identifying data. Synthetic identities are preferred in all automated suites.

---

## 13. Conformance suites

The core of this document is a set of conformance suites that must be implemented and run repeatedly.

### 13.1 Suite `WC` — wire conformance

Purpose:

- prove adherence to the frozen binary contract
- prevent silent drift in encoders/decoders

Mandatory coverage:

- canonical varint encoding rules
- fixed field order
- required frame envelope handling
- frame-size limits
- zero/empty-field semantics where frozen
- reserved-bit handling
- unknown-TLV handling for ignorable vs non-ignorable classes

Minimum required cases:

- `WC-HELLO-VALID-001`
- `WC-HELLO-MINMAX-002`
- `WC-HELLO-EMPTYTOKEN-003`
- `WC-HELLO-BADCARRIER-004`
- `WC-HELLO-NONCANON-005`
- `WC-SERVERHELLO-CAPMISMATCH-006`
- `WC-STREAMOPEN-TARGETDOMAIN-007`
- `WC-STREAMOPEN-IPV4-008`
- `WC-STREAMOPEN-IPV6-009`
- `WC-STREAMOPEN-RESERVEDBITS-010`
- `WC-UDPFLOWOPEN-VALID-011`
- `WC-ERROR-CODE-VALID-012`
- `WC-FRAME-TOOLARGE-013`
- `WC-UNKNOWN-FRAMETYPE-014`

Pass criteria:

- all frozen valid fixtures decode identically
- all malformed fixtures fail closed
- serializer output remains byte-stable for frozen fixtures unless compatibility review updates the fixture

### 13.2 Suite `SM` — session state machine

Purpose:

- prove legal and illegal sequencing behavior
- prevent state drift across client and gateway

Mandatory coverage:

- first control frame must be `CLIENT_HELLO`
- server cannot send post-handshake frames before `SERVER_HELLO`
- client cannot open relay streams before successful hello completion
- `GOAWAY` and `SESSION_CLOSE` behavior
- idle timeout behavior
- duplicate or reordered control frame handling where relevant

Minimum required cases:

- `SM-INIT-HELLO-001`
- `SM-PREHELLO-FRAME-REJECT-002`
- `SM-POSTGOAWAY-DRAIN-003`
- `SM-IDLETIMEOUT-004`
- `SM-DUPLICATE-UDP-FLOW-ID-005`
- `SM-STREAMACCEPT-WITHOUT-OPEN-006`
- `SM-SESSIONCLOSE-BOTH-SIDES-007`

Pass criteria:

- state transitions match the documented finite-state model
- invalid transitions do not leak resources or panic

### 13.3 Suite `AU` — auth and token verification

Purpose:

- prove that token and signature handling is strict and confusion-resistant

Mandatory coverage:

- algorithm allowlist enforcement
- issuer and audience binding
- clock-skew handling
- expiration and not-before boundaries
- JWKS rotation windows
- key-id mismatch
- missing claims
- duplicate claims or malformed claim types
- replay-suspected behavior where enabled by policy

Minimum required cases:

- `AU-TOKEN-VALID-001`
- `AU-TOKEN-EXPIRED-002`
- `AU-TOKEN-NBF-FUTURE-003`
- `AU-TOKEN-WRONGISS-004`
- `AU-TOKEN-WRONGAUD-005`
- `AU-TOKEN-WRONGALG-006`
- `AU-TOKEN-UNKNOWNKID-007`
- `AU-TOKEN-STALEJWKS-008`
- `AU-TOKEN-MALFORMED-009`
- `AU-TOKEN-REVOKEDSUB-010`

Pass criteria:

- unauthorized tokens are rejected before expensive downstream work
- error classification is correct and observable
- stale-key behavior is deterministic and policy-compliant

### 13.4 Suite `MF` — manifest verification and policy behavior

Purpose:

- prove manifest authenticity, parsing correctness, and policy precedence

Mandatory coverage:

- manifest signature verification
- digest verification where used
- schema validation
- unknown property handling
- expired manifest handling
- policy epoch comparison
- disabled profile behavior
- inventory mismatch and empty-inventory behavior

Minimum required cases:

- `MF-MANIFEST-VALID-001`
- `MF-MANIFEST-BADSIG-002`
- `MF-MANIFEST-EXPIRED-003`
- `MF-MANIFEST-SCHEMA-004`
- `MF-POLICYEPOCH-STALE-005`
- `MF-DISABLEDPROFILE-006`
- `MF-EMPTYINVENTORY-007`
- `MF-METADATA-PRECEDENCE-008`

Pass criteria:

- manifest rejection is strict and cheap
- compiled manifests are deterministic for identical inputs
- client behavior under stale or invalid manifest is safe and diagnosable

### 13.5 Suite `BG` — Bridge public API and domain logic

Purpose:

- prove correctness of Bridge bootstrap, refresh, manifest, and metadata flows

Mandatory coverage:

- endpoint auth context
- bootstrap replay/race handling
- device registration semantics
- refresh lifecycle
- idempotency
- pagination or cohort selection logic where applicable
- rate limiting
- public error-code mapping

Minimum required cases:

- `BG-BOOTSTRAP-VALID-001`
- `BG-BOOTSTRAP-RACE-002`
- `BG-REFRESH-ROTATE-003`
- `BG-DEVICE-LIMIT-004`
- `BG-RATELIMIT-005`
- `BG-MANIFEST-FETCH-006`
- `BG-REVOKED-USER-007`
- `BG-HWID-OPTIONAL-008`
- `BG-HWID-MISMATCH-POLICY-009`

Pass criteria:

- all Bridge public errors are explicit and test-covered
- idempotent paths remain idempotent under retry storms
- invalid clients are not able to escalate state

### 13.6 Suite `RW` — Remnawave adapter and sandbox integration

Purpose:

- prove safe interoperability with the external control plane

Mandatory coverage:

- adapter normalization from Remnawave source data
- signed webhook verification
- duplicate webhook handling
- reordered webhook handling
- polling and reconciliation after webhook loss
- `resolvedProxyConfigs` ingestion and mapping
- user status transitions
- metadata namespacing and merge precedence

Minimum required cases:

- `RW-WEBHOOK-VALID-001`
- `RW-WEBHOOK-FORGED-002`
- `RW-WEBHOOK-DUP-003`
- `RW-WEBHOOK-REORDER-004`
- `RW-POLL-RECOVER-005`
- `RW-RESOLVEDPROXY-MAP-006`
- `RW-USER-DISABLE-007`
- `RW-USER-REACTIVATE-008`
- `RW-METADATA-NAMESPACE-009`

Pass criteria:

- Bridge state converges correctly after loss, duplication, or stale snapshots
- no direct trust is placed in unsigned upstream data on public boundaries

### 13.7 Suite `NT` — network adversity and carrier behavior

Purpose:

- validate the transport stack under realistic impairments

Mandatory coverage:

- packet loss
- latency injection
- jitter
- reorder
- bandwidth clamp
- MTU reduction / PMTU pressure
- UDP blocked or degraded
- NAT rebinding and port change
- transient DNS or endpoint selection failure where relevant

Minimum required cases:

- `NT-LOSS-1PCT-001`
- `NT-LOSS-5PCT-002`
- `NT-JITTER-003`
- `NT-REORDER-004`
- `NT-MTU-1200-005`
- `NT-UDP-BLOCKED-FALLBACK-006`
- `NT-NAT-REBIND-007`
- `NT-ENDPOINT-FAILOVER-008`
- `NT-ALTERNATE-GATEWAY-009`

Pass criteria:

- system remains functional within expected degradation envelopes
- fallback behavior is explicit and observable
- no correctness bug appears only under impairment

### 13.8 Suite `FP` — probing, fingerprinting, and adaptation drills

Purpose:

- validate defenses and operational response around profile burn and probing pressure

Mandatory coverage:

- cheap pre-auth rejection
- behavior under malformed active probes
- absence of expensive or unique pre-auth paths
- profile disable and rollout rollback
- canary rollout of new profile
- manifest refresh after profile withdrawal

Minimum required cases:

- `FP-PREAUTH-PROBE-001`
- `FP-HELLO-MUTATION-STORM-002`
- `FP-CHEAP-REJECT-003`
- `FP-PROFILE-DISABLE-004`
- `FP-CANARY-ROLLOUT-005`
- `FP-BURN-ROLLBACK-006`

Pass criteria:

- no probe path causes unbounded work
- operators can remove a burned profile without breaking unrelated cohorts

### 13.9 Suite `AB` — abuse and resource containment

Purpose:

- prove that the system degrades safely under hostile demand

Mandatory coverage:

- pre-auth connection flood
- token spray
- frame-size abuse
- stream-id abuse
- target-denied abuse
- device-slot exhaustion
- refresh storm
- webhook flood with many invalid signatures

Minimum required cases:

- `AB-PREAUTH-FLOOD-001`
- `AB-TOKEN-SPRAY-002`
- `AB-FRAME-SIZE-003`
- `AB-STREAM-LIMIT-004`
- `AB-DEVICE-SLOT-005`
- `AB-REFRESH-STORM-006`
- `AB-WEBHOOK-SIGFAIL-007`
- `AB-RATELIMIT-EFFECTIVE-008`

Pass criteria:

- CPU/memory/file-descriptor growth remains bounded within configured budgets
- service remains observable and recoverable under sustained abuse

### 13.10 Suite `OB` — observability, secrecy, and privacy hygiene

Purpose:

- validate that telemetry supports diagnosis without becoming a liability

Mandatory coverage:

- log redaction
- absence of raw tokens in logs
- absence of raw webhook secrets in logs
- stable but privacy-aware session correlation strategy
- metric-cardinality guardrails
- qlog or trace scrubbing policy

Minimum required cases:

- `OB-LOG-REDACTION-001`
- `OB-NO-RAW-TOKEN-002`
- `OB-METRIC-CARDINALITY-003`
- `OB-QLOG-SCRUB-004`
- `OB-SESSION-CORRELATION-005`

Pass criteria:

- secret values are not recoverable from logs or standard telemetry artifacts
- metric cardinality remains within defined budgets

### 13.11 Suite `PF` — performance and scalability

Purpose:

- ensure Verta is not only correct but practical under realistic concurrency

Mandatory coverage:

- handshake latency baseline
- steady-state TCP throughput
- UDP relay latency and packet handling
- memory per live session
- CPU per handshake
- Bridge manifest/token endpoint capacity
- concurrent session churn behavior

Minimum required cases:

- `PF-HANDSHAKE-BASE-001`
- `PF-TCP-THROUGHPUT-002`
- `PF-UDP-RELAY-003`
- `PF-MEMORY-PER-SESSION-004`
- `PF-CPU-HANDSHAKE-005`
- `PF-BRIDGE-QPS-006`
- `PF-CONCURRENT-CHURN-007`
- `PF-SOAK-24H-008`

Pass criteria:

- no catastrophic regression relative to the current baseline or prior release candidate
- performance numbers are published with environment metadata and cannot be cherry-picked from a single “best run”

### 13.12 Suite `RL` — release and rollback drills

Purpose:

- validate production-like operational safety

Mandatory coverage:

- signer key rotation
- JWKS propagation timing
- gateway drain and cohort disable
- profile rollback
- forced manifest refresh
- stale-cache detection and recovery
- Remnawave sandbox outage behavior

Minimum required cases:

- `RL-KEY-ROTATE-001`
- `RL-JWKS-PROPAGATE-002`
- `RL-GATEWAY-DRAIN-003`
- `RL-PROFILE-ROLLBACK-004`
- `RL-MANIFEST-FORCE-005`
- `RL-STALE-CACHE-006`
- `RL-RW-OUTAGE-007`

Pass criteria:

- operators can restore a safe state within predefined operational runbooks
- rollback paths are tested, not merely documented

### 13.13 Suite `SC` — supply-chain and release integrity

Purpose:

- reduce the risk of shipping the right code the wrong way

Mandatory coverage:

- reproducible build checks where feasible
- signed artifacts
- SBOM generation if adopted
- dependency review workflow
- no-debug-secrets in release builds
- version stamping and provenance checks

Minimum required cases:

- `SC-SIGN-BUILD-001`
- `SC-PROVENANCE-002`
- `SC-NO-DEBUG-SECRETS-003`
- `SC-DEP-REVIEW-004`
- `SC-RELEASE-MANIFEST-005`

Pass criteria:

- release artifacts are attributable, inspectable, and not built from ambiguous state

---

## 14. Detailed wire and parser test requirements

### 14.1 Canonical encoding tests

The encoder/decoder test corpus MUST include:

- minimum-length varint examples
- non-canonical varint encodings that must be rejected
- zero-length strings/bytes where allowed
- zero-length strings/bytes where forbidden
- oversized declared lengths
- declared-length shorter/longer than actual payload

### 14.2 Envelope tests

The generic frame envelope tests MUST cover:

- valid envelope parsing
- truncated envelope
- frame length too large
- reserved flag bits if frozen as zero
- invalid context for frame type
- unexpected control frame on relay stream
- unexpected relay preamble on control stream

### 14.3 `CLIENT_HELLO` tests

Mandatory checks:

- valid fixture decode/encode round-trip
- `MinVersion > MaxVersion`
- unsupported `CarrierKind`
- empty token
- duplicated capabilities
- malformed opaque lengths
- non-canonical varints
- too many capabilities beyond advertised limit
- unknown capability handling according to policy

### 14.4 `SERVER_HELLO` tests

Mandatory checks:

- selected capabilities must be subset of client-offered capabilities
- profile binding and epoch handling if carried by hello metadata
- mismatched carrier selection rejection
- invalid stats mode values
- invalid datagram mode values

### 14.5 Relay preamble tests

Mandatory checks for `STREAM_OPEN`, `STREAM_ACCEPT`, `STREAM_REJECT`:

- domain target with valid port
- IPv4 target with valid port
- IPv6 target with valid port
- unsupported target type rejection
- reserved bits zero enforcement
- target length mismatch rejection
- target-denied policy path
- flow limit reached path

### 14.6 UDP tests

Mandatory checks for `UDP_FLOW_OPEN`, `UDP_FLOW_OK`, `UDP_FLOW_CLOSE`, and `UDP_STREAM_*` fallback frames:

- valid open and close lifecycle
- duplicate flow id rejection or idempotent handling as documented
- unsupported datagram mode fallback
- malformed packet length in `UDP_STREAM_PACKET`
- closure of unknown flow id
- datagram payload framing rules

### 14.7 Error-path tests

Mandatory checks:

- every frozen error code must have at least one test
- unknown error code handling must be deterministic
- `FRAME_TOO_LARGE`, `AUTH_FAILED`, `TOKEN_EXPIRED`, `PROFILE_MISMATCH`, `DRAINING`, `UDP_DATAGRAM_UNAVAILABLE` require explicit tests

---

## 15. Property testing requirements

Property testing SHOULD be used for high-value parsers and state transforms.

### 15.1 Suggested property targets

- canonical varint round-trip
- frame encode/decode round-trip under valid generated values
- deterministic manifest compilation from identical normalized inputs
- metadata precedence associativity/override invariants
- token-claim parser handling of optional/unknown fields
- stream/flow id uniqueness invariants

### 15.2 Property testing guardrails

Generated inputs MUST still respect bounded sizes. Property tests are not an excuse to generate impractically huge objects that slow CI without increasing coverage.

---

## 16. Fuzzing requirements

Fuzzing is mandatory for v0.1.

### 16.1 Minimum fuzz targets

At minimum, Verta MUST fuzz:

- frame envelope decoder
- `CLIENT_HELLO` decoder
- `SERVER_HELLO` decoder
- relay preamble decoders
- UDP fallback frame decoder
- manifest parser
- token claim parsing wrapper or token-verification boundary
- Bridge public request decoders
- webhook verification and payload-decoding path

### 16.2 Fuzzing objectives

The fuzzing program should detect:

- panics
- integer overflows/underflows
- unchecked allocations
- catastrophic CPU blowups on malformed input
- state-machine corruption from malformed sequences
- parser inconsistencies across debug/release builds

### 16.3 Fuzzing execution policy

Suggested policy:

- smoke fuzz on pull requests for a bounded time budget
- longer fuzz campaigns on nightly or dedicated runners
- corpus minimization and regression preservation after every crash

### 16.4 Fuzzing artifacts

Every fixed bug discovered by fuzzing MUST add:

- the minimized reproducer
- a regression test
- a note in the security or defect tracker if the issue had security implications

---

## 17. Concurrency and async-runtime validation

Verta is an async Rust system. Concurrency bugs may not show up under ordinary unit tests.

### 17.1 Required concurrency targets

The team SHOULD test:

- token cache refresh races
- manifest refresh races
- session shutdown vs stream-open races
- policy-epoch update vs live session admission races
- Bridge reconciliation races between webhook ingestion and polling
- gateway drain vs new session races

### 17.2 Suggested techniques

Possible techniques include:

- deterministic scheduler tests where practical
- reduced-state concurrency models
- `loom`-style concurrency verification for selected core primitives
- lock-order assertions and lock-contention metrics

### 17.3 Required outcomes

No race condition may result in:

- accepting invalid authorization
- corrupting device slot counts
- double-free or panic
- unbounded stale state retention
- inconsistent keyset adoption within one process without explicit policy

---

## 18. Bridge and Remnawave-specific validation

This section expands the `BG` and `RW` suites because the non-fork strategy depends on this boundary being reliable.

### 18.1 Bootstrap flow tests

The test program MUST validate:

- import/bootstrap with valid bootstrap credential
- duplicate bootstrap attempts from same device
- simultaneous bootstrap on two devices competing for device slot limits
- bootstrap replay after successful completion
- bootstrap after account disable
- bootstrap with stale policy epoch or stale app config

### 18.2 Refresh lifecycle tests

The test program MUST validate:

- normal refresh rotation
- refresh token reuse detection if rotation policy requires one-time use
- refresh after account disable
- refresh after profile disable
- refresh after manifest signing key rotation

### 18.3 Webhook verification tests

Mandatory scenarios:

- valid signature
- wrong signature
- missing signature
- valid signature but replayed timestamp or nonce if present
- body mutation after signing
- duplicate deliveries
- delivery reorder
- partial delivery or parse failure

### 18.4 Polling and reconciliation tests

Mandatory scenarios:

- webhook dropped, polling later restores correct state
- polling sees stale upstream snapshot
- webhook says user revoked but cache still contains active manifest
- webhook reactivation after prior revoke
- partial adapter failure during reconciliation

### 18.5 `resolvedProxyConfigs` mapping tests

The adapter SHOULD validate:

- typed inputs are normalized correctly
- unsupported families are ignored or mapped according to policy
- malformed upstream config does not panic the compiler
- inventory and profile derivation are deterministic

### 18.6 Metadata strategy tests

Mandatory checks:

- namespaced keys do not collide with unrelated metadata
- Verta-specific overrides apply in the documented precedence order
- malformed metadata values are rejected or ignored safely
- user metadata cannot grant impossible capabilities outside allowed policy

---

## 19. End-to-end interoperability matrix

Interop testing must be explicit. A single reference implementation still benefits from permutation testing across revisions and roles.

### 19.1 Matrix axes

The interop matrix SHOULD vary:

- client build revision
- gateway build revision
- Bridge build revision
- JWKS generation
- policy epoch
- datagram available vs unavailable
- profile enabled vs withdrawn
- Remnawave sandbox state

### 19.2 Minimum matrix combinations

At minimum, release-candidate validation SHOULD run:

1. client `main` ↔ gateway `main`
2. client `release-candidate` ↔ gateway `release-candidate`
3. client `previous-rc` ↔ gateway `current-rc`
4. client `current-rc` ↔ gateway `previous-rc`
5. current client ↔ current gateway ↔ previous Bridge manifest compiler
6. current client ↔ previous JWKS cache view ↔ rotated signer state
7. current client ↔ current gateway with datagrams disabled
8. current client ↔ current gateway with datagrams enabled

### 19.3 Mandatory interop questions

The interop matrix MUST answer:

- do same-version artifacts remain compatible across independent builds?
- do additive non-critical fields remain safely ignored where allowed?
- do stale-but-valid caches fail predictably instead of corrupting state?
- does policy-epoch drift surface clearly in telemetry and user-facing error paths?

---

## 20. Network-chaos and transport test program

Verta is expected to operate on imperfect networks. The lab must therefore simulate bad conditions deliberately.

### 20.1 Impairment profiles

The team SHOULD maintain named impairment profiles such as:

- `clean`
- `loss-1`
- `loss-5`
- `jitter-low`
- `jitter-high`
- `reorder-2`
- `reorder-10`
- `mtu-1200`
- `udp-blocked`
- `udp-flaky`
- `slow-start-wan`
- `nat-rebind-midflow`

### 20.2 Required measurements per impairment run

Each impairment run SHOULD record:

- connection success rate
- handshake latency percentiles
- TCP stream completion rate
- UDP packet delivery characteristics where applicable
- fallback activation rate
- reconnect success rate
- error code distribution
- CPU and memory summaries
- qlog or packet trace where feasible

### 20.3 NAT rebinding tests

Mandatory scenarios:

- port-only change while session remains otherwise valid
- address and port change
- rebinding during idle period
- rebinding during active TCP relay
- rebinding during active UDP relay

Expected result:

- behavior must match carrier capabilities and policy; unsupported recovery paths must fail predictably, not corrupt state

### 20.4 UDP impairment tests

Mandatory scenarios:

- UDP fully blocked before session start
- UDP degraded after successful startup
- intermittent datagram loss with fallback available
- datagram path disabled by policy

Expected result:

- client and gateway must converge on the documented fallback behavior and surface that behavior in telemetry

---

## 21. Active probing and profile-burn drills

Verta is not promising magical invisibility, but it does need operational discipline under probing pressure.

### 21.1 Probe simulation goals

The lab SHOULD simulate:

- malformed hello storms
- random frame injection pre-auth
- repeated short-lived connection attempts with mutated tokens
- partial frame truncation
- invalid carrier metadata
- unsupported capability combinations

### 21.2 Required assertions

The system MUST demonstrate:

- no panics
- no expensive pre-auth path triggered by trivial mutations
- rate limits and admission budgets remain effective
- logs and metrics identify the probe pattern without storing raw secrets

### 21.3 Profile-burn drill

At least once before public beta, the team SHOULD conduct a profile-burn drill:

1. declare one active profile “burned”
2. disable it in policy
3. recompile manifests
4. force or induce refresh for a canary cohort
5. observe recovery metrics
6. verify unaffected cohorts continue to function if assigned other profiles
7. document time-to-mitigation and operator pain points

### 21.4 Canary rollout drill

At least once before public beta, the team SHOULD conduct a canary rollout of a new profile to a small cohort and verify:

- opt-in scope is respected
- rollback is quick
- metrics and logs identify the cohort clearly without exposing raw user identity

---

## 22. Abuse, rate-limit, and resource-budget testing

### 22.1 Gateway admission abuse

The gateway MUST be tested against:

- pre-auth connection floods
- HELLO floods with invalid tokens
- valid-format but expired-token floods
- oversized frame floods
- stream-open floods after successful auth
- denied-target floods

Measurements MUST include:

- CPU per handshake path
- memory growth
- file-descriptor consumption
- rate-limit effectiveness
- time-to-recovery after flood stops

### 22.2 Bridge abuse tests

The Bridge MUST be tested against:

- bootstrap credential spray
- refresh storm from one user and many users
- device registration abuse
- webhook invalid-signature flood
- manifest fetch spikes
- polling amplification risk under upstream instability

Measurements MUST include:

- request rejection ratios
- latency percentiles under abuse
- queue lengths
- DB connection pool health
- cache hit/miss changes

### 22.3 Resource budgets

Every release candidate SHOULD document configured budgets such as:

- max concurrent pre-auth sessions per process
- max relay streams per session
- max UDP flows per session
- max frame size
- max token validation cache size
- max Bridge request body size
- max per-user device slots

Tests MUST verify that these budgets are enforced.

---

## 23. Observability and privacy test program

### 23.1 Logging requirements

Tests MUST verify that logs:

- include enough identifiers to correlate events safely
- do not log raw bearer tokens
- do not log refresh credentials
- do not log raw webhook secret material
- do not log full manifest contents unless explicitly enabled in a safe synthetic environment

### 23.2 Metrics requirements

Tests MUST verify that metrics:

- expose cardinality within budget
- include key counters for auth failures, replay suspicion, manifest verification failures, webhook signature failures, and profile mismatch
- do not explode cardinality due to user-controlled labels

### 23.3 Tracing requirements

Tests SHOULD verify that traces:

- can correlate client request → Bridge response → gateway session outcome in synthetic environments
- scrub or hash sensitive identifiers consistently
- do not attach raw tokens as span attributes

### 23.4 qlog and packet artifact requirements

If qlog or packet capture is collected, the test program MUST verify:

- artifact location and retention are controlled
- sensitive annotation fields are minimized
- qlog is used primarily in lab/staging, not by default in production

---

## 24. Performance and scalability program

Performance testing is not only about peak throughput. It must also expose regressions in correctness, resource use, and operational stability.

### 24.1 Measurement philosophy

All performance reports SHOULD include:

- git revision
- build mode
- OS and kernel version where relevant
- CPU model and core count
- memory size
- impairment profile used
- whether datagrams were enabled
- number of concurrent clients
- test duration

### 24.2 Core KPIs

The performance program SHOULD track at least:

- handshake latency p50/p95/p99
- manifest fetch latency p50/p95/p99
- token issuance latency p50/p95/p99
- TCP relay throughput under clean and impaired networks
- UDP relay latency and effective packet rate
- memory per session at multiple concurrency levels
- Bridge API throughput and error rate
- gateway CPU per accepted session and per rejected session
- reconnect success after impairment events

### 24.3 Regression policy

Every release candidate SHOULD compare results against:

- last main-branch baseline
- last release candidate
- known regression threshold per KPI

If a regression exceeds threshold, it MUST be triaged before promotion. Not every regression is a blocker, but every major regression needs an explicit decision record.

### 24.4 Soak tests

The v0.1 release program SHOULD include soak tests such as:

- 24-hour mixed TCP/UDP session load
- repeated reconnect cycles over many hours
- periodic key refresh / manifest refresh during load
- gateway drain and re-admission during active load

Required outcomes:

- no unbounded memory growth
- no descriptor leak
- acceptable log growth
- no collapse after hours of churn

---

## 25. Platform and build matrix

Even for v0.1, Verta should not only be tested on one machine profile.

### 25.1 Recommended platform matrix

At minimum, the team SHOULD exercise:

- Linux x86_64
- Linux ARM64 if deployment targets require it
- Windows client build validation if Windows is a first-class desktop target
- macOS client build validation if targeted

### 25.2 Minimum expectations by component

- **Gateway**: Linux primary, with the exact deployment target treated as authoritative
- **Bridge**: Linux primary
- **Client**: every officially supported desktop or mobile target must have at least smoke and bootstrap coverage before claiming support

### 25.3 Cross-build expectations

Release artifacts MUST be version-stamped and distinguishable. The interop matrix should never confuse “works on my machine” with actual release compatibility.

---

## 26. CI/CD pipeline requirements

### 26.1 Pull request gates

Every pull request touching protocol, auth, Bridge, or policy logic SHOULD run:

- static verification
- deterministic unit/fixture tests
- selected property tests
- quick smoke fuzzers
- API/schema diff checks

### 26.2 Merge-to-main gates

Every merge to main SHOULD run:

- full deterministic suites
- component integration suites
- selected end-to-end flows
- signed fixture regeneration checks if fixture changes are expected

### 26.3 Nightly scheduled gates

Nightly or scheduled runners SHOULD run:

- extended fuzzing
- RW sandbox integration
- net-chaos profiles
- interop matrix subset
- long-running soak subset

### 26.4 Release-candidate gates

A release candidate MUST run:

- all mandatory conformance suites
- full interop matrix required for the target phase
- security and abuse suites
- rollback drills
- performance baseline capture
- artifact signing and provenance checks

### 26.5 CI artifact policy

CI must persist enough context to reproduce failures, but sensitive artifacts should remain restricted and synthetic.

---

## 27. Release phases and promotion criteria

### 27.1 Alpha entry criteria

Before alpha begins, Verta MUST have:

- frozen v0.1 wire contract
- reference client, gateway, and Bridge capable of happy-path end-to-end flow
- deterministic unit and fixture suites wired into CI
- basic fuzzing targets created
- manifest and token verification paths implemented
- sandbox Remnawave integration environment available

### 27.2 Alpha exit criteria

To exit alpha, Verta SHOULD demonstrate:

- all critical wire conformance tests passing
- all critical auth and manifest tests passing
- Bridge webhook verification and reconciliation tests passing
- no open critical parser panic or token confusion bugs
- at least one successful net-chaos campaign with documented findings

### 27.3 Beta entry criteria

Before beta begins, Verta MUST have:

- all mandatory conformance suites operational
- interop matrix automated for at least the minimum combinations
- rate limiting and resource budgets enforced and tested
- observability redaction tests passing
- rollback drill performed at least once in staging

### 27.4 Beta exit criteria

To exit beta, Verta SHOULD demonstrate:

- no known critical release blockers
- stable soak results across multiple runs
- profile-burn drill completed with documented time-to-mitigation
- signer/JWKS rotation drill completed successfully
- Remnawave outage/reconciliation scenarios completed successfully
- no unresolved high-severity privacy leak in logs/metrics/traces

### 27.5 Public release criteria

Before public release, Verta MUST have:

- reproducible and attributable release artifacts
- runbooks for rollback, key rotation, profile disable, and stale policy recovery
- documented support matrix
- clear operator guidance on what is and is not promised about censorship resistance
- test coverage report tied back to frozen contracts and threat register

---

## 28. Defect taxonomy and triage

Defects should not be treated as one undifferentiated backlog.

### 28.1 Suggested severity classes

- **S0** — release-blocking critical security or data-plane correctness failure
- **S1** — severe security, compatibility, or stability issue requiring immediate fix
- **S2** — important but contained issue; can block promotion depending on scope
- **S3** — non-critical issue or test debt
- **S4** — cosmetic or documentation-only issue

### 28.2 Release-blocking defect classes

The following SHOULD be treated as release blockers until explicitly waived:

- parser panic or memory corruption on hostile input
- acceptance of invalid or forged token/manifest
- Bridge accepting unsigned or improperly verified webhook content
- silent wire incompatibility within the same frozen version
- inability to revoke or rotate signing material safely
- log leakage of raw bearer credentials in normal operation
- unbounded CPU/memory growth under straightforward abuse scenario
- broken rollback of a carrier profile or gateway cohort

### 28.3 Triage requirement

Every failed release-gating suite MUST produce:

- owning component
- affected severity
- reproduction artifact pointer
- suspected requirement source (`WF`, `BR`, `TM`, etc.)
- decision on block / defer / waive

---

## 29. Manual exercises that still matter

Even with strong automation, some validation must remain manual or semi-manual for v0.1.

### 29.1 Recommended manual exercises

- walkthrough of client bootstrap UX against RW sandbox
- operator rollback drill using runbook only
- inspection of logs and traces during an abuse event
- reverse-engineering sanity pass against the client package to identify obvious secret exposure or debug leftovers
- staged profile disable with real humans following documented procedure

### 29.2 Documentation requirement

Every manual exercise MUST produce:

- date
- build revision
- operator(s)
- scenario description
- deviations from expected behavior
- follow-up bugs or runbook updates

---

## 30. AI coding agent guardrails for test generation

Verta is a good candidate for AI-assisted implementation, but test generation must be disciplined.

### 30.1 Mandatory instructions for AI test authors

AI coding agents MUST be instructed to:

- treat the Freeze Candidate as the authoritative wire contract
- never “simplify” signature checks in production code
- generate tests for negative paths, not only happy paths
- preserve fixture ids and avoid rewriting them casually
- produce explicit regression tests for every security-relevant bug fix
- avoid embedding real secrets in tests
- avoid asserting unstable timing values unless the test is explicitly a performance test

### 30.2 Forbidden AI shortcuts

AI coding agents MUST NOT:

- bypass auth to make integration tests easier
- weaken validation under “debug mode” unless tightly scoped and impossible to ship accidentally
- remove rate limiting or budget checks just to reduce test flakiness
- silently update frozen fixture bytes without human review
- skip malformed input coverage for parsers and public endpoints

### 30.3 Review expectation

Security-sensitive tests and fixture changes still require human review.

---

## 31. Deferred but important validation backlog

These items are intentionally recorded now so they stay visible.

### 31.1 Advanced protocol-assurance work

- formal state-machine models
- symbolic protocol analysis
- differential testing against future independent implementations
- verified parser subsets for the most security-sensitive decoders

### 31.2 Advanced network-lab work

- multi-region WAN emulation
- mobile-radio transition scenarios
- captive-portal interference studies
- carrier-grade NAT path studies at larger scale
- ISP/ASN-specific impairment replay where ethically and legally appropriate

### 31.3 Advanced abuse-economics work

- cost-of-probe modeling
- large-scale account sharing and reseller abuse simulations
- adversarial traffic shaping studies
- behavioral anomaly detection with privacy review

### 31.4 Advanced privacy work

- telemetry privacy budgets
- operator analytics minimization reviews
- better unlinkability between cohorts or gateway groups

### 31.5 Advanced release integrity work

- transparency logs for client releases
- stronger provenance attestation
- reproducible-build guarantees for all targets

---

## 32. Acceptance criteria for this document itself

This plan is considered usable only when:

1. all conformance suite namespaces are reflected in the repository test layout or issue tracker  
2. every frozen wire rule has a mapped automated or scheduled validation path  
3. the RW sandbox exists or has an approved implementation plan  
4. the CI pipeline has defined entry points for deterministic, fuzz, interop, and release-gating runs  
5. at least one rollback drill and one profile-burn drill are scheduled before beta exit  

---

## 33. Immediate implementation priorities

If the team starts implementing the validation program now, the recommended order is:

1. fixture harness for frozen wire examples  
2. manifest and token validation tests  
3. Bridge webhook verification and reconciliation tests  
4. end-to-end happy-path and revoked-user-path tests  
5. parser fuzzing targets  
6. net-chaos lab for loss/MTU/UDP-blocked scenarios  
7. abuse and budget tests  
8. rollback and key-rotation drills  
9. extended soak and release-candidate dashboards  

This ordering produces the best risk reduction early.

---

## 34. Final conclusion

Verta should be treated as an engineering system that earns trust through evidence, not optimism.

A protocol aimed at speed, adaptability, and operational resilience must prove more than connectivity. It must prove that:

- its wire behavior is stable
- its authorization boundary is strict
- its Bridge is resilient to stale and hostile control-plane inputs
- its gateway rejects abuse cheaply
- its client/gateway/Bridge remain interoperable over time
- its observability is useful but not reckless
- its rollback story works when the network gets ugly

That is what this document is for.

It is not a checklist to run once before launch.
It is the repeatable validation program that turns Verta from an idea into a protocol stack that can survive real use.

---

## Appendix A — Example repository test layout

```text
workspace/
  crates/
    ns-proto-core/
      tests/
        wc_hello.rs
        wc_stream_open.rs
        sm_session.rs
        fuzz_regressions/
    ns-gateway/
      tests/
        au_token.rs
        nt_udp_fallback.rs
        ab_preauth_flood.rs
    ns-bridge-api/
      tests/
        bg_bootstrap.rs
        bg_refresh.rs
    ns-bridge-webhooks/
      tests/
        rw_webhook_sig.rs
        rw_webhook_reorder.rs
    ns-bridge-domain/
      tests/
        mf_manifest_compile.rs
        mf_policy_epoch.rs
  fixtures/
    wire/
    manifest/
    token/
    webhook/
    rw/
    netchaos/
  labs/
    rw-sandbox/
    net-chaos/
    soak/
```

---

## Appendix B — Example release-gating dashboard headings

A useful release-gating dashboard could expose:

- wire conformance pass rate
- auth/manifest pass rate
- webhook verification pass rate
- interop matrix summary
- abuse-test budget compliance
- handshake latency trend
- memory-per-session trend
- soak-test leak indicators
- key rotation drill status
- profile-burn drill status

---

## Appendix C — Minimal must-have suite before serious coding acceleration

Before turning multiple AI agents loose on the codebase, the project SHOULD already have:

- frozen fixture harness
- token verification tests
- manifest signature tests
- webhook signature tests
- state-machine smoke tests
- at least one parser fuzz target
- CI schema diff checks

Without these, the project will likely accumulate silent incompatibilities and fragile “fixes” that are hard to unwind later.
