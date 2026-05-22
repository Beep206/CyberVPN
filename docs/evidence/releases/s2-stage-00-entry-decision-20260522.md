# S2-STAGE-00 Entry Decision Evidence

**Date:** 2026-05-22
**Stage:** `S2-STAGE-00: S1 Stabilization Freeze And Entry Decision`
**Decision Type:** S1 baseline review before Stage 2 Public Release 1.0 work
**Result:** `GO to S2-STAGE-01`, with listed S2 blockers tracked inside fixed S2 stages

---

## 1. Decision Summary

CyberVPN can move from S1 stabilization into **S2-STAGE-01: Local Fast-Fix And Test Baseline**.

This is **not** approval to open full public sales immediately. It means the current S1 production baseline is stable enough to become the engineering base for S2 Public Release 1.0 work.

The public-release decision remains gated by `S2-STAGE-17: Public Release 1.0 Go/No-Go`.

---

## 2. Frozen Baseline

| Item | Value |
|---|---|
| Local branch | `main` |
| GitLab remote | `origin/main` |
| GitHub remote | `github/main` |
| Baseline commit | `4b1d442239ee` |
| Latest commit | `Document Stage 2 public release plan` |
| Previous runtime fix commit | `bbfa5a2c` / `Fix Stage 1 subscription URL delivery` |
| Working tree at review start | Clean |
| S2 master plan | `docs/plans/2026-05-22-cybervpn-stage2-public-release-master-plan.md` |

Command evidence:

```text
git status --short --branch
## main...origin/main

git log --oneline -5 --decorate
4b1d4422 (HEAD -> main, origin/main, github/main) Document Stage 2 public release plan
bbfa5a2c Fix Stage 1 subscription URL delivery
8ea5bb71 Remove Russian display-only price copy
48ee7bd7 Remove Mini App local price estimate copy
892e8226 Wait for Stage 1 deploy smoke readiness
```

---

## 3. Current Production Runtime Snapshot

| Area | Observed Result | Decision Impact |
|---|---|---|
| Public Mini App Home | `https://cyber-vpn.net/ru-RU/miniapp/home` returned `200` | Healthy for S2 entry |
| Public Mini App Plans | `https://cyber-vpn.net/ru-RU/miniapp/plans` returned `200` | Healthy for S2 entry |
| API health | `https://api.cyber-vpn.net/health` returned `200` | Healthy for S2 entry |
| API docs | `https://api.cyber-vpn.net/docs` returned `404` | Good: docs are not publicly exposed |
| HTTP/3/QUIC signal | response included `alt-svc: h3=":443"` | Required rule preserved |
| Prod app image tag | `stage1-direct-suburl-refresh-20260522T091303Z` | Matches last direct production fix |
| Prod app containers | backend, frontend, bot, worker, scheduler, DB, Valkey, Remnawave all reported healthy/running | Healthy for S2 entry |
| Recent app logs | backend/frontend/bot scan found no traceback/critical/uncaught/fatal/exception matches in checked window | No immediate blocker |
| VPN node | `de-1.cyber-vpn.org`, `cybervpn-remnawave-node` only application container | Node-only rule preserved |
| VPN node recent logs | no panic/fatal/critical/error/exception matches in checked window | No immediate blocker |

Public smoke commands:

```text
curl https://cyber-vpn.net/ru-RU/miniapp/home
home status=200 time=0.867477 ip=104.21.85.196

curl https://cyber-vpn.net/ru-RU/miniapp/plans
plans status=200 time=1.484443 ip=172.67.209.233

curl https://api.cyber-vpn.net/health
status=200 time=0.712210
```

Header evidence:

```text
HTTP/2 200
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload
via: 1.1 Caddy
```

---

## 4. Home Operations Snapshot

Home services remain **non-critical** for customer runtime. They provide GitLab, CI, observability, evidence, and operational tooling.

| Area | Observed Result | Decision Impact |
|---|---|---|
| Grafana edge health | `200` | Available |
| Alertmanager edge health | `200` | Available |
| Sentry health | `200` | Available |
| Home disk `/` | 10% used | Healthy |
| Home disk `/srv/storage` | 1% used | Healthy |
| Home RAM | 46 GiB total, 28 GiB available | Healthy |
| Home swap | 911 MiB used from 31 GiB | Watch item only |
| Home local Stage 1 admin container | old local admin container reported unhealthy | Non-customer-runtime watch item |

The home `admin` container health warning does not block S2 entry because customer-facing runtime is on rented production infrastructure. It should be reviewed under `S2-STAGE-11` or `S2-STAGE-14` if it affects observability/CI/admin rehearsal.

---

## 5. S1 Evidence Reviewed

Recent S1 evidence present in the repository:

```text
stage1-rented-prod-15h-subscription-url-refresh-20260522T091303Z.md
stage1-rented-prod-15g-xhttp-ru-bundle-20260522T083900Z.md
stage1-rented-prod-15f-home-invite-ruplans-suborg-20260522T073900Z.md
stage1-rented-prod-12-catalog-support-beta-gate-20260520T180458Z.md
stage1-rented-prod-13-first-controlled-cohort-trial-watch-20260520T184156Z.md
stage1-rented-prod-14c-miniapp-session-restore-20260521T065247Z.md
stage1-rented-prod-15e-account-delete-reset-20260521T151949Z.md
stage1-rented-prod-15d-invite-config-delivery-20260521T143200Z.md
stage1-rented-prod-15c-miniapp-allowlist-closure-20260521T133832Z.md
stage1-rented-prod-15b-telegram-bot-allowlist-20260521T130216Z.md
stage1-rented-prod-15a-my-invites-miniapp-bot-20260521T123754Z.md
```

Important S1 facts from recent work:

- owner device VPN proof succeeded through `77.90.13.29`;
- Mini App/Bot invite flow was exercised;
- account deletion was fixed and verified by owner;
- raw `vless://` delivery was replaced with subscription URL preference for primary Bot/Mini App config delivery;
- `.org` is used for subscription/node surface;
- XHTTP/RU bundle support was added and deployed;
- HTTP/3/QUIC is active and must stay active.

---

## 6. Must Fix Before Full S2 Public Opening

These are not blockers for entering `S2-STAGE-01`, but they are blockers or gates before `S2-STAGE-17`.

| Item | Stage Owner | Reason |
|---|---|---|
| Owner real-device recheck after latest subscription URL/XHTTP refresh | `S2-STAGE-08` | Latest production fix was smoke-tested internally, but human client validation should confirm UX and client behavior |
| Final S2 public plan catalog | `S2-STAGE-04` | S2 cannot open publicly with beta/hidden/special pricing ambiguity |
| Public registration/rate-limit policy | `S2-STAGE-05` | Wider public access needs abuse control |
| Payment production hardening | `S2-STAGE-06` | Public sale requires reliable success/failure/duplicate/orphan/reconciliation evidence |
| Subscription lifecycle copy and states | `S2-STAGE-07` | Users need clear active/expired/renewal/refund states |
| Support/admin operational proof | `S2-STAGE-09` | Public users need support path without developer-only intervention |
| Legal/trust copy final public pass | `S2-STAGE-10` | Public claims must match actual service behavior |
| S2 dashboards/alerts | `S2-STAGE-11` | Owner visibility is required before wider public sale |
| Restore/rollback drill freshness | `S2-STAGE-12` | Public release must have proven recovery path |
| Security/abuse/privacy gate | `S2-STAGE-13` | Public traffic changes the risk profile |
| GitLab CI/CD release-speed hardening | `S2-STAGE-14` | Fix cycle must be faster and less manual for S2 |

---

## 7. Accepted For S2 Entry Only

These are accepted only for starting S2 work, not necessarily for full public opening.

| Risk | Acceptance |
|---|---|
| Single current production app server | Accept for S2 entry; evaluate load balancer/second app server under S2 infra hardening if traffic requires it |
| Single current production VPN node | Accept for S2 entry; evaluate second node under `S2-STAGE-08` |
| Home observability server can be unavailable without breaking customers | Accept; customer runtime must remain on rented infrastructure |
| GitLab is home-hosted | Accept; GitHub remains fallback/mirror and production must not depend only on home GitLab |
| Manual hotfix path still exists | Accept for S2 entry; reduce through `S2-STAGE-14` |
| Same owner still carries many operational roles | Accept for S2 entry; split backup/support before wider S2 public opening if possible |

---

## 8. Deferred To Later Stages

| Deferred Item | Target Stage |
|---|---|
| Partner payouts | S3 |
| Full partner/reseller portal production launch | S3 |
| Mobile store release | S4 |
| Desktop/Android TV/device expansion | S5 |
| Helix/Verta/Beep mass rollout | S6 |
| Kubernetes/Talos/GitOps as a platform migration | S7 |
| Enterprise hardening | S7 |

---

## 9. Entry Decision

`S2-STAGE-00` is complete.

Recommended decision:

```text
GO: proceed to S2-STAGE-01: Local Fast-Fix And Test Baseline.
```

Rationale:

- current production user-facing smoke is healthy;
- API health is alive;
- HTTP/3/QUIC remains enabled;
- prod-app containers are healthy;
- VPN node remains node-only;
- current GitLab/GitHub baseline is pushed and clean;
- no immediate P0/P1 customer-impacting issue was observed during this gate;
- remaining work fits the fixed S2 stage plan and does not require changing stage numbers.

---

## 10. Security Review Notes

Security review was limited to this gate's scope: documentation/evidence creation and release-readiness classification. No runtime code was changed in this stage.

| Check | Result |
|---|---|
| `git diff --check` | PASS |
| Targeted secret scan on this evidence file | PASS: no matches |
| Targeted dangerous-pattern scan on this evidence file | PASS: no matches |
| Full repository secret scan | PASS: no leaks found |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate advisories remain |

Moderate dependency watch items observed:

- `brace-expansion` moderate advisory through transitive dependencies;
- `postcss` moderate advisory through the bundled Next dependency.

These are not S2-STAGE-00 blockers because this stage did not change runtime dependencies and the audit command returned exit code `0` at high severity threshold. Track dependency cleanup under `S2-STAGE-13` and `S2-STAGE-14`.

---

## 11. Next Stage

Next required stage:

```text
S2-STAGE-01: Local Fast-Fix And Test Baseline
```

Primary goal of the next stage:

- make local validation fast and reliable;
- document exact local check commands;
- reduce reliance on public production deploys for every small Mini App/Bot/UI correction.
