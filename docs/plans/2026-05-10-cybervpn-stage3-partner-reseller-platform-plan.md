# CyberVPN Stage 3 Partner / Reseller Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare partner/reseller staging, reporting, settlement evidence, and observability without overloading S1/S2 production services.

**Architecture:** Stage 3 is prepared as an off-by-default partner lab plus observability/evidence contracts. Live production behavior is not enabled until DNS, partner staging routes, webhook signing, and sandbox data approvals are complete.

**Tech Stack:** Docker Compose, Caddy, Prometheus, Grafana, Loki, GitLab CI, Python 3.13, shell scripts.

---

## Stage 3 Entry Gate

Before executing this plan, complete:

```text
S3-STAGE-00: Partner/Event Backbone Readiness Decision
```

Decision document:

```text
docs/plans/2026-05-23-cybervpn-s3-stage00-partner-event-backbone-readiness-decision.md
```

Current recommendation is to prepare S3 documents and non-production event-backbone proof first, while keeping production partner event backbone, partner payouts and reseller storefronts disabled. The S2 `accepted_no_transport` outbox closure is valid S2 stabilization evidence, but it is not evidence of real broker delivery for S3.

---

## Task 1: Partner Lab Skeleton

**Files:**

- Create: `infra/partner-lab/compose.yml`
- Create: `infra/partner-lab/README.md`
- Create: `scripts/partner/run-webhook-test-receiver.py`

**Steps:**

1. Create an off-by-default Docker Compose profile named `manual`.
2. Bind the webhook test receiver to `127.0.0.1:9088`.
3. Mount evidence storage at `/srv/storage/evidence/settlements`.
4. Require HMAC secret from `/srv/cybervpn-h/secrets/partner-webhook-test.secret`.
5. Verify with `docker compose config` before starting anything.

**Acceptance:**

- Partner lab is resource-limited.
- No partner lab service starts by default.
- Webhook receiver is local-only until public routing is explicitly approved.

---

## Task 2: Stage 3 Observability

**Files:**

- Create: `infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json`
- Create: `infra/grafana/dashboards/stage3-partner-attribution-storefront-dashboard.json`
- Create: `infra/grafana/dashboards/stage3-partner-settlement-payout-dashboard.json`
- Create: `infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json`
- Create: `scripts/grafana/generate-stage3-partner-dashboards.py`
- Create: `infra/prometheus/rules/stage3_partner_reseller_alerts.yml`

**Steps:**

1. Generate dashboards with `python3 scripts/grafana/generate-stage3-partner-dashboards.py`.
2. Validate dashboards as JSON.
3. Validate Prometheus rules with `promtool check rules`.
4. Install dashboards and rules on `10.10.10.34`.
5. Reload Prometheus.
6. Verify Grafana search returns all Stage 3 dashboards.

**Acceptance:**

- Stage 3 dashboards are visible in Grafana.
- Prometheus loads Stage 3 recording rules and alerts.
- Alerts are safe before future partner metrics exist because expressions use zero fallbacks and traffic guards where needed.

---

## Task 3: Storefront Synthetic Checks

**Files:**

- Create: `infra/prometheus/targets/stage3-storefront-endpoints.json`
- Create: `scripts/partner/check-storefront-synthetic-targets.sh`

**Steps:**

1. Define CyberVPN-only storefront staging targets.
2. Check DNS resolution before enabling live Prometheus scrape.
3. Do not add the job to live Prometheus until DNS exists.
4. Document Cloudflare records required for activation.

**Acceptance:**

- Target file exists.
- Current activation is blocked if DNS is missing.
- No failing live scrape is added to S1/S2 Prometheus.

---

## Task 4: Reporting Sandbox And Evidence

**Files:**

- Create: `scripts/partner/generate-stage3-sandbox-reports.sh`
- Create: `scripts/partner/redact-stage3-import.py`
- Create: `docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md`

**Steps:**

1. Generate sandbox report templates for referral attribution, commission ledger, payout simulation, settlement dry-run, anti-fraud experiments, imports, and incidents.
2. Add redaction tool for JSON, JSONL, and CSV imports.
3. Create server evidence tree under `/srv/storage/evidence/settlements`.
4. Test redaction with a synthetic payload.

**Acceptance:**

- No production data is required.
- Redacted imports hash identifiers and remove direct sensitive fields.
- Settlement evidence directories exist.

---

## Task 5: Partner CI Pipeline

**Files:**

- Modify: `.gitlab-ci.yml`
- Create: `scripts/validate-stage3-partner-artifacts.py`

**Steps:**

1. Add Stage 3 artifact validation job.
2. Add sandbox evidence generation job.
3. Keep heavy partner conformance jobs manual or rules-scoped.
4. Ensure existing `partner:lint`, `partner:test`, and `partner:build` remain unchanged.

**Acceptance:**

- Stage 3 CI validation passes locally.
- CI does not start partner lab services.
- CI does not store secrets or source maps as artifacts.

---

## Task 6: Runbooks And Incident Process

**Files:**

- Create: `docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md`
- Create: `docs/evidence/partner-platform/phase23-*.md`

**Steps:**

1. Document partner staging operations.
2. Document settlement evidence preservation.
3. Document webhook receiver usage and constraints.
4. Document DNS activation prerequisites.
5. Document incident response for partner finance, audit, risk, attribution, storefront, and support.

**Acceptance:**

- Runbook can be followed under pressure.
- Evidence pack exists locally and on server.
- DNS/service blockers are explicit.
