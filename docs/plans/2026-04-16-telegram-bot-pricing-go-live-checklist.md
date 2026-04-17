# Telegram Bot Pricing Go-Live Checklist

## Backend

- Run pricing catalog seed in preview mode and verify `basic/plus/pro/max/start/test/development` SKUs exist.
- Verify `GET /api/v1/telegram/bot/plans` returns only public plans for channel `telegram_bot`.
- Verify `GET /api/v1/telegram/bot/addons/catalog` returns only bot-supported add-ons.
- Verify `GET /api/v1/telegram/bot/user/{telegram_id}/entitlements` returns `none`, `trial`, or `active` correctly.
- Verify `POST /api/v1/telegram/bot/user/{telegram_id}/checkout/quote` matches frontend/miniapp pricing for the same SKU.
- Verify `POST /api/v1/telegram/bot/user/{telegram_id}/checkout/commit` creates pending CryptoBot invoices and zero-gateway completions.

## Telegram Bot

- `/start` bootstraps both `AdminUser` and `MobileUser` for a new Telegram account.
- Main menu reflects `trial` and `active` status instead of treating them as `none`.
- Public purchase flow is `plan -> period -> add-ons -> quote -> payment`.
- Hidden plans are not visible in the default purchase flow.
- Trial activation returns canonical `7 days / 1 device / shared-only` entitlements.
- Payment polling through `payment:check` reaches `completed` after webhook processing.
- Config delivery works after both trial activation and paid purchase.

## Admin And Support

- Bot admin plan list shows `display_name`, `plan_code`, `duration`, `visibility`, and `active` state.
- Hidden plans are distinguishable from public plans in bot admin view.
- Support can inspect a user and see `active` or `trial` subscription state via canonical entitlements.

## Release Safety

- Keep CryptoBot enabled for bot checkout before enabling the new purchase flow in production.
- Do not advertise dedicated IP add-on in the bot until location selection is implemented.
- If bot checkout fails in production, roll back by disabling purchase entrypoints in the bot and keep config/referral/profile flows online.
- After release, monitor Telegram payment conversion, checkout error rate, and trial activation rate for 24 hours.
