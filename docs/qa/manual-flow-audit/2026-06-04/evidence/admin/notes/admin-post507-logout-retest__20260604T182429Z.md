# CYBA-458 Post-CYBA-507 Logout Retest

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Related fix: [CYBA-507](/CYBA/issues/CYBA-507)

Timestamp: `20260604T182429Z`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless desktop `1440x1000`, locale `en-EN`.

Overall result: `FAIL`

Invalid-login sanity: `PASS`, login status `401`, saw refresh `false`, alert `Invalid credentials.`.

Login before logout: login `200`, 2FA `200`, session `200`, role `owner/super_admin`, active `true`.

Route before logout: path `/en-EN/dashboard`, heading `OZOXY COMMAND CENTER`, session `200`.

UI logout: response `403`, path after click `/en-EN/dashboard`, sanitized body `{"detail":"CSRF origin validation failed"}`.

Post-logout checks: session `200`, dashboard after logout path `/en-EN/dashboard`, dashboard shows login `false`.

Evidence:

- Invalid login screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST507-LOGIN-NEG-001__admin-panel__anonymous__en-EN__desktop-1440__20260604T182429Z.png`
- Before logout screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST507-LOGOUT-BEFORE-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T182429Z.png`
- After logout screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST507-LOGOUT-AFTER-001__admin-panel__owner__en-EN__desktop-1440__fail__20260604T182429Z.png`
- Dashboard after logout screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST507-DASH-AFTER-LOGOUT-001__admin-panel__owner__en-EN__desktop-1440__fail__20260604T182429Z.png`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post507-logout-retest__20260604T182429Z.json`

Sensitive-data review: PASS - no credentials/TOTP/cookies/tokens/storage/header data stored; screenshots are approved local-stage synthetic UI only.

Context7 docs checked: MCP quota exceeded; fallback ctx7 docs /microsoft/playwright checked Chromium launch, browser context, locators, waitForResponse, waitForURL, and screenshot APIs.
