# Growth Codes Implementation Plan

**Date:** 2026-04-21  
**Status:** execution baseline

---

## 1. Goal

Build a dedicated customer growth codes platform on top of current CyberVPN pricing, checkout, wallet, entitlement and admin systems.

---

## 2. Phase Overview

### Phase 0 — Rule Freeze

Freeze:

- code taxonomy
- stacking rules
- referral economics
- legacy referral migration decision
- gift semantics
- invite conversion reward policy
- promo eligibility
- partner conflict rules

### Phase 1 — Backend Code Engine

Build:

- code registry
- issuance tracking
- touchpoint tracking
- signup attribution
- typed policy resolver
- hashing
- reservations
- redemptions
- reward allocations
- audit trail

### Phase 2 — Checkout Integration

Integrate:

- promo and referral into quote
- partner conflict logic
- wallet interaction
- entitlement snapshot effects
- idempotency

### Phase 3 — Invite And Referral Client Frontend

Build:

- invites page
- referral page
- rewards overview
- share and QR
- notifications

### Phase 4 — Promo Admin And Checkout UI

Build:

- admin promo campaigns
- code lookup
- checkout code input UX
- resolution messages
- promo analytics

### Phase 5 — Gift Codes

Build:

- buy gift
- redeem gift
- admin gift batches
- entitlement grant flow
- revoke and refund linkage

### Phase 6 — Partner Portal Touchpoints

Build:

- approved promo assets
- reseller voucher capability if approved
- disclosure guidance

### Phase 7 — Risk, Analytics, Observability

Build:

- abuse detection hooks
- dashboards
- review queues
- growth metrics
- admin operational metrics
- lifecycle events

### Phase 8 — E2E Conformance

Validate:

- invite generation and redemption
- referral first paid reward
- promo conflict with partner code
- gift purchase and redeem
- reward and entitlement non-recursion
- lifecycle tracking and audit correctness

### Phase 9 — Post-Conformance Cutover And Customer Communications

Build and harden:

- canonical referral reward cutover
- customer growth notification fanout policy
- delivery preferences
- automatic user-visible notifications from admin and lifecycle actions
- delivery observability and admin review signals
- support-grade delivery forensics and export

### Phase 10 — Customer Troubleshooting And Recovery

Build:

- customer-safe troubleshooting states in rewards surfaces
- resend-request and support handoff flows for recoverable delivery failures
- archived delivery history views for customer support follow-up
- deterministic recovery CTAs for revoked, paused, or unavailable channels

### Phase 11 — Guided Repair And Escalation

Build:

- guided repair deep links for broken delivery channels
- structured support escalation for unresolved customer recovery
- repair analytics vs escalation analytics

### Phase 12 — Repair Automation And Escalation Closure

Build:

- automatic retry and re-arm after real repair actions
- support/admin resolution actions with closure state
- customer-visible closure notifications
- recovery and resolution observability

### Phase 13 — Growth Notification Conformance And Rollout Hardening

Build:

- conformance packs for delivery and repair chains
- evidence and rollout assets
- governance-safe alerts, dashboards, and runbooks

### Phase 14 — Growth Notification Staging Rollout And Governance Gate

Build:

- staging smoke and evidence capture toolkit
- protected-gate handoff and disabled ruleset prep
- rollout-readiness workflow for live execution

### Phase 15 — Growth Reporting And Rollup Layer

Build:

- persisted daily growth rollups
- admin reporting APIs and export surfaces
- cost, liability, and reward summaries from canonical lifecycle data

### Phase 16 — Scheduled Rollup Refresh And Executive Reporting Hardening

Build:

- scheduled rollup refresh
- freshness tracking and lag handling
- executive summary hardening
- refresh monitoring and alerting

### Phase 17 — Reporting Distribution, Retention, And Lifecycle Maintenance

Build:

- recurring distribution deliveries
- retention cleanup for rollups and delivery artifacts
- recurring subscription management and export surfaces

### Phase 18 — Reporting Template Governance And Recipient Policy Controls

Build:

- audience-specific reporting templates
- recipient governance and suppression windows
- audit trail for template and recipient policy changes

### Phase 19 — Reporting Governance Audit Trail And Coverage Forensics

Build:

- governance coverage drilldown
- recent governance decisions and policy audit timeline
- exportable governance snapshots
- alerts for silent reporting coverage gaps

### Phase 20 — Reporting Governance Conformance, Evidence, And Gate Automation

Build:

- governance conformance packs
- evidence bootstrap and rollout-safe gates
- protected-check handoff automation

### Phase 21 — Reporting Governance Staging Rollout And Protected Gate Activation

Build:

- staging smoke and evidence capture tooling
- disabled GitHub ruleset preparation
- machine-readable `enable` or `hold` gate-readiness recommendation from evidence
- rollout decision path for protected gate activation

### Phase 22 — Reporting Governance Recovery Automation And Follow-up Controls

Build:

- persisted governance recovery follow-up lifecycle
- scheduled follow-up processing and reminder automation
- overdue admin recovery queue with resolve and dismiss actions
- follow-up metrics, alerts, and runbook triage

---

## 3. Workboards

## GC-WB-01 Rule Freeze And Resolver Baseline

Deliverables:

- finalize typed rules
- create resolver interface
- define resolution context and conflict model
- decide legacy referral cutover or grandfathering policy

Done when:

- no open ambiguity remains about stacking or surface ownership

## GC-WB-02 Data Model, Tracking, And Backend Registry

Deliverables:

- growth code registry
- growth code issuances
- touchpoints
- signup attributions
- policy tables
- reservations
- redemptions
- reward allocation tables
- audit-linked lifecycle tables

Done when:

- backend can persist typed code lifecycle safely

## GC-WB-03 Checkout Integration

Deliverables:

- quote path uses resolver
- commit path consumes reservation
- promo and referral pricing behavior works

Done when:

- frontend quote is fully backend-owned for customer growth codes

## GC-WB-04 Invite And Referral Frontend

Deliverables:

- rewards overview
- invites
- referral
- notifications hooks

## GC-WB-05 Promo Admin And Checkout UI

Deliverables:

- admin promo management
- code lookup
- checkout code box
- conflict and rejection UX

## GC-WB-06 Gift Codes

Deliverables:

- gift purchase
- gift redeem
- admin gift issue
- entitlement grant handling

## GC-WB-07 Partner Touchpoints

Deliverables:

- partner-facing approved campaign assets
- reseller voucher capability if policy enables it

## GC-WB-08 Risk And Analytics

Deliverables:

- abuse review signals
- dashboards
- reporting
- observability
- admin operational metrics
- event stream for code lifecycle

## GC-WB-09 E2E Conformance

Deliverables:

- happy-path tests
- conflict tests
- abuse-block tests
- audit evidence

Scenarios must prove:

- issued -> touched -> registered -> redeemed linkage
- manual admin grant auditability
- reward hold and reversal correctness
- metrics and events generated for each code type

## GC-WB-10 Referral Cutover And Canonical Reward Lifecycle

Deliverables:

- referral reward cutover from legacy commission flow
- pending, available, and reversed reward lifecycle
- canonical public and admin referral read models

## GC-WB-11 Customer Growth Notification Delivery And Preferences

Deliverables:

- in-app, email, and telegram delivery planning
- customer notification preferences
- user-visible lifecycle notifications

## GC-WB-12 Delivery Execution And Admin Review Controls

Deliverables:

- delivery execution workers
- resend, pause, revoke, and manual notify controls
- admin delivery status surfaces

## GC-WB-13 Support Timeline, Export, And Delivery Forensics

Deliverables:

- support-grade delivery forensic timeline
- exportable delivery artifacts
- queue and resend history drilldown

## GC-WB-14 Customer Troubleshooting And Recovery Surface

Deliverables:

- customer troubleshooting states
- archived history and recovery CTAs
- self-service recovery where policy allows

## GC-WB-15 Guided Channel Repair And Support Escalation

Deliverables:

- repair-target deep links
- structured support escalation
- routing for disabled, unlinked, or unavailable channels

## GC-WB-16 Repair Automation And Escalation Closure

Deliverables:

- automatic recovery after repair actions
- support resolution actions
- closure notifications and recovery metrics

## GC-WB-17 Growth Notification Conformance And Rollout Hardening

Deliverables:

- delivery conformance packs
- evidence bootstrap and rollout assets
- repair-chain dashboards, alerts, and runbooks

## GC-WB-18 Growth Notification Staging Rollout And Governance Gate

Deliverables:

- staging smoke toolkit
- disabled protected-gate setup
- rollout evidence and decision path for live execution

## GC-WB-19 Growth Reporting And Rollup Layer

Deliverables:

- persisted rollups
- admin reporting overview and export
- daily summaries for invite, referral, promo, and gift

## GC-WB-20 Scheduled Rollup Refresh And Executive Reporting Hardening

Deliverables:

- scheduled refresh worker
- freshness indicators and stale handling
- refresh monitoring and executive reporting hardening

## GC-WB-21 Reporting Distribution, Retention, And Lifecycle Maintenance

Deliverables:

- recurring distribution ledger
- reporting retention cleanup
- recurring delivery status and artifact export

## GC-WB-22 Reporting Template Governance And Recipient Policy Controls

Deliverables:

- reporting templates by audience
- recipient allowlist and suppression controls
- policy audit trail

## GC-WB-23 Reporting Governance Audit Trail And Coverage Forensics

Deliverables:

- governance coverage overview
- decision timeline and audit trail
- exportable governance snapshots
- metrics and alerts for coverage gaps

## GC-WB-24 Reporting Governance Conformance, Evidence, And Gate Automation

Deliverables:

- governance conformance packs
- evidence bootstrap
- required-check and protected-gate automation

## GC-WB-25 Reporting Governance Staging Rollout And Protected Gate Activation

Deliverables:

- staging smoke tooling
- rollout runbook and evidence capture path
- disabled ruleset prep for protected gate activation

## GC-WB-26 Reporting Governance Recovery Automation And Follow-up Controls

Deliverables:

- governance follow-up persistence and lifecycle
- scheduled reminder and auto-resolution processing
- admin follow-up queue with resolve and dismiss actions
- overdue follow-up alerts and runbook triage

## GC-WB-10 Referral Cutover And Canonical Reward Lifecycle

Deliverables:

- replace legacy referral commission runtime with canonical growth reward lifecycle
- pending -> available -> reversed referral rewards
- referral read APIs use canonical reward allocations
- refund and dispute flows reverse referral rewards correctly

Done when:

- referral runtime no longer depends on legacy commission semantics for new accruals

## GC-WB-11 Customer Growth Notification Delivery And Preferences

Deliverables:

- in-app, email and telegram fanout policy
- customer growth notification preferences
- automatic user-visible notifications from admin grant and reward lifecycle actions
- delivery planning records and channel auditability

Done when:

- customer growth events can be planned and surfaced consistently across channels

## GC-WB-12 Delivery Execution And Admin Review Controls

Deliverables:

- actual email delivery execution path
- admin review actions for pause, revoke, resend and manual notify
- delivery status views in admin console
- customer-visible delivery troubleshooting and support lookup

Done when:

- growth notification channels are not only planned but operationally executable and reviewable

## GC-WB-13 Support Timeline, Export, And Delivery Forensics

Deliverables:

- support-grade lookup for growth notification lifecycle by user, code, reward and delivery
- exportable delivery and audit timelines for customer support and incident review
- admin drilldown for queue failures, resend history and channel-specific troubleshooting
- customer-safe troubleshooting states and operator notes for failed or revoked growth deliveries

Done when:

- support and operations teams can explain any growth notification outcome end-to-end without raw database inspection

## GC-WB-14 Customer Troubleshooting And Recovery Surface

Deliverables:

- customer-facing troubleshooting states for failed, paused, revoked, and skipped deliveries
- recovery CTA and resend-request flow where channel policy allows it
- support handoff payloads with stable troubleshooting summaries
- archived customer delivery history in rewards surfaces

Done when:

- customer growth notices no longer fail silently from the user perspective
- support and customer see the same deterministic recovery state

## Phase 11 — Guided Repair And Escalation

This phase converts troubleshooting visibility into guided next actions.

### GC-WB-15 Guided Channel Repair And Support Escalation

Deliverables:

- customer-safe deep links from troubleshooting states to the right repair surface
- support escalation payloads that can open or prefill the correct support workflow
- explicit channel repair guidance for email, Telegram, and preference-related suppression states
- lifecycle events and analytics for customer recovery attempts vs support escalations

Done when:

- customers can move from a failed delivery state to either self-service repair or structured support escalation without guesswork
- support receives deterministic handoff context instead of free-form customer descriptions

## Phase 12 — Repair Automation And Closure

This phase closes the loop between repair actions, support interventions, and user-visible outcomes.

### GC-WB-16 Repair Automation And Escalation Closure

Deliverables:

- automatic re-arming or replay of eligible deliveries after customer repair actions such as preference enablement, Telegram linking, or contact data correction
- admin/support resolution actions that mark delivery escalations as resolved and produce customer-visible closure notifications
- unified escalation lifecycle states from `requested` to `resolved` or `abandoned`
- analytics and observability for `repair_completed`, `support_resolved`, and `delivery_recovered`

Done when:

- a successful customer or support repair can move a delivery from blocked state to recovered state without manual data spelunking
- customers receive deterministic closure feedback after support fixes a growth delivery issue
- delivery analytics can separate unresolved escalation backlog from completed recovery outcomes

---

## Phase 13 — Conformance And Rollout Hardening

This phase turns the repaired delivery lifecycle into a rollout-safe operational surface.

### GC-WB-17 Growth Notification Conformance And Rollout Hardening

Deliverables:

- end-to-end conformance coverage for `preferences_reenabled`, `telegram_linked`, `contact_data_corrected`, and `support_resolved`
- admin and customer evidence capture for `repair_completed`, `support_resolved`, and `delivery_recovered`
- delivery troubleshooting dashboards and alert thresholds for unresolved escalation backlog
- rollout checklist for enabling the repaired delivery lifecycle in live environments without silent regressions

Done when:

- repair and closure flows are covered by deterministic conformance checks rather than manual spot verification
- admin delivery operations can distinguish recovered, unresolved, and abandoned issues from dashboards and exported evidence
- the team can run a rollout window with a repeatable proof pack for customer growth notification repairs

---

## Phase 14 — Live Rollout And Governance

This phase takes the hardened repair chain into a managed rollout window.

### GC-WB-18 Growth Notification Staging Rollout And Governance Gate

Deliverables:

- staging rollout window using the growth notification evidence pack
- recovered, unresolved, and support-resolved proof captured from a live environment
- rollout decision and rollback notes attached to the evidence pack
- CI required-check handoff prepared for branch protection or release governance
- repo-managed staging smoke runner, staging rollout runbook, and disabled governance ruleset helper

Done when:

- a live rollout window proves the repaired delivery lifecycle without silent regressions
- unresolved backlog and recovery ratio remain within the defined rollout thresholds
- release governance has a concrete required-check and evidence trail for future widens

---

## Phase 15 — Reporting And Rollup Layer

This phase adds a persisted reporting layer on top of the canonical growth lifecycle backbone.

### GC-WB-19 Growth Codes Reporting And Rollup Layer

Deliverables:

- persisted daily rollups over canonical `growth_codes`, `growth_code_resolution_events`, `growth_code_reservations`, `growth_code_redemptions`, and `growth_reward_allocations`
- admin reporting overview and export surfaces backed by those rollups rather than ad-hoc live joins
- family-level summaries for invite, referral, promo, and gift performance over an operator-selected window
- explicit coverage notes that separate real rollup coverage from still-unimplemented touchpoint or signup attribution funnels

Done when:

- admin can refresh, inspect, and export growth reporting rollups without querying raw lifecycle tables directly
- reporting remains honest about current data coverage and does not fabricate touchpoint or signup funnel metrics that runtime does not yet populate
- growth reporting can support later executive dashboards and finance or risk reviews from a stable persisted layer

---

## Phase 16 — Scheduled Reporting Automation

This phase turns the manual reporting layer into an operationally refreshed surface.

### GC-WB-20 Scheduled Rollup Refresh And Executive Reporting Hardening

Deliverables:

- scheduled or worker-driven refresh of growth reporting rollups
- stale-rollup detection and admin-visible freshness indicators
- hardened export or executive summary surfaces for finance, product, and risk review
- rollout-safe monitoring around reporting refresh failures or lag

Done when:

- growth reporting no longer depends on manual operator refresh for normal daily use
- admin can tell whether reporting is fresh, stale, or failed without inspecting task logs
- reporting exports are stable enough to support recurring business reviews

---

## Phase 17 — Reporting Distribution And Retention

This phase turns reporting from a refreshed operator surface into a governed recurring review artifact.

### GC-WB-21 Reporting Distribution, Retention, And Lifecycle Maintenance

Deliverables:

- scheduled delivery or publication of executive growth reporting exports for finance, product, and risk review
- retention and cleanup policy for stale rollups, refresh runs, and generated reporting artifacts
- admin-visible reporting subscription or delivery status for recurring review recipients
- operational safeguards for abandoned reporting pipelines, export drift, or retention-policy violations

Done when:

- recurring reporting reviews no longer depend on manual export collection
- reporting storage and refresh-run history have explicit lifecycle or retention boundaries
- operators can distinguish healthy recurring reporting delivery from stale or abandoned reporting distribution

---

## Phase 18 — Reporting Governance And Template Controls

This phase turns recurring reporting from a raw delivery pipeline into a governed communication surface.

### GC-WB-22 Reporting Template Governance And Recipient Policy Controls

Deliverables:

- audience-specific reporting templates and subject/title policy
- admin-managed recipient governance for finance, product, risk, and ops audiences
- recurring delivery pause windows, delivery suppression, or domain-safety controls where policy requires them
- audit trail for recipient changes and template-level operator actions

Done when:

- recurring reporting content is no longer coupled only to generic growth notification copy
- recipient policy changes are auditable and operator-safe
- distribution governance can evolve without rewriting the reporting lifecycle backbone

---

## Phase 19 — Reporting Governance Audit And Coverage Closure

This phase turns governed reporting policy into an operator-visible control loop.

### GC-WB-23 Reporting Governance Audit Trail And Coverage Forensics

Deliverables:

- admin-visible audit timeline for reporting subscription recipient or template policy changes
- coverage drilldown for `delivery_suppressed`, `recipient_domain_blocked`, and related governed skip reasons
- exportable governance snapshots for finance, product, risk, and ops reporting subscriptions
- reporting governance metrics or alerts that surface silent audience coverage gaps

Done when:

- operators can explain who changed recurring reporting policy, when, and why without raw audit-log access
- governed skip reasons are visible as intentional coverage posture, not silent delivery loss
- reporting governance can be reviewed during rollout or support windows without querying the database directly

---

## Phase 20 — Reporting Governance Conformance And Rollout Gate

This phase turns reporting governance into a rollout-safe, evidence-backed control surface.

### GC-WB-24 Reporting Governance Conformance, Evidence, And Gate Automation

Deliverables:

- conformance coverage for governance overview, export, alert rules, and runbook assets
- governance evidence bootstrap for blocked-domain and suppressed-delivery incident windows
- rollout-safe checks for governance gap metrics, recipient-domain alerts, and export availability
- handoff material for enabling governance checks as a protected delivery gate

Done when:

- reporting governance incidents can be reproduced, exported, and reviewed through a stable conformance pack
- rollout or incident evidence does not depend on ad-hoc screenshots or manual database queries
- governance alerts and exports are safe to gate in CI and later in branch protection

---

## Phase 21 — Reporting Governance Live Rollout And Protected Gate Activation

This phase takes governance conformance from repo-hardening into a live rollout and merge-governance decision.

### GC-WB-25 Reporting Governance Staging Rollout And Protected Gate Activation

Deliverables:

- governance rollout window proving `delivery_suppressed` and `recipient_domain_blocked` scenarios in a live environment
- completed governance evidence pack with exports, alert proof, and operator sign-off
- protected-check enablement or explicit deferral recorded with rollback notes
- disabled governance ruleset helper used to create or activate the required gate only after evidence is accepted

Done when:

- live staging proves governance overview, export, and alert posture end-to-end
- the team can enable the required governance check without guesswork
- blocked-domain and suppressed-delivery incidents have a repeatable evidence trail outside of local conformance runs

---

## 4. Recommended Execution Order

1. GC-WB-01
2. GC-WB-02
3. GC-WB-03
4. GC-WB-04 and GC-WB-05 in parallel
5. GC-WB-06
6. GC-WB-07
7. GC-WB-08
8. GC-WB-09
9. GC-WB-10
10. GC-WB-11
11. GC-WB-12
12. GC-WB-13
13. GC-WB-14
14. GC-WB-15
15. GC-WB-16
16. GC-WB-17
17. GC-WB-18
18. GC-WB-19
19. GC-WB-20
20. GC-WB-21
21. GC-WB-22
22. GC-WB-23
23. GC-WB-24
24. GC-WB-25

---

## 5. First Safe Implementation Slice

The first safe slice to start coding is:

- resolver contract
- typed conflicts
- issuer, owner, touchpoint and redemption trace model
- reservation model
- promo/referral vs partner stacking enforcement

That is the minimum backbone needed before UX screens scale out.
