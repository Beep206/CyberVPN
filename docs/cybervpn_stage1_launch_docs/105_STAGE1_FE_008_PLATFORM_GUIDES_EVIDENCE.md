# S1-FE-008 Platform Guides Evidence

> Date: 2026-05-07
> Backlog ID: `S1-FE-008`
> Scope: local/no-cost public platform setup guide review for S1 Controlled Public Beta.
> Result: `LOCAL_PASS`

## Purpose

`S1-FE-008` proves that the public setup-guide surface covers the minimum Stage 1 platforms before beta users reach support with connection questions.

The Stage 1 requirement is text guidance for:

- Android.
- iOS.
- Windows.
- macOS.
- Linux.
- Telegram Bot / Telegram Mini App connection flow.

Video guides are not required for Stage 1. Real client-import evidence against generated Remnawave payloads is still a go-live requirement.

## Implemented Scope

- Expanded the public `/devices` content hub from 3 setup guides to 6 S1 platform guides.
- Added macOS, Linux and Telegram Mini App setup guides.
- Kept Android, iOS and Windows setup guides in the same server-rendered content model.
- Updated hub copy from generic "3 setup guides" to "6 S1 setup guides".
- Added EN/RU reviewed copy for the new macOS, Linux and Telegram Mini App guide details.
- Added EN/RU/ZH hub card copy for the new platform cards.
- Preserved the existing `SoftwareApplication` structured-data path for each guide.
- Added tests proving the exact required guide slug set is present.
- Added tests proving the guide copy avoids unsupported S1 promises for App Store, Google Play, automatic renewal and native desktop release.

## Platform Guide Matrix

| Platform | Route | S1 stance |
|---|---|---|
| Android | `/devices/android-vpn-setup` | Existing guide retained; compatible client, fallback route and support path remain explicit |
| iOS | `/devices/ios-vpn-setup` | Existing guide retained; mobile onboarding and route-degradation support remain explicit |
| Windows | `/devices/windows-vpn-setup` | Existing guide retained; desktop profile packaging and recovery path remain explicit |
| macOS | `/devices/macos-vpn-setup` | New guide; compatible-client setup, no native desktop app promise inside S1 |
| Linux | `/devices/linux-vpn-setup` | New guide; separates user access config from operator infrastructure and raw secrets |
| Telegram Mini App | `/devices/telegram-mini-app-vpn-setup` | New guide; Telegram onboarding to VPN-ready config handoff, with safe support escalation |

## Safety Review

The guides intentionally state:

- use QR, subscription URL or config file only from trusted logged-in CyberVPN surfaces;
- do not paste raw subscription URLs, QR payloads, private keys or full config files into chats/support messages;
- S1 uses compatible clients and does not require native CyberVPN mobile/desktop app releases;
- Telegram Stars can be available only in Telegram paid flow after evidence;
- paid-but-no-access / orphan payment cases must be escalated before exceeding 24 hours;
- support diagnostics should use account identifiers, visible error text, timestamps, client/device information and provider IDs where available, not secrets.

## Files Touched

- `frontend/src/content/seo/devices.ts`
- `frontend/src/content/seo/market-localization.ts`
- `frontend/src/content/seo/market-detail-localization.ts`
- `frontend/src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx`
- `docs/cybervpn_stage1_launch_docs/105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/00_INDEX.md`
- `docs/cybervpn_stage1_launch_docs/06_STAGE1_IMPLEMENTATION_BACKLOG.md`
- `docs/cybervpn_stage1_launch_docs/11_STAGE1_REVIEW_CHECKLIST.md`
- `docs/cybervpn_stage1_launch_docs/21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md`
- `docs/cybervpn_stage1_launch_docs/77_STAGE1_REMAINING_WORK_TO_LAUNCH.md`
- `docs/cybervpn_stage1_launch_docs/91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`
- `docs/cybervpn_stage1_launch_docs/99_STAGE1_FE_002_DASHBOARD_STATES_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/101_STAGE1_FE_004_DEVICES_PAGE_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/102_STAGE1_FE_005_WALLET_PAGE_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/103_STAGE1_FE_006_GROWTH_UI_GATES_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/104_STAGE1_FE_007_OPERATOR_SURFACE_AUDIT_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/evidence_pack/stage1/frontend/README.md`
- `docs/cybervpn_stage1_launch_docs/CYBERVPN_STAGE1_LAUNCH_PACK_COMBINED.md`

## Local Verification

| Check | Command | Result |
|---|---|---|
| Focused device-guide and sitemap tests | `npm --prefix frontend run test:run -- 'src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx' 'src/app/__tests__/sitemap.test.ts'` | `PASS`: 2 files, 6 tests |
| Focused lint | `npm --prefix frontend run lint -- src/content/seo/devices.ts src/content/seo/market-localization.ts src/content/seo/market-detail-localization.ts 'src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx'` | `PASS` |
| Production build | `npm --prefix frontend run build` | `PASS`: Next.js 16.2.4, Cache Components enabled |
| Production dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | `PASS` for high/critical. Existing low/moderate dependency advisories remain tracked outside this task. |
| Secret scan | `rg` high-confidence secret patterns over touched frontend/docs files | `PASS`: no matches |
| Static dangerous-pattern scan | `rg` for `dangerouslySetInnerHTML`, `eval`, `new Function`, `document.write`, shell/process and obvious SQL template patterns over touched runtime files | `PASS`: no matches |
| Whitespace/diff check | `git diff --check` over touched runtime/docs files | `PASS` |
| Running containers | `docker ps --format '{{.Names}}\t{{.Status}}'` | `PASS`: no running containers reported |

## Library Documentation Checked

- Official Next.js project-structure docs were checked for App Router route/content organization before editing the public `/devices` content surface.

## Remaining Go-Live Evidence

This local evidence does not clear go-live by itself. Before S1 go-live, attach:

1. Deployed staging/RC screenshots for `/devices` and all six `/devices/...` detail pages.
2. Real generated Remnawave payload import proof for at least the S1-supported client stack per platform.
3. Redacted QR/subscription URL/config delivery proof from the web cabinet and Telegram Mini App.
4. Support transcript proving users are not asked to share raw configs, QR payloads or subscription URLs.
5. `S1-FE-009` i18n critical-path validation for the enabled S1 launch locales.

## Acceptance Result

`S1-FE-008` is **completed locally** for platform-guide coverage, reviewed EN/RU setup copy, safe config-delivery wording, focused tests, lint and production frontend build.

This closes the no-cost/local platform-guide step. Deployed staging/RC screenshots and real client-import evidence remain open go-live requirements.

Next ID to execute: `S1-FE-009` - i18n critical-path validation.
