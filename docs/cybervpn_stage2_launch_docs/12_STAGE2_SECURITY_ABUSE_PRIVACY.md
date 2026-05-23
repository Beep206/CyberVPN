# Stage 2 Security, Abuse, And Privacy Gate

**Stage:** `S2-STAGE-13`
**Status:** Passed with controlled gaps
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. Purpose

Stage 2 opens CyberVPN from controlled beta toward Public Release 1.0. The security goal is practical: no known high/critical issue should block opening, abuse paths must be gated, and privacy-sensitive data must not leak through bundles, logs, support views, evidence or public headers.

This gate covers the customer-facing rented runtime and the home operations runtime:

- `cyber-vpn.net` public frontend;
- `api.cyber-vpn.net` backend API and webhook routes;
- `admin.cyber-vpn.net` admin/support surface;
- `cyber-vpn.org` VPN node/subscription-only routes;
- Telegram Bot and Mini App runtime;
- worker/scheduler queues;
- home GitLab/observability evidence path.

---

## 2. Security Baseline Decision

S2 can continue with controlled public expansion if these conditions remain true:

1. high/critical dependency audit is clean;
2. secrets scan is clean;
3. frontend/admin production bundles do not contain runtime secrets, raw VPN configs or raw subscription URLs;
4. production API docs are not publicly exposed;
5. payment and Remnawave webhooks reject unsigned/invalid requests without Cloudflare challenge HTML;
6. backend rate limits fail closed in production;
7. admin access requires the admin host and `ADMIN_2FA_REQUIRED=true`;
8. registration, referral, promo, gift and autoprolongation are controlled by kill switches until their own enablement evidence is complete;
9. logs do not contain raw `vless://`, subscription URL tokens, bearer tokens, refresh/access tokens, payment API tokens or Telegram bot tokens;
10. public evidence files remain redacted.

---

## 3. Production Runtime Controls

| Control | Production observation | S2 status |
|---|---|---|
| Environment | `environment=production`, `debug=False` | Pass |
| Swagger/OpenAPI | `swagger_enabled=False`; `/docs` and `/openapi.json` return `404` | Pass |
| CSRF | `csrf_protection_enabled=True` | Pass |
| Rate limits | `rate_limit_enabled=True`, `rate_limit_fail_open=False` | Pass |
| Proxy trust | `trust_proxy_headers=True` behind Caddy/Cloudflare | Pass |
| Admin host guard | `admin_host_protection_enabled=True` | Pass |
| Admin 2FA requirement | `admin_2fa_required=True` | Pass |
| Registration | `registration_enabled=False`, invite required | Controlled |
| Trial provisioning | `stage1_trial_provisioning_enabled=True` | Pass for current trial beta |
| Paid provisioning | `stage1_paid_provisioning_enabled=False` | Controlled |
| Payments | `payments_enabled=False`, Telegram Stars configured | Controlled until paid reopen |
| Referral | `referral_enabled=False` | Controlled |
| Promo codes | `promo_codes_enabled=False` | Controlled |
| Gift codes | `gift_codes_enabled=False` | Controlled |
| Checkout code discounts | `checkout_code_discounts_enabled=False` | Controlled |
| Autoprolongation | `payment_autorenewal_enabled=False` | Controlled |
| Cookie posture | `cookie_secure=True`, `cookie_domain=cyber-vpn.net` | Pass |
| Log sanitization | `log_sanitization_enabled=True` | Pass |
| OAuth provider scope | `google,github` only | Pass |
| OAuth token encryption | `OAUTH_TOKEN_ENCRYPTION_KEY` configured | Pass |

---

## 4. Public Edge And Header Findings

Observed public routes:

| Route | Observation | S2 status |
|---|---|---|
| `https://cyber-vpn.net/ru-RU` | `200`, HSTS, `alt-svc: h3`, no secret leak | Pass |
| `https://api.cyber-vpn.net/health` | `200`, API security headers, no-store | Pass |
| `https://api.cyber-vpn.net/docs` | `404` | Pass |
| `https://api.cyber-vpn.net/openapi.json` | `404` | Pass |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200`, HSTS, `alt-svc: h3`, admin Link header stripped | Pass |
| `https://cyber-vpn.org/api/sub/<redacted>` | Remnawave subscription route only, invalid token returns `404` JSON | Pass |
| `https://cyber-vpn.org/` | Redirects to `https://cyber-vpn.net/` | Pass |
| `https://admin.cyber-vpn.org/` | Redirects to `https://admin.cyber-vpn.net/` | Pass |

During this gate an admin response hygiene issue was found and fixed:

```text
Issue: admin.cyber-vpn.net emitted a public Link header containing internal 127.0.0.1 origin fragments.
Impact: no secret disclosure, but public internal-origin leakage is not acceptable for S2 hygiene.
Fix: admin root metadata is private/noindex and Caddy strips downstream Link headers on admin responses.
Evidence: link_count=0 after Caddy reload; alt-svc h3 remains present.
```

The repository deployment snippets now keep this edge behavior:

```text
infra/deploy/stage1/Caddyfile.stage1.snippet
infra/deploy/stage1/Caddyfile.system-stage1.snippet
```

---

## 5. Dependency And Secret Scan Results

Artifact directory:

```text
.tmp/s2-stage13-security/
```

This directory is local evidence and is not committed.

| Surface | Tool | Result |
|---|---|---|
| Git tree secrets | `gitleaks` via `scripts/security/scan-secrets.sh` | `no leaks found` |
| Root npm workspace | `npm audit --audit-level=high` | `0 high`, `0 critical`, `4 moderate` |
| Admin npm workspace | `npm audit --audit-level=high` | `0 high`, `0 critical`, `3 moderate` |
| Frontend npm workspace | `npm audit --audit-level=high` | `0 high`, `0 critical`, `3 moderate` |
| Partner npm workspace | `npm audit --audit-level=high` | `0 high`, `0 critical`, `3 moderate` |
| Backend Python | `pip-audit` | `No known vulnerabilities found` |
| Telegram Bot Python | `pip-audit` | `No known vulnerabilities found` |
| Task Worker Python | `pip-audit` | `No known vulnerabilities found` after dependency fix |

Dependency blocker closed in this gate:

```text
services/task-worker:
idna      3.12  -> 3.16
starlette 1.0.0 -> 1.0.1
urllib3   2.6.3 -> 2.7.0
```

The remaining npm findings are moderate severity and do not block S2, but they must stay visible in the dependency audit output.

---

## 6. Bundle And Runtime Leak Scan

Production build scans covered:

```text
frontend/.next/static
frontend/.next/server/app
admin/.next/static
admin/.next/server/app
```

No matches were found for:

- Telegram bot tokens;
- GitHub/GitLab tokens;
- private keys;
- database URLs;
- Redis URLs;
- JWT/TOTP/Remnawave/payment secret env names;
- raw `vless://` configs;
- raw `https://api.cyber-vpn.net/api/sub/<token>` URLs;
- raw `https://cyber-vpn.org/api/sub/<token>` URLs.

Build sizes observed:

```text
frontend/.next/static  7.1M
frontend/.next/server  1.2G
admin/.next/static     5.6M
admin/.next/server     117M
```

---

## 7. Webhook And Abuse Controls

| Area | Evidence | S2 decision |
|---|---|---|
| CryptoBot webhook | Unsigned JSON `POST /api/v1/webhooks/cryptobot` returns `401 {"detail":"Invalid webhook signature"}` | Pass |
| Remnawave webhook | Invalid JSON `POST /api/v1/webhooks/remnawave` returns JSON `{"status":"invalid_signature"}` and no HTML challenge | Pass |
| Webhook challenge avoidance | Both webhook paths return JSON from app, not Cloudflare challenge pages | Pass |
| Idempotency | Backend security suite covers webhook idempotency and terminal status handling | Pass |
| Auth abuse | Rate-limit tests cover auth buckets and production fail-closed behavior | Pass |
| Trial abuse | Trial provisioning and policy tests pass | Pass |
| Referral/promo/gift abuse | Kill switches are off in current production; public enablement requires separate evidence | Controlled |
| Autoprolongation abuse | Kill switch is off; enable only after consent/cancel/retry/refund/webhook evidence | Controlled |

Growth flows are allowed for S2 implementation, but not allowed to become public until the owner has:

1. kill switch evidence;
2. duplicate-subject/self-referral tests;
3. redemption idempotency tests;
4. refund/reversal behavior;
5. support reversal workflow;
6. legal copy in public pages;
7. observability alerts and audit trail.

---

## 8. Log Privacy Result

Last-24h production container log scan returned zero matches for risky payload patterns:

```text
cybervpn-stage1-cybervpn-backend-1       risky_log_pattern_count=0
cybervpn-stage1-cybervpn-worker-1        risky_log_pattern_count=0
cybervpn-stage1-cybervpn-scheduler-1     risky_log_pattern_count=0
cybervpn-stage1-cybervpn-telegram-bot-1  risky_log_pattern_count=0
cybervpn-stage1-cybervpn-admin-1         risky_log_pattern_count=0
cybervpn-stage1-cybervpn-frontend-1      risky_log_pattern_count=0
```

Patterns checked:

- `vless://`;
- `/api/sub/<token>`;
- `Authorization: Bearer`;
- `access_token`;
- `refresh_token`;
- payment API token names;
- Remnawave/Telegram secret names;
- Telegram bot token shape.

No raw VPN credentials or raw subscription URL tokens were observed in production logs during this gate.

---

## 9. Firewall And Network Boundary

Production app server firewall:

```text
Default: deny incoming, allow outgoing, deny routed
Allowed: 22/tcp, 80/tcp, 443/tcp, 443/udp
```

Observed listening boundary:

```text
0.0.0.0:80/tcp
0.0.0.0:443/tcp
0.0.0.0:443/udp
127.0.0.1:13000 frontend
127.0.0.1:13001 admin
127.0.0.1:13005 Remnawave control/subscription proxy path
127.0.0.1:18080 backend
127.0.0.1:18088 Telegram bot
```

PostgreSQL, Valkey, backend, admin, frontend, bot and Remnawave app ports are not directly public.

DNS boundary:

```text
cyber-vpn.net / api / admin -> Cloudflare proxied
cyber-vpn.org / admin.cyber-vpn.org -> direct A to prod-app-1 for node/subscription and redirects
```

The `.org` zone remains node/subscription-only, not a customer website mirror.

---

## 10. Support Privacy Boundaries

Support/admin users must not paste or request:

- raw VPN configs;
- raw subscription URLs with live tokens;
- payment provider secret payloads;
- Telegram bot tokens;
- JWT or refresh tokens;
- TOTP secrets;
- database dumps;
- unredacted screenshots containing provider credentials.

Allowed support evidence:

- user ID or Telegram username;
- plan name;
- subscription status;
- provider name;
- redacted payment ID;
- redacted subscription token prefix/suffix if required;
- error code;
- timestamp;
- support action and audit event ID.

Privacy requests remain manual but documented through the public privacy/delete-account path and support contacts. That is acceptable for S2 as long as support does not expose secrets in Telegram/chat/evidence.

---

## 11. Controlled Gaps

| Gap | Risk | S2 decision | Follow-up |
|---|---|---|---|
| NPM moderate vulnerabilities remain | Dependency hygiene | Accept for S2 because high/critical gate is clean | Keep audit in CI and upgrade when upstream fixes are available |
| Frontend/admin CSP is `Report-Only` and allows inline/eval patterns | Browser hardening | Accept for S2 because current Next/React/Sentry build needs staged tightening | Move toward enforced CSP after compatibility testing |
| Cloudflare WAF dashboard was not API-verified from repo | Evidence completeness | Accept with current Caddy/backend fail-closed rate limits and public-route probes | Add Cloudflare API/token-based evidence or owner screenshot before larger paid traffic |
| OAuth plaintext fallback flag remains enabled | Legacy compatibility | Accept because token encryption key is configured and new writes are encrypted | Disable fallback after confirming no legacy plaintext OAuth token rows |
| Paid/referral/promo/gift/autoprolongation public flows are disabled | Feature readiness | Accept because disabled flows cannot be abused publicly | Re-run this gate when each flow is enabled |

None of these are high/critical blockers for current S2 preparation.

---

## 12. Exit Criteria

`S2-STAGE-13` is accepted when:

1. dependency audit has no high/critical blocker;
2. secret scan passes;
3. bundle/env leak scan passes for frontend and admin;
4. production API docs are closed;
5. webhook routes reject invalid requests and are not blocked by challenge pages;
6. admin public header leakage is fixed;
7. production runtime flags show fail-closed rate limits, 2FA requirement and kill switches;
8. log privacy scan has zero risky payload matches;
9. known gaps are explicitly carried forward.

Result:

```text
PASS_WITH_CONTROLLED_GAPS
```

Next stage:

```text
S2-STAGE-14: GitLab CI/CD And Release Speed
```
