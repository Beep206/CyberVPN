# CyberVPN S1 Release Notes Template

> Use this template for every `stage1-beta-rc.N` and `stage1-beta-live.N` candidate.
> Deploy only by immutable tag or commit SHA. Do not deploy floating `main`.

## 1. Release Identity

| Field | Value |
|---|---|
| Release type | `RC` / `LIVE` |
| Release tag | `stage1-beta-rc.N` or `stage1-beta-live.N` |
| Commit SHA | `<immutable commit SHA>` |
| Source branch | `release/stage1-controlled-public-beta` |
| Prepared by | `<owner/operator>` |
| Prepared at | `<YYYY-MM-DD HH:MM TZ>` |
| Go/no-go owner | `@Sasha_Beep` |
| Support/on-call primary | `@Sasha_Beep` |
| Support/on-call backup | `@Sasha_Beep` |

## 2. Release Summary

Short summary:

- `<one-line summary of what this candidate proves>`
- `<main user-facing change>`
- `<main operational change>`

Launch intent:

```text
site / Telegram
-> registration/login
-> trial or one proven payment path
-> Remnawave provisioning
-> QR/subscription URL/config delivery
-> user connects
-> support/admin can recover the case
```

## 3. Backlog IDs Included

Every runtime change must reference an approved `S1-*` backlog ID.

| ID | Included change | Evidence |
|---|---|---|
| `S1-...` | `<change summary>` | `<evidence file/path>` |

## 4. Scope Included

| Area | Included in this candidate | Notes |
|---|---|---|
| Public website | Yes / No | `<pages/routes>` |
| Web cabinet | Yes / No | `<states proven>` |
| Telegram Bot | Yes / No | `<commands/webhook proof>` |
| Telegram Mini App | Yes / No | `<flows proven>` |
| Backend API | Yes / No | `<public/internal/admin boundary>` |
| Worker/scheduler | Yes / No | `<jobs enabled>` |
| Payments | Yes / No | `<enabled providers only>` |
| Remnawave provisioning | Yes / No | `<staging/prod evidence>` |
| Admin/support | Yes / No | `<roles/actions proven>` |
| Observability | Yes / No | `<dashboards/alerts>` |

## 5. Explicitly Disabled / Out of Scope

These must remain disabled unless a separate approved change request exists.

| Area | Required S1 state | Evidence |
|---|---|---|
| Partner portal / partner payouts | Disabled | `<flag/scope evidence>` |
| Referral / promo / gift public flows | Disabled by default | `<flag/UI/API evidence>` |
| Add-ons | Disabled by default | `<flag/UI/API evidence>` |
| Mobile store release | Out of S1 | `<scope evidence>` |
| Desktop / Android TV / browser extension | Out of S1 | `<scope evidence>` |
| Helix / Verta / Beep production | Disabled | `<flag/scope evidence>` |
| Auto-prolongation | Not promised; manual renewal only | `<copy/payment evidence>` |
| Full Talos/Kubernetes/GitOps migration | Not a S1 blocker | `<topology decision>` |

## 6. Evidence Pack Checklist

| Gate | Required evidence | Status | Link |
|---|---|---|---|
| Dirty worktree/scope map | Fresh before first RC | Pending / Pass / Blocked | `<link>` |
| Secrets scan | Current-tree scan and rotation decision | Pending / Pass / Blocked | `<link>` |
| Clean DB migrations | Staging/prod clean migration transcript | Pending / Pass / Blocked | `<link>` |
| First admin bootstrap | One-time bootstrap, 2FA, audit | Pending / Pass / Blocked | `<link>` |
| DNS/TLS/redirects | `.net` primary, `.org` redirects, admin domains | Pending / Pass / Blocked | `<link>` |
| CORS/cookies/CSRF | Deployed HTTPS evidence | Pending / Pass / Blocked | `<link>` |
| Payment provider | Real callback/status/signature/idempotency evidence | Pending / Pass / Blocked | `<link>` |
| Remnawave | Staging/prod profile, node and provisioning evidence | Pending / Pass / Blocked | `<link>` |
| Backup/restore | Backup config and restore drill | Pending / Pass / Blocked | `<link>` |
| Rollback | Component rollback proof | Pending / Pass / Blocked | `<link>` |
| Observability | Sentry/metrics/alerts/PII proof | Pending / Pass / Blocked | `<link>` |
| Legal/support | Final legal copy, mailboxes, support escalation | Pending / Pass / Blocked | `<link>` |

## 7. Feature Flags and Kill Switches

| Function | Expected state before release | Tested? | Evidence |
|---|---|---|---|
| Public registration | Controlled / disabled until go-live step | Yes / No | `<link>` |
| Trial | Controlled | Yes / No | `<link>` |
| Payments global | Controlled | Yes / No | `<link>` |
| Individual payment providers | Only evidence-proven provider enabled | Yes / No | `<link>` |
| Provisioning | Controlled | Yes / No | `<link>` |
| Referral/promo/gift | Disabled | Yes / No | `<link>` |
| Add-ons | Disabled | Yes / No | `<link>` |
| Telegram Mini App | Controlled | Yes / No | `<link>` |
| Notifications | Controlled | Yes / No | `<link>` |

## 8. Database and Migration Notes

| Item | Value |
|---|---|
| Current migration revision | `<revision>` |
| New migrations in this release | `<none/list>` |
| Pre-deploy backup required | Yes / No |
| Backward-compatible rollback | Yes / No / Not applicable |
| Manual DB steps | `<none/list>` |
| Data seed steps | `<plans/config/profile mappings>` |

## 9. Deployment Plan

1. Confirm release tag and commit SHA.
2. Confirm evidence pack and go/no-go status.
3. Take pre-deploy backup where applicable.
4. Deploy frontend/admin if changed.
5. Deploy backend/worker/bot if changed.
6. Apply migrations/seeds if approved.
7. Verify health checks.
8. Verify auth/session/cookie behavior.
9. Verify payment/provisioning smoke if enabled.
10. Verify support/admin visibility.
11. Verify alert delivery.
12. Start controlled cohort only after owner approval.

## 10. Rollback Notes

| Component | Rollback action | Data risk | Owner |
|---|---|---|---|
| Frontend/admin | `<previous artifact/tag>` | Low / Medium / High | `<owner>` |
| Backend API | `<previous artifact/tag or feature flags>` | Low / Medium / High | `<owner>` |
| Worker/scheduler | `<pause/previous artifact>` | Low / Medium / High | `<owner>` |
| Telegram Bot | `<disable webhook/commands or previous artifact>` | Low / Medium / High | `<owner>` |
| Payment provider | `<disable provider flag>` | Low / Medium / High | `<owner>` |
| Remnawave config | `<restore previous config/export>` | Low / Medium / High | `<owner>` |
| Database | `<restore only if approved; prefer forward fix>` | Low / Medium / High | `<owner>` |

Rollback success criteria:

- New risky actions are stopped.
- Existing paid users are not made worse.
- Payment/subscription/provisioning state is preserved.
- Support can identify impacted users.
- Monitoring shows error rate returns to acceptable level.
- Incident note is written.

## 11. Known Issues and Risk Acceptance

| Issue | Severity | User impact | Decision |
|---|---|---|---|
| `<issue>` | P0/P1/P2/P3 | `<impact>` | Fix before release / accept / defer |

No P0 launch blocker may be accepted without explicit owner sign-off.

## 12. Post-Release Checks

Run immediately after deployment and again after the first cohort.

| Check | Target | Result |
|---|---|---|
| API health | Healthy | Pending |
| Frontend routes | Public pages load | Pending |
| Login/session | Works over HTTPS | Pending |
| Trial -> VPN ready | Median <= 60s, p95 <= 5m | Pending |
| Paid -> VPN ready | Median <= 60s, p95 <= 5m | Pending |
| Paid-but-no-access | Zero unresolved older than 24h | Pending |
| Support queue | Test ticket visible | Pending |
| Admin audit | Privileged action logged | Pending |
| Alerts | Telegram and backup email delivered | Pending |
| Sentry/logs | No secret/PII leakage | Pending |

## 13. Approval

| Role | Approver | Decision | Timestamp |
|---|---|---|---|
| Owner / go-no-go | `@Sasha_Beep` | Go / No-go | `<timestamp>` |
| Support/on-call | `@Sasha_Beep` | Ready / Not ready | `<timestamp>` |
| Finance/ops | `@Sasha_Beep` | Ready / Not ready | `<timestamp>` |
| Technical release | `<name>` | Ready / Not ready | `<timestamp>` |

