# 56. Stage 1 Evidence - S1-TG-004 Mini App Cabinet Routes

Date: 2026-05-04

Backlog ID: `S1-TG-004`

Status: completed locally for Mini App cabinet route smoke and screenshots; real Telegram client, real `initData` auth/linking and deployed staging evidence remain required before S1 go-live.

## Objective

Prove that the Stage 1 Telegram Mini App can operate as a light customer cabinet across the required B2C routes:

- home;
- plans;
- payments;
- devices;
- profile;
- wallet.

This evidence verifies the real frontend routes in a mobile viewport with deterministic local API fixtures. It does not claim that Telegram identity/linking is production-ready; that is the scope of `S1-TG-005`.

## Official Docs Checked

| Surface | Source |
|---|---|
| Telegram Mini Apps launch/runtime expectations | https://core.telegram.org/bots/webapps |
| Playwright Python screenshot capture | https://playwright.dev/python/docs/screenshots |

## Implemented Evidence Harness

Repository changes:

- `scripts/testing/s1_tg_004_miniapp_mock_api.py`
  - serves local, non-secret JSON fixtures for Mini App bootstrap, offers, config, orders, devices, wallet, 2FA, antiphishing and partner dashboard endpoints;
  - uses no production credentials, provider tokens, Telegram bot tokens or Remnawave secrets;
  - exposes only local smoke data for repeatable screenshot evidence.
- `scripts/testing/s1_tg_004_miniapp_browser_smoke.py`
  - opens six Mini App routes in a 390x844 mobile viewport;
  - injects a safe Telegram WebApp runtime with empty `initData`, so Mini App theming works while auth/linking remains out of scope;
  - asserts route-specific visible text;
  - captures full-page screenshots;
  - writes route text dumps and a machine-readable summary.

No frontend runtime code was changed for this task.

## Route Evidence Matrix

| Route | Required proof text | Screenshot |
|---|---|---|
| `/en-EN/miniapp/home` | `Subscription Active`, `Plus Beta`, `VPN Configuration`, `Usage Statistics` | `evidence/s1-tg-004/screenshots/home.png` |
| `/en-EN/miniapp/plans` | `Choose Your Plan`, `Basic`, `Plus`, `180 days` | `evidence/s1-tg-004/screenshots/plans.png` |
| `/en-EN/miniapp/payments` | `Payment History`, `Plus Beta 30 days`, `$14.99` | `evidence/s1-tg-004/screenshots/payments.png` |
| `/en-EN/miniapp/devices` | `Active Devices`, `Chrome on Windows`, `Current` | `evidence/s1-tg-004/screenshots/devices.png` |
| `/en-EN/miniapp/profile` | `s1_tg_004`, `Security`, `Payment History`, `Partner Dashboard` | `evidence/s1-tg-004/screenshots/profile.png` |
| `/en-EN/miniapp/wallet` | `Wallet Balance`, `$27.50`, `Transaction History`, `S1 local wallet deposit` | `evidence/s1-tg-004/screenshots/wallet.png` |

Additional artifacts:

- `docs/cybervpn_stage1_launch_docs/evidence/s1-tg-004/summary.json`;
- `docs/cybervpn_stage1_launch_docs/evidence/s1-tg-004/route-text/*.txt`.

## Local Evidence Commands

Python syntax check:

```bash
python -m py_compile scripts/testing/s1_tg_004_miniapp_mock_api.py scripts/testing/s1_tg_004_miniapp_browser_smoke.py
```

Result:

```text
passed with no output
```

Mini App route screenshot smoke:

```bash
python /home/beep/.codex/skills/webapp-testing/scripts/with_server.py \
  --server "python scripts/testing/s1_tg_004_miniapp_mock_api.py --host 0.0.0.0 --port 8000" \
  --port 8000 \
  --server "bash -lc 'cd frontend && NEXT_TELEMETRY_DISABLED=1 NEXT_DIST_DIR=.next-s1-tg-004 node node_modules/next/dist/bin/next dev --turbopack -p 3000 -H 127.0.0.1'" \
  --port 3000 \
  --timeout 180 \
  -- uv run --with playwright python scripts/testing/s1_tg_004_miniapp_browser_smoke.py --base-url http://localhost:3000
```

Result:

```text
6 routes passed:
- home
- plans
- payments
- devices
- profile
- wallet

All 2 temporary servers stopped.
```

Targeted Mini App unit suite:

```bash
cd frontend
npm run test:run -- \
  'src/app/[locale]/miniapp/home/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/payments/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/devices/components/__tests__/DevicesClient.test.tsx' \
  'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/wallet/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/components/__tests__/MiniAppBottomNav.test.tsx' \
  'src/app/[locale]/miniapp/components/__tests__/VpnConfigCard.test.tsx'
```

Result:

```text
Test Files  8 passed (8)
Tests       89 passed (89)
Duration    1.26s
```

## Security Review Notes

| Check | Result |
|---|---|
| Telegram secrets | No real Telegram bot token, webhook secret, BotFather username or `initData` from a real user was added |
| Payment secrets | No provider credentials, invoice secrets or webhook secrets were added |
| VPN config secrecy | Screenshot fixture uses a non-production `example.invalid` config and local mock subscription URL only |
| Production side effects | No provider, Telegram, Remnawave or production API calls are made |
| Local server lifecycle | Temporary mock API and temporary Next dev server were stopped by the smoke harness |
| Existing server | Pre-existing Next dev server on `9001` was not started or stopped by this task |
| Scope boundary | Telegram identity/linking remains assigned to `S1-TG-005`, not claimed here |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| BotFather Mini App URL/menu button configured for staging bot | Open |
| Real Telegram client screenshots/video for home/plans/payments/devices/profile/wallet | Open |
| Real `Telegram.WebApp.initData` auth/signature validation and account-linking proof | Local contract completed in `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`; real Telegram client/deployed proof remains open |
| Deployed staging Mini App URL over HTTPS with production-like domains | Open |
| Staging backend cookies/CORS/CSRF/rate-limit behavior in Mini App browser context | Open |
| Real payment invoice open/return behavior inside Telegram Mini App | Open |
| Real Remnawave config delivery from staging entitlement state | Open |
| Support owner visual approval of Mini App copy and state matrix | Open |

## Next ID

Next ID to execute: `S1-TG-006` - verify Telegram notifications.
