> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-03
> Повторный freeze/scope pass: 2026-05-09
> Backlog ID: `S1-REL-002`
> Статус: completed for the 2026-05-09 repeat snapshot. Must be re-run again before first `stage1-beta-rc.N` tag if the worktree changes.

# S1-REL-002 Dirty Worktree Inventory and Launch Scope Map

## Purpose

Этот документ закрывает текущий проход `S1-REL-002`: audit dirty worktree and separate launch-critical vs experimental. Он фиксирует, какие текущие изменения можно считать S1 documentation/supporting scope, какие влияют на runtime/build, какие нужно валидировать перед release candidate, и какие компоненты должны оставаться excluded/default-off.

## 2026-05-09 Repeat RC/Freeze Gate

Этот повторный проход выполнен после серии S1 implementation/evidence задач. Его цель - не утверждать RC, а зафиксировать текущий blast radius перед следующим freeze/security pass.

### Repository Snapshot

| Item | Value |
|---|---|
| Current branch | `main` |
| Current HEAD short SHA | `b31728dc` |
| Current HEAD full SHA | `b31728dc2921b5739fc5bb606166cec0d1e843ae` |
| `git status --short` entries | `965` |
| Tracked modified entries | `612` |
| Untracked actual files | `353` |
| Tracked diff size | `612 files`, `44305 insertions`, `14029 deletions` |
| Docker | `Docker version 29.4.0`, `Docker Compose version v5.1.2` |
| Running Docker containers | none shown by `docker ps` |

### Dirty Worktree Summary

`git status --short` status code summary:

```text
612 M
353 ??
```

Top-level status summary:

| Top-level path | Entries | Scope reading |
|---|---:|---|
| `frontend/` | 607 | Launch-critical customer web/Mini App UI plus generated locale artifacts |
| `backend/` | 229 | Launch-critical API, DB, auth, payments, VPN provisioning and tests |
| `services/` | 50 | Launch-critical Telegram Bot and task-worker changes |
| `infra/` | 33 | S1 observability, topology, DNS/TLS, ingress, payments and backup/supporting infra contracts |
| `scripts/` | 17 | S1 validators, evidence/security tooling and support scripts |
| `admin/` | 17 | Launch-critical admin/support surface, gated by admin domain/RBAC/2FA evidence |
| `docs/` | 9 in porcelain; `163` actual untracked docs files via `git ls-files --others` | S1 documentation/evidence pack and supporting docs |
| `.gitignore`, `.gitleaks.s1.current-tree.baseline.json`, `package-lock.json` | 3 | Release/security/build supporting files |

Second-level hotspot summary:

| Path group | Entries | Scope classification |
|---|---:|---|
| `frontend/messages` | 446 | Runtime-visible locale copy; must be deterministic and included only after i18n/placeholder scan |
| `frontend/src` | 150 | Launch-critical customer UI/API client/Mini App/frontend observability |
| `backend/src` | 92 | Launch-critical backend runtime |
| `backend/tests` | 79 | Supporting tests/evidence; not runtime, but required for RC proof |
| `backend/alembic` | 51 | Launch-critical DB migration surface; partner/growth/non-S1 tables must remain inert/default-off |
| `services/task-worker` | 26 | Launch-critical worker/scheduler runtime |
| `services/telegram-bot` | 24 | Launch-critical Telegram Bot runtime |
| `admin/src` | 13 | Launch-critical admin runtime, protected ingress only |
| `infra/ansible`, `infra/tests`, `infra/prometheus`, `infra/alertmanager` | 24 | Supporting infra/observability/evidence contracts |
| `docs/cybervpn_stage1_launch_docs` | untracked folder | Supporting docs/evidence, must be included in docs freeze |

### Explicit Exclusion Scan

Command:

```bash
git status --short | rg -n "(^.. (partner|cybervpn_mobile|apps/desktop|apps/android|services/helix|packages/(helix|verta|beep)|platform-gitops|infra/talos|infra/k8s)|^.. .*extension)"
```

Observed result:

```text
no matches
```

Interpretation:

- No dirty top-level partner, mobile, desktop, Android TV, browser extension, Helix/Verta/Beep or full platform GitOps runtime directories are currently visible in the dirty worktree.
- This does not automatically approve all backend DB/API changes for S1. Several backend migrations and existing modules reference partner/growth/phase scaffolding, so those must be proven inert/default-off before any RC tag.

### Launch Scope Classification

| Path group | Category | S1 runtime included? | Required action before RC |
|---|---|---:|---|
| `backend/src`, `backend/.env.example`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock` | `launch-critical` | Yes | Re-run backend focused tests, dependency audit, settings/secrets guardrails and route/payment/VPN evidence checks |
| `backend/alembic` | `launch-critical-db` with mixed S1 and non-S1 scaffolding | Yes, if migrations run | Re-run clean DB migration gate and classify partner/growth/non-S1 tables as inert/default-off or exclude before RC |
| `backend/tests`, `backend/docs/api/openapi.json` | `supporting-qa-contract` | No runtime, but release evidence | Keep with RC evidence; regenerate OpenAPI only from approved runtime |
| `frontend/src`, `frontend/package*.json`, `frontend/next.config.ts`, `frontend/tsconfig.json`, `frontend/sentry.*.config.ts` | `launch-critical` | Yes | Re-run build, lint/tests, bundle/env scan and deployed screenshot plan |
| `frontend/messages`, `frontend/src/i18n/messages/generated` | `runtime-copy-generated` | Yes | Re-run i18n critical path/placeholder scan; ensure generated locale artifacts are deterministic |
| `admin/src`, `admin/messages`, `admin/next.config.ts`, `admin/vitest.config.ts` | `launch-critical-admin` | Yes, protected only | Re-run admin build/tests and confirm admin remains behind protected ingress/RBAC/2FA |
| `services/telegram-bot` | `launch-critical-bot` | Yes, after real bot token/webhook evidence | Re-run bot tests/audit; keep real BotFather/token evidence external before beta |
| `services/task-worker` | `launch-critical-worker` | Yes | Re-run worker tests/audit and durable job/retry evidence |
| `infra/docker-compose.yml`, `infra/prometheus`, `infra/alertmanager`, `infra/grafana`, `infra/topology`, `infra/dns`, `infra/ingress`, `infra/edge`, `infra/payments`, `infra/ansible`, `infra/tests` | `supporting-infra` / conditional production contract | Yes only when deployed by approved tag/config | Re-run validators; production/staging proof remains external |
| `scripts/validate-*`, `scripts/run-*`, `scripts/security/*`, `scripts/testing/*` | `supporting-validation` | No direct runtime | Keep as evidence tooling; run syntax/static scans |
| `docs/cybervpn_stage1_launch_docs` | `supporting-docs` | No runtime | Include in docs freeze; keep next-step and evidence pack consistent |
| `.gitleaks.s1.current-tree.baseline.json` | `security-baseline` | No runtime | Must be reviewed/updated only with explicit accepted findings |
| `.gitignore`, `package-lock.json` | `supporting-release-build` | Conditional | Review before RC; no unrelated package churn |

### RC Blockers Found By This Pass

| Blocker | Why it matters | Recommended next action |
|---|---|---|
| Dirty worktree is broad | 965 entries is too much to tag or deploy without a reviewed inclusion map | Treat this document as inventory only; do not create `stage1-beta-rc.N` yet |
| Current-tree Gitleaks gate reported 52 findings against the older baseline | Even if many are test/doc false positives, RC cannot rely on undocumented assumptions | Closed locally by `S1-INFRA-007` revalidation in `27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md`; repeat before RC after any more broad worktree changes |
| Backend migrations include non-S1 partner/growth/phase scaffolding | S1 excludes partner/payout/growth runtime; DB migration blast radius must be explicit | Re-run clean migration and stage1 table/default-off review before RC |
| Frontend locale/generated files dominate the dirty set | Generated i18n artifacts can hide stale copy, placeholders or unsupported claims | Re-run `S1-FE-009`/`S1-FE-010` style scans against final RC artifact |
| Docs/evidence pack is still untracked | Freeze requires documentation to become explicit source, not loose local files | Stage/commit docs only after security/scope review |

### Validation and Security Review

| Command | Result |
|---|---|
| `git status --short \| wc -l` | PASS: `965` entries captured |
| `git diff --numstat` summary | PASS: `612 files`, `44305 insertions`, `14029 deletions` |
| Top-level exclusion scan for partner/mobile/desktop/TV/Helix/GitOps dirty paths | PASS: no matches |
| `npm audit --audit-level=high` | PASS for high/critical threshold; known moderate Next/PostCSS advisory remains tracked and is not force-fixed because npm proposes a breaking downgrade |
| `uv export` + `uvx pip-audit --timeout 60` in `backend/` | PASS: no known vulnerabilities found |
| `uv export` + `uvx pip-audit --timeout 60` in `services/telegram-bot/` | PASS: no known vulnerabilities found |
| `uv export` + `uvx pip-audit --timeout 60` in `services/task-worker/` | PASS: no known vulnerabilities found |
| Targeted secret-pattern scan over touched `S1-REL-002` docs | PASS: no matches |
| Targeted dangerous-pattern scan over touched `S1-REL-002` docs | PASS: no matches |
| `scripts/security/scan-secrets.sh` | PASS after `S1-INFRA-007` revalidation: accepted baseline is redacted and the baseline-enforced current-tree scan returns `no leaks found` |
| `git diff --check` over touched docs | PASS |
| `docker ps --format ...` | PASS: no running containers shown |

Gitleaks finding summary from `.tmp/stage1-secrets/gitleaks-s1-current-tree-redacted.json`:

| Group | Count |
|---|---:|
| `generic-api-key` | 52 |
| `frontend` | 41 |
| `docs` | 6 |
| `backend` | 2 |
| `services` | 2 |
| `admin` | 1 |

### 2026-05-09 Result

`S1-REL-002` repeat gate is complete for inventory and scope classification.

This does not authorize a release candidate yet. The current worktree is still too broad for an immutable RC tag until the immediate security/scope follow-up is complete.

Current next ID: `S1-INFRA-007` - repeat secrets scan/current-tree baseline review for the updated S1 worktree.

## 2026-05-09 Batch Revalidation

`S1-REL-002` was re-run as item 2 in the owner-requested batch:

1. `S1-BE-003`
2. `S1-REL-002`
3. `S1-INFRA-002`
4. `S1-INFRA-004`
5. `S1-BE-001`

Current repository snapshot:

| Item | Value |
|---|---|
| Current branch | `main` |
| Current HEAD short SHA | `b31728dc` |
| Current HEAD full SHA | `b31728dc2921b5739fc5bb606166cec0d1e843ae` |
| `git status --short` entries | `965` |
| Tracked modified entries | `612` |
| Untracked entries | `353` |
| Tracked diff size | `612 files`, `44316 insertions`, `14040 deletions` |
| Running Docker containers | none shown by `docker ps` after the batch DB container was removed |

Top-level status summary:

| Top-level path | Entries |
|---|---:|
| `frontend/` | 607 |
| `backend/` | 229 |
| `services/` | 50 |
| `infra/` | 33 |
| `scripts/` | 17 |
| `admin/` | 17 |
| `docs/` | 9 |
| `package-lock.json` | 1 |
| `.gitleaks.s1.current-tree.baseline.json` | 1 |
| `.gitignore` | 1 |

Explicit exclusion scan:

```text
git status --short | rg -n "(^.. (partner|cybervpn_mobile|apps/desktop|apps/android|services/helix|packages/(helix|verta|beep)|platform-gitops|infra/talos|infra/k8s)|^.. .*extension)"
Result: no matches
```

Interpretation:

- This pass does not approve an RC tag.
- The worktree is still broad and must be re-run before `stage1-beta-rc.N`.
- No dirty top-level partner/mobile/desktop/Android TV/browser extension/Helix/Verta/Beep/full GitOps runtime path was detected by the exclusion scan.
- The next execution item after this five-task batch is `S1-BE-002`.

## Commands Executed

```bash
git status --short
git diff --name-status
git diff --stat
git diff --numstat
git ls-files --others --exclude-standard
docker --version
docker compose version
```

## Current Git Inventory

### Tracked modified files

```text
 M docs/2026-04-25-cybervpn-launch-questionnaire-answers.md
 M frontend/next.config.ts
 M frontend/package.json
 M frontend/scripts/dev-server.mjs
 M frontend/scripts/seo-static-audit.mjs
```

### Untracked files

```text
?? docs/cybervpn_stage1_launch_docs/
```

The untracked Stage 1 launch docs folder contains:

```text
00_INDEX.md
01_LAUNCH_ROADMAP.md
02_STAGE1_CHARTER.md
03_STAGE1_PRD_USER_FLOWS.md
04_STAGE1_TECHNICAL_SPEC.md
05_STAGE1_DOCUMENT_REVIEW_PROTOCOL.md
06_STAGE1_IMPLEMENTATION_BACKLOG.md
07_STAGE1_ACCEPTANCE_GATES.md
08_STAGE1_GO_LIVE_RUNBOOK.md
09_STAGE1_LEGAL_SUPPORT_OPERATIONS.md
10_STAGE1_RISK_REGISTER.md
11_STAGE1_REVIEW_CHECKLIST.md
12_STAGE1_DECISION_LOG_TEMPLATE.md
13_STAGE1_DOCUMENT_AUDIT_AND_APPROVAL_RECOMMENDATION.md
14_STAGE1_BLOCKER_RESOLUTION_PLAN.md
15_STAGE1_OWNER_DECISION_PACKET.md
16_STAGE1_IMPLEMENTATION_ENTRY_CRITERIA.md
17_STAGE1_APPROVED_DECISION_LOG.md
18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md
19_STAGE1_TECH_DEBT_REGISTER.md
20_HOME_LAB_NON_CRITICAL_OPTION.md
21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md
22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md
CYBERVPN_STAGE1_LAUNCH_PACK_COMBINED.md
```

## Diff Size

```text
docs/2026-04-25-cybervpn-launch-questionnaire-answers.md  200 insertions / 1549 deletions
frontend/next.config.ts                                      2 insertions / 0 deletions
frontend/package.json                                        1 insertion / 1 deletion
frontend/scripts/dev-server.mjs                              1 insertion / 1 deletion
frontend/scripts/seo-static-audit.mjs                        1 insertion / 1 deletion
```

## Docker Readiness Snapshot

Docker is available for the next local work package:

```text
Docker version 29.4.0, build 9d7ad9f
Docker Compose version v5.1.2
```

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-REL-002` as item `29` in the owner-requested ordered batch.

| Item | Value |
|---|---|
| Current branch | `main` |
| Current HEAD short SHA | `b31728dc` |
| Current HEAD full SHA | `b31728dc2921b5739fc5bb606166cec0d1e843ae` |
| `git status --short` entries | `965` |
| Tracked modified entries | `612` |
| Untracked porcelain entries | `353` |
| Untracked actual files | `534` |
| Tracked diff size | `612 files`, `44318 insertions`, `14040 deletions` |
| Docker | `Docker version 29.4.0`, `Docker Compose version v5.1.2` |
| Running Docker containers | `0` |

Top-level status summary:

| Top-level path | Entries |
|---|---:|
| `frontend/` | 607 |
| `backend/` | 229 |
| `services/` | 50 |
| `infra/` | 33 |
| `scripts/` | 17 |
| `admin/` | 17 |
| `docs/` | 9 |
| `package-lock.json` | 1 |
| `.gitleaks.s1.current-tree.baseline.json` | 1 |
| `.gitignore` | 1 |

Explicit exclusion scan:

```text
git status --short | rg -n "(^.. (partner|cybervpn_mobile|apps/desktop|apps/android|services/helix|packages/(helix|verta|beep)|platform-gitops|infra/talos|infra/k8s)|^.. .*extension)"
Result: excluded_runtime_dirty_paths=none
```

Interpretation: this pass still does not approve an RC tag. The worktree remains broad, but the explicit excluded-runtime scan did not detect dirty partner/mobile/desktop/Android TV/browser extension/Helix/Verta/Beep/full GitOps runtime paths.

Current next ID: `S1-VPN-005` - paid provisioning.

This only confirms local tooling availability. It does not close Remnawave staging/prod evidence.

## File-Level Scope Classification

| Path | Git state | Category | Runtime included in S1? | Backlog / evidence link | Required action |
|---|---|---|---|---|---|
| `docs/cybervpn_stage1_launch_docs/` | Untracked | `supporting-docs` / S1 governance | No runtime effect | `S1-REL-003`, `S1-REL-007`, docs freeze | Include in S1 docs pack after owner review |
| `docs/2026-04-25-cybervpn-launch-questionnaire-answers.md` | Modified | `supporting-docs` / owner questionnaire source | No runtime effect | `S1-REL-003`, decision provenance | Treat as source/reference, not active S1 authority |
| `frontend/next.config.ts` | Modified | `launch-critical` frontend config | Yes, if frontend is deployed | `S1-FE-010`, `S1-BE-005`, `S1-INFRA-004` | Validate before RC; confirm old `vpn.ozoxy.ru` origin is removed/replaced for S1 domains when frontend config is finalized |
| `frontend/package.json` | Modified | `launch-critical` build config | Yes, if frontend is deployed | `S1-FE-001`, `S1-FE-010`, `S1-QA-001` | Build must pass with selected build mode before RC |
| `frontend/scripts/dev-server.mjs` | Modified | `supporting-dev` | No production runtime | `S1-QA-001` local dev support | Keep only if dev server behavior is intentional |
| `frontend/scripts/seo-static-audit.mjs` | Modified | `supporting-qa` | No production runtime | `S1-FE-010`, `S1-QA-002` | Validate SEO/static audit still runs with selected build mode |

## Launch-Critical Runtime Candidates

These paths are part of S1 runtime only when their linked workstream is active and evidence exists:

| Path/module | S1 category | Runtime included? | Required backlog IDs |
|---|---|---:|---|
| `backend/` | `launch-critical` | Yes, after S1 backend scope starts | `S1-BE-*`, `S1-AUTH-*`, `S1-PAY-*`, `S1-VPN-*` |
| `frontend/` | `launch-critical` | Yes, after frontend scope starts | `S1-FE-*`, `S1-QA-*` |
| `admin/` | `launch-critical` | Yes, after admin protection is proven | `S1-ADM-*`, `S1-AUTH-004` |
| `services/telegram-bot/` | `launch-critical` | Yes, after bot/token/webhook evidence | `S1-TG-*`, `S1-SUP-*` |
| `services/task-worker/` | `launch-critical` | Yes, after queue/job evidence | `S1-PAY-*`, `S1-PROD-*`, `S1-VPN-*` |
| `infra/docker-compose.yml` | `supporting-dev` / local lab | No production authority by itself | `S1-INFRA-009`, `S1-VPN-012` |
| `docs/cybervpn_stage1_launch_docs/` | `supporting-docs` | No runtime | `S1-REL-*` |

## Explicitly Excluded or Default-Off for S1

| Path/module | Category | S1 runtime status | Reason |
|---|---|---|---|
| `partner/` | `experimental` / Stage 3 | Excluded/default-off | Partner portal and payouts are S3 |
| `cybervpn_mobile/` | `experimental` / Stage 4 | Excluded/default-off | Mobile store release is S4 |
| `services/helix-*` | `experimental` / Stage 6 | Excluded/default-off | Helix/Verta/Beep production is S6 |
| `platform-gitops/` | target-state platform | Excluded unless explicitly used | Full GitOps/Talos/Kubernetes maturity is S7 |
| Browser extension placeholders, if present | `experimental` | Excluded/default-off | Not S1 |
| Public referral/promo/gift surfaces | `disabled-runtime` | Hidden/default-off | `REFERRAL_ENABLED=false` for S1 |
| Autoprolongation | `disabled-runtime` | Not promised | Manual renewal only in S1 |

## Generated / Local Artifacts

No untracked generated runtime artifacts were shown by `git ls-files --others --exclude-standard` outside `docs/cybervpn_stage1_launch_docs/` in this snapshot.

Known local/generated directories visible in the repository root, such as `node_modules/`, `.next/`, `.coverage`, `htmlcov/`, `.ruff_cache/` and similar, must not be included in S1 release source unless already tracked intentionally.

## Secrets-Sensitive Scope

The current dirty inventory does not show modified `.env` files or direct secret files.

Before first RC:

- run `S1-INFRA-007` secrets scan;
- record secrets inventory without values;
- confirm no provider credentials, Telegram tokens, OAuth secrets, Remnawave tokens, JWT/TOTP secrets or raw config URLs are committed;
- confirm frontend public env/bundle scan under `S1-FE-010`.

## Findings

1. No current dirty file directly enables partner/native/Helix/browser extension production runtime.
2. The S1 launch docs are currently untracked; they are supporting docs and should be included in the docs freeze once reviewed.
3. The large questionnaire file diff is documentation/source material, not active S1 authority. The active authority is the Stage 1 launch docs set.
4. Frontend build/config changes are runtime/build-impacting and must be validated before RC:
   - `frontend/package.json` changes `next build --webpack` to `next build --turbopack`;
   - `frontend/scripts/dev-server.mjs` starts dev with `--turbopack`;
   - `frontend/scripts/seo-static-audit.mjs` builds with `--turbopack`;
   - `frontend/next.config.ts` disables Turbopack dev filesystem cache and still needs S1 domain/origin review.
5. Docker is now available locally, so the next Docker/Remnawave local package is unblocked.

## 2026-05-03 S1-REL-002 Result

`S1-REL-002` was complete for the 2026-05-03 snapshot with the following constraints:

- this scope map must be re-run before the first `stage1-beta-rc.N` tag;
- frontend build/config changes are not rejected, but are conditional launch-critical changes that require validation;
- no production/staging evidence is implied by this local worktree audit;
- no experimental runtime should be included in S1 unless a future decision log explicitly changes scope.

## Current Next Work Item

At the time the original 2026-05-03 evidence was created, the next ID was `S1-INFRA-009` - verify local Docker/Compose stack.

`S1-INFRA-009` is now completed in `23_STAGE1_INFRA_009_LOCAL_DOCKER_COMPOSE_EVIDENCE.md`.

The 2026-05-09 repeat gate supersedes the old next step.

Current next ID: `S1-INFRA-007` - repeat secrets scan/current-tree baseline review for the updated S1 worktree.
