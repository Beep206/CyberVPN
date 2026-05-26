# My Cabinet API Route Fix

Date: 2026-05-26

## Root Cause

`my.cyber-vpn.net` Caddy `@public_routes` included the `api` route segment. That made `POST /api/v1/auth/login` match the public-site redirect rule before it could reach the backend API proxy.

Browser impact:

- frontend submitted login from `https://my.cyber-vpn.net`;
- edge returned `302 Location: https://cyber-vpn.net/api/v1/auth/login`;
- browser followed the 302 as `GET`;
- backend correctly returned `405 Method Not Allowed` for `GET /api/v1/auth/login`.

## Change

Removed `api` from the `my.cyber-vpn.net` public-route redirect segment list. `/api/v1/*` now reaches backend proxy directly on the cabinet domain.

Production Caddy was restarted after the file update because the first in-place edit created a new inode while the running Docker bind mount still saw the old file.

## Verification

```text
POST https://my.cyber-vpn.net/api/v1/auth/login
Result: 401
Redirect: none
CORS: access-control-allow-origin: https://my.cyber-vpn.net
Body: {"detail":"Invalid credentials."}

OPTIONS https://my.cyber-vpn.net/api/v1/auth/login
Result: 200
Redirect: none
CORS methods: GET, POST, PUT, DELETE, PATCH, OPTIONS

GET https://my.cyber-vpn.net/api/v1/auth/login
Result: 405
Redirect: none
Allow: POST

HTTP/3/QUIC signal:
alt-svc: h3=":443"; ma=86400
```
