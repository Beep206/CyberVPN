# CyberVPN Partner Platform Target-State Architecture

**Date:** 2026-04-17  
**Status:** Canonical target-state architecture  
**Purpose:** define the long-lived platform model for CyberVPN partner, growth, storefront, identity, attribution, settlement, risk, and reporting domains without mixing that target state with rollout sequencing.

---

## 1. Document Role

This document is the canonical target-state specification for the CyberVPN partner platform.

It defines:

- platform boundaries;
- domain invariants;
- canonical actor and principal models;
- multi-brand operating model;
- commerce, attribution, settlement, entitlement, and risk domains;
- channel and API expectations;
- non-functional requirements for a durable platform.

This document does **not** act as the rollout plan.

Delivery sequencing, migration, cutover, QA, rollback, and phased repository execution are intentionally moved into the companion document:

- `docs/plans/2026-04-17-partner-platform-delivery-program.md`

This target-state document is designed to remain stable even if delivery phases change.

---

## 2. Executive Position

CyberVPN should operate a partner platform, not a collection of loosely related referral features.

The platform must support:

- two consumer-growth lanes;
- three partner-revenue lanes;
- multi-brand storefronts;
- backend-owned attribution;
- policy-versioned partner economics;
- partner workspaces and finance operations;
- separate consumer and partner financial domains;
- full-channel parity across web, Telegram, mobile, desktop, and partner APIs;
- strict brand and auth-realm isolation with cross-realm risk visibility.

The platform intentionally canonizes **five** lanes:

- Invite / Gift
- Consumer Referral Credits
- Creator / Affiliate
- Performance / Media Buyer
- Reseller / API / Distribution

---

## 3. Program Families

## 3.1 Consumer Growth Programs

These programs are customer-growth mechanisms, not partner-revenue programs.

| Lane | Primary actor | Reward type | Withdrawable | Cash owner |
|---|---|---|---|---|
| Invite / Gift | existing customer | bonus days, extra invites, non-cash perks | no | never |
| Consumer Referral Credits | normal customer | fixed non-withdrawable wallet credits | no | never |

Consumer growth programs exist to drive:

- activation;
- social recommendation;
- retention;
- LTV support;
- upgrade discovery into approved affiliate status.

They must not be modelled as partner finance.

## 3.2 Partner Revenue Programs

These programs are commercial acquisition and distribution programs.

| Lane | Primary actor | Reward type | Withdrawable | Cash owner |
|---|---|---|---|---|
| Creator / Affiliate | approved creator or publisher | revshare earnings | yes, after hold | yes |
| Performance / Media Buyer | approved paid-acquisition partner | custom CPA or hybrid | yes, after longer hold | yes |
| Reseller / API / Distribution | approved distributor | markup and/or hybrid earnings | yes | yes |

An optional one-level sub-affiliate model may exist only as a **derived earnings overlay** on top of partner revenue programs. It must not be treated as an acquisition owner.

## 3.3 Program Family Separation

Consumer growth programs and partner revenue programs must remain separate across:

- actor model;
- permissions;
- ledgers;
- payout eligibility;
- compliance requirements;
- dispute handling;
- portal surfaces;
- reporting semantics.

Invite and consumer referral should share platform primitives where useful, but they must not be collapsed into the same partner domain semantics as creators, media buyers, or resellers.

---

## 4. Canonical Invariants

The following rules are non-negotiable.

1. One `order` has at most one cash payout owner.
2. `Invite / Gift` never becomes a cash payout owner.
3. Growth rewards and commercial ownership are separate concepts.
4. `explicit_code > passive_click > default_referral_state`.
5. Persistent reseller or storefront commercial bindings outrank later incidental affiliate clicks.
6. Official CyberVPN-branded surfaces never expose self-serve markup.
7. Partner-branded storefront pricing is native storefront pricing, not “base CyberVPN price plus markup” rendered to the user.
8. Referral-earned wallet credit never produces recursive referral or partner payouts.
9. `extra_device` may be commissionable; `dedicated_ip` is excluded from open programs unless explicitly allowed by typed policy.
10. Tiering is driven by quality and economics, not only raw client counts.
11. Critical commerce and payout logic lives in typed, versioned policy objects, not mutable `system_config` JSON blobs.
12. The canonical commercial object is `order`, not `payment`.
13. Partner codes do not define arbitrary precedence. Precedence is resolved by a deterministic platform engine.
14. There is no classical MLM.

---

## 5. Bounded Contexts

| Context | Core responsibility |
|---|---|
| Brand and Storefront | brands, storefronts, domains, support and communications surfaces |
| Identity and Access | principals, realms, sessions, auth, permissions, API credentials |
| Product and Offers | product catalog, offers, pricebooks, eligibility |
| Merchant, Billing, Tax, and Disputes | merchant-of-record, invoices, taxes, billing descriptors, refunds, chargebacks |
| Commerce and Orders | quotes, checkout sessions, orders, order items, renewals, refunds |
| Attribution and Commercial Ownership | touchpoints, bindings, attribution results, owner resolution |
| Growth Rewards | invite rewards, referral credits, non-cash benefits |
| Partner Organizations | partner accounts, partner users, roles, codes, memberships, contracts |
| Finance and Settlement | statements, holds, adjustments, reserves, payouts, reconciliation |
| Service Access and Entitlements | service identities, entitlements, provisioning, delivery channels |
| Risk, Compliance, and Governance | risk graph, policy acceptance, declarations, reviews, disputes |
| Analytics and Reporting | events, metric definitions, marts, dashboards, exports, alerts |

Each bounded context must own its own invariants and public contracts. Cross-context coupling must happen through explicit APIs, events, and immutable snapshots.

---

## 6. Multi-Brand Operating Model

## 6.1 Core Surface Entities

The platform must treat these entities as distinct:

| Entity | Meaning |
|---|---|
| `brands` | visual identity, naming, positioning, copy direction |
| `storefronts` | concrete public sales or self-service surfaces |
| `auth_realms` | identity namespaces for login, registration, session, and credential uniqueness |
| `merchant_profiles` | merchant-of-record, billing, invoices, tax, descriptors |
| `support_profiles` | support channels, SLA, escalation routing, help-center routing |
| `communication_profiles` | sender domains, transactional messaging, push, SMS, bot copy |
| `storefront_legal_doc_sets` | terms, privacy, refund, disclosure, and policy documents active on that surface |

These entities must not be collapsed into a single “storefront” abstraction.

## 6.2 Relationship Model

Recommended rules:

- one `brand` may own many `storefronts`;
- one `auth_realm` may serve multiple storefronts of the same brand if policy allows;
- one `storefront` maps to one `auth_realm`;
- one `storefront` maps to one active `merchant_profile`;
- one `storefront` maps to one `support_profile`;
- one `storefront` maps to one `communication_profile`;
- one `storefront` maps to one active `legal_doc_set`.

## 6.3 Account Model

The canonical account rule is:

- a customer account belongs to exactly one `auth_realm_id`;
- a customer account stores `origin_storefront_id`;
- `quote_session`, `checkout_session`, `order`, and session context carry `storefront_id`;
- a customer account may interact with multiple storefronts inside the same realm only if realm policy explicitly allows it.

This replaces the more rigid idea that an account belongs to exactly one storefront forever.

## 6.4 Brand Isolation Rules

The platform must enforce:

- partner-branded accounts do not automatically log in to official CyberVPN;
- official CyberVPN credentials do not automatically log in to partner-branded storefronts;
- cookie namespaces, domains, and token audiences are realm-aware;
- support and communications routing are storefront-aware;
- legal disclosures are storefront-aware;
- reporting is storefront-aware;
- risk analysis can correlate cross-realm abuse without breaking customer-visible brand isolation.

---

## 7. Identity And Access Model

## 7.1 Principal Classes

The platform must support four principal classes:

| Principal class | Description |
|---|---|
| `customer` | end-user identity for buying and using services |
| `partner_operator` | external partner workspace user |
| `admin` | internal CyberVPN staff user |
| `service` | machine-to-machine or automation actor |

Identity design must not assume that all non-admin actors are customers.

## 7.2 Realm Types

Recommended realm types:

- `customer`
- `partner`
- `admin`
- `service`

Realm type may be explicit in the identity domain or encoded through equivalent structures, but the platform must preserve the distinction.

## 7.3 Partner Organization Identity

Partner access must not be modelled as “customer user upgraded into partner mode” only.

The canonical model requires:

- `partner_accounts`
- `partner_account_users`
- `partner_account_roles`
- `partner_permissions`
- `contracts`
- `tax_profiles`
- `kyb_kyc_status`
- `settlement_profiles`

Partners are organizations, not only individuals.

## 7.4 Cross-Realm Rules

The platform must allow:

- the same email address to exist in multiple auth realms;
- the same password value to be used independently in multiple realms;
- the same human to maintain separate accounts under different brands.

The platform must prevent:

- cross-realm automatic login;
- cross-realm wallet sharing;
- cross-realm referral-credit stacking;
- cross-realm silent trial duplication.

Any future explicit account-linking feature must be opt-in, policy-controlled, audited, and separate from login.

---

## 8. Product, Offer, And Pricing Model

## 8.1 Four Commercial Layers

The platform must separate these four layers:

| Layer | Responsibility |
|---|---|
| `product_catalog` | what the product is |
| `offer_layer` | how the product is commercially packaged |
| `pricebooks` | how much it costs on a specific surface |
| `program_eligibility_layer` | which growth or partner programs may apply |

## 8.2 Product Catalog

The product catalog contains stable product facts such as:

- plan family;
- duration;
- base entitlements;
- connection modes;
- device limits;
- server pool;
- support SLA;
- add-on compatibility.

## 8.3 Offer Layer

The offer layer contains commercial overlays such as:

- invite bundle;
- trial eligibility;
- gift eligibility;
- referral eligibility;
- renewal incentives;
- channel restrictions;
- visibility rules.

Offer-layer properties must not be forced into the same permanent semantics as the product catalog if they vary by channel or brand.

## 8.4 Pricebooks

Pricebooks define:

- storefront;
- merchant profile;
- region and currency;
- visible price;
- discount rules;
- price overrides;
- included add-ons;
- renewal pricing policy.

## 8.5 Program Eligibility Layer

Program eligibility determines whether a SKU or add-on may participate in:

- invite;
- referral credits;
- creator affiliate;
- performance;
- reseller;
- renewal commissionability;
- add-on commissionability.

This layer must remain explicit and queryable.

## 8.6 Versioned Commercial Layers

Policy-version discipline must extend beyond partner-code economics.

The target-state platform should treat the following as versionable, effective-dated layers:

- `pricebook_versions`
- `offer_versions`
- `program_eligibility_versions`
- `surface_policy_matrix_versions`
- `storefront_legal_doc_set_versions`
- `storefront_profile_binding_versions`

Orders should still snapshot final commercial state, but these versioned layers are required for operational explainability, audit, and controlled publication workflows.

---

## 9. Merchant, Billing, Tax, Refund, And Chargeback Model

## 9.1 Merchant Of Record

Every commercial surface must resolve a single merchant-of-record model for each order.

Each `order` must snapshot:

- `merchant_profile_id`
- `invoice_profile_id`
- `billing_descriptor`
- `tax_profile_id`
- `chargeback_liability_profile`
- `refund_responsibility_profile`
- `support_profile_id`

This is required so the platform can always answer:

- who sold the order;
- who issued the invoice or receipt;
- who handles refunds;
- who absorbs chargeback liability;
- which billing name or descriptor the customer should see;
- which support channel owns the post-payment relationship.

## 9.2 Merchant Profiles

`merchant_profiles` must define:

- merchant legal identity;
- descriptor configuration;
- settlement account or liable account;
- supported currencies;
- invoice and receipt behavior;
- jurisdictional tax behavior;
- refund authority model;
- chargeback liability model.

If a storefront is partner-branded while the merchant of record remains CyberVPN, that must be explicit in customer-visible disclosures, billing descriptors, invoices, refunds, and support routing.

## 9.3 Billing And Tax

The platform requires first-class support for:

- `invoice_profiles`
- `tax_calculation_snapshots`
- `billing_descriptors`

Pricebooks must define whether visible prices are:

- gross or net;
- tax-inclusive or tax-exclusive;
- region-specific or global;
- consumer or B2B specific.

Tax and invoice snapshots must be captured on the order so later refunds, disputes, and statements do not depend on mutable current tax rules.

## 9.4 Refunds And Chargebacks

The platform requires first-class support for:

- `refunds`
- `payment_disputes`

Refund and dispute handling must be tied to the merchant-of-record and liability model, not inferred indirectly from storefront branding alone.

`payment_disputes` is the canonical dispute object.

`chargeback` is not a separate parallel domain object by default. It is a dispute subtype, provider-specific stage, or final dispute outcome class represented through the `payment_disputes` lifecycle and snapshots.

Chargeback and dispute design must assume:

- inquiries and formal disputes are different lifecycle stages;
- disputes may debit the liable balance before the final outcome;
- partially refunded transactions can still be fully disputed;
- dispute evidence and outcomes must be retained immutably;
- finance and support need a single dispute object model across providers.

## 9.5 Billing Responsibility Rules

The platform must keep these rules explicit:

1. Merchant-of-record determines invoice, receipt, and payment descriptor behavior.
2. Refund authority and chargeback liability must be stored as policy, not guessed from the brand.
3. A partner-branded storefront does not automatically imply partner merchant-of-record status.
4. Support responsibility may differ from merchant-of-record, but the mapping must be explicit and auditable.

---

## 10. Commerce And Order Domain

## 10.1 Canonical Commercial Object

The canonical commercial object is `order`.

`payment_attempt` is a settlement attempt against an order. It is not the canonical source for ownership or payouts.

## 10.2 Required Order-Domain Entities

The target-state order domain includes:

- `quote_sessions`
- `checkout_sessions`
- `orders`
- `order_items`
- `payment_attempts`
- `refunds`
- `cancellations`
- `renewal_orders`
- `adjustments`
- `commissionability_evaluations`

## 10.3 Order Responsibilities

`order` must own or snapshot:

- customer principal and auth realm;
- storefront and merchant profile;
- line items and pricing snapshot;
- applied codes and policies;
- attribution result;
- growth reward allocation references or snapshot;
- entitlement result;
- settlement status;
- refund and adjustment history.

## 10.4 Why This Separation Is Mandatory

This separation is required because:

- one order may have multiple payment attempts;
- one order may be partially covered by wallet spend;
- one order may expire without payment;
- one order may be renewed automatically;
- payouts must be calculated on commercial state, not gateway retry noise;
- attribution and growth decisions must remain reproducible after payment retries and refunds.

---

## 11. Attribution, Bindings, And Growth Rewards

## 11.1 Four-Layer Resolution Model

The target-state platform must separate four layers:

1. `attribution_touchpoints`
2. `customer_commercial_bindings`
3. `order_attribution_results`
4. `growth_reward_allocations`

They must not be collapsed into one generic ownership table.

## 11.2 Attribution Touchpoints

`attribution_touchpoints` are append-only evidence records such as:

- passive clicks;
- explicit code entry;
- deep links;
- QR scans;
- invite redemptions;
- storefront origin;
- campaign parameters;
- postbacks;
- approved manual support actions.

They are evidence, not payout outcomes.

## 11.3 Customer Commercial Bindings

`customer_commercial_bindings` capture persistent commercial relationships such as:

- reseller binding;
- storefront default owner binding;
- long-lived commercial owner constraints;
- approved manual reassignments;
- contract-driven ownership assignments.

Bindings are not the same thing as touchpoints.

## 11.4 Order Attribution Results

`order_attribution_results` are immutable per-order snapshots containing:

- winning commercial owner;
- owner type;
- owner source;
- evidence used;
- binding used;
- policy versions used;
- rule path;
- explainability payload;
- timestamps.

Once an order is finalized, the attribution result must remain reproducible.

## 11.5 Growth Reward Allocations

`growth_reward_allocations` are separate from commercial ownership and may include one or more outputs tied to the same order, referral action, or invite action:

- invite reward;
- referral credit;
- bonus days;
- gift bonus.

Growth rewards may coexist with a commercial owner, but they do not convert into that commercial owner.

## 11.6 Canonical Enums

Commercial owner type:

- `none`
- `affiliate`
- `performance`
- `reseller`
- `direct_store`

Commercial owner semantics:

- `none` = no commercial owner resolved or no payout-relevant owner exists for the order
- `direct_store` = first-party direct commercial ownership for analytics, provenance, and direct-commerce reporting, without partner payout semantics

Owner source or binding reason:

- `explicit_code`
- `passive_click`
- `persistent_reseller_binding`
- `storefront_default`
- `manual_override`

Growth reward type:

- `invite_reward`
- `referral_credit`
- `bonus_days`
- `gift_bonus`

This is intentionally cleaner than mixing growth rewards, owner sources, and commercial owners into one enum.

## 11.7 Precedence Engine

Precedence must be resolved by a global deterministic engine. Partner codes may expose capability flags, but they must not define arbitrary custom precedence.

The engine must always preserve these rules:

- explicit code outranks passive click;
- persistent reseller or storefront commercial binding outranks incidental affiliate touch;
- growth rewards do not create cash-owner status;
- manual overrides require audit and actor attribution.

---

## 12. Program Compatibility, Stacking, And Qualifying Events

## 12.1 Stacking Principles

The platform must evaluate stacking through typed compatibility rules, not ad hoc frontend logic.

Canonical principles:

1. Only one commercial discount instrument may reduce merchandise price unless an explicit policy says otherwise.
2. Wallet spend is a settlement instrument, not a discount instrument.
3. Growth rewards may be produced by an order without becoming its cash owner.
4. Non-withdrawable credit usage must not bootstrap new cash payouts.
5. Surface policy may restrict external code override even when the backend generally supports codes.

## 12.2 Baseline Compatibility Matrix

| Combination | Default rule |
|---|---|
| promo + creator code | not stackable by default |
| consumer referral discount + creator code | not stackable |
| consumer referral discount + reseller code | not stackable |
| wallet spend + one eligible discount instrument | stackable |
| wallet spend + non-withdrawable referral credit + partner payout | order may complete, but partner payout requires positive commissionable net amount |
| invite reward + commercial owner | allowed |
| partner storefront default owner + external creator code | blocked by default unless storefront policy explicitly allows override |

## 12.3 Qualifying First Payment

A qualifying first payment must satisfy all of the following:

- eligible offer and SKU;
- eligible program policy at order time;
- positive commissionable net paid amount after non-withdrawable credits are excluded;
- not voided, fully refunded, or fraud-rejected;
- not classified as self-purchase or abuse by risk policy.

An order that is economically free because it is fully covered by non-withdrawable credits does not qualify as a commissionable first payment.

## 12.4 Partial Refunds And Adjustments

Partial refunds, post-settlement corrections, and chargebacks must flow through typed adjustment policies so that:

- growth rewards can be reversed if policy requires;
- partner earnings can be clawed back proportionally;
- statements remain auditable;
- explainability survives after settlement changes.

---

## 13. Renewal Ownership And Renewal Economics

## 13.1 Renewal Orders

All renewals, whether automatic or manually initiated, must be represented as `renewal_orders`.

Renewals are new orders linked to prior commercial context, not mutations of the original order.

## 13.2 Renewal Ownership Rules

Default rules:

1. Renewal ownership inherits from the originating commissionable acquisition chain unless a stronger persistent commercial binding already exists.
2. Consumer referral credits never create renewal ownership.
3. Renewal payout eligibility depends on the renewal policy effective for that renewal event, not on the original acquisition payout percentages alone.
4. Attribution history and payout eligibility are separate. A historical owner may remain part of provenance even when no renewal payout is due.

## 13.3 Renewal Policy Resolution

The platform must define:

- whether the lane pays on renewals;
- how long renewal ownership eligibility lasts;
- which offer, storefront, and code constraints still apply;
- how upgrades and downgrades affect renewal commissionability;
- what happens when the original partner becomes inactive, suspended, or terminated.

Recommended rule:

- the originating acquisition chain remains traceable;
- the renewal order uses the renewal policy version effective at renewal-order creation;
- payout execution is blocked if the partner is ineligible at renewal time, while provenance remains intact.

---

## 14. Partner Organization And Policy Model

## 14.1 Partner Organization Structure

The platform requires:

- `partner_accounts`
- `partner_account_users`
- `partner_account_roles`
- `partner_permissions`
- `partner_program_memberships`
- `contracts`
- `tax_profiles`
- `settlement_profiles`

This is the canonical external partner model.

## 14.2 Partner Codes

`partner_code` remains the external commercial carrier, but it must not be the only place where mutable policy lives.

The canonical model requires:

- `partner_codes`
- `partner_code_versions`
- `commission_policy_versions`
- `discount_policy_versions`
- `markup_policy_versions`
- `attribution_policy_versions`
- `eligibility_policy_versions`

## 14.3 Versioning Requirement

Orders and statements must reference exact policy versions so that:

- historical payouts remain explainable;
- finance can reconcile statements;
- support can answer disputes;
- policy changes do not rewrite history.

## 14.4 Code Modes

Examples of code-level commercial modes include:

- creator margin mode;
- creator conversion mode;
- reseller markup mode;
- reseller hybrid mode;
- performance custom mode.

These are external business concepts resolved through versioned policy objects, not mutable ad hoc config keys.

## 14.5 Policy Version Lifecycle And Effective Dating

All critical policy versions must support:

- `effective_from`
- `effective_to`
- `approval_state`
- `draft`
- `approved`
- `active`
- `superseded`
- `archived`

The platform must define:

- how quote-time versions are locked;
- how commit-time validation behaves if policy changed since quote creation;
- how renewal policies are selected;
- whether any retroactive correction is allowed;
- how statement adjustments reference the original or replacement policy logic.

Canonical rules:

1. Finalized orders never lose the ability to reference their original policy versions.
2. Policy supersession does not retroactively rewrite financial history.
3. Quote sessions must either lock compatible policy versions for their lifetime or fail safely at commit with an explicit recomputation path.

Versioning discipline should be applied consistently across:

- partner-code economics;
- offers;
- pricebooks;
- program eligibility;
- surface policy matrices;
- storefront legal document sets;
- storefront profile bindings.

## 14.6 Partner Portal

The target-state platform requires a dedicated partner portal or workspace for partner operators.

It must support:

- users and roles;
- contracts;
- payout accounts;
- statements;
- traffic declarations;
- creative assets and approvals;
- API tokens;
- postbacks;
- reports;
- compliance actions.

This is separate from the official CyberVPN customer dashboard.

---

## 15. Finance And Settlement Model

## 15.1 Two Financial Domains

The platform must separate:

- `Consumer Finance`
- `Partner Finance`

They may share ledger primitives internally, but they are not the same domain.

## 15.2 Consumer Finance

Consumer finance includes:

- customer wallet;
- promo credits;
- referral credits;
- non-withdrawable balance;
- wallet spend;
- customer refunds;
- consumer-side reversals.

## 15.3 Partner Finance

Partner finance includes:

- earnings events;
- earning holds;
- reserves;
- clawbacks;
- partner statements;
- settlement periods;
- payout instructions;
- payout executions;
- reconciliation;
- statement adjustments;
- payout accounts.

## 15.4 Settlement Entities

The target-state platform requires first-class support for:

- `partner_statements`
- `settlement_periods`
- `payout_instructions`
- `payout_executions`
- `statement_adjustments`
- `earning_holds`
- `earning_adjustments`
- `reserves`
- `fx_rate_snapshots`

## 15.5 Settlement Principles

The platform must enforce:

- wallet is not the accounting system;
- no hard delete for financial records;
- immutable audit for settlement actions;
- maker-checker approval for sensitive payout actions;
- explicit accrual, available, paid, and clawed-back states;
- re-open policy for statements;
- payout rail abstraction;
- reconciliation lifecycle tracking;
- multi-currency support through explicit FX snapshots and settlement policies.

## 15.6 Boundary Contract Between Commerce, Billing, And Settlement

The platform must keep these boundaries explicit:

Commerce and Orders owns:

- order creation and order state;
- checkout and quote lineage;
- refund intent and refund linkage to order state;
- commercial composition of the order;
- commercial snapshots used by attribution and entitlements.

Merchant, Billing, Tax, and Disputes owns:

- merchant-of-record resolution;
- invoice and tax snapshots;
- billing descriptors;
- provider-facing dispute objects and evidence lifecycle;
- refund and dispute provider-state synchronization.

Finance and Settlement owns:

- economic consequences of commercial events;
- accrual, hold, reserve, release, clawback, and statement logic;
- payout eligibility and payout execution;
- financial reconciliation and liability reporting.

---

## 16. Service Identity And Entitlements

## 16.1 Service Identity Layer

CyberVPN needs a first-class service-access layer separate from customer identity and storefront identity.

The target-state platform requires:

- `service_identities`
- `entitlement_grants`
- `device_credentials`
- `provisioning_profiles`
- `access_delivery_channels`

## 16.2 Why This Matters

This separation is required because:

- users buy through storefronts but consume through the VPN service layer;
- the same human may hold multiple brand-scoped accounts and subscriptions;
- multiple channels need the same entitlement truth;
- provisioning should not remain an implicit side effect of a customer row.

## 16.3 Cross-Channel Service Consumption Model

The platform must separate:

- channel of purchase;
- channel of account access;
- channel of service consumption;
- channel of support.

Canonical service-consumption rules:

1. A partner-storefront customer may consume the VPN service through shared clients only if those clients are realm-aware and storefront-aware.
2. Shared mobile or desktop clients must resolve the user’s realm at login, fetch the correct support and branding context, and never imply access to the official CyberVPN web account surface.
3. If a shared client cannot satisfy branding, compliance, or support requirements for a storefront, that storefront must use branded delivery profiles or branded access channels.
4. Telegram, Mini App, mobile, and desktop channels must request entitlements from the same service-identity layer.
5. Support tooling must distinguish purchase surface from service-consumption surface.

## 16.4 Domain Language

The long-lived domain should stop using mobile-centric language as the conceptual center of the platform.

Even if some legacy operational tables retain mobile-centric names, the target-state architecture should speak in terms of:

- customer accounts;
- customer principals;
- service identities;
- entitlement grants;
- provisioning state.

---

## 17. Risk, Compliance, And Governance

## 17.1 Risk Identity Graph

The platform requires a risk identity graph to detect abuse without collapsing brand isolation.

Recommended entities:

- `risk_subjects`
- `risk_identifiers`
- `risk_links`
- `risk_events`
- `risk_reviews`
- `risk_decisions`

## 17.2 Why The Risk Graph Is Mandatory

It is needed to detect:

- self-referral across realms;
- same-human farming across brands;
- duplicate trials;
- partner self-purchases;
- synthetic first-payment abuse;
- abnormal velocity;
- cross-realm payout abuse.

## 17.3 Risk Subject Scope

The platform must define whether eligibility and anti-abuse checks are:

- account-scoped;
- realm-scoped;
- storefront-scoped;
- person- or cluster-scoped through the risk graph.

At minimum, the platform must explicitly define scope rules for:

- trial eligibility;
- consumer referral eligibility;
- invite issuance and invite redemption limits;
- self-purchase detection;
- payout freeze;
- storefront abuse clusters.

## 17.4 Governance Mechanisms

The target-state governance layer requires:

- policy acceptance versioning;
- traffic declaration lifecycle;
- creative approval workflow;
- restricted-claims control;
- payout freeze;
- reserve extension;
- manual review queue;
- evidence attachments;
- dispute cases;
- `accepted_legal_documents`;
- immutable decision audit trail;
- jurisdiction and payment-eligibility checks.

`accepted_legal_documents` evidence must capture at minimum:

- `document_version_id` or `legal_doc_set_version_id`
- `storefront_id`
- `auth_realm_id`
- `actor_principal_id`
- `acceptance_channel`
- `quote_session_id`, `checkout_session_id`, or `order_id` where applicable
- `accepted_at`
- source network or device evidence if policy requires it

## 17.5 Traffic And Claims Bans

The platform must support hard policy controls against:

- brand PPC without written approval;
- trademark or misspelling bidding;
- spam;
- bots and fake traffic;
- cookie stuffing;
- fake reviews and incentivized fake ratings;
- popunders, forced redirects, adware;
- misleading privacy or anonymity claims.

---

## 18. Channels, Surfaces, And Policy Matrix

## 18.1 Official CyberVPN Frontend

The official frontend in `frontend/` is the flagship CyberVPN-branded surface.

It must support:

- official pricing;
- invite and consumer referral;
- creator-affiliate compatible code entry;
- customer dashboard functions;
- official-brand legal and communications rules.

It must not expose self-serve reseller markup.

## 18.2 Partner Storefront Platform

`apps/partner-storefront/` must be treated as a generic multi-brand storefront engine, not merely a second site for one partner.

It must support:

- host-based storefront resolution;
- brand-config driven theming and copy;
- realm binding;
- pricebook binding;
- merchant/support/communication/legal profile binding;
- partner-owned checkout and self-service;
- campaign landing profiles;
- storefront-specific auth and session rules.

## 18.3 Partner Portal

The platform requires a dedicated partner portal for partner operators, separate from customer dashboard functions and separate from customer-facing storefronts.

## 18.4 Surface Policy Matrix

The platform must maintain a formal surface-by-surface policy matrix defining, per surface:

- allowed code entry types;
- whether external code override is allowed;
- whether only same-owner codes are accepted;
- whether promo stacking is allowed;
- whether wallet spend is allowed;
- whether invite redemption is allowed;
- whether referral discount is allowed;
- whether the surface is customer-facing or operator-facing.

The matrix must exist as a typed policy artifact, not only as prose.

## 18.5 Full-Channel Parity

The target-state platform must serve the same rulebook across:

- official web frontend;
- partner storefronts;
- partner portal;
- Telegram Bot;
- Telegram Mini App;
- mobile apps;
- desktop apps;
- partner APIs and reporting integrations.

Target-state parity means the core domains for:

- identity;
- orders;
- attribution;
- entitlements;
- reporting;
- settlements

must work consistently across all channels.

---

## 19. RBAC, Scopes, And Credential Model

## 19.1 Role Families

The platform must define explicit role models for:

- partner portal roles;
- admin roles;
- finance roles;
- support roles;
- fraud and risk roles;
- partner analyst roles;
- partner traffic-manager roles;
- service principals.

## 19.2 Scope Model

Access tokens and machine credentials must use explicit scopes and permissions.

Recommended principles:

- scopes express resource access intent;
- permissions express concrete actions;
- tokens carry least-privilege grants;
- service-to-service credentials remain separated from human session tokens;
- row-level visibility rules are enforced server-side, not only in UI.

## 19.3 Credential Types

The target-state platform requires explicit models for:

- customer session tokens;
- partner operator session tokens;
- admin session tokens;
- service tokens;
- postback credentials;
- reporting API tokens.

## 19.4 Visibility Rules

The platform must enforce:

- row-level partner data isolation;
- storefront-aware data isolation;
- role-based statement and payout visibility;
- audit of privileged read access to sensitive financial and risk data.

---

## 20. API, Event, And Processing Architecture

## 20.1 API Domains

The API domains listed below are representative and not exhaustive. Canonical endpoint contracts, schemas, idempotency behavior, auth scopes, and error semantics belong to the API specification package.

The target-state platform requires or expands APIs for:

- `/api/v1/brands`
- `/api/v1/orders`
- `/api/v1/order-items`
- `/api/v1/quotes`
- `/api/v1/checkout-sessions`
- `/api/v1/payment-attempts`
- `/api/v1/refunds`
- `/api/v1/payment-disputes`
- `/api/v1/storefronts`
- `/api/v1/storefront-profiles`
- `/api/v1/offers`
- `/api/v1/pricebooks`
- `/api/v1/program-eligibility`
- `/api/v1/surface-policies`
- `/api/v1/merchant-profiles`
- `/api/v1/invoice-profiles`
- `/api/v1/billing-descriptors`
- `/api/v1/partner-workspaces`
- `/api/v1/partner-codes`
- `/api/v1/partner-statements`
- `/api/v1/partner-payout-accounts`
- `/api/v1/payouts`
- `/api/v1/attribution`
- `/api/v1/growth-rewards`
- `/api/v1/service-identities`
- `/api/v1/entitlements`
- `/api/v1/contracts`
- `/api/v1/policy-acceptance`
- `/api/v1/legal-documents`
- `/api/v1/risk-reviews`
- `/api/v1/risk-decisions`
- `/api/v1/governance-actions`
- `/api/v1/campaigns`
- `/api/v1/creative-assets`
- `/api/v1/reporting`

## 20.1.1 API Surface Families

The platform should expose clearly separated API surface families:

- customer-facing APIs;
- partner-operator APIs;
- admin and internal-ops APIs;
- service-to-service integration APIs;
- reporting and export APIs.

These surfaces should differ by:

- principal type;
- token scope set;
- row-level visibility model;
- allowed write actions;
- audit requirements.

## 20.1.2 Contract Principles

Canonical API contract principles:

1. Idempotency is mandatory for checkout commit, refund submission, payout execution triggers, and postback ingestion.
2. Auth scope and realm validation happen server-side on every write operation.
3. Finalized commercial and financial objects expose immutable snapshots and explicit adjustment links rather than silent in-place mutation.
4. Long-running operations expose operation status or job handles instead of blocking writes indefinitely.
5. Dispute APIs expose canonical `payment_dispute` lifecycles, while provider-specific terms such as inquiry or chargeback remain mapped subtypes or statuses.
6. Reporting APIs must be row-level filtered according to partner workspace, storefront, and role permissions.

Representative contract expectations:

- order and checkout APIs must be idempotent at commit boundaries;
- payout and postback APIs must use explicit credential scopes;
- dispute APIs must expose inquiry, chargeback, and final-outcome semantics through the canonical `payment_dispute` model;
- legal-document APIs must expose both active policy retrieval and acceptance evidence recording;
- reporting APIs must honor row-level visibility and partner workspace scopes.

## 20.2 Event Layer

The platform requires a reliable event or outbox layer with:

- idempotent publication;
- replay safety;
- explicit versioning;
- actor attribution;
- deterministic consumers.

Representative events:

- `quote_session_created`
- `checkout_session_started`
- `order_created`
- `order_paid`
- `order_refunded`
- `order_attribution_resolved`
- `growth_reward_created`
- `earning_created`
- `earning_hold_released`
- `statement_closed`
- `payout_executed`
- `service_entitlement_changed`

## 20.3 Background Processing

Background jobs must handle:

- attribution resolution;
- hold release;
- payout export;
- postback delivery;
- reporting refresh;
- fraud scoring;
- QR generation;
- backfills;
- reconciliation.

---

## 21. Lifecycle State Machines

The platform must define formal lifecycle specifications for at least:

- `quote_session`
- `checkout_session`
- `order`
- `payment_attempt`
- `refund`
- `payment_dispute`
- `partner_statement`
- `payout_execution`
- `risk_review`
- `entitlement_grant`

Each lifecycle spec must define:

- allowed statuses;
- valid transitions;
- initiating actor or system;
- idempotent transitions;
- replay-safe transitions;
- terminal states;
- reopen rules;
- immutability rules after finalization.

Representative final-state expectations:

| Object | Final-state expectation |
|---|---|
| `quote_session` | expires or converts, never silently mutates into a completed order |
| `checkout_session` | tracks customer interaction and commit boundary separately from order |
| `order` | finalized commercial record with immutable pricing and ownership snapshot |
| `payment_attempt` | retryable settlement object linked to one order |
| `refund` | explicit refund lifecycle, not only a numeric field on order |
| `payment_dispute` | inquiry/dispute lifecycle with evidence and final outcome |
| `partner_statement` | closeable and auditable statement period object |
| `payout_execution` | approval, submission, completion, and reconciliation lifecycle |
| `risk_review` | triage and decision lifecycle with evidence trail |
| `entitlement_grant` | pending, active, suspended, revoked, or expired service-access state |

---

## 22. Analytics And Reporting Architecture

## 22.1 Three Analytical Layers

The platform requires:

| Layer | Purpose |
|---|---|
| `OLTP` | operational source of truth |
| `event/outbox layer` | reliable publication and replay |
| `analytical layer` | reporting marts, cohorts, margin, retention, fraud, liability analytics |

## 22.2 Canonical Metric Definitions

Every critical metric must have one platform definition, especially:

- paid conversion;
- qualifying first payment;
- refund rate;
- chargeback rate;
- D30 paid retention;
- earnings available;
- payout liability;
- net paid orders 90d.

Finance, growth, and partner management must not operate from competing definitions.

## 22.3 Reporting Outputs

The target-state platform must support:

- internal operational dashboards;
- partner dashboards;
- partner statements;
- exports;
- postbacks;
- explainability views for attribution and payout decisions;
- alerts on quality, payout, and fraud anomalies.

---

## 23. Non-Functional Requirements

The platform must explicitly guarantee:

- immutable audit for financial, attribution, and policy actions;
- idempotency on webhook, checkout commit, payout, and postback flows;
- actor attribution for every policy change and override;
- report freshness objectives;
- SLOs for quote and checkout APIs;
- background job retry and dead-letter strategy;
- migration rehearsal policy;
- data retention policy;
- restore and backfill strategy;
- row-level data isolation for partner analytics;
- feature flags per realm, storefront, and program;
- secret management and request signing for postbacks and webhooks.

---

## 24. Canonical Policy Baselines

These baseline business directions remain canonical in the target state:

- consumer referral uses fixed non-withdrawable credit, not indefinite revshare;
- public creator economics favor 90d, 180d, and 365d plans over 30d plans;
- performance is a closed program with stronger hold and stricter quality gates;
- official CyberVPN surfaces do not self-serve markup;
- reseller markup exists only on partner-owned or approved surfaces;
- partner quality tiering uses net economics and retention quality;
- sub-affiliate, if enabled, is a derived earnings overlay and not an acquisition owner;
- critical policy semantics are versioned and effective-dated.

These directions must be expressed through typed and versioned policy objects, not only config keys.

---

## 25. Documentation Package

This target-state document is the anchor of a broader documentation package.

The recommended companion set is:

- `Partner Platform Rulebook`
- `Partner Platform Target-State Architecture`
- `Partner Platform API Specification Package`
- `Commerce, Attribution, And Settlement Data Model Spec`
- `Storefront, Identity, And Access Model Spec`
- `Partner Operations, Risk, Finance, And Compliance Spec`
- `Program Compatibility, Qualifying Events, And Renewal Spec`
- `Lifecycle And State Machine Spec`
- `Analytics And Reporting Spec`
- `Delivery Program And Cutover Plan`

The required companion operational document is:

- `docs/plans/2026-04-17-partner-platform-delivery-program.md`

---

## 26. Architectural Acceptance Conditions

CyberVPN reaches the intended target state only when all of the following are true:

- target-state documents no longer mix stable architecture with rollout sequencing;
- brand, storefront, auth realm, merchant, support, and communication profiles are distinct first-class concepts;
- the platform uses a real order domain rather than payment-centric ownership logic;
- commercial ownership, growth rewards, bindings, and touchpoints are separated cleanly;
- partner economics are reproducible through versioned policy objects;
- partner settlements are modelled separately from customer wallet behavior;
- merchant-of-record, tax, billing, refund, and dispute responsibilities are explicit per order;
- partner access is organization-aware and workspace-aware;
- service identity and entitlements are first-class;
- risk analysis can see cross-realm abuse without breaking brand isolation;
- stacking, qualifying-event, renewal, and lifecycle semantics are formally defined;
- all major channels consume the same identity, order, attribution, entitlement, and reporting foundations.

At that point CyberVPN has a long-lived partner and growth platform, not an upgraded referral feature set.
