> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-04
> Backlog ID: `S1-BE-005`
> Статус: local production-mode CORS/cookie config proof completed; deployed staging/prod domain/TLS/ingress evidence remains required before go-live.

# S1-BE-005 CORS and Cookie Config Evidence

## Purpose

Этот документ фиксирует `S1-BE-005`: browser origins and auth-cookie settings must match the selected S1 domains.

Owner decisions:

- public primary: `https://cyber-vpn.net`;
- public mirror: `https://cyber-vpn.org` redirects to primary;
- admin primary: `https://admin.cyber-vpn.net`;
- admin mirror: `https://admin.cyber-vpn.org` redirects to primary admin.

S1 rule: `.org` domains must not become independent API/CORS/auth-cookie surfaces. They are redirect-only until a later decision explicitly approves a separate mirror auth surface.

## Implementation

Added production validation in `backend/src/config/settings.py`:

- production `CORS_ORIGINS` must be non-empty;
- `CORS_ORIGINS='*'` is rejected in production;
- production CORS origins must use `https`;
- S1 production CORS origins are limited to:
  - `https://cyber-vpn.net`;
  - `https://admin.cyber-vpn.net`;
- `https://cyber-vpn.org` and `https://admin.cyber-vpn.org` are rejected as redirect-only origins;
- production `COOKIE_SECURE=false` is rejected;
- production `COOKIE_DOMAIN` is limited to:
  - empty value for host-only cookies; or
  - `cyber-vpn.net` if intentional subdomain sharing is required;
- leading dot in `COOKIE_DOMAIN=.cyber-vpn.net` is normalized to `cyber-vpn.net`.

Updated `backend/.env.example` with S1 production CORS/cookie guidance.

## Source References

FastAPI CORS docs: https://fastapi.tiangolo.com/tutorial/cors/

Starlette CORSMiddleware docs: https://www.starlette.io/middleware/

MDN Set-Cookie docs: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie

Important rules reflected in this implementation:

- credentialed CORS must use explicit origins, not wildcard;
- cookies using `SameSite=None` require `Secure`; CyberVPN auth cookies currently use `SameSite=Lax` and `Secure=true` by default;
- cookie `Domain` broadens cookie availability to subdomains; omitted Domain creates host-only cookies;
- `__Host-` style host-only behavior is the safest long-term shape if cookie names are migrated later.

## Evidence Summary

| Check | Result |
|---|---|
| Settings validation for approved S1 origins | Passed |
| Production wildcard CORS rejected | Passed |
| Production `.org` redirect-only CORS rejected | Passed |
| Production unknown CORS origin rejected | Passed |
| Production `http://` CORS rejected | Passed |
| CORS origin with path/query rejected | Passed |
| Host-only production cookie domain accepted | Passed |
| `cyber-vpn.net` production cookie domain accepted | Passed |
| `.cyber-vpn.net` normalized to `cyber-vpn.net` | Passed |
| `cyber-vpn.org` cookie domain rejected | Passed |
| `COOKIE_SECURE=false` rejected in production | Passed |
| Fresh production ASGI preflight allows only approved `.net` origins | Passed |

## Local ASGI CORS Evidence

Command shape:

```bash
ENVIRONMENT=production \
CORS_ORIGINS='https://cyber-vpn.net,https://admin.cyber-vpn.net' \
COOKIE_DOMAIN='cyber-vpn.net' \
COOKIE_SECURE=true \
REMNAWAVE_TOKEN='<redacted-production-shaped-value>' \
JWT_SECRET='<redacted-production-shaped-value>' \
CRYPTOBOT_TOKEN='<redacted-production-shaped-value>' \
TOTP_ENCRYPTION_KEY='<redacted-production-shaped-value>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-production-shaped-value>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python '<fresh ASGI CORS probe>'
```

Observed result:

```json
{
  "cookie_domain": "cyber-vpn.net",
  "cookie_secure": true,
  "cors_origins": [
    "https://cyber-vpn.net",
    "https://admin.cyber-vpn.net"
  ],
  "preflight": {
    "https://admin.cyber-vpn.net": {
      "allow_credentials": "true",
      "allow_origin": "https://admin.cyber-vpn.net",
      "status": 200
    },
    "https://cyber-vpn.net": {
      "allow_credentials": "true",
      "allow_origin": "https://cyber-vpn.net",
      "status": 200
    },
    "https://cyber-vpn.org": {
      "allow_credentials": "true",
      "allow_origin": null,
      "status": 400
    }
  }
}
```

Note: failed `.org` preflight still includes `access-control-allow-credentials: true` from middleware defaults, but has no `access-control-allow-origin` and returns `400`, so browsers do not accept it as an approved credentialed origin.

## Rejected Misconfiguration Evidence

Wildcard production CORS:

```text
ENVIRONMENT=production CORS_ORIGINS='*' ...
ValidationError
1 validation error for Settings
cors_origins
```

Dedicated tests cover the specific rejection messages for wildcard, `.org`, unknown origin, `http://`, path-bearing origin, `COOKIE_DOMAIN=cyber-vpn.org` and `COOKIE_SECURE=false`.

## Regression Tests

Updated:

```text
backend/tests/unit/config/test_settings.py
```

Added:

```text
backend/tests/security/test_stage1_cors_cookie_config.py
```

Targeted result:

```text
25 passed in 4.68s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-005` local CORS/cookie config proof | Closed locally |
| Wildcard CORS in production | Mitigated |
| `.org` mirror becoming independent API/CORS surface | Mitigated in backend config |
| Insecure production cookies | Mitigated in backend config |

## What Remains Open

| Item | Why still open |
|---|---|
| Deployed DNS/TLS/redirect evidence | Requires real domains and ingress |
| Deployed CORS curl evidence | Requires staging/prod deployment |
| Deployed cookie `Set-Cookie` evidence | Requires real auth flow over HTTPS |
| Final decision on host-only vs `.cyber-vpn.net` cookie domain | Both are allowed; host-only is safest unless subdomain sharing is required |
| CSRF assessment | Local proof completed in `33_STAGE1_BE_006_CSRF_ASSESSMENT_EVIDENCE.md`; deployed HTTPS/browser evidence remains open |

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
  backend/tests/unit/config/test_settings.py \
  backend/tests/security/test_stage1_cors_cookie_config.py \
  -q --no-cov
```
