> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Acceptance Gates

## Purpose

Acceptance gates define when Stage 1 is allowed to move from documents to implementation, from implementation to staging, from staging to beta, and from beta to production operation.

A gate is passed only when evidence exists. Verbal confirmation is not sufficient.

## Gate overview

| Gate | Name | Purpose | Result |
|---|---|---|---|
| G0 | Document Approval | Approve scope, requirements, spec and risks | Implementation may start |
| G1 | Repo/Release Candidate Freeze | Separate launch code from experimental work | Stage 1 candidate created |
| G2 | Local/Integration Readiness | Critical flows work in controlled dev/integration | Staging deploy allowed |
| G3 | Staging End-to-End | Full flow works on staging with separate services | Beta go-live candidate |
| G4 | Security/Legal/Operations | Secrets, legal, support, backup, rollback ready | Public beta allowed |
| G5 | Controlled Public Beta | Limited real users, real support loop | Stabilization evidence |
| G6 | Stage 1 Production Operation | Stage 1 is operational and monitored | Proceed to S2 planning |

## G0 — Document Approval Gate

### Required documents

- Stage 1 Charter.
- PRD/User Flows.
- Technical Specification.
- Payment Provider Readiness Matrix.
- Remnawave Provisioning Runbook.
- Admin/RBAC Matrix.
- Legal Pack. Local Terms, Privacy, AUP, Refund and Cookie Policy candidates exist in `72_STAGE1_LEGAL_001_TERMS_OF_SERVICE_EVIDENCE.md`, `73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`, `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md`, `75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md` and `76_STAGE1_LEGAL_005_COOKIE_POLICY_EVIDENCE.md`; owner-approved legal/text closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- Support Playbook.
- Risk Register.
- Go-live/Rollback Runbook.
- Approved Decision Log.
- Operational Inputs and Evidence Checklist.
- Technical Debt Register.

### Pass criteria

- Scope and out-of-scope approved.
- Hard blockers listed.
- Approved owner decisions tracked in `17_STAGE1_APPROVED_DECISION_LOG.md`; operational values, payment placeholder mappings and scope-map rules tracked in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`.
- Accepted placeholders and deferred items tracked in `19_STAGE1_TECH_DEBT_REGISTER.md`.
- Implementation backlog items have IDs and acceptance criteria.
- No critical contradiction between business requirements and launch safety remains unresolved.

## G1 — Repo/Release Candidate Freeze

### Required checks

- Dirty worktree reviewed.
- Experimental components excluded from runtime.
- Launch-critical/excluded scope map created using the categories in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`.
- Launch candidate branch/tag selected.
- Launch branch policy matches `release/stage1-controlled-public-beta`, `stage1-beta-rc.N`, `stage1-beta-live.N`.
- Feature flags/kill switches mapped.
- Release notes and rollback notes templates created; `S1-REL-005` local release notes template exists in `78_STAGE1_REL_005_RELEASE_NOTES_TEMPLATE_EVIDENCE.md`, while rollback dry-run remains tracked under `S1-REL-006`.

### Pass criteria

- There is a clear Stage 1 release candidate.
- Partner/native/Helix/browser extension are not accidentally enabled.
- No production secret appears in repo.
- All implementation tasks link to approved requirements.

## G2 — Local/Integration Readiness

### Required tests

| Area | Required proof |
|---|---|
| Backend | App starts, health endpoints work, public/internal routes protected |
| DB | Migrations apply to clean DB; local evidence exists in `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md`, staging evidence still required for go-live |
| Auth | Registration/login/logout; local admin 2FA enforcement proof exists in `64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`; local Telegram account linking/no-silent-merge proof exists in `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`; deployed support/audit/persona evidence still required |
| Payments | Sandbox/test provider events; signature verification; local idempotency proof exists in `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`; durable/live idempotency evidence still required before paid beta |
| Provisioning | Remnawave staging integration or local equivalent |
| Worker | Retry/reconciliation/expiry jobs work |
| Frontend | Critical flows render and handle states |
| Telegram | Bot/Mini App flows work against test backend; auth/linking contract is locally proven in `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`; real Telegram client/webhook evidence still required |
| Admin | RBAC/audit/security basics work; local manual subscription operation evidence exists in `67_STAGE1_ADM_006_MANUAL_SUBSCRIPTION_OPS_EVIDENCE.md`, deployed persona/UI/API and real Remnawave evidence still required |
| Logs | Sensitive values redacted |

### Pass criteria

- Critical flows pass without manual DB edits.
- Known failures are documented and not P0.
- No blocking security/logging/secrets issue remains.

## G3 — Staging End-to-End Gate

### Required staging evidence

1. User registers through website.
2. User starts trial: 3 days / 1 device.
3. Trial triggers Remnawave provisioning.
4. User receives QR/subscription URL/config file.
5. User can connect using generated config or documented verification equivalent.
6. User purchases plan with sandbox/test payment provider.
7. Webhook is verified and idempotent.
8. Duplicate webhook does not duplicate subscription/wallet/provisioning.
9. Payment success + Remnawave failure test preserves paid state and queues retry.
10. Subscription expiry/grace worker behaves as expected.
11. Telegram Bot/Mini App complete equivalent flow.
12. Admin/support can inspect safe payment/subscription/provisioning state. Local safe payment-attempt support/finance view evidence exists in `66_STAGE1_ADM_005_PAYMENT_ATTEMPTS_VIEW_EVIDENCE.md`; local manual subscription operation evidence exists in `67_STAGE1_ADM_006_MANUAL_SUBSCRIPTION_OPS_EVIDENCE.md`; deployed persona/UI/API, real provider and real Remnawave evidence remain required before go-live.
13. Alerts fire for simulated payment/provisioning/Remnawave failures.
14. Logs/Sentry do not leak config links/secrets/PII beyond policy.

### Pass criteria

- All P0 E2E cases pass.
- Evidence is stored under evidence pack.
- Public beta risks are understood and documented.

## G4 — Security, Legal and Operations Gate

### Security requirements

- Secrets scan clean or accepted findings documented.
- Frontend bundle/env scan clean; local proof exists in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`, and RC/staging/production deployed artifact scan still must be repeated with final env values.
- Admin 2FA enforced; local proof exists in `64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`, deployed browser/API persona proof still required.
- RBAC tested.
- Audit log tested; local privileged-action proof exists in `65_STAGE1_ADM_004_PRIVILEGED_AUDIT_LOG_EVIDENCE.md`, and manual subscription audit action is covered locally in `67_STAGE1_ADM_006_MANUAL_SUBSCRIPTION_OPS_EVIDENCE.md`; deployed audit-log/persona proof still required.
- CORS/cookie/CSRF verified.
- Swagger disabled publicly.
- Rate limits tested or risk-accepted.
- Backup encryption/storage decided.
- JWT/secret rotation runbook exists.

### Legal/privacy requirements

- Terms of Service final for S1 owner-approved legal/text closure.
- Privacy Policy final for S1 owner-approved legal/text closure; no public placeholder should remain in published copy.
- Acceptable Use Policy final for S1 owner-approved legal/text closure.
- Refund Policy final for S1 owner-approved legal/text closure.
- Cookie Policy final for S1 owner-approved legal/text closure if cookies/analytics are used.
- No-logs wording stance approved for S1: no absolute overpromise and operational metadata is disclosed where used.
- Data retention/manual export-delete procedure approved for S1.
- Abuse process documented and owner-approved for S1.
- Law enforcement request process documented and owner-approved for S1.
- Legal/text closure evidence exists in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; mailbox delivery, provider, cookie inventory, PII scrubbing and deployed workflow proofs remain operational/security/provider evidence, not legal-copy blockers.

### Operations requirements

- Support channels tested.
- Alert channel `-5173727789` and backup email `backup@cyber-vpn.net` tested.
- Support/refund mailboxes `support@cyber-vpn.net` and `refund@cyber-vpn.net` tested.
- Support templates prepared.
- AI support first-line has escalation path. Local runbook contract exists in `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`; deployed queue/alert/human SLA evidence remains required before go-live.
- On-call/ops owner `@Sasha_Beep` assigned; same-handle backup risk accepted for S1 or split before go-live.
- Status page ready.
- Backup restore drill completed.
- Rollback dry-run or proof completed.
- Go/no-go owner identified.

### Pass criteria

- No public-facing placeholder remains.
- No P0 operational gap remains.
- Support can handle the expected first-week incidents.

## G5 — Controlled Public Beta Gate

### Entry criteria

- G0–G4 passed.
- Production environment ready.
- Production Remnawave ready.
- At least one production payment path ready, or beta explicitly configured as trial-only with payments disabled. If payments are promised, payment path must be live.
- Kill switches tested.
- Alerts configured locally in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live Telegram/email delivery tested before go-live.
- Support online path tested.

### Rollout recommendation

Use progressive rollout:

1. Internal smoke test.
2. 3–5 trusted users.
3. 10–25 beta users.
4. 25–100 beta users only if metrics remain healthy.
5. Wider public beta if payment/provisioning/support metrics remain stable.

### Beta success metrics

The following metrics should be monitored daily:

- Registration success rate.
- Trial activation success rate.
- Payment success/failure rate.
- Provisioning success/failure rate.
- Time from paid/trial to VPN ready.
- Median `trial/pay -> VPN ready` <=60 seconds and p95 <=5 minutes.
- Support tickets per active user.
- “Paid but no access” count.
- Zero unresolved paid-but-no-access/orphan payments older than 24h.
- Remnawave/node availability.
- Worker queue lag.
- Sentry critical errors.

## G6 — Stage 1 Production Operation Gate

Stage 1 is considered operational when:

- Public beta has active users.
- No unresolved P0/P1 incident blocks the core flow.
- Support process is functioning.
- Payment reconciliation is running; local orphan-payment policy exists in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, local alert routing exists in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`, and deployed admin/support queue plus live alert delivery evidence must exist before paid beta.
- Provisioning retry system is functioning.
- Backups are running and restore was tested.
- Logs/metrics/alerts are reliable.
- Known issues are documented and classified.
- Decision is made whether to proceed to Stage 2 or continue stabilization.

## Automatic No-Go conditions

Any of these conditions forces No-Go:

- Auth broken.
- Payment path broken or untested while payments are enabled.
- Webhook idempotency not proven with durable Redis/DB persistence and live provider duplicate callbacks.
- Provisioning broken.
- Remnawave unavailable with no retry/support state.
- No rollback plan.
- No backup restore evidence.
- Admin not protected.
- Secrets leak.
- Legal pages contain placeholders.
- Support cannot process “paid but no access”.
- Critical alerts not working.
- Provider documentation-derived payment mapping not replaced by real evidence for an enabled provider.
- Unresolved paid-but-no-access/orphan payment can exceed 24h without P0 escalation.
- Dirty worktree launch-critical/excluded scope map missing before RC tag.

## Evidence pack index template

```text
Stage: S1 Controlled Public Beta
Gate: G3 Staging End-to-End
Date:
Release candidate:
Environment:
Reviewer:

Evidence files:
- commands.txt
- screenshots/
- test-output/
- logs-redacted/
- configs-redacted/
- payment-webhook-tests.md
- remnawave-provisioning-tests.md
- rollback-test.md
- backup-restore-test.md

Result: PASS / FAIL
Open issues:
Decision:
```
