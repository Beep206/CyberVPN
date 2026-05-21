# S1-INFRA-005 - Protected Ingress Contract Evidence

> Backlog ID: `S1-INFRA-005`
> Status: local protected ingress contract complete; revalidated on 2026-05-09; deployed ingress evidence still required
> Date: 2026-05-08
> Revalidation date: 2026-05-09
> Scope: no-cost repository evidence only; no external edge, firewall or reverse proxy changes were applied

## Decision

`S1-INFRA-005` is closed locally as a protected ingress contract, not as deployed ingress proof.

For S1 Controlled Public Beta:

- backend and admin container ports must not be directly public;
- `api.cyber-vpn.net` is the only approved public backend API host;
- `admin.cyber-vpn.net` is the only canonical admin host and must be protected before the admin login page;
- `admin.cyber-vpn.org` is not used for S1 admin and must not serve admin;
- `cyber-vpn.org` is reserved for VPN node hostnames and future subscription delivery only, not customer/admin mirror traffic;
- customer domains must not serve admin/internal/operator routes;
- payment, Telegram and OAuth callback paths must not receive interactive browser challenges;
- Remnawave API, PostgreSQL, Valkey/Redis and observability ports must stay private;
- staging and home-lab origins must not receive customer production traffic.

## Repository Artifacts Added

| Artifact | Purpose |
|---|---|
| `infra/ingress/stage1-protected-ingress-contract.json` | Machine-readable protected ingress contract |
| `scripts/validate_s1_protected_ingress.py` | Static validator for ingress invariants |
| `infra/tests/test_stage1_protected_ingress.py` | Pytest coverage for backend/admin/private-boundary rules |
| `infra/ingress/README.md` | Operator-facing summary of the S1 protected ingress contract |

## S1 Entrypoint Contract

| Entrypoint | Behavior |
|---|---|
| `cyber-vpn.net` | Public customer web/cabinet only |
| `www.cyber-vpn.net` | Redirect to primary `.net` |
| `cyber-vpn.org` | Reserved for VPN nodes and future subscription delivery; no customer web mirror |
| `www.cyber-vpn.org` | Not used for S1 customer web |
| `api.cyber-vpn.net` | Controlled public backend API, payment webhooks, Telegram webhook and OAuth callbacks |
| `admin.cyber-vpn.net` | Protected admin entrypoint only |
| `admin.cyber-vpn.org` | Not used for S1 admin; no independent session |

## Required Controls

| Area | S1 Rule |
|---|---|
| Public API | TLS, security headers, CORS allowlist, CSRF for cookie flows, Swagger disabled, application and edge rate limits |
| Admin primary | TLS, Cloudflare Access/IP allowlist/private VPN or equivalent, backend admin host guard, mandatory 2FA, RBAC, audit and admin rate limits |
| `.org` admin surface | Must not serve admin; no independent session cookie and no admin backend origin |
| Payment webhooks | Provider signature or status recheck, idempotency, conservative rate limit and no interactive challenge |
| Telegram webhook | Telegram secret/signature validation, conservative rate limit and no interactive challenge |
| OAuth callbacks | Google/GitHub only, state/nonce validation, callback allowlist and no interactive challenge |
| Private services | Remnawave API, PostgreSQL, Valkey/Redis, worker, bot runtime and observability stay private |

## Blocked Public Paths

| Policy | Hosts | Paths |
|---|---|---|
| Customer web cannot serve admin/internal paths | `cyber-vpn.net`, `www.cyber-vpn.net`; `.org` is not customer web | `/admin/*`, `/api/v1/admin/*`, `/operator/*`, `/internal/*` |
| Production API docs disabled publicly | `api.cyber-vpn.net` | `/docs`, `/redoc`, `/openapi.json` |
| Internal/worker/debug APIs disabled publicly | `api.cyber-vpn.net` | `/api/v1/internal/*`, `/api/v1/worker/*`, `/api/v1/debug/*` |

## Live Evidence Required Before Go-Live

The following proof must be attached later, after external ingress exists:

1. edge route inventory for every public entrypoint;
2. redacted reverse proxy configuration;
3. origin firewall/security-group proof showing backend/admin container ports are not directly public;
4. `admin.cyber-vpn.net` Access/IP allowlist/private VPN proof before login page;
5. proof that `admin.cyber-vpn.org` is not serving S1 admin;
6. public customer domains cannot serve admin/internal routes;
7. `api.cyber-vpn.net` Swagger/OpenAPI disabled proof;
8. `api.cyber-vpn.net` CORS/cookie/CSRF proof for approved domains only;
9. payment webhook no-interactive-challenge proof;
10. Telegram webhook no-interactive-challenge proof;
11. OAuth callback no-interactive-challenge proof;
12. Remnawave API private/internal proof;
13. PostgreSQL private-only proof;
14. Valkey/Redis private-only proof;
15. admin 2FA/RBAC/audit smoke through deployed ingress;
16. edge/reverse-proxy log correlation for customer and webhook requests;
17. rollback route or release pointer proof for ingress changes.

## Live Probe Result From Current Workspace

No edge, firewall, reverse proxy or DNS provider configuration was changed during this task. The no-cost probes from the current workspace are blocker evidence, not go-live evidence:

| Probe | Current result | S1 interpretation |
|---|---|---|
| `https://cyber-vpn.net/admin/` and `https://cyber-vpn.net/api/v1/admin/users` | HTTPS requests did not complete within the local probe timeout | Blocker; customer-domain admin/internal route behavior is not live-proven |
| `https://api.cyber-vpn.net/docs` and `https://api.cyber-vpn.net/openapi.json` | `api.cyber-vpn.net` did not resolve from this workspace | Blocker; production Swagger/OpenAPI disablement is not live-proven |
| `https://admin.cyber-vpn.net/` | `admin.cyber-vpn.net` did not resolve from this workspace | Blocker; admin access gate before login is not live-proven |
| `https://admin.cyber-vpn.org/` | `admin.cyber-vpn.org` did not resolve from this workspace | Accepted after 2026-05-19 domain decision; admin `.org` mirror is not required |
| Telegram/payment/OAuth callback probes on `api.cyber-vpn.net` | `api.cyber-vpn.net` did not resolve from this workspace | Blocker; no-interactive-challenge callback behavior is not live-proven |
| Remnawave/PostgreSQL/Valkey/private observability ingress | No external production private network exists in this no-cost task | Blocker until production/staging private network evidence is attached |

## Example Live Commands For Later Evidence

These commands are examples for the future deployed evidence pack. They are not run as proof in this local task because external ingress and production origins are not configured yet.

```bash
curl -I https://cyber-vpn.net/admin/
curl -I https://cyber-vpn.net/api/v1/admin/users
curl -I https://api.cyber-vpn.net/docs
curl -I https://api.cyber-vpn.net/openapi.json
curl -I https://admin.cyber-vpn.net/
curl -I https://api.cyber-vpn.net/api/v1/telegram/webhook
curl -I https://api.cyber-vpn.net/api/v1/webhooks/payments/example
curl -I https://api.cyber-vpn.net/api/v1/oauth/google/callback
```

## Verification Commands

```bash
python -m json.tool infra/ingress/stage1-protected-ingress-contract.json >/tmp/stage1-protected-ingress-contract.pretty.json
python scripts/validate_s1_protected_ingress.py
python scripts/validate_s1_dns_tls_contract.py
python scripts/validate_s1_edge_waf_baseline.py
python scripts/validate_s1_production_environment.py
cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_protected_ingress.py -q --no-cov
cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py ../infra/tests/test_stage1_edge_waf_baseline.py -q --no-cov
cd backend && PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_protected_ingress.py ../scripts/validate_s1_dns_tls_contract.py ../scripts/validate_s1_edge_waf_baseline.py ../scripts/validate_s1_production_environment.py ../scripts/validate_s1_production_topology.py ../scripts/validate_s1_staging_environment.py ../infra/tests/test_stage1_protected_ingress.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_edge_waf_baseline.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py
npm audit --omit=dev --audit-level=high
cd backend && PYENV_VERSION=3.13.11 pip-audit --skip-editable .
curl -I https://cyber-vpn.net/admin/
curl -I https://api.cyber-vpn.net/docs
curl -I https://admin.cyber-vpn.net/
docker ps --format '{{.Names}}\t{{.Status}}'
```

## Verification Result

| Check | Result |
|---|---|
| Protected ingress JSON parse/format | Passed |
| Protected ingress contract validator | Passed |
| DNS/TLS contract validator | Passed |
| Edge WAF baseline validator | Passed |
| Production environment validator | Passed |
| Protected ingress summary check | Passed: 10 entrypoints, 3 blocked-public policies, 8 private-only components, 17 required live-evidence items, 14 forbidden conditions, go-live clearance false, external ingress false, floating `main` false |
| Protected ingress pytest contract tests | Passed: 6 passed |
| Combined infra pytest regression | Passed: 27 passed |
| Ruff | Passed for protected ingress, DNS/TLS, edge WAF, production environment, topology and staging validators/tests |
| No-cost live customer/admin path probes | Failed/blocking: `cyber-vpn.net` admin/internal route probes did not complete within the local timeout |
| No-cost live API/admin host probes | Failed/blocking: `api.cyber-vpn.net` and `admin.cyber-vpn.net` did not resolve from this workspace; `admin.cyber-vpn.org` is no longer an S1 admin mirror |
| No-cost live webhook/OAuth callback probes | Failed/blocking: no-interactive-challenge behavior cannot be proven until `api.cyber-vpn.net` resolves and routes to deployed production/staging ingress |
| Diff whitespace check | Passed for new S1-INFRA-005 artifacts |
| High/critical npm production audit | Passed; current npm audit threshold is clean for high/critical findings and still reports only the tracked moderate Next/PostCSS advisory |
| Backend dependency audit | Passed: no known vulnerabilities found |
| Secret/IP-looking value scan for S1-INFRA-005 artifacts | Passed |
| Dangerous command/pattern scan for S1-INFRA-005 artifacts | Passed |
| Docker resource check | No S1-INFRA-005 containers were started; no running containers were reported |

## Demo

| Component | Feature | Status |
|---|---|---|
| `scripts/validate_s1_protected_ingress.py` | Static protected-ingress contract validation | PASS |
| `infra/tests/test_stage1_protected_ingress.py` | Backend/admin direct-public exposure, admin access gate, private-service and callback no-challenge invariants | PASS |
| Dependent infra gates | DNS/TLS, edge WAF and production environment contracts continue to pass together | PASS |
| Live protected ingress | Public customer/admin/API/callback probes from current workspace | PARTIAL/FAIL as expected: no deployed ingress evidence; required API/admin hosts do not resolve and customer-domain admin route behavior is not proven |

## Closed Locally

`S1-INFRA-005` now has a no-secret protected ingress contract with validator and contract tests.

## Still Blocking External Ingress

- External edge/reverse proxy routes are not deployed.
- Origin firewall/security-group evidence is not attached.
- Admin access protection is not proven live.
- Backend direct-public exposure is not proven blocked live.
- Webhook/callback no-challenge behavior is not proven live.
- Private Remnawave/PostgreSQL/Valkey reachability is not proven live.
- Ingress rollback proof is not attached.

## Next Step

Next ID superseded by `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`, `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`, `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`, `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`, `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Ordered Batch Revalidation

`S1-INFRA-005` was re-run as item 20 in the owner-requested ordered batch.

Static/local verification:

```text
python -m json.tool infra/ingress/stage1-protected-ingress-contract.json
Result: PASS

python scripts/validate_s1_protected_ingress.py
Result: S1-INFRA-005 protected ingress contract validation passed

python scripts/validate_s1_dns_tls_contract.py
Result: S1-INFRA-004 DNS/TLS contract validation passed

python scripts/validate_s1_edge_waf_baseline.py
Result: PASS: infra/edge/stage1-cloudflare-waf-baseline.json is valid for S1-INFRA-008

python scripts/validate_s1_production_environment.py
Result: S1-INFRA-003 production environment validation passed

cd backend
PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_protected_ingress.py -q --no-cov
Result: 6 passed in 0.03s

PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py ../infra/tests/test_stage1_edge_waf_baseline.py -q --no-cov
Result: 27 passed in 0.06s

PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_protected_ingress.py ../scripts/validate_s1_dns_tls_contract.py ../scripts/validate_s1_edge_waf_baseline.py ../scripts/validate_s1_production_environment.py ../scripts/validate_s1_production_topology.py ../scripts/validate_s1_staging_environment.py ../infra/tests/test_stage1_protected_ingress.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_edge_waf_baseline.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py
Result: All checks passed
```

Execution note: one initial validator attempt used `backend/` as the working directory and failed to locate root-level `scripts/` and `infra/` paths. The validator block was then re-run from the repository root successfully; the successful root-level validator results above are the accepted evidence.

No-cost live probe result from this workspace remains blocker evidence:

| Probe | Current result |
|---|---|
| `https://cyber-vpn.net/admin/` | HTTP `000`, local probe timeout |
| `https://cyber-vpn.net/api/v1/admin/users` | HTTP `000`, local probe timeout |
| `https://api.cyber-vpn.net/docs` | HTTP `000`, host did not resolve |
| `https://api.cyber-vpn.net/openapi.json` | HTTP `000`, host did not resolve |
| `https://admin.cyber-vpn.net/` | HTTP `000`, host did not resolve |

Local acceptance remains unchanged. Real edge/reverse-proxy/firewall/admin-access and webhook/OAuth no-challenge evidence remain required before go-live.

## 2026-05-19 Domain Decision Update

Owner decision: `.org` is no longer a customer/admin mirror for `.net`.

Updated ingress contract:

- customer web is served only from `.net` approved hosts;
- `admin.cyber-vpn.net` remains the only canonical S1 admin host;
- `admin.cyber-vpn.org` is reserved/not used and must not serve admin;
- `.org` is reserved for VPN node hostnames and future subscription delivery;
- future subscription delivery on `.org` requires separate ingress/DNS/TLS evidence.

Revalidation:

```text
python scripts/validate_s1_protected_ingress.py
Result: S1-INFRA-005 protected ingress contract validation passed

PYENV_VERSION=3.13.11 pytest infra/tests/test_stage1_protected_ingress.py -q
Result: 6 passed
```
