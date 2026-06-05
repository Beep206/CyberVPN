# Safe Client Fixture Pack

This pack is synthetic-only coverage for client business flows created for `CYBA-546`.

## Scope

- Customer states: active subscription, trial, expired subscription, no subscription.
- Business surfaces: customer subscriptions, selected config, VPN/service-state, device credential shape, wallet balance and transactions, payment history, promo, referral, partner-code and Mini App bootstrap.
- External systems: no real payment capture, no real Telegram `initData`, no production Remnawave provisioning and no customer data.

## Seed

- Helper: `backend/tests/fixtures/safe_client.py`
- Main entry point: `seed_safe_client_fixture_pack(sessionmaker, auth_service)`
- The pack uses `example.test` and `cybervpn.test` identities, deterministic code labels and a fake Remnawave client in tests.
- Synthetic Mini App `initData` is signed-shaped with fixture-only key `safe-client-fixture-bot-token`.

## Reset

- Tests run against the existing isolated SQLite helper from `tests.helpers.realm_auth`.
- Each test disposes the engine and removes the temporary SQLite file with `cleanup_sqlite_file`.
- FastAPI dependency overrides are removed in `finally` blocks.

## Rollback

- Remove `backend/tests/fixtures/safe_client.py`, `backend/tests/integration/test_safe_client_fixture_pack.py` and this document.
- No migrations, production config or provider state are created.

## Safety Controls

- `assert_safe_client_fixture_pack_is_synthetic` and `assert_safe_payload_is_synthetic` scan fixture metadata and API evidence for production domains, raw VPN links, private keys, live payment keys, bearer/API-key markers, provider checkout URLs and real Telegram bot-token-shaped values.
- The pack intentionally stores only sanitized subscription URLs and provider references.

## Context7 Docs Checked

- Context7 MCP quota was exceeded, so `ctx7` fallback was used.
- Checked: `/pytest-dev/pytest` fixture guidance, `/websites/sqlalchemy_en_20_orm` ORM session fixture data, `/fastapi/fastapi` dependency override and async HTTPX testing guidance.
- Telegram Mini App init data signing was checked against official Telegram Mini Apps documentation.
