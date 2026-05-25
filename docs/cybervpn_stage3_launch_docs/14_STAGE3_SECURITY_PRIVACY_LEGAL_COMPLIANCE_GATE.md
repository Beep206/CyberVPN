# Stage 3 Security, Privacy, Legal, And Compliance Gate

**Stage:** `S3-STAGE-14`
**Status:** Passed for local security/privacy/legal evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-13: Partner Observability And Alerting`

---

## 1. Назначение

S3-STAGE-14 закрывает security/privacy/legal/compliance риски перед controlled partner pilot.

Цель этапа: подтвердить, что партнёрский контур можно репетировать в staging и позже выкатывать в production disabled-state без известных high/critical blocker:

- partner legal copy зафиксирована для controlled pilot;
- payout policy остаётся sandbox/controlled;
- privacy/data sharing boundaries задокументированы;
- abuse policy покрывает основные fraud-сценарии;
- KYC/KYB решение принято для S3;
- RBAC и tenant isolation проверены тестами;
- webhook signing и replay protection доказаны;
- CSRF/CORS/session boundaries проверены;
- sensitive data leakage не обнаружен в изменениях этапа.

Этот этап не открывает партнёрский публичный pilot сам по себе. Он разрешает переходить к S3-STAGE-15 full staging rehearsal.

---

## 2. Decision

S3-STAGE-14 decision:

```text
APPROVED_FOR_S3_STAGING_REHEARSAL
```

Controlled partner pilot допускается только после:

```text
S3-STAGE-15 full partner staging rehearsal
S3-STAGE-16 production disabled-state deploy
S3-STAGE-17 owner-approved controlled partner pilot
```

Production defaults remain conservative:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_CODES_ENABLED=false
PARTNER_ATTRIBUTION_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
```

---

## 3. Partner Legal Copy Baseline

Partner legal copy is approved for controlled S3 pilot under these terms:

| Area | S3 requirement |
|---|---|
| Program status | Partner/reseller program is controlled pilot, not open public program. |
| Eligibility | CyberVPN may approve, restrict, suspend or terminate partner workspace access. |
| Attribution | CyberVPN attribution records are operational source of truth for pilot settlement. |
| Codes/storefronts | Partner codes and storefronts may be disabled for abuse, leakage, policy or support risk. |
| No guaranteed earnings | No partner is promised guaranteed revenue, traffic, payout timing or payout method. |
| Reporting | Reports are informational until settlement is approved by finance/admin. |
| Payouts | No live payouts in S3-STAGE-14; payouts require later approval and maker-checker controls. |
| Audit | Sensitive partner/admin actions must be auditable. |
| Support | Partner cases use controlled support/admin process, not shell/database access. |
| Data sharing | Customer data visible to partners remains redacted/minimized. |

Required partner documents for pilot:

```text
Partner Terms
Partner Program Rules
Partner Payout Policy
Partner Privacy/Data Sharing Notice
Partner Acceptable Use / Abuse Policy
```

These can be represented through the existing legal document/policy system and must be accepted before moving a partner from approved probation to live pilot access.

---

## 4. Payout Policy Baseline

S3 payout decision:

```text
live payouts disabled
settlement sandbox allowed only as read-only finance/admin surface
no partner self-serve withdrawal
no mass payout
no payout export to partner
no same-admin maker-checker bypass
```

Before any live payout:

1. finance/admin reviews settlement sandbox;
2. payout account verification/approval exists;
3. maker and checker are different privileged users;
4. refund/chargeback/hold/reserve impact is visible;
5. payout instruction is approved;
6. payout execution is dry-run proven;
7. legal seller/project owner approves payout method;
8. S3-STAGE-15 and S3-STAGE-17 evidence exists.

Live payout blockers:

```text
commission ledger mismatch
unapproved payout account
open payout dispute
chargeback/refund mismatch
audit log failure
missing KYC/KYB decision for the payout recipient
same-admin approval attempt
PARTNER_PAYOUTS_ENABLED=false
```

---

## 5. Privacy And Data Sharing

Partner-facing surfaces must not expose:

- raw customer email;
- raw Telegram id;
- phone number;
- raw user id;
- IP address;
- payment provider payload;
- provider customer id;
- VPN subscription URL;
- VPN config link;
- payout destination secrets;
- webhook signatures;
- OAuth codes;
- TOTP secrets;
- raw import files.

Allowed partner-facing data:

```text
masked customer label
aggregate conversion counts
workspace-scoped statement totals
redacted export fields
campaign/source/channel labels
case ids and workflow statuses
settlement explanation notes
```

Internal support/admin can see only the minimum operational context needed for diagnosis. Raw payment provider payloads, VPN subscription links and payout secrets remain out of partner ops overview.

---

## 6. Abuse Policy Baseline

S3 controlled partner pilot blocks or escalates:

| Abuse scenario | S3 response |
|---|---|
| Self-referral | Block attribution/reward; send repeated attempts to abuse queue. |
| Duplicate/multi-account abuse | Review queue and reward hold. |
| Code leakage | Disable code and freeze workspace if needed. |
| Incentivized fraud traffic | Restrict workspace, hold settlement, request evidence. |
| Chargeback/refund manipulation | Block payout until finance review. |
| Suspicious payout recipient | Require manual review/KYC/KYB decision. |
| Storefront misleading copy | Disable storefront and request correction. |
| Webhook abuse/replay | Reject invalid signature/timestamp/replay and preserve redacted evidence. |

Partner expansion is blocked while P0/P1 abuse signals are unresolved.

---

## 7. KYC/KYB Decision

S3 decision:

```text
KYC/KYB is manual/controlled for pilot.
No public self-serve cash payout is allowed before formal KYC/KYB policy.
```

For controlled pilot:

- partner identity/business information may be collected manually only when required;
- evidence must be stored outside public logs and outside Git;
- payout recipient must match approved partner/operator record;
- payout approval remains finance/admin controlled;
- KYC/KYB provider automation is deferred until payout scale or jurisdiction requirements justify it.

Before open partner payouts, S3 or later stage must define:

```text
required identity/business fields
document retention policy
jurisdiction restrictions
sanctions/abuse screening decision
manual review owner
appeal/rejection process
data deletion/export path
```

---

## 8. Security Proof Summary

| Area | Proof |
|---|---|
| RBAC | Partner workspace scope enforcement test passes. |
| Tenant isolation | Cross-realm isolation and outsider workspace denial tests pass. |
| Legal acceptance | Legal document set acceptance captures realm/storefront/principal context. |
| Abuse | S3 partner code/attribution anti-abuse e2e passes. |
| Webhook signing | Partner webhook receiver validates HMAC-SHA256 signatures. |
| Webhook replay | Partner webhook receiver validates timestamp and rejects repeated `event_id + body_sha256`. |
| CORS | Production CORS allows only approved primary origins. |
| CSRF | Cookie-auth unsafe requests require approved Origin/Referer; bearer/no-cookie remains allowed. |
| Secret scan | No real secret material found in changed S3-STAGE-14 files. |
| Static dangerous pattern scan | No new `eval/exec/os.system/subprocess shell/raw SQL f-string` match in changed S3-STAGE-14 code. |

---

## 9. Webhook Security Contract

The local partner webhook test receiver now requires these headers when the shared secret is configured:

```text
X-CyberVPN-Partner-Signature: sha256=<hmac_sha256(body)>
X-CyberVPN-Partner-Timestamp: <unix_seconds>
X-CyberVPN-Partner-Event-Id: <stable_event_id>
```

Replay policy:

```text
PARTNER_WEBHOOK_REPLAY_WINDOW_SECONDS=300
```

Rejected results:

```text
invalid_signature -> 401
invalid_timestamp -> 401
replay -> 409
invalid_json -> 400
too_large -> 413
```

The receiver writes redacted evidence and exposes:

```text
cybervpn_partner_webhook_test_receiver_requests_total{result=...}
cybervpn_partner_webhook_test_receiver_evidence_files
```

The receiver remains local-only and must not be exposed publicly until DNS, route, HMAC, replay, rate-limit, retention and rollback evidence are approved.

---

## 10. Residual Risks

| Risk | Status | Decision |
|---|---|---|
| Real partner payouts | Disabled | Not a blocker because S3-STAGE-14 does not enable live payouts. |
| Public partner storefronts | Disabled | Requires S3-STAGE-16/17 approval. |
| Public partner webhook route | Disabled | Local test receiver only. |
| KYC/KYB automation | Deferred | Manual/controlled pilot decision accepted; needed before payout scale. |
| External legal counsel review | Not evidenced here | Owner-approved copy is accepted for controlled pilot; obtain counsel review before open partner program if required. |
| npm moderate advisories | Existing | No high/critical advisory from `npm audit --audit-level=high`; moderate advisories tracked separately. |
| Live Loki/Sentry sensitive log proof | Deferred to live rehearsal | Local static scan passed; live query proof belongs to S3-STAGE-15/17. |

---

## 11. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Partner legal copy approved | Passed for controlled pilot baseline. |
| Tenant isolation доказан | Passed locally through partner scope and auth realm isolation tests. |
| No high/critical security blocker | Passed locally; `npm audit --audit-level=high` returns success. |
| Webhook signatures proven | Passed locally through HMAC validation test. |
| Replay protection proven | Passed locally through timestamp and duplicate `event_id + body_sha256` test. |
| CSRF/CORS/session checks | Passed locally through Stage 1 production security tests reused for S3 gate. |
| Abuse gate | Passed locally through S3 partner codes attribution anti-abuse e2e. |

---

## 12. Validation

Commands:

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

---

## 13. Next

```text
S3-STAGE-15: Full Partner Staging Rehearsal
```
