# Техническое задание v7.3
# Production hardening Telegram Mini App / Telegram Bot / Edge Routing для CyberVPN

**Проект:** CyberVPN
**Версия ТЗ:** v7.3
**Дата:** 2026-06-29
**Основание:** после внедрения v7.2 lifetime invite system production продолжает показывать проблемы Telegram Mini App и Telegram Bot `/start`.

---

## 1. Цель

Довести Telegram-направление до production-ready состояния:

1. Telegram Mini App должен открывать именно Mini App, а не страницу регистрации, dashboard или web auth flow.
2. `/start` в Telegram Bot должен работать в корректном onboarding-flow даже при `REGISTRATION_ENABLED=false`.
3. Telegram webhook не должен возвращать `401 Unauthorized`.
4. Внешние домены `cyber-vpn.net`, `my.cyber-vpn.net`, `api.cyber-vpn.net` должны смотреть на один актуальный production runtime.
5. `client_capabilities` снаружи и на origin должны быть синхронизированы.
6. В `cabinet_only` режиме Mini App должен быть явно разрешён и протестирован.
7. RSC/CORS cross-origin redirect должен быть исключён на уровне frontend proxy, Caddy/edge и smoke-тестов.
8. Telegram invite/lifetime campaign flow должен быть доступен через Bot/Mini App.

---

## 2. Текущее состояние и выводы

### 2.1. v7.2 lifetime invite реализован в коде

В коде уже есть:

- `InviteAccessDurationMode`: `fixed_days | lifetime`;
- `InviteCodeExpiryMode`: `relative | absolute | none`;
- `grant_device_limit_override`;
- `child_grant_device_limit_override`;
- lifetime entitlement snapshots;
- child invite lifetime policy;
- admin UI preset `Premium Smart RU Lifetime`;
- migration `20260629_growth_invite_lifetime_v72.py`;
- deploy evidence для `main-6865e021-growth-v72-lifetime-20260629`.

### 2.2. Mini App проблема

Диагностика production показала:

```text
https://cyber-vpn.net/ru-RU/miniapp
→ 307
→ https://my.cyber-vpn.net/ru-RU/dashboard
```

Причина:

```text
customer_site_mode = cabinet_only
allowed_path_prefixes не содержит /miniapp
```

При этом локальный origin может отдавать `/ru-RU/miniapp` как `200 OK`, что указывает на рассинхрон external edge/runtime.

### 2.3. Telegram Bot `/start` проблема

Диагностика показала:

```text
Telegram Bot API getWebhookInfo:
pending_update_count: 4
last_error_message: Wrong response from the webhook: 401 Unauthorized
```

Дополнительно backend route:

```text
POST /api/v1/telegram/bot/user
```

сейчас блокирует создание нового Telegram пользователя, если:

```text
REGISTRATION_ENABLED=false
username не входит в telegram_bot_bootstrap_usernames
```

В результате bot `/start` для нового Telegram user может падать в generic error:

```text
❌ Не удалось зарегистрировать аккаунт. Попробуйте позже или напишите в поддержку.
```

---

## 3. Product decision: где должен жить Mini App

Выбрать один canonical URL.

### Вариант A — Mini App на публичном домене

```text
https://cyber-vpn.net/ru-RU/miniapp
```

Тогда `/miniapp` должен быть разрешён в public allowlist даже в `cabinet_only`.

### Вариант B — Mini App на cabinet-домене

```text
https://my.cyber-vpn.net/ru-RU/miniapp
```

Тогда `/miniapp` должен быть разрешён в cabinet allowlist, а bot menu button должен использовать `my.cyber-vpn.net`.

### Рекомендация

Использовать **вариант A**:

```text
TELEGRAM_MINIAPP_URL=https://cyber-vpn.net/ru-RU/miniapp
```

Mini App является отдельной Telegram surface, а не обычной marketing/dashboard страницей. Поэтому её нужно явно пропускать на public host даже при `cabinet_only`.

---

## 4. Backend changes

## 4.1. CustomerSiteRuntimeConfig: разрешить Mini App в cabinet_only

Файл:

```text
backend/src/application/services/config_service.py
```

Добавить mandatory public allowed prefixes:

```python
MANDATORY_PUBLIC_ALLOWED_PREFIXES: tuple[str, ...] = (
    "/miniapp",
    "/miniapp/",
)
```

Добавить в `CustomerSiteRuntimeConfig.allowed_path_prefixes`:

```python
"/miniapp",
```

Добавить в `CustomerSiteRuntimeConfig.cabinet_allowed_prefixes` тоже:

```python
"/miniapp",
```

При чтении runtime config делать union:

```python
allowed_path_prefixes = _union_path_tuples(
    MANDATORY_PUBLIC_ALLOWED_PREFIXES,
    configured_allowed_path_prefixes,
)
```

Требование: даже если в БД лежит старый `customer_site.runtime`, `/miniapp` должен оставаться разрешённым.

---

## 4.2. Client capabilities: явно отдавать Mini App allowlist

Endpoint:

```text
GET /api/v1/client/capabilities
```

В поле `site` должны присутствовать:

```json
{
  "allowed_path_prefixes": ["/miniapp"],
  "cabinet_allowed_prefixes": ["/miniapp"]
}
```

Если `customer_site_mode=cabinet_only`, внешний response всё равно должен содержать `/miniapp`.

---

## 4.3. Telegram Bot registration flow при закрытой публичной регистрации

Файл:

```text
backend/src/presentation/api/v1/telegram/routes.py
```

Сейчас при `REGISTRATION_ENABLED=false` новый bot user блокируется, если username не в allowlist.

Нужно ввести отдельный режим:

```python
telegram_bot_registration_mode: Literal[
    "disabled",
    "allow_existing_only",
    "allow_with_invite_code",
    "allow_pending_onboarding",
    "allow_all_bot_users",
]
```

Переменные окружения:

```env
TELEGRAM_BOT_REGISTRATION_MODE=allow_pending_onboarding
TELEGRAM_BOT_ALLOW_REGISTRATION_WHEN_PUBLIC_CLOSED=true
```

### Режимы

#### `disabled`

Новых пользователей не создавать.

#### `allow_existing_only`

Только уже существующие пользователи.

#### `allow_with_invite_code`

Новый пользователь создаётся только при `/start code_<CODE>` или `/code <CODE>`.

#### `allow_pending_onboarding`

Новый пользователь создаётся в статусе `pending_onboarding`, без активного доступа, но может открыть Mini App и ввести код.

#### `allow_all_bot_users`

Новый пользователь создаётся независимо от public registration. Использовать только для временного публичного теста.

### Рекомендация для production

```env
TELEGRAM_BOT_REGISTRATION_MODE=allow_pending_onboarding
```

---

## 4.4. Изменить `POST /telegram/bot/user`

При создании нового Telegram bot user:

1. Проверить `X-Telegram-Bot-Secret`.
2. Если пользователь существует — обновить profile и вернуть его.
3. Если пользователь новый:
   - если registration mode запрещает создание — вернуть structured error;
   - если mode `allow_pending_onboarding` — создать `AdminUserModel` и `MobileUserModel`;
   - создать `customer_onboarding_state` со `source_channel="telegram_bot"`;
   - не выдавать trial/access автоматически;
   - вернуть `requires_onboarding=true`.

Response расширить:

```json
{
  "uuid": "...",
  "telegram_id": 123,
  "status": "pending_onboarding",
  "requires_onboarding": true,
  "onboarding_entrypoint": "miniapp",
  "miniapp_url": "https://cyber-vpn.net/ru-RU/miniapp/onboarding/code"
}
```

---

## 4.5. Structured error для bot registration

Вместо generic 403 сделать:

```json
{
  "code": "TELEGRAM_BOT_REGISTRATION_REQUIRES_INVITE",
  "message_key": "telegram.registration.requiresInvite",
  "allowed_actions": ["open_miniapp", "enter_code", "contact_support"]
}
```

или:

```json
{
  "code": "TELEGRAM_BOT_REGISTRATION_DISABLED",
  "message_key": "telegram.registration.disabled"
}
```

---

## 5. Telegram Bot changes

## 5.1. `/start` не должен показывать generic registration failed

Файл:

```text
services/telegram-bot/src/handlers/start.py
```

Сейчас generic catch:

```python
except Exception:
    await message.answer(i18n.get("error-registration-failed"))
```

Нужно:

1. Ловить `APIError` отдельно.
2. Проверять `exc.status_code` и `exc.detail`.
3. Если backend вернул `TELEGRAM_BOT_REGISTRATION_REQUIRES_INVITE`:
   - показать понятное сообщение;
   - предложить кнопку Mini App;
   - предложить `/code <код>`.
4. Если backend вернул `TELEGRAM_BOT_REGISTRATION_DISABLED`:
   - показать закрытый режим;
   - предложить support.
5. Логировать structured event:

```python
logger.warning(
    "telegram_bot_registration_blocked",
    user_id=user_id,
    status_code=exc.status_code,
    detail_code=detail_code,
)
```

---

## 5.2. Bot `/start` flow при `allow_pending_onboarding`

Если backend вернул `requires_onboarding=true`, бот должен ответить:

```text
Добро пожаловать в CyberVPN.
Чтобы активировать доступ, откройте Mini App и введите invite / gift / promo code.
```

Кнопки:

```text
[Открыть Mini App]
[Ввести код в боте]
[Поддержка]
```

Mini App URL должен быть из backend response или settings:

```text
https://cyber-vpn.net/ru-RU/miniapp/onboarding/code
```

---

## 5.3. `/code <код>` должен работать для нового Telegram user

Если пользователь ещё не существует:

1. Bot вызывает `POST /telegram/bot/user`.
2. Backend создаёт pending onboarding user.
3. Bot вызывает:

```text
POST /customer/onboarding/growth-code/apply
```

с:

```http
X-Telegram-Bot-Secret: ...
```

payload:

```json
{
  "code": "....",
  "source_surface": "telegram_bot",
  "telegram_id": 123,
  "idempotency_key": "tg-code:{telegram_id}:{message_id}:{hash}"
}
```

4. Если код успешен — бот показывает connection UX.

---

## 6. Telegram webhook 401 fix

## 6.1. Проверить secret-token path

Telegram Bot webhook использует `SimpleRequestHandler(secret_token=...)`, который проверяет:

```text
X-Telegram-Bot-Api-Secret-Token
```

Нужно обеспечить:

1. `WEBHOOK_SECRET_TOKEN` в bot runtime.
2. Bot startup вызывает `set_webhook(..., secret_token=WEBHOOK_SECRET_TOKEN)`.
3. Telegram Bot API `getWebhookInfo` показывает нужный URL.
4. Внешний `https://api.cyber-vpn.net/webhook/telegram` реально проксирует в текущий bot container.
5. Edge/Caddy не удаляет header `X-Telegram-Bot-Api-Secret-Token`.

---

## 6.2. Webhook diagnostics endpoint

Добавить в bot service:

```text
GET /webhook/telegram/diagnostics
```

Защитить `X-Observability-Secret`.

Response:

```json
{
  "service": "cybervpn-telegram-bot",
  "mode": "webhook",
  "webhook_path": "/webhook/telegram",
  "secret_configured": true,
  "bot_username": "...",
  "release": "...",
  "environment": "production"
}
```

Не возвращать секрет.

---

## 6.3. Deploy smoke

Добавить smoke:

```bash
curl -i https://api.cyber-vpn.net/webhook/telegram
```

Ожидаемо для GET:

```text
405 или 404
```

Но не 401 от другого слоя.

Для POST без Telegram secret:

```bash
curl -i -X POST https://api.cyber-vpn.net/webhook/telegram -d '{}'
```

Ожидаемо:

```text
401 от bot SimpleRequestHandler
```

Для POST с правильным secret и невалидным body:

```text
400/422 от aiogram handler
```

Главное: response должен содержать fingerprint/header, подтверждающий, что ответил актуальный bot container.

---

## 7. Edge / Cloudflare / Origin routing hardening

## 7.1. Single-origin contract

Ввести документированный contract:

```text
cyber-vpn.net        -> current frontend/backend Caddy origin
my.cyber-vpn.net     -> current frontend/backend Caddy origin
api.cyber-vpn.net    -> current backend/bot Caddy origin
admin.cyber-vpn.net  -> current admin/backend Caddy origin
```

Cloudflare DNS/origin rules должны быть проверены и зафиксированы.

---

## 7.2. Runtime fingerprint endpoint

Добавить backend endpoint:

```text
GET /api/v1/runtime/fingerprint
```

Response:

```json
{
  "service": "backend",
  "release": "main-6865e021-growth-v72-lifetime-20260629",
  "git_sha": "...",
  "container_image": "...",
  "customer_site_mode": "cabinet_only",
  "origin_marker": "stage1-prod-a"
}
```

Добавить frontend route/endpoint:

```text
GET /runtime/fingerprint
```

Response:

```json
{
  "service": "frontend",
  "release": "...",
  "git_sha": "...",
  "origin_marker": "stage1-prod-a"
}
```

Цель: быстро выявлять, что external domain смотрит на не тот контейнер.

---

## 7.3. External vs internal capabilities smoke

В deploy script добавить проверки:

```bash
curl -s https://api.cyber-vpn.net/api/v1/client/capabilities
curl -s http://127.0.0.1:18080/api/v1/client/capabilities
```

Проверять:

```text
customer_site_mode совпадает
allowed_path_prefixes содержит /miniapp
cabinet_allowed_prefixes содержит /miniapp
release/fingerprint совпадает
```

---

## 7.4. RSC/CORS redirect smoke

Проверки:

```bash
curl -I 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component'

curl -I 'https://my.cyber-vpn.net/en-EN/messages?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component'
```

Fail condition:

```text
Location: https://cyber-vpn.net/...
```

Allow:

```text
200 / 204 / 404
```

Запрещено:

```text
301/302/307/308 cross-origin для RSC/preflight
```

---

## 8. Frontend proxy changes

Файл:

```text
frontend/src/proxy.ts
```

Добавить `/miniapp` в:

```typescript
DEFAULT_CUSTOMER_SITE_RUNTIME.allowedPathPrefixes
DEFAULT_CUSTOMER_SITE_RUNTIME.cabinetAllowedPrefixes
```

Также в shared:

```text
frontend/src/shared/lib/cabinet-routes.ts
```

Добавить:

```typescript
'miniapp'
'/miniapp'
```

Но важно: если Mini App остаётся на public host, `/miniapp` должен быть public allowed, а не обязательно cabinet route redirect.

---

## 9. Caddy changes

Файл:

```text
infra/deploy/stage1/Caddyfile.stage1.snippet
```

Требования:

1. `/webhook/telegram` на `api.cyber-vpn.net` должен проксироваться в `cybervpn-telegram-bot:8080`.
2. Caddy не должен требовать basic auth для `/webhook/telegram`.
3. Caddy не должен удалять `X-Telegram-Bot-Api-Secret-Token`.
4. `/ru-RU/miniapp` на `cyber-vpn.net` не должен попадать в cabinet redirect.
5. RSC запросы на `my.cyber-vpn.net` не должны получать redirect на `cyber-vpn.net`.

Обновить Caddy matchers:

```caddy
@miniapp_routes path_regexp miniapp_routes ^/(?:(?:[a-z]{2}-[A-Z]{2}|zh-Hant)/)?miniapp(?:/.*)?$
handle @miniapp_routes {
    reverse_proxy cybervpn-frontend:3000
}
```

Перед cabinet redirect rules.

---

## 10. Mini App URL management

Добавить admin/runtime config:

```json
{
  "telegram": {
    "miniapp_url": "https://cyber-vpn.net/ru-RU/miniapp",
    "miniapp_onboarding_url": "https://cyber-vpn.net/ru-RU/miniapp/onboarding/code",
    "bot_username": "..."
  }
}
```

Bot startup должен логировать sanitized Mini App URL:

```text
telegram_surface_configured bot_menu_button=miniapp miniapp_url_host=cyber-vpn.net path=/ru-RU/miniapp
```

---

## 11. Tests

### 11.1. Backend tests

- `customer_site.runtime` with `cabinet_only` always allows `/miniapp`.
- `client_capabilities.site.allowed_path_prefixes` contains `/miniapp`.
- `POST /telegram/bot/user` with `registration_enabled=false` and `TELEGRAM_BOT_REGISTRATION_MODE=allow_pending_onboarding` creates pending onboarding user.
- `POST /telegram/bot/user` with disabled mode returns structured error.
- `/customer/onboarding/growth-code/apply` works for `source_surface=telegram_bot` and auto-created pending state.

### 11.2. Bot tests

- `/start` new user in `allow_pending_onboarding` returns Mini App button.
- `/start` blocked registration returns specific message, not generic registration failed.
- `/code <code>` creates pending user if needed and applies code.
- Webhook secret diagnostics.

### 11.3. Frontend/proxy tests

- `cyber-vpn.net/ru-RU/miniapp` in cabinet_only does not redirect to dashboard.
- `my.cyber-vpn.net/ru-RU/miniapp` either works or redirects according to chosen canonical policy.
- RSC requests for rewards/messages do not cross-origin redirect.
- Mini App session-first auth does not open registration page when customer session exists.

### 11.4. Deployment smoke

Add to deploy evidence:

```text
external_api_capabilities
internal_api_capabilities
external_miniapp_url
external_webhook_url
telegram_get_webhook_info
rsc_rewards_invites_probe
rsc_messages_probe
runtime_fingerprint_all_hosts
```

---

## 12. Acceptance criteria

Работа считается выполненной, если:

1. `https://cyber-vpn.net/ru-RU/miniapp` открывает Mini App, а не dashboard/register.
2. В `cabinet_only` `/miniapp` явно разрешён.
3. `https://api.cyber-vpn.net/api/v1/client/capabilities` и прямой origin capabilities совпадают по `customer_site_mode`.
4. `getWebhookInfo` не содержит `401 Unauthorized`.
5. `pending_update_count` не растёт.
6. `/start` для нового Telegram пользователя не показывает generic registration failed.
7. `/start` показывает корректный onboarding entrypoint.
8. `/code <invite>` в боте работает для нового пользователя.
9. Mini App открывает onboarding/code prompt и connection flow.
10. RSC/CORS ошибки вида `redirected from my.cyber-vpn.net/... to cyber-vpn.net/en-EN` отсутствуют.
11. Deploy evidence содержит external smoke, а не только local smoke.
12. Runtime fingerprint на всех внешних доменах указывает на актуальный release.

---

## 13. Operational rollback

Если после релиза webhook ломается:

1. Переключить Bot mode на polling временно.
2. Отключить webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=false"
   ```
3. Включить polling container.
4. Проверить `/start`.
5. После исправления edge/webhook secret вернуть webhook mode.

Если Mini App ломается:

1. Временно установить:
   ```json
   customer_site.runtime.allowed_path_prefixes += ["/miniapp"]
   customer_site.runtime.mode = "full_site"
   ```
2. Purge Cloudflare cache.
3. Перезапустить frontend.
4. Проверить external smoke.
5. Вернуть `cabinet_only` только после прохождения smoke.

---

## 14. Что не входит в это ТЗ

- новая логика lifetime invite v7.2;
- изменение тарифов Premium Smart RU;
- изменение Remnawave Smart RU provisioning;
- изменение ML anti-fraud;
- redesign Mini App UI.

Это ТЗ фокусируется только на production доступности Telegram Bot, Mini App и edge/runtime consistency.
