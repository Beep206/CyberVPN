# Partner portal findings

Дата: `2026-06-04`

Подробный partner findings log ведется здесь:

- `docs/qa/manual-flow-audit/2026-06-04/partner-findings.md`

## Current Result

- `MF-PART-001` protected-route `SYSTEM FAILURE` ранее подтверждён как исправленный в local-dev portal preview.
- `MF-PART-002` подтверждён исправленным в [CYBA-523](/CYBA/issues/CYBA-523) через обязательный path-matched cookie probe.
- Более ранний ретест [CYBA-520](/CYBA/issues/CYBA-520) после [CYBA-519](/CYBA/issues/CYBA-519) падал, потому что cookie probe не доказывал cookies с `Path=/api`:
  - `POST /api/v1/auth/login -> 200`, `requires_2fa=true`
  - `POST /api/auth/2fa/pending -> 204`
  - `POST /api/auth/2fa/complete -> 401`
  - `GET /api/v1/auth/session -> 401`
  - cookies after complete: `[]`
  - protected partner routes redirect to login
- Последний ретест [CYBA-523](/CYBA/issues/CYBA-523):
  - `POST /api/auth/2fa/complete -> 200`, `redirect_to=/en-EN/dashboard`
  - `GET /api/v1/auth/session -> 200`, `auth_realm_key=partner`
  - root-origin cookie probe после complete: `[]`
  - path-matched probe под `/api/v1/auth/session`: `partner_access_token`, `partner_refresh_token`, обе `Path=/api`
  - protected partner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team` render без login redirect
- Canonical partner dashboard data, codes, markup boundaries, client attribution, finance, earnings, balances, withdrawals и cross-surface attribution checks остаются заблокированы вне этого ретеста под `MF-PART-003`.

## Evidence

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`
- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T202139Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T210730Z.png`
- Bug packet: `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/MF-PART-002.md`

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option.
