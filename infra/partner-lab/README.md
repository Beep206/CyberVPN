# CyberVPN Partner Lab

This directory contains off-by-default Stage 3 partner/reseller lab infrastructure for the home server.

The lab must not run as part of the default S1/S2 stack. Start it only for controlled staging, sandbox, or evidence work.

## Services

| Service | Purpose | Public by default |
|---|---|---|
| `partner-postgres` | disposable PostgreSQL 17 lab database for S3 outbox dispatcher evidence | no, bound to `127.0.0.1:6788` |
| `partner-nats` | local non-prod NATS JetStream proof broker for S3 event backbone work | no, bound to `127.0.0.1:4222` and `127.0.0.1:8222` |
| `partner-nats-box` | NATS CLI toolbox used only for manual smoke/evidence runs | no |
| `partner-webhook-test-receiver` | receives partner webhook test payloads and writes redacted evidence | no, bound to `127.0.0.1:9088` |

## S3 NATS JetStream Smoke

Use this proof before enabling any production partner event fan-out. The lab is off by default and is not part of the customer runtime.

```bash
bash scripts/partner/run-stage3-nats-jetstream-smoke.sh
```

The script:

- starts `partner-nats` only on localhost;
- creates the `PARTNER_EVENTS` stream with `partner.>` subjects;
- publishes one canonical partner event payload;
- proves durable consume and replay through separate pull consumers;
- captures `/healthz`, `/jsz`, stream info, publish output, consume output, replay output and checksums;
- stops containers and removes the temporary JetStream volume unless `KEEP_STAGE3_NATS_LAB=1` is set.

Evidence is written under:

```text
docs/evidence/partner-platform/stage3-nats-YYYYMMDDTHHMMSSZ
```

The generated NATS password is redacted from the compose config evidence. Do not commit rendered credentials or a live `NATS_URL`.

## S3 Outbox Dispatcher Smoke

Use this proof after the JetStream smoke and before any production partner event fan-out:

```bash
bash scripts/partner/run-stage3-outbox-dispatcher-proof.sh
```

The script:

- starts `partner-postgres` and `partner-nats` only on localhost;
- creates disposable outbox/runtime tables;
- appends a canonical event through `EventOutboxService`;
- proves dispatcher transitions from `pending` through `published`;
- proves NATS delivery into durable consumers and PostgreSQL consumer receipts;
- proves duplicate delivery is idempotent;
- proves retry/dead-letter behavior for a failed publication;
- captures backlog/alert input evidence;
- stops containers and removes temporary volumes unless `KEEP_STAGE3_OUTBOX_LAB=1` is set.

Evidence is written under:

```text
docs/evidence/partner-platform/stage3-outbox-YYYYMMDDTHHMMSSZ
```

## Start

```bash
cd /srv/cybervpn-h/compose/partner-lab
sudo docker compose --profile manual up -d partner-webhook-test-receiver
```

## Stop

```bash
cd /srv/cybervpn-h/compose/partner-lab
sudo docker compose --profile manual down
```

For the NATS lab, remove the temporary JetStream volume after a proof run unless you intentionally need to inspect the local state:

```bash
NATS_LAB_USER=stage3_lab NATS_LAB_PASSWORD=placeholder docker compose --profile manual down --volumes
```

## Evidence

Webhook receiver evidence is stored under:

```text
/srv/storage/evidence/settlements/webhook-receiver
```

Do not publish this service through Caddy until DNS, HMAC signing, rate-limits, and evidence retention have been reviewed.

## Webhook Security Contract

The local test receiver requires these headers when `PARTNER_WEBHOOK_SHARED_SECRET_FILE` or
`PARTNER_WEBHOOK_SHARED_SECRET` is configured:

```text
X-CyberVPN-Partner-Signature: sha256=<hmac_sha256(body)>
X-CyberVPN-Partner-Timestamp: <unix_seconds>
X-CyberVPN-Partner-Event-Id: <stable_event_id>
```

Replay guard:

- timestamp must be within `PARTNER_WEBHOOK_REPLAY_WINDOW_SECONDS`, default `300`;
- the same `event_id + body_sha256` is rejected as replay within the window;
- failed attempts are written as redacted evidence with `invalid_signature`, `invalid_timestamp` or `replay`;
- metrics expose `cybervpn_partner_webhook_test_receiver_requests_total{result=...}` for Stage 3 alerts.
