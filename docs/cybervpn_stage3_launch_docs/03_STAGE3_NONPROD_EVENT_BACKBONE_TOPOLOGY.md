# Stage 3 Non-Prod Event Backbone Topology

**Stage:** `S3-STAGE-03`
**Status:** Approved non-production topology
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-02: Partner Domain Model And Role Contract`

---

## 1. Назначение

Этот документ фиксирует non-prod event backbone для Stage 3 до любой production-активации партнёрских событий, webhook fan-out, storefront attribution, отчётов или payout-related процессов.

Цель этапа: доказать, что CyberVPN может поднять управляемый брокер событий, создать stream, опубликовать каноническое партнёрское событие, прочитать его durable consumer'ом, повторно прочитать через replay consumer и получить monitoring payload для будущих alert rules.

---

## 2. Решение

Для S3 утверждён следующий baseline:

```text
APPROVED_NONPROD_EVENT_BACKBONE=NATS_JETSTREAM_LOCAL_LAB
PRODUCTION_PARTNER_EVENT_BACKBONE_ENABLED=false
```

На этом этапе production не подключается к NATS и не публикует партнёрские события наружу. Production по-прежнему работает в режиме disabled/no-transport для partner event backbone до `S3-STAGE-04` и последующих gates.

---

## 3. Topology

### 3.1 Local Lab Placement

| Component | Value |
|---|---|
| Compose file | `infra/partner-lab/compose.yml` |
| NATS image | `nats:2.12.7-alpine` |
| CLI image | `natsio/nats-box:0.18.0` |
| Profile | `manual` |
| Runtime default | off |
| Client port | `127.0.0.1:4222` |
| Monitoring port | `127.0.0.1:8222` |
| JetStream storage | Docker volume `partner_nats_jetstream` |
| Public exposure | none |
| Customer runtime dependency | none |

### 3.2 Why This Topology

Выбран локальный non-prod JetStream lab, потому что он:

1. не требует аренды дополнительных серверов;
2. не влияет на S1/S2 customer runtime;
3. даёт реальное broker evidence, а не mock;
4. повторяем в CI/lab окружении;
5. достаточно близок к будущему staging/prod NATS contract;
6. позволяет дальше проверять outbox dispatcher и consumers без преждевременной production-активации.

---

## 4. Stream Contract

| Field | Value |
|---|---|
| Stream name | `PARTNER_EVENTS` |
| Subjects | `partner.>` |
| Storage | file |
| Retention | limits |
| Discard policy | old |
| Max age | 7 days |
| Max messages | 10000 |
| Duplicate window | 2 minutes |
| Replica count | 1 for local lab |

For future real staging/prod, replica count, storage quota, TLS, auth accounts and node placement must be revisited. This S3-STAGE-03 decision approves the non-prod lab shape, not a final production cluster.

---

## 5. Subject Taxonomy

Baseline subject format:

```text
partner.<consumer_key>.<event_family>.<event_name>
```

Current proof subject:

```text
partner.analytics_mart.entitlement.grant.activated
```

Reserved consumer keys for current backend runtime:

| Consumer key | Purpose |
|---|---|
| `analytics_mart` | analytics/reporting projections |
| `operational_replay` | operational replay/support/feed projections |

Reserved event families remain aligned with the current application event taxonomy:

- `storefront`
- `realm`
- `order`
- `attribution`
- `growth_reward`
- `settlement`
- `risk`
- `entitlement`
- `service_access`
- `reporting`

---

## 6. Authentication And Secrets

Local lab authentication:

```text
NATS_LAB_USER=stage3_lab
NATS_LAB_PASSWORD=<generated random password unless explicitly provided>
```

Rules:

1. `NATS_URL` must not be committed with a real password.
2. Evidence must redact generated passwords.
3. Production `NATS_URL` remains unset/unused while `PARTNER_EVENT_BACKBONE_ENABLED=false`.
4. Future staging/prod must use approved secret storage, TLS and restricted client CIDRs.

---

## 7. Monitoring Contract

The local lab exposes NATS monitoring only on localhost:

```text
http://127.0.0.1:8222/healthz?js-enabled-only=true
http://127.0.0.1:8222/jsz
http://127.0.0.1:8222/jsz?streams=true&consumers=true
```

S3-STAGE-03 alert proof is limited to monitoring input evidence. Full Prometheus/Grafana/Alertmanager integration for partner event lag, publish failures, consumer lag and dead-letter behavior belongs to `S3-STAGE-13`.

Minimum future alert dimensions:

| Signal | Why it matters |
|---|---|
| JetStream health | Broker availability. |
| Stream message growth | Detect stopped consumers or unexpected event volume. |
| Consumer pending/ack state | Detect consumer lag. |
| Publish failures | Detect dispatcher or broker issues. |
| Replay/duplicate handling failures | Protect finance/reporting correctness. |

---

## 8. Backup And Rebuild Strategy

For the local lab, JetStream data is disposable. The source of truth for Stage 3 remains PostgreSQL transactional outbox until `S3-STAGE-04` proves dispatcher/consumer behavior.

Local lab rebuild:

```bash
NATS_LAB_USER=stage3_lab NATS_LAB_PASSWORD=placeholder \
  docker compose -f infra/partner-lab/compose.yml --profile manual down --volumes

bash scripts/partner/run-stage3-nats-jetstream-smoke.sh
```

Future staging/prod strategy:

1. PostgreSQL outbox remains durable source of truth.
2. NATS stream may be rebuilt from outbox/replay tooling.
3. Production backups are required only after production broker approval.
4. Dead-letter and replay evidence are required before enabling payouts or reporting that depend on event delivery.

---

## 9. Evidence

Authoritative evidence:

```text
docs/evidence/partner-platform/stage3-nats-20260524T164000Z
```

Key files:

| File | Proof |
|---|---|
| `compose.config.yml` | Rendered local topology with password redacted. |
| `healthz.json` | JetStream-enabled health endpoint. |
| `stream-add.txt` | Stream creation output. |
| `stream-info-after-add.json` | Stream created with expected config. |
| `published-event.json` | Canonical JSON payload used for proof. |
| `publish.txt` | JetStream publish acknowledgement. |
| `stream-info-after-publish.json` | Stream contains the published message. |
| `consumer-next.txt` | Durable consumer received payload and acked it. |
| `consumer-info-after-ack.json` | Ack floor advanced; no pending ack. |
| `consumer-replay-next.txt` | Separate replay consumer received the same payload. |
| `jsz-after.json` | Monitoring input with stream/consumer state. |
| `checksums.sha256` | Evidence checksums. |

Observed proof summary:

```text
status=ok
published_bytes=353
stream=PARTNER_EVENTS
subject=partner.analytics_mart.entitlement.grant.activated
messages=1
consumers=2
ack_pending=0
replay=ok
containers_after_smoke=stopped
```

---

## 10. Production Boundary

Production remains unchanged by this stage.

Required production state:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
```

Allowed after this stage:

1. Continue to `S3-STAGE-04`.
2. Use local/non-prod NATS for dispatcher and consumer proof.
3. Keep partner production runtime disabled.

Not allowed after this stage:

1. Claim production partner events are live.
2. Enable real partner webhook delivery.
3. Enable real partner payouts.
4. Treat `accepted_no_transport` as broker delivery evidence.

---

## 11. Exit Criteria Check

| Exit Criteria | Result |
|---|---|
| Broker target selected | Passed: NATS JetStream |
| Non-prod topology documented | Passed |
| Stream name frozen | Passed: `PARTNER_EVENTS` |
| Subject taxonomy frozen for S3 baseline | Passed |
| Auth/credentials model documented | Passed |
| Monitoring endpoint captured | Passed |
| Backup/rebuild strategy documented | Passed |
| Stream creation proof | Passed |
| Publish proof | Passed |
| Consume + ack proof | Passed |
| Replay proof | Passed |
| Alert input proof | Passed via `/jsz` evidence |
| Production remains disabled | Passed |

---

## 12. Next Stage

Proceed to:

```text
S3-STAGE-04: Outbox Dispatcher And Consumer Proof
```

Do not enable production partner event fan-out until `S3-STAGE-04` proves backend outbox dispatch, consumer receipts, retry/idempotency and dead-letter behavior.
