# S3-STAGE-00 Partner/Event Backbone Readiness Decision Evidence

**Stage:** `S3-STAGE-00: Partner/Event Backbone Readiness Decision`
**Date:** 2026-05-24
**Snapshot time:** 2026-05-24T15:12:27Z
**Runtime host:** `prod-app-1`
**Decision:** `APPROVE_OPTION_A`

---

## 1. Summary

`S3-STAGE-00` is approved as a preparation gate for S3, not as permission to enable production partner money flows.

Approved path:

```text
APPROVE_OPTION_A
```

Meaning:

- S3 may proceed to documentation, scope freeze, domain model work and non-production event-backbone proof.
- Production partner event backbone remains disabled until real broker/dispatcher/consumer evidence exists.
- Production partner payouts remain disabled until finance, maker-checker, audit, sandbox and rollback evidence exists.
- Production reseller storefronts remain disabled until staging rehearsal and controlled partner pilot gates are passed.
- `accepted_no_transport` rows remain valid S2 stabilization evidence, but they are not S3 broker-delivery evidence.

---

## 2. Documents Reviewed

Reviewed before the decision:

- `docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md`
- `docs/plans/2026-05-23-cybervpn-s3-stage00-partner-event-backbone-readiness-decision.md`
- `docs/evidence/releases/s2-stage-18-stabilization-20260523.md`
- `docs/evidence/releases/s2-stage-18-outbox-backlog-closure-20260523.md`
- `docs/plans/2026-05-10-cybervpn-stage3-partner-reseller-platform-plan.md`

The S3 roadmap remains stable at `S3-STAGE-00` through `S3-STAGE-18`. New work must be added inside existing stages, not by inventing new top-level stage numbers.

---

## 3. Production Snapshot

Observed on `prod-app-1` during this gate:

```text
CYBERVPN_IMAGE_TAG=main-0b454923
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=false
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
PAYMENT_RECONCILIATION_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
OAUTH_ENABLED_LOGIN_PROVIDERS=
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_PAYOUTS_ENABLED=not configured; treat as disabled
PARTNER_STOREFRONTS_ENABLED=not configured; treat as disabled
```

Container health:

```text
cybervpn-admin                running   healthy
cybervpn-backend              running   healthy
cybervpn-frontend             running   healthy
cybervpn-postgres             running   healthy
cybervpn-postgres-exporter    running   healthy
cybervpn-redis-exporter       running   healthy
cybervpn-remnawave            running   healthy
cybervpn-remnawave-postgres   running   healthy
cybervpn-remnawave-valkey     running   healthy
cybervpn-scheduler            running   healthy
cybervpn-telegram-bot         running   healthy
cybervpn-valkey               running   healthy
cybervpn-worker               running   healthy
```

Public probes:

```text
https://api.cyber-vpn.net/health             http=200
https://cyber-vpn.net/ru-RU                  http=200
https://cyber-vpn.net/ru-RU/miniapp/home     http=200
https://admin.cyber-vpn.net/ru-RU/login      http=200
```

Outbox state:

```text
events_status=published:17
publications_status=published:34
events_open=0
publications_open=0
```

Interpretation:

- S2 public runtime is healthy enough to remain online.
- There is no open S2 outbox backlog.
- S3 can start only as controlled preparation and non-production proof work.
- Current production state does not prove real broker delivery because the partner event backbone is disabled.

---

## 4. Approved S3 Entry Boundary

Allowed after this gate:

- `S3-STAGE-01` scope/backlog/decision freeze.
- `S3-STAGE-02` partner domain model and role contract.
- `S3-STAGE-03` non-production event backbone topology.
- Local/staging-only tests for event delivery, consumer receipts, replay and idempotency.
- Documentation and evidence updates.

Not allowed after this gate:

- production partner payouts;
- public reseller storefronts;
- production partner event fan-out claims;
- treating `accepted_no_transport` as NATS/JetStream delivery;
- changing S2 customer runtime as a test bed for S3 experiments;
- adding new `S3-STAGE-19+` numbers without a separate owner decision.

---

## 5. Required Evidence Before Production Partner Enablement

Hard blockers remain:

| ID | Blocker | Evidence Required |
|---|---|---|
| `S3-BLOCKER-001` | S2 remains stable while S3 preparation starts | Daily or periodic S2/S3 stabilization snapshots with no unresolved P0/P1 |
| `S3-BLOCKER-002` | Event backbone target selected | Owner-approved NATS JetStream or equivalent topology |
| `S3-BLOCKER-003` | Broker proven in non-production | Stream create, publish, consume and replay transcript |
| `S3-BLOCKER-004` | Dispatcher proven | Outbox `pending -> claimed -> submitted -> published` evidence |
| `S3-BLOCKER-005` | Consumers proven | Durable receipt/projection evidence |
| `S3-BLOCKER-006` | Idempotency proven | Duplicate event replay does not double-apply rewards, attribution or settlements |
| `S3-BLOCKER-007` | Alerts proven | Pending age, publish failures, consumer lag and dead-letter alerts |
| `S3-BLOCKER-008` | Partner finance boundary approved | Maker-checker, audit log, manual review and payout policy |
| `S3-BLOCKER-009` | Partner legal/support copy approved | Partner terms, payout policy and support escalation |
| `S3-BLOCKER-010` | Kill switches proven | Partner portal, storefronts, event backbone and payouts pause independently |

---

## 6. Next Stage

Proceed to:

```text
S3-STAGE-01: S3 Scope, Backlog, And Decision Freeze
```

S3-STAGE-01 must not implement partner runtime yet. It should freeze the S3 PRD/charter, backlog, role owners, kill switch matrix, excluded items and evidence rules.
