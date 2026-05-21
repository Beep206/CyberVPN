# S1-INFRA-004 - DNS/TLS Contract Evidence

> Backlog ID: `S1-INFRA-004`
> Status: local DNS/TLS contract complete; revalidated on 2026-05-09; external DNS/TLS evidence still required
> Date: 2026-05-08
> Revalidation date: 2026-05-09
> Scope: no-cost repository evidence only; no DNS provider changes were applied

## Decision

`S1-INFRA-004` is closed locally as a DNS/TLS contract, not as live DNS/TLS proof.

For S1 Controlled Public Beta:

- `cyber-vpn.net` is the primary public domain;
- `cyber-vpn.org` is reserved for VPN node hostnames and future subscription delivery only, not a mirror/redirect surface to the primary public domain;
- `admin.cyber-vpn.net` is the canonical admin host;
- `admin.cyber-vpn.org` is not used for S1 admin and must not serve an independent admin session;
- API/webhooks/OAuth use `api.cyber-vpn.net`;
- S1 status uses `https://cyber-vpn.net/status`; a separate status subdomain is not required for S1;
- payment webhooks, Telegram webhooks and OAuth callbacks must not be placed behind interactive browser challenges;
- no DNS record may point customer production traffic to staging or home-lab origins.

## Repository Artifacts Added

| Artifact | Purpose |
|---|---|
| `infra/dns/stage1-dns-tls-contract.json` | Machine-readable DNS/TLS contract |
| `scripts/validate_s1_dns_tls_contract.py` | Static validator for the DNS/TLS contract |
| `infra/tests/test_stage1_dns_tls_contract.py` | Pytest coverage for DNS/TLS invariants |
| `infra/dns/README.md` | Operator-facing summary of the S1 DNS/TLS contract |

## S1 Host Contract

| Host | Behavior |
|---|---|
| `cyber-vpn.net` | Primary public site and customer cabinet |
| `www.cyber-vpn.net` | Redirect to `https://cyber-vpn.net` |
| `api.cyber-vpn.net` | Backend API, payment webhooks, Telegram webhook and OAuth callbacks |
| `admin.cyber-vpn.net` | Protected admin canonical host |
| `cyber-vpn.org` | Reserved for VPN nodes and future subscription delivery; no customer web mirror |
| `www.cyber-vpn.org` | Not used for S1 customer web |
| `admin.cyber-vpn.org` | Not used for S1 admin; no independent admin session |
| `de-1.cyber-vpn.org` | Production VPN node hostname, DNS-only |
| `de-1.node.cyber-vpn.org` | Production VPN node alias, DNS-only |
| `https://cyber-vpn.net/status` | S1 status endpoint |

## TLS Requirements

| Requirement | S1 Rule |
|---|---|
| Edge TLS | Required for every public/admin/API host |
| Origin TLS | Required when the origin is reached through HTTPS |
| TLS mode | Full strict or equivalent before go-live |
| Minimum TLS | 1.2 minimum; TLS 1.3 preferred |
| HSTS | Enable only after DNS/TLS/redirects/subdomains are verified |
| Certificate hosts | `.net` primary, API/admin; future `.org` subscription host only after approval |
| Certificate private keys | Never committed |

## Live Evidence Required Before Go-Live

The following proof must be attached later, after DNS provider access and production origins exist:

1. DNS resolution for every required host.
2. TLS certificate check for every required host.
3. HTTP to HTTPS redirect proof.
4. `www.cyber-vpn.net` redirect proof.
5. Proof that `.org` customer/admin mirror routes are not enabled.
6. VPN node DNS proof for approved `.org` node hostnames.
7. `https://cyber-vpn.net/status` route proof.
8. Admin access protection before login.
9. Payment webhook no-interactive-challenge probe.
10. Telegram webhook no-interactive-challenge probe.
11. OAuth callback no-interactive-challenge probe.

## Live Probe Result From Current Workspace

No DNS provider or edge configuration was changed during this task. The no-cost live probes from the current workspace are useful as blocker evidence, not as go-live evidence:

| Probe | Current result | S1 interpretation |
|---|---|---|
| Apex DNS for `cyber-vpn.net` and `cyber-vpn.org` | Resolves to public addresses | Partial only; public IPs are intentionally not recorded in docs; `.org` is not a customer mirror |
| DNS for `www.cyber-vpn.net`, `api.cyber-vpn.net`, `admin.cyber-vpn.net` | Not resolved from this workspace | Blocker for live DNS/TLS evidence |
| TLS certificate probe for `cyber-vpn.net` | Public Let's Encrypt certificate observed, CN `cyber-vpn.net`, valid May 3-Aug 1 2026 | Partial only; does not prove app readiness, redirects, API/admin hosts or required full host coverage |
| TLS certificate probe for `cyber-vpn.org` | Public Let's Encrypt certificate observed, CN `cyber-vpn.org`, valid May 3-Aug 1 2026 | Historical partial probe only; `.org` is now reserved for nodes/future subscription, not customer mirror behavior |
| `http://cyber-vpn.net/` | Returned HTTP 200 without required HTTP->HTTPS redirect | Blocker; required behavior is 301/308 to HTTPS |
| HTTPS app/status curl probes | HTTPS application responses for apex/status did not complete within the local probe timeout | Blocker until a production edge/app target is configured and evidenced |
| Admin protection, payment webhook, Telegram webhook and OAuth callback no-challenge probes | Not provable because required API/admin hosts do not resolve | Blocker before go-live |

## Example Live Commands For Later Evidence

These commands are examples for the future live evidence pack. They are not run as proof in this local task because DNS/provider/origin access is not configured yet.

```bash
dig +short cyber-vpn.net
dig +short www.cyber-vpn.net
dig +short api.cyber-vpn.net
dig +short admin.cyber-vpn.net
dig +short cyber-vpn.org
dig +short de-1.cyber-vpn.org
dig +short de-1.node.cyber-vpn.org

curl -I http://cyber-vpn.net/
curl -I https://www.cyber-vpn.net/
curl -I https://cyber-vpn.net/status

openssl s_client -connect cyber-vpn.net:443 -servername cyber-vpn.net </dev/null
openssl s_client -connect api.cyber-vpn.net:443 -servername api.cyber-vpn.net </dev/null
openssl s_client -connect admin.cyber-vpn.net:443 -servername admin.cyber-vpn.net </dev/null
```

## Verification Commands

```bash
python -m json.tool infra/dns/stage1-dns-tls-contract.json >/tmp/stage1-dns-tls-contract.pretty.json
python scripts/validate_s1_dns_tls_contract.py
python scripts/validate_s1_production_environment.py
python scripts/validate_s1_edge_waf_baseline.py
python scripts/validate_s1_protected_ingress.py
cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_dns_tls_contract.py -q --no-cov
cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py ../infra/tests/test_stage1_edge_waf_baseline.py -q --no-cov
cd backend && PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_dns_tls_contract.py ../scripts/validate_s1_production_environment.py ../scripts/validate_s1_edge_waf_baseline.py ../scripts/validate_s1_protected_ingress.py ../scripts/validate_s1_production_topology.py ../scripts/validate_s1_staging_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_edge_waf_baseline.py ../infra/tests/test_stage1_protected_ingress.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_staging_environment.py
npm audit --omit=dev --audit-level=high
cd backend && PYENV_VERSION=3.13.11 pip-audit --skip-editable .
dig +short cyber-vpn.net
curl -I http://cyber-vpn.net/
openssl s_client -connect cyber-vpn.net:443 -servername cyber-vpn.net </dev/null
docker ps --format '{{.Names}}\t{{.Status}}'
```

## Verification Result

| Check | Result |
|---|---|
| DNS/TLS JSON parse/format | Passed |
| DNS/TLS contract validator | Passed |
| Production environment validator | Passed |
| Edge WAF baseline validator | Passed |
| Protected ingress validator | Passed |
| DNS/TLS contract summary check | Passed: 2 zones, 7 records, 7 certificate hosts, 6 redirects, 6 admin controls, 6 webhook/callback controls, 10 evidence commands, 10 forbidden conditions, go-live ready false |
| DNS/TLS pytest contract tests | Passed: 5 passed |
| Combined infra pytest regression | Passed: 27 passed |
| Ruff | Passed for DNS/TLS, production environment, edge WAF, protected ingress, topology and staging validators/tests |
| No-cost live DNS probe | Partial/blocking: apex `.net` and `.org` resolve; required `www`, `api` and `admin` hosts were not resolved from this workspace |
| No-cost live TLS probe | Partial/blocking: apex `.net` and `.org` certificates were observed; full required host coverage and app/redirect behavior are not proven |
| No-cost live redirect/status probe | Failed/blocking: `http://cyber-vpn.net/` returned 200 instead of required 301/308; HTTPS app/status responses did not complete within local probe timeout |
| Diff whitespace check | Passed for new S1-INFRA-004 artifacts |
| High/critical npm production audit | Passed; current npm audit threshold is clean for high/critical findings and still reports only the tracked moderate Next/PostCSS advisory |
| Backend dependency audit | Passed: no known vulnerabilities found |
| Secret/IP-looking value scan for S1-INFRA-004 artifacts | Passed |
| Dangerous command/pattern scan for S1-INFRA-004 artifacts | Passed |
| Docker resource check | No S1-INFRA-004 containers were started; no running containers were reported |

## Demo

| Component | Feature | Status |
|---|---|---|
| `scripts/validate_s1_dns_tls_contract.py` | Static DNS/TLS contract validation | PASS |
| `infra/tests/test_stage1_dns_tls_contract.py` | Host, certificate-host, redirect, status-route and forbidden-condition invariants | PASS |
| Dependent infra gates | Production environment, protected ingress and edge WAF contracts continue to pass together | PASS |
| Live DNS/TLS/redirects | Public DNS/TLS probes from current workspace | PARTIAL/FAIL as expected: apex DNS/TLS is partial, required subdomains/redirects/status/admin/webhook/OAuth proof are still missing |

## Closed Locally

`S1-INFRA-004` now has a no-secret DNS/TLS contract with validator and contract tests.

## Still Blocking External DNS/TLS

- DNS provider account/zone access is not evidenced.
- Production web/API/admin/redirect edge targets are not evidenced.
- TLS certificate status is not evidenced.
- Redirects are not proven live.
- Admin access protection is not proven live. Local protected ingress contract is completed in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`, but deployed proof is still missing.
- Webhook/callback no-challenge behavior is not proven live.

## Next Step

Next ID superseded by `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`, `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`, `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`, `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`, `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`, `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-19 Domain Decision Update

Owner decision: `.org` is no longer a customer/admin mirror for `.net`.

Updated contract:

- `.net` remains the only S1 customer/admin/API surface;
- `.org` is reserved for VPN nodes and future subscription delivery;
- `de-1.cyber-vpn.org` and `de-1.node.cyber-vpn.org` are DNS-only VPN node hostnames;
- `admin.cyber-vpn.org` must not serve S1 admin;
- future `.org` subscription delivery requires separate DNS/TLS/route evidence before live traffic is moved.

Revalidation:

```text
python scripts/validate_s1_dns_tls_contract.py
Result: S1-INFRA-004 DNS/TLS contract validation passed

PYENV_VERSION=3.13.11 pytest infra/tests/test_stage1_dns_tls_contract.py -q
Result: 5 passed
```

## 2026-05-09 Batch Revalidation

`S1-INFRA-004` was re-run as item 4 in the owner-requested batch:

1. `S1-BE-003`
2. `S1-REL-002`
3. `S1-INFRA-002`
4. `S1-INFRA-004`
5. `S1-BE-001`

Static contract verification:

```text
python -m json.tool infra/dns/stage1-dns-tls-contract.json
Result: PASS

python scripts/validate_s1_dns_tls_contract.py
Result: S1-INFRA-004 DNS/TLS contract validation passed

python scripts/validate_s1_edge_waf_baseline.py
Result: PASS: infra/edge/stage1-cloudflare-waf-baseline.json is valid for S1-INFRA-008

cd backend
uv run pytest ../infra/tests/test_stage1_staging_environment.py ../infra/tests/test_stage1_production_topology.py ../infra/tests/test_stage1_production_environment.py ../infra/tests/test_stage1_dns_tls_contract.py ../infra/tests/test_stage1_protected_ingress.py -q --no-cov
Result: 24 passed in 0.06s
```

No-cost live probe from this workspace:

| Probe | 2026-05-09 result | S1 interpretation |
|---|---|---|
| `cyber-vpn.net` DNS | Resolved; values not recorded | Partial only |
| `cyber-vpn.org` DNS | Resolved; values not recorded | Partial only |
| `www.cyber-vpn.net` DNS | Not resolved | Blocker |
| `api.cyber-vpn.net` DNS | Not resolved | Blocker |
| `admin.cyber-vpn.net` DNS | Not resolved | Blocker |
| `.org` customer/admin mirror DNS | Not required after 2026-05-19 domain decision | Not a blocker |
| `cyber-vpn.net` TLS | Certificate CN `cyber-vpn.net`, valid until Aug 1 2026 GMT | Partial only |
| `cyber-vpn.org` TLS | Certificate CN `cyber-vpn.org`, valid until Aug 1 2026 GMT | Historical partial probe only; `.org` is now node/future subscription zone |
| Required subdomain TLS | Failed because required subdomains do not resolve | Blocker |
| `http://cyber-vpn.net/` | HTTP 200, no redirect location | Blocker; required behavior is HTTP -> HTTPS redirect |
| HTTPS app/status probes | Timed out or failed from this workspace | Blocker until edge/app target is configured |
| API/admin/webhook/OAuth no-challenge probes | Not provable because required API/admin hosts do not resolve | Blocker |

Status remains unchanged: local DNS/TLS contract is valid, but live DNS/TLS/redirect/webhook/admin evidence is not ready for go-live.

The next execution item after this five-task batch is `S1-BE-002`.
