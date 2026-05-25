# S3-STAGE-14 Evidence: Security, Privacy, Legal, And Compliance Gate

**Date:** 2026-05-25
**Stage:** `S3-STAGE-14`
**Status:** Passed for local security/privacy/legal evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/14_STAGE3_SECURITY_PRIVACY_LEGAL_COMPLIANCE_GATE.md`

---

## 1. Summary

S3-STAGE-14 proves the controlled partner pilot security/privacy/legal baseline locally:

```text
partner legal copy baseline is approved for controlled pilot
payout policy remains sandbox/controlled
privacy/data sharing boundaries are documented
abuse policy covers self-referral, code leakage, fraud traffic and payout risk
KYC/KYB is manual/controlled for pilot; public self-serve payouts remain blocked
partner RBAC and tenant isolation tests pass
webhook HMAC signature validation and replay protection are proven
CORS and CSRF production safety tests pass
no high/critical dependency blocker from npm audit high gate
no real secret material found in changed S3-STAGE-14 files
```

This does not enable public partner portal, public storefronts, partner webhooks or live partner payouts.

---

## 2. Changed Files

```text
scripts/partner/run-webhook-test-receiver.py
backend/tests/security/test_stage3_partner_webhook_receiver_security.py
backend/tests/security/test_partner_scope_enforcement.py
infra/partner-lab/compose.yml
infra/partner-lab/README.md
docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md
docs/cybervpn_stage3_launch_docs/14_STAGE3_SECURITY_PRIVACY_LEGAL_COMPLIANCE_GATE.md
docs/evidence/releases/s3-stage-14-security-privacy-legal-compliance-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| Partner webhook HMAC signature validation | Passed |
| Partner webhook timestamp freshness validation | Passed |
| Partner webhook duplicate event replay rejection | Passed |
| Partner webhook sensitive payload redaction | Passed |
| Partner scope enforcement | Passed |
| Auth realm isolation | Passed |
| Legal document set acceptance context | Passed |
| Partner code attribution anti-abuse | Passed |
| Production CORS origin boundary | Passed |
| CSRF cookie-auth unsafe request boundary | Passed |
| Partner lab remains local-only by compose binding | Passed |
| Payouts remain disabled by S3 policy | Passed by decision/gate, not enabled |
| No high/critical npm blocker | Passed |
| Dangerous pattern scan | Passed |
| Secret scan | Passed with expected test-only false positives |

---

## 4. Commands

```bash
cd backend

.venv/bin/python -m pytest \
  tests/security/test_stage3_partner_webhook_receiver_security.py \
  tests/security/test_partner_scope_enforcement.py \
  tests/security/test_auth_realm_isolation.py \
  tests/integration/test_legal_document_acceptance.py \
  tests/e2e/test_s3_partner_codes_attribution_anti_abuse.py \
  tests/security/test_stage1_cors_cookie_config.py \
  tests/security/test_stage1_csrf_protection.py \
  -q --no-cov

.venv/bin/python -m ruff check \
  ../scripts/partner/run-webhook-test-receiver.py \
  tests/security/test_stage3_partner_webhook_receiver_security.py \
  tests/security/test_partner_scope_enforcement.py
```

Observed result:

```text
pytest S3 security/privacy/legal pack: 21 passed
ruff changed security files: All checks passed
```

Final hygiene:

```bash
git diff --check
npm audit --audit-level=high
rg -n "<secret-patterns>" <changed S3-STAGE-14 files>
rg -n "(eval\\(|exec\\(|os\\.system\\(|subprocess\\.|shell=True|text\\(f|\\.execute\\(f)" <changed S3-STAGE-14 code>
docker ps --format '{{.Names}}\t{{.Status}}'
```

Observed result:

```text
git diff --check: passed
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this gate
secret scan: no real secret material found
dangerous pattern scan: no new dangerous pattern in changed S3-STAGE-14 code
docker ps: no running containers reported
```

---

## 5. Webhook Proof Details

Required headers:

```text
X-CyberVPN-Partner-Signature
X-CyberVPN-Partner-Timestamp
X-CyberVPN-Partner-Event-Id
```

Validated locally:

```text
valid HMAC -> accepted by validation helper
invalid HMAC -> rejected
fresh timestamp -> accepted
stale timestamp -> rejected
first event_id + body_sha256 -> accepted
repeated event_id + body_sha256 -> rejected as replay
```

The test receiver still binds only to localhost in partner lab compose:

```text
127.0.0.1:9088:9088
```

---

## 6. Legal/Compliance Decision

Approved for controlled pilot:

```text
Partner Terms baseline
Partner Program Rules baseline
Partner Payout Policy baseline
Partner Privacy/Data Sharing Notice baseline
Partner Acceptable Use / Abuse Policy baseline
```

KYC/KYB decision:

```text
manual/controlled for pilot
no public self-serve cash payout
formal provider/jurisdiction policy required before open payouts
```

---

## 7. Residual Risk

| Risk | Status |
|---|---|
| Live partner payout | Disabled until later gates. |
| Public partner webhook route | Disabled; local receiver only. |
| External legal counsel sign-off | Not evidenced in code; owner-approved baseline accepted for controlled pilot. |
| Live Loki/Sentry sensitive log query proof | Deferred to S3-STAGE-15/17 live rehearsal. |
| npm moderate advisories | Existing, non-high/critical; track separately. |

---

## 8. Next

```text
S3-STAGE-15: Full Partner Staging Rehearsal
```
