> CyberVPN Launch Program
> Дата evidence: 2026-05-06
> Backlog ID: `S1-FE-003`
> Статус: PASS for local/no-cost frontend implementation. Not a go-live clearance.

# S1-FE-003 Config Delivery UI Evidence

## Purpose

`S1-FE-003` proves that the customer web access surface can deliver the S1 VPN import kit:

- QR code;
- subscription URL action;
- downloadable config file;
- masked on-screen preview;
- no raw subscription URL/config value in visible UI text.

## Implemented Scope

| Area | Result |
|---|---|
| Customer surface | Updated `frontend/src/widgets/server-access/server-access-dashboard.tsx` on the `/servers` dashboard route |
| QR delivery | Added client-only `react-qr-code` rendering for the active delivery payload |
| Subscription URL | Kept explicit copy/open actions, but removed raw URL from visible text and link `href` markup |
| Config file | Added browser-only Blob download as `cybervpn-access-config.txt`; file is generated only after a user click |
| Safe preview | Tightened `maskConfigValue()` so HTTP(S) URLs show only `origin/...` and VPN URIs show scheme plus a short tail |
| Payload fallback | `extractConfigLinks()` now accepts both generated Remnawave config response and `access_delivery_channel.delivery_payload` fallback keys |
| i18n | Added EN/RU copy and English fallback copy for other enabled locales; regenerated 39 locale bundles |

## Raw Value Safety

| Risk | Local control |
|---|---|
| Raw subscription URL visible in page text | Component tests assert `container.textContent` does not contain the raw subscription URL |
| Raw config visible in page text | Component tests assert `container.textContent` does not contain the raw config value |
| Raw URL leaked through static anchor markup | The open action uses `window.open()` from a button instead of rendering the raw URL as visible text or an anchor `href` |
| Raw values logged | No `console.log` or logging path was added; dangerous-pattern/security scans cover the touched files |
| Support screenshots exposing config | The default UI shows masked previews and explicit user actions only |

## Validation Commands

| Check | Command | Result |
|---|---|---|
| Server access model/UI tests | `npm --prefix frontend run test:run -- src/widgets/server-access/__tests__/server-access-model.test.ts src/widgets/server-access/__tests__/server-access-dashboard.test.tsx` | PASS: 2 files, 9 tests |
| Server access lint | `npm --prefix frontend run lint -- src/widgets/server-access/server-access-model.ts src/widgets/server-access/server-access-dashboard.tsx src/widgets/server-access/__tests__/server-access-model.test.ts src/widgets/server-access/__tests__/server-access-dashboard.test.tsx` | PASS |
| Frontend production build | `npm --prefix frontend run build` | PASS: Next.js 16.2.4 production build, TypeScript, 2684 static pages generated |
| i18n bundle generation | Triggered by frontend scripts | PASS: 39 locale bundles generated |
| Frontend dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory through `next` remains tracked because `npm audit fix --force` proposes a breaking Next downgrade |
| Secret-pattern scan over touched runtime/docs files | High-confidence `rg` token/private-key pattern scan excluding historical combined-pack examples | PASS: no matches |
| Dangerous-pattern scan over touched runtime/docs files | `rg` for `eval`, dynamic `Function`, `dangerouslySetInnerHTML`, `innerHTML`, `document.write` and shell execution patterns | PASS: no matches |
| Whitespace/diff check | `git diff --check` over touched runtime/docs files | PASS |

## Documentation / Library References Used

- Next.js official App Router docs: Client Components and lazy loading/dynamic import.
- React official `useState` docs for event-driven state updates.
- `react-qr-code` upstream README for `value`, `size`, `level`, `fgColor` and `bgColor` props.
- Testing Library official `ByRole` docs for accessible component assertions.

## Remaining Go-Live Evidence

Before S1 Controlled Public Beta go-live, this local proof must be repeated on staging/RC:

1. Disposable beta account receives real Remnawave subscription URL/config from staging/prod-like backend.
2. Browser screenshot proves QR/subscription/config actions are visible without exposing raw values.
3. Support/admin screenshots prove raw subscription URLs, QR payloads and raw config files are not exposed by default.
4. Real VPN client import is tested from QR and config/subscription URL.
5. Final RC artifact scan confirms no raw fixture values or secrets are bundled.

## Acceptance Result

`S1-FE-003` is **completed locally** for implementation, i18n, focused tests, lint and production frontend build.

This does **not** clear go-live by itself. It closes the no-cost/local config-delivery UI step and leaves deployed staging/RC evidence open.

Next ID to execute: `S1-FE-009` - i18n critical-path validation. `S1-FE-004`...`S1-FE-008` are completed locally through `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`.
