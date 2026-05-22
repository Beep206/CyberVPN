# CyberVPN Stage 2 Public Release 1.0 Master Plan

> **For Codex:** execute this plan task-by-task. Do not rename top-level `S2-STAGE-*` identifiers after this document is approved. If new work is discovered, attach it to the nearest existing stage as an item, blocker, or evidence requirement.

**Goal:** Move CyberVPN from Stage 1 Controlled Public Beta to Stage 2 Public Release 1.0: a stable public B2C VPN product that can be openly sold to users.

**Architecture:** Stage 2 keeps the proven S1 topology, then hardens it only where real S1 evidence shows pressure. Customer-facing runtime stays on rented servers. Home infrastructure remains non-critical for GitLab, CI, observability, evidence, dashboards, logs, and operational tooling.

**Tech Stack:** GitLab first, GitHub mirror/fallback, Docker Compose, FastAPI/Python, Next.js/React, Telegram Bot/Mini App, PostgreSQL, Valkey/Redis, Remnawave, Xray/VLESS/XHTTP, Caddy, Cloudflare, Prometheus/Grafana/Loki/Alertmanager, Sentry, backup/restore evidence.

---

## 1. Stage 2 Definition

Stage 2 is **Public Release 1.0**.

It is not a rewrite and not a feature expansion stage. Its purpose is to turn the S1 beta product into a public B2C release with stable purchase, trial, VPN provisioning, support, monitoring, legal, and operational flows.

### In Scope

- stabilized S1 user flows;
- public B2C website and Mini App readiness;
- final public pricing and plan catalog;
- stable registration/login without narrow beta invite dependency;
- production-ready payments;
- payment reconciliation and orphan-payment handling;
- clear subscription, expiry, renewal, refund, and support flows;
- Remnawave provisioning reliability;
- VLESS/XHTTP subscription delivery through `.org` subscription/node surface;
- production observability and S2 analytics dashboards;
- status page data source;
- support/admin operational readiness;
- legal/public-copy finalization;
- CI/CD and release-speed hardening;
- backup, restore, rollback, and release evidence.

### Out Of Scope For S2

- partner payouts;
- full partner/reseller portal production launch;
- mobile store release;
- desktop app release;
- Android TV release;
- browser extension release;
- Helix/Verta/Beep mass rollout;
- Kubernetes/Talos/GitOps migration as a blocker;
- enterprise-scale platform hardening.

Those belong to S3+ unless the owner explicitly changes the roadmap.

---

## 2. Numbering Contract

Top-level stage numbers are frozen:

- `S2-STAGE-00` through `S2-STAGE-18` are the only Stage 2 top-level stages.
- Do not insert `S2-STAGE-03A`, `S2-STAGE-19`, or renumber existing stages during normal execution.
- If new work appears, place it under the nearest existing stage as:
  - `Additional Work`;
  - `Blocker`;
  - `Evidence Required`;
  - `Deferred To S3+`.
- Every runtime code/config change must reference one `S2-STAGE-*` identifier in commit text, evidence, or deployment notes.
- Evidence files should use this format:

```text
docs/evidence/releases/s2-stage-XX-<short-name>-YYYYMMDD.md
```

### Release Branches And Tags

Recommended S2 release naming:

```text
release/stage2-public-1.0
stage2-public-rc.N
stage2-public-live.N
```

Deployment must use immutable commit SHA or immutable tag, never a floating branch alone.

---

## 3. Work Mode

S2 should be **local-first** wherever possible.

The normal loop is:

1. local implementation;
2. local tests and Docker smoke;
3. GitLab CI validation;
4. staging/prod-like smoke;
5. controlled production deployment;
6. evidence update.

Public production deploy must not be used for every small edit. We only deploy publicly when a group of changes has passed local and CI gates, unless the owner approves an urgent hotfix.

### Fast Fix Policy

For small Mini App/Bot/UI fixes:

- first reproduce locally;
- add or update a targeted test;
- deploy to production only when the fix is isolated and low-risk;
- commit/push afterward or immediately before deployment depending on urgency;
- record evidence.

For payment, auth, provisioning, database, security, or subscription changes:

- local tests are mandatory;
- staging/prod-like smoke is mandatory;
- production deploy must be gated.

---

## 4. Permanent S2 Stage List

| Stage | Name | Primary Work Mode | Exit Result |
|---|---|---|---|
| `S2-STAGE-00` | S1 Stabilization Freeze And Entry Decision | Docs + production evidence | Owner accepts that S1 is stable enough to start S2 |
| `S2-STAGE-01` | Local Fast-Fix And Test Baseline | Local | Local loop is fast, reproducible, and safe |
| `S2-STAGE-02` | S2 Scope, Backlog, And Decision Freeze | Docs | S2 scope is locked without S3 creep |
| `S2-STAGE-03` | Public Domain, Edge, And Route Contract | Local + prod config | Public route rules are final |
| `S2-STAGE-04` | Public Catalog And Pricing Finalization | Local + backend seed | Public plans are final and test-covered |
| `S2-STAGE-05` | Auth And Registration Public Readiness | Local + staging/prod-like | Public signup/login is safe |
| `S2-STAGE-06` | Payment Production Hardening | Local + provider smoke | Payments are reliable and auditable |
| `S2-STAGE-07` | Subscription, Renewal, Expiry, And Refund Flows | Local + staging/prod-like | Subscription lifecycle is clear |
| `S2-STAGE-08` | VPN Provisioning, Protocols, And Capacity | Local + Remnawave/prod node | VPN access is stable at public-release level |
| `S2-STAGE-09` | Support And Admin Operations | Local + admin smoke | Support can operate without developer-only access |
| `S2-STAGE-10` | Legal, Public Copy, And Trust Pages | Docs + frontend | Public legal/trust copy is release-ready |
| `S2-STAGE-11` | Observability And Analytics | Home ops + prod probes | S2 metrics are visible and actionable |
| `S2-STAGE-12` | Backup, Restore, And Disaster Recovery | Home ops + prod evidence | Restore and rollback are proven |
| `S2-STAGE-13` | Security, Abuse, And Privacy Gate | Local + edge + evidence | Public abuse/security risks are controlled |
| `S2-STAGE-14` | GitLab CI/CD And Release Speed | GitLab first | Release cycle is faster and repeatable |
| `S2-STAGE-15` | Full Staging/Public-Release Rehearsal | Staging/prod-like | Full S2 flow is proven before public release |
| `S2-STAGE-16` | Production Canary Release | Production | Small public cohort succeeds |
| `S2-STAGE-17` | Public Release 1.0 Go/No-Go | Production + owner sign-off | CyberVPN opens for public B2C sale |
| `S2-STAGE-18` | Post-Launch Stabilization And S3 Readiness | Operations | S2 is stable or paused with clear findings |

---

## 5. Stage Details

## S2-STAGE-00: S1 Stabilization Freeze And Entry Decision

**Purpose:** Decide that S1 Controlled Public Beta is stable enough to become the base for S2.

**Do First Locally:** No code work. Review evidence and current production behavior.

**Required Inputs:**

- latest S1 stabilization evidence;
- production Mini App/Bot smoke;
- VPN client proof;
- payment state;
- known issues list;
- current dirty worktree status;
- latest pushed GitLab/GitHub commit.

**Work:**

1. Review all open S1 blockers and beta issues.
2. Classify each issue as:
   - must fix before S2;
   - can fix during S2;
   - defer to S3+;
   - accepted risk.
3. Freeze S1 baseline commit.
4. Confirm S2 starts from `main` at a known commit.

**Evidence:**

```text
docs/evidence/releases/s2-stage-00-entry-decision-YYYYMMDD.md
```

**Exit Criteria:**

- owner accepts S1 as the S2 base;
- no unresolved P0/P1 customer-impacting issue is hidden;
- S2 work begins from a clean known commit.

---

## S2-STAGE-01: Local Fast-Fix And Test Baseline

**Purpose:** Make local development the default path so we stop waiting for public deploys for every small fix.

**Do First Locally:** Yes. This stage is mostly local.

**Work:**

1. Confirm local backend test command set.
2. Confirm local frontend test/lint command set.
3. Confirm local Telegram bot test command set.
4. Confirm local Docker smoke command set.
5. Document the fastest safe loop for:
   - Mini App UI fix;
   - bot text/handler fix;
   - backend subscription/provisioning fix;
   - payment webhook fix;
   - admin/support fix.
6. Ensure local smoke can run without production secrets.
7. Add missing targeted tests for the currently fragile areas:
   - invite redemption refresh;
   - subscription URL selection;
   - XHTTP subscription delivery expectations;
   - config unavailable states;
   - Russian/English locale leakage.

**Recommended Files To Check:**

- `backend/tests/`
- `frontend/src/app/[locale]/miniapp/**/__tests__/`
- `services/telegram-bot/tests/`
- `infra/deploy/stage1/`
- `docs/evidence/releases/`

**Evidence:**

```text
docs/evidence/releases/s2-stage-01-local-fast-fix-baseline-YYYYMMDD.md
```

**Exit Criteria:**

- local checks are documented;
- targeted smoke is repeatable;
- public deploy is no longer the first validation step.

---

## S2-STAGE-02: S2 Scope, Backlog, And Decision Freeze

**Purpose:** Prevent S2 from turning into S3/S4/S7.

**Do First Locally:** Docs only.

**Work:**

1. Create/confirm S2 backlog.
2. Mark every item as:
   - required for S2 public release;
   - optional for S2;
   - deferred to S3+.
3. Confirm S2 does not include partner payouts, mobile store release, desktop release, or Helix mass rollout.
4. Confirm public B2C is the only S2 launch surface.
5. Confirm owner go/no-go rules.

**Evidence:**

```text
docs/evidence/releases/s2-stage-02-scope-freeze-YYYYMMDD.md
```

**Exit Criteria:**

- S2 backlog is frozen;
- no unrelated launch surface is mixed into S2;
- every future task maps to a fixed `S2-STAGE-*`.

---

## S2-STAGE-03: Public Domain, Edge, And Route Contract

**Purpose:** Finalize public routing before opening wider access.

**Hard Rules:**

- `cyber-vpn.net` is the main customer-facing domain.
- `api.cyber-vpn.net` is the customer API domain.
- `admin.cyber-vpn.net` is the admin domain.
- `.org` is reserved for VPN nodes and subscription delivery only.
- `.org` must not be used as a general mirror of `.net`.
- HTTP/3/QUIC must stay enabled and must not be disabled.
- VPN node server must run only node workload, nothing extra.

**Work:**

1. Verify Caddy/Cloudflare routes.
2. Verify admin protection.
3. Verify API/webhook no-challenge routes.
4. Verify `.org` subscription URL and node routing.
5. Verify HTTP/3/QUIC.
6. Verify DNS/TLS expiry checks in observability.
7. Record current production route map.

**Evidence:**

```text
docs/evidence/releases/s2-stage-03-route-contract-YYYYMMDD.md
```

**Exit Criteria:**

- route contract is documented;
- no public route conflicts with `.org` node/subscription rule;
- edge behavior is observable.

---

## S2-STAGE-04: Public Catalog And Pricing Finalization

**Purpose:** Make pricing public-release ready.

**Status:** Completed locally on 2026-05-22.

**Do First Locally:** Yes. Seed data and UI must be tested locally.

**Work:**

1. Finalize public plans.
2. Finalize Russian-specific plans if they remain in S2.
3. Confirm hidden plans do not leak into public catalog.
4. Confirm plan traffic/device limits use safe database types.
5. Confirm quote behavior.
6. Confirm Mini App Plans copy is single-language per locale.
7. Confirm Home screen invite section and trial section ordering.
8. Confirm public catalog works without display-only fake price text.

**Testing:**

- backend pricing seed tests;
- Mini App plan page tests;
- Home page invite/trial tests;
- localization checks.

**Evidence:**

```text
docs/evidence/releases/s2-stage-04-public-catalog-YYYYMMDD.md
docs/cybervpn_stage2_launch_docs/03_STAGE2_PUBLIC_CATALOG_PRICING_CONTRACT.md
docs/evidence/releases/s2-stage-04-public-catalog-20260522.md
```

**Exit Criteria:**

- public catalog is final for S2;
- hidden/special tariffs are intentionally hidden or intentionally exposed;
- no mixed-language UX in core flows.

**Result:** Public plans remain Basic/Plus/Pro/Max; RU plans remain hidden/admin-only with `Mihomo (RU bundle)`; fake local currency display-only estimates were removed from public pricing/dashboard checkout surfaces; targeted frontend/backend tests passed.

---

## S2-STAGE-05: Auth And Registration Public Readiness

**Purpose:** Move from beta/invite-heavy access to safe public registration.

**Do First Locally:** Yes, then staging/prod-like smoke.

**Work:**

1. Confirm enabled auth methods:
   - email/password;
   - Telegram identity/linking;
   - magic link/OTP;
   - Google OAuth if production credentials are ready;
   - GitHub OAuth if production credentials are ready.
2. Decide whether public signup opens fully or gradually.
3. Add/verify rate limits for:
   - registration;
   - login;
   - Telegram auth;
   - magic links;
   - OAuth callback;
   - invite redemption.
4. Confirm account deletion works.
5. Confirm user export/privacy request path.
6. Confirm admin 2FA remains mandatory.
7. Confirm no default/admin bootstrap endpoint remains publicly usable.

**Evidence:**

```text
docs/evidence/releases/s2-stage-05-auth-registration-YYYYMMDD.md
```

**Exit Criteria:**

- public auth is safe enough to open beyond the first beta cohort;
- abuse controls exist;
- support can diagnose auth problems without seeing secrets.

---

## S2-STAGE-06: Payment Production Hardening

**Purpose:** Make payments reliable enough for public B2C sale.

**Do First Locally:** Payment adapters and webhook idempotency tests first. Provider smoke only after local pass.

**Work:**

1. Confirm the primary S2 payment path.
2. Confirm secondary payment paths only if they have credentials and evidence.
3. Confirm final payment statuses per provider.
4. Confirm webhook signature validation.
5. Confirm duplicate webhook idempotency.
6. Confirm paid-but-no-access queue.
7. Confirm orphan payment policy:
   - no paid-but-no-access/orphan item older than 24 hours without escalation.
8. Confirm payment reconciliation dashboard.
9. Confirm refund handling.
10. Confirm Telegram Stars behavior stays Telegram-only.
11. Build referral/promo/gift payment safety only behind kill switches.
12. Keep autoprolongation disabled until recurring consent/cancel/failure/refund evidence is complete.

**Evidence:**

```text
docs/evidence/releases/s2-stage-06-payment-hardening-YYYYMMDD.md
```

**Exit Criteria:**

- at least one live payment path is reliable and monitored;
- failed, duplicate, orphan, refund, and reconciliation paths are proven;
- payment support can operate without developer-only database access.

---

## S2-STAGE-07: Subscription, Renewal, Expiry, And Refund Flows

**Purpose:** Make the customer lifecycle clear after purchase or trial.

**Do First Locally:** Yes.

**Work:**

1. Confirm subscription states.
2. Confirm trial states and one-time trial rules.
3. Confirm manual renewal flow.
4. Confirm expiry reminders.
5. Confirm disabled/expired access behavior.
6. Confirm grace period decision.
7. Confirm renewal invoice/link flow if used.
8. Confirm refund state and access state after refund.
9. Confirm UI messages for expired, active, payment pending, provisioning pending, and config unavailable.
10. Confirm autoprolongation consent, cancellation, failed-renewal and reminder flows before enabling true recurring billing.

**Evidence:**

```text
docs/evidence/releases/s2-stage-07-subscription-lifecycle-YYYYMMDD.md
```

**Exit Criteria:**

- user and support both understand the subscription lifecycle;
- no paid user silently loses access without visible/supportable state.

---

## S2-STAGE-08: VPN Provisioning, Protocols, And Capacity

**Purpose:** Make VPN provisioning and subscription delivery stable enough for public release.

**Hard Rules:**

- subscription and node links should use `.org`;
- primary customer-facing config should be subscription URL, not raw `vless://`, unless explicitly requested by a client flow;
- XHTTP delivery must be validated through subscription;
- VPN node server must remain node-only.

**Work:**

1. Confirm Remnawave production control-plane health.
2. Confirm node inventory.
3. Confirm VLESS and XHTTP in subscription output.
4. Confirm Mihomo RU bundle behavior only for intended Russian plans.
5. Confirm retry behavior when Remnawave is down.
6. Confirm support/admin can reprovision or inspect status safely.
7. Confirm capacity for expected S2 public cohort.
8. Decide whether a second VPN node is needed before full public opening.

**Evidence:**

```text
docs/evidence/releases/s2-stage-08-vpn-provisioning-capacity-YYYYMMDD.md
```

**Exit Criteria:**

- users can reliably obtain a working subscription URL;
- VLESS/XHTTP expectations are proven;
- support can resolve provisioning failures.

---

## S2-STAGE-09: Support And Admin Operations

**Purpose:** Make support operational rather than developer-dependent.

**Do First Locally:** Admin UI/API tests first.

**Work:**

1. Confirm support queue.
2. Confirm customer lookup.
3. Confirm payment lookup.
4. Confirm subscription/provisioning lookup.
5. Confirm manual support grants remain audited.
6. Confirm admin dangerous actions are protected.
7. Split primary and backup support/on-call if possible before S2 launch.
8. Confirm support email/refund contact.
9. Confirm common support templates:
   - cannot login;
   - payment succeeded but no access;
   - VPN does not connect;
   - refund request;
   - subscription expired.

**Evidence:**

```text
docs/evidence/releases/s2-stage-09-support-admin-ops-YYYYMMDD.md
```

**Exit Criteria:**

- support can handle normal public user issues;
- support actions are audited;
- admin access remains protected.

---

## S2-STAGE-10: Legal, Public Copy, And Trust Pages

**Purpose:** Ensure public-facing terms and product promises are final for Release 1.0.

**Do First Locally:** Docs and frontend copy.

**Work:**

1. Confirm Terms of Service.
2. Confirm Privacy Policy.
3. Confirm Acceptable Use Policy.
4. Confirm Refund Policy.
5. Confirm Cookie Policy.
6. Confirm legal seller/public contact copy.
7. Confirm no-logs/privacy claims match actual architecture.
8. Confirm public website does not overpromise SLA, privacy, protocols, or geography.
9. Confirm support/refund contacts are visible.

**Evidence:**

```text
docs/evidence/releases/s2-stage-10-legal-trust-copy-YYYYMMDD.md
```

**Exit Criteria:**

- public legal pack is ready;
- marketing/trust text does not make claims the system cannot support.

---

## S2-STAGE-11: Observability And Analytics

**Purpose:** Give the owner operational visibility for public release.

**Do First Locally/Home Ops:** Most work stays on the home observability server.

**Work:**

1. Provision S2 Payment Reconciliation dashboard.
2. Provision S2 Refund And Renewal dashboard.
3. Provision S2 Subscription Expiry dashboard.
4. Provision S2 Support SLA dashboard.
5. Provision S2 Status Page Data Source dashboard.
6. Provision S2 Product Analytics dashboard.
7. Provision S2 Release Quality Gates dashboard.
8. Confirm Prometheus rules and alerts.
9. Confirm external probes for:
   - website;
   - API;
   - Mini App;
   - bot health where possible;
   - subscription URL endpoint;
   - VPN node health;
   - TLS expiry;
   - Cloudflare/edge health.
10. Confirm Sentry frontend release health and sourcemaps if enabled.
11. Confirm no sensitive payloads are logged.

**Evidence:**

```text
docs/evidence/releases/s2-stage-11-observability-analytics-YYYYMMDD.md
```

**Exit Criteria:**

- owner has dashboards for payments, access, support, product health, release health, and public endpoints;
- alerts reach Telegram/email;
- observability is useful without becoming the only source of production truth.

---

## S2-STAGE-12: Backup, Restore, And Disaster Recovery

**Purpose:** Ensure public release can survive operational mistakes and service failures.

**Work:**

1. Confirm PostgreSQL backup schedule.
2. Confirm off-host backup storage.
3. Confirm Remnawave backup/export/rebuild procedure.
4. Confirm GitLab backup status.
5. Confirm Sentry/Grafana/dashboard backup status.
6. Run restore drill.
7. Run rollback drill.
8. Confirm RPO/RTO targets.
9. Confirm secrets backup and rotation policy.

**Evidence:**

```text
docs/evidence/releases/s2-stage-12-backup-restore-dr-YYYYMMDD.md
```

**Exit Criteria:**

- restore is proven, not theoretical;
- rollback is proven, not theoretical;
- owner knows what is lost and how long recovery takes.

---

## S2-STAGE-13: Security, Abuse, And Privacy Gate

**Purpose:** Make public access safe enough to open.

**Work:**

1. Run dependency audit.
2. Run secrets scan.
3. Run frontend bundle/env leak scan.
4. Confirm WAF/rate-limit rules.
5. Confirm payment webhook routes are protected but not blocked by challenge pages.
6. Confirm auth abuse controls.
7. Confirm trial abuse controls.
8. Confirm invite/referral/promo/gift abuse controls before public enablement.
9. Confirm PII/log redaction.
10. Confirm admin domain protection.
11. Confirm support privacy boundaries.
12. Confirm no raw subscription URLs or VPN credentials are exposed in logs.
13. Confirm referral/promo/gift/autoprolongation kill switches and audit trails.

**Evidence:**

```text
docs/evidence/releases/s2-stage-13-security-abuse-privacy-YYYYMMDD.md
```

**Exit Criteria:**

- no known high/critical security issue blocks S2;
- public abuse paths have controls;
- privacy-sensitive data is not leaking through logs, analytics, support views, or evidence.

---

## S2-STAGE-14: GitLab CI/CD And Release Speed

**Purpose:** Make GitLab the first operational path and reduce release time.

**Work:**

1. Confirm GitLab `main` is first source for CI/CD.
2. Keep GitHub as mirror/fallback.
3. Confirm GitLab Runner health.
4. Confirm CI jobs for:
   - backend tests;
   - frontend tests/lint;
   - bot tests;
   - security scan;
   - dependency audit;
   - Docker build;
   - deploy dry-run;
   - release evidence generation.
5. Confirm manual deploy jobs for staging and production.
6. Confirm deploy jobs use immutable SHA/tag.
7. Confirm production deploy does not depend only on home GitLab being online.
8. Confirm emergency hotfix path.

**Evidence:**

```text
docs/evidence/releases/s2-stage-14-gitlab-cicd-release-speed-YYYYMMDD.md
```

**Exit Criteria:**

- normal fix path is faster than manual rebuild/deploy;
- GitLab is first;
- GitHub remains a fallback;
- release artifacts are reproducible.

---

## S2-STAGE-15: Full Staging/Public-Release Rehearsal

**Purpose:** Rehearse Release 1.0 before opening public traffic.

**Work:**

1. Create `stage2-public-rc.1`.
2. Deploy RC to staging/prod-like environment.
3. Run full user journey:
   - visit website;
   - register/login;
   - Telegram/Mini App auth;
   - select plan;
   - pay or trial;
   - provisioning;
   - subscription URL;
   - VPN client connect;
   - support/admin verification;
   - expiry/renewal/refund simulation.
4. Run observability validation.
5. Run rollback validation.
6. Record known issues.

**Evidence:**

```text
docs/evidence/releases/s2-stage-15-release-rehearsal-YYYYMMDD.md
```

**Exit Criteria:**

- Release 1.0 RC works end-to-end;
- rollback is available;
- unresolved issues are classified before canary.

---

## S2-STAGE-16: Production Canary Release

**Purpose:** Open public-release behavior to a small controlled real cohort before full public opening.

**Work:**

1. Deploy immutable RC to production.
2. Enable limited public registration or controlled expanded cohort.
3. Watch:
   - registration success;
   - payment success;
   - provisioning success;
   - config delivery;
   - VPN connection proof;
   - support issues;
   - Sentry errors;
   - logs;
   - alerts;
   - database/Redis health;
   - VPN node load.
4. Keep kill switches ready for:
   - registration;
   - payments;
   - trial;
   - provisioning;
   - plan visibility.

**Evidence:**

```text
docs/evidence/releases/s2-stage-16-production-canary-YYYYMMDD.md
```

**Exit Criteria:**

- canary users can buy/trial/connect;
- no unresolved paid-but-no-access older than 24h;
- no P0/P1 issue remains open.

---

## S2-STAGE-17: Public Release 1.0 Go/No-Go

**Purpose:** Make the formal owner decision to open CyberVPN for public B2C sale.

**Go Criteria:**

- S2-STAGE-00 through S2-STAGE-16 complete or explicitly accepted;
- at least one payment path is live and monitored;
- subscription URL delivery works;
- VLESS/XHTTP behavior is proven;
- support can operate;
- legal pack is public;
- observability is active;
- backup/restore/rollback evidence exists;
- no high/critical security blocker remains open;
- owner accepts residual risks.

**No-Go Criteria:**

- payment/provider uncertainty;
- paid-but-no-access unresolved backlog;
- provisioning failure rate above accepted threshold;
- missing legal/public refund contact;
- admin/security exposure;
- no rollback;
- no alert delivery;
- no owner/support availability.

**Evidence:**

```text
docs/evidence/releases/s2-stage-17-go-no-go-YYYYMMDD.md
```

**Exit Criteria:**

- CyberVPN is either opened for public B2C release or paused with exact blockers.

---

## S2-STAGE-18: Post-Launch Stabilization And S3 Readiness

**Purpose:** Operate S2 after launch and decide whether to keep stabilizing or prepare S3 Partner/Reseller Platform.

**Daily Checks:**

1. Sentry critical errors.
2. Alertmanager firing alerts.
3. Payment reconciliation.
4. Refund/chargeback queue.
5. Paid-but-no-access/orphan payments.
6. Provisioning failures.
7. Support tickets and SLA.
8. VPN node health.
9. Database/Redis health.
10. Backups.
11. Public endpoint probes.
12. Telegram Bot/Mini App health.
13. Home observability server health.
14. Loki sensitive-payload checks.
15. S2 success metrics.
16. Known issues.

**Evidence:**

```text
docs/evidence/releases/s2-stage-18-stabilization-YYYYMMDD.md
```

**Exit Criteria:**

- S2 is stable enough to remain public;
- or S2 is paused with clear blockers;
- or owner approves planning for S3.

---

## 6. Recommended Execution Order

Execute strictly in this order:

1. `S2-STAGE-00`
2. `S2-STAGE-01`
3. `S2-STAGE-02`
4. `S2-STAGE-03`
5. `S2-STAGE-04`
6. `S2-STAGE-05`
7. `S2-STAGE-06`
8. `S2-STAGE-07`
9. `S2-STAGE-08`
10. `S2-STAGE-09`
11. `S2-STAGE-10`
12. `S2-STAGE-11`
13. `S2-STAGE-12`
14. `S2-STAGE-13`
15. `S2-STAGE-14`
16. `S2-STAGE-15`
17. `S2-STAGE-16`
18. `S2-STAGE-17`
19. `S2-STAGE-18`

If a later stage exposes a blocker, return to the relevant earlier stage by reference, but do not create a new top-level stage number.

---

## 7. First Practical Move After Approval

Start with:

```text
S2-STAGE-00: S1 Stabilization Freeze And Entry Decision
```

Immediate outputs:

1. current S1 production state summary;
2. known issues list;
3. current commit/tag baseline;
4. accepted/deferred risk table;
5. owner decision: proceed to S2-STAGE-01 or keep stabilizing S1.

After that, run:

```text
S2-STAGE-01: Local Fast-Fix And Test Baseline
```

This should reduce the time spent on small production fixes before we touch larger S2 work.
