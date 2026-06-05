# MF-PART-001

Related issue: [CYBA-457](/CYBA/issues/CYBA-457)

Follow-up issue: [CYBA-464](/CYBA/issues/CYBA-464)

Evidence index rows: `EV-CYBA-457-PART-001` through `EV-CYBA-457-PART-006`

## Summary

Protected partner portal routes crash into `SYSTEM FAILURE` before route guard or business UI renders.

## Classification

- Type: `bug`
- Severity: `P1`
- Surface: `partner-portal`
- Flow: partner protected route access, codes, finance, role boundary
- Environment: local partner dev `http://127.0.0.1:3002`; approved local-stage backend `http://127.0.0.1:18080`
- Browser/channel: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- User role/state: anonymous; `DEV_BYPASS_AUTH=true` synthetic partner owner/active; `DEV_BYPASS_AUTH=true` synthetic analyst/active
- Test data fixture: synthetic local `ozoxy-partner-portal-state:v1`; no production/customer/payment data

## Steps To Reproduce

1. Start partner dev with:
   `NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 HOST=127.0.0.1 PORT=3002 NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3002 npm run dev -w partner`
2. Open `http://127.0.0.1:3002/en-EN/login`.
3. Open `http://127.0.0.1:3002/en-EN/dashboard` without a session.
4. Set `DEV_BYPASS_AUTH=true` and a synthetic local partner state.
5. Open `http://127.0.0.1:3002/en-EN/codes`.
6. Open `http://127.0.0.1:3002/en-EN/finance`.
7. Open `http://127.0.0.1:3002/en-EN/team` with synthetic `workspaceRole=analyst`.

## Expected Result

Anonymous protected routes should redirect to login or render a stable auth/access gate. Synthetic local dev-bypass states should render partner shell routes enough to verify access-state, empty-state, and route-boundary behavior. Backend/API failures should not crash the whole route tree.

## Actual Result

`/dashboard`, `/codes`, `/finance`, and `/team` render `SYSTEM FAILURE`. Console notes include `No QueryClient set, use QueryClientProvider to set one`. Network notes include `500 /api/v1/auth/session`; the `codes` route also records `500 /api/v1/partner-workspaces/me`, `500 /api/v1/partner-session/bootstrap`, and `500 /api/v1/partner-notifications/preferences`.

Additional environment finding: `partner/next.config.ts` rewrites `/api/v1/:path*` to `http://localhost:8000/api/v1/:path*`, but the approved local-stage backend for this QA run is `http://127.0.0.1:18080`, and no process was listening on `localhost:8000`.

## Sanitized Evidence

- JSON summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-CAPTURE-RERUN-DEVENV__partner-portal__manual-qa__20260604T160419Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-AUTH-002__partner-portal__anonymous__en-EN__desktop-1440__fail__20260604T160406Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-CODES-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__fail__20260604T160410Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-FIN-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__fail__20260604T160415Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-ROLE-001__partner-portal__dev-bypass-analyst-active__en-EN__desktop-1440__fail__20260604T160419Z.png`
- Console notes: stored in JSON summary.
- Network notes: stored in JSON summary.

## Sensitive-Data Review

Result: `PASS - no sensitive data present`

Reviewer: `qa-partner-portal-manual`

Notes: Screenshots/JSON contain no cookies, storage state, JWT, refresh tokens, payment secrets, production PII, or real Telegram initData. Synthetic data uses masked labels and example/test values only.

## Docs Evidence Line

Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Playwright navigation/screenshots and TanStack Query provider/devtools docs.

## Owner And Next Action

Owner: `Prism Admin Partner Frontend Engineer`

Next action: fix or document/start the local backend/proxy path required by partner browser `/api/v1/*`, and ensure protected partner routes handle missing/failed auth/bootstrap without global `SYSTEM FAILURE`.
