# CyberVPN S3-STAGE-00 Partner/Event Backbone Readiness Decision

> **For Codex:** this is a decision gate, not an implementation stage. Do not start S3 partner/reseller runtime work until the owner explicitly approves one decision option below.

**Goal:** Decide whether CyberVPN can begin Stage 3 Partner / Reseller Platform work, and whether the event backbone must be proven before partner production growth.

**Architecture:** S3 must not depend on silent database side effects or manual publication cleanup. Partner, reseller, attribution, invite, entitlement, reporting, and settlement flows must either remain disabled/manual or use a proven transactional outbox to durable event backbone path.

**Tech Stack:** PostgreSQL transactional outbox, backend dispatcher, NATS JetStream target state, durable consumers, Prometheus/Grafana/Alertmanager, GitLab CI evidence, partner/admin/frontend surfaces.

---

## 1. Stage Identity

```text
Stage: S3-STAGE-00
Name: Partner/Event Backbone Readiness Decision
Status: APPROVED_OPTION_A
Prepared: 2026-05-23
Approved: 2026-05-24
Owner decision required: closed
Runtime implementation allowed by this document: no
```

`S3-STAGE-00` is the bridge between:

- `S2-STAGE-18: Post-Launch Stabilization And S3 Readiness`;
- `S3: Partner / Reseller Platform`.

It exists because S2 is now public, but S3 adds growth, partner attribution, reseller, finance and payout surfaces where event correctness matters more than in the S2 B2C baseline.

---

## 2. Current S2 Facts

Observed during the 2026-05-23 S2 stabilization cycle:

```text
CYBERVPN_IMAGE_TAG=stage2-public-rc.5
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=false
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
PAYMENT_RECONCILIATION_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
```

Customer runtime remains healthy:

- public site, pricing, registration, status, help and Mini App routes return `200`;
- API health returns `200`;
- admin login returns `200`;
- HTTP/3/QUIC remains enabled;
- VPN node remains node-only;
- Alertmanager has zero active alerts.

Outbox state after the S2 stabilization closure:

```text
outbox_events_by_event_status|{"published": 17}
outbox_publications_by_status|{"published": 34}
outbox_pending_events|0
outbox_pending_publications|0
outbox_accepted_no_transport|34
```

Important interpretation:

- S2 backlog is closed for current public B2C operation.
- `accepted_no_transport` is an explicit audit marker.
- It is **not** proof that a production broker, dispatcher, or durable consumer received events.
- It must not be used as S3 readiness evidence for partner payouts, reseller reporting, attribution, or automated settlements.

Evidence:

- `docs/evidence/releases/s2-stage-18-stabilization-20260523.md`
- `docs/evidence/releases/s2-stage-18-outbox-backlog-closure-20260523.md`

---

## 3. Why This Decision Exists

S3 introduces flows where event loss, duplicate delivery, stale attribution, or invisible settlement state can create direct business damage:

- partner code issuance and redemption;
- invite/referral attribution;
- reseller ownership and storefront attribution;
- entitlement activation events;
- partner reporting exports;
- commission/settlement calculations;
- payout review and maker-checker workflows;
- audit trail and support escalation.

For S2, manually closing stale outbox rows was acceptable because:

- production partner event backbone is disabled;
- generic payment providers are disabled;
- partner payouts are out of scope;
- S2 public release is B2C-first.

For S3, that model is not enough. Partner growth requires either a proven event backbone or a deliberately manual, restricted launch mode.

---

## 4. Decision Options

### Option A: Recommended - Non-Prod Event Backbone Proof Before S3 Production

Prepare S3 documents and non-production implementation work, but keep production partner event backbone and payouts disabled until the real path is proven:

```text
transactional outbox -> dispatcher -> NATS JetStream -> durable consumer -> receipt/projection
```

Production flags remain:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
```

Required proof before production S3 enablement:

1. NATS/JetStream topology decision.
2. Stream and subject taxonomy.
3. Dispatcher lifecycle evidence: `pending -> claimed -> submitted -> published`.
4. Consumer receipt evidence for at least one partner/growth event family.
5. Duplicate delivery/idempotency test.
6. Replay test from durable event or outbox state.
7. Alerting for pending publication age, publish failures, consumer lag and dead-letter volume.
8. Backup/rebuild evidence for event backbone state or documented replay-from-PostgreSQL strategy.
9. S3 dashboard showing event throughput, lag, failures and consumer health.
10. Owner sign-off before enabling production partner traffic.

Recommendation:

```text
APPROVE_OPTION_A
```

This gives the safest path: S3 can move forward locally/non-prod, but production partner money flows do not depend on an unproven event layer.

### Option B: Manual Partner Pilot Without Event Backbone

Allow a very narrow S3 partner pilot with all money-impacting actions manual and audited:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
```

Allowed:

- manual partner application review;
- manual partner codes for internal/pilot users;
- read-only reporting previews;
- manual support/admin audit notes;
- no automated payouts;
- no public reseller storefronts.

Blocked:

- automated commissionability;
- automated settlement;
- payout exports;
- partner public growth campaigns;
- reseller storefront launch;
- production event fan-out claims.

This option is acceptable only if the owner wants to validate partner UX before event backbone investment. It is not enough for real S3 production growth.

### Option C: Start Full S3 Without Event Backbone Proof

Start full partner/reseller production work while keeping event delivery manual or partially simulated.

Decision:

```text
REJECTED
```

Reason:

- S2 already produced stale outbox publication rows when the event backbone was disabled;
- S3 increases the business impact of stale, missing, duplicated or invisible events;
- partner payouts and reseller reporting need traceable evidence;
- this would create operational and financial risk before CyberVPN has enough stabilization history.

---

## 5. Recommended Decision

The recommended owner decision is:

```text
S3-STAGE-00_DECISION=APPROVE_OPTION_A
```

Owner execution decision captured on 2026-05-24:

```text
S3-STAGE-00_DECISION=APPROVE_OPTION_A
S3_PRODUCTION_PARTNER_RUNTIME=DISABLED_UNTIL_EVIDENCE
S3_PRODUCTION_EVENT_BACKBONE=DISABLED_UNTIL_REAL_BROKER_PROOF
S3_PRODUCTION_PAYOUTS=DISABLED_UNTIL_MAKER_CHECKER_AUDIT_AND_SANDBOX_EVIDENCE
```

Meaning:

- continue daily S2 stabilization snapshots;
- prepare S3 scope/backlog documents;
- build event backbone proof in non-production first;
- do not enable production partner/reseller/payout runtime yet;
- do not claim S3 production readiness from `accepted_no_transport` outbox rows.

---

## 6. Hard Blockers Before S3 Production Enablement

| ID | Blocker | Required Evidence |
|---|---|---|
| `S3-BLOCKER-001` | S2 stabilization watch window accepted | Daily `S2-STAGE-18` snapshots with no unresolved P0/P1 |
| `S3-BLOCKER-002` | Event backbone target selected | Owner-approved topology and cost/placement decision |
| `S3-BLOCKER-003` | NATS/JetStream or equivalent broker proven in non-prod | Stream creation, publish, consume and replay transcript |
| `S3-BLOCKER-004` | Dispatcher proven | Outbox row lifecycle and retry evidence |
| `S3-BLOCKER-005` | Durable consumer receipts proven | Consumer ack/projection evidence |
| `S3-BLOCKER-006` | Idempotency proven | Duplicate event replay does not double-apply rewards or settlements |
| `S3-BLOCKER-007` | Alerts proven | Pending age, publish failures, consumer lag, dead-letter alerts |
| `S3-BLOCKER-008` | Partner finance boundary approved | No payout path without maker-checker and audit |
| `S3-BLOCKER-009` | Partner legal/support copy approved | Partner terms, payout policy, support escalation |
| `S3-BLOCKER-010` | Kill switches proven | Partner portal, storefront, event backbone and payouts can be paused independently |

---

## 7. S3-STAGE-00 Exit Criteria

`S3-STAGE-00` is complete only when:

1. owner chooses Option A or Option B explicitly;
2. production partner payouts remain disabled unless a later S3 gate proves otherwise;
3. production partner event backbone remains disabled until real broker/consumer evidence exists;
4. S3 work starts from a named backlog, not ad-hoc feature edits;
5. every S3 runtime change references an `S3-STAGE-*` identifier.

---

## 8. First S3 Work After Option A Approval

The next practical S3 stages must follow the permanent S3 roadmap numbering exactly:

1. `S3-STAGE-01: S3 Scope, Backlog, And Decision Freeze`
2. `S3-STAGE-02: Partner Domain Model And Role Contract`
3. `S3-STAGE-03: Non-Prod Event Backbone Topology`
4. `S3-STAGE-04: Outbox Dispatcher And Consumer Proof`
5. `S3-STAGE-05: Partner Portal Disabled-State Boundary`

Do not start `S3-STAGE-04` before `S3-STAGE-03` has real non-production broker evidence.
Do not enable production partner portal, storefronts, event fan-out or payouts before `S3-STAGE-16` and `S3-STAGE-17` evidence gates.

---

## 9. Documentation References

- `docs/plans/2026-05-10-cybervpn-stage3-partner-reseller-platform-plan.md`
- `docs/plans/2026-04-17-partner-platform-target-state-architecture.md`
- `docs/plans/2026-04-21-platform-foundation-target-state-architecture.md`
- `docs/plans/2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md`
- `docs/cybervpn_stage2_launch_docs/01_STAGE2_SCOPE_BACKLOG_FREEZE.md`
- `docs/evidence/releases/s2-stage-18-stabilization-20260523.md`
- `docs/evidence/releases/s2-stage-18-outbox-backlog-closure-20260523.md`

---

## 10. Current Recommendation For Owner

Choose:

```text
APPROVE_OPTION_A
```

Then continue S2 stabilization while preparing S3 non-prod event-backbone proof. This keeps CyberVPN public for B2C users and prevents partner/reseller scale from depending on unproven event delivery.

---

## 11. Validation Performed

This document is docs-only. No runtime configuration or code was changed.

Local validation before commit:

```text
git diff --check
result=pass
```

```text
rg secret/token/password patterns in changed docs
result=no unredacted secret material found
```

```text
SECURITY_ARTIFACT_DIR=.tmp/s3-stage00-security-docs GITLEAKS_EXIT_CODE=1 bash scripts/security/scan-secrets.sh
result=no leaks found
scanned_bytes=159130482
```
