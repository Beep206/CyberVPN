# CYBA-607 API / UI Mismatch Findings

Дата проверки: 2026-06-09

## Баги

Подтверждённых backend/API bugs в этом read-only проходе не найдено. Targeted backend tests для refresh/session/device/IP behavior прошли на synthetic local data.

## Product gaps / downstream UI follow-up

### CYBA-607-GAP-001 - Customer settings UI всё ещё реализует "Logout All Others" как несколько `DELETE /auth/devices/{device_id}` вместо нового atomic endpoint

Серьёзность: P2 product/API adoption gap

Окружение: source inspection в текущем dirty worktree, только local repo. Browser UI в этой backend support роли не запускался.

Роль/состояние пользователя: authenticated customer web user с минимум двумя active web devices, один current и один или несколько non-current.

Шаги воспроизведения по source:

1. Inspect `frontend/src/lib/api/auth.ts:488`; API wrapper exposes `authApi.logoutOtherDevices()` for `POST /api/v1/auth/devices/logout-others`.
2. Inspect `frontend/src/app/[locale]/(dashboard)/settings/sections/DevicesSection.tsx:83`.
3. Inspect `frontend/src/app/[locale]/(dashboard)/settings/sections/DevicesSection.tsx:92` through `frontend/src/app/[locale]/(dashboard)/settings/sections/DevicesSection.tsx:94`.
4. Inspect tests at `frontend/src/app/[locale]/(dashboard)/settings/sections/__tests__/DevicesSection.test.tsx:262` through `frontend/src/app/[locale]/(dashboard)/settings/sections/__tests__/DevicesSection.test.tsx:290`.

Ожидаемый результат:

- Customer UI использует `POST /api/v1/auth/devices/logout-others` для команды "Logout All Others", совпадает с новым backend contract и избегает partial success/failure при нескольких remote device deletes.

Фактический результат:

- UI вычисляет `otherDevices` и вызывает `authApi.logoutDevice(d.device_id)` для каждого non-current device через `Promise.all`.
- Существующие UI tests mock-ят несколько `DELETE /auth/devices/{device_id}` calls вместо atomic `POST /auth/devices/logout-others`.

Sanitized evidence:

- Backend endpoint существует в `backend/src/presentation/api/v1/auth/routes.py:3274` и возвращает `LogoutOthersResponse`.
- Frontend API wrapper существует в `frontend/src/lib/api/auth.ts:488`.
- UI component всё ещё вызывает per-device delete в `frontend/src/app/[locale]/(dashboard)/settings/sections/DevicesSection.tsx:93`.
- Backend test `backend/tests/integration/test_auth_realm_sessions.py:552` проверяет atomic endpoint.

Рекомендуемый owner/action:

- Customer frontend owner: переключить "Logout All Others" в `DevicesSection` на `authApi.logoutOtherDevices()`, затем обновить MSW tests так, чтобы ожидался один `POST /auth/devices/logout-others` call и использовалась новая форма `DeviceSessionListResponse`.

Context7 docs checked: N/A - repo-local API/UI contract adoption gap.

### CYBA-607-GAP-002 - Admin и partner auth API wrappers ещё не expose helper для `POST /auth/devices/logout-others`

Серьёзность: P3 product/API adoption gap

Окружение: source inspection в текущем dirty worktree, только local repo.

Роль/состояние пользователя: authenticated admin или partner operator с несколькими active web devices.

Шаги воспроизведения по source:

1. Inspect generated OpenAPI/TS contracts: `admin/src/lib/api/generated/types.ts:519` and `partner/src/lib/api/generated/types.ts:519` include `/api/v1/auth/devices/logout-others`.
2. Inspect `admin/src/lib/api/auth.ts:431` through `admin/src/lib/api/auth.ts:457`.
3. Inspect `partner/src/lib/api/auth.ts:426` through `partner/src/lib/api/auth.ts:452`.

Ожидаемый результат:

- Admin и partner auth wrappers expose typed helper for `POST /auth/devices/logout-others`, consistent with generated contracts and frontend/customer wrapper.

Фактический результат:

- Admin и partner wrappers expose `listDevices`, `logoutDevice`, and `logoutAllDevices`, но не имеют `logoutOtherDevices` helper.

Sanitized evidence:

- Generated types include `LogoutOthersResponse`.
- `frontend/src/lib/api/auth.ts:260` exports `LogoutOthersResponse`, and `frontend/src/lib/api/auth.ts:488` exposes `logoutOtherDevices`.
- Admin/partner wrappers stop at per-device delete and `logout-all`.

Рекомендуемый owner/action:

- Admin/partner frontend owner: добавить typed `logoutOtherDevices` helper и обновить security/session UI, если ему нужна safer atomic command.

Context7 docs checked: N/A - repo-local API/UI contract adoption gap.

## Не баги

- `DeviceSessionListResponse.total` остаётся как backward-compatible alias. Новый UI должен предпочитать `total_devices`, но старые reads of `total` backend contract сейчас не ломает.
- `device_limit` и `remaining_devices` nullable by design, когда realm/customer device limit не enforced.
- Raw token values не ожидаются в `WebLoginResponse`; web login использует httpOnly cookies.

## Не тестировалось / заблокированные области

- Browser UI не запускался в этом backend support heartbeat; screenshot/video evidence не создавались.
- Admin/partner security session consoles не проходили browser testing.
- Mobile `/api/v1/mobile/auth/devices` отделён от web auth contract pass и не ретестился.

## Context7 Evidence

Context7 docs checked: N/A - manual API/UI source-contract inspection. Backend behavior evidence находится в `backend-data-support-notes.md`.
