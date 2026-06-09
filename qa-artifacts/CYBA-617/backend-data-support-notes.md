# CYBA-617 Backend Data Support Notes

Дата проверки: 2026-06-09

## Область проверки

Read-only backend/API/test-data support для [CYBA-617](/CYBA/issues/CYBA-617), дочерней задачи [CYBA-597](/CYBA/issues/CYBA-597). Проверялись native mobile auth routes после завершения implementation blocker [CYBA-615](/CYBA/issues/CYBA-615): source contract, PostgreSQL-backed targeted tests, локальное fixture состояние и sanitized runtime evidence.

Backend code, migrations, contracts, seeds, `.env` files, production data и secrets не изменялись. Для DB verification временно поднимался disposable local `postgres:17.7` контейнер `cyba617-postgres` на `127.0.0.1:15432`; контейнер остановлен после проверки.

## Безопасная обработка данных

- Production/staging secrets, `.env` values, JWT, cookies, refresh tokens, passwords, payment secrets, Telegram `initData`, customer PII и raw provider data не сохранялись.
- Тестовые email/device/user ids были synthetic local values из pytest fixtures.
- Raw access/refresh token values не включены в artifacts/comments.
- Docker env/log output был sanitized; sensitive env values не публиковались.

## Контекст снятого blocker

[CYBA-615](/CYBA/issues/CYBA-615) сообщил, что mobile auth migrated на `AuthSessionIssuer`, `UserDeviceModel`, `PrincipalSessionModel` и persisted `refresh_tokens` family, но DB-backed integration tests ранее были `skipped` из-за недоступной local PostgreSQL.

Этот heartbeat повторил targeted verification после `issue_blockers_resolved`.

## Source evidence

| Acceptance area | Evidence |
|---|---|
| Flutter request/response shape retained | `backend/src/presentation/api/v1/mobile_auth/schemas.py:255` defines `TokenResponse` with `access_token`, `refresh_token`, `token_type`, `expires_in`; `backend/src/presentation/api/v1/mobile_auth/schemas.py:282` defines `AuthResponse`; `backend/src/presentation/api/v1/mobile_auth/schemas.py:316` and `backend/src/presentation/api/v1/mobile_auth/schemas.py:337` keep body `refresh_token` + `device_id`. |
| Password register/login use shared mobile session service | `backend/src/application/use_cases/mobile_auth/register.py:76` and `backend/src/application/use_cases/mobile_auth/login.py:78` call `MobileSessionService.issue_session(...)`. |
| Shared issue path creates user device/session/refresh records | `backend/src/application/services/mobile_session.py:73` calls `AuthSessionIssuer.issue_auth_session`; `backend/src/application/services/auth_session_issuer.py:133` through `backend/src/application/services/auth_session_issuer.py:175` creates/updates `UserDeviceModel`, inserts `RefreshToken`, creates `PrincipalSessionModel`, and links `principal_session_id`. |
| Mobile refresh validates body `device_id` against shared session/device | `backend/src/application/services/mobile_session.py:248` locks refresh token by hash; `backend/src/application/services/mobile_session.py:271` through `backend/src/application/services/mobile_session.py:280` rejects mismatched or revoked `UserDeviceModel.device_key_hash`. |
| Refresh rotation uses shared model | `backend/src/application/services/mobile_session.py:102` calls `RefreshTokenUseCase.execute(... principal_type="customer" ...)`; `backend/src/application/use_cases/auth/refresh_token.py:130` locks the presented refresh token; `backend/src/application/use_cases/auth/refresh_token.py:206` through `backend/src/application/use_cases/auth/refresh_token.py:232` writes child token, `parent_token_id`, `replaced_by_token_id`, `consumed_at`, `family_id`, and `current_refresh_token_id`. |
| Logout/device revoke use shared session scope | `backend/src/application/services/mobile_session.py:124` validates current refresh token/device before logout; `backend/src/application/use_cases/auth/logout.py:50` revokes current session family; `backend/src/application/services/mobile_session.py:178` calls `LogoutUseCase.execute_device` for selected device revoke. |
| Legacy mobile device is display/metadata, not active-session authority | `backend/src/application/services/mobile_session.py:149` through `backend/src/application/services/mobile_session.py:162` lists legacy `MobileDeviceModel` only if its hashed `device_id` exists in active `UserDeviceModel`. |

## Подтверждённый backend blocker

### CYBA-617-BUG-001 - PostgreSQL FK blocks mobile shared-session refresh token issuance

Серьёзность: P1 auth/session regression

Окружение: local repo worktree, backend `.venv`, disposable `postgres:17.7` on `127.0.0.1:15432`, `DATABASE_URL=postgresql+asyncpg://cybervpn:cybervpn@localhost:15432/cybervpn`, `REDIS_URL=redis://localhost:6379/15`, ASGI `async_client`.

Роль/состояние пользователя: synthetic mobile customer account (`MobileUserModel`) in customer realm, active status, password login from synthetic iOS device.

Шаги воспроизведения:

1. Start disposable local PostgreSQL with database/user matching the test `DATABASE_URL`.
2. Run targeted tests:
   `PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql+asyncpg://cybervpn:cybervpn@localhost:15432/cybervpn REDIS_URL=redis://localhost:6379/15 .venv/bin/pytest --no-cov tests/integration/api/v1/mobile_auth/test_telegram_oidc_flow.py::test_mobile_password_login_persists_shared_session_and_refresh_rotates tests/integration/api/v1/mobile_auth/test_telegram_oidc_flow.py::test_mobile_logout_revokes_current_shared_session tests/integration/api/v1/mobile_auth/test_telegram_oidc_flow.py::test_mobile_remove_device_revokes_selected_session_only -q`
3. On clean `Base.metadata.create_all()` DB, default `auth_realms` seed is absent; seed the four deterministic default realms from `backend/alembic/versions/20260417_phase1_auth_realms.py:57` through `backend/alembic/versions/20260417_phase1_auth_realms.py:100` into the disposable DB.
4. Re-run the same command.

Ожидаемый результат:

- `/api/v1/mobile/auth/login` returns `200`, persists a `RefreshToken` linked to `PrincipalSessionModel` and `UserDeviceModel`, then refresh/logout/remove-device tests can verify rotation/replay/revoke behavior.

Фактический результат:

- All three DB-backed tests fail before acceptance assertions because `/api/v1/mobile/auth/login` hits PostgreSQL `ForeignKeyViolationError` on `refresh_tokens.user_id`.
- Sanitized failure signature:
  `insert or update on table "refresh_tokens" violates foreign key constraint "refresh_tokens_user_id_fkey"; Key (user_id)=(synthetic mobile user UUID) is not present in table "admin_users".`

Sanitized evidence:

- `backend/src/infrastructure/database/models/refresh_token_model.py:38` through `backend/src/infrastructure/database/models/refresh_token_model.py:40` defines `RefreshToken.user_id` as `ForeignKey("admin_users.id", ondelete="CASCADE")`.
- `backend/alembic/versions/20260205_add_refresh_tokens.py:35` through `backend/alembic/versions/20260205_add_refresh_tokens.py:40` creates the same FK to `admin_users.id`.
- `backend/src/application/services/auth_session_issuer.py:146` through `backend/src/application/services/auth_session_issuer.py:157` inserts `RefreshToken(user_id=request.user_id, ...)`.
- For mobile login, `request.user_id` is the `MobileUserModel.id` passed from `backend/src/application/services/mobile_session.py:75`.
- PostgreSQL runtime rejects that insert because the referenced row is in `mobile_users`, not `admin_users`.

Рекомендуемый owner/action:

- Backend implementation owner for [CYBA-615](/CYBA/issues/CYBA-615): fix shared refresh-token ownership model for `principal_type="customer"` before release gate. The fix likely needs a contract/schema decision: either make `refresh_tokens` principal-aware instead of admin-only, split mobile refresh token table, or otherwise remove the invalid `admin_users` FK for customer principals with a migration and tests.

## Команды проверки

| Проверка | Результат | Sanitized evidence |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov tests/unit/api/v1/mobile_auth/test_telegram_oidc.py tests/unit/application/use_cases/mobile_auth/test_telegram_oidc_auth.py tests/security/test_stage1_registration_kill_switch.py::test_mobile_password_registration_blocked_before_repository_side_effects tests/security/test_stage1_registration_kill_switch.py::test_mobile_telegram_new_account_creation_blocked_when_paused tests/security/test_stage1_registration_kill_switch.py::test_mobile_telegram_oidc_existing_user_login_allowed_when_paused -q` from `backend/` | Pass | `10 passed`. |
| `PYTHONDONTWRITEBYTECODE=1 REDIS_URL=redis://localhost:6379/15 .venv/bin/pytest --no-cov ...three mobile shared-session integration tests... -q` from `backend/` | Skipped | Existing local `127.0.0.1:6767` DB unavailable for expected `cybervpn` role; test reports `3 skipped`. |
| Same three integration tests with disposable `DATABASE_URL=postgresql+asyncpg://cybervpn:cybervpn@localhost:15432/cybervpn` before default realm seed | Fail | `mobile_users_auth_realm_id_fkey`: default customer realm row absent in `create_all()` bootstrap DB. This is fixture/setup gap, not final product behavior when Alembic seed ran. |
| Same three integration tests after default realm seed | Fail | `refresh_tokens_user_id_fkey`: mobile user UUID is not present in `admin_users`. This is the release-blocking backend mismatch. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov tests/unit/infrastructure/test_session_device_schema_models.py -q` from `backend/` | Pass | `3 passed`; model-level unit tests do not catch the mobile/customer FK failure. |

## Coverage status vs acceptance criteria

| Acceptance criterion | QA status |
|---|---|
| Mobile password `register`/`login` returns `AuthResponse` and persists `UserDeviceModel`, `PrincipalSessionModel`, DB-backed refresh family | Blocked by [CYBA-617-BUG-001](#cyba-617-bug-001---postgresql-fk-blocks-mobile-shared-session-refresh-token-issuance). Source path is wired, but PostgreSQL rejects refresh token insert for mobile users. |
| Mobile `refresh` rotates atomically and rejects replay/reuse | Not reached in DB test because login cannot issue initial refresh token. Static source shows intended shared path. |
| Mobile `refresh` rejects mismatched body `device_id` | Static source checked; DB execution blocked before refresh. |
| Mobile `logout` revokes current session/family | Not reached in DB test because login cannot issue initial refresh token. |
| `DELETE /api/v1/mobile/auth/devices/{device_id}` does not revoke unrelated devices | Not reached in DB test because login cannot issue sessions for two devices. |
| Mobile TOTP completion and Telegram OIDC/callback issuance use persisted session model | Static source checked; DB execution blocked by the same refresh token FK risk for paths that issue mobile sessions. |
| Flutter DTO/request shape compatibility | Source-compatible on request/response schemas. Runtime mobile issuance is blocked. |
| Legacy JWT-only mobile refresh transition | Static source maps missing persisted token to `legacy_unpersisted_refresh_token` then route returns `401`; DB execution not reached beyond login failure. |

## Context7 Evidence

Context7 docs checked: MCP quota exceeded. Fallback `ctx7` checked `/websites/sqlalchemy_en_20` for DB integrity failures surfacing as `sqlalchemy.exc.IntegrityError`, and `/websites/postgresql_17` for foreign key constraint violations when an inserted row references a missing parent row. Product/root-cause evidence is from repo source and local PostgreSQL runtime trace.

## Resume after CYBA-618 done

Дата resume-проверки: 2026-06-09T19:56:47Z

Wake reason: `issue_blockers_resolved`; [CYBA-618](/CYBA/issues/CYBA-618) is reported as `done` and is the resolved blocker for [CYBA-617](/CYBA/issues/CYBA-617).

Проверка текущего workspace показала, что заявленный backend fix из [CYBA-618](/CYBA/issues/CYBA-618) недоступен в этом checkout, поэтому acceptance verification всё ещё заблокирован:

- `backend/src/infrastructure/database/models/refresh_token_model.py:38` through `backend/src/infrastructure/database/models/refresh_token_model.py:40` still defines `RefreshToken.user_id` with `ForeignKey("admin_users.id", ondelete="CASCADE")`.
- `rg -n "20260609_refresh_token_owner|principal_subject|principal_class|ForeignKey\\(\"admin_users\\.id\"" backend/src/infrastructure/database/models/refresh_token_model.py backend/alembic/versions backend/tests/integration/api/v1/mobile_auth` still returns the admin FK in `refresh_token_model.py` and does not find the expected `20260609_refresh_token_owner` migration/test artifact.
- `find backend/alembic/versions -maxdepth 1 -type f -name '*refresh*' -o -name '20260609*' | sort` does not list `20260609_refresh_token_owner`.
- `find backend/tests -path '*mobile_auth*' -type f | sort` does not list `tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py`.

Fresh sanity subset:

- Command from `backend/`: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov tests/unit/api/v1/mobile_auth/test_telegram_oidc.py tests/unit/application/use_cases/mobile_auth/test_telegram_oidc_auth.py tests/security/test_stage1_registration_kill_switch.py::test_mobile_password_registration_blocked_before_repository_side_effects tests/security/test_stage1_registration_kill_switch.py::test_mobile_telegram_new_account_creation_blocked_when_paused tests/security/test_stage1_registration_kill_switch.py::test_mobile_telegram_oidc_existing_user_login_allowed_when_paused -q`
- Result: `10 passed`.

DB-backed mobile shared-session acceptance tests were not rerun in this resume because the same release-blocking source/schema mismatch remains present before execution. Re-running the disposable PostgreSQL integration without the missing owner-schema fix would only reproduce the already documented `refresh_tokens_user_id_fkey` blocker.

Sensitive evidence scan: no raw JWT, cookies, refresh tokens, passwords, `.env` values, Telegram token material, payment data, production identifiers, or customer PII were written to this artifact.

Context7 docs checked: N/A - this resume finding is workspace/fix-availability evidence. The underlying PostgreSQL FK behavior remains covered by the earlier Context7 fallback evidence in this document.

## Final verification after CYBA-626 done

Дата финальной проверки: 2026-06-09T20:13:16Z

Wake reason: `issue_children_completed`; [CYBA-626](/CYBA/issues/CYBA-626) is `done` and the current [CYBA-617](/CYBA/issues/CYBA-617) workspace now contains the landed refresh-token owner fix.

Fix availability confirmed:

- `backend/src/infrastructure/database/models/refresh_token_model.py` now has `auth_realm_id`, `principal_class`, `principal_subject`, `audience`, and `scope_family`, and `RefreshToken.user_id` no longer has `ForeignKey("admin_users.id", ondelete="CASCADE")`.
- `backend/alembic/versions/20260609_refresh_token_principal_owner.py` is present.
- `backend/tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py` is present.

Runtime verification used disposable local PostgreSQL only:

- Started `postgres:17.7` container `cyba617-postgres` on `127.0.0.1:15432`; stopped and removed after verification.
- Used isolated Redis DB `redis://localhost:6379/15`.
- No production/staging data, real Telegram token material, payment data, customer PII, `.env` values, JWT, cookies, or raw refresh/access tokens were stored in artifacts/comments.

Verification results:

| Check | Result | Evidence |
|---|---:|---|
| Current workspace source/migration/regression artifact check | Pass | Owner fields and migration/test artifacts present; admin-only `refresh_tokens.user_id` FK removed from current model. |
| Targeted DB-backed acceptance pack: `tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py` plus password login/refresh/logout/remove-device and TOTP completion nodes from `test_telegram_oidc_flow.py` | Pass | `..... [100%]` / 6 selected tests passed. |
| Current DB-backed mobile auth pack excluding obsolete legacy-only device fixture: `tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py tests/integration/api/v1/mobile_auth/test_telegram_oidc_flow.py -k 'not test_mobile_devices_list_and_delete' -q` | Pass | `............ [100%]` / 13 selected tests passed. |
| Unit/security sanity subset from `backend/` | Pass | `.......... [100%]` / 10 selected tests passed. |
| Sanitized runtime probe for mismatched body `device_id` on `/api/v1/mobile/auth/refresh` | Pass | `register_status=201`, `mismatch_refresh_status=401`, `mismatch_refresh_detail_code=INVALID_TOKEN`, `original_refresh_row_present=True`, `original_refresh_revoked_after_mismatch=False`. No token values printed. |

Acceptance status after [CYBA-626](/CYBA/issues/CYBA-626):

| Acceptance criterion | QA status |
|---|---|
| Mobile password `register`/`login` returns `AuthResponse` and persists `UserDeviceModel`, `PrincipalSessionModel`, DB-backed refresh family | Passed on disposable PostgreSQL. `test_refresh_token_principal_owner.py` covers register/login owner metadata; `test_mobile_password_login_persists_shared_session_and_refresh_rotates` covers session/device/refresh persistence. |
| Mobile `refresh` rotates atomically and rejects replay/reuse | Passed. `test_mobile_password_login_persists_shared_session_and_refresh_rotates` verifies rotation lineage/current token and replay family revocation; `test_mobile_password_refresh_rotation_uses_customer_principal_owner_schema` verifies unrelated device token remains active until its own logout. |
| Mobile `refresh` rejects mismatched body `device_id` | Passed via sanitized ASGI runtime probe: wrong device id returned `401` / `INVALID_TOKEN`; original refresh row remained present and unrevoked. |
| Mobile `logout` revokes only the current session/family and clears/invalidates subsequent refresh use | Passed. `test_mobile_logout_revokes_current_shared_session` verifies `204`, token/session revoked, subsequent refresh `401`. |
| `DELETE /api/v1/mobile/auth/devices/{device_id}` does not revoke unrelated devices | Passed in current shared-session model. `test_mobile_remove_device_revokes_selected_session_only` and `test_mobile_remove_device_revokes_selected_device_without_unrelated_devices` verify selected device/session revoked while unrelated device token/session remains active. |
| Mobile TOTP completion and Telegram OIDC/callback issuance use persisted session model | Passed in DB-backed mobile auth pack. `test_route_returns_pending_2fa_and_completion_issues_session` and Telegram OIDC route tests pass in the 13-test pack. |
| Flutter DTO/request shape compatibility | Source-compatible and runtime auth issuance now passes. `AuthResponse`/`TokenResponse` shape unchanged; no new Flutter DTO mismatch found. |
| Legacy JWT-only mobile refresh transition | Source-level behavior remains `401` for unpersisted/unknown refresh token. Not reclassified as a bug in this final run. |

Residual non-blocking test-data gap:

- `tests/integration/api/v1/mobile_auth/test_telegram_oidc_flow.py::test_mobile_devices_list_and_delete` fails both in full file run and isolated rerun because the test seeds only legacy `MobileDeviceModel` rows. Current `/api/v1/mobile/auth/devices` intentionally lists legacy device metadata only when there is an active shared `UserDeviceModel` for the principal/device hash. This does not block [CYBA-617](/CYBA/issues/CYBA-617) acceptance because the shared-session device list/delete behavior is covered and passing in the new/current tests. Owner/action: backend test-data owner should update or retire this legacy-only fixture if the full integration file is expected to be green in CI.

Context7 docs checked: N/A - final verification is based on repo-local source inspection plus local PostgreSQL/ASGI test execution; the earlier PostgreSQL FK behavior claim remains documented above with Context7 fallback evidence.
