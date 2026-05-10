# Phase 18 Live Notification Receivers Evidence

Date: `2026-05-10`

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Scope

Enable and verify live Alertmanager notification receivers without committing secrets to the repository.

## Server Changes

- Updated `/srv/cybervpn-h/secrets/alertmanager.env` with live receiver settings.
- Preserved root-only backups of the previous secret file:
  - `/srv/cybervpn-h/secrets/alertmanager.env.before-live-receivers-20260510T145407Z.bak`
  - `/srv/cybervpn-h/secrets/alertmanager.env.before-resend-2587-20260510T145824Z.bak`
- Recreated only the `cybervpn-alertmanager` container.

## Telegram

- Direct Telegram Bot API smoke returned `ok=true`.
- Sanitized evidence:
  - `/srv/storage/evidence/observability/notification-direct-smoke-20260510T145636Z/telegram-response-sanitized.json`

## Resend SMTP

- Standard `smtp.resend.com:587` timed out from this host.
- Resend fallback STARTTLS port `smtp.resend.com:2587` succeeded.
- Sender domain: `email.cyber-vpn.net`.
- Sanitized evidence:
  - `/srv/storage/evidence/observability/resend-smtp-live-20260510T145843Z/resend-smtp-smoke.json`

## Alertmanager End-To-End Smoke

- Test alert: `CyberVPNPhase18TelegramDeliverySmoke`.
- Alertmanager status includes both `telegram_configs` and `email_configs`.
- Sanitized Alertmanager log check found `notify_errors=0`.
- Evidence:
  - `/srv/storage/evidence/observability/alertmanager-live-receivers-20260510T145909Z`

## Follow-Up

The Telegram bot token and Resend API key were provided during setup and should be rotated after live receiver verification. After rotation, replace only the values in `/srv/cybervpn-h/secrets/alertmanager.env` and recreate `alertmanager`.
