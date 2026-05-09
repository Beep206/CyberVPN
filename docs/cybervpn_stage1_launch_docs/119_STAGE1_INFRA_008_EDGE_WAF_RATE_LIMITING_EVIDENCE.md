# 119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE

Backlog ID: `S1-INFRA-008`
Status: completed locally as edge baseline; real provider enablement evidence remains required
Date: 2026-05-08
Scope: Stage 1 edge WAF/rate limiting baseline for Controlled Public Beta

## Decision

For S1 Controlled Public Beta, edge protection is accepted as a two-layer model:

- local/no-cost work defines the Cloudflare-or-equivalent baseline and validation checks;
- live Cloudflare/edge configuration is not considered enabled until DNS/TLS/admin/webhook/rate-limit evidence is attached;
- backend Redis/application rate limits from `S1-BE-007` remain mandatory even after edge controls are enabled;
- payment and Telegram webhooks must not receive interactive browser challenges;
- VPN transport ports, Remnawave private API, PostgreSQL and Valkey/Redis are not HTTP WAF surfaces and must stay private/protected by network/service controls.

This closes `S1-INFRA-008` for implementation readiness, but not for go-live clearance.

## Official References Checked

Context7 MCP is not available in this local tool session, so official Cloudflare documentation was used as the required fallback.

| Reference | Use |
|---|---|
| <https://developers.cloudflare.com/waf/custom-rules/> | Confirmed custom WAF rules, actions, plan limits and zone-level availability |
| <https://developers.cloudflare.com/waf/managed-rules/> | Confirmed managed WAF rulesets and plan-dependent availability |
| <https://developers.cloudflare.com/waf/rate-limiting-rules/> | Confirmed rate-limit rule parameters, periods, characteristics and availability caveats |
| <https://developers.cloudflare.com/waf/reference/phases/> | Confirmed WAF phases: custom rules, rate limiting and managed rules |
| <https://developers.cloudflare.com/cloudflare-one/access-controls/applications/choose-application-type/> | Confirmed Cloudflare Access self-hosted application model for admin protection |

## Local Implementation

Added:

- `infra/edge/stage1-cloudflare-waf-baseline.json`
- `infra/edge/README.md`
- `scripts/validate_s1_edge_waf_baseline.py`
- `infra/tests/test_stage1_edge_waf_baseline.py`

The baseline records:

| Area | Local baseline |
|---|---|
| Public primary | `cyber-vpn.net`, `www.cyber-vpn.net` behind managed WAF, custom sensitive-path block and basic rate limits |
| Public mirror | `cyber-vpn.org`, `www.cyber-vpn.org` as redirect-only mirror to `.net` |
| API | `api.cyber-vpn.net` through controlled public API ingress, with Swagger disabled in production |
| Admin | `admin.cyber-vpn.net` protected by Cloudflare Access, IP allowlist or equivalent, plus backend admin host guard and admin 2FA |
| Admin mirror | `admin.cyber-vpn.org` redirect-only to `admin.cyber-vpn.net` |
| Telegram webhook | Conservative rate limit only, no interactive challenge |
| Payment webhooks | Conservative rate limit only, no interactive challenge; backend signature/recheck/idempotency remains source of truth |
| OAuth callbacks | No interactive challenge loops; Google/GitHub callbacks only for S1 |
| Non-HTTP surfaces | VPN transport, Remnawave API, PostgreSQL and Valkey/Redis are excluded from public HTTP edge WAF |

## Rate Limit Baseline

| ID | Surface | Default local baseline |
|---|---|---|
| `s1-auth-sensitive` | login/register/verify/reset/magic/OTP | `30 / 60s` per IP, 300s mitigation |
| `s1-admin-sensitive` | admin auth and 2FA | `20 / 60s` per IP, 600s mitigation |
| `s1-trial-and-checkout` | trial, checkout, orders | `20 / 60s` per IP, 300s mitigation |
| `s1-payment-webhooks-conservative` | provider callbacks | `300 / 60s` per IP, no challenge; log first |
| `s1-telegram-webhook-conservative` | Telegram webhook | `600 / 60s` per IP, no challenge; log first |
| `s1-support-and-privacy-requests` | support/privacy requests | `30 / 60s` per IP, 300s mitigation |
| `s1-public-web-abuse` | public web | `1200 / 60s` per IP, managed challenge for non-verified bots where available |

These edge values are launch defaults, not final traffic-tuned limits. They must be adjusted only after staging/live traffic evidence.

## Verification

Commands:

```bash
python scripts/validate_s1_edge_waf_baseline.py

cd backend
uv run pytest ../infra/tests/test_stage1_edge_waf_baseline.py -q --no-cov
uv run ruff check ../scripts/validate_s1_edge_waf_baseline.py ../infra/tests/test_stage1_edge_waf_baseline.py

cd ..
git diff --check -- <touched S1-INFRA-008 files>
rg -n --pcre2 '<high-confidence secret patterns>' <touched S1-INFRA-008 files>
rg -n --pcre2 '<dangerous-code patterns>' <touched S1-INFRA-008 files>
npm --prefix frontend audit --omit=dev --audit-level=high
docker ps --format '{{.Names}}\t{{.Status}}'
```

Results:

| Check | Result |
|---|---|
| Static baseline validator | PASS: `infra/edge/stage1-cloudflare-waf-baseline.json` is valid for `S1-INFRA-008` |
| Pytest contract | PASS: 3 passed |
| Ruff on validator/test | PASS |
| `git diff --check` on touched S1-INFRA-008 files | PASS |
| High-confidence secret scan on touched S1-INFRA-008 files | PASS: no matches |
| Dangerous-pattern scan on touched S1-INFRA-008 files | PASS: no matches |
| Frontend production dependency audit | PASS for high/critical; existing low/moderate `icu-minify`/`next-intl`/`postcss` advisories remain tracked outside this task |
| Running containers after task | PASS: no running containers reported |
| Webhook no-challenge exceptions | PASS: payment, Telegram and OAuth exceptions present |
| Non-HTTP surface exclusion | PASS: VPN transport, Remnawave private API, PostgreSQL and Valkey/Redis excluded |

## Remaining Go-Live Evidence

Before S1 go-live, attach redacted evidence for:

- Cloudflare or equivalent edge account/zone configured outside repo;
- DNS records for `cyber-vpn.net` and `cyber-vpn.org`;
- TLS evidence for primary and mirror domains;
- `cyber-vpn.org` redirect to `cyber-vpn.net`;
- `admin.cyber-vpn.org` redirect to `admin.cyber-vpn.net`;
- `admin.cyber-vpn.net` protected by Cloudflare Access, IP allowlist or equivalent before exposing the login page;
- managed WAF enabled and false-positive review captured;
- custom sensitive-path block evidence with expected block event;
- auth/admin/trial/support rate-limit transcript with expected `429` or challenge behavior;
- payment webhook callback transcript proving no interactive challenge and backend idempotency still works;
- Telegram webhook transcript proving no interactive challenge and healthy webhook status;
- redacted Cloudflare Security Events or equivalent export with rule IDs and request correlation.

## What This Closes

| Item | Status |
|---|---|
| `S1-INFRA-008` local edge/WAF/rate-limit baseline | Closed locally |
| Cloudflare/equivalent edge policy shape | Documented |
| Webhook challenge exception policy | Documented and tested |
| Admin edge protection requirement | Documented and tested in baseline contract |
| Non-HTTP surface boundary | Documented and tested |

## What Remains Open

| Item | Why still open |
|---|---|
| Real edge WAF/rate-limit enablement | Requires Cloudflare/equivalent account, DNS and public ingress |
| DNS/TLS/redirect evidence | Local contract completed in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; live evidence not yet attached |
| Protected admin ingress evidence | Local ingress contract completed in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md` and local admin access guard covered by `S1-ADM-001`; deployed proof still required |
| Live webhook proof | Requires real provider/BotFather/public webhook endpoint |
| Live Security Events export | Requires real edge traffic |

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-INFRA-008` as item `21` in the owner-requested ordered batch before revalidating `S1-OBS-001` through `S1-OBS-004`.

| Check | Result |
|---|---|
| `python scripts/validate_s1_edge_waf_baseline.py` | PASS: `infra/edge/stage1-cloudflare-waf-baseline.json` is valid |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_edge_waf_baseline.py -q --no-cov` | PASS: `3` tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check ../scripts/validate_s1_edge_waf_baseline.py ../infra/tests/test_stage1_edge_waf_baseline.py` | PASS |

Local/no-cost contract status remains closed. Live DNS/TLS, WAF/rate-limit transcripts, admin-protection proof, webhook no-challenge proof and Security Events export remain required before go-live.

## Next ID

The current ordered local/revalidation chain has now completed through `S1-OBS-004`. Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
