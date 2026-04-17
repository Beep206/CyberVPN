# CyberVPN Partner Platform Domain Dependency Matrix

**Date:** 2026-04-17  
**Status:** Cross-domain dependency matrix  
**Purpose:** define the canonical dependency graph between the bounded contexts of the CyberVPN partner platform so implementation planning, sequencing, ownership, and seam management can proceed without hidden assumptions.

---

## 1. Document Role

This document is the dependency map for the platform specification package.

It answers:

- which domains are upstream of other domains;
- which contracts are blocking prerequisites;
- which domains consume snapshots versus live state;
- which seam objects need explicit cross-team ownership;
- which contexts can be built in parallel and which cannot.

This is not the phased implementation plan. It is the cross-domain dependency map that the phased plan must follow.

---

## 2. Canonical Domain Set

The matrix covers the same bounded contexts defined in the target-state architecture:

1. Brand and Storefront
2. Identity and Access
3. Product and Offers
4. Merchant, Billing, Tax, and Disputes
5. Commerce and Orders
6. Attribution and Commercial Ownership
7. Growth Rewards
8. Partner Organizations
9. Finance and Settlement
10. Service Access and Entitlements
11. Risk, Compliance, and Governance
12. Analytics and Reporting

Cross-cutting semantic packages referenced by this matrix:

- Rulebook
- API Specification Package
- Program Compatibility, Qualifying Events, And Renewal Spec
- Lifecycle And State Machine Spec

---

## 3. Dependency Types

Use the following dependency vocabulary:

| Type | Meaning |
|---|---|
| `Foundational` | downstream domain cannot be canonically implemented without the upstream domain existing first |
| `Policy` | downstream domain depends on upstream policy, eligibility, or versioned rules |
| `Snapshot` | downstream domain snapshots upstream state into immutable records |
| `Operational` | downstream domain uses upstream objects in workflow or case handling |
| `Financial` | downstream domain derives economic consequences from upstream objects |
| `Reporting` | downstream domain consumes upstream events or records for metrics and exports |

A domain may have several dependency types on the same upstream domain.

---

## 4. Layered Dependency Order

## 4.1 Platform Layers

| Layer | Domains | Why they are here |
|---|---|---|
| `L0` | Rulebook and semantic specs | defines invariants, naming, lifecycle, and compatibility semantics |
| `L1` | Brand and Storefront; Identity and Access; Product and Offers; Partner Organizations | namespace, actor, surface, and commercial-policy foundations |
| `L2` | Merchant, Billing, Tax, and Disputes; Risk, Compliance, and Governance | liability, compliance, and anti-abuse foundations |
| `L3` | Commerce and Orders | canonical commercial object layer |
| `L4` | Attribution and Commercial Ownership; Growth Rewards | order-level ownership and non-cash outputs |
| `L5` | Finance and Settlement; Service Access and Entitlements | economic consequences and service delivery |
| `L6` | Analytics and Reporting | derived measurement and export layer |

`L1` must be treated as a contract-first dependency cluster, not as a perfectly linear or fully acyclic subgraph. Mutual reference-dependencies are allowed inside this layer only when they are limited to co-designed reference contracts such as storefront bindings, realm bindings, partner-operator bindings, merchant bindings, and pricebook bindings. Hidden semantic dependencies inside the cluster are not allowed.

Within `L1`, domain existence and binding completeness are different concerns. A storefront core, identity core, product core, or partner-account core may exist before every realm, merchant, or pricebook binding is finalized.

## 4.2 Parallelism Guidance

Parallelizable work begins only after `L1` foundations are stable.

Safe early parallel tracks:

- partner workspace scaffolding;
- storefront engine scaffolding;
- API and auth scope scaffolding;
- analytics event contract design;
- service identity abstraction.

Unsafe early parallel tracks:

- final payout logic before order and attribution contracts stabilize;
- final reporting logic before canonical metric definitions and attribution outputs stabilize;
- channel rollout before realm, entitlement, and settlement semantics stabilize.

---

## 5. Domain Dependency Matrix

## 5.1 Brand And Storefront

| Field | Detail |
|---|---|
| Owns | brands, storefronts, storefront_domains, support/communication/legal profile bindings, surface policy matrix versions |
| Direct upstream dependencies | Rulebook as the foundational input; reference and binding contracts from Product and Offers, Merchant/Billing/Tax/Disputes, and Identity and Access |
| Dependency types | `Foundational` for storefront core, `Policy` for binding completeness |
| Clarification | storefront core does not require every binding to exist first; realm, merchant, and pricebook relationships complete the surface rather than create the domain |
| Provides to | Identity and Access, Commerce and Orders, Partner Organizations, Service Access and Entitlements, Analytics and Reporting |
| Provides contracts | storefront resolution, host mapping, active profiles, legal doc sets, surface policy matrix versions, and binding anchors for realms, merchant profiles, and pricebooks |
| Hard blockers it creates | no realm-aware auth, no storefront-aware pricing, no brand-isolated channels without this domain |

## 5.2 Identity And Access

| Field | Detail |
|---|---|
| Owns | auth_realms, principal classes, sessions, tokens, scopes, role bindings |
| Direct upstream dependencies | Rulebook, Brand and Storefront, Partner Organizations |
| Dependency types | `Foundational`, `Policy` |
| Provides to | Commerce and Orders, Service Access and Entitlements, Risk/Compliance/Governance, Analytics and Reporting |
| Provides contracts | principal identity, realm validation, scope model, partner/admin/service access model |
| Hard blockers it creates | no cross-surface auth, no row-level access, no realm isolation without this domain |

## 5.3 Product And Offers

| Field | Detail |
|---|---|
| Owns | catalog, offers, pricebooks, program eligibility versions |
| Direct upstream dependencies | Rulebook, Brand and Storefront |
| Dependency types | `Policy`, `Foundational` |
| Provides to | Commerce and Orders, Attribution, Growth Rewards, Analytics and Reporting |
| Provides contracts | product definitions, offer versions, pricebook versions, eligibility versions |
| Hard blockers it creates | no quote/order pricing, no program eligibility, no renewal economics without this domain |

## 5.4 Merchant, Billing, Tax, And Disputes

| Field | Detail |
|---|---|
| Owns | merchant_profiles, invoice_profiles, billing_descriptors, tax snapshots, canonical payment_disputes |
| Direct upstream dependencies | Brand and Storefront, Product and Offers, Identity and Access |
| Dependency types | `Foundational`, `Policy`, `Operational` |
| Provides to | Commerce and Orders, Finance and Settlement, Risk/Compliance/Governance, Analytics and Reporting |
| Provides contracts | merchant-of-record, descriptor snapshots, tax behavior, dispute lifecycle and provider normalization |
| Hard blockers it creates | no correct billing liability, no dispute normalization, no tax-safe order snapshots without this domain |

## 5.5 Commerce And Orders

| Field | Detail |
|---|---|
| Owns | quote_sessions, checkout_sessions, orders, order_items, payment_attempts, refunds, commissionability_evaluations, renewal_orders |
| Direct upstream dependencies | Brand and Storefront, Identity and Access, Product and Offers, Merchant/Billing/Tax/Disputes |
| Dependency types | `Foundational`, `Policy`, `Snapshot` |
| Provides to | Attribution, Growth Rewards, Finance and Settlement, Service Access and Entitlements, Analytics and Reporting |
| Provides contracts | canonical commercial records, order snapshots, refund linkage, renewal order lineage |
| Hard blockers it creates | no attribution winner, no settlement liability, no entitlement issuance without order domain |

## 5.6 Attribution And Commercial Ownership

| Field | Detail |
|---|---|
| Owns | attribution_touchpoints, customer_commercial_bindings, order_attribution_results |
| Direct upstream dependencies | Rulebook, Product and Offers, Commerce and Orders, Partner Organizations, Brand and Storefront, Risk/Compliance/Governance |
| Dependency types | `Policy`, `Snapshot`, `Operational` |
| Provides to | Finance and Settlement, Analytics and Reporting, Partner Organizations, Growth Rewards |
| Provides contracts | winner selection, owner source, explainability path, persistent commercial bindings |
| Hard blockers it creates | no payout ownership, no direct-store attribution, no partner-source explainability without this domain |

## 5.7 Growth Rewards

| Field | Detail |
|---|---|
| Owns | growth_reward_allocations for invite, referral credit, bonus days, gift outputs |
| Direct upstream dependencies | Rulebook, Program Compatibility spec, Product and Offers, Commerce and Orders, Risk/Compliance/Governance |
| Dependency types | `Policy`, `Snapshot`, `Operational` |
| Provides to | Finance and Settlement, Analytics and Reporting, Service Access and Entitlements |
| Provides contracts | non-cash output allocation, reward eligibility, reversal hooks |
| Hard blockers it creates | no clean separation between growth outputs and commercial ownership without this domain |

## 5.8 Partner Organizations

| Field | Detail |
|---|---|
| Owns | partner_accounts, partner_account_users, partner roles, program memberships, partner codes, contracts, settlement profiles |
| Direct upstream dependencies | Rulebook, Identity and Access, Brand and Storefront |
| Dependency types | `Foundational`, `Policy` |
| Provides to | Attribution, Finance and Settlement, Risk/Compliance/Governance, Analytics and Reporting |
| Provides contracts | partner identity, workspace membership, code ownership, contractual eligibility |
| Hard blockers it creates | no partner portal, no partner payout ownership, no org-level partner control without this domain |

## 5.9 Finance And Settlement

| Field | Detail |
|---|---|
| Owns | earning_events, earning_holds, earning_adjustments, partner_statements, partner_payout_accounts, settlement_periods, payout_instructions, payout_executions, reserves |
| Direct upstream dependencies | Commerce and Orders, Attribution, Growth Rewards, Partner Organizations, Merchant/Billing/Tax/Disputes, Risk/Compliance/Governance |
| Dependency types | `Financial`, `Operational`, `Snapshot` |
| Provides to | Partner Organizations, Analytics and Reporting, Admin/ops surfaces, Partner portal |
| Provides contracts | accrual, hold, reserve, statement, payout, clawback, liability views |
| Hard blockers it creates | no statement-aware partner surfaces, no payout reconciliation, no partner finance without this domain |

## 5.10 Service Access And Entitlements

| Field | Detail |
|---|---|
| Owns | service_identities, entitlement_grants, device_credentials, provisioning_profiles, access_delivery_channels |
| Direct upstream dependencies | Identity and Access, Commerce and Orders, Growth Rewards, Brand and Storefront |
| Dependency types | `Foundational`, `Snapshot`, `Operational` |
| Provides to | official clients, partner storefronts, Telegram, mobile, desktop, Analytics and Reporting |
| Provides contracts | service access state, provisioning decisions, entitlement lifecycle |
| Hard blockers it creates | no unified service-consumption layer, no realm-aware access delivery without this domain |

## 5.11 Risk, Compliance, And Governance

| Field | Detail |
|---|---|
| Owns | risk_subjects, risk_identifiers, risk_links, risk_reviews, risk_decisions, accepted_legal_documents, partner_traffic_declarations, creative_approvals, dispute_cases, governance actions |
| Direct upstream dependencies | Identity and Access, Brand and Storefront, Partner Organizations, Merchant/Billing/Tax/Disputes, Commerce and Orders |
| Dependency types | `Foundational`, `Operational`, `Policy`, `Snapshot` |
| Provides to | Attribution, Growth Rewards, Finance and Settlement, Analytics and Reporting, all surface domains |
| Provides contracts | eligibility gates, abuse controls, legal acceptance evidence, traffic and creative governance, order-linked operational case overlays |
| Hard blockers it creates | no fraud-safe eligibility, no order-aware abuse detection, no cross-realm abuse detection, no governance actions without this domain |

## 5.12 Analytics And Reporting

| Field | Detail |
|---|---|
| Owns | analytical marts, dashboards, exports, reconciliations, alert definitions |
| Direct upstream dependencies | all bounded contexts, especially Commerce, Attribution, Growth Rewards, Finance and Settlement, Risk/Compliance/Governance |
| Dependency types | `Reporting`, `Snapshot` |
| Provides to | executives, finance, partner managers, risk, support, partner portal |
| Provides contracts | canonical metrics, exports, alerting, explainability reporting |
| Hard blockers it creates | no shared metric truth, no trustworthy partner reporting, no liability and quality dashboards without this domain |

---

## 6. Critical Seam Objects

These seam objects require explicit ownership and contract discipline because they cross more than one bounded context.

## 6.1 partner_payout_accounts

| Aspect | Decision |
|---|---|
| Canonical owner | Finance and Settlement |
| Referenced by | Partner Organizations, Partner portal, Admin ops |
| API family | Finance and Settlement APIs |
| Primary dependencies | Identity and Access, Partner Organizations, Risk/Compliance/Governance |
| Why it matters | payout execution cannot be treated as a generic wallet action |

## 6.2 partner_traffic_declarations

| Aspect | Decision |
|---|---|
| Canonical owner | Risk, Compliance, and Governance |
| Referenced by | Partner Organizations, Attribution, Analytics |
| API family | Attribution/Growth and Risk/Governance surfaces |
| Primary dependencies | Partner Organizations, Brand and Storefront |
| Why it matters | approval-only traffic lanes require declared source context before safe scaling |

## 6.3 creative_approvals

| Aspect | Decision |
|---|---|
| Canonical owner | Risk, Compliance, and Governance |
| Referenced by | Partner Organizations, Campaigns, Analytics |
| API family | Attribution/Growth and Risk/Governance surfaces |
| Primary dependencies | Partner Organizations, Brand and Storefront |
| Why it matters | claims control and creative governance cannot live only in campaign metadata |

## 6.4 dispute_cases

| Aspect | Decision |
|---|---|
| Canonical owner | Risk, Compliance, and Governance |
| Referenced by | Merchant/Billing/Tax/Disputes, Finance and Settlement, Support |
| API family | Risk/Governance surfaces |
| Primary dependencies | canonical `payment_dispute`, Partner Organizations, Identity and Access |
| Why it matters | operational case handling is not the same thing as provider dispute state |

## 6.5 payment_dispute

| Aspect | Decision |
|---|---|
| Canonical owner | Merchant, Billing, Tax, and Disputes |
| Referenced by | Finance and Settlement, Risk/Compliance/Governance, Analytics |
| API family | Merchant/Billing/Dispute APIs |
| Primary dependencies | Commerce and Orders, merchant profiles, provider payment references |
| Why it matters | inquiries, chargebacks, and dispute outcomes need one normalized platform object |

## 6.6 surface_policy_matrix_versions

| Aspect | Decision |
|---|---|
| Canonical owner | Brand and Storefront |
| Referenced by | Product and Offers, Commerce, Growth Rewards, Surface clients |
| API family | Brand/Storefront and policy-management APIs |
| Primary dependencies | Rulebook, Product and Offers |
| Why it matters | channel behavior cannot be left to frontend conditionals |

## 6.7 accepted_legal_documents

| Aspect | Decision |
|---|---|
| Canonical owner | Risk, Compliance, and Governance |
| Referenced by | Identity and Access, Commerce and Orders, Merchant/Billing/Tax/Disputes |
| API family | Policy acceptance and legal-document APIs |
| Primary dependencies | Brand and Storefront, Identity and Access |
| Why it matters | legal acceptance must be surface-aware, actor-aware, and auditable |

---

## 7. Direct-Dependency Summary Matrix

The following compact matrix shows **direct** upstream dependencies only.

Rows represent the dependent domain; columns represent direct upstream dependencies.

Legend:

- `X` = direct dependency
- blank = no direct dependency

For `L1` domains, an `X` may represent a co-designed reference contract required for binding completeness rather than a hard sequential build gate.

| Domain | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. Brand and Storefront |  | X | X | X |  |  |  |  |  |  |  |  |
| 2. Identity and Access | X |  |  |  |  |  |  | X |  |  |  |  |
| 3. Product and Offers | X |  |  |  |  |  |  |  |  |  |  |  |
| 4. Merchant/Billing/Tax/Disputes | X | X | X |  |  |  |  |  |  |  |  |  |
| 5. Commerce and Orders | X | X | X | X |  |  |  |  |  |  |  |  |
| 6. Attribution and Commercial Ownership | X |  | X |  | X |  |  | X |  |  | X |  |
| 7. Growth Rewards |  |  | X |  | X |  |  |  |  |  | X |  |
| 8. Partner Organizations | X | X |  |  |  |  |  |  |  |  |  |  |
| 9. Finance and Settlement |  |  |  | X | X | X | X | X |  |  | X |  |
| 10. Service Access and Entitlements | X | X |  |  | X |  | X |  |  |  |  |  |
| 11. Risk/Compliance/Governance | X | X |  | X | X |  |  | X |  |  |  |  |
| 12. Analytics and Reporting | X | X | X | X | X | X | X | X | X | X | X |  |

Interpretation:

- Domains `1-4` are upstream-heavy foundation domains.
- Domain `5` is the commercial center.
- Domains `6-7` derive order-level ownership and non-cash outputs.
- Domains `9-10` turn commercial outcomes into money and service access.
- Domain `11` constrains eligibility and governs operational risk.
- Domain `12` is fully downstream.

---

## 8. Blocking Decisions Before Detailed Phase Planning

The following questions must be treated as dependency blockers before writing the detailed phased implementation plan:

1. Which exact policy layers are effective-dated versus only snapshotted?
2. Which surface-policy overrides are allowed on partner storefronts?
3. Which risk decisions block eligibility versus only block payout release?
4. Which renewal scenarios inherit provenance but not payout eligibility?
5. Which clients can consume shared service identities without violating brand isolation?
6. Which operational overlay objects need their own first-class APIs versus subresources?

---

## 9. Acceptance Conditions

This matrix is acceptable only when:

- every bounded context has explicit upstream and downstream dependencies;
- seam objects have a canonical owner;
- the eventual phased implementation plan can be derived from this graph without inventing new hidden prerequisites;
- the matrix preserves the same domain language as the target-state architecture and domain specs.
