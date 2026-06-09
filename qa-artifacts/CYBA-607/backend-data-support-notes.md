# CYBA-607 Backend Data Support Notes

Дата проверки: 2026-06-09

## Область проверки

Read-only backend/API/test-data support для [CYBA-607](/CYBA/issues/CYBA-607), дочерней задачи [CYBA-597](/CYBA/issues/CYBA-597). Проверялись только backend source, migrations, generated contracts и tests. Backend code, migrations, contracts, seeds, `.env` files, production data и secrets в этом QA-проходе не изменялись.

## Безопасная обработка данных

- Production/staging secrets, `.env` values, JWT, cookies, refresh tokens, passwords, payment secrets, Telegram `initData`, customer PII и raw provider data не читались и не сохранялись.
- Команды использовали только synthetic local values там, где импорт настроек требовал обязательные env names.
- Тестовый запуск использовал in-repo synthetic fixtures и local SQLite helper state из `backend/tests/helpers/realm_auth.py`.
- Существующие dirty worktree changes от upstream implementation agents оставлены без изменений.

## Контекст снятых блокеров

`CYBA-607` возобновлена после перехода blocker issues в `done`:

| Source issue | QA-relevant completion signal |
|---|---|
| [CYBA-599](/CYBA/issues/CYBA-599) | Добавлен trusted client IP resolver для auth/session/rate-limit audit paths; прямой spoofed `X-Forwarded-For` игнорируется, если proxy headers не включены и peer не trusted. |
| [CYBA-601](/CYBA/issues/CYBA-601) | Реализована atomic refresh rotation с row locks, одной active `principal_session`, append-only refresh history, benign race window и replay family revocation после окна. |
| [CYBA-602](/CYBA/issues/CYBA-602) | Обновлён device/logout API contract: unique active stable devices, `POST /auth/devices/logout-others`, realm/device-scoped logout-all/delete-device behavior, refreshed OpenAPI/TS clients. |

## Доказательства source / contract

| Область | Evidence |
|---|---|
| Web login token delivery | `backend/src/presentation/api/v1/auth/routes.py:938` ставит auth cookies; `backend/src/presentation/api/v1/auth/routes.py:969` возвращает `WebLoginResponse` без raw token fields. |
| Opaque web device cookie | `backend/src/presentation/api/v1/auth/cookies.py:51` создаёт или переиспользует opaque cookie value; `backend/src/presentation/api/v1/auth/cookies.py:58` ставит `settings.web_device_cookie_name`. |
| Pepper-hashed device key | `backend/src/application/services/auth_session_issuer.py:204` хэширует device key до lookup; test evidence в `backend/tests/integration/test_auth_realm_sessions.py:392` подтверждает, что DB hash не равен ни cookie, ни plain `sha256(cookie)`. |
| Stable unique device model | `backend/src/infrastructure/database/models/user_device_model.py:22` задаёт active principal/device uniqueness с `postgresql_where=revoked_at IS NULL`. |
| Device provenance fields | `backend/src/infrastructure/database/models/user_device_model.py:52` through `backend/src/infrastructure/database/models/user_device_model.py:56` содержат `first_user_agent`, `last_user_agent`, `last_ip_address`, `last_ip_source`, `last_proxy_peer`. |
| Refresh rotation lock | `backend/src/application/use_cases/auth/refresh_token.py:130` выбирает presented `RefreshToken` через `with_for_update()`; `backend/src/application/use_cases/auth/refresh_token.py:239` lock-ит связанную `PrincipalSessionModel`. |
| Refresh rotation persistence | `backend/src/application/use_cases/auth/refresh_token.py:199` создаёт child refresh token; `backend/src/application/use_cases/auth/refresh_token.py:214` помечает old token как consumed/rotated; `backend/src/application/use_cases/auth/refresh_token.py:220` обновляет `current_refresh_token_id`. |
| Replay handling | `backend/src/application/use_cases/auth/refresh_token.py:289` трактует replay внутри 10s tolerance как no cookie clear; `backend/src/application/use_cases/auth/refresh_token.py:301` revokes token family/session после tolerance. |
| Device list contract | `backend/src/presentation/api/v1/auth/routes.py:3179` возвращает unique active devices; `backend/src/presentation/api/v1/auth/schemas.py:394` включает `total`, `total_devices`, `device_limit`, `remaining_devices`. |
| Logout semantics | `backend/src/presentation/api/v1/auth/routes.py:1241` обрабатывает realm-scoped `logout-all`; `backend/src/presentation/api/v1/auth/routes.py:3274` обрабатывает `logout-others`; `backend/src/presentation/api/v1/auth/routes.py:3341` обрабатывает selected-device remote logout. |
| Generated contract parity | `backend/docs/api/openapi.json` и generated clients в `frontend/src/lib/api/generated/types.ts`, `admin/src/lib/api/generated/types.ts`, `partner/src/lib/api/generated/types.ts` содержат `/api/v1/auth/devices/logout-others`, `LogoutOthersResponse`, `DeviceSessionListResponse.total_devices`, `device_limit`, `remaining_devices`. |

## Команды проверки

Команды выполнялись из repo root, если явно не указано `backend/`.

| Проверка | Результат | Sanitized evidence |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov tests/integration/test_auth_realm_sessions.py tests/unit/presentation/test_client_ip.py tests/unit/infrastructure/test_session_device_schema_models.py -q` from `backend/` | Pass | `........................ [100%]` = 24 targeted tests passed. |
| `.venv/bin/alembic heads` from `backend/` | Pass | `20260609_user_devices_audit_provenance (head)`; observed one current Alembic head. |
| `ENVIRONMENT=test REMNAWAVE_TOKEN=pytest-remnawave-token JWT_SECRET=pytest-jwt-secret-with-minimum-32-character-length CRYPTOBOT_TOKEN=pytest-cryptobot-token CYBERVPN_DEVICE_COOKIE_PEPPER=pytest-device-cookie-pepper .venv/bin/alembic upgrade 20260609_session_device_refresh:20260609_user_devices_audit_provenance --sql` from `backend/` | Pass | Offline SQL добавляет пять nullable `user_devices` provenance columns и обновляет `alembic_version`. |
| `.venv/bin/alembic check` from `backend/` без synthetic env | Не учитывается как verification | Остановился до migration comparison из-за отсутствующих required local settings: `remnawave_token`, `jwt_secret`, `cryptobot_token`. Secret files не читались. |

## Покрытие тестами по запрошенным flow

| Flow | Coverage evidence | Статус |
|---|---|---|
| Repeated login on same web device | `backend/tests/integration/test_auth_realm_sessions.py:360` through `backend/tests/integration/test_auth_realm_sessions.py:419` | Covered на synthetic local data. Остаётся один stable device; предыдущие session/token revoked как `replaced_by_new_login`. |
| Refresh rotation | `backend/tests/integration/test_auth_realm_sessions.py:151` through `backend/tests/integration/test_auth_realm_sessions.py:195` | Covered. Одна principal session остаётся active; old refresh token consumed/rotated; new token linked as current. |
| Refresh replay detection | `backend/tests/integration/test_auth_realm_sessions.py:248` through `backend/tests/integration/test_auth_realm_sessions.py:312` | Covered. Benign race возвращает `401` без cookie clear; delayed replay revokes family/session and clears cookies. |
| Unique devices after refresh | `backend/tests/integration/test_auth_realm_sessions.py:459` through `backend/tests/integration/test_auth_realm_sessions.py:485` | Covered. Refresh не создаёт duplicate device. |
| Logout others | `backend/tests/integration/test_auth_realm_sessions.py:546` through `backend/tests/integration/test_auth_realm_sessions.py:579` | Covered. Current session остаётся valid; non-current session returns `401`; list drops to one device. |
| Delete selected device | `backend/tests/integration/test_auth_realm_sessions.py:638` through `backend/tests/integration/test_auth_realm_sessions.py:654` | Covered. Selected non-current device revoked; current session остаётся valid. |
| Logout all realm scoping | `backend/tests/integration/test_auth_realm_sessions.py:742` through `backend/tests/integration/test_auth_realm_sessions.py:760` | Covered. Admin realm session revoked; synthetic partner realm session remains active. |
| Trusted IP resolver | `backend/tests/unit/presentation/test_client_ip.py:21` through `backend/tests/unit/presentation/test_client_ip.py:180` | Covered. Spoofed headers игнорируются, если trusted proxy settings не разрешают их; malformed headers fall back closed. |
| Schema/migration foundation | `backend/tests/unit/infrastructure/test_session_device_schema_models.py:10` through `backend/tests/unit/infrastructure/test_session_device_schema_models.py:83` плюс offline Alembic SQL | Covered на model/schema/offline SQL level. |

## Остаточные риски

- Проверка использовала synthetic local tests, а не production-like traffic или real customer/payment data. Production data testing запрещён без Board approval.
- SQLite-backed integration helpers подтверждают application behavior, но не доказывают PostgreSQL lock contention при concurrent refresh requests. Source использует SQLAlchemy `with_for_update()`, offline SQL подтверждает migration topology; true concurrent Postgres stress test остаётся отдельной non-production task, если QA Lead потребует.
- `alembic check` всё ещё требует полностью настроенную disposable database/env для сравнения metadata с real schema. Offline SQL и model tests достаточны для read-only support scope этого heartbeat, но не заменяют release DBA validation.

## Context7 Evidence

Context7 docs checked: MCP quota unavailable. Fallback `ctx7` checked `/fastapi/fastapi/0.128.0` for request header access and `/websites/sqlalchemy_en_20` for `GenerativeSelect.with_for_update()` rendering `FOR UPDATE`. Pure CyberVPN contract/fixture conclusions use repo-local source and tests.
