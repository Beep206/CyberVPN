> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-04
> Backlog ID: `S1-BE-006`
> Статус: local production-mode CSRF mitigation proof completed; deployed HTTPS/browser evidence remains required before go-live.

# S1-BE-006 CSRF Assessment Evidence

## Purpose

Этот документ фиксирует `S1-BE-006`: cookie-based browser flows must not allow cross-site state-changing requests during S1 Controlled Public Beta.

S1 auth model includes browser cookies for web/admin flows and bearer-style tokens for API/mobile/server-to-server flows. CORS and `SameSite=Lax` cookies reduce risk, but they are not enough as the only mitigation for every unsafe browser request. For S1, production-like environments now require an explicit Origin/Referer guard for cookie-authenticated unsafe methods.

## Source References

OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

FastAPI CORS docs: https://fastapi.tiangolo.com/tutorial/cors/

Starlette middleware docs: https://www.starlette.io/middleware/

MDN Set-Cookie docs: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie

Important rules reflected in this implementation:

- state-changing cookie-auth browser requests need CSRF-specific validation, not only CORS;
- `Origin` is preferred when present; `Referer` can be used as a fallback source-origin signal;
- credentialed CORS must use explicit origins;
- omitted cookie `Domain` creates host-only cookies; broad domain cookies increase cross-subdomain blast radius;
- `SameSite=Lax` helps, but should not be treated as the only control for production state-changing flows.

## Implementation

Added `backend/src/presentation/middleware/csrf.py`.

The middleware:

- runs only when `CSRF_PROTECTION_ENABLED=true`;
- is installed only for `production` and `staging`;
- applies only to unsafe methods: non-`GET`, non-`HEAD`, non-`OPTIONS`, non-`TRACE`;
- applies only when the request carries an auth cookie:
  - `access_token`;
  - `refresh_token`;
  - cookie names ending in `_access_token`;
  - cookie names ending in `_refresh_token`;
- bypasses bearer/API-token requests with an `Authorization` header;
- bypasses requests with no auth cookie, so provider webhooks and other non-cookie server callbacks are not broken by CSRF checks;
- normalizes `Origin` or `Referer` to scheme + host + optional port;
- allows only origins configured in `CORS_ORIGINS`;
- rejects missing, `null`, malformed, unapproved or redirect-only origins with:

```json
{"detail": "CSRF origin validation failed"}
```

Production configuration validation now rejects `CSRF_PROTECTION_ENABLED=false`.

## S1 Allowed Browser Origins

| Origin | Status |
|---|---|
| `https://cyber-vpn.net` | Allowed |
| `https://admin.cyber-vpn.net` | Allowed |
| `https://cyber-vpn.org` | Rejected for API/CORS/CSRF; redirect-only mirror |
| `https://admin.cyber-vpn.org` | Rejected for API/CORS/CSRF; redirect-only admin mirror |

## Local Evidence Summary

| Check | Result |
|---|---|
| Origin normalization strips path/query | Passed |
| `null`, empty and malformed origins rejected by normalization | Passed |
| Auth cookie detection covers legacy and scoped cookie names | Passed |
| Cookie-auth unsafe request without Origin/Referer | `403` |
| Cookie-auth unsafe request from `https://cyber-vpn.net` | Allowed |
| Cookie-auth unsafe request from approved Referer | Allowed |
| Cookie-auth unsafe request from redirect-only `https://cyber-vpn.org` | `403` |
| Bearer request without Origin/Referer | Allowed |
| No-cookie unsafe request without Origin/Referer | Allowed |
| Safe cookie-auth `GET` without Origin/Referer | Allowed |
| Fresh production ASGI app installs `CSRFMiddleware` | Passed |
| Fresh production ASGI app rejects missing-origin cookie POST before routing | `403` |
| Fresh production ASGI app lets approved-origin cookie POST reach routing | `405` on intentionally unsupported route |
| Fresh production ASGI app lets bearer POST reach routing | `405` on intentionally unsupported route |
| Production settings reject `CSRF_PROTECTION_ENABLED=false` | Passed |

## Production-Mode Probe Evidence

Command shape:

```bash
ENVIRONMENT=production \
RATE_LIMIT_ENABLED=false \
CORS_ORIGINS='https://cyber-vpn.net,https://admin.cyber-vpn.net' \
COOKIE_DOMAIN='' \
COOKIE_SECURE=true \
CSRF_PROTECTION_ENABLED=true \
REMNAWAVE_TOKEN='<redacted-production-shaped-value>' \
JWT_SECRET='<redacted-production-shaped-value>' \
CRYPTOBOT_TOKEN='<redacted-production-shaped-value>' \
TOTP_ENCRYPTION_KEY='<redacted-production-shaped-value>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-production-shaped-value>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python '<fresh ASGI CSRF probe>'
```

Observed result:

```json
{
  "approved_origin_status": 405,
  "bearer_status": 405,
  "csrf_middleware_installed": true,
  "missing_origin_status": 403
}
```

Interpretation:

- `missing_origin_status=403` proves CSRF rejects cookie-auth unsafe requests before route handling;
- `approved_origin_status=405` proves an approved origin passed CSRF and reached FastAPI routing;
- `bearer_status=405` proves bearer-style requests are not blocked by the cookie CSRF guard;
- `csrf_middleware_installed=true` proves production-mode app wiring includes the guard.

## Regression Tests

Added:

```text
backend/tests/security/test_stage1_csrf_protection.py
```

Updated:

```text
backend/tests/unit/config/test_settings.py
```

Targeted result:

```text
39 passed in 4.56s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-006` cookie-flow CSRF assessment | Closed locally |
| Production/staging CSRF middleware wiring | Implemented |
| Production misconfiguration guard for disabling CSRF | Implemented |
| `.org` mirror as CSRF-approved API surface | Rejected |
| Bearer/server callback compatibility | Preserved |

## What Remains Open

| Item | Why still open |
|---|---|
| Deployed HTTPS/browser evidence | Requires staging/prod deployment and real auth cookies over HTTPS |
| Deployed `Set-Cookie` proof | Requires real login/refresh/logout flow against staging/prod |
| Host-only vs `cyber-vpn.net` cookie-domain final proof | Host-only is safest; broad domain is allowed but must be intentionally proven if used |
| Route-specific admin origin policy | Current S1 guard allows both public and admin `.net` origins globally; stricter route-origin mapping can be added if admin cookie/domain sharing requires it |
| Token-based double-submit CSRF | Not required for current S1 local mitigation, but can be evaluated later if frontend needs stronger per-request tokens |

## Regeneration Command

```bash
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_csrf_protection.py \
  backend/tests/unit/config/test_settings.py \
  -q --no-cov
```
