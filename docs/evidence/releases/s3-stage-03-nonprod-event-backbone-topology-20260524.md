# S3-STAGE-03 Non-Prod Event Backbone Topology Evidence

**Stage:** `S3-STAGE-03: Non-Prod Event Backbone Topology`
**Date:** 2026-05-24
**Decision:** `APPROVED_NONPROD_EVENT_BACKBONE=NATS_JETSTREAM_LOCAL_LAB`
**Prior gate:** `S3-STAGE-02: Partner Domain Model And Role Contract`

---

## 1. Summary

S3 non-production event backbone topology is approved and proven with local NATS JetStream.

The proof covered:

- localhost-only NATS JetStream runtime;
- stream creation;
- canonical JSON event publication;
- durable consumer delivery and ack;
- replay through a separate consumer;
- monitoring input through `/healthz` and `/jsz`;
- redacted evidence and checksums;
- cleanup of temporary containers/volumes after the run.

Production partner event backbone remains disabled.

---

## 2. Files Created Or Updated

Created:

- `docs/cybervpn_stage3_launch_docs/03_STAGE3_NONPROD_EVENT_BACKBONE_TOPOLOGY.md`
- `docs/evidence/releases/s3-stage-03-nonprod-event-backbone-topology-20260524.md`
- `docs/evidence/partner-platform/stage3-nats-20260524T164000Z/`
- `scripts/partner/run-stage3-nats-jetstream-smoke.sh`

Updated:

- `infra/partner-lab/compose.yml`
- `infra/partner-lab/README.md`
- `docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md`

---

## 3. Evidence Directory

Authoritative evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z
```

Summary:

```text
started_at_utc=2026-05-24T16:28:58Z
finished_at_utc=2026-05-24T16:29:05Z
status=ok
stream_name=PARTNER_EVENTS
subject_prefix=partner
consumer_name=stage3-proof
```

Key proof files:

```text
compose.config.yml
healthz.json
jsz-before.json
stream-add.txt
stream-info-after-add.json
published-event.json
publish.txt
stream-info-after-publish.json
consumer-add.txt
consumer-next.txt
consumer-info-after-ack.json
consumer-replay-add.txt
consumer-replay-next.txt
jsz-after.json
checksums.sha256
```

---

## 4. Topology Proof

Rendered compose config captured:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/compose.config.yml
```

Security posture:

- `partner-nats` is under the `manual` profile;
- NATS client port is bound to `127.0.0.1:4222`;
- NATS monitoring port is bound to `127.0.0.1:8222`;
- generated password is redacted in evidence;
- no public port or production network route is opened;
- containers are stopped after proof.

---

## 5. Stream Proof

Stream:

```text
PARTNER_EVENTS
```

Subjects:

```text
partner.>
```

Stream config observed:

```text
storage=file
retention=limits
discard=old
max_age=7d
max_msgs=10000
duplicate_window=2m
replicas=1
```

Evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/stream-add.txt
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/stream-info-after-add.json
```

---

## 6. Publish Proof

Subject:

```text
partner.analytics_mart.entitlement.grant.activated
```

Payload:

```json
{"event_id":"s3-stage03-proof-001","event_type":"entitlement.grant.activated","event_version":1,"consumer_key":"analytics_mart","aggregate_type":"partner_workspace","aggregate_id":"stage3-nonprod-proof","correlation_id":"s3-stage03-proof-001","idempotency_key":"analytics_mart:s3-stage03-proof-001","payload":{"result":"stage3_nonprod_jetstream_proof"}}
```

Publish result:

```text
Reading payload from STDIN
Published 353 bytes to "partner.analytics_mart.entitlement.grant.activated"
Stored in Stream: PARTNER_EVENTS Sequence: 1
```

Evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/published-event.json
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/publish.txt
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/stream-info-after-publish.json
```

---

## 7. Consume And Ack Proof

Consumer:

```text
stage3-proof
```

Filter:

```text
partner.analytics_mart.>
```

Observed result:

```text
consumer_seq=1
stream_seq=1
num_ack_pending=0
num_redelivered=0
num_pending=0
```

Evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/consumer-next.txt
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/consumer-info-after-ack.json
```

---

## 8. Replay Proof

Replay consumer:

```text
stage3-proof-replay
```

Replay result:

```text
same event_id=s3-stage03-proof-001 consumed from stream_seq=1
num_ack_pending=0
```

Evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/consumer-replay-next.txt
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/jsz-after.json
```

---

## 9. Monitoring Input Proof

Health endpoint:

```text
http://127.0.0.1:8222/healthz?js-enabled-only=true
```

JetStream monitoring endpoint:

```text
http://127.0.0.1:8222/jsz?streams=true&consumers=true
```

Observed:

```text
streams=1
consumers=2
messages=1
bytes=433
```

Evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/healthz.json
docs/evidence/partner-platform/stage3-nats-20260524T164000Z/jsz-after.json
```

Full Prometheus/Grafana/Alertmanager wiring remains assigned to `S3-STAGE-13`. S3-STAGE-03 proves the monitoring input source and expected fields.

---

## 10. Cleanup Proof

The smoke script uses `trap cleanup EXIT` and runs:

```bash
docker compose --profile manual down --volumes
```

Post-run container check returned no running `partner-nats` or `partner-lab` containers.

---

## 11. Production Boundary

Production state remains:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
```

This stage does not:

- enable production NATS;
- enable production partner webhooks;
- enable production partner payouts;
- change customer runtime;
- claim `accepted_no_transport` is broker delivery.

---

## 12. Exit Criteria Check

| Exit Criteria | Result |
|---|---|
| Broker target selected | Passed |
| Non-prod topology documented | Passed |
| Stream creation proof | Passed |
| Publish proof | Passed |
| Consume proof | Passed |
| Ack proof | Passed |
| Replay proof | Passed |
| Monitoring/alert input proof | Passed |
| Containers stopped after proof | Passed |
| Production partner event runtime remains disabled | Passed |

---

## 13. Local Validation

Commands completed:

```text
bash -n scripts/partner/run-stage3-nats-jetstream-smoke.sh
NATS_LAB_USER=stage3_lab NATS_LAB_PASSWORD=placeholder docker compose -f infra/partner-lab/compose.yml --profile manual config
git diff --check
secret/static pattern scan for new S3-STAGE-03 artifacts
npm audit --workspaces --audit-level=high --omit=dev
```

Validation result:

```text
script_syntax=passed
compose_config=passed
diff_check=passed
new_artifact_secret_scan=passed
new_artifact_static_dangerous_pattern_scan=passed
npm_audit_high=passed
```

Residual note:

```text
npm audit reported 4 moderate vulnerabilities in existing dependency tree.
No package dependency was changed by S3-STAGE-03.
```

---

## 14. Next Stage

Proceed to:

```text
S3-STAGE-04: Outbox Dispatcher And Consumer Proof
```
