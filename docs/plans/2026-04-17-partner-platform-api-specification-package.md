# CyberVPN Partner Platform API Specification Package

**Date:** 2026-04-17  
**Status:** API specification package  
**Purpose:** define the canonical API surface families, contract principles, endpoint groups, auth model, idempotency rules, error semantics, async job patterns, and integration expectations for the five-lane CyberVPN partner platform.

---

## 1. Document Role

This document defines the API package at the platform-contract level.

It does not attempt to inline every OpenAPI path item in prose. Instead it defines:

- the canonical API families;
- resource groups;
- auth and scope expectations;
- idempotency and concurrency rules;
- response and error conventions;
- async job and webhook patterns;
- reporting and postback contracts.

Detailed path-level OpenAPI can be generated later from implementation contracts, but it must conform to this document.

The resource groups defined below are representative and not exhaustive. Domain-specific API specs may add narrower subresources as long as they preserve the package rules in this document.

---

## 2. API Surface Families

The platform exposes five API surface families:

| Surface family | Primary caller | Auth model |
|---|---|---|
| Customer APIs | customer-facing web, mobile, desktop, Telegram | customer session tokens |
| Partner Workspace APIs | partner portal and partner team tools | partner-operator tokens |
| Admin / Internal Ops APIs | admin panel and internal tooling | admin tokens |
| Service / Integration APIs | internal services, jobs, partner integrations | service tokens or scoped API credentials |
| Reporting / Export APIs | BI, partner reports, exports | partner reporting tokens or admin/service tokens |

Each family must differ in:

- principal type;
- realm validation;
- row-level visibility;
- writable resources;
- audit requirements.

---

## 3. Canonical Contract Principles

1. API contracts are resource-oriented and versioned.
2. Auth scope, realm, and workspace validation happen server-side.
3. Commit-style operations are idempotent.
4. Finalized commercial and financial records expose immutable snapshots plus adjustments.
5. Long-running operations return job or operation handles.
6. Sensitive write operations support maker-checker or approval states where required.
7. Reporting endpoints enforce row-level visibility and workspace restrictions.
8. Provider-specific payment and dispute terminology is normalized into canonical platform objects.

---

## 4. Canonical Resource Groups

## 4.1 Brand And Storefront

- `/api/v1/brands`
- `/api/v1/storefronts`
- `/api/v1/storefront-profiles`
- `/api/v1/surface-policies`
- `/api/v1/legal-documents`

Representative responsibilities:

- resolve active storefront by host or explicit context;
- expose active brand, support, communication, merchant, and legal context;
- manage surface-level policy matrices;
- expose legal document versions for acceptance flows.

## 4.2 Identity And Access

- `/api/v1/auth`
- `/api/v1/realms`
- `/api/v1/principals`
- `/api/v1/partner-workspaces`
- `/api/v1/roles`
- `/api/v1/tokens`

Representative responsibilities:

- login and logout;
- realm-aware session issuance;
- password reset and verification;
- partner workspace membership;
- scope introspection where required;
- service credential issuance and rotation.

## 4.3 Product, Offer, And Pricing

- `/api/v1/offers`
- `/api/v1/pricebooks`
- `/api/v1/program-eligibility`
- `/api/v1/catalog`

Representative responsibilities:

- product and offer retrieval by surface;
- pricebook resolution by storefront, currency, and region;
- program eligibility discovery;
- effective-date-aware pricing and offer responses.

## 4.4 Commerce And Orders

- `/api/v1/quotes`
- `/api/v1/checkout-sessions`
- `/api/v1/orders`
- `/api/v1/order-items`
- `/api/v1/payment-attempts`
- `/api/v1/refunds`

Representative responsibilities:

- create and retrieve quote sessions;
- create and retrieve checkout sessions;
- commit orders;
- attach payment attempts;
- submit refunds and track refund lifecycle.

## 4.5 Attribution And Growth

- `/api/v1/attribution`
- `/api/v1/growth-rewards`
- `/api/v1/partner-codes`
- `/api/v1/campaigns`
- `/api/v1/creative-assets`
- `/api/v1/traffic-declarations`
- `/api/v1/creative-approvals`

Representative responsibilities:

- resolve attribution evidence;
- record or inspect bindings;
- allocate growth rewards;
- manage partner codes and code versions;
- manage campaign and creative assets;
- capture partner traffic declarations;
- review or publish creative approval state.

## 4.6 Merchant, Billing, Tax, And Disputes

- `/api/v1/merchant-profiles`
- `/api/v1/invoice-profiles`
- `/api/v1/billing-descriptors`
- `/api/v1/payment-disputes`

Representative responsibilities:

- resolve merchant-of-record context;
- expose invoice and billing descriptors;
- normalize inquiry and chargeback states through canonical `payment_dispute` resources.

## 4.7 Finance And Settlement

- `/api/v1/partner-statements`
- `/api/v1/partner-payout-accounts`
- `/api/v1/payouts`
- `/api/v1/settlement-periods`
- `/api/v1/reserves`

Representative responsibilities:

- statement retrieval and reconciliation;
- payout-account linking, verification, and lifecycle management;
- payout execution workflows;
- reserve and hold visibility;
- settlement-period reporting.

Canonical rule:

- `partner_payout_account` is a first-class API resource and not only a nested field under payout execution;
- payout instructions and payout executions must reference a `partner_payout_account_id`;
- payout-account verification, suspension, archival, and default-selection are managed on `/api/v1/partner-payout-accounts`;
- `/api/v1/payouts` manages payout instructions, approval, execution, and execution history, not the identity of the payout destination itself.

Representative payout-account subresources may include:

- `/api/v1/partner-payout-accounts/{id}`
- `/api/v1/partner-payout-accounts/{id}/verify`
- `/api/v1/partner-payout-accounts/{id}/suspend`
- `/api/v1/partner-payout-accounts/{id}/archive`
- `/api/v1/partner-payout-accounts/{id}/make-default`

## 4.8 Service Identity And Entitlements

- `/api/v1/service-identities`
- `/api/v1/entitlements`
- `/api/v1/provisioning`

Representative responsibilities:

- grant and revoke entitlements;
- provision access profiles;
- query service-consumption state across channels.

## 4.9 Risk And Governance

- `/api/v1/policy-acceptance`
- `/api/v1/risk-reviews`
- `/api/v1/risk-decisions`
- `/api/v1/governance-actions`
- `/api/v1/contracts`
- `/api/v1/dispute-cases`

Representative responsibilities:

- capture acceptance evidence;
- start and resolve risk reviews;
- trigger payout freezes, code suspension, reserve extension, or manual overrides;
- expose contract and governance state where required;
- manage operational dispute cases linked to canonical payment disputes.

## 4.10 Reporting

- `/api/v1/reporting`
- `/api/v1/exports`
- `/api/v1/postbacks`

Representative responsibilities:

- aggregated metrics;
- partner export jobs;
- postback delivery status;
- audit and explainability reporting.

---

## 5. Auth, Tokens, And Scopes

## 5.1 Token Classes

The platform requires:

- customer session tokens;
- partner-operator session tokens;
- admin session tokens;
- service tokens;
- reporting tokens;
- postback credentials.

## 5.2 Scope Principles

Scopes express resource access intent, while permissions express concrete actions.

Examples of scope families:

- `customer:orders:read`
- `customer:checkout:write`
- `partner:workspace:read`
- `partner:statements:read`
- `partner:payouts:write`
- `admin:risk:write`
- `service:postbacks:write`
- `reporting:partner:read`

## 5.3 Scope Rules

Canonical rules:

- scopes are least-privilege;
- row-level restrictions are enforced server-side;
- auth realm and workspace context are validated independently of raw token presence;
- service-to-service tokens are not interchangeable with human session tokens;
- reporting and postback tokens are separately scoped.

---

## 6. Idempotency And Concurrency

## 6.1 Operations Requiring Idempotency

The following must require idempotency keys or equivalent replay-safe semantics:

- quote creation where side effects exist;
- checkout commit;
- refund submission;
- payout execution submission;
- postback ingestion;
- governance actions with financial consequences.

## 6.2 Conflict Rules

If the same logical write is replayed:

- the API must return the original resulting resource or operation state;
- duplicate side effects must not occur;
- response semantics must remain stable enough for retries.

## 6.3 Concurrency Rules

Resources that require optimistic concurrency or serialization:

- policy publications;
- pricebook activation;
- statement close;
- payout execution transitions;
- risk review decisions;
- entitlement grant finalization.

---

## 7. Canonical Response Semantics

## 7.1 Resource Responses

Canonical resource responses should include:

- `id`
- `object_type`
- `version` where relevant
- `created_at`
- `updated_at`
- immutable snapshot fields where finalized
- adjustment or linked-operation references where mutable history exists

## 7.2 List Responses

List responses should support:

- cursor or offset pagination;
- deterministic ordering;
- stable filtering fields;
- realm or workspace scoping;
- expansion where justified.

## 7.3 Explainability Fields

Certain objects must expose explainability payloads, especially:

- `order_attribution_result`
- `growth_reward_allocation`
- `commissionability_evaluation`
- `risk_decision`
- `partner_statement_adjustment`

---

## 8. Canonical Error Model

Error responses should normalize into a platform envelope with:

- machine-readable code;
- human-readable summary;
- optional field-level detail;
- correlation or request id;
- retryability hint where relevant;
- actor or scope failure reason where relevant.

Representative classes:

- auth failure;
- realm mismatch;
- scope denied;
- validation error;
- policy conflict;
- stale quote or stale policy version;
- idempotency conflict;
- resource state conflict;
- not found;
- unsupported operation for current surface or lane.

---

## 9. Async Jobs And Long-Running Operations

Operations that may run asynchronously:

- export generation;
- payout batch execution;
- analytical refresh;
- attribution replay;
- statement regeneration;
- risk review enrichment;
- large-scale legal acceptance backfill.

Async responses should return:

- `job_id` or `operation_id`
- initial status
- polling or callback location
- submitted-by actor
- dedupe key where relevant

---

## 10. Disputes And Provider Normalization

`payment_dispute` is the canonical dispute resource.

Provider-specific concepts such as:

- inquiry;
- warning;
- chargeback;
- dispute reversal;
- second chargeback;
- provider dispute fee state

must be represented as:

- subtype;
- status;
- provider snapshot;
- outcome class;
- financial consequence links.

`dispute_case` is a separate internal operational overlay used for:

- evidence collection;
- support and finance workflows;
- governance or escalation tracking.

It must link to one or more canonical `payment_dispute` objects rather than replacing them.

This keeps disputes unified across providers while preserving provider-specific evidence and timelines.

---

## 11. Webhooks, Events, And Postbacks

## 11.1 Internal Event Expectations

Platform events must be:

- versioned;
- idempotent;
- replay-safe;
- actor-attributed;
- correlated to canonical resource ids.

## 11.2 Outbound Partner Postbacks

Partner postbacks must support:

- scoped credentials;
- replay-safe delivery ids;
- signature verification;
- retry with bounded backoff;
- delivery status inspection;
- support tooling for replay and disablement.

## 11.3 Webhook Security

Webhook and postback security must include:

- signed payloads;
- secret rotation;
- timestamp or nonce validation;
- audit of replay attempts.

---

## 12. API Family To Principal Matrix

| API family | Customer | Partner operator | Admin | Service |
|---|---|---|---|---|
| Customer APIs | yes | no | no | limited |
| Partner Workspace APIs | no | yes | limited | limited |
| Admin APIs | no | no | yes | limited |
| Service APIs | no | no | limited | yes |
| Reporting APIs | limited | yes | yes | yes |

This matrix is only the high-level access shape. Detailed per-endpoint scopes belong in the eventual OpenAPI and authorization package.

---

## 13. Acceptance Conditions

The API package is acceptable only when:

- every core domain has a clearly owned API family;
- auth, scope, and realm rules are explicit;
- commit-style operations are idempotent;
- disputes are normalized into canonical `payment_dispute` resources;
- reporting and partner APIs honor row-level isolation;
- async operations expose explicit job semantics;
- eventual OpenAPI contracts can be generated without violating these package rules.
