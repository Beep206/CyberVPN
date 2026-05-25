# Partner / Reseller Stage 3 Runbook

**Scope:** CyberVPN partner/reseller staging, sandbox reporting, settlement dry-runs, webhook testing, and partner incidents.  
**Home server:** `10.10.10.34`  
**Public domain scope:** CyberVPN `*.h.cyber-vpn.net` only.

---

## 1. Current Operating Mode

Stage 3 is prepared but intentionally off by default.

Allowed now:

- provision Grafana dashboards;
- load Prometheus rules that do not fire without traffic or future metrics;
- create settlement evidence directories;
- run local-only webhook receiver;
- generate sandbox reports;
- redact/anonymize synthetic or approved data imports.

Not allowed without explicit activation:

- public partner portal exposure;
- public partner webhook receiver;
- real payouts;
- real settlement close;
- production partner data imports without redaction approval.

---

## 2. Server Paths

```text
/srv/cybervpn-h/compose/partner-lab
/srv/cybervpn-h/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md
/srv/cybervpn-h/scripts/run-webhook-test-receiver.py
/srv/cybervpn-h/scripts/redact-stage3-import.py
/srv/cybervpn-h/scripts/generate-stage3-sandbox-reports.sh
/srv/cybervpn-h/scripts/check-storefront-synthetic-targets.sh
/srv/storage/evidence/settlements
```

Settlement evidence tree:

```text
/srv/storage/evidence/settlements/attribution
/srv/storage/evidence/settlements/commission-ledger
/srv/storage/evidence/settlements/payout-simulation
/srv/storage/evidence/settlements/settlement-dry-runs
/srv/storage/evidence/settlements/anti-fraud
/srv/storage/evidence/settlements/imports
/srv/storage/evidence/settlements/incidents
/srv/storage/evidence/settlements/webhook-receiver
```

---

## 3. Partner Lab

The partner lab compose stack is off by default.

Start local webhook receiver:

```bash
cd /srv/cybervpn-h/compose/partner-lab
sudo docker compose --profile manual up -d partner-webhook-test-receiver
```

Stop:

```bash
cd /srv/cybervpn-h/compose/partner-lab
sudo docker compose --profile manual down
```

Health check:

```bash
curl -fsS http://127.0.0.1:9088/health
```

The receiver writes redacted evidence to:

```text
/srv/storage/evidence/settlements/webhook-receiver
```

Do not expose this receiver through Caddy until all of these are done:

- DNS records exist;
- HMAC signature is required;
- replay guard is enabled through timestamp and stable event id headers;
- rate-limit policy is written;
- evidence retention policy is accepted;
- public webhook test route has a rollback plan.

Required webhook test headers:

```text
X-CyberVPN-Partner-Signature: sha256=<hmac_sha256(body)>
X-CyberVPN-Partner-Timestamp: <unix_seconds>
X-CyberVPN-Partner-Event-Id: <stable_event_id>
```

Replay window:

```text
PARTNER_WEBHOOK_REPLAY_WINDOW_SECONDS=300
```

---

## 4. Storefront Synthetic Checks

Target file:

```text
infra/prometheus/targets/stage3-storefront-endpoints.json
```

Server copy:

```text
/srv/cybervpn-h/configs/prometheus/targets/stage3-storefront-endpoints.json
```

Current expected state: prepared but not live-scraped until DNS exists.

Check DNS and HTTP readiness:

```bash
/srv/cybervpn-h/scripts/check-storefront-synthetic-targets.sh /srv/cybervpn-h/configs/prometheus/targets/stage3-storefront-endpoints.json
```

Cloudflare records required before live scrape:

```text
partner.h.cyber-vpn.net    A or CNAME to the CyberVPN edge
storefront.h.cyber-vpn.net A or CNAME to the CyberVPN edge
reseller.h.cyber-vpn.net   A or CNAME to the CyberVPN edge
```

Use DNS-only or proxied mode consistently with the rest of the CyberVPN edge plan.

---

## 5. Dashboards

Stage 3 dashboards:

- `Stage 3 Partner Staging Readiness`
- `Stage 3 Partner Attribution And Storefront`
- `Stage 3 Partner Settlement And Payout`
- `Stage 3 Partner Support Audit Risk`

Existing partner dashboards remain useful:

- `Partner Platform Runtime`
- `Partner Platform Frontend UX`

Operator use:

- use Stage 3 dashboards for readiness and sandbox evidence;
- use existing partner dashboards for runtime/UX drilldown;
- do not treat Prometheus as the long-term settlement ledger.

Stage 3 Prometheus assets:

```text
infra/prometheus/rules/stage3_partner_reseller_alerts.yml
infra/prometheus/targets/stage3-storefront-endpoints.json
```

Prometheus must load:

```text
stage3-storefront-endpoints
cybervpn_stage3_partner_reseller_recording_rules
cybervpn_stage3_partner_reseller_alerts
```

Minimum alert families:

- storefront synthetic failure;
- partner outbox lag, publish failure and dead-letter;
- payout review backlog;
- settlement dry-run / payout simulation failures;
- risk review backlog;
- audit log failure;
- webhook receiver failures;
- attribution no-owner spike;
- frontend errors.

---

## 6. Reporting Sandbox

Generate a sandbox evidence pack:

```bash
/srv/cybervpn-h/scripts/generate-stage3-sandbox-reports.sh
```

Expected reports:

- referral attribution test report;
- commission ledger test report;
- payout simulation report;
- settlement dry-run report;
- anti-fraud experiment report;
- redacted import manifest template;
- partner incident register.

All reports are templates until filled with approved synthetic or redacted data.

---

## 7. Redacted/Anonymized Data Import

Use only for sandbox imports, not production direct loading.

JSON example:

```bash
/srv/cybervpn-h/scripts/redact-stage3-import.py \
  /path/to/input.json \
  /srv/storage/evidence/settlements/imports/input.redacted.json \
  --salt stage3-sandbox-2026-05
```

JSONL example:

```bash
/srv/cybervpn-h/scripts/redact-stage3-import.py \
  /path/to/input.jsonl \
  /srv/storage/evidence/settlements/imports/input.redacted.jsonl \
  --format jsonl \
  --salt stage3-sandbox-2026-05
```

CSV example:

```bash
/srv/cybervpn-h/scripts/redact-stage3-import.py \
  /path/to/input.csv \
  /srv/storage/evidence/settlements/imports/input.redacted.csv \
  --salt stage3-sandbox-2026-05
```

Rules:

- direct identifiers are hashed;
- emails, phones, tokens, signatures, payout destinations, card/bank/wallet fields are redacted;
- generated manifest must be preserved;
- raw input must not be copied into evidence unless explicitly approved and encrypted.

---

## 8. Settlement And Payout Rules

Never run real payouts from the home lab.

Dry-run requirements:

- every dry-run gets an evidence directory;
- source fixture hash is recorded;
- policy version is recorded;
- output report hash is recorded;
- mismatch count is explicit;
- operator notes are written before changing settlement logic.

P0 blockers:

- commission ledger mismatch;
- audit log write failure;
- real payout failure;
- missing source fixture hash;
- unredacted production data in sandbox evidence.

---

## 9. Partner Incidents

Create incident evidence under:

```text
/srv/storage/evidence/settlements/incidents/<incident-id>
```

Minimum contents:

- `summary.md`;
- Grafana export or screenshot;
- Prometheus query output;
- Loki log extract with sensitive fields redacted;
- Sentry issue links if available;
- decision log;
- rollback or mitigation notes.

Incident families:

- partner portal staging outage;
- storefront synthetic failures;
- attribution no-owner/conflict spike;
- commission ledger mismatch;
- settlement dry-run failure;
- payout simulation failure;
- audit log failure;
- risk/anti-fraud backlog;
- partner support SLA breach;
- webhook receiver signature/JSON failures.

---

## 10. Activation Checklist

Before public partner staging:

- [ ] DNS records are created and verified.
- [ ] Caddy route plan is reviewed.
- [ ] partner lab stays off unless explicitly started.
- [ ] HMAC signing is required for webhook tests.
- [ ] storefront synthetic targets pass manually.
- [ ] Stage 3 dashboards are visible in Grafana.
- [ ] Stage 3 Prometheus rules are loaded.
- [ ] CI Stage 3 artifact validation passes.
- [ ] settlement evidence tree exists.
- [ ] redaction test passes with synthetic data.
- [ ] rollback owner is available.
