# CYBA-617 Blocked Flow Diagnosis

Дата проверки: 2026-06-09

## Исполнительное резюме

[CYBA-617](/CYBA/issues/CYBA-617) возобновилась после завершения [CYBA-615](/CYBA/issues/CYBA-615), но DB-backed mobile shared-session acceptance сейчас заблокирован backend schema mismatch: mobile auth issuance пишет `MobileUserModel.id` в `refresh_tokens.user_id`, а PostgreSQL schema всё ещё требует parent row в `admin_users`.

Это не UI issue и не production data blocker. Это backend API/schema regression, найденный на disposable local PostgreSQL.

## Матрица flow

| Flow | Текущий статус | Evidence | Owner/action |
|---|---|---|---|
| Mobile password login issues shared session | Blocked | `backend/src/application/services/auth_session_issuer.py:146` inserts `RefreshToken(user_id=request.user_id)`; PostgreSQL rejects mobile user id due `refresh_tokens_user_id_fkey` to `admin_users`. | Backend owner: fix refresh-token owner/schema for `principal_type="customer"`. |
| Mobile password register issues shared session | Blocked by same root cause | `backend/src/application/use_cases/mobile_auth/register.py:76` uses same `MobileSessionService.issue_session`. | Backend owner: include register in PostgreSQL-backed regression pack after schema fix. |
| Refresh rotation/replay | Blocked downstream | Intended source path in `backend/src/application/use_cases/auth/refresh_token.py:130` through `backend/src/application/use_cases/auth/refresh_token.py:232`; tests cannot reach it because login cannot create initial refresh row. | Backend owner: rerun after issuance fix. |
| Refresh body `device_id` mismatch | Static source checked, DB execution blocked | `backend/src/application/services/mobile_session.py:271` through `backend/src/application/services/mobile_session.py:280` checks hashed body `device_id` against active `UserDeviceModel`. | Backend owner/QA: add/confirm PostgreSQL regression after issuance fix. |
| Logout current session/family | Blocked downstream | `backend/src/application/services/mobile_session.py:124` validates current token/device and calls `LogoutUseCase`; targeted test fails at login setup. | Backend owner: rerun after issuance fix. |
| Remove selected mobile device only | Blocked downstream | `backend/src/application/services/mobile_session.py:178` calls device-scoped logout; targeted test fails at login setup. | Backend owner: rerun after issuance fix. |
| Telegram callback / Telegram OIDC / TOTP completion token issuance | High risk, not DB-proven | Source paths all call `MobileSessionService.issue_session` when issuing mobile tokens; same refresh-token FK applies once a mobile session is issued. | Backend owner: include Telegram/OIDC/TOTP DB-backed tests after schema fix. |
| DTO shape compatibility | Source-level unblocked | `RefreshTokenRequest`, `LogoutRequest`, `TokenResponse`, `AuthResponse` keep expected shape. | No UI owner action until backend issuance passes. |
| Legacy JWT-only refresh forced re-login | Static source checked | Missing persisted refresh token maps to `InvalidTokenError("legacy_unpersisted_refresh_token")`; route returns `401`. | Backend QA can verify after issuance path fixed. |

## Root cause

1. `RefreshToken.user_id` is still modeled as an admin-only FK:
   `backend/src/infrastructure/database/models/refresh_token_model.py:38` through `backend/src/infrastructure/database/models/refresh_token_model.py:40`.
2. The original migration creates the same FK:
   `backend/alembic/versions/20260205_add_refresh_tokens.py:35` through `backend/alembic/versions/20260205_add_refresh_tokens.py:40`.
3. Shared session issuance is now used by mobile:
   `backend/src/application/services/mobile_session.py:73` through `backend/src/application/services/mobile_session.py:89`.
4. Shared issuance inserts a `RefreshToken` with `user_id=request.user_id`:
   `backend/src/application/services/auth_session_issuer.py:146` through `backend/src/application/services/auth_session_issuer.py:157`.
5. For mobile, `request.user_id` is a `mobile_users.id`, so PostgreSQL rejects the insert with a FK violation.

## Test-data blocker separated from product blocker

There is also a QA fixture gap: clean PostgreSQL `Base.metadata.create_all()` does not seed default `auth_realms`, while Alembic migration `20260417_phase1_auth_realms` does. After manually seeding default realms in disposable DB, the `refresh_tokens.user_id` FK failure still occurs. Therefore the release blocker is not merely missing test seed data.

## Recommended disposition

Create/track a backend fix issue and keep [CYBA-617](/CYBA/issues/CYBA-617) blocked by that fix. The aggregate gate [CYBA-611](/CYBA/issues/CYBA-611) should not consume [CYBA-617](/CYBA/issues/CYBA-617) as passing evidence until PostgreSQL-backed mobile auth issuance tests pass.

## Context7 Evidence

Context7 docs checked: MCP quota exceeded. Fallback `ctx7` checked `/websites/sqlalchemy_en_20` for DB integrity failures surfacing as `sqlalchemy.exc.IntegrityError`, and `/websites/postgresql_17` for foreign key constraint violations on missing referenced parent rows. The concrete root cause is from repo source and local PostgreSQL runtime evidence.

## Resume diagnosis after CYBA-618 closure

Дата resume-проверки: 2026-06-09T19:56:47Z

После wake `issue_blockers_resolved` [CYBA-618](/CYBA/issues/CYBA-618) значится `done`, но текущий [CYBA-617](/CYBA/issues/CYBA-617) workspace не содержит заявленный refresh-token owner-schema fix:

- `backend/src/infrastructure/database/models/refresh_token_model.py:38` through `backend/src/infrastructure/database/models/refresh_token_model.py:40` still keeps `refresh_tokens.user_id` as `ForeignKey("admin_users.id", ondelete="CASCADE")`.
- Expected migration `20260609_refresh_token_owner` is absent from `backend/alembic/versions`.
- Expected regression test `tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py` is absent from `backend/tests`.

Updated blocked-flow status:

| Flow | Resume status | Evidence | Owner/action |
|---|---|---|---|
| Mobile password login/register shared-session issuance | Still blocked | Admin-only FK is still present in the current model, so the previously proven `refresh_tokens_user_id_fkey` product blocker is still applicable. | Backend implementation owner: land/sync the [CYBA-618](/CYBA/issues/CYBA-618) schema/model/test fix into this QA workspace or provide the correct verification workspace. |
| Refresh rotation/replay/logout/device revoke | Still blocked downstream | Acceptance setup cannot safely proceed until initial mobile refresh token issuance can persist for customer principals. | Backend owner, then backend QA rerun DB-backed mobile auth pack. |
| Telegram OIDC/TOTP mobile token issuance | Still high-risk/not DB-proven | These paths share the same mobile session issuance model. | Backend owner should include these paths in the post-fix DB-backed regression pack if touched by [CYBA-615](/CYBA/issues/CYBA-615). |

Recommended disposition remains `blocked`, but the blocker is now fix-delivery/sync rather than an unknown root cause: [CYBA-617](/CYBA/issues/CYBA-617) needs a first-class follow-up to land or expose the [CYBA-618](/CYBA/issues/CYBA-618) artifacts before QA can complete acceptance.

Context7 docs checked: N/A - resume diagnosis is based on local workspace artifact availability; PostgreSQL FK behavior was already tied to docs in the prior evidence section.

## Final disposition after CYBA-626

Дата финальной проверки: 2026-06-09T20:13:16Z

[CYBA-626](/CYBA/issues/CYBA-626) is `done`, and the [CYBA-617](/CYBA/issues/CYBA-617) workspace now contains the refresh-token owner-schema fix that was missing during the prior resume.

Updated flow status:

| Flow | Final status | Evidence | Remaining owner/action |
|---|---|---|---|
| Mobile password register/login shared-session issuance | Passed | Disposable PostgreSQL run passed `test_refresh_token_principal_owner.py`; current model no longer has admin-only FK on `refresh_tokens.user_id`. | None for [CYBA-617](/CYBA/issues/CYBA-617). |
| Refresh rotation/replay | Passed | `test_mobile_password_login_persists_shared_session_and_refresh_rotates` passed and verifies rotation lineage, current refresh token, replay `401`, family revocation. | None. |
| Refresh body `device_id` mismatch | Passed | Sanitized ASGI probe: register `201`, refresh with wrong `device_id` returned `401` / `INVALID_TOKEN`; original refresh row stayed present/unrevoked. | None. |
| Logout current session/family | Passed | `test_mobile_logout_revokes_current_shared_session` passed: logout `204`, token/session revoked, later refresh `401`. | None. |
| Remove selected mobile device only | Passed | `test_mobile_remove_device_revokes_selected_session_only` and `test_mobile_remove_device_revokes_selected_device_without_unrelated_devices` passed. | None. |
| Telegram OIDC/TOTP token issuance | Passed | DB-backed mobile auth pack passed with Telegram OIDC route tests and TOTP completion test after owner-schema fix. | None. |
| DTO shape compatibility | Passed source/runtime check | Auth/token response shape remains source-compatible; runtime issuance now succeeds. | None. |

The earlier product blocker `refresh_tokens_user_id_fkey` is resolved in the current verification workspace.

Residual non-blocking diagnosis:

- Full `test_telegram_oidc_flow.py` currently has one failing legacy-only test, `test_mobile_devices_list_and_delete`, because it creates `MobileDeviceModel` rows without corresponding active shared `UserDeviceModel` rows. Current implementation lists only devices backed by active shared session/device state. This is a test-data/fixture update need, not a blocker for [CYBA-617](/CYBA/issues/CYBA-617), because the shared-session device list/delete acceptance path passed in current tests.

Recommended final disposition: mark [CYBA-617](/CYBA/issues/CYBA-617) `done`; no first-class blocker remains for the scoped backend/API QA evidence.

Context7 docs checked: N/A - final disposition is based on repo-local integration execution and source inspection; no new external framework behavior claim added.
