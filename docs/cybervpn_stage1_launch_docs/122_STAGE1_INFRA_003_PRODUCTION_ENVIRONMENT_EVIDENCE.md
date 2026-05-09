# S1-INFRA-003 - Production Environment Deployability Evidence

> Backlog ID: `S1-INFRA-003`
> Status: local production deployability contract complete; revalidated on 2026-05-09; external production evidence still required
> Date: 2026-05-08
> Revalidation date: 2026-05-09
> Scope: no-cost repository evidence only; no paid production infrastructure was created

## Decision

`S1-INFRA-003` is closed locally as a production deployability contract, not as a live production deployment.

For S1 Controlled Public Beta, production must be:

- separate from staging;
- deployed only from immutable tag or commit SHA;
- backed by managed/private PostgreSQL 17.x;
- backed by private Valkey/Redis that is not the durable source of truth;
- connected to a dedicated private/internal production Remnawave control-plane;
- exposed publicly only through required ingress surfaces;
- protected by kill switches for registration, payments, trial, provisioning, Telegram Stars, growth flows, add-ons and risky auth flows;
- blocked from go-live until external production evidence exists.

Home-lab infrastructure is explicitly not accepted as production authority for S1. It may remain useful for non-critical lab/evidence/device-testing work.

## Repository Artifacts Added

| Artifact | Purpose |
|---|---|
| `infra/topology/stage1-production-environment.json` | Machine-readable production deployability contract |
| `scripts/validate_s1_production_environment.py` | Static validator for the production environment contract |
| `infra/tests/test_stage1_production_environment.py` | Pytest contract coverage for production invariants |
| `infra/topology/README.md` | Topology index updated with production environment artifacts |

## Existing Production Scaffolds Observed

The repository already contains production-oriented scaffolding. These files are useful for future rollout, but they are not live production evidence by themselves:

| Path | Role |
|---|---|
| `infra/terraform/live/production/foundation` | Production foundation stack scaffold |
| `infra/terraform/live/production/prod-mgmt` | Production management cluster scaffold |
| `infra/terraform/live/production/edge` | Production edge scaffold |
| `infra/terraform/live/production/dns` | Production DNS scaffold |
| `infra/terraform/live/production/control-plane` | Production control-plane scaffold |
| `infra/scripts/prod_mgmt_bootstrap.py` | Production management bootstrap helper |

## Production Boundary

The production contract requires these boundaries:

| Boundary | S1 Rule |
|---|---|
| Staging credentials | Must not be used in production |
| Staging state | Must not be shared with production |
| Staging Remnawave | Must be separate from production Remnawave |
| Staging Telegram bot | Must be separate from production Telegram bot |
| Staging OAuth apps | Must be separate from production OAuth apps |
| Staging payment credentials | Must not be used for enabled live payment paths |
| Home lab | Not accepted as production authority |
| Deploy source | Immutable tag or commit SHA only; no floating `main` |
| Secrets | No production secrets in repository |

## Production Public Ingress Contract

| Surface | Host | Required Control |
|---|---|---|
| Public site primary | `cyber-vpn.net` | TLS, security headers, canonical origin |
| Public site primary www | `www.cyber-vpn.net` | TLS, redirect/canonical to primary |
| Public mirror | `cyber-vpn.org` | TLS, mirror/redirect policy, no duplicate cookie scope |
| Public mirror www | `www.cyber-vpn.org` | TLS, mirror/redirect policy |
| Backend API | `api.cyber-vpn.net` | TLS, CORS allowlist, CSRF where needed, rate limits, Swagger off |
| Admin primary | `admin.cyber-vpn.net` | TLS, access protection, admin 2FA, RBAC, audit |
| Admin mirror | `admin.cyber-vpn.org` | TLS, redirect to primary admin, no independent session cookie |
| Telegram webhook | `api.cyber-vpn.net` | TLS, no interactive edge challenge, bot verification |
| Payment webhooks | `api.cyber-vpn.net` | TLS, provider signature/recheck, idempotency, no interactive edge challenge |
| OAuth callbacks | `api.cyber-vpn.net` | TLS, Google/GitHub only, state/nonce validation |

## Required External Evidence Before Go-Live

The local contract is not enough to send users to production. Before S1 go-live, attach redacted evidence for:

1. production hosting/provider account and region;
2. production public origins;
3. production private network boundary;
4. DNS/TLS/redirect proof for `.net` primary and `.org` mirrors;
5. backend readiness/health proof;
6. managed PostgreSQL private access, clean migrations, encrypted backup and restore drill;
7. private Valkey/Redis access, memory policy and monitoring;
8. production Remnawave health, profile/inbound, node connectivity and backup/export/rebuild strategy;
9. BotFather production bot, webhook and Mini App domain proof;
10. at least one live payment provider callback/signature/idempotency proof before paid beta;
11. production observability and alert delivery proof;
12. production rollback dry-run proof on final RC artifacts;
13. redacted production secrets inventory without values;
14. production first-admin bootstrap, mandatory 2FA and audit evidence;
15. final RC artifact security scan evidence.

## Verification Commands

```bash
python -m json.tool infra/topology/stage1-production-environment.json >/tmp/stage1-production-environment.pretty.json
python scripts/validate_s1_production_environment.py
python scripts/validate_s1_production_topology.py
python scripts/validate_s1_staging_environment.py
python scripts/validate_s1_dns_tls_contract.py
python scripts/validate_s1_protected_ingress.py
cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_environment.py -q --no-cov
cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py -q --no-cov
cd backend && PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_production_environment.py ../scripts/validate_s1_production_topology.py ../scripts/validate_s1_staging_environment.py ../scripts/validate_s1_dns_tls_contract.py ../scripts/validate_s1_protected_ingress.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py
git diff --check -- infra/topology/stage1-production-environment.json scripts/validate_s1_production_environment.py infra/tests/test_stage1_production_environment.py infra/topology/README.md docs/cybervpn_stage1_launch_docs/122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md
npm audit --omit=dev --audit-level=high
cd backend && PYENV_VERSION=3.13.11 pip-audit --skip-editable .
docker ps
```

## Verification Result

| Check | Result |
|---|---|
| Production environment JSON parse/format | Passed |
| Production environment validator | Passed |
| Production contract summary check | Passed: 12 required services, 10 public ingress surfaces, 12 deployability preflight items, 11 kill switches, 15 external evidence requirements, no staging-shared services, no public private-data/control/backup services, home-lab authority disabled, floating `main` deploys disabled |
| Dependent infra validators | Passed: production topology, staging environment, DNS/TLS contract and protected ingress contract |
| Production pytest contract tests | Passed: 5 passed |
| Combined infra pytest regression | Passed: 24 passed |
| Ruff | Passed for production/staging/DNS/TLS/protected-ingress validators and tests |
| Diff whitespace check | Passed for new S1-INFRA-003 artifacts; existing untracked historical docs still contain Markdown hard-break trailing spaces |
| High/critical npm production audit | Passed; current npm audit threshold is clean for high/critical findings and still reports only the tracked moderate Next/PostCSS advisory |
| Backend dependency audit | Passed: no known vulnerabilities found |
| Secret/IP-looking value scan for S1-INFRA-003 artifacts | Passed |
| Dangerous command/pattern scan for S1-INFRA-003 artifacts | Passed |
| Docker resource check | No running containers required for this task |

## Demo

| Component | Feature | Status |
|---|---|---|
| `scripts/validate_s1_production_environment.py` | Static production-environment contract validation | PASS |
| `infra/tests/test_stage1_production_environment.py` | Production boundary invariants: no staging/shared state, private data/control services, immutable deploy source, kill switches and required evidence | PASS |
| Dependent infra gates | Production topology, staging environment, DNS/TLS and protected ingress contracts continue to pass together | PASS |
| Live production deployment | External production host, public origins, managed DB/Valkey, Remnawave, bot, payment, observability, backup/restore, rollback and health evidence | PARTIAL by design; blocked until paid/external production resources are provisioned |

## Closed Locally

`S1-INFRA-003` now has a no-secret production deployability contract with validator and contract tests.

## Still Blocking External Production

The following remain blockers before S1 production traffic:

- real production host/provider not selected or evidenced;
- managed production PostgreSQL not created/evidenced;
- private production Valkey not created/evidenced;
- production Remnawave not created/evidenced;
- production DNS/TLS/redirects not proven;
- deployed protected ingress and origin firewall/security-group boundary not proven;
- live payment provider credentials/callbacks not proven;
- production observability alert delivery not proven;
- production backup/restore and rollback evidence not attached;
- production first-admin bootstrap/2FA/audit evidence not attached.

## Next Step

Next ID superseded by `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`, `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`, `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`, `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`, `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`, `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`, `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
