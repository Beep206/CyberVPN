# Telegram Bot

Status: implemented
Owner: core
Last updated: 2026-04-24
Scope: `services/telegram-bot/`
Depends on: `../07-privacy-pii-scrubbing-and-replay-policy.md`, `../08-tags-context-correlation-and-fingerprinting-contract.md`
Related paths: `services/telegram-bot/src/main.py`, `services/telegram-bot/src/config.py`, `services/telegram-bot/tests/unit/test_main.py`, `.github/workflows/telegram-bot-ci.yml`, `services/telegram-bot/README.md`

## Current state

- Bot supports both polling and webhook modes.
- `sentry-sdk` now initializes from `SENTRY_DSN`, `ENVIRONMENT` and `SENTRY_RELEASE`.
- A minimal-PII `before_send` scrubber removes auth headers, cookies, request bodies and Telegram/config-like payload blobs.
- Dedicated CI validation now exists for env/release contract, webhook runtime contract and live HTTP smoke.

## Target

- add bot-specific Sentry initialization
- use separate bot tokens by environment
- keep only safe user context and hashed Telegram identifiers
- tag events by handler, bot mode, flow step and payment provider

## Critical bot flows

- payment
- referral
- config delivery and QR paths
- subscription lifecycle
- admin actions

## Implemented baseline

- runtime Sentry init is wired with explicit `ENVIRONMENT` and `SENTRY_RELEASE`
- webhook app exposes `/observability/sentry-contract` behind `TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET`
- smoke-only `TELEGRAM_BOT_SKIP_NETWORK_CALLS` keeps CI from calling real Telegram APIs during startup and shutdown
- webhook runtime smoke proves `/health` and `/observability/sentry-contract`
- config parsing now accepts both JSON arrays and comma-separated list envs for `AVAILABLE_LANGUAGES`, `ADMIN_IDS` and Prometheus IP lists

## Remaining carryover

- polling mode still has no separate live runtime smoke beyond startup-level coverage
- backend correlation IDs and handler/flow-step tagging remain follow-up work
- production alert routing is still open
