# CyberVPN Partner Platform Phase 5 Execution Ticket Decomposition

**Date:** 2026-04-18  
**Status:** Execution ticket decomposition for `Phase 5` implementation start  
**Purpose:** translate `Phase 5` from the detailed phased implementation plan into executable backlog tickets for service identity, entitlements, provisioning, access delivery, and migration work.

---

## 1. Document Role

This document is the `Phase 5` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 4` gate evidence pack.

It exists so backend platform, channel teams, support tooling, and QA do not continue to treat service access as an accidental side effect of `mobile_users`, `payments`, or channel-specific provisioning shortcuts.

This document does not reopen:

- realm, storefront, and partner workspace rules frozen in `Phase 1`;
- order-domain and payment seams frozen in `Phase 2`;
- attribution, growth-reward, stacking, and renewal rules frozen in `Phase 3`;
- settlement and payout rules frozen in `Phase 4`;
- UI assembly and surface rollout reserved for `Phase 6`.

If a proposed `Phase 5` ticket changes any of those, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 5` follows these rules:

1. `Phase 5` starts only after `Phase 4` engineering gate is green.
2. `service_identities`, `entitlement_grants`, `device_credentials`, `provisioning_profiles`, and `access_delivery_channels` remain separate entity families.
3. Service access must resolve from entitlement state, not from storefront session reuse or direct wallet/payment checks.
4. Purchase surface and service-consumption surface remain separately explainable.
5. Shared channels may consume the same entitlement truth, but must stay realm-aware and storefront-aware.
6. Legacy `mobile_users.remnawave_uuid` and `subscription_url` may be bridged as provenance only; they are not the new canonical service-access model.
7. `Phase 5` may dual-read or dual-write against legacy subscription/provisioning semantics, but the new service layer is the canonical target.
8. Every `Phase 5` ticket must produce at least one of:
   - merged code;
   - frozen API contract updates;
   - executable tests;
   - reconciliation or shadow evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T5.x` for `Phase 5`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B15` | service identities, provisioning profiles, entitlement grants | backend platform |
| `B16` | device credentials, access delivery channels, channel adapters | backend platform, channel teams |
| `B17` | support/admin observability and explainability for service consumption | backend platform, support enablement |
| `B18` | migration, shadow parity, reconciliation, and phase closure | QA, platform, channel teams |

Suggested backlog labels:

- `phase-5`
- `service-identity`
- `entitlements`
- `provisioning`
- `access-delivery`
- `channel-parity`
- `migration`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T5.1` | `P5.1` | `B15` | `L` | `Phase 4 gate`, `T1.3`, `T2.3` |
| `T5.2` | `P5.2` | `B15` | `L` | `T5.1`, `T2.3`, `T3.4` |
| `T5.3` | `P5.3` | `B16` | `L` | `T5.1`, `T5.2`, `T1.1` |
| `T5.4` | shared entitlement and service-state APIs | `B15`, `B17` | `M` | `T5.2`, `T5.3` |
| `T5.5` | support/admin observability for purchase vs consumption | `B17` | `M` | `T5.2`, `T5.3`, `T3.7` |
| `T5.6` | legacy subscription/provisioning migration and shadow parity | `B18` | `L` | `T5.2`, `T5.3`, `T5.4` |
| `T5.7` | entitlement and provisioning replay / reconciliation evidence | `B18` | `M` | `T5.4`, `T5.6` |
| `T5.8` | phase-exit evidence | `B18` | `M` | `T5.1`, `T5.2`, `T5.3`, `T5.4`, `T5.5`, `T5.6`, `T5.7` |

`T5.1` is the only valid starting point for `Phase 5` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T5.1` Service Identities And Provisioning Profiles Foundation

**Packet alignment:** `P5.1`  
**Primary owners:** backend platform  
**Supporting owners:** QA, support enablement

**Repository touchpoints:**

- Create: `backend/src/domain/entities/service_identity.py`
- Create: `backend/src/domain/entities/provisioning_profile.py`
- Create: `backend/src/infrastructure/database/models/service_identity_model.py`
- Create: `backend/src/infrastructure/database/models/provisioning_profile_model.py`
- Create: `backend/src/infrastructure/database/repositories/service_access_repo.py`
- Create: `backend/src/application/use_cases/service_access/`
- Create: `backend/src/presentation/api/v1/service_identities/`
- Create: `backend/src/presentation/api/v1/provisioning_profiles/`
- Create: `backend/tests/integration/test_service_identity_foundations.py`
- Create: `backend/tests/contract/test_service_identity_openapi_contract.py`

**Scope:**

- first-class `service_identities` detached from storefront login assumptions;
- first-class `provisioning_profiles` detached from raw customer rows;
- order-linked provenance for service identities where service access is born from a commercial order;
- legacy bridge fields for current provider references, without making them canonical state.

**Acceptance criteria:**

- a customer account can be resolved to one canonical service identity per realm/provider context without mutating the order;
- provisioning profiles are managed independently from entitlement grants or device credentials;
- foundation APIs expose service identity and provisioning profile read/write behavior for admin/support use.

## 5.2 `T5.2` Entitlement Grants And Lifecycle

**Packet alignment:** `P5.2`  
**Primary owners:** backend platform  
**Supporting owners:** growth platform, QA

**Scope:**

- first-class `entitlement_grants`;
- activate, suspend, revoke, and expire transitions;
- grant provenance from orders, rewards, and renewal lineage.

**Acceptance criteria:**

- entitlement lifecycle is canonical and auditable;
- service access reads entitlement grants instead of customer-row shortcuts;
- non-cash growth rewards may affect service access without becoming payout owners.

## 5.3 `T5.3` Device Credentials And Access Delivery Channels

**Packet alignment:** `P5.3`  
**Primary owners:** backend platform, channel teams  
**Supporting owners:** QA

**Scope:**

- first-class `device_credentials`;
- first-class `access_delivery_channels`;
- realm-aware delivery methods for shared clients, subscription URLs, and bot-driven delivery.

**Acceptance criteria:**

- device credentials do not replace entitlement state;
- delivery channels can be audited separately from purchase channels;
- realm-aware access delivery exists without assuming official-web account ownership.

## 5.4 `T5.4` Shared Entitlement And Service-State APIs

**Packet alignment:** derived from `P5.2` and `P5.3`  
**Primary owners:** backend platform  
**Supporting owners:** channel teams, QA

**Scope:**

- shared read APIs for current entitlement state;
- shared service-identity and provisioning resolution;
- channel-neutral service-state payloads.

**Acceptance criteria:**

- web, Telegram, mobile, and desktop can consume the same service-state contract;
- purchase context and service-consumption context stay separately inspectable.

## 5.5 `T5.5` Support And Admin Observability For Service Consumption

**Packet alignment:** `P5.4`  
**Primary owners:** backend platform, support enablement  
**Supporting owners:** QA

**Scope:**

- explainability payloads for service identity, entitlement, provisioning profile, and channel state;
- support/admin read models showing purchase channel versus service-consumption channel.

**Acceptance criteria:**

- support can inspect service access without inferring it from storefront login state;
- service state is visible per realm and per channel.

## 5.6 `T5.6` Legacy Subscription And Provisioning Migration

**Packet alignment:** `P5.5`  
**Primary owners:** backend platform, QA  
**Supporting owners:** channel teams

**Scope:**

- migration path from legacy subscription/provisioning semantics;
- dual-read or dual-write bridge where needed;
- shadow parity against current entitlements and service delivery.

**Acceptance criteria:**

- service counts and access outcomes reconcile against legacy sources during migration windows;
- legacy provider references are preserved as provenance, not as the new source of truth.

## 5.7 `T5.7` Entitlement And Provisioning Replay / Reconciliation Evidence

**Packet alignment:** replay and reconciliation evidence  
**Primary owners:** QA, backend platform  
**Supporting owners:** channel teams

**Scope:**

- deterministic replay pack for service identities, grants, and provisioning profiles;
- machine-readable mismatch vocabulary for service-access drift.

**Acceptance criteria:**

- entitlement and provisioning replay output is deterministic;
- channel parity mismatches are explicit and explainable.

## 5.8 `T5.8` Phase 5 Gate And Evidence Pack

**Packet alignment:** phase-exit evidence  
**Primary owners:** QA, backend platform  
**Supporting owners:** support enablement, channel teams

**Scope:**

- freeze evidence for service identities, entitlements, credentials, provisioning profiles, and shared service-state APIs;
- attach replay and channel-parity evidence;
- record unresolved but non-blocking residuals.

**Acceptance criteria:**

- schema and API freeze for service identity and entitlement families;
- support sign-off that purchase surface and consumption surface are separately visible;
- cross-channel parity evidence exists for at least web and one non-web channel.

---

## 6. Phase 5 Completion Gate

`Phase 5` is complete only when:

1. `T5.1` through `T5.7` are merged or explicitly waived by governance;
2. canonical service identities, entitlements, provisioning profiles, and access delivery objects exist and remain distinct;
3. service access is no longer treated as a loosely coupled side effect of customer rows;
4. replay and parity evidence are green;
5. the `Phase 5` evidence pack is green.
