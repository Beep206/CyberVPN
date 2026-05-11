# STAGE1-PUB-09 Telegram Bot And Mini App Deploy Evidence

Date: `2026-05-10T20:53:38Z`

## Result

Status: `runtime-pass / Telegram-client-smoke-pending`

The Stage 1 Telegram runtime path was prepared for public internet deployment:

- Telegram bot image built as `local/cybervpn-telegram-bot:stage1-beta-rc.1`.
- Image loaded on `cybervpn-h-ops`.
- `api.cyber-vpn.net` Cloudflare DNS record created for the Stage 1 API/webhook edge.
- System Caddy config updated and reloaded with `api.cyber-vpn.net` and `/webhook/telegram`.
- Caddy DNS-01 certificate issuance for `api.cyber-vpn.net` completed.
- Stage 1 app compose updated with bot loopback port `127.0.0.1:18088:8080`.
- Telegram bot env updated for internal backend auth via `AUTH_BACKEND_API_URL` and `AUTH_BACKEND_INTERNAL_SECRET`.
- Mini App URL remains `https://cyber-vpn.net/ru-RU/miniapp`.
- Prometheus public blackbox target added for `https://api.cyber-vpn.net/healthz`.
- Webhook URL join bug fixed so aiogram receives `https://api.cyber-vpn.net/webhook/telegram` instead of a double-slash URL.

The production `BOT_TOKEN` was installed after Telegram `getMe` confirmed that it belongs to `C_y_b_e_r_VPN_Bot`.
The token value is not recorded here.

## Verification

Local bot image smoke:

```text
GET http://127.0.0.1:18089/health -> 200
GET http://127.0.0.1:18089/metrics -> exposes bot_updates_total and runtime process metrics
```

Server edge smoke:

```text
GET https://api.cyber-vpn.net/healthz -> 200 ok
GET https://api.cyber-vpn.net/healthz through Cloudflare -> 200 ok
GET https://cyber-vpn.net/ru-RU/miniapp -> 200
GET https://api.cyber-vpn.net/webhook/telegram -> 405 GET not allowed; Telegram uses POST
GET http://127.0.0.1:18088/health on server -> 200 ok
```

Telegram API smoke:

```text
getMe -> username C_y_b_e_r_VPN_Bot
getWebhookInfo.url -> https://api.cyber-vpn.net/webhook/telegram
getWebhookInfo.pending_update_count -> 0
getWebhookInfo.allowed_updates -> message, callback_query, pre_checkout_query
```

Tests:

```text
services/telegram-bot unit checks: 58 passed
stage1 compose config syntax: valid
Caddy config: valid
api.cyber-vpn.net certificate: obtained successfully
Prometheus blackbox-stage1-public-web: api.cyber-vpn.net/healthz up
Prometheus cybervpn-telegram-bot scrape target: up=1
```

## Remaining Live Gate

Before this step can be promoted from `runtime-pass` to full user-flow pass, complete a real Telegram client smoke:

1. Configure or confirm BotFather domain and Mini App URL.
2. Verify `/start`, `/menu`, `/connect`, `/plans`, `/trial`, `/support`, `/paysupport` from a real Telegram client.
3. Verify Mini App with real Telegram `initData`.
4. Verify support escalation and Telegram rate limiting.
5. Verify bot metrics by `update_type` and `status` in Grafana/Prometheus after a real update is processed.
6. Rotate the BotFather token before public beta because the current token was pasted into the chat during setup.

## Notes

No production secrets are recorded in this evidence file. Token and internal secret checks were redacted to key presence, placeholder status and length only.
