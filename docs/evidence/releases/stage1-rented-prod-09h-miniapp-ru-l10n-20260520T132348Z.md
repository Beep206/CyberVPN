# Stage 1 Rented Production Evidence: Mini App RU Localization Hotfix

Date: 2026-05-20

Release tag: `stage1-rent09h-miniapp-ru-l10n-20260520t132348z`

## Purpose

Remove visible English/Russian language mixing from the Telegram Mini App RU flow during the Stage 1 controlled beta.

User-visible issue reported:

- Home showed English labels such as `No Active Subscription`, `Free Trial Available`, `No VPN config available`.
- Plans mixed Russian text with English terms such as `trial`, `shared pool`, `Quote`, `entitlements`.
- Wallet showed English labels such as `Wallet Balance`, `Transaction History`.
- Profile showed English section labels and a technical fallback email ending in `@telegram.local`.

## Changes

- Completed `MiniApp` RU translation coverage and regenerated generated message bundles.
- Added matching EN keys so `MiniApp` message schemas stay aligned.
- Localized plan display names, connection modes, server pools, `Unlimited`, checkout-code state, config copy errors, and default plan labels.
- Localized `404` VPN config fetch handling so `Subscription config not found` is not shown to the user.
- Hid technical Telegram fallback emails ending in `@telegram.local` in the Mini App profile.
- Removed English fallback labels from the Mini App devices route while keeping the existing `Devices` namespace.

## Local Verification

Commands run from repository root:

```bash
node <MiniApp message schema compare>
npm --workspace frontend run lint -- 'src/app/[locale]/miniapp/components/VpnConfigCard.tsx' 'src/app/[locale]/miniapp/home/page.tsx' 'src/app/[locale]/miniapp/plans/page.tsx' 'src/app/[locale]/miniapp/profile/page.tsx' 'src/app/[locale]/miniapp/devices/page.tsx'
npm --workspace frontend test -- MiniAppBottomNav VpnConfigCard HomeClient PlansClient ProfilePage checkout-code-box
npm --workspace frontend run build
git diff --check -- <changed frontend files>
rg -n -- '<secret-patterns>' <changed frontend files> || true
```

Result:

- `missing_in_ru=0`
- `extra_in_ru=0`
- Lint passed.
- Mini App tests passed: 5 files, 53 tests.
- Frontend production build passed.
- `git diff --check` passed.
- Secret scan over changed frontend files returned no matches.

## Production Deployment

Target: `prod-app-1`

Actions:

- Synced changed frontend files into `/srv/cybervpn/releases/src-90f5b4b5-rent04`.
- Built frontend Docker image:
  - `cybervpn/cybervpn-frontend:stage1-rent09h-miniapp-ru-l10n-20260520t132348z`
- Retagged unchanged backend/admin/bot/worker images with the same release tag for compose consistency.
- Updated `/srv/cybervpn/compose/app/.env`:
  - `CYBERVPN_IMAGE_TAG=stage1-rent09h-miniapp-ru-l10n-20260520t132348z`
- Recreated only `cybervpn-frontend`.

## Production Verification

Runtime:

```text
cybervpn-stage1-cybervpn-frontend-1 cybervpn/cybervpn-frontend:stage1-rent09h-miniapp-ru-l10n-20260520t132348z healthy
```

HTTPS probes:

```text
https://cyber-vpn.net/ru-RU/miniapp/home    200
https://cyber-vpn.net/ru-RU/miniapp/plans   200
https://cyber-vpn.net/ru-RU/miniapp/wallet  200
https://cyber-vpn.net/ru-RU/miniapp/profile 200
```

String regression check:

- The reported English phrases were not found in public RU Mini App HTML for `home`, `plans`, `wallet`, and `profile`.

## Owner Retest

Retest inside Telegram Mini App:

1. Open Home.
2. Open Plans.
3. Open Wallet.
4. Open Profile.
5. Confirm visible customer-facing text is Russian in RU locale.
6. Confirm Profile no longer shows a synthetic `@telegram.local` email.

## Known Notes

- Hidden technical strings may still exist in non-visible Next.js error/not-found payloads and generic accessibility fallbacks outside the Mini App customer flow.
- This evidence covers the RU Mini App customer-visible surfaces reported during `STAGE1-RENT-09`.
