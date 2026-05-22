# Stage 1 Production Evidence: XHTTP Subscription And RU Mihomo Bundle

Date: 2026-05-22

Scope:

- Ensure active Stage 1 subscriptions can deliver XHTTP through the public `.org` subscription path.
- Apply `Mihomo (RU bundle)` only for hidden RU plans: `ru_start` / `ru_basic`.
- Reset owner/internal test accounts for the next invite redemption smoke.

## Runtime Changes

- Backend image deployed directly to `prod-app-1`:
  - `cybervpn/cybervpn-backend:stage1-direct-xhttp-ru-bundle-20260522T081900Z`
- Only `cybervpn-backend` was recreated.
- Frontend, Telegram bot, worker, scheduler, Remnawave, Caddy and VPN node were not rebuilt or replaced.
- The compose release tag was aligned to `stage1-direct-xhttp-ru-bundle-20260522T081900Z`.
- Non-backend CyberVPN runtime images were retagged to the same release tag without rebuild to keep future compose restarts deterministic.

## Backend Contract

- Added RU bundle settings:
  - `REMNAWAVE_RU_BUNDLE_EXTERNAL_SQUAD_UUID`
  - `REMNAWAVE_RU_BUNDLE_PLAN_CODES=ru_start,ru_basic`
  - `REMNAWAVE_RU_BUNDLE_SUBSCRIPTION_TEMPLATE_NAME=Mihomo (RU bundle)`
- Paid and manual S1 provisioning now pass Remnawave `externalSquadUuid` only when `plan_code` is one of the RU plan codes.
- Trial and invite provisioning are not assigned to the RU external squad.

## Remnawave Template State

- Created/updated subscription template:
  - Type: `MIHOMO`
  - Name: `Mihomo (RU bundle)`
- Created/updated external squad:
  - Name: `S1_RU_BUNDLE`
  - Template override: `MIHOMO -> Mihomo (RU bundle)`

## Verification

Local targeted checks:

- `tests/unit/pricing/test_pricing_catalog_seed.py`: 4 passed.
- `tests/security/test_stage1_paid_provisioning.py`: 16 passed.
- `tests/security/test_stage1_admin_manual_subscription_ops.py`: 5 passed.
- `ruff check` on touched backend files: passed.

Production checks:

- Backend health: `/health` returned `{"status":"ok"}`.
- Backend container became healthy after recreate.
- `@Sasha_Beep` Remnawave user reset to active 2 GiB trial.
- Public subscription URL under `https://cyber-vpn.org/api/sub/...` returned:
  - Default/base64 response: 2 VLESS entries.
  - XHTTP present: yes.
  - Limited marker present: no.
  - Public `.org` host count: 2.
- Temporary Remnawave-only RU bundle smoke user:
  - RU Mihomo group marker present: yes (`CyberVPN RU`).
  - Temporary user deleted after smoke.

## Known Limitation

Mihomo itself documents `network: xhttp` / `xhttp-opts`, but Remnawave `2.7.4` Mihomo and Clash generators explicitly mark `xhttp` as unsupported transport:

- `dist/src/modules/subscription-template/generators/mihomo.generator.service.js`
- `dist/src/modules/subscription-template/generators/clash.generator.service.js`
- Mihomo reference checked: `https://wiki.metacubex.one/ru/config/proxies/transport/`

Result:

- XHTTP is available in the default/base64 subscription output.
- Mihomo RU bundle template is correctly selected for RU-plan users, but Remnawave does not include XHTTP in Mihomo output without a separate upstream/custom renderer change.

Recommended follow-up:

- Keep Stage 1 XHTTP delivery via default subscription clients.
- For S2, decide whether to:
  - wait for upstream Remnawave Mihomo XHTTP support;
  - maintain a controlled Remnawave fork/patch;
  - implement a CyberVPN-owned Mihomo subscription renderer.

## Account Reset

- `@Sasha_Beep`:
  - Trial refreshed to 3 days.
  - Traffic limit reset to 2 GiB.
  - Remnawave usage reset.
  - Subscription URL stored with `.org` domain.
- `@Sasha_Beep` invite codes:
  - `409FDE75`: unused.
  - `A21E8475`: unused.
  - `C46C8409`: unused.
- `@Sasha_Beep_KZ`:
  - Local subscription fields cleared.
  - No Remnawave user exists.
