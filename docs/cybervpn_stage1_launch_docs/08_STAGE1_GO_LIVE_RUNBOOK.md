> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Go-Live and Rollback Runbook

## Purpose

Runbook описывает порядок ввода Stage 1 в эксплуатацию, проверки production readiness, staged rollout, emergency rollback и первые incident flows.

## Pre-flight checklist

Before production rollout:

- Approved Stage 1 documents exist.
- Launch candidate branch/tag selected.
- Production topology selected.
- Production domains configured.
- Public domains configured: `cyber-vpn.net` primary and `cyber-vpn.org` mirror/redirect.
- Admin domains configured and protected: `admin.cyber-vpn.net` primary and `admin.cyber-vpn.org` redirect to primary admin.
- TLS certificates valid.
- Backend/frontend/bot/worker/admin deployed or ready to deploy.
- Production PostgreSQL ready.
- Production Redis/Valkey ready.
- Production Remnawave ready.
- Production secrets stored securely.
- Payment provider production credential inventory is documented locally in `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`; real provider account and secret-store evidence must be attached before paid beta.
- Approved provider set checked: PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, YooKassa for users from Russia. Only providers with real evidence may be enabled; documentation-derived mappings in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` are placeholders.
- Webhook endpoints registered.
- Admin first user created securely.
- Admin 2FA/RBAC/audit verified.
- Sentry/metrics/alerts working; Telegram alert channel `-5173727789` and `backup@cyber-vpn.net` tested.
- Backups running.
- Restore drill completed.
- Legal pages final.
- Support templates ready.
- `support@cyber-vpn.net` and `refund@cyber-vpn.net` tested.
- Status page ready.
- Kill switches tested.

## Kill switches

The following must be controllable in Stage 1:

| Function | Expected control |
|---|---|
| Public registration | `REGISTRATION_ENABLED=false` or system config |
| Trial | Feature flag/env/system config |
| Payments | Provider-level disable or backend flag |
| Specific payment provider | Provider flag |
| Provider placeholder mapping | Must block provider enablement until replaced by real callback/status evidence |
| Referral | Feature flag; S1 default `REFERRAL_ENABLED=false` |
| Promo/gift codes | Feature flag; S1 default hidden/gated |
| OAuth Google/GitHub | Provider flag; enabled only after callback/linking evidence |
| Mini App rollout | Bot/menu/app flag or route control |
| Notifications | Worker/bot flag |
| Helix | Must remain disabled/default-off |
| Partner payouts | Must remain disabled |

## Go-live sequence

### Step 1 — Final production smoke test

1. Check API health.
2. Check frontend marketing pages.
3. Check customer cabinet login page.
4. Check Telegram Bot responds.
5. Check Mini App opens.
6. Check admin domain requires protected access and 2FA.
7. Check DB/Redis health.
8. Check Remnawave production health.
9. Check Sentry test event.
10. Check alert delivery to Telegram `-5173727789` and `backup@cyber-vpn.net` using the procedure in `docs/runbooks/STAGE1_OBSERVABILITY_ALERT_RUNBOOK.md`; local alert routing evidence is in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`.
11. Check support/refund mailboxes.

### Step 2 — Enable controlled functions

Recommended order:

1. Enable production frontend/site.
2. Enable auth with registration either off or limited for internal smoke.
3. Enable trial for internal smoke.
4. Test trial provisioning.
5. Enable payment provider for internal smoke.
6. Test low-value production payment if provider allows.
7. Verify payment -> provisioning.
8. Verify support/admin visibility.
9. Enable public registration in controlled mode.
10. Announce beta only to first cohort.

### Step 3 — First cohort

Start with a small cohort:

- 3–5 trusted users.
- Then 10–25 users.
- Then expand only if metrics are healthy.

Monitor:

- Registration errors.
- Payment errors.
- Orphan payments and paid-but-no-access age.
- Provisioning errors.
- Time to VPN ready.
- Support tickets.
- Remnawave/node health.
- Worker lag.
- Sentry errors.

### Step 4 — Stabilization loop

For first beta days:

- Review incidents daily.
- Review payment/provisioning reconciliation daily.
- Review support tickets daily.
- Review Sentry and critical alerts daily.
- Update known issues list.
- Do not enable partner/native/Helix scope without change request.

## Rollback strategy

Rollback should be component-specific where possible.

| Problem | Preferred action |
|---|---|
| Frontend regression | Roll back frontend only |
| Backend regression | Roll back backend if DB migrations allow; otherwise use maintenance/feature flags |
| Payment bug | Disable affected provider; keep support/reconciliation path |
| Provisioning bug | Stop new provisioning, preserve paid state, queue/manual support |
| Telegram Bot bug | Disable problematic commands/Mini App route; keep web path |
| Admin bug | Restrict admin access; use manual runbook if safe |
| Remnawave config issue | Roll back Remnawave config separately |
| Legal/support issue | Pause public registration/payments if public terms are invalid |

## Rollback success criteria

Rollback is successful when:

- Existing paid users are not made worse by the rollback.
- Payment/subscription/provisioning state is not lost.
- Users can still receive support.
- New risky actions are stopped.
- Monitoring confirms error rate returns to acceptable level.
- Incident note is written.

## Rollback dry-run evidence

Local `S1-REL-006` evidence exists in `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md`.

It proves a local release-pointer rollback, rollback-target Compose validation, Mini App/admin runtime rollback controls and registration/payment/provisioning safety tests. It is acceptable for continuing local/no-cost S1 work.

Before go-live, rollback must be repeated against staging/prod final RC artifacts and the real hosting/provider/Remnawave/backup/alert surfaces. The go-live evidence must include artifact versions, rollback target, command/procedure transcript, time-to-rollback, health checks and incident/status communication proof.

## Incident runbooks

### INC-S1-001 — User paid but no VPN access

1. Confirm user identity safely: email, Telegram, payment/order id.
2. Check payment status.
3. Check subscription status.
4. Check provisioning status.
5. If payment is not final, explain payment pending/failure state.
6. If payment is paid and provisioning failed, trigger retry if role permits.
7. If retry fails, escalate to ops.
8. Do not expose raw config links in support logs.
9. Add incident/evidence note if multiple users affected.

### INC-S1-002 — Duplicate payment webhook

1. Confirm duplicate event id/provider payment id.
2. Verify only one wallet transaction exists.
3. Verify only one subscription activation/extension exists.
4. Verify provisioning was not duplicated unsafely.
5. If duplicate side effect occurred, freeze provider and escalate.
6. Add regression test.

### INC-S1-003 — Orphan payment

1. Find provider payment id.
2. Determine whether customer/account identifier exists.
3. Put payment into `orphaned` or `reconciliation_required` state.
4. Create support ticket.
5. Ask user for safe account proof.
6. Manually attach payment only through role-gated audited operation.
7. Never create silent arbitrary account link.
8. Escalate as P1 after 1 hour and P0 before 24 hours if still unresolved.

### INC-S1-004 — Remnawave unavailable

1. Confirm Remnawave health from monitoring.
2. Disable new provisioning only if necessary; do not disable payments unless paid access cannot be delivered within acceptable support policy.
3. Queue provisioning retries.
4. Notify support with user-facing message.
5. Update status page if user impact exists.
6. Recover Remnawave or fail over if backup node/control plane exists.
7. Run reconciliation after recovery.

### INC-S1-005 — Auth/login broken

1. Confirm whether issue affects all auth or specific provider.
2. Disable affected OAuth/provider if needed.
3. Keep at least one safe auth path if possible.
4. If admin auth affected, use documented emergency owner path only.
5. Pause public registration if account creation is unsafe.
6. Communicate status if user-facing.

### INC-S1-006 — Secret leak suspected

1. Stop affected deployment/path.
2. Rotate affected secret.
3. Revoke sessions/tokens if JWT/OAuth/session affected.
4. Check logs/repo/build artifacts/frontend bundle.
5. Redeploy with rotated secret.
6. Document incident and blast radius.
7. Add regression check to secrets scan.

### INC-S1-007 — Production DB failure

1. Stop writes if data corruption is suspected.
2. Check backup availability.
3. Restore to clean environment if needed.
4. Verify payment/subscription/provisioning consistency.
5. Reconcile with payment provider and Remnawave.
6. Communicate status to users.
7. Document RPO/RTO achieved.

### INC-S1-008 — JWT secret compromised

1. Rotate JWT secret.
2. Revoke active sessions/refresh tokens.
3. Force re-login.
4. Check admin accounts and audit logs.
5. Check whether OAuth/TOTP/payment/Remnawave secrets also exposed.
6. Document incident.

## Communications

### User-facing channels

- Status page.
- Telegram bot notification/banner.
- Email if enabled.
- Support ticket reply.

### Internal channels

- Private Telegram alert channel `-5173727789`.
- Backup alert email `backup@cyber-vpn.net`.
- Evidence pack index: `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`.
- Incident notes.
- Go/no-go log.

## Post-launch stabilization checklist

Daily during Stage 1 beta:

- Review payment failures.
- Review orphan/paid-but-no-access payments and confirm none are older than 24h.
- Review provisioning failures.
- Review support tickets.
- Review Sentry critical errors.
- Review Remnawave/node health.
- Review worker queue lag.
- Review suspicious referrals/trials.
- Review logs for accidental PII/config URL leaks.
- Review backup status.
- Update known issues.
- Decide whether to expand beta cohort or pause.

## Stage 1 completion criteria

Stage 1 can be considered complete when:

- Core B2C flow is stable for real users.
- Payments and provisioning are reconciled.
- Support can resolve first-week issues.
- Known issues list has no unresolved P0/P1 blockers.
- Evidence pack is complete and all go-live blocker slots from `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md` are filled.
- A decision is made to proceed to Stage 2: Public Release 1.0.
