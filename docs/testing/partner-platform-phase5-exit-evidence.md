# CyberVPN Partner Platform Phase 5 Exit Evidence

**Date:** 2026-04-18  
**Status:** Phase 5 gate evidence pack  
**Purpose:** define the canonical automated evidence, service-access replay evidence, and sign-off checklist required to declare `Phase 5` complete.

---

## 1. Gate Role

This document is the concrete exit-evidence companion to:

- [../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md](../plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md)
- [../plans/2026-04-18-partner-platform-phase-5-execution-ticket-decomposition.md](../plans/2026-04-18-partner-platform-phase-5-execution-ticket-decomposition.md)
- [../plans/2026-04-17-partner-platform-operational-readiness-package.md](../plans/2026-04-17-partner-platform-operational-readiness-package.md)
- [partner-platform-phase5-service-access-replay-pack.md](partner-platform-phase5-service-access-replay-pack.md)

It converts the generic `Phase 5` readiness requirements into a named closure package.

This pack is complete only when:

1. required backend tests pass;
2. the committed OpenAPI export includes the frozen `Phase 5` surface;
3. the service-access replay harness produces deterministic output and explicit channel-parity mismatch explanations;
4. cross-channel parity evidence proves the same service-access truth across official web and at least one non-web consumption channel;
5. named owners sign off or explicitly record residual non-blocking gaps.

Current execution status for the 2026-04-18 closure run:

- targeted backend `Phase 5` verification pack passed with `22 passed in 84.31s`;
- targeted backend lint passed with `All checks passed!`;
- committed OpenAPI export was refreshed successfully for the frozen `Phase 5` surface;
- deterministic service-access replay contract pack passed with `2 passed in 1.94s`;
- `Phase 5` cross-channel e2e gate pack passed with `4 passed in 8.78s`.

---

## 2. Canonical Phase 5 Evidence Scope

`Phase 5` exit evidence must prove all of the following:

- `service_identities`, `entitlement_grants`, `provisioning_profiles`, `device_credentials`, and `access_delivery_channels` remain separate canonical entity families;
- service access is driven by entitlement grants rather than loosely coupled customer-row shortcuts;
- purchase context and service-consumption context remain separately explainable;
- legacy provider references survive only as provenance, not as the new source of truth;
- shared service-state APIs remain realm-aware and channel-neutral;
- support and admin observability can inspect service access without inferring it from storefront login state;
- deterministic replay can surface structural service-access drift and cross-channel parity mismatches.

Important clarification:

- `Phase 5` does not require full mobile, desktop, Telegram, or partner API rollout;
- `Phase 5` does require canonical contracts and runtime proof for channel-neutral service access;
- `Phase 5` does require cross-channel parity evidence across at least web and one non-web channel.

---

## 3. Required Automated Evidence

## 3.1 Backend Gate Tests

The canonical backend gate command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_service_identity_openapi_contract.py \
  backend/tests/contract/test_entitlement_grant_openapi_contract.py \
  backend/tests/contract/test_access_delivery_openapi_contract.py \
  backend/tests/contract/test_phase5_api_surface_contract.py \
  backend/tests/contract/test_phase5_service_access_replay_pack.py \
  backend/tests/contract/test_partner_platform_api_conventions.py \
  backend/tests/integration/test_service_identity_foundations.py \
  backend/tests/integration/test_entitlement_grants.py \
  backend/tests/integration/test_access_delivery_channels.py \
  backend/tests/integration/test_current_service_state.py \
  backend/tests/integration/test_service_access_observability.py \
  backend/tests/integration/test_service_access_legacy_migration.py \
  backend/tests/e2e/test_phase5_service_access_foundations.py \
  -q
```

Expected result:

- all tests pass;
- no skipped tests are accepted without a written explanation;
- failures block `Phase 5` closure.

## 3.2 Lint And Contract Hygiene

The canonical backend lint command is:

```bash
backend/.venv/bin/ruff check \
  backend/src/application/services/phase5_service_access_replay.py \
  backend/scripts/build_phase5_service_access_replay_pack.py \
  backend/scripts/print_phase5_service_access_replay_summary.py \
  backend/tests/contract/test_phase5_api_surface_contract.py \
  backend/tests/contract/test_phase5_service_access_replay_pack.py \
  backend/tests/e2e/test_phase5_service_access_foundations.py
```

The canonical OpenAPI export command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
backend/.venv/bin/python backend/scripts/export_openapi.py
```

The exported file `backend/docs/api/openapi.json` remains the frozen contract source for downstream consumers.

## 3.3 Replay And Cross-Channel Parity Evidence

The canonical replay and parity contract command is:

```bash
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=0123456789abcdef0123456789abcdef \
CRYPTOBOT_TOKEN=test-cryptobot-token \
SKIP_TEST_DB_BOOTSTRAP=1 \
backend/.venv/bin/pytest --no-cov \
  backend/tests/contract/test_phase5_service_access_replay_pack.py \
  backend/tests/e2e/test_phase5_service_access_foundations.py \
  -q
```

The harness must prove:

- identical service-access snapshots with fixed `replay_generated_at` produce identical replay packs;
- the generated pack contains explicit mismatch rows and `blocking_mismatches`;
- channel parity output can distinguish structural drift from channel-expectation drift;
- cross-channel runtime proof exists for official web and at least one non-web consumption channel;
- the compact summary script can be attached to evidence archives.

---

## 4. Required Artifact Set

The following artifacts must be attached to the evidence archive:

| Artifact | Source | Mandatory |
|---|---|---|
| backend gate test output | pytest command transcript | yes |
| backend lint output | ruff transcript | yes |
| committed OpenAPI export diff | `backend/docs/api/openapi.json` | yes |
| service-access replay CLI transcript | builder and summary script output | yes |
| service-access replay pack JSON | generated evidence file | yes |
| cross-channel parity evidence | e2e output and linked API payloads | yes |
| divergence register | issue list for non-blocking residuals | yes |
| sign-off block | named approvers | yes |

Recommended archive location:

```text
docs/evidence/partner-platform/<YYYY-MM-DD>/phase5-gate/
```

---

## 5. Acceptance Mapping

The `Phase 5` completion gate is considered satisfied only when the evidence maps to the frozen requirements below.

| Requirement | Evidence source |
|---|---|
| service identities remain first-class and provider-scoped | `test_service_identity_foundations.py`, `test_service_identity_openapi_contract.py` |
| entitlements remain canonical and lifecycle-driven | `test_entitlement_grants.py`, `test_entitlement_grant_openapi_contract.py` |
| delivery channels and device credentials remain separate from entitlement state | `test_access_delivery_channels.py`, `test_access_delivery_openapi_contract.py` |
| current service-state contracts are realm-aware and channel-neutral | `test_current_service_state.py`, `test_phase5_api_surface_contract.py` |
| support and admin observability can inspect purchase context versus service consumption | `test_service_access_observability.py`, `test_phase5_service_access_foundations.py` |
| legacy migration preserves provenance without re-centering legacy truth | `test_service_access_legacy_migration.py`, `test_phase5_api_surface_contract.py` |
| deterministic replay exposes structural and parity drift | `test_phase5_service_access_replay_pack.py`, attached replay pack JSON |
| exported OpenAPI contains the frozen `Phase 5` surface | committed `openapi.json`, `test_phase5_api_surface_contract.py` |

## 5.1 Closure Run Record

The closure run attached to this document produced the following results:

| Evidence item | Result |
|---|---|
| targeted backend `Phase 5` verification pack | `22 passed in 84.31s` |
| backend targeted lint | `All checks passed!` |
| service-access replay contract pack | `2 passed in 1.94s` |
| `Phase 5` cross-channel e2e gate pack | `4 passed in 8.78s` |
| OpenAPI export | refreshed successfully, frozen schema confirmed |

---

## 6. Divergence Policy

Allowed non-blocking residuals:

- unrelated channel-adapter rollout work that consumes frozen `Phase 5` contracts later;
- repo-wide security advisories unrelated to the touched `Phase 5` backend paths;
- human sign-off still pending after automated closure evidence is complete.

Recorded non-blocking residuals for this closure run:

- at the time of the original closure run, repo-wide `npm audit --omit=dev` still reported pre-existing production advisories in `hono`, `@hono/node-server`, `path-to-regexp`, `follow-redirects`, and `brace-expansion`; that historical residual was later retired by `RB-010` on 2026-04-19;
- sign-off remains human-controlled and must be completed separately from automated validation.

Blocking residuals:

- stale or missing OpenAPI export for service identity, entitlements, provisioning, device credential, or access-delivery surfaces;
- missing deterministic replay evidence for service-access drift and channel parity;
- missing cross-channel runtime proof for official web and a non-web consumption path;
- any proof that service access still depends on direct customer-row shortcuts instead of canonical `Phase 5` objects.

---

## 7. Sign-Off Block

| Function | Owner | Decision | Timestamp | Notes |
|---|---|---|---|---|
| platform architecture |  |  |  |  |
| backend platform |  |  |  |  |
| channel teams |  |  |  |  |
| QA |  |  |  |  |
| support enablement |  |  |  |  |
| risk |  |  |  |  |

`Phase 5` is not closed until this table is complete or an explicit waiver is attached by program governance.
