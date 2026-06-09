# CYBA-617 API / UI Mismatch Findings

Дата проверки: 2026-06-09

## Баги

### CYBA-617-BUG-001 - Mobile auth API cannot issue shared-session tokens for mobile customers on PostgreSQL

Серьёзность: P1 auth/session regression

Окружение: local backend ASGI tests, disposable `postgres:17.7`, synthetic mobile user/device data only.

Роль/состояние пользователя: mobile customer using native mobile password login from an iOS/Android device.

Шаги воспроизведения:

1. Use a PostgreSQL database with CyberVPN tables and default `auth_realms` rows.
2. Create an active `MobileUserModel` synthetic customer.
3. Call `POST /api/v1/mobile/auth/login` with body shape:
   `{ "email": "...", "password": "...", "device": { "device_id": "<uuid>", "platform": "ios", "platform_id": "...", "os_version": "17.4", "app_version": "1.2.3", "device_model": "iPhone 15 Pro" } }`
4. Observe backend insert into `refresh_tokens`.

Ожидаемый результат:

- API returns source-compatible `AuthResponse` with `tokens.access_token`, `tokens.refresh_token`, `tokens.token_type`, `tokens.expires_in`, and user profile.
- Backend persists refresh token family linked to the customer `PrincipalSessionModel`/`UserDeviceModel`.

Фактический результат:

- PostgreSQL rejects the insert because `refresh_tokens.user_id` is FK-constrained to `admin_users.id`, while mobile issuance passes `MobileUserModel.id`.
- Result in ASGI test is an unhandled backend `IntegrityError` before the route can return the expected `AuthResponse`.

Sanitized evidence:

- Runtime failure: `insert or update on table "refresh_tokens" violates foreign key constraint "refresh_tokens_user_id_fkey"; Key (user_id)=(synthetic mobile user UUID) is not present in table "admin_users".`
- Schema/model: `backend/src/infrastructure/database/models/refresh_token_model.py:38` through `backend/src/infrastructure/database/models/refresh_token_model.py:40`.
- Migration: `backend/alembic/versions/20260205_add_refresh_tokens.py:35` through `backend/alembic/versions/20260205_add_refresh_tokens.py:40`.
- Mobile issuance source: `backend/src/application/services/auth_session_issuer.py:146` through `backend/src/application/services/auth_session_issuer.py:157` and `backend/src/application/services/mobile_session.py:73` through `backend/src/application/services/mobile_session.py:89`.

Рекомендуемый owner/action:

- Backend implementation owner: update refresh-token persistence/schema for customer principals and add PostgreSQL-backed regression coverage for mobile login/register/Telegram/TOTP issuance.

Context7 docs checked: MCP quota exceeded; fallback `ctx7` checked `/websites/sqlalchemy_en_20` and `/websites/postgresql_17` for `IntegrityError` and FK violation behavior.

## API / Flutter DTO compatibility

Подтверждённых source-level DTO mismatches с текущим Flutter-facing shape не найдено:

- `POST /api/v1/mobile/auth/register` and `POST /api/v1/mobile/auth/login` still accept body `device`.
- `POST /api/v1/mobile/auth/refresh` and `POST /api/v1/mobile/auth/logout` still accept JSON `refresh_token` + `device_id`.
- `AuthResponse`/`TokenResponse` still expose `access_token`, `refresh_token`, `token_type`, `expires_in`.

Однако runtime compatibility сейчас фактически broken, потому что API не может выдать tokens на PostgreSQL до исправления [CYBA-617-BUG-001](#cyba-617-bug-001---mobile-auth-api-cannot-issue-shared-session-tokens-for-mobile-customers-on-postgresql).

## UI notes

Browser/mobile UI не запускался в этом backend support heartbeat; screenshots/videos не создавались. Downstream UI bug не заявляю. Для UI/Flutter владельца главный риск: даже при compatible DTO shape native app получит failed auth flow, пока backend token issuance падает на DB FK.

## Product gaps / test-data gaps

### CYBA-617-GAP-001 - PostgreSQL integration fixture bootstrap misses default `auth_realms` seed when using `Base.metadata.create_all()`

Серьёзность: P2 QA/test-data gap

Окружение: disposable local PostgreSQL, `backend/tests/conftest.py` schema bootstrap.

Шаги воспроизведения:

1. Start a clean PostgreSQL database.
2. Run the three targeted mobile shared-session integration tests with `DATABASE_URL` pointing at that database.

Ожидаемый результат:

- Test bootstrap creates schema and minimum default realm seed needed by auth/session fixtures.

Фактический результат:

- Before manual default realm seed, tests fail at synthetic `MobileUserModel` fixture creation with `mobile_users_auth_realm_id_fkey`; default customer realm row is absent.

Evidence:

- Alembic migration seeds realms in `backend/alembic/versions/20260417_phase1_auth_realms.py:57` through `backend/alembic/versions/20260417_phase1_auth_realms.py:100`.
- Pytest `create_all()` path in `backend/tests/conftest.py` creates tables but does not run Alembic seed data.

Рекомендуемый owner/action:

- Backend test-data owner: add a default auth realm bootstrap fixture for PostgreSQL integration tests or run Alembic migrations/seeds for this DB-backed pack. This does not remove the P1 product blocker above; after seeding realms, the refresh-token FK bug still fails.

Context7 docs checked: N/A - repo-local test fixture/seed gap plus PostgreSQL runtime evidence.

## Не тестировалось

- Real staging/production data.
- Real Telegram provider token material or Telegram `initData`.
- Browser UI, screenshots, mobile simulator, Flutter client execution.
- Payment/VPN provisioning/Remnawave production behavior.

## Resume update after CYBA-618 closure

Дата resume-проверки: 2026-06-09T19:56:47Z

[CYBA-618](/CYBA/issues/CYBA-618) is marked `done`, but the current QA workspace still presents the same API/backend blocker:

- `backend/src/infrastructure/database/models/refresh_token_model.py:38` through `backend/src/infrastructure/database/models/refresh_token_model.py:40` still maps `refresh_tokens.user_id` to `ForeignKey("admin_users.id", ondelete="CASCADE")`.
- Expected migration `20260609_refresh_token_owner` was not found under `backend/alembic/versions`.
- Expected regression test `tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py` was not found under `backend/tests`.

Updated API/UI risk:

- No new Flutter DTO shape mismatch was found in this resume.
- Runtime API compatibility remains blocked because the backend checkout has not landed the owner-schema fix needed for mobile customer refresh-token persistence.
- UI/Flutter owners should not treat [CYBA-617](/CYBA/issues/CYBA-617) as passing backend evidence until a synced backend fix is present and PostgreSQL-backed mobile auth tests pass.

Fresh sanity subset from `backend/`: `10 passed` for the mobile Telegram OIDC unit tests and Stage 1 registration kill-switch security cases listed in `backend-data-support-notes.md`.

Context7 docs checked: N/A - this resume update is workspace/fix-availability evidence, not a new framework/API behavior claim.

## Final API / Flutter compatibility update after CYBA-626

Дата финальной проверки: 2026-06-09T20:13:16Z

[CYBA-626](/CYBA/issues/CYBA-626) landed into the current workspace. The previous P1 runtime API blocker for mobile customer token issuance is resolved in this verification workspace:

- `POST /api/v1/mobile/auth/register` and `POST /api/v1/mobile/auth/login` can persist shared mobile refresh-token owner/session/device state on PostgreSQL.
- `POST /api/v1/mobile/auth/refresh` rotates current refresh tokens and rejects replay/reuse.
- `POST /api/v1/mobile/auth/refresh` with mismatched body `device_id` returns `401` / `INVALID_TOKEN` in a sanitized runtime probe.
- `POST /api/v1/mobile/auth/logout` revokes current session/family and later refresh returns `401`.
- `DELETE /api/v1/mobile/auth/devices/{device_id}` revokes the selected shared-session device without revoking unrelated device state.
- Telegram OIDC and TOTP completion token issuance passed in the DB-backed mobile auth pack.

No new Flutter DTO shape mismatch found:

- `AuthResponse`/`TokenResponse` remain source-compatible with `access_token`, `refresh_token`, `token_type`, and `expires_in`.
- Refresh/logout body shape remains `refresh_token` + `device_id`.
- Device list/delete behavior is compatible for devices created through current shared-session login/register flows.

Residual non-blocking finding:

- `tests/integration/api/v1/mobile_auth/test_telegram_oidc_flow.py::test_mobile_devices_list_and_delete` is obsolete against the new shared-session model: it seeds only legacy `MobileDeviceModel` rows, while current `/devices` lists legacy metadata only when backed by active shared `UserDeviceModel` state. The current shared-session device list/delete tests pass, so this is a test fixture maintenance gap rather than a product/API blocker for [CYBA-617](/CYBA/issues/CYBA-617).

Verification summary:

- DB-backed mobile auth pack excluding the obsolete legacy-only fixture: `13` selected tests passed.
- Full same pack result: `13` passed, `1` failed (`test_mobile_devices_list_and_delete`) due the fixture gap above.
- Unit/security sanity subset: `10` selected tests passed.
- Disposable `cyba617-postgres` container was stopped and removed after verification.

Sensitive evidence scan: no raw access/refresh tokens, cookies, JWTs, passwords, `.env` values, Telegram token material, production identifiers, customer PII, or payment data included.

Context7 docs checked: N/A - final API compatibility result is from local PostgreSQL-backed ASGI/integration verification and source shape inspection.
