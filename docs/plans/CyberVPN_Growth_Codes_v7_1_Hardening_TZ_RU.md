# Техническое задание v7.1 Hardening: устранение недостатков flexible invite system, Mini App auth и RSC/CORS production issues

**Проект:** CyberVPN
**Репозиторий:** `Beep206/CyberVPN`
**Актуальная базовая точка анализа:** commit `bfa85063a348a0064932f05ec83d51b84d6dec6e` — `feat: add flexible premium invite system`
**Дата подготовки:** 2026-06-29
**Статус документа:** новое ТЗ на доработку после v7
**Язык реализации:** backend — Python/FastAPI/SQLAlchemy/Alembic; frontend/admin — Next.js/React/TypeScript; Telegram Bot — Python

---

## 1. Цель ТЗ

Довести реализацию **Flexible Premium Invite System v7** до production-ready состояния и устранить выявленные недостатки:

1. Исправить production-проблему с переходами в личном кабинете, где RSC-запросы с `my.cyber-vpn.net` получают cross-origin redirect на `cyber-vpn.net`, из-за чего браузер блокирует запросы по CORS.
2. Исправить Mini App auth flow, чтобы Telegram Mini App не открывал Telegram/web login и не ломался на повторной отправке `initData`.
3. Довести admin invite inventory API до полноценного paginated contract.
4. Сделать `allowed_surfaces` в admin UI реально управляемым, а не всегда `web + miniapp + telegram_bot`.
5. Убрать путаницу между legacy invite creation и новым campaign-based invite flow.
6. Синхронизировать cabinet route metadata между proxy, auth redirect utils, navigation и backend runtime config.
7. Гарантировать end-to-end сценарий:
   - регистрация пользователя;
   - onboarding code prompt;
   - ввод invite code;
   - получение `premium_smart_ru` entitlement;
   - показ VPN connection UX;
   - создание дочерних invite codes;
   - отображение invite tree в admin.
8. Добавить обязательные тесты, smoke checks, runbook и критерии приёмки.

---

## 2. Контекст и найденные проблемы

### 2.1. Production RSC/CORS проблема

В production логах виден сценарий:

```text
Access to fetch at 'https://cyber-vpn.net/en-EN'
redirected from 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=...'
from origin 'https://my.cyber-vpn.net' has been blocked by CORS policy
Redirect is not allowed for a preflight request.
```

Затронутые routes:

```text
/en-EN/rewards
/en-EN/rewards/referral
/en-EN/rewards/gifts
/en-EN/rewards/invites
/en-EN/rewards/codes
/en-EN/rewards/notifications
/en-EN/messages
```

Фактическое поведение:

```text
my.cyber-vpn.net → rewards/messages RSC request → cyber-vpn.net/en-EN redirect → CORS block
```

Ожидаемое поведение:

```text
my.cyber-vpn.net → rewards/messages RSC request → no cross-origin redirect
```

Для Next.js RSC/internal navigation запросов допустимы только:

```text
200 / 204 / 304 / 404 / 401 / 403 на том же origin
```

Недопустимы:

```text
301 / 302 / 307 / 308 на другой origin
```

---

### 2.2. Mini App открывает Telegram login / auth page

Текущий вероятный сценарий ошибки:

```text
1. Пользователь уже авторизован в Telegram Mini App.
2. Backend поставил httpOnly customer cookies.
3. Пользователь обновляет Mini App или переходит на новый route.
4. Zustand state после reload снова isAuthenticated=false.
5. TelegramMiniAppAuthProvider повторно отправляет тот же Telegram initData.
6. Backend replay guard отклоняет повторный initData как уже использованный.
7. Frontend показывает Telegram auth/login error или уводит в login flow.
```

Корневая проблема:

```text
Mini App provider делает initData-auth до session restore.
```

Ожидаемое поведение:

```text
Mini App route → сначала восстановить customer session по cookie → если session валидна, не трогать initData → если session нет, только тогда использовать initData.
```

---

### 2.3. Admin invite inventory API не полноценный для больших списков

Сейчас `GET /admin/invite-codes` возвращает массив:

```json
[
  {
    "id": "...",
    "code_prefix": "..."
  }
]
```

Недостатки:

```text
- нет total;
- нет offset/limit в response;
- frontend не может построить нормальную пагинацию;
- нельзя корректно показывать “найдено N кодов”;
- сложно делать export по фильтрам;
- сложно диагностировать большие campaigns.
```

Нужен paginated contract.

---

### 2.4. Admin UI всегда отправляет все allowed surfaces

В backend и schema уже предусмотрен список `allowed_surfaces`, но frontend при создании кампании фактически всегда отправляет:

```ts
['web', 'miniapp', 'telegram_bot']
```

Это лишает оператора гибкости.

Ожидаемое поведение:

```text
Оператор в админке выбирает, где можно применять invite campaign:
☑ Web onboarding
☑ Telegram Mini App
☑ Telegram Bot
```

---

### 2.5. Legacy invite flow может путать операторов

Сейчас рядом существуют:

```text
POST /admin/invite-codes                         legacy invite creation
POST /admin/invite-campaigns                     new flexible campaign creation
POST /admin/invite-campaigns/{id}/batches        new root campaign batch creation
```

Риск:

```text
Админ может случайно создать legacy invite вместо plan-backed campaign invite.
```

Особенно опасно для `premium_smart_ru`, потому что legacy creation не должен использоваться для production viral invite campaigns.

---

### 2.6. Route metadata рассинхронизирована

Нужно централизовать или синхронизировать списки cabinet routes между:

```text
frontend/src/proxy.ts
frontend/src/features/auth/lib/redirect-path.ts
frontend/src/shared/cabinet-navigation/index.ts
backend CustomerSiteRuntimeConfig / client capabilities
admin customer-site runtime config
```

Минимальный обязательный cabinet allowlist:

```text
/dashboard
/subscriptions
/payment-history
/referral
/rewards
/rewards/referral
/rewards/gifts
/rewards/invites
/rewards/codes
/rewards/notifications
/messages
/wallet
/settings
/support
/servers
/onboarding
/monitoring
/analytics
/users
/partner
```

---

### 2.7. Требуется полный E2E premium invite сценарий

Обязательный production сценарий:

```text
1. Admin создаёт invite campaign:
   - grant_plan_code = premium_smart_ru
   - grant_duration_days = 365
   - child_invite_count = 10
   - child_grant_plan_code = premium_smart_ru
   - child_grant_duration_days = 365
   - child_invite_expiry_days = 30
   - max_generation_depth = 5

2. Admin публикует campaign.
3. Admin создаёт root batch.
4. Новый пользователь регистрируется.
5. Пользователь вводит root invite при onboarding.
6. Backend выдаёт premium_smart_ru entitlement.
7. Backend создаёт 10 child invites для этого пользователя.
8. Frontend/Mini App показывает:
   - активированный тариф;
   - срок доступа;
   - количество полученных инвайтов;
   - VPN URL;
   - QR;
   - инструкции iOS/Android/Windows/macOS/Linux.
9. Admin видит:
   - root code;
   - redemption;
   - child batch;
   - tree edge;
   - closure path;
   - analytics.
```

---

## 3. Область работ

### Входит в scope

```text
- frontend proxy hardening;
- backend customer site runtime hardening;
- route metadata sync;
- Mini App session-first auth;
- Mini App auth interceptor hardening;
- admin invite inventory pagination;
- admin allowed surfaces UI;
- legacy invite flow deprecation/hiding;
- E2E тесты для premium_smart_ru invite;
- smoke tests для production;
- deploy/runbook updates;
- мониторинг и acceptance criteria.
```

### Не входит в scope

```text
- полная переделка pricing catalog;
- изменение бизнес-цены premium_smart_ru;
- новая ML anti-fraud модель;
- PostHog/A/B testing;
- редизайн всего личного кабинета;
- миграция всех legacy invite codes в campaign codes задним числом, кроме совместимости чтения.
```

---

## 4. Приоритеты

### P0 — обязательно до production deploy

```text
1. RSC/CORS cross-origin redirect fix.
2. Mini App session-first auth fix.
3. Smoke tests для my.cyber-vpn.net rewards/messages RSC routes.
4. E2E test: onboarding invite → premium_smart_ru → connection bootstrap → 10 child invites.
```

### P1 — обязательно до закрытия v7.1

```text
5. Paginated admin invite inventory response.
6. Allowed surfaces UI.
7. Legacy invite UI deprecation/hiding.
8. Route metadata sync.
```

### P2 — желательно сразу, но можно отдельным PR

```text
9. Расширенные analytics rollups.
10. CSV export by filters.
11. Admin bulk actions для inventory.
12. Дополнительные bot/Mini App diagnostics.
```

---

# 5. Требования к RSC/CORS hardening

## 5.1. Единый принцип

Любой Next.js internal navigation/RSC request не должен получать cross-origin redirect.

Определять internal request по признакам:

```text
query contains _rsc
header RSC: 1
header Next-Router-State-Tree
header Next-Router-Prefetch
Accept contains text/x-component
Purpose: prefetch
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
x-nextjs-data: 1
```

Для таких запросов:

```text
- если route должен быть доступен на текущем origin → пропустить;
- если route не должен быть доступен → вернуть 404/403 на текущем origin;
- не делать redirect на другой host.
```

---

## 5.2. Frontend proxy изменения

Файл:

```text
frontend/src/proxy.ts
```

### Требование 5.2.1. Расширить internal navigation detection

Добавить функцию:

```ts
function isNextInternalNavigationRequest(request: NextRequest): boolean {
  const accept = request.headers.get('accept')?.toLowerCase() ?? '';
  const secFetchMode = request.headers.get('sec-fetch-mode')?.toLowerCase() ?? '';
  const secFetchDest = request.headers.get('sec-fetch-dest')?.toLowerCase() ?? '';
  const purpose = request.headers.get('purpose')?.toLowerCase() ?? '';

  return (
    request.nextUrl.searchParams.has('_rsc') ||
    request.headers.get('rsc') === '1' ||
    request.headers.has('next-router-state-tree') ||
    request.headers.has('next-router-prefetch') ||
    request.headers.get('x-nextjs-data') === '1' ||
    accept.includes('text/x-component') ||
    purpose === 'prefetch' ||
    (secFetchMode === 'cors' && secFetchDest === 'empty')
  );
}
```

### Требование 5.2.2. Запретить cross-origin redirect для internal request

Любой helper, который делает redirect, должен проходить через:

```ts
function redirectOrInternalNotFound(request: NextRequest, target: URL): NextResponse {
  if (isNextInternalNavigationRequest(request) && isCrossOriginTarget(request, target)) {
    return new NextResponse(null, { status: 404 });
  }

  return NextResponse.redirect(target);
}
```

Проверить все места:

```text
- public → cabinet redirect;
- cabinet → public redirect;
- cabinet_only redirect;
- maintenance redirect;
- auth route redirect;
- partner/referral canonical redirects;
- root cabinet redirect.
```

Для internal request не должно остаться прямого `NextResponse.redirect(target)` на другой origin.

### Требование 5.2.3. Разрешить все реальные cabinet routes

В `CABINET_ROUTE_SEGMENTS` добавить и держать синхронно:

```ts
const CABINET_ROUTE_SEGMENTS = new Set([
  'analytics',
  'dashboard',
  'delete-account',
  'messages',
  'monitoring',
  'onboarding',
  'partner',
  'payment-history',
  'referral',
  'rewards',
  'servers',
  'settings',
  'subscriptions',
  'support',
  'users',
  'wallet',
]);
```

### Требование 5.2.4. Добавить route-level allowlist для nested rewards

Проверить, что следующие paths не редиректятся с `my.cyber-vpn.net`:

```text
/en-EN/rewards
/en-EN/rewards/referral
/en-EN/rewards/gifts
/en-EN/rewards/invites
/en-EN/rewards/codes
/en-EN/rewards/notifications
/en-EN/messages
/ru-RU/rewards
/ru-RU/rewards/referral
/ru-RU/rewards/gifts
/ru-RU/rewards/invites
/ru-RU/rewards/codes
/ru-RU/rewards/notifications
/ru-RU/messages
```

---

## 5.3. Синхронизация redirect-path metadata

Файл:

```text
frontend/src/features/auth/lib/redirect-path.ts
```

Сейчас там должен быть тот же route set, что и в proxy. Обновить:

```ts
const CABINET_ROUTE_SEGMENTS = new Set([
  'analytics',
  'dashboard',
  'delete-account',
  'messages',
  'monitoring',
  'onboarding',
  'partner',
  'payment-history',
  'referral',
  'rewards',
  'servers',
  'settings',
  'subscriptions',
  'support',
  'users',
  'wallet',
]);
```

Лучше вынести shared-конфиг:

```text
frontend/src/shared/routing/cabinet-routes.ts
```

```ts
export const CABINET_ROUTE_SEGMENTS = [...];
export const CABINET_ALLOWED_PREFIXES = [...];
export function isCabinetRouteSegment(value: string): boolean;
export function isCabinetPath(pathname: string): boolean;
```

И импортировать в:

```text
frontend/src/proxy.ts
frontend/src/features/auth/lib/redirect-path.ts
frontend/src/shared/cabinet-navigation/index.ts
```

Если proxy не может импортировать часть shared-кода из-за runtime constraints, добавить тест, который сравнивает duplicated arrays.

---

## 5.4. Backend runtime config hardening

Файл:

```text
backend/src/application/services/config_service.py
```

Проверить и сохранить принцип:

```python
cabinet_allowed_prefixes = union(
    MANDATORY_CABINET_ALLOWED_PREFIXES,
    db_config.cabinet_allowed_prefixes,
)
```

`MANDATORY_CABINET_ALLOWED_PREFIXES` должен содержать:

```python
(
    "/dashboard",
    "/subscriptions",
    "/payment-history",
    "/referral",
    "/rewards",
    "/rewards/referral",
    "/rewards/gifts",
    "/rewards/invites",
    "/rewards/codes",
    "/rewards/notifications",
    "/messages",
    "/wallet",
    "/settings",
    "/support",
    "/servers",
    "/onboarding",
)
```

Добавить тест:

```text
DB config содержит устаревший cabinet_allowed_prefixes без /rewards и /messages
→ get_customer_site_runtime_config() всё равно возвращает /rewards и /messages
```

---

## 5.5. Production smoke tests

Добавить скрипт:

```text
scripts/smoke/customer_site_rsc_routes.sh
```

Проверки:

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST="https://my.cyber-vpn.net"
ROUTES=(
  "/en-EN/rewards"
  "/en-EN/rewards/referral"
  "/en-EN/rewards/gifts"
  "/en-EN/rewards/invites"
  "/en-EN/rewards/codes"
  "/en-EN/rewards/notifications"
  "/en-EN/messages"
  "/ru-RU/rewards"
  "/ru-RU/rewards/referral"
  "/ru-RU/rewards/gifts"
  "/ru-RU/rewards/invites"
  "/ru-RU/rewards/codes"
  "/ru-RU/rewards/notifications"
  "/ru-RU/messages"
)

for route in "${ROUTES[@]}"; do
  url="$HOST$route?_rsc=smoke"
  echo "Checking $url"
  headers="$(curl -sS -D - -o /dev/null \
    -H 'RSC: 1' \
    -H 'Accept: text/x-component' \
    "$url")"
  echo "$headers"
  if echo "$headers" | grep -i '^location: https://cyber-vpn.net' >/dev/null; then
    echo "FAIL: cross-origin redirect detected for $route"
    exit 1
  fi
  if echo "$headers" | grep -E '^HTTP/.* 30[1278]' >/dev/null; then
    echo "FAIL: redirect detected for internal RSC route $route"
    exit 1
  fi
done
```

Добавить в deploy pipeline после frontend deploy.

---

# 6. Требования к Mini App auth hardening

## 6.1. Session-first auth flow

Файл:

```text
frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx
```

Новый порядок:

```text
1. Detect Telegram Mini App runtime.
2. Если route не miniapp и runtime не miniapp → render children.
3. Если miniapp route/runtime:
   3.1. Сначала вызвать session restore.
   3.2. Если session валидна → set authenticated → render children.
   3.3. Если session отсутствует → проверить initData.
   3.4. Если initData есть → вызвать /auth/telegram/miniapp.
   3.5. Если /auth/telegram/miniapp вернул replay/401 → ещё раз session restore.
   3.6. Если session restore успешен → render children.
   3.7. Если нет → показать miniapp-only error state, без redirect на обычный login.
```

### Требование 6.1.1. Добавить `restoreMiniAppSession()`

В auth store или provider добавить функцию:

```ts
async function restoreMiniAppSession(): Promise<boolean> {
  try {
    await fetchUser(); // или dedicated customer session endpoint
    return useAuthStore.getState().isAuthenticated;
  } catch {
    return false;
  }
}
```

Лучше использовать customer realm endpoint:

```text
GET /api/v1/mobile/auth/me
```

или dedicated:

```text
GET /api/v1/auth/session
```

при условии, что он корректно работает для customer realm cookies.

### Требование 6.1.2. Не отправлять `initData`, если session уже восстановлена

Псевдокод:

```ts
const authenticateMiniApp = useCallback(async () => {
  setAuthError(null);

  const restored = await restoreMiniAppSession();
  if (restored) {
    invalidateMiniAppQueries();
    return;
  }

  if (!window.Telegram?.WebApp?.initData) {
    setAuthError(t('miniAppAutoAuth'));
    return;
  }

  try {
    const result = await telegramMiniAppAuth();
    // existing handling
  } catch (error) {
    const restoredAfterFailure = await restoreMiniAppSession();
    if (restoredAfterFailure) {
      invalidateMiniAppQueries();
      return;
    }
    setAuthError(getMiniAppAuthErrorMessage(error));
  }
}, [...]);
```

---

## 6.2. Axios interceptor Mini App request classification

Файл:

```text
frontend/src/lib/api/client.ts
```

Заменить:

```ts
const isMiniAppRequest = requestUrl.includes('/miniapp/');
```

на:

```ts
const currentPathname = typeof window !== 'undefined' ? window.location.pathname : '';
const isMiniAppRequest =
  requestUrl.includes('/miniapp/') ||
  requestUrl.includes('/auth/telegram/miniapp') ||
  requestUrl.includes('/customer/onboarding/connection/bootstrap') ||
  requestUrl.includes('/customer/onboarding/growth-code/apply') ||
  requestUrl.includes('/customer/onboarding/growth-code/preview') ||
  requestUrl.includes('/customer/onboarding/growth-code/skip') ||
  isMiniAppRoute(currentPathname);
```

Поведение:

```text
Если Mini App request получил 401/refresh failed:
- dispatch MINIAPP_AUTH_RESTORE_REQUIRED_EVENT;
- не делать window.location.href = /login;
- не открывать telegram-link/login page;
- оставить пользователя внутри Mini App error/retry state.
```

---

## 6.3. Backend: idempotent Mini App auth replay handling

Файл:

```text
backend/src/application/use_cases/auth/telegram_miniapp.py
backend/src/presentation/api/v1/auth/routes.py
```

Сейчас replay guard отклоняет повторный `initData`. Это правильно с точки зрения безопасности, но UX должен быть устойчивым.

Требования:

1. Если replay guard отклонил initData, backend не должен выдавать новую session.
2. Frontend должен пробовать session restore.
3. Backend response должен иметь machine-readable code:

```json
{
  "detail": {
    "code": "TELEGRAM_INIT_DATA_REPLAYED",
    "message": "Invalid or expired Telegram initData"
  }
}
```

Для обычного invalid HMAC/expired:

```json
{
  "detail": {
    "code": "TELEGRAM_INIT_DATA_INVALID_OR_EXPIRED",
    "message": "Invalid or expired Telegram initData"
  }
}
```

Так frontend сможет различать:

```text
replay → try session restore
invalid → show Mini App auth error
```

---

## 6.4. Mini App UX при ошибке

Если session restore и initData auth оба не сработали, показывать внутри Mini App:

```text
Не удалось подтвердить Telegram Mini App сессию.
[Повторить]
[Открыть бота]
[Закрыть]
```

Запрещено:

```text
- редиректить на /login;
- открывать Telegram Login Widget web page;
- показывать обычную web login form внутри Mini App.
```

---

# 7. Требования к Admin Invite Inventory API

## 7.1. Новый response contract

Изменить `GET /api/v1/admin/invite-codes`.

Сейчас:

```python
response_model=list[AdminInviteCodeSummaryResponse]
```

Нужно:

```python
class AdminInviteCodeInventoryResponse(BaseModel):
    items: list[AdminInviteCodeSummaryResponse]
    total: int
    offset: int
    limit: int
```

Endpoint:

```python
@admin_router.get(
    "",
    response_model=AdminInviteCodeInventoryResponse,
)
async def admin_list_invite_codes(...):
    ...
```

Response:

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 50
}
```

---

## 7.2. Backward compatibility

Если breaking change нежелателен, добавить новый endpoint:

```text
GET /admin/invite-codes/inventory
```

А старый `/admin/invite-codes` оставить временно.

Рекомендуемый вариант:

```text
- сразу перевести admin UI на paginated response;
- оставить legacy list только если есть внешние потребители.
```

---

## 7.3. Дополнительные поля summary

Расширить `AdminInviteCodeSummaryResponse`:

```python
class AdminInviteCodeSummaryResponse(BaseModel):
    id: UUID
    code_prefix: str | None
    code_hash: str | None
    status: str
    is_used: bool
    owner_user_id: UUID | None
    used_by_user_id: UUID | None
    used_at: datetime | None
    revoked_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    campaign_id: UUID | None
    campaign_key: str | None
    campaign_version_id: UUID | None
    batch_id: UUID | None

    root_invite_code_id: UUID | None
    parent_invite_code_id: UUID | None
    source_redemption_id: UUID | None
    generation_depth: int

    grant_mode: str | None
    grant_plan_id: UUID | None
    grant_plan_code: str | None
    grant_duration_days: int | None

    child_grant_plan_id: UUID | None
    child_grant_plan_code: str | None
    child_grant_duration_days: int | None
    child_policy_preview: dict[str, object] | None
```

---

## 7.4. Admin UI pagination

Файл:

```text
admin/src/features/growth/components/invite-codes-console.tsx
```

Добавить state:

```ts
const [inventoryPage, setInventoryPage] = useState(0);
const [inventoryLimit, setInventoryLimit] = useState(50);
```

Использовать response:

```ts
const inviteCodes = inviteCodesQuery.data?.items ?? [];
const inviteCodesTotal = inviteCodesQuery.data?.total ?? 0;
```

UI:

```text
Найдено: N
Страница: X
[Назад] [Вперёд]
Limit: 25 / 50 / 100
```

---

# 8. Требования к allowed surfaces UI

## 8.1. Campaign create form

Файл:

```text
admin/src/features/growth/components/invite-codes-console.tsx
```

Добавить в `initialCampaignForm`:

```ts
allowedSurfaces: {
  web: true,
  miniapp: true,
  telegram_bot: true,
}
```

Или:

```ts
allowedSurfaces: ['web', 'miniapp', 'telegram_bot']
```

UI блок:

```text
Allowed Surfaces
☑ Web onboarding
☑ Telegram Mini App
☑ Telegram Bot
```

При отправке:

```ts
allowed_surfaces: selectedAllowedSurfaces,
```

Запрещать submit, если список пуст:

```text
Выберите хотя бы одну поверхность применения кода.
```

---

## 8.2. Campaign settings tab

В settings/read-only view показывать:

```text
Allowed surfaces: Web, Mini App, Telegram Bot
```

В campaign list/table показывать compact chips:

```text
web · miniapp · bot
```

---

## 8.3. Tests

Добавить admin UI tests:

```text
- create campaign with only web surface;
- create campaign with only miniapp surface;
- create campaign with web + telegram_bot;
- prevent submit when no surfaces selected;
- payload contains exact selected allowed_surfaces.
```

---

# 9. Legacy invite flow deprecation / operator safety

## 9.1. UI разделение

В admin UI добавить явное разделение:

```text
Recommended: Flexible Campaign Invites
Legacy: Manual Invite Codes
```

Legacy блок должен быть:

```text
- скрыт по умолчанию;
- раскрывается через Advanced / Legacy;
- имеет warning banner.
```

Текст warning:

```text
Legacy invite codes do not create flexible campaign trees and must not be used for Premium Smart RU viral campaigns. Use Campaign Batch instead.
```

На русском:

```text
Legacy invite-коды не создают гибкое дерево кампании и не должны использоваться для Premium Smart RU viral campaigns. Используйте Campaign Batch.
```

---

## 9.2. Backend safety

В `POST /admin/invite-codes` добавить optional guard:

```text
Если plan_id относится к premium_smart_ru и request не содержит explicit legacy_acknowledgement=true → 422.
```

Schema:

```python
class AdminCreateInviteRequest(BaseModel):
    ...
    legacy_acknowledgement: bool = False
```

Validation:

```python
if plan.plan_code == "premium_smart_ru" and not body.legacy_acknowledgement:
    raise HTTPException(
        422,
        detail={
            "code": "PREMIUM_SMART_REQUIRES_FLEXIBLE_CAMPAIGN",
            "message": "Use invite campaigns for premium_smart_ru invites."
        },
    )
```

---

## 9.3. Audit

Для legacy creation добавить audit event:

```text
invite.legacy_manual_created
```

В audit details:

```json
{
  "legacy_acknowledgement": true,
  "plan_code": "premium_smart_ru",
  "risk": "legacy_path_used_for_premium_plan"
}
```

---

# 10. Premium Smart RU end-to-end hardening

## 10.1. Backend E2E test

Добавить integration test:

```text
backend/tests/integration/invites/test_premium_smart_ru_invite_campaign_flow.py
```

Сценарий:

```python
async def test_premium_smart_ru_invite_campaign_redeem_issues_child_invites_and_connection(...):
    # 1. seed premium_smart_ru plan
    # 2. configure Smart RU env/settings test doubles
    # 3. create campaign with child_invite_count=10
    # 4. publish campaign
    # 5. create root batch count=1
    # 6. create new mobile user
    # 7. ensure onboarding pending state
    # 8. apply invite code through onboarding endpoint
    # 9. assert response.status == completed
    # 10. assert response.connection_required == true
    # 11. assert entitlement.plan_code == premium_smart_ru
    # 12. assert child_invites.generated_count == 10
    # 13. assert DB has child batch with generation_depth=1
    # 14. assert tree edge exists
    # 15. assert closure rows exist
    # 16. call /customer/onboarding/connection/bootstrap
    # 17. assert available=true and subscription_url/qr_payload exist
```

---

## 10.2. Smart RU provisioning assertion

Test double должен проверять, что Remnawave payload содержит:

```json
{
  "external_squad_uuid": "...",
  "active_internal_squads": ["..."],
  "hwid_device_limit": 5,
  "trafficLimitStrategy": "..."
}
```

Если `premium_smart_ru` plan_code используется без Smart RU UUID settings, validation должна падать до publish:

```text
Validate campaign version → error REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID is required
```

---

## 10.3. Frontend onboarding test

Добавить test:

```text
frontend/src/features/customer-onboarding/__tests__/premium-invite-onboarding.test.tsx
```

Проверить:

```text
- preview показывает invite;
- apply возвращает entitlement premium_smart_ru;
- UI показывает активированный тариф;
- UI показывает “вы получили 10 инвайтов”;
- connection panel появляется;
- QR/link visible;
- кнопки “Я подключил” и “Перейти в личный кабинет” работают.
```

---

## 10.4. Mini App onboarding test

Проверить:

```text
miniapp onboarding code apply
→ premium_smart_ru entitlement
→ child_invites count 10
→ connection panel surface=miniapp
→ no redirect to /login
→ no telegram-link page
```

---

# 11. Admin API/client updates

## 11.1. Update generated OpenAPI types

После backend schema changes:

```bash
cd backend
python -m scripts.generate_openapi

cd ../frontend
npm run generate:api

cd ../admin
npm run generate:api

cd ../partner
npm run generate:api
```

Команды адаптировать под реальные scripts проекта.

---

## 11.2. Admin `growthApi` updates

Добавить/обновить types:

```ts
export interface AdminInviteCodeInventoryResponse {
  items: AdminInviteCodeSummaryResponse[];
  total: number;
  offset: number;
  limit: number;
}
```

Метод:

```ts
listInviteCodes: (params?: AdminInviteCodeInventoryParams) =>
  apiClient.get<AdminInviteCodeInventoryResponse>('/admin/invite-codes', { params })
```

Если используется `/inventory` endpoint:

```ts
apiClient.get<AdminInviteCodeInventoryResponse>('/admin/invite-codes/inventory', { params })
```

---

# 12. Tests

## 12.1. Backend unit tests

Добавить/обновить:

```text
backend/tests/unit/application/use_cases/invites/test_invite_campaigns.py
backend/tests/unit/application/use_cases/invites/test_redeem_invite_plan_backed.py
backend/tests/unit/application/use_cases/customer_onboarding/test_apply_allowed_code_types.py
backend/tests/unit/application/services/test_customer_site_runtime_config.py
backend/tests/unit/presentation/api/v1/invites/test_admin_invite_inventory.py
backend/tests/unit/presentation/api/v1/auth/test_telegram_miniapp_replay_codes.py
```

Покрыть:

```text
- create campaign with grant_plan_id;
- create campaign with grant_plan_code;
- child invite policy count/duration/plan;
- max_generation_depth;
- plan-backed grant snapshot;
- self-redemption block;
- require_no_active_access;
- blocked redemption ledger;
- tree edge and closure;
- paginated inventory response;
- Smart RU validation errors;
- runtime mandatory cabinet prefixes union;
- Telegram initData replay machine-readable error code.
```

---

## 12.2. Backend integration tests

Добавить:

```text
backend/tests/integration/invites/test_premium_smart_ru_invite_campaign_flow.py
backend/tests/integration/customer_onboarding/test_premium_invite_connection_bootstrap.py
backend/tests/integration/auth/test_telegram_miniapp_session_first.py
```

Сценарии:

```text
1. Full premium invite flow.
2. Repeated same invite redemption by same user is idempotent.
3. Same invite redemption by another user fails.
4. Child invites generated exactly once on retry.
5. Tree closure is stable on retry.
6. Mini App valid cookie + replayed initData restores session.
7. Mini App invalid initData + no cookie shows auth error without redirect.
```

---

## 12.3. Frontend tests

Добавить:

```text
frontend/src/__tests__/proxy-rsc-routes.test.ts
frontend/src/features/auth/components/__tests__/TelegramMiniAppAuthProvider.test.tsx
frontend/src/features/customer-onboarding/__tests__/PostRegistrationGrowthCodePrompt.test.tsx
frontend/src/features/auth/lib/__tests__/redirect-path.test.ts
```

Покрыть:

```text
- RSC request to rewards/messages on cabinet host does not redirect to public host;
- normal browser request to public marketing route on cabinet host can redirect according to policy;
- Mini App route restores session before sending initData;
- replayed initData fallback restores session;
- failed Mini App auth does not call window.location.href=/login;
- redirect-path route set includes rewards/messages/support/onboarding;
- onboarding invite success shows entitlement and child invites.
```

---

## 12.4. Admin tests

Добавить:

```text
admin/src/features/growth/components/__tests__/invite-codes-console.test.tsx
```

Покрыть:

```text
- inventory consumes paginated response;
- pagination controls work;
- allowed surfaces checkboxes affect payload;
- legacy panel hidden by default;
- premium_smart_ru campaign creation payload has selected plan/duration/child count;
- batch creation displays raw codes only from create/export response;
- tree lookup renders nodes and edges.
```

---

## 12.5. Telegram Bot tests

Добавить/обновить:

```text
services/telegram-bot/tests/unit/test_connection_flow.py
services/telegram-bot/tests/unit/test_invite_code_apply.py
```

Покрыть:

```text
- /code applies invite through telegram_bot surface;
- backend creates pending onboarding state if missing;
- child invite count is shown in bot response;
- /connect works independently from post_registration_code_prompt_enabled if connection_bootstrap_enabled=true;
- group/supergroup/channel cannot receive raw config.
```

---

# 13. Deployment / smoke / rollback

## 13.1. Pre-deploy checklist

```text
- Alembic migration applied on staging.
- OpenAPI regenerated.
- Admin/frontend/partner generated API types updated.
- Production env has Smart RU UUIDs.
- customer_site.runtime checked.
- customer_onboarding.runtime checked.
- Telegram bot internal secret configured.
- Mini App domain configured in BotFather.
```

---

## 13.2. Required production smoke commands

### RSC no-redirect smoke

```bash
./scripts/smoke/customer_site_rsc_routes.sh
```

### Client capabilities smoke

```bash
curl -s https://cyber-vpn.net/api/v1/client/capabilities \
  | jq '.site.cabinet_allowed_prefixes'
```

Must contain:

```text
/rewards
/rewards/referral
/rewards/gifts
/rewards/invites
/rewards/codes
/rewards/notifications
/messages
/onboarding
```

### Mini App auth smoke

Manual or automated:

```text
1. Open Mini App in Telegram.
2. Confirm no web Telegram login page appears.
3. Refresh Mini App.
4. Confirm session is restored without replay error.
5. Navigate to onboarding/code.
6. Apply test invite.
7. Confirm connection panel appears.
```

### Premium invite smoke

```text
1. Admin create campaign premium_smart_ru_smoke.
2. Publish campaign.
3. Create root batch count=1.
4. Register test user.
5. Apply invite in onboarding.
6. Confirm entitlement premium_smart_ru.
7. Confirm 10 child invites.
8. Confirm invite tree root has 1 redemption and child batch.
9. Confirm connection bootstrap available.
10. Revoke test campaign/batch after smoke.
```

---

## 13.3. Rollback plan

Если RSC/CORS сохраняется:

```text
1. Переключить CUSTOMER_SITE_MODE_FALLBACK=full_site.
2. В customer_site.runtime временно cabinet_marketing_route_action=allow.
3. Purge CDN cache.
4. Перезапустить frontend container.
5. Запустить RSC smoke.
```

Если Mini App auth ломается:

```text
1. Временно отключить replay strict failure UX только на frontend через session-first retry.
2. Не отключать backend replay guard.
3. Проверить customer cookies path/domain.
4. Проверить /mobile/auth/me из Mini App WebView.
```

Если invite campaign redemption ломается:

```text
1. Pause campaign.
2. Revoke unused root/child batches.
3. Reverse affected redemptions только если entitlement выдан ошибочно.
4. Export audit snapshot.
```

---

# 14. Monitoring and observability

## 14.1. Metrics

Добавить/проверить метрики:

```text
customer_site_rsc_cross_origin_redirect_blocked_total
customer_site_rsc_cross_origin_redirect_attempt_total
miniapp_session_restore_attempt_total
miniapp_session_restore_success_total
miniapp_initdata_auth_attempt_total
miniapp_initdata_replay_recovered_total
miniapp_initdata_auth_failure_total
invite_campaign_created_total
invite_campaign_batch_created_total
invite_campaign_redemption_total
invite_campaign_child_invites_issued_total
invite_campaign_tree_edge_created_total
invite_campaign_connection_bootstrap_success_total
```

## 14.2. Logs

Добавить structured logs:

```text
customer_site_internal_redirect_suppressed
miniapp_session_restore_success
miniapp_initdata_replay_session_restored
miniapp_initdata_auth_failed
invite_campaign_redemption_completed
invite_campaign_child_batch_created
invite_tree_closure_created
```

Запрещено логировать:

```text
- raw invite codes;
- raw Telegram initData;
- raw VPN subscription URL;
- access/refresh tokens;
- QR payload raw value.
```

---

# 15. Security requirements

1. Raw invite codes возвращаются только:
   - при create batch response;
   - при explicit export endpoint;
   - при наличии permission `GROWTH_CODE_SETS_EXPORT`.
2. Raw invite codes не должны попадать в logs, analytics, metrics, audit details.
3. Telegram Mini App `initData` не хранить в БД и не логировать.
4. Replay guard нельзя отключать на backend.
5. Для Telegram Bot raw VPN config запрещено отправлять в group/supergroup/channel.
6. Connection session ledger хранит только hash config, без raw URL.
7. Admin export должен писать audit entry.
8. Reversal должен отзывать unused child invites и entitlement grant.

---

# 16. Acceptance Criteria / Definition of Done

## 16.1. RSC/CORS

```text
✅ Все rewards/messages RSC smoke routes не редиректятся на cyber-vpn.net.
✅ В browser console нет CORS error “Redirect is not allowed for a preflight request”.
✅ Переходы по пунктам личного кабинета работают без F5.
✅ Route sets синхронизированы в proxy и redirect-path.
```

## 16.2. Mini App

```text
✅ Mini App сначала восстанавливает session, потом использует initData.
✅ Повторное открытие Mini App не вызывает replay error UX.
✅ Mini App не открывает обычную Telegram/web login page.
✅ 401 на /auth/telegram/miniapp не редиректит на /login.
✅ Error state остаётся внутри Mini App и имеет Retry/Open bot.
```

## 16.3. Invite campaigns

```text
✅ Admin может создать campaign на premium_smart_ru.
✅ Admin может задать grant plan, grant duration, child invite count, child grant plan, child duration, expiry, max depth.
✅ Root batch создаёт raw codes only once.
✅ User onboarding invite redemption выдаёт premium_smart_ru entitlement.
✅ После redemption создаётся ровно 10 child invites при настройке count=10.
✅ Retry redemption не создаёт второй child batch.
✅ Tree edge и closure создаются.
✅ Admin tree отображает root, nodes, edges, stats.
```

## 16.4. Admin UI/API

```text
✅ Inventory endpoint возвращает items/total/offset/limit.
✅ Admin UI показывает pagination.
✅ allowed surfaces выбираются оператором.
✅ Legacy invite creation скрыт или помечен как legacy-danger.
✅ premium_smart_ru legacy creation требует acknowledgement или блокируется.
```

## 16.5. Tests and deployment

```text
✅ Backend unit/integration tests проходят.
✅ Frontend tests проходят.
✅ Admin tests проходят.
✅ Telegram Bot tests проходят.
✅ Production smoke scripts добавлены в deploy pipeline.
✅ Runbook обновлён.
```

---

# 17. Рекомендуемый порядок реализации

## PR 1 — P0 RSC/CORS fix

```text
- proxy internal detection hardening;
- redirectOrInternalNotFound everywhere;
- route set sync;
- backend mandatory prefixes test;
- smoke script;
- deploy pipeline hook.
```

## PR 2 — P0 Mini App auth fix

```text
- session-first provider;
- interceptor miniapp classification;
- backend machine-readable replay error;
- Mini App tests;
- no login redirect guarantee.
```

## PR 3 — P0 Premium invite E2E

```text
- backend E2E premium_smart_ru campaign flow;
- connection bootstrap assertion;
- frontend onboarding success test;
- Telegram Bot /code test.
```

## PR 4 — P1 Admin/API polish

```text
- paginated inventory response;
- admin pagination UI;
- allowed surfaces UI;
- legacy invite warning/guard;
- OpenAPI regen.
```

## PR 5 — P1 Observability/runbook

```text
- metrics/logs;
- runbook updates;
- rollback instructions;
- production dashboards.
```

---

# 18. Notes for implementation

1. Не удалять backward compatibility без явной миграции.
2. Не ломать существующие gift/promo/referral flows.
3. Не выключать backend replay protection для Telegram initData.
4. Не возвращать raw codes в inventory list.
5. Не хранить raw VPN URLs в connection session ledger.
6. Везде использовать idempotency для invite batch/redemption/child invite generation.
7. Любой production redirect между `my.cyber-vpn.net` и `cyber-vpn.net` должен быть проверен на RSC/internal request safety.

---

## 19. Минимальная ручная проверка после релиза

```text
1. Открыть https://my.cyber-vpn.net/ru-RU/dashboard.
2. Перейти в Rewards → Invites.
3. Перейти в Rewards → Gifts.
4. Перейти в Rewards → Notifications.
5. Перейти в Messages.
6. Убедиться, что console не содержит CORS redirect errors.
7. Открыть Mini App в Telegram.
8. Обновить Mini App.
9. Убедиться, что не открывается Telegram/web login page.
10. Применить тестовый premium_smart_ru invite.
11. Убедиться, что показан VPN QR/link.
12. Убедиться, что создано 10 child invites.
13. Проверить дерево в admin.
```

---

# 20. Финальный результат

После выполнения v7.1 система должна быть готова к production-использованию flexible invite campaigns:

```text
- без CORS/RSC поломок в кабинете;
- без неправильного Telegram login в Mini App;
- с полноценным premium_smart_ru onboarding invite flow;
- с гибкими настройками campaign policy;
- с деревом приглашений;
- с admin inventory/pagination;
- с понятным разделением legacy и new invite flows;
- с тестами, smoke checks и rollback plan.
```
