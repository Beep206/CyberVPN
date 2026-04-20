# CyberVPN Partner Platform Phase 2 Execution Ticket Decomposition

**Date:** 2026-04-18  
**Status:** Execution ticket decomposition for `Phase 2` implementation start  
**Purpose:** translate `Phase 2` from the detailed phased implementation plan into executable backlog tickets with clear ownership, repository touchpoints, dependencies, acceptance criteria, and evidence requirements.

---

## 1. Document Role

This document is the `Phase 2` execution bridge between:

- the canonical specification package;
- the domain dependency matrix;
- the detailed phased implementation plan;
- the operational readiness package;
- the completed `Phase 1` gate evidence pack.

It exists so commerce, billing, finance, QA, and risk do not invent their own order-domain ticket boundaries.

This document does not reopen:

- multi-brand identity rules;
- program eligibility semantics already frozen in `Phase 1`;
- attribution precedence;
- settlement payout rules;
- consumer versus partner finance separation.

If a proposed `Phase 2` ticket changes any of those, the canonical documents must be updated first.

---

## 2. Execution Rules

Execution for `Phase 2` follows these rules:

1. `Phase 2` starts only after `Phase 1` gate evidence is green.
2. `merchant`, `invoice`, `billing descriptor`, and tax-behavior foundations land before `quote`, `checkout`, or `order` work.
3. No order object may be committed without explicit merchant, invoice, and descriptor snapshot inputs.
4. The canonical commercial object remains `order`, not `payment_attempt`.
5. `payment_dispute` is the canonical dispute resource; `chargeback` is represented as subtype, stage, or outcome inside that object.
6. `Phase 2` must keep current consumer-facing flows working while the new order domain is introduced behind frozen contracts.
7. Frontend and admin surfaces may consume `Phase 2` contracts for validation, but they must not become the system of record for order or billing semantics.
8. Every `Phase 2` ticket must produce at least one of:
   - merged code;
   - frozen API contract updates;
   - executable tests;
   - replay or reconciliation evidence.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T2.x` for `Phase 2`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B4` | merchant, invoice, billing descriptor, tax foundation | backend commerce, billing platform, finance ops |
| `B5` | quote, checkout, order, payment-attempt core | backend commerce, QA |
| `B6` | refunds, payment disputes, commissionability scaffolding | backend commerce, risk, finance ops |
| `B7` | replay, reconciliation, migration, evidence | platform backend, QA, finance ops |

Suggested backlog labels:

- `phase-2`
- `commerce`
- `merchant-billing`
- `orders`
- `checkout`
- `refunds`
- `payment-disputes`
- `commissionability`
- `reconciliation`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|
| `T2.1` | `P2.1` | `B4` | `M` | `Phase 1 gate` |
| `T2.2` | `P2.2` | `B5` | `L` | `T2.1` |
| `T2.3` | `P2.3` | `B5` | `L` | `T2.2` |
| `T2.4` | `P2.4` | `B5` | `M` | `T2.2`, `T2.3` |
| `T2.5` | `P2.5` | `B6` | `L` | `T2.1`, `T2.3`, `T2.4` |
| `T2.6` | `P2.6` | `B6` | `M` | `T2.3`, `T2.5` |
| `T2.7` | `P2.7` | `B7` | `M` | `T2.3`, `T2.4`, `T2.5` |
| `T2.8` | phase-exit evidence | `B7` | `M` | `T2.2`, `T2.3`, `T2.4`, `T2.5`, `T2.6`, `T2.7` |

`T2.1` is the only valid starting point for `Phase 2` implementation.

---

## 5. Ticket Decomposition

## 5.1 `T2.1` Merchant, Invoice, Billing Descriptor, And Tax Foundation

**Packet alignment:** `P2.1`  
**Primary owners:** backend commerce, billing platform  
**Supporting owners:** finance ops, support enablement

**Repository touchpoints:**

- Modify: `docs/plans/2026-04-17-commerce-attribution-and-settlement-data-model-spec.md`
- Modify: `docs/plans/2026-04-17-partner-platform-api-specification-package.md`
- Modify: `backend/src/domain/entities/storefront.py`
- Modify: `backend/src/infrastructure/database/models/merchant_profile_model.py`
- Create: `backend/src/infrastructure/database/models/invoice_profile_model.py`
- Create: `backend/src/infrastructure/database/models/billing_descriptor_model.py`
- Create: `backend/src/presentation/api/v1/merchant_profiles/`
- Create: `backend/src/presentation/api/v1/invoice_profiles/`
- Create: `backend/src/presentation/api/v1/billing_descriptors/`
- Create: `backend/tests/unit/test_merchant_billing_foundations.py`
- Create: `backend/tests/contract/test_merchant_billing_openapi_contract.py`

**Scope:**

- introduce first-class `invoice_profiles`;
- introduce first-class `billing_descriptors`;
- extend `merchant_profiles` with explicit invoice/tax/refund/chargeback behavior anchors;
- make storefront and pricebook merchant context resolvable without order creation;
- freeze the minimum API surface for merchant, invoice, and descriptor management.

**Acceptance criteria:**

- merchant-of-record context is explicit and referenceable;
- invoice behavior does not live in loose JSON blobs without typed top-level anchors;
- billing descriptors are first-class records, not only strings hidden inside storefront or pricebook rows;
- tax behavior baseline is available for later order snapshots.

**Evidence required:**

- passing OpenAPI contract test for merchant/invoice/billing routes;
- backend unit or integration tests proving persistence and resolution behavior;
- doc links showing `Phase 2` API families are no longer only reserved names.

## 5.2 `T2.2` Quote Sessions And Checkout Sessions

**Packet alignment:** `P2.2`  
**Primary owners:** backend commerce  
**Supporting owners:** frontend, admin, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/quote_session.py`
- Create: `backend/src/domain/entities/checkout_session.py`
- Create: `backend/src/infrastructure/database/models/quote_session_model.py`
- Create: `backend/src/infrastructure/database/models/checkout_session_model.py`
- Create: `backend/src/presentation/api/v1/quotes/`
- Create: `backend/src/presentation/api/v1/checkout_sessions/`
- Create: `backend/tests/integration/test_quote_checkout_sessions.py`

**Scope:**

- quote creation with storefront, realm, pricebook, offer, merchant, and legal context;
- checkout-session creation bound to quote lineage;
- stale quote and stale policy detection;
- idempotent checkout-session creation keys.

**Acceptance criteria:**

- one quote can lead to zero or one checkout session;
- checkout session snapshots merchant, invoice, tax, and descriptor context before order commit;
- quote expiration and policy drift are explicit API failures.

## 5.3 `T2.3` Orders And Order Items

**Packet alignment:** `P2.3`  
**Primary owners:** backend commerce  
**Supporting owners:** finance ops, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/order.py`
- Create: `backend/src/infrastructure/database/models/order_model.py`
- Create: `backend/src/presentation/api/v1/orders/`
- Create: `backend/tests/integration/test_order_commit.py`
- Create: `backend/tests/unit/test_order_snapshot_reproducibility.py`

**Scope:**

- canonical `order` and `order_item` models;
- committed pricing and policy snapshots;
- lineage from quote and checkout to order;
- order history read surface for later explainability.

**Acceptance criteria:**

- order remains stable across later payment retries;
- merchant, invoice, tax, and descriptor snapshots are persisted on order creation;
- order items preserve the committed commercial view independently from later catalog mutation.

## 5.4 `T2.4` Payment Attempts, Retry Semantics, And Commit Idempotency

**Packet alignment:** `P2.4`  
**Primary owners:** backend commerce  
**Supporting owners:** finance ops, QA

**Repository touchpoints:**

- Create: `backend/src/domain/entities/payment_attempt.py`
- Create: `backend/src/infrastructure/database/models/payment_attempt_model.py`
- Modify: payment/provider integration adapters where needed
- Create: `backend/tests/integration/test_order_payment_attempt_retries.py`

**Scope:**

- one order to many payment attempts;
- retry lineage and terminal-attempt semantics;
- checkout commit idempotency;
- wallet-plus-external-payment compatibility if the current flow uses mixed tenders.

**Acceptance criteria:**

- payment attempts never become the canonical commercial object;
- retries preserve a single order identity and stable snapshots;
- idempotent commit guards prevent duplicate orders for the same checkout intent.

## 5.5 `T2.5` Refunds, Canonical Payment Disputes, And Chargeback Normalization

**Packet alignment:** `P2.5`  
**Primary owners:** backend commerce, risk  
**Supporting owners:** finance ops, support enablement

**Repository touchpoints:**

- Create: `backend/src/domain/entities/refund.py`
- Create: `backend/src/domain/entities/payment_dispute.py`
- Create: `backend/src/infrastructure/database/models/refund_model.py`
- Create: `backend/src/infrastructure/database/models/payment_dispute_model.py`
- Create: `backend/src/presentation/api/v1/refunds/`
- Create: `backend/src/presentation/api/v1/payment_disputes/`
- Create: `backend/tests/integration/test_refund_and_dispute_lifecycle.py`

**Scope:**

- refunds as first-class order-linked objects;
- canonical `payment_dispute` resource;
- `chargeback` as subtype/stage/outcome inside the dispute model;
- provider-normalized dispute lifecycle and evidence references.

**Acceptance criteria:**

- refunds and disputes attach to orders, not only legacy payment rows;
- one dispute object can explain inquiry, formal dispute, chargeback, reversal, and fee state;
- partial refunds and dispute overlap are representable.

## 5.6 `T2.6` Commissionability Scaffolding And Order Explainability

**Packet alignment:** `P2.6`  
**Primary owners:** backend commerce, attribution platform  
**Supporting owners:** finance ops, support

**Repository touchpoints:**

- Create: `backend/src/domain/entities/commissionability_evaluation.py`
- Create: `backend/src/infrastructure/database/models/commissionability_evaluation_model.py`
- Create: `backend/src/presentation/api/v1/orders/explainability/`
- Create: `backend/tests/integration/test_commissionability_scaffolding.py`

**Scope:**

- order-level commissionability preconditions;
- explainability payload showing snapshots and eligibility context;
- placeholders for later attribution and growth-reward linking without implementing Phase 3 logic early.

**Acceptance criteria:**

- commissionability records do not compute payout ownership yet, but they do freeze the preconditions for Phase 3;
- support and finance can inspect why an order is or is not eligible for downstream partner logic.

## 5.7 `T2.7` Order-Domain Migration And Replay Harness

**Packet alignment:** `P2.7`  
**Primary owners:** platform backend, QA  
**Supporting owners:** finance ops, BI

**Repository touchpoints:**

- Create: replay/backfill scripts under `backend/scripts/`
- Create: validation docs under `docs/testing/`
- Create: `backend/tests/contract/test_phase2_reconciliation_pack.py`

**Scope:**

- legacy payment-centric to order-centric mapping harness;
- historical replay shape for orders, payment attempts, refunds, and disputes;
- reconciliation baselines for count and amount parity.

**Acceptance criteria:**

- replay harness can materialize deterministic order vocabulary without live cutover;
- reconciliation reports can explain mismatches, not only count them.

## 5.8 `T2.8` Phase 2 Gate And Evidence Pack

**Packet alignment:** phase-exit evidence  
**Primary owners:** QA, backend commerce  
**Supporting owners:** finance ops, risk, support enablement

**Repository touchpoints:**

- Create: `docs/testing/partner-platform-phase2-exit-evidence.md`
- Modify: `docs/plans/2026-04-17-partner-platform-operational-readiness-package.md`
- Create: `backend/tests/e2e/test_phase2_commerce_foundations.py`

**Scope:**

- freeze evidence for order-domain, billing, refund, and dispute foundations;
- attach reconciliation outputs;
- record unresolved but non-blocking residuals.

**Acceptance criteria:**

- schema and API freeze for quote, checkout, order, refund, and dispute families;
- shadow reconciliation exists for order count, payment attempts, and refunds;
- finance can review a complete order history with merchant and descriptor snapshots.

---

## 6. Phase 2 Completion Gate

`Phase 2` is complete only when:

1. `T2.1` through `T2.7` are merged or explicitly waived by governance;
2. order-first explainability is demonstrable through tests or review artifacts;
3. `payment_dispute` is present as a first-class API and persistence object;
4. merchant, invoice, and billing descriptor context are snapshot-ready for orders;
5. the `Phase 2` evidence pack is green.
