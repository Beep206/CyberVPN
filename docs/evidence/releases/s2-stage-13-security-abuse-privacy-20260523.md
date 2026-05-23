# S2-STAGE-13 Security, Abuse, And Privacy Evidence

**Date:** 2026-05-23
**Stage:** `S2-STAGE-13`
**Result:** `PASS_WITH_CONTROLLED_GAPS`
**Owner:** `@Sasha_Beep`

---

## 1. Scope

This evidence records the Stage 2 security, abuse and privacy gate.

Covered:

- dependency audit;
- secrets scan;
- frontend/admin bundle/env leak scan;
- production public route probes;
- payment and Remnawave webhook invalid-request probes;
- production runtime security flags;
- required admin 2FA;
- admin public header hygiene;
- production container log privacy scan;
- firewall/listening boundary;
- controlled gap classification.

No secret values are stored in this evidence file.

---

## 2. Dependency Audit

Command:

```text
PYENV_VERSION=3.13.11 SECURITY_ARTIFACT_DIR=.tmp/s2-stage13-security bash scripts/security/audit-dependencies.sh all
```

NPM high/critical result:

```text
root     high=0 critical=0 moderate=4 exit_code=0
admin    high=0 critical=0 moderate=3 exit_code=0
frontend high=0 critical=0 moderate=3 exit_code=0
partner  high=0 critical=0 moderate=3 exit_code=0
```

Python result:

```text
backend              No known vulnerabilities found, exit_code=0
services/task-worker No known vulnerabilities found, exit_code=0
services/telegram-bot No known vulnerabilities found, exit_code=0
```

Fixed during this gate:

```text
services/task-worker
idna      3.12  -> 3.16
starlette 1.0.0 -> 1.0.1
urllib3   2.6.3 -> 2.7.0
```

Verification:

```text
idna 3.16
starlette 1.0.1
urllib3 2.7.0
```

---

## 3. Secrets Scan

Command:

```text
SECURITY_ARTIFACT_DIR=.tmp/s2-stage13-security GITLEAKS_EXIT_CODE=1 bash scripts/security/scan-secrets.sh
```

Observed:

```text
scanned ~158.98 MB in 16.3s
no leaks found
```

Local artifacts:

```text
.tmp/s2-stage13-security/gitleaks-s1-current-tree-redacted.json
.tmp/s2-stage13-security/gitleaks-s1-current-tree-by-file.tsv
.tmp/s2-stage13-security/gitleaks-s1-current-tree-by-rule.tsv
```

These artifacts are intentionally not committed.

---

## 4. Backend Security Test Suite

Command:

```text
cd backend && uv run pytest --no-cov \
  tests/security/test_stage1_rate_limit_policy.py \
  tests/security/test_stage1_webhook_signature_verification.py \
  tests/security/test_stage1_webhook_idempotency.py \
  tests/security/test_stage1_csrf_protection.py \
  tests/security/test_stage1_cors_cookie_config.py \
  tests/security/test_stage1_registration_kill_switch.py \
  tests/security/test_stage1_trial_provisioning.py \
  tests/security/test_stage2_payment_production_hardening.py \
  tests/security/test_stage2_support_admin_ops.py \
  tests/security/test_stage2_subscription_lifecycle.py \
  tests/security/test_stage2_vpn_provisioning_capacity.py
```

Observed:

```text
109 passed in 9.16s
```

Covered:

- rate limits;
- webhook signatures;
- webhook idempotency;
- CSRF;
- CORS/cookie config;
- registration kill switch;
- trial provisioning;
- payment hardening;
- support/admin ops;
- subscription lifecycle;
- VPN provisioning/capacity.

---

## 5. Bundle And Env Leak Scan

Production builds passed:

```text
NEXT_TELEMETRY_DISABLED=1 npm run build -w frontend
NEXT_TELEMETRY_DISABLED=1 npm run build -w admin
```

Production bundle scan targets:

```text
frontend/.next/static
frontend/.next/server/app
admin/.next/static
admin/.next/server/app
```

Observed:

```text
No token/config/secret pattern matches.
No sensitive env-name matches.
```

Build sizes:

```text
frontend/.next/static  7.1M
frontend/.next/server  1.2G
admin/.next/static     5.6M
admin/.next/server     117M
```

---

## 6. Production Route Probes

Observed:

```text
https://cyber-vpn.net/ru-RU                 HTTP/2 200, alt-svc h3, HSTS
https://cyber-vpn.net/ru-RU/login           HTTP/2 200, alt-svc h3, HSTS
https://api.cyber-vpn.net/health            HTTP/2 200, JSON {"status":"ok"}
https://api.cyber-vpn.net/docs              HTTP/2 404
https://api.cyber-vpn.net/openapi.json      HTTP/2 404
https://admin.cyber-vpn.net/ru-RU/login     HTTP/2 200, alt-svc h3, HSTS
https://cyber-vpn.org/api/sub/<redacted>    HTTP/2 404 JSON from Remnawave
https://cyber-vpn.org/                      HTTP/2 301 -> https://cyber-vpn.net/
https://admin.cyber-vpn.org/                HTTP/2 301 -> https://admin.cyber-vpn.net/
```

The local `curl` build does not support `--http3-only`, so HTTP/3 was verified by public `alt-svc` headers and the production firewall/listener state for `443/udp`.

---

## 7. Admin Header Hygiene Fix

Finding:

```text
admin.cyber-vpn.net emitted Link headers containing internal 127.0.0.1 origin fragments.
```

Fix applied:

```text
admin/src/app/[locale]/layout.tsx -> root admin metadata is private/noindex
prod-app-1 Caddy admin_proxy -> header_down -Link
infra/deploy/stage1/Caddyfile.stage1.snippet -> header_down -Link
infra/deploy/stage1/Caddyfile.system-stage1.snippet -> header_down -Link
```

Caddy validation/reload:

```text
Valid configuration
caddy reload completed
```

Post-fix verification:

```text
admin.cyber-vpn.net link_count=0
alt-svc: h3=":443"; ma=86400
```

No HTTP/3/QUIC setting was disabled.

---

## 8. Webhook Invalid-Request Probes

CryptoBot unsigned request:

```text
POST https://api.cyber-vpn.net/api/v1/webhooks/cryptobot
HTTP/2 401
{"detail":"Invalid webhook signature"}
```

Remnawave invalid request:

```text
POST https://api.cyber-vpn.net/api/v1/webhooks/remnawave
HTTP/2 200
{"status":"invalid_signature"}
```

Interpretation:

1. invalid webhook payloads do not create successful side effects;
2. routes are reachable by providers without Cloudflare challenge HTML;
3. invalid requests are handled by application logic and return JSON.

---

## 9. Production Runtime Flags

Observed from backend settings, secret values not printed:

```text
environment=production
debug=False
swagger_enabled=False
csrf_protection_enabled=True
rate_limit_enabled=True
rate_limit_fail_open=False
trust_proxy_headers=True
admin_host_protection_enabled=True
admin_2fa_required=True
registration_enabled=False
registration_invite_required=True
referral_enabled=False
promo_codes_enabled=False
gift_codes_enabled=False
checkout_code_discounts_enabled=False
payment_autorenewal_enabled=False
stage1_trial_provisioning_enabled=True
stage1_paid_provisioning_enabled=False
payments_enabled=False
telegram_stars_enabled=True
log_sanitization_enabled=True
cookie_secure=True
cookie_domain=cyber-vpn.net
oauth_enabled_login_providers=google,github
oauth_web_base_url_configured=True
oauth_token_encryption_key_configured=True
totp_fallback_key_configured=True
jwt_secret_configured=True
totp_encryption_key_configured=True
cryptobot_token_configured=True
telegram_bot_token_configured=True
remnawave_token_configured=True
remnawave_webhook_secret_configured=True
```

Controlled item:

```text
oauth_token_plaintext_fallback_enabled=True
```

This is accepted for staged compatibility because `OAUTH_TOKEN_ENCRYPTION_KEY` is configured and new OAuth token writes are encrypted. Disable fallback after confirming there are no legacy plaintext token rows.

---

## 10. Production Log Privacy Scan

Last-24h scan:

```text
cybervpn-stage1-cybervpn-backend-1       risky_log_pattern_count=0
cybervpn-stage1-cybervpn-worker-1        risky_log_pattern_count=0
cybervpn-stage1-cybervpn-scheduler-1     risky_log_pattern_count=0
cybervpn-stage1-cybervpn-telegram-bot-1  risky_log_pattern_count=0
cybervpn-stage1-cybervpn-admin-1         risky_log_pattern_count=0
cybervpn-stage1-cybervpn-frontend-1      risky_log_pattern_count=0
```

Checked for:

- raw `vless://`;
- raw `/api/sub/<token>`;
- `Authorization: Bearer`;
- `access_token`;
- `refresh_token`;
- payment API token names;
- Remnawave/Telegram secret names;
- Telegram bot token shape.

---

## 11. Firewall And Listener Boundary

Production firewall:

```text
Status: active
Default: deny incoming, allow outgoing, deny routed
Allowed inbound:
22/tcp
80/tcp
443/tcp
443/udp
```

Observed direct listeners:

```text
0.0.0.0:80/tcp
0.0.0.0:443/tcp
0.0.0.0:443/udp
127.0.0.1:13000 frontend
127.0.0.1:13001 admin
127.0.0.1:13005 Remnawave
127.0.0.1:18080 backend
127.0.0.1:18088 Telegram bot
```

Interpretation:

1. only SSH and edge ports are public;
2. application/data/service ports are loopback-bound;
3. QUIC remains allowed on `443/udp`.

---

## 12. Controlled Gaps

| Gap | Accepted for S2? | Follow-up |
|---|---|---|
| NPM moderate findings remain | Yes | Keep visible in dependency audit; upgrade when upstream packages resolve them |
| CSP remains Report-Only and includes inline/eval allowances | Yes | Tighten after S2 compatibility testing |
| Cloudflare WAF dashboard state was not API-verified | Yes | Add API evidence or owner screenshot before materially larger public paid traffic |
| OAuth plaintext fallback flag remains enabled | Yes | Disable after legacy-token check/migration |
| Paid/referral/promo/gift/autoprolongation are disabled | Yes | Re-run security/abuse gate before public enablement of each flow |

---

## 13. Result

`S2-STAGE-13` passes with controlled gaps.

No known high/critical issue blocks the next stage. Abuse-sensitive features remain behind kill switches until their public enablement evidence is complete. The detected admin public-header hygiene issue was fixed during the gate.

Next stage:

```text
S2-STAGE-14: GitLab CI/CD And Release Speed
```
