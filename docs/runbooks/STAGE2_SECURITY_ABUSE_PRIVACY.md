# Stage 2 Security, Abuse, And Privacy Runbook

**Stage:** `S2-STAGE-13`
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. When To Run

Run this gate:

1. before S2 public expansion;
2. before enabling paid production checkout;
3. before enabling public referral, promo, gift or autoprolongation flows;
4. after dependency upgrades in backend, frontend, admin, bot or worker;
5. after edge/Caddy/Cloudflare route changes;
6. after any suspected secret, token, webhook or log disclosure.

---

## 2. Dependency Audit

From repo root:

```bash
SECURITY_ARTIFACT_DIR="$PWD/.tmp/s2-stage13-security" \
PYENV_VERSION=3.13.11 \
bash scripts/security/audit-dependencies.sh all
```

Acceptance:

- `npm audit --audit-level=high` must have `0 high` and `0 critical`;
- `pip-audit` must report no known vulnerabilities for backend, bot and task-worker;
- moderate/low npm findings may be accepted only if documented.

If the script cannot find `pip-audit`, install or select a Python where `pip-audit` is available. Do not bypass Python audit silently.

---

## 3. Secret Scan

```bash
SECURITY_ARTIFACT_DIR="$PWD/.tmp/s2-stage13-security" \
GITLEAKS_EXIT_CODE=1 \
bash scripts/security/scan-secrets.sh
```

Acceptance:

```text
no leaks found
```

Do not commit `.tmp/s2-stage13-security`.

---

## 4. Bundle / Env Leak Scan

Build:

```bash
NEXT_TELEMETRY_DISABLED=1 npm run build -w frontend
NEXT_TELEMETRY_DISABLED=1 npm run build -w admin
```

Scan public/static and server app bundles:

```bash
rg -n --hidden --pcre2 \
"(875[0-9]{7,}:AA[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|BEGIN (RSA |OPENSSH |EC |DSA |PRIVATE )?PRIVATE KEY|postgresql\\+asyncpg://[^\\s'\\\"]+|redis://[^\\s'\\\"]+|vless://[A-Za-z0-9._~:/?#\\[\\]@!$&'()*+,;=%-]{40,}|https://api\\.cyber-vpn\\.net/api/sub/[A-Za-z0-9_-]{12,}|https://cyber-vpn\\.org/api/sub/[A-Za-z0-9_-]{12,})" \
frontend/.next/static admin/.next/static frontend/.next/server/app admin/.next/server/app
```

Scan secret env names:

```bash
rg -n --hidden \
"SENTRY_AUTH_TOKEN|OAUTH_TRANSACTION_SECRET|PENDING_2FA_SECRET|TELEGRAM_BOT_TOKEN|CRYPTOBOT_TOKEN|REMNAWAVE_TOKEN|REMNAWAVE_API_TOKEN|DATABASE_URL|REDIS_URL|JWT_SECRET|TOTP_ENCRYPTION_KEY|FRONTEND_OBSERVABILITY_INTERNAL_SECRET" \
frontend/.next/static admin/.next/static frontend/.next/server/app admin/.next/server/app
```

Acceptance: no matches.

---

## 5. Public Edge Probes

```bash
for url in \
  https://cyber-vpn.net/ru-RU \
  https://api.cyber-vpn.net/health \
  https://api.cyber-vpn.net/docs \
  https://api.cyber-vpn.net/openapi.json \
  https://admin.cyber-vpn.net/ru-RU/login \
  https://cyber-vpn.org/api/sub/test-redacted \
  https://cyber-vpn.org/ \
  https://admin.cyber-vpn.org/
do
  echo "URL $url"
  curl -k -sS -D - -o /tmp/cybervpn-edge-body --max-time 15 "$url" \
    | sed -n '1,24p'
  head -c 120 /tmp/cybervpn-edge-body | tr '\n' ' '
  echo
done
```

Expected:

- `cyber-vpn.net` and admin login return `200`;
- API health returns `200`;
- API docs and OpenAPI return `404`;
- `.org` non-subscription routes redirect to `.net`;
- `.org /api/sub/<invalid>` returns controlled JSON error;
- `alt-svc: h3` remains present where Cloudflare/Caddy advertises HTTP/3;
- admin response has `link_count=0`.

Admin link check:

```bash
curl -k -sS -D - -o /dev/null --max-time 15 https://admin.cyber-vpn.net/ru-RU/login \
  | awk 'BEGIN{IGNORECASE=1;c=0} /^link:/{c++} END{print c}'
```

Expected:

```text
0
```

---

## 6. Webhook Safety Probes

CryptoBot unsigned request:

```bash
curl -k -sS -D - -o /tmp/cryptobot-webhook-body \
  --max-time 15 \
  -X POST https://api.cyber-vpn.net/api/v1/webhooks/cryptobot \
  -H 'content-type: application/json' \
  --data '{}'
cat /tmp/cryptobot-webhook-body
```

Expected:

```text
HTTP 401
{"detail":"Invalid webhook signature"}
```

Remnawave invalid request:

```bash
curl -k -sS -D - -o /tmp/remnawave-webhook-body \
  --max-time 15 \
  -X POST https://api.cyber-vpn.net/api/v1/webhooks/remnawave \
  -H 'content-type: application/json' \
  --data '{}'
cat /tmp/remnawave-webhook-body
```

Expected:

```text
JSON response from backend, no HTML challenge page
```

---

## 7. Production Runtime Flag Probe

Run from the operator machine. Do not print secret values.

```bash
ssh -i ~/.ssh/MainKey2_private_fixed.pem root@45.87.41.146 \
"docker exec -i cybervpn-stage1-cybervpn-backend-1 python - <<'PY'
from src.config.settings import settings
fields = [
    'environment', 'debug', 'swagger_enabled', 'csrf_protection_enabled',
    'rate_limit_enabled', 'rate_limit_fail_open', 'trust_proxy_headers',
    'admin_host_protection_enabled', 'admin_2fa_required',
    'registration_enabled', 'registration_invite_required',
    'referral_enabled', 'promo_codes_enabled', 'gift_codes_enabled',
    'checkout_code_discounts_enabled', 'payment_autorenewal_enabled',
    'stage1_trial_provisioning_enabled', 'stage1_paid_provisioning_enabled',
    'payments_enabled', 'telegram_stars_enabled', 'log_sanitization_enabled',
    'cookie_secure', 'cookie_domain', 'oauth_token_plaintext_fallback_enabled',
]
for name in fields:
    print(f'{name}={getattr(settings, name, None)}')
for name in ['jwt_secret', 'totp_encryption_key', 'cryptobot_token', 'telegram_bot_token', 'remnawave_token', 'remnawave_webhook_secret', 'oauth_token_encryption_key']:
    value = getattr(settings, name, None)
    if hasattr(value, 'get_secret_value'):
        value = value.get_secret_value()
    print(f'{name}_configured={bool(value)}')
PY"
```

Acceptance:

- production and debug false;
- Swagger false;
- CSRF true;
- rate limit enabled and fail-open false;
- admin host protection true;
- admin 2FA required true;
- critical secrets configured;
- growth/payment/autorenewal switches match the current rollout decision.

---

## 8. Log Privacy Scan

```bash
ssh -i ~/.ssh/MainKey2_private_fixed.pem root@45.87.41.146 '
set -eu
patterns="vless://|/api/sub/[A-Za-z0-9_-]{8,}|Authorization: Bearer|access_token|refresh_token|Crypto-Pay-API-Token|REMNAWAVE_API_TOKEN|TELEGRAM_BOT_TOKEN|875[0-9]{7,}:AA"
for c in \
  cybervpn-stage1-cybervpn-backend-1 \
  cybervpn-stage1-cybervpn-worker-1 \
  cybervpn-stage1-cybervpn-scheduler-1 \
  cybervpn-stage1-cybervpn-telegram-bot-1 \
  cybervpn-stage1-cybervpn-admin-1 \
  cybervpn-stage1-cybervpn-frontend-1
do
  count=$(docker logs --since 24h "$c" 2>&1 | grep -E -c "$patterns" || true)
  echo "$c risky_log_pattern_count=$count"
done'
```

Acceptance:

```text
risky_log_pattern_count=0
```

If any count is non-zero, inspect a redacted sample only. Do not paste raw tokens into docs or chat.

---

## 9. Admin Header Leak Fix

If admin emits `Link` headers with internal origins, apply the edge guard:

```caddy
(admin_proxy) {
  reverse_proxy cybervpn-stage1-cybervpn-admin-1:3000 {
    header_up Host {host}
    header_up X-Real-IP {remote_host}
    header_up X-Forwarded-Host {host}
    header_up X-Forwarded-Proto https
    header_up X-Forwarded-Port 443
    header_down -Link
  }
}
```

Validate and reload:

```bash
docker exec cybervpn-edge-caddy caddy validate --config /etc/caddy/Caddyfile
docker exec cybervpn-edge-caddy caddy reload --config /etc/caddy/Caddyfile
```

Re-test:

```bash
curl -k -sS -D - -o /dev/null https://admin.cyber-vpn.net/ru-RU/login \
  | awk 'BEGIN{IGNORECASE=1;c=0} /^link:/{c++} END{print c}'
```

---

## 10. No-Go Conditions

Do not expand S2 traffic if any of these are true:

1. any high/critical dependency issue is unresolved;
2. gitleaks reports a real leak;
3. bundle scan finds a real secret, raw subscription URL or raw VPN config;
4. `/docs` or `/openapi.json` become public in production;
5. unsigned payment webhooks can create or mutate payment state;
6. webhook paths are blocked by Cloudflare challenge pages;
7. admin 2FA is not required;
8. rate limits fail open in production;
9. logs contain raw configs, raw subscription tokens or auth tokens;
10. paid/referral/promo/gift/autoprolongation flows are public without kill-switch and abuse evidence.

---

## 11. After The Gate

Commit and push evidence GitLab-first, then GitHub mirror.

Next stage:

```text
S2-STAGE-14: GitLab CI/CD And Release Speed
```
