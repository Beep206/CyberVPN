# CyberVPN S1 Release Notes: `stage1-beta-rc.2`

## 1. Release Identity

| Field | Value |
|---|---|
| Release type | `RC runtime snapshot` |
| Runtime tag | `stage1-beta-rc.2` |
| Git tag at checked commit | `stage1-beta-rc.1` |
| Commit SHA | `cb042eb77fbc71bec69f4410149e44b4986960bd` |
| Source branch | `main` at check time; intended branch remains `release/stage1-controlled-public-beta` |
| Prepared by | Codex |
| Prepared at | `2026-05-11T07:03:41Z` |
| Go/no-go owner | `@Sasha_Beep` |
| Support/on-call primary | `@Sasha_Beep` |
| Support/on-call backup | `@Sasha_Beep` |

## 2. Release Summary

This runtime candidate proves that the Stage 1 public surface can be operated on the prepared no-cost server topology:

- public website, admin domain, API health and mirror redirects are live;
- backend, frontend, admin, Telegram bot, worker, scheduler, PostgreSQL, Valkey, Remnawave and observability-related exporters are healthy;
- security/legal/support, backup/restore and rollback gates have current evidence;
- payments, public registration and provisioning remain intentionally disabled.

Launch intent remains:

```text
site / Telegram
-> registration/login
-> trial or one proven payment path
-> Remnawave provisioning
-> QR/subscription URL/config delivery
-> user connects
-> support/admin can recover the case
```

The full launch intent is not yet satisfied for outside beta users because production VPN node/provisioning and paid provider evidence are still blocked.

## 3. Backlog IDs Included

| ID | Included change | Evidence |
|---|---|---|
| `STAGE1-PUB-00` | Freeze and risk review | `docs/evidence/releases/stage1-pub-00-freeze-20260510T154942Z.md` |
| `STAGE1-PUB-01` | Runtime access and edge safety | `docs/evidence/routeros/stage1-pub-01-upnp-firewall-review-20260510T161807Z.md` |
| `STAGE1-PUB-02` | GitLab/CI alignment | `docs/evidence/gitlab/stage1-pub-02-gitlab-ci-20260510T162541Z.md` |
| `STAGE1-PUB-03` | RC packaging evidence | `docs/evidence/releases/stage1-beta-rc.1-rerun-after-03b/STAGE1_PUB_03_RERUN_AFTER_03B.md` |
| `STAGE1-PUB-04` | Runtime secrets/env redacted inventory | `docs/evidence/security/stage1-pub-04-env-inventory-redacted-20260510T175958Z.md` |
| `STAGE1-PUB-05` | App compose/internal network | `docs/evidence/releases/stage1-pub-05-compose-20260510T183400Z.md` |
| `STAGE1-PUB-06` | Data services | `docs/evidence/backups/stage1-pub-06-app-db-backup-20260510T185056Z.md` |
| `STAGE1-PUB-07` | Backend/API/Admin deploy | `docs/evidence/releases/stage1-pub-07-backend-admin-20260510T192426Z.md` |
| `STAGE1-PUB-08` | Frontend/public web deploy | `docs/evidence/releases/stage1-pub-08-frontend-screenshots-20260510T201837Z.md` |
| `STAGE1-PUB-09` | Telegram Bot/Mini App deploy | `docs/evidence/releases/stage1-pub-09-telegram-20260510T205338Z.md` |
| `STAGE1-PUB-10` | Remnawave/lab node deploy | `docs/evidence/releases/stage1-pub-10-remnawave-vpn-20260510T214814Z.md` |
| `STAGE1-PUB-11` | Payment path deploy safe-block | `docs/evidence/releases/stage1-pub-11-payments-20260510T220926Z.md` |
| `STAGE1-PUB-12` | Observability integration | `docs/evidence/observability/stage1-pub-12-app-observability-20260510T231455Z.md` |
| `STAGE1-PUB-13` | Security/legal/support gate | `docs/evidence/security/stage1-pub-13-security-legal-support-20260511T062902Z.md` |
| `STAGE1-PUB-14` | Backup/restore/rollback gate | `docs/evidence/releases/stage1-pub-14-rollback-dry-run-20260511T064630Z.md` |
| `STAGE1-PUB-15` | Final go/no-go | `docs/evidence/releases/stage1-pub-15-go-no-go-20260511T070341Z.md` |

## 4. Scope Included

| Area | Included in this candidate | Notes |
|---|---|---|
| Public website | Yes | Public pages and legal/status routes are live |
| Web cabinet | Partial | Runtime exists; public registration is disabled |
| Telegram Bot | Yes, controlled | Webhook runtime is live; payments/referral disabled |
| Telegram Mini App | Partial | Runtime path exists; paid/trial provisioning gated |
| Backend API | Yes | Public/internal/admin boundaries verified in prior gates |
| Worker/scheduler | Yes | Running and healthy |
| Payments | Disabled | `PAYMENTS_ENABLED=false`; no paid checkout |
| Remnawave provisioning | Disabled for users | Control-plane and lab node proven; no user-facing production node |
| Admin/support | Yes, controlled | Admin route/auth/audit/RBAC evidence exists |
| Observability | Yes | Prometheus reachable; dashboards/alerts evidence exists |

## 5. Explicitly Disabled / Out of Scope

| Area | Required S1 state | Evidence |
|---|---|---|
| Partner portal / partner payouts | Disabled | Stage 3 scope |
| Referral / promo / gift public flows | Disabled | `REFERRAL_ENABLED=false`, `PROMO_CODES_ENABLED=false`, `GIFT_CODES_ENABLED=false` |
| Add-ons | Disabled | S1 product flags remain off |
| Mobile store release | Out of S1 | Stage 4 |
| Desktop / Android TV / browser extension | Out of S1 | Stage 5 |
| Helix / Verta / Beep production | Disabled | Future private transport stage |
| Auto-prolongation | Not promised; disabled | `PAYMENT_AUTORENEWAL_ENABLED=false` |
| Full Talos/Kubernetes/GitOps migration | Not a S1 blocker | Simple controlled container topology |

## 6. Evidence Pack Checklist

| Gate | Status | Link |
|---|---|---|
| Dirty worktree/scope map | Warning | broad dirty tree remains; see go/no-go evidence |
| Secrets scan | Pass | `STAGE1-PUB-13`, `STAGE1-PUB-14` |
| Clean DB migrations | Pass local/runtime | `STAGE1-PUB-06`, `STAGE1-PUB-14` |
| First admin bootstrap | Pass previous S1 gate | admin evidence pack |
| DNS/TLS/redirects | Pass | `STAGE1-PUB-01`, `STAGE1-PUB-13` |
| CORS/cookies/CSRF | Pass previous runtime/admin gates | `STAGE1-PUB-07`, `STAGE1-PUB-13` |
| Payment provider | Blocked for paid beta | `STAGE1-PUB-11` |
| Remnawave | Partial | `STAGE1-PUB-10` |
| Backup/restore | Pass | `STAGE1-PUB-14` |
| Rollback | Pass dry-run | `STAGE1-PUB-14` |
| Observability | Pass with warning alerts | `STAGE1-PUB-12`, `STAGE1-PUB-15` |
| Legal/support | Pass with notes | `STAGE1-PUB-13` |

## 7. Feature Flags and Kill Switches

| Function | Expected state before release | Current state | Tested? |
|---|---|---|---|
| Public registration | Disabled until explicit go-live | `REGISTRATION_ENABLED=false` | Yes |
| Trial | Controlled | Bot flag true, backend provisioning false | Partial |
| Payments global | Disabled | `PAYMENTS_ENABLED=false` | Yes |
| Individual payment providers | Disabled | CryptoBot/Stars disabled | Yes |
| Provisioning | Disabled until production node | `STAGE1_*_PROVISIONING_ENABLED=false` | Yes |
| Referral/promo/gift | Disabled | false | Yes |
| Add-ons | Disabled | disabled by S1 scope | Yes |
| Telegram Mini App | Controlled | runtime only | Partial |
| Notifications | Controlled | observability evidence exists | Yes |

## 8. Database and Migration Notes

| Item | Value |
|---|---|
| Current app migration revision | `20260423_p27_partner_events` |
| New migrations in this runtime step | none |
| Pre-deploy backup required | yes for future changes |
| Backward-compatible rollback | dry-run only; DB restore available |
| Manual DB steps | none for internal smoke |
| Data seed steps | no real-user seed approved |

## 9. Deployment Plan

Current decision does not deploy a wider cohort.

Allowed:

1. Keep current runtime online.
2. Run internal smoke.
3. Watch observability and support workflow.
4. Close production VPN node/provisioning/payment blockers.

Blocked:

1. Public registration.
2. Paid checkout.
3. Trial provisioning to real users.
4. External beta cohort invitations.

## 10. Rollback Notes

| Component | Rollback action | Data risk | Owner |
|---|---|---|---|
| Frontend/admin | previous immutable local image where available | Low | `@Sasha_Beep` |
| Backend API | previous immutable local image + kill switches | Medium | `@Sasha_Beep` |
| Worker/scheduler | current known-good image; pause jobs with flags | Medium | `@Sasha_Beep` |
| Telegram Bot | previous immutable local image or disable webhook/commands | Medium | `@Sasha_Beep` |
| Payment provider | keep provider/global payment flags disabled | Low | `@Sasha_Beep` |
| Remnawave config | restore/export from latest backup or rebuild lab state | Medium | `@Sasha_Beep` |
| Database | restore only with explicit owner approval; prefer forward fix | High | `@Sasha_Beep` |

## 11. Known Issues and Risk Acceptance

| Issue | Severity | User impact | Decision |
|---|---:|---|---|
| No production VPN node | P0 | Real users cannot get approved VPN access | Fix before beta users |
| Payments disabled/provider not proven | P0 | Paid beta impossible | Fix before paid cohort |
| Public registration disabled | P0 for public launch | New users cannot self-register | Keep disabled until explicit owner go |
| Trial/paid provisioning disabled | P0 | No VPN delivery to users | Fix before user invite |
| Dirty worktree/rc.2 not immutable Git tag | P1 | Reproducibility risk | Commit/tag before expansion |
| Active swap alerts | P2 | Host pressure risk | Review before external users |
| Support/refund mailbox DNS not proven | P1 | Email support may fail | Use Telegram/on-call until fixed |

## 12. Post-Release Checks

| Check | Target | Result |
|---|---|---|
| API health | Healthy | Pass |
| Frontend routes | Public pages load | Pass |
| Login/session | Admin login route loads | Partial |
| Trial -> VPN ready | Median <= 60s | Blocked |
| Paid -> VPN ready | Median <= 60s | Blocked |
| Paid-but-no-access | Zero unresolved older than 24h | Pass by no paid traffic |
| Support queue | Test ticket visible | Not run in this gate |
| Admin audit | Privileged action logged | Covered by earlier tests/evidence |
| Alerts | Telegram and backup email delivered | Covered by `STAGE1-PUB-12`; current host swap warnings active |
| Sentry/logs | No secret/PII leakage | Covered by `STAGE1-PUB-12`/`13` |

## 13. Approval

| Role | Approver | Decision | Timestamp |
|---|---|---|---|
| Owner / go-no-go | `@Sasha_Beep` | Pending | Pending |
| Support/on-call | `@Sasha_Beep` | Ready for internal smoke | 2026-05-11T07:03:41Z |
| Finance/ops | `@Sasha_Beep` | Not ready for paid beta | 2026-05-11T07:03:41Z |
| Technical release | Codex | Ready for internal smoke; no-go for real users | 2026-05-11T07:03:41Z |

## 14. Final Hygiene

```text
git diff --check: pass
targeted secret scan over release notes/go-no-go docs: no matches
targeted static-dangerous-pattern scan over release notes/go-no-go docs: no matches
npm audit --omit=dev --audit-level=high: exit 0, no high/critical findings
```

Residual dependency note:

```text
2 moderate postcss/Next.js audit findings remain.
npm audit fix --force proposes a breaking Next.js downgrade and was not applied.
```
