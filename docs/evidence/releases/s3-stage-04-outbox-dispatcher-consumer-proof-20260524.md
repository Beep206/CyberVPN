# S3-STAGE-04 Evidence: Outbox Dispatcher And Consumer Proof

**Date:** 2026-05-24
**Stage:** `S3-STAGE-04`
**Status:** Passed for local/non-production proof
**Evidence directory:** `docs/evidence/partner-platform/stage3-outbox-20260524T170000Z`

---

## 1. Summary

`S3-STAGE-04` proved the first real CyberVPN Stage 3 event path:

```text
transactional outbox -> dispatcher -> NATS JetStream -> durable consumer -> receipt/projection
```

The proof used disposable local PostgreSQL and NATS JetStream containers. The script removed the lab containers, volumes and network after completion.

---

## 2. Command

```bash
STAGE3_OUTBOX_EVIDENCE_DIR=docs/evidence/partner-platform/stage3-outbox-20260524T170000Z \
  bash scripts/partner/run-stage3-outbox-dispatcher-proof.sh
```

Observed run result:

```text
finished_at_utc=2026-05-24T17:23:17Z
status=ok
```

---

## 3. Main Results

From `summary.json`:

```text
status=ok
successful_event_status=published
published_publications=2
consumer_receipts=3
duplicate_delivery_idempotent=true
```

From `db-after-dispatch.json`:

```text
event_name=entitlement.grant.activated
event_status=published
analytics_mart.publication_status=published
operational_replay.publication_status=published
stream=PARTNER_EVENTS
subject=partner.<consumer>.entitlement.grant.activated.v1
```

From `dead-letter-proof.json`:

```text
publication_status=dead_letter
event_status=failed
last_error=stage3 synthetic broker unavailable
```

From `duplicate-idempotency-proof.json`:

```text
before_receipts=1
after_receipts=1
before_feed_events=1
after_feed_events=1
idempotent=true
```

From `metrics-proof.json`:

```text
labeled_samples=52
created_total present
published_total present
publish_failures_total present
lag_seconds buckets present
```

---

## 4. Blocker Found And Closed

The first end-to-end proof exposed a real dispatcher issue:

```text
OutboxPublicationModel.outbox_event was unavailable under lazy='raise' during dispatch.
```

Fix:

```text
OutboxRepository.claim_publications() now refetches claimed rows with outbox_event eager-loaded.
```

This matters because the dispatcher builds the NATS envelope from the persisted event row. Without this fix, runtime dispatch could claim publications but fail before broker publish.

---

## 5. Validation

Validation commands run:

```bash
bash -n scripts/partner/run-stage3-outbox-dispatcher-proof.sh
python -m py_compile scripts/partner/stage3_outbox_dispatcher_proof.py
cd backend && . .venv/bin/activate && ruff check src/infrastructure/messaging/nats_partner_runtime.py src/infrastructure/database/repositories/outbox_repo.py src/domain/enums/enums.py tests/unit/infrastructure/test_nats_partner_runtime.py ../scripts/partner/stage3_outbox_dispatcher_proof.py
cd backend && . .venv/bin/activate && pytest tests/unit/infrastructure/test_nats_partner_runtime.py -q --no-cov
```

Observed unit test result:

```text
5 passed
```

Container cleanup checks returned no partner lab containers, volumes or networks:

```text
docker ps | rg 'partner-nats|partner-postgres|partner-lab' -> no output
docker volume ls | rg 'partner_nats|partner_postgres|partner-lab' -> no output
docker network ls | rg 'partner-lab' -> no output
```

---

## 6. Decision

`S3-STAGE-04` is accepted for local/non-production proof.

Production remains disabled for:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_PORTAL_ENABLED=false
```

Next stage:

```text
S3-STAGE-05: Partner Portal Disabled-State Boundary
```
