# CyberVPN Partner Platform Phase 0 And Phase 1 Execution Ticket Decomposition

**Date:** 2026-04-17  
**Status:** Execution ticket decomposition for implementation start  
**Purpose:** translate `Phase 0` and `Phase 1` from the detailed phased implementation plan into executable backlog tickets with clear ownership, repository touchpoints, dependencies, acceptance criteria, and evidence requirements.

---

## 1. Document Role

This document is the execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package.

It exists so implementation can start without teams inventing their own ticket boundaries.

This document does not reopen:

- business rules;
- target-state architecture;
- domain boundaries;
- lane definitions;
- payout semantics;
- multi-brand isolation rules.

If a proposed ticket changes any of those, the change must first be approved in the canonical documents.

---

## 2. Execution Rules

Execution for `Phase 0` and `Phase 1` follows these rules:

1. `Phase 0` blocks schema, API, and workflow work that depends on unresolved terminology or contract ambiguity.
2. `Phase 1` may start only after the `Phase 0` contract baseline is signed off.
3. Every ticket must produce one of:
   - merged code;
   - frozen contract documentation;
   - executable tests;
   - operational evidence templates.
4. Every ticket must identify the system of record it changes.
5. Every backend ticket must define:
   - domain objects or contracts introduced;
   - persistence changes;
   - API or event impacts;
   - required tests.
6. No frontend or admin surface may invent business logic locally; it may only consume backend-owned contracts.
7. All `Phase 1` tickets must preserve the canonical rule that the same email may exist in multiple realms without cross-login.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T0.x` for `Phase 0`
- `T1.x` for `Phase 1`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B0` | contracts, glossary, metrics, API and event conventions | platform architecture, product, data/BI |
| `B1` | storefront, realm, auth, partner workspace foundations | backend platform, security, admin |
| `B2` | offer, pricebook, policy, legal acceptance | backend platform, commerce, governance |
| `B3` | risk foundations and validation harnesses | risk/platform, QA, support enablement |

Suggested backlog labels:

- `phase-0`
- `phase-1`
- `contracts`
- `identity`
- `storefront`
- `partner-workspace`
- `policy-versioning`
- `risk-foundation`
- `test-harness`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Phase | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|---|
| `T0.1` | `Phase 0` | `P0.1` | `B0` | `S` | none |
| `T0.2` | `Phase 0` | `P0.2` | `B0` | `S` | `T0.1` |
| `T0.3` | `Phase 0` | `P0.3` | `B0` | `S` | `T0.1` |
| `T0.4` | `Phase 0` | `P0.4` | `B0` | `S` | `T0.1` |
| `T0.5` | `Phase 0` | `P0.5` | `B0` | `S` | `T0.2`, `T0.4` |
| `T0.6` | `Phase 0` | `P0.6`, `P0.7` | `B0`, `B3` | `M` | `T0.2`, `T0.4`, `T0.5` |
| `T1.1` | `Phase 1` | `P1.1` | `B1` | `M` | `T0.1`, `T0.3` |
| `T1.2` | `Phase 1` | `P1.1` | `B1` | `M` | `T1.1`, `T0.4` |
| `T1.3` | `Phase 1` | `P1.2` | `B1` | `L` | `T0.1`, `T0.4` |
| `T1.4` | `Phase 1` | `P1.3` | `B1` | `M` | `T0.1`, `T1.3` |
| `T1.5` | `Phase 1` | `P1.4` | `B2` | `M` | `T1.1`, `T0.3` |
| `T1.6` | `Phase 1` | `P1.5` | `B2` | `M` | `T0.3`, `T0.4`, `T1.1`, `T1.3` |
| `T1.7` | `Phase 1` | `P1.6` | `B3` | `M` | `T1.3`, `T1.4`, `T1.6` |
| `T1.8` | `Phase 1` | phase-exit evidence | `B3` | `M` | `T1.2`, `T1.3`, `T1.4`, `T1.6`, `T1.7` |

`Phase 1` implementation must not start before `T0.1` through `T0.4` are complete.

---

## 5. Phase 0 Ticket Decomposition

## 5.1 `T0.1` Canonical Glossary And Enum Registry Freeze

**Packet alignment:** `P0.1`  
**Primary owners:** platform architecture, backend platform  
**Supporting owners:** product, risk, finance ops

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-partner-platform-rulebook.md`
- Modify: `docs/plans/2026-04-17-partner-platform-target-state-architecture.md`
- Modify: `docs/plans/2026-04-17-commerce-attribution-and-settlement-data-model-spec.md`
- Modify: `backend/src/domain/enums/enums.py`
- Create: `docs/api/partner-platform-enum-registry.md`
- Create: `backend/tests/unit/test_partner_platform_enum_registry.py`

**Scope:**

- freeze canonical singular object names;
- freeze canonical enum values for:
  - commercial owner types;
  - owner source reasons;
  - growth reward types;
  - policy version states;
  - dispute subtypes and outcomes;
  - surface policy capabilities;
- define reserved names that cannot be reused later.

**Deliverables:**

- signed enum registry;
- backend enum module updated with placeholders or reserved values;
- unit tests proving enum serialization and naming stability.

**Acceptance criteria:**

- no document in the package uses conflicting enum names for the same concept;
- `direct_store` and `none` are defined distinctly;
- `payment_dispute` is the canonical dispute object name everywhere;
- pluralization convention is explicitly preserved.

**Evidence required:**

- review sign-off from platform, product, risk, and finance;
- passing backend enum unit test output;
- link to enum registry document.

---

## 5.2 `T0.2` Canonical Metric Dictionary And Reconciliation Vocabulary

**Packet alignment:** `P0.2`  
**Primary owners:** data/BI, finance ops  
**Supporting owners:** platform architecture, backend platform, risk

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-analytics-and-reporting-spec.md`
- Modify: `docs/plans/2026-04-17-partner-platform-operational-readiness-package.md`
- Create: `docs/api/partner-platform-metric-dictionary.md`
- Create: `backend/tests/contract/test_partner_platform_metric_dictionary.py`

**Scope:**

- define one canonical meaning for:
  - `paid_conversion`
  - `qualifying_first_payment`
  - `refund_rate`
  - `chargeback_rate`
  - `d30_paid_retention`
  - `earnings_available`
  - `payout_liability`
  - `net_paid_orders_90d`
- define reconciliation vocabulary for order totals, reward totals, statement totals, and payout totals.

**Deliverables:**

- metric dictionary with dimensional notes;
- reconciliation vocabulary sheet for finance, risk, and partner ops;
- contract test asserting required metric names exist in the dictionary artifact.

**Acceptance criteria:**

- the same metric name is not defined differently across analytics, finance, and readiness docs;
- qualifying rules use the same terminology as the rulebook;
- every phase gate that references a metric points to the same canonical name.

**Evidence required:**

- BI sign-off;
- finance ops sign-off;
- contract test result for dictionary completeness.

---

## 5.3 `T0.3` Policy Version Lifecycle And Effective Dating Contract

**Packet alignment:** `P0.3`  
**Primary owners:** platform architecture, backend platform  
**Supporting owners:** governance, risk, finance ops

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-partner-platform-target-state-architecture.md`
- Modify: `docs/plans/2026-04-17-commerce-attribution-and-settlement-data-model-spec.md`
- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`
- Create: `docs/api/partner-platform-policy-version-lifecycle.md`
- Create: `backend/tests/contract/test_policy_version_lifecycle_contract.py`

**Scope:**

- freeze allowed lifecycle states:
  - `draft`
  - `active`
  - `superseded`
  - `archived`
  - any explicit approval or rejection states if retained;
- define `effective_from`, `effective_to`, approval actor attribution, and no-retroactive-mutation rules;
- define how order snapshots, legal acceptance, and future renewals reference versioned objects.

**Deliverables:**

- lifecycle contract document;
- version-state contract test;
- frozen rule on retroactive supersession behavior.

**Acceptance criteria:**

- all versioned objects use the same effective dating semantics;
- no critical economics object depends on mutable `system_config`;
- order-level reproducibility rules reference policy version IDs, not loose keys.

**Evidence required:**

- governance approval;
- backend contract test output;
- explicit note of unresolved optional extensions, if any, without blocking the lifecycle baseline.

---

## 5.4 `T0.4` API Conventions And Contract Baseline

**Packet alignment:** `P0.4`  
**Primary owners:** backend platform, platform architecture  
**Supporting owners:** admin/frontend platform, QA

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`
- Modify: `backend/src/presentation/api/v1/router.py`
- Create: `docs/api/partner-platform-api-conventions.md`
- Create: `backend/tests/contract/test_partner_platform_api_conventions.py`
- Modify: `admin/src/lib/api/__tests__/client.test.ts`
- Modify: `frontend/src/lib/api/__tests__/client.test.ts`

**Scope:**

- freeze conventions for:
  - auth families and token audiences;
  - idempotency headers and conflict behavior;
  - async job envelopes;
  - error shape;
  - pagination and filtering;
  - audit metadata and explainability payloads;
- define the required resource family naming pattern for new `Phase 1` APIs.

**Deliverables:**

- API conventions document;
- router-level namespace reservation for new partner platform resources;
- contract tests for headers, error envelopes, and idempotency behavior expectations.

**Acceptance criteria:**

- `partner_payout_accounts` remains a first-class resource in the API vocabulary;
- new `Phase 1` APIs can be added without renaming existing conventions later;
- admin and frontend API clients can validate against the same baseline.

**Evidence required:**

- API review sign-off;
- contract test output;
- confirmation that generated clients can consume the documented envelope shape.

---

## 5.5 `T0.5` Event Taxonomy Baseline

**Packet alignment:** `P0.5`  
**Primary owners:** backend platform, data/BI  
**Supporting owners:** finance ops, risk

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-analytics-and-reporting-spec.md`
- Modify: `docs/plans/2026-04-17-partner-platform-detailed-phased-implementation-plan.md`
- Create: `docs/api/partner-platform-event-taxonomy.md`
- Create: `backend/src/application/events/README_partner_platform.md`
- Create: `backend/tests/contract/test_partner_platform_event_taxonomy.py`

**Scope:**

- freeze draft event names and minimum payload requirements for:
  - storefront and realm lifecycle;
  - order and order-item lifecycle;
  - attribution touchpoints and results;
  - growth reward allocations;
  - statement and payout lifecycle;
  - risk review and governance actions;
  - entitlement lifecycle;
- define naming, versioning, and deprecation rules.

**Deliverables:**

- event taxonomy document;
- application event registry placeholder;
- contract test for required event names.

**Acceptance criteria:**

- analytics, replay, and reconciliation docs reference the same event vocabulary;
- event names are object-centric and not provider-centric;
- `Phase 1` can emit placeholder events without renaming them later in `Phase 3` or `Phase 4`.

**Evidence required:**

- BI and backend sign-off;
- contract test output;
- explicit note that payload shape may expand later without renaming the canonical event family.

---

## 5.6 `T0.6` Governance, Synthetic Data, Replay, And QA Evidence Foundation

**Packet alignment:** `P0.6`, `P0.7`  
**Primary owners:** program management, QA  
**Supporting owners:** platform architecture, backend platform, risk, finance ops

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-partner-platform-operational-readiness-package.md`
- Modify: `docs/plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md`
- Modify: `backend/tests/factories.py`
- Modify: `backend/tests/integration/conftest.py`
- Create: `docs/testing/partner-platform-phase-0-and-phase-1-validation-pack.md`
- Create: `backend/tests/contract/test_partner_platform_phase0_gate.py`

**Scope:**

- freeze sign-off cadence and ownership for `Phase 0` and `Phase 1`;
- define the minimum synthetic fixture model for:
  - multiple realms;
  - official storefront and partner storefront;
  - same-email different-realm users;
  - partner accounts and operator roles;
  - legal acceptance records;
  - risk subjects and identifiers;
- define the evidence pack shape that later phases must populate.

**Deliverables:**

- phase validation pack template;
- synthetic fixture extensions in backend test helpers;
- contract gate test ensuring required phase evidence artifacts exist.

**Acceptance criteria:**

- `Phase 1` teams can write tests without inventing realm/storefront fixtures;
- sign-off ownership is explicit;
- evidence file naming and storage is aligned with the readiness package.

**Evidence required:**

- QA sign-off;
- platform program sign-off;
- passing contract gate test.

---

## 6. Phase 1 Ticket Decomposition

## 6.1 `T1.1` Brand, Storefront, And Profile Core

**Packet alignment:** `P1.1`  
**Primary owners:** backend platform  
**Supporting owners:** finance ops, support enablement

**Repository touchpoints:**

- Create: `backend/src/domain/entities/brand.py`
- Create: `backend/src/domain/entities/storefront.py`
- Create: `backend/src/domain/entities/merchant_profile.py`
- Create: `backend/src/domain/entities/support_profile.py`
- Create: `backend/src/domain/entities/communication_profile.py`
- Create: `backend/src/domain/repositories/brand_repository.py`
- Create: `backend/src/domain/repositories/storefront_repository.py`
- Create: `backend/src/infrastructure/database/models/brand_model.py`
- Create: `backend/src/infrastructure/database/models/storefront_model.py`
- Create: `backend/src/infrastructure/database/models/merchant_profile_model.py`
- Create: `backend/src/infrastructure/database/models/support_profile_model.py`
- Create: `backend/src/infrastructure/database/models/communication_profile_model.py`
- Create: `backend/src/infrastructure/database/repositories/brand_repository.py`
- Create: `backend/src/infrastructure/database/repositories/storefront_repository.py`
- Create: `backend/alembic/versions/<timestamp>_phase1_brand_storefront_core.py`
- Create: `backend/tests/unit/test_brand_storefront_entities.py`
- Create: `backend/tests/integration/test_brand_storefront_persistence.py`

**Scope:**

- implement first-class storage and domain objects for:
  - `brands`
  - `storefronts`
  - `merchant_profiles`
  - `support_profiles`
  - `communication_profiles`
- preserve the rule that account identity is realm-scoped, while storefront is a separate surface object.

**Deliverables:**

- persisted brand and storefront core;
- profile-binding capable schema foundation;
- unit and integration tests for persistence and invariants.

**Acceptance criteria:**

- storefront core may exist before all commercial bindings are attached;
- one brand can own multiple storefronts;
- a storefront may reference merchant, support, and communication profiles independently;
- no account object is incorrectly tied to a single immutable storefront.

**Evidence required:**

- migration reviewed;
- unit and integration tests passing;
- schema review sign-off.

---

## 6.2 `T1.2` Storefront Host Resolution And Binding APIs

**Packet alignment:** `P1.1`  
**Primary owners:** backend platform  
**Supporting owners:** frontend platform, support enablement, infra

**Repository touchpoints:**

- Create: `backend/src/application/use_cases/storefronts/`
- Create: `backend/src/presentation/api/v1/storefronts/routes.py`
- Create: `backend/src/presentation/api/v1/storefronts/schemas.py`
- Modify: `backend/src/presentation/api/v1/router.py`
- Create: `backend/src/presentation/middleware/storefront_resolution.py`
- Create: `backend/tests/integration/test_storefront_host_resolution.py`
- Create: `backend/tests/contract/test_storefront_api_contract.py`
- Modify: `frontend/src/__tests__/proxy.test.ts`
- Modify: `admin/src/__tests__/proxy.test.ts`

**Scope:**

- implement host-based storefront resolution;
- expose internal or admin-safe APIs to inspect storefront bindings;
- provide middleware or request-context primitives that later phases can reuse.

**Deliverables:**

- resolved storefront request context;
- storefront read APIs;
- host-resolution tests and proxy-aware smoke coverage.

**Acceptance criteria:**

- unknown hosts fail safely;
- known hosts resolve to one storefront only;
- host resolution does not imply login access across realms;
- request context can carry `storefront_id`, `brand_id`, and profile binding references.

**Evidence required:**

- integration test output;
- contract test output;
- proxy smoke test output for admin and frontend shells.

---

## 6.3 `T1.3` Auth Realms, Principal Classes, Sessions, And Token Audiences

**Packet alignment:** `P1.2`  
**Primary owners:** backend platform, security  
**Supporting owners:** frontend platform, admin platform

**Repository touchpoints:**

- Create: `backend/src/domain/entities/auth_realm.py`
- Create: `backend/src/domain/entities/principal.py`
- Create: `backend/src/domain/entities/principal_session.py`
- Create: `backend/src/domain/repositories/auth_realm_repository.py`
- Create: `backend/src/infrastructure/database/models/auth_realm_model.py`
- Create: `backend/src/infrastructure/database/models/principal_session_model.py`
- Create: `backend/src/application/use_cases/auth_realms/`
- Modify: `backend/src/application/use_cases/auth/`
- Modify: `backend/src/application/use_cases/mobile_auth/`
- Modify: `backend/src/presentation/api/v1/auth/routes.py`
- Modify: `backend/src/presentation/api/v1/auth/schemas.py`
- Create: `backend/src/presentation/api/v1/realms/routes.py`
- Create: `backend/src/presentation/api/v1/realms/schemas.py`
- Modify: `backend/src/presentation/dependencies/`
- Create: `backend/alembic/versions/<timestamp>_phase1_auth_realms.py`
- Create: `backend/tests/security/test_auth_realm_isolation.py`
- Create: `backend/tests/integration/test_auth_realm_sessions.py`

**Scope:**

- add first-class `auth_realms`;
- define principal classes for customer, partner operator, admin, and service identities where required by the target-state model;
- enforce realm-aware session and token audience behavior.

**Deliverables:**

- persisted realm model;
- realm-aware auth APIs and middleware;
- session and token audience enforcement tests.

**Acceptance criteria:**

- the same email can register in more than one realm;
- credentials from one realm do not authenticate into another realm;
- token audiences and scopes are explicit and testable;
- mobile-auth legacy terminology does not remain the canonical identity contract for new work.

**Evidence required:**

- security test output;
- integration test output;
- auth contract review sign-off.

---

## 6.4 `T1.4` Partner Account, Workspace Membership, RBAC, And Permission Foundation

**Packet alignment:** `P1.3`  
**Primary owners:** backend platform, admin platform  
**Supporting owners:** support enablement, finance ops

**Repository touchpoints:**

- Modify: `backend/src/domain/entities/partner.py`
- Create: `backend/src/domain/entities/partner_account_user.py`
- Create: `backend/src/domain/entities/partner_role.py`
- Create: `backend/src/domain/entities/partner_permission.py`
- Create: `backend/src/domain/repositories/partner_account_repository.py`
- Modify: `backend/src/infrastructure/database/models/partner_model.py`
- Create: `backend/src/infrastructure/database/models/partner_account_user_model.py`
- Create: `backend/src/infrastructure/database/models/partner_role_model.py`
- Create: `backend/src/infrastructure/database/repositories/partner_account_repository.py`
- Modify: `backend/src/application/use_cases/partners/`
- Modify: `backend/src/presentation/api/v1/partners/routes.py`
- Modify: `backend/src/presentation/api/v1/partners/schemas.py`
- Create: `backend/alembic/versions/<timestamp>_phase1_partner_workspace.py`
- Create: `backend/tests/integration/test_partner_workspace_membership.py`
- Create: `backend/tests/security/test_partner_scope_enforcement.py`
- Modify: `admin/src/lib/api/__tests__/growth-admin.test.ts`
- Modify: `admin/src/lib/api/__tests__/security-admin.test.ts`

**Scope:**

- evolve the current partner model into an account/workspace-root model;
- add organization users, roles, permissions, and membership semantics;
- expose RBAC-capable partner APIs for later partner portal work.

**Deliverables:**

- partner workspace data model;
- scope-aware partner API contracts;
- security and integration coverage for role enforcement.

**Acceptance criteria:**

- a partner account can have multiple operator users;
- finance, analyst, and manager-style permissions can be represented separately;
- partner membership is not modelled as a customer-only upgrade;
- scope enforcement is testable from API clients.

**Evidence required:**

- admin platform review sign-off;
- integration and security test output;
- updated partner API client tests.

---

## 6.5 `T1.5` Offer, Pricebook, And Program Eligibility Foundation

**Packet alignment:** `P1.4`  
**Primary owners:** backend commerce, backend platform  
**Supporting owners:** product, finance ops

**Repository touchpoints:**

- Create: `backend/src/domain/entities/offer.py`
- Create: `backend/src/domain/entities/pricebook.py`
- Create: `backend/src/domain/entities/program_eligibility_policy.py`
- Modify: `backend/src/domain/entities/subscription_plan.py`
- Modify: `backend/src/domain/entities/plan_addon.py`
- Create: `backend/src/domain/repositories/offer_repository.py`
- Create: `backend/src/domain/repositories/pricebook_repository.py`
- Create: `backend/src/infrastructure/database/models/offer_model.py`
- Create: `backend/src/infrastructure/database/models/pricebook_model.py`
- Create: `backend/src/infrastructure/database/models/program_eligibility_policy_model.py`
- Create: `backend/src/application/use_cases/offers/`
- Create: `backend/src/presentation/api/v1/offers/routes.py`
- Create: `backend/src/presentation/api/v1/offers/schemas.py`
- Create: `backend/src/presentation/api/v1/pricebooks/routes.py`
- Create: `backend/src/presentation/api/v1/pricebooks/schemas.py`
- Create: `backend/alembic/versions/<timestamp>_phase1_offers_pricebooks.py`
- Create: `backend/tests/unit/test_offer_pricebook_foundations.py`
- Create: `backend/tests/contract/test_pricing_openapi_contract.py`

**Scope:**

- separate product catalog concepts from offer and pricebook overlays;
- add program eligibility foundations required for later order snapshots and stacking rules;
- avoid hiding critical economics inside `system_config`.

**Deliverables:**

- first-class offer and pricebook foundation;
- API surface for pricebooks and offers;
- compatibility-ready eligibility storage.

**Acceptance criteria:**

- one product family may map to multiple offers or pricebooks;
- official storefront and partner storefront pricing can diverge without mutating base plan semantics;
- partner program eligibility is referenceable from later order snapshots.

**Evidence required:**

- unit and contract test output;
- commerce review sign-off;
- data model review for snapshot compatibility.

---

## 6.6 `T1.6` Policy Version Objects, Approvals, Legal Document Sets, And Acceptance Evidence

**Packet alignment:** `P1.5`  
**Primary owners:** backend platform, governance  
**Supporting owners:** security, finance ops, support enablement

**Repository touchpoints:**

- Create: `backend/src/domain/entities/policy_version.py`
- Create: `backend/src/domain/entities/legal_document.py`
- Create: `backend/src/domain/entities/legal_document_set.py`
- Create: `backend/src/domain/entities/accepted_legal_document.py`
- Create: `backend/src/infrastructure/database/models/policy_version_model.py`
- Create: `backend/src/infrastructure/database/models/legal_document_model.py`
- Create: `backend/src/infrastructure/database/models/legal_document_set_model.py`
- Create: `backend/src/infrastructure/database/models/accepted_legal_document_model.py`
- Create: `backend/src/application/use_cases/policies/`
- Create: `backend/src/application/use_cases/legal_documents/`
- Create: `backend/src/presentation/api/v1/policies/routes.py`
- Create: `backend/src/presentation/api/v1/policies/schemas.py`
- Create: `backend/src/presentation/api/v1/legal_documents/routes.py`
- Create: `backend/src/presentation/api/v1/legal_documents/schemas.py`
- Create: `backend/alembic/versions/<timestamp>_phase1_policy_versions_and_legal_docs.py`
- Create: `backend/tests/integration/test_legal_document_acceptance.py`
- Create: `backend/tests/security/test_policy_actor_attribution.py`
- Modify: `admin/src/lib/api/__tests__/governance-admin.test.ts`

**Scope:**

- implement typed policy-version storage and approval workflow;
- implement legal document sets bound to storefront and policy context;
- implement acceptance evidence with surface and principal context.

**Deliverables:**

- versioned policy foundation;
- legal document set and acceptance evidence model;
- governance and audit tests for actor attribution.

**Acceptance criteria:**

- acceptance evidence captures document or document-set version, storefront, realm, actor principal, and timestamp;
- policy changes record actor attribution and approval state transitions;
- future order snapshots can reference version IDs instead of free-form config keys.

**Evidence required:**

- integration and security test output;
- governance sign-off;
- audit-field completeness review.

---

## 6.7 `T1.7` Early Risk Subject Graph And Baseline Eligibility Checks

**Packet alignment:** `P1.6`  
**Primary owners:** risk platform  
**Supporting owners:** backend platform, security, finance ops

**Repository touchpoints:**

- Create: `backend/src/domain/entities/risk_subject.py`
- Create: `backend/src/domain/entities/risk_identifier.py`
- Create: `backend/src/domain/entities/risk_link.py`
- Create: `backend/src/domain/entities/risk_review.py`
- Create: `backend/src/domain/repositories/risk_subject_repository.py`
- Create: `backend/src/infrastructure/database/models/risk_subject_model.py`
- Create: `backend/src/infrastructure/database/models/risk_identifier_model.py`
- Create: `backend/src/infrastructure/database/models/risk_link_model.py`
- Create: `backend/src/infrastructure/database/models/risk_review_model.py`
- Create: `backend/src/application/use_cases/risk/`
- Modify: `backend/src/presentation/api/v1/security/routes.py`
- Modify: `backend/src/presentation/api/v1/security/schemas.py`
- Create: `backend/alembic/versions/<timestamp>_phase1_risk_foundation.py`
- Create: `backend/tests/security/test_risk_subject_linkage.py`
- Create: `backend/tests/security/test_same_email_multi_realm_abuse_guards.py`
- Create: `backend/tests/integration/test_phase1_eligibility_guards.py`

**Scope:**

- implement the minimum risk graph needed for:
  - self-referral detection;
  - multi-realm abuse detection;
  - trial/referral/payout eligibility guardrails;
- keep the graph separate from customer-facing identity semantics.

**Deliverables:**

- risk subject foundation;
- identifier linking rules;
- baseline eligibility checks callable by later phases.

**Acceptance criteria:**

- same-email different-realm accounts may exist without being treated as the same account object;
- the risk layer can still detect suspicious linkage across realms;
- baseline eligibility checks can be called without waiting for `Phase 3` attribution logic.

**Evidence required:**

- security and integration test output;
- risk review sign-off;
- explicit documentation of false-positive containment strategy for early rollout.

---

## 6.8 `T1.8` Phase 1 Validation Harness And Exit Evidence Pack

**Packet alignment:** phase-exit validation  
**Primary owners:** QA, backend platform  
**Supporting owners:** admin platform, frontend platform, support enablement, risk

**Repository touchpoints:**

- Create: `backend/tests/e2e/test_phase1_foundations.py`
- Create: `backend/tests/contract/test_phase1_api_surface_contract.py`
- Modify: `backend/tests/factories.py`
- Modify: `backend/tests/integration/conftest.py`
- Create: `docs/testing/partner-platform-phase1-exit-evidence.md`
- Modify: `docs/plans/2026-04-17-partner-platform-operational-readiness-package.md`
- Modify: `docs/plans/2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md`
- Modify: `admin/src/lib/api/generated/`
- Modify: `frontend/src/lib/api/generated/`

**Scope:**

- build the minimum automated and evidence-producing harness required to close `Phase 1`;
- verify:
  - realm isolation;
  - storefront host resolution;
  - partner workspace roles and scopes;
  - legal acceptance evidence capture;
  - risk-subject linkage behavior.

**Deliverables:**

- end-to-end validation test for `Phase 1`;
- contract coverage for new APIs;
- exit evidence document ready for sign-off.

**Acceptance criteria:**

- `Phase 1` exit evidence in the detailed phased plan can be produced from actual tests and artifacts;
- frontend and admin generated clients compile against the new API contracts even if full surfaces are deferred;
- the internal demo no longer depends on ad hoc manual scripts only.

**Evidence required:**

- e2e and contract test output;
- generated-client validation output;
- signed `Phase 1` exit evidence pack.

---

## 7. Explicit Non-Goals For This Decomposition

The following are intentionally not part of `Phase 0` or `Phase 1` ticket execution:

- canonical order domain implementation;
- attribution result engine;
- settlement statements and payout execution;
- partner payout activation;
- partner storefront full customer UI;
- channel parity rollout;
- pilot traffic activation.

If a team needs any of those to close a `Phase 0` or `Phase 1` ticket, the ticket is oversized and must be split.

---

## 8. Phase Completion Gates

## 8.1 `Phase 0` Can Be Declared Complete When

- `T0.1` through `T0.6` are complete;
- glossary, metric, API, policy-lifecycle, and event-taxonomy baselines are signed off;
- synthetic fixtures and validation pack templates exist;
- no `Phase 1` schema or API work remains blocked by unresolved vocabulary.

## 8.2 `Phase 1` Can Be Declared Complete When

- `T1.1` through `T1.8` are complete;
- schema freeze is reached for storefront, realm, partner-account, policy-version, legal-acceptance, and risk-foundation objects;
- API freeze is reached for auth, realms, storefronts, partners, offers, pricebooks, policies, legal documents, and early risk surfaces;
- automated evidence proves:
  - same-email different-realm registration works;
  - cross-login across realms is blocked;
  - partner workspace RBAC is enforced;
  - legal acceptance evidence is captured correctly;
  - risk-subject linkage works without collapsing realm isolation.

---

## 9. Immediate Handoff After This Document

After this decomposition is accepted, the next execution artifacts are:

1. owner-by-owner workboards derived from `B0` through `B3`;
2. ticket import into the chosen tracker with environment tags and assignees;
3. `Phase 0` start using `T0.1` through `T0.4` as the blocking set;
4. `Phase 1` implementation kickoff only after `Phase 0` contract sign-off is recorded.

This document is the last planning layer before active execution for `Phase 0` and `Phase 1`.
