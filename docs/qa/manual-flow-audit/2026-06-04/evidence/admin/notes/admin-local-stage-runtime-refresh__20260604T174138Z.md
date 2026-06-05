# Admin local-stage runtime refresh - CYBA-498

Issue: [CYBA-498](/CYBA/issues/CYBA-498)

Date: `2026-06-04T17:41:38Z`

Environment:

- Admin local-stage: `http://127.0.0.1:13001`
- Container: `cybervpn-stage1-cybervpn-admin-1`
- Image tag refreshed: `local/cybervpn-admin:stage1-beta-rc.2`
- Backend origin used by runtime: `http://cybervpn-backend:8000`

## Action

- Confirmed the running admin container was stale:
  - `admin/src/app/api/v1/[...path]/route.ts` was missing inside the running container.
  - `local/cybervpn-admin:stage1-beta-rc.1` and `local/cybervpn-admin:stage1-beta-rc.2` pointed to the same three-week-old image ID.
- Rebuilt only the admin local-stage image from the current workspace with `infra/deploy/stage1/Dockerfile.next-workspace`.
- Preserved the existing container env/ports/networks without reading protected env files:
  - created a temporary source container from the fresh image,
  - copied built `/app` files into the existing stopped admin container,
  - fixed `.next` ownership for the runtime user,
  - restarted the same `cybervpn-stage1-cybervpn-admin-1` container.

No backend, payment, admin permission, VPN provisioning, Remnawave, or production deployment changes were made.

## Verification

- Fresh image contains the route handler:
  - `route-present`
  - `route-built`
- Runtime health:
  - `GET http://127.0.0.1:13001/en-EN/login -> 200`
  - `cybervpn-stage1-cybervpn-admin-1` is `healthy`
- Route handler activation:
  - `GET http://127.0.0.1:13001/api/v1/auth/session -> 401`
  - response now includes Next route headers plus upstream backend headers, confirming the Next route handler is active before forwarding.
- Browser invalid-login smoke:
  - result: `pass`
  - events:
    - `POST /api/v1/auth/login -> 401`
  - refresh count: `0`
- Targeted tests:
  - `npm run test:run -w admin -- src/lib/api/__tests__/auth.test.ts 'src/app/api/v1/[...path]/route.test.ts'`
  - result: `2 passed`, `87 passed`
- Scoped lint:
  - `npm run lint -w admin -- src/lib/api/client.ts 'src/app/api/v1/[...path]/route.ts'`
  - result: passed
- Docker build:
  - `next build` passed and listed `ƒ /api/v1/[...path]`.

## QA Handoff

QA can retest [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484), and the remaining authenticated admin read-only flows against `http://127.0.0.1:13001`.

Expected retest baseline:

- Invalid login should not call `/api/v1/auth/refresh` after `/api/v1/auth/login -> 401`.
- `/api/v1/*` calls on `13001` should pass through the admin Next route handler before reaching the backend.
- Synthetic admin authenticated flows still require QA-owned protected fixture credentials; they were not read or stored during this heartbeat.

## Sensitive-Data Review

PASS - no real customer/payment data, cookies, JWTs, refresh tokens, passwords, TOTP values, HAR, traces, screenshots, or `.env` values were stored in this note.

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /vercel/next.js/v16.2.2` checked route handlers, async params, proxy/rewrite patterns, and route-handler proxying.
