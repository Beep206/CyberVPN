# 121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE

Backlog ID: `S1-INFRA-002`
Status: completed locally as staging environment contract; revalidated on 2026-05-09; real external staging is not created yet
Date: 2026-05-08
Revalidation date: 2026-05-09
Scope: Stage 1 staging environment definition for Controlled Public Beta

## Decision

`S1-INFRA-002` is closed locally as a **staging environment contract**, not as live staging infrastructure.

This is intentional. Owner previously asked to maximize no-cost work before paying for servers. A real staging environment requires external host/managed services, public origins, BotFather/test provider credentials and live health evidence. The repo can still lock the contract now so later provisioning does not drift.

## What Staging Must Prove

Stage 1 staging must be separate from production and must prove the full B2C flow with disposable data:

```text
staging site / Telegram
-> registration/login
-> trial or sandbox/test payment
-> Remnawave staging provisioning
-> QR/subscription URL/config delivery
-> VPN client connection or documented equivalent
-> support/admin inspection
-> alert/rollback evidence
```

## Local Implementation

Added:

- `infra/topology/stage1-staging-environment.json`
- `scripts/validate_s1_staging_environment.py`
- `infra/tests/test_stage1_staging_environment.py`

Updated:

- `infra/topology/README.md`

## Staging Contract Summary

| Area | Requirement |
|---|---|
| Authority | Staging is not go-live or paid-beta clearance |
| Data | Disposable; no production user data |
| Credentials | No production DB, Remnawave, Telegram, OAuth, payment, JWT/TOTP/encryption or observability credentials |
| Home lab | Not allowed as staging authority for S1 |
| PostgreSQL | Separate staging PostgreSQL 17.x, private-only, separate CyberVPN and Remnawave DB/users |
| Valkey/Redis | Separate private staging Valkey/Redis; not durable source of truth |
| Remnawave | Separate staging control-plane, private/internal API, disposable data, test node/profile/inbound evidence |
| Telegram | Separate staging bot and Mini App/domain evidence |
| Payments | Sandbox/test provider credentials only |
| Admin | Protected staging admin origin, admin 2FA, RBAC and audit proof |
| Observability | Staging Sentry/dashboard/alert proof with PII scrubbing |

## External Inputs Still Missing

The repository still does not know:

- staging host/cloud provider;
- staging region;
- staging public origins/domains;
- staging origin IPs;
- staging private network CIDR;
- managed PostgreSQL provider;
- private Valkey provider;
- staging Remnawave URL/node/profile/inbound;
- staging Telegram BotFather bot and Mini App domain;
- payment sandbox accounts;
- Google/GitHub staging OAuth apps;
- email provider/sender-domain;
- observability project IDs/DSNs;
- container registry and image digests;
- deploy user/SSH policy.

## Existing Repo Scaffolds Observed

| Scaffold | Current meaning |
|---|---|
| `infra/terraform/live/staging/foundation` | Staging OpenTofu foundation scaffold |
| `infra/terraform/live/staging/edge` | Staging edge-node scaffold |
| `infra/terraform/live/staging/dns` | Staging DNS scaffold |
| `infra/terraform/live/staging/control-plane` | Staging control-plane host scaffold |
| `infra/scripts/remnawave-staging-smoke.sh` | Staging Remnawave smoke script placeholder |
| `infra/docker-compose.yml` | Local/dev Remnawave/PostgreSQL/Valkey stack; useful for development, not staging authority |

## Evidence Required To Convert This Into Real Staging

| Evidence | Required result |
|---|---|
| Provider/host account | Recorded without secrets |
| Public origins | Staging site/API/admin/webhook origins recorded |
| DNS/TLS | Staging records resolve and TLS is valid |
| Backend health | Backend readiness passes with staging DB/Valkey/Remnawave |
| PostgreSQL | Private access, clean migration transcript, separate DB/users, backup config |
| Valkey | Private access, memory policy, monitoring target, recovery behavior |
| Remnawave | Health, API smoke, connected test node, profile/inbound, backup/export/rebuild plan |
| Telegram | getMe, commands, webhook, Mini App domain |
| Payments | Sandbox/test callback, signature/recheck and duplicate-idempotency proof |
| Observability | Sentry test event, dashboard/live target, alert delivery, PII scrubber proof |
| Rollback | Staging rollback dry-run against RC artifact |
| Secrets | Redacted staging secrets inventory without values |

## Verification

Commands:

```bash
python scripts/validate_s1_staging_environment.py
python -m json.tool infra/topology/stage1-staging-environment.json >/tmp/stage1-staging-environment.pretty.json

cd backend
PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_staging_environment.py -q --no-cov
PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_staging_environment.py ../infra/tests/test_stage1_staging_environment.py

cd ..
python scripts/validate_s1_production_topology.py
python scripts/validate_s1_staging_environment.py
python scripts/validate_s1_production_environment.py
python scripts/validate_s1_dns_tls_contract.py
python scripts/validate_s1_protected_ingress.py

cd backend
PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py -q --no-cov
PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_production_topology.py ../scripts/validate_s1_staging_environment.py ../scripts/validate_s1_production_environment.py ../scripts/validate_s1_dns_tls_contract.py ../scripts/validate_s1_protected_ingress.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py
```

Results:

| Check | Result |
|---|---|
| Static staging validator | PASS: `infra/topology/stage1-staging-environment.json` is valid for `S1-INFRA-002` |
| JSON parse/format check | PASS: `python -m json.tool infra/topology/stage1-staging-environment.json` completed |
| Staging summary check | PASS: 11 required services, 5 staging public ingress entries, 13 required E2E flows, 13 required external evidence items, no production-shared services, no public private-data/control services, home-lab authority disabled |
| Pytest contract | PASS: 4 passed in 0.03s |
| Ruff on validator/test | PASS |
| Production topology regression validator | PASS: `infra/topology/stage1-production-topology.json` remains valid |
| Dependent infra validators | PASS: production topology, staging, production deployability, DNS/TLS and protected-ingress contracts validate |
| Combined staging/topology/production/DNS/ingress pytest regression | PASS: 24 passed in 0.06s |
| Ruff on dependent validators/tests | PASS |
| `git diff --check` on touched tracked files | PASS |
| Secret-pattern scan over S1-INFRA-002 touched files excluding historical combined pack | PASS: no high-confidence matches |
| Dangerous-code pattern scan over S1-INFRA-002 touched files excluding historical combined pack | PASS: no matches |
| Root npm production dependency audit | PASS for high/critical threshold; only moderate Next/PostCSS advisory reported |
| Backend Python dependency audit | PASS: no known vulnerabilities found |
| Running containers after task | PASS: no running containers reported |

The historical combined pack contains older command transcripts and test placeholders, so broad secret/dangerous scans over that aggregate can match previously documented local examples. The task scan above targets the current S1-INFRA-002 source/evidence files and excludes the historical aggregate.

## DEMO

COMPONENT:

- Command: `python scripts/validate_s1_staging_environment.py`
- Result: PASS, the staging manifest validates required services, separation, ingress, E2E flows and external evidence list.

FEATURE:

- Command: `cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py -q --no-cov`
- Result: PASS, 24 tests proved that staging remains separate from production and still agrees with production topology, production deployability, DNS/TLS and protected ingress contracts.

Feature test status is **partial by design**: live staging cannot be fully tested until external staging host/provider/public origins and test credentials exist.

## What This Closes

| Item | Status |
|---|---|
| `S1-INFRA-002` local staging environment contract | Closed locally |
| Separate staging DB/Valkey/Remnawave/bot/payment-mode requirements | Documented and validated |
| Staging no-production-credential/no-production-data boundary | Documented and validated |
| Required staging health/evidence checklist | Documented and validated |
| Existing repo staging scaffolds | Identified |

## What Remains Open

| Item | Why still open |
|---|---|
| Real external staging environment | Requires external host/managed services or accepted staging infrastructure |
| Staging DNS/TLS | Requires selected staging origins and DNS/edge provider access |
| Staging Remnawave | Requires real separate Remnawave instance and test node |
| Staging Telegram | Requires BotFather staging bot, token storage and webhook proof |
| Staging payment sandbox | Requires provider accounts/credentials/callback evidence |
| Staging observability | Requires live Sentry/dashboard/alert delivery proof |
| Staging rollback | Requires deployed RC artifact and rollback drill |

## Next ID

Next ID superseded by this 2026-05-09 `S1-INFRA-002` revalidation; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Batch Revalidation

`S1-INFRA-002` was re-run as item 3 in the owner-requested batch:

1. `S1-BE-003`
2. `S1-REL-002`
3. `S1-INFRA-002`
4. `S1-INFRA-004`
5. `S1-BE-001`

Verification:

```text
python scripts/validate_s1_staging_environment.py
Result: PASS: infra/topology/stage1-staging-environment.json is valid for S1-INFRA-002

python -m json.tool infra/topology/stage1-staging-environment.json
Result: PASS

python scripts/validate_s1_production_topology.py
Result: PASS

python scripts/validate_s1_production_environment.py
Result: PASS

python scripts/validate_s1_dns_tls_contract.py
Result: PASS

python scripts/validate_s1_protected_ingress.py
Result: PASS

cd backend
uv run pytest ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py -q --no-cov
Result: 24 passed in 0.06s

uv run ruff check ../scripts/validate_s1_staging_environment.py ../scripts/validate_s1_dns_tls_contract.py ../scripts/validate_s1_production_topology.py ../scripts/validate_s1_production_environment.py ../scripts/validate_s1_protected_ingress.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_protected_ingress.py
Result: All checks passed
```

Status remains unchanged: local contract is valid, but real staging is still not created. External staging still requires host/provider, public origins, private network, separate PostgreSQL/Valkey/Remnawave, staging bot, sandbox payment accounts, OAuth/email provider configuration, observability, rollback and redacted secret inventory.

The next execution item after this five-task batch is `S1-BE-002`.
