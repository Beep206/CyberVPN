# CYBA-607 Blocked Flow Diagnosis

Дата проверки: 2026-06-09

## Исполнительное резюме

Backend/data/auth-flow blockers, которые мешали [CYBA-607](/CYBA/issues/CYBA-607) подготовить evidence, сняты для synthetic local QA. Targeted tests прошли, generated contracts содержат новый web device/logout surface, Alembic topology/offline SQL для новой provenance migration согласованы.

Это не production-data signoff. Это backend QA evidence handoff для downstream aggregate gate [CYBA-611](/CYBA/issues/CYBA-611).

## Матрица flow

| Flow | Текущий статус | Evidence | Owner/action |
|---|---|---|---|
| Login creates stable device/session | Unblocked | `backend/tests/integration/test_auth_realm_sessions.py:360` through `backend/tests/integration/test_auth_realm_sessions.py:419`; targeted pytest passed. | Нет backend QA blocker. |
| Refresh rotation | Unblocked | `backend/src/application/use_cases/auth/refresh_token.py:130`, `backend/src/application/use_cases/auth/refresh_token.py:199`, `backend/tests/integration/test_auth_realm_sessions.py:151` through `backend/tests/integration/test_auth_realm_sessions.py:195`. | Нет backend QA blocker. |
| Refresh replay detection | Unblocked | `backend/src/application/use_cases/auth/refresh_token.py:289`; `backend/tests/integration/test_auth_realm_sessions.py:248` through `backend/tests/integration/test_auth_realm_sessions.py:312`. | Нет backend QA blocker. |
| Unique device list after refresh | Unblocked | `backend/src/presentation/api/v1/auth/routes.py:3179`; `backend/tests/integration/test_auth_realm_sessions.py:459` through `backend/tests/integration/test_auth_realm_sessions.py:485`. | Нет backend QA blocker. |
| `logout-others` | Backend unblocked; customer UI adoption gap remains | Backend route `backend/src/presentation/api/v1/auth/routes.py:3274`; backend test `backend/tests/integration/test_auth_realm_sessions.py:552`; UI gap в `api-ui-mismatch-findings.md`. | Customer frontend owner должен переключить UI с per-device deletes на atomic helper. |
| Selected-device remote logout | Unblocked | `backend/src/presentation/api/v1/auth/routes.py:3341`; `backend/tests/integration/test_auth_realm_sessions.py:638` through `backend/tests/integration/test_auth_realm_sessions.py:654`. | Нет backend QA blocker. |
| `logout-all` realm scoping | Unblocked | `backend/src/presentation/api/v1/auth/routes.py:1241`; `backend/tests/integration/test_auth_realm_sessions.py:742` through `backend/tests/integration/test_auth_realm_sessions.py:760`. | Нет backend QA blocker. |
| Trusted client IP provenance | Unblocked | `backend/src/presentation/dependencies/client_ip.py`; `backend/tests/unit/presentation/test_client_ip.py:21` through `backend/tests/unit/presentation/test_client_ip.py:180`. | Нет backend QA blocker. |
| Migration/provenance columns | Partially unblocked for QA; disposable DB validation remains optional follow-up | `alembic heads` shows `20260609_user_devices_audit_provenance (head)`; offline SQL generation passed for `20260609_session_device_refresh:20260609_user_devices_audit_provenance`. | DBA/backend owner может run full `alembic check`/upgrade на disposable Postgres DB, если release gate требует DB-level validation. |

## Текущий root cause summary

Изначально blocked state была вызвана implementation dependencies, а не отсутствием QA steps:

- Refresh rotation зависела от corrected stable device/session model, чтобы rotation не привязывалась к fingerprint-derived или unpeppered device identity.
- Device/logout API behavior зависело от unique active stable devices и realm-scoped revocation semantics.
- Auth/session audit and rate-limit evidence зависели от trusted client IP resolver вместо прямого доверия spoofable forwarded headers.

Эти зависимости теперь реализованы в текущем worktree и покрыты targeted tests. Оставшиеся пункты являются downstream adoption и release validation gaps, а не backend flow blockers.

## Остаточные риски / follow-up

- `api-ui-mismatch-findings.md` фиксирует два downstream UI/API adoption gaps вокруг `POST /auth/devices/logout-others`.
- True PostgreSQL concurrent refresh stress test не запускался. Code использует SQLAlchemy `with_for_update()`, tests покрывают application invariants, но SQLite helpers не доказывают lock contention behavior.
- Full `alembic check` не завершён, потому что unconfigured local settings fail before DB comparison. Offline SQL generation with synthetic env passed; disposable Postgres DB check остаётся backend/DBA follow-up только если QA Lead потребует.
- Browser screenshots/videos не создавались, потому что эта роль выполняет backend/data support, а browser UI QA был явно out of scope для `CYBA-607`.

## Disposition

Backend/data/auth-flow evidence по этой issue завершён. Recommended next owner: [CYBA-611](/CYBA/issues/CYBA-611) aggregate QA release gate consumes these artifacts, а customer/admin/partner frontend owners обрабатывают non-blocking API adoption gaps.

## Context7 Evidence

Context7 docs checked: MCP quota unavailable. Fallback `ctx7` checked `/fastapi/fastapi/0.128.0` for request header access and `/websites/sqlalchemy_en_20` for `with_for_update()` / `FOR UPDATE` behavior. Pure blocked-flow status uses repo-local source, tests, and Paperclip blocker comments.
