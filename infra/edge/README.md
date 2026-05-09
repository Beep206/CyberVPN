# Stage 1 Edge WAF / Rate Limiting Baseline

This directory contains the no-secret local baseline for `S1-INFRA-008`.

The baseline is intentionally provider-specific enough for Cloudflare because the project already selected public domains that fit a Cloudflare-style DNS/TLS/WAF edge. It is still written as a baseline, not as live infrastructure state: no account ID, zone ID, API token, origin IP, tunnel token or secret value belongs here.

## Files

| File | Purpose |
|---|---|
| `stage1-cloudflare-waf-baseline.json` | Canonical Stage 1 edge/WAF/rate-limit baseline |
| `../../scripts/validate_s1_edge_waf_baseline.py` | Static validator for the baseline contract |
| `../tests/test_stage1_edge_waf_baseline.py` | Pytest coverage for the baseline contract |

## S1 Controls

The baseline requires:

- proxied HTTP edge for `cyber-vpn.net` and redirect-only mirror behavior for `cyber-vpn.org`;
- admin canonical host `admin.cyber-vpn.net`, with `admin.cyber-vpn.org` redirecting to it;
- Cloudflare Access, IP allowlist or equivalent protection in front of admin before go-live;
- managed WAF rules where the selected Cloudflare plan allows them;
- custom blocking for sensitive/scanner paths like `/.env`, `/.git`, `wp-login.php`, backup/database suffixes and debug paths;
- route-specific rate limits for auth, admin, trial/checkout, support/privacy requests, payment webhooks, Telegram webhook and public web abuse;
- explicit no-interactive-challenge exceptions for payment webhooks, Telegram webhooks and OAuth callbacks.

## Not Covered By HTTP Edge WAF

The baseline deliberately excludes:

- VPN transport ports;
- production Remnawave private API;
- managed PostgreSQL;
- private Valkey/Redis.

Those surfaces must be protected by private networking, provider firewall rules, service authentication and app-level controls rather than HTTP WAF rules.

## How To Use Before Go-Live

1. Configure Cloudflare or equivalent edge outside this repository.
2. Keep all zone IDs, API tokens and origin IP evidence outside committed files.
3. Apply the controls from `stage1-cloudflare-waf-baseline.json`.
4. Capture redacted evidence for DNS/TLS, redirects, admin protection, managed WAF, custom blocks, rate-limit behavior and no-challenge webhook behavior.
5. Attach the evidence to the Stage 1 evidence pack before any `stage1-beta-live.N` tag.

Until that real edge evidence exists, `S1-INFRA-008` is complete only as a local baseline and remains a go-live evidence gap.
