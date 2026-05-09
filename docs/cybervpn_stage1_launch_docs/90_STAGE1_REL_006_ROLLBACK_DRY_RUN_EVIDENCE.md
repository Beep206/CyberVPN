> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-05
> Backlog ID: `S1-REL-006`
> Статус: PASS for local/no-cost rollback dry-run. Repeat on staging/production release candidates before go-live.

# S1-REL-006 Rollback Dry-Run Evidence

## Purpose

`S1-REL-006` proves that Stage 1 rollback is not only a written idea. The local drill validates the rollback mechanics available without paid hosting:

- release-pointer rollback from a bad RC back to previous live release;
- deployability check of the rollback target with Docker Compose config validation;
- application-level runtime rollback controls for Mini App / checkout / config delivery;
- kill-switch-adjacent tests for registration, payment/provisioning failure and orphan payment policy.

This is a local no-cost dry-run. It does not replace staging/prod rollback evidence against real domains, live provider credentials, managed PostgreSQL, production Valkey, production Remnawave or final release artifacts.

## Rollback Scope Covered Locally

| Scope | Local proof | Result |
|---|---|---|
| Release pointer rollback | Temporary `current` symlink pointed from bad RC back to previous live release | PASS |
| Rollback target deployability | `docker compose config --quiet` validated the selected rollback target compose file | PASS |
| Local compose surface | `infra/docker-compose.yml` with `worker`, `bot` and `monitoring` profiles validates | PASS |
| Mini App runtime rollback | Backend/admin tests prove `start_rollback`, `mode=rollback`, audit/timeline and user-facing Mini App gates | PASS |
| Registration/payment/provisioning risk controls | Backend tests cover registration disabled state, payment -> provisioning failure and orphan payment policy | PASS |
| Containers/resources | No long-running containers left after the dry-run | PASS |

## Release Pointer Dry-Run

Command:

```bash
set -euo pipefail
root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT
release_root="$root/control-plane"
live="$release_root/releases/stage1-beta-live.1"
bad="$release_root/releases/stage1-beta-rc.2"
mkdir -p "$live" "$bad"

cat > "$live/docker-compose.yml" <<'YAML'
name: cybervpn-stage1-rollback-drill
services:
  backend:
    image: cybervpn-backend-qa002:latest
    environment:
      REGISTRATION_ENABLED: "true"
      PAYMENTS_ENABLED: "true"
      PROVISIONING_ENABLED: "true"
  worker:
    image: cybervpn-task-worker-qa002:latest
    environment:
      PROVISIONING_ENABLED: "true"
  telegram-bot:
    image: cybervpn-telegram-bot-qa002:latest
    environment:
      MINIAPP_RUNTIME_MODE: "live"
YAML

cat > "$bad/docker-compose.yml" <<'YAML'
name: cybervpn-stage1-rollback-drill
services:
  backend:
    image: cybervpn-backend-qa002:latest
    environment:
      REGISTRATION_ENABLED: "false"
      PAYMENTS_ENABLED: "false"
      PROVISIONING_ENABLED: "false"
  worker:
    image: cybervpn-task-worker-qa002:latest
    environment:
      PROVISIONING_ENABLED: "false"
  telegram-bot:
    image: cybervpn-telegram-bot-qa002:latest
    environment:
      MINIAPP_RUNTIME_MODE: "rollback"
YAML

ln -sfn "$live" "$release_root/previous"
ln -sfn "$bad" "$release_root/current"
started_ns=$(date +%s%N)
rollback_target=$(readlink "$release_root/previous")
ln -sfn "$rollback_target" "$release_root/current"
docker compose -f "$release_root/current/docker-compose.yml" config --quiet
ended_ns=$(date +%s%N)
elapsed_ms=$(( (ended_ns - started_ns) / 1000000 ))
printf 'rollback_target=%s\n' "$rollback_target"
printf 'current_after=%s\n' "$(readlink "$release_root/current")"
printf 'compose_config=valid\n'
printf 'elapsed_ms=%s\n' "$elapsed_ms"
if [ "$(readlink "$release_root/current")" != "$live" ]; then
  printf 'rollback_result=failed\n'
  exit 1
fi
printf 'rollback_result=passed\n'
```

Observed result:

```text
rollback_target=/tmp/tmp.XRAB4Owinj/control-plane/releases/stage1-beta-live.1
current_after=/tmp/tmp.XRAB4Owinj/control-plane/releases/stage1-beta-live.1
compose_config=valid
elapsed_ms=31
rollback_result=passed
```

Interpretation:

- The local release-root model supports the same `current` / `previous` release-pointer behavior used by the existing `control_plane_stack` Ansible role.
- The selected rollback target remains Docker Compose-valid before any containers are started.
- Time-to-switch in the local pointer drill was 31 ms. Real staging/prod time-to-rollback must include image pull/recreate, health checks, DNS/edge propagation where applicable, and verification.

## Existing Control-Plane Role Alignment

The repository already contains a control-plane rollback role:

- `infra/ansible/roles/control_plane_stack/tasks/rollback.yml`
- `infra/ansible/roles/control_plane_stack/tasks/state.yml`
- `infra/ansible/roles/control_plane_stack/tasks/deploy.yml`

The local dry-run mirrors the same high-level model:

1. read current and previous release pointers;
2. resolve rollback target;
3. point `current` to rollback target;
4. apply compose;
5. verify service state.

`ansible-playbook` is not installed in this local workspace, so the Ansible role itself was not executed. This remains a staging/ops evidence requirement before go-live.

## Compose Config Validation

Command:

```bash
cd infra
docker compose --profile worker --profile bot --profile monitoring config --quiet
```

Observed result:

```text
passed with no output
```

Interpretation:

- The current local compose topology for worker/bot/monitoring profiles is syntactically valid.
- This does not prove production ingress, secrets, health checks or service startup.

## Runtime Rollback Control Tests

Backend command:

```bash
cd backend
SKIP_TEST_DB_BOOTSTRAP=1 uv run pytest --no-cov \
  tests/unit/presentation/api/v1/admin/test_system_config.py \
  tests/unit/presentation/api/v1/miniapp/test_routes.py \
  -q
```

Observed result:

```text
27 passed in 0.32s
```

This verifies:

- Mini App runtime can enter `mode=rollback`;
- checkout/trial/config delivery gates respond to rollback/disabled states;
- admin launch action `start_rollback` is represented in summary/timeline;
- audit events are written for runtime/readiness/launch-action changes.

Admin command:

```bash
cd admin
npm run test:run -- \
  src/lib/api/__tests__/governance-miniapp-runtime.test.ts \
  src/features/governance/components/__tests__/policy-console.test.tsx
```

Observed result:

```text
Test Files  2 passed (2)
Tests       13 passed (13)
```

This verifies:

- admin API client handles Mini App runtime/readiness/launch action surfaces;
- policy console exposes rollback-related action state and timeline behavior.

Additional backend safety command:

```bash
cd backend
SKIP_TEST_DB_BOOTSTRAP=1 uv run pytest --no-cov \
  tests/security/test_registration_security.py \
  tests/security/test_stage1_payment_provisioning_failure.py \
  tests/security/test_stage1_orphan_payment_policy.py \
  -q
```

Observed result:

```text
27 passed in 0.35s
```

This verifies:

- registration-disabled behavior is covered;
- payment -> provisioning failure does not silently lose the paid state;
- orphan payment policy and escalation contract remain covered.

## Component Rollback Rules for S1

| Component | S1 rollback action |
|---|---|
| Public frontend | Redeploy previous immutable frontend artifact/tag; if deployment platform is not finalized, public registration/payments must be paused until rollback proof exists |
| Admin frontend | Redeploy previous immutable admin artifact/tag; if admin UI is broken, restrict admin access and use documented backend/support runbook only if safe |
| Backend API | Roll back container image/tag only if DB migrations are compatible; otherwise switch to maintenance/kill switches and keep support/reconciliation paths |
| Worker/scheduler | Roll back worker image/tag or pause risky jobs; PostgreSQL remains durable source of truth |
| Telegram Bot/Mini App | Disable problematic commands/Mini App routes or set runtime mode to rollback/maintenance; keep web/support path if safe |
| Payments | Disable affected provider first; do not delete payment state; reconcile paid/orphan records manually through audited support/finance flow |
| Provisioning | Stop new provisioning if needed; preserve paid subscriptions; queue/manual support resolution |
| Remnawave | Roll back Remnawave config/profile/node changes separately; do not claim this local dry-run proves staging/prod Remnawave rollback |
| Database | No destructive rollback without backup/restore evidence and explicit owner decision |

## What This Proves

| Claim | Result |
|---|---|
| A release-pointer rollback model is locally executable | Proven |
| Rollback target compose can be validated before container start | Proven |
| Mini App runtime rollback controls exist and are tested locally | Proven |
| Admin rollback UI/API client paths are tested locally | Proven |
| Registration/payment/provisioning failure controls are tested locally | Proven |
| No local containers were left running | Proven |

## What This Does Not Prove Yet

| Gap | Required later |
|---|---|
| Real staging/prod rollback | Run against actual staging stack and preserve transcript |
| Final RC artifact rollback | Use immutable `stage1-beta-rc.N` / previous tag or digest |
| Frontend/admin hosting rollback | Depends on final hosting target; must be proven on that platform |
| DB migration rollback safety | Requires clean backup, restore drill and migration compatibility decision |
| Real payment provider pause/rollback | Requires provider credentials/dashboard/API evidence |
| Real Remnawave rollback | Requires staging/prod Remnawave config/export/rebuild evidence |
| Alert/status communication | Local alert routing exists in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live alert delivery and status/support proof still required |

## Documentation Sync and Final Checks

After creating this evidence, the Stage 1 documentation set was synchronized:

- `00_INDEX.md` references this evidence file;
- `06_STAGE1_IMPLEMENTATION_BACKLOG.md` marks `S1-REL-006` as completed locally;
- `21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md` and `77_STAGE1_REMAINING_WORK_TO_LAUNCH.md` were updated after `S1-QA-004` to point to `S1-OBS-001` as the next ID;
- `08_STAGE1_GO_LIVE_RUNBOOK.md`, `10_STAGE1_RISK_REGISTER.md`, `11_STAGE1_REVIEW_CHECKLIST.md` and `14_STAGE1_BLOCKER_RESOLUTION_PLAN.md` record local rollback proof plus the remaining staging/prod rollback requirement;
- `CYBERVPN_STAGE1_LAUNCH_PACK_COMBINED.md` was regenerated.

Verification commands and results:

| Check | Result |
|---|---|
| Stale next-step scan for `Next ID to execute: S1-REL-006` in source docs | PASS: no matches |
| `git diff --check` on touched docs | PASS |
| Running containers after task | PASS: no running Compose services reported |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory via `next` remains tracked, and `audit fix --force` was not applied because it proposes a breaking/downgrade path |
| Backend `uv export` + `pip-audit` | PASS: no known vulnerabilities found |
| Secret-pattern scan over touched docs | PASS: no matches |
| Dangerous-pattern scan over touched docs | PASS: no matches |

## Acceptance Result

`S1-REL-006` is **completed locally** as a no-cost rollback dry-run/proof.

It is acceptable for continuing local S1 work. It is not sufficient for go-live until the same rollback model is repeated on staging/production release candidates with real artifacts, real hosting surfaces, managed backup/restore proof and alert delivery evidence.

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-REL-006` as item `26` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| Release pointer dry-run | PASS: `current` switched back to `stage1-beta-live.1`, compose config valid, `elapsed_ms=30` |
| `cd infra && docker compose --profile worker --profile bot --profile monitoring config --quiet` | PASS |
| `cd backend && SKIP_TEST_DB_BOOTSTRAP=1 PYENV_VERSION=3.13.11 uv run pytest --no-cov tests/unit/presentation/api/v1/admin/test_system_config.py tests/unit/presentation/api/v1/miniapp/test_routes.py -q` | PASS: `27` tests |
| `npm --prefix admin run test:run -- src/lib/api/__tests__/governance-miniapp-runtime.test.ts src/features/governance/components/__tests__/policy-console.test.tsx` | PASS: `2` files, `13` tests |
| `cd backend && SKIP_TEST_DB_BOOTSTRAP=1 PYENV_VERSION=3.13.11 uv run pytest --no-cov tests/security/test_registration_security.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_orphan_payment_policy.py -q` | PASS: `27` tests |

`S1-OBS-001`, `S1-OBS-002`, `S1-OBS-003` and `S1-OBS-004` were completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`, `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` and `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
