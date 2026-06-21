# Техническое задание: исправление `401 Unauthorized` при привязке Telegram в customer-кабинете

## 1. Назначение документа

Исправить привязку Telegram-аккаунта к уже авторизованному customer-пользователю на `https://my.cyber-vpn.net`, не затронув:

- обычный вход через Telegram;
- Telegram Login Widget/OAuth для административного контура;
- Telegram Mini App;
- мобильную OIDC-привязку;
- существующие auth cookies и сессии;
- Telegram-бот и его защищённый backend callback, кроме возможных дополнительных тестов.

Основная ошибка сейчас:

```text
POST /api/v1/oauth/telegram/account-link/magic-link
401 Unauthorized
WWW-Authenticate: Bearer
```

При этом браузер отправляет корректную customer-cookie:

```text
customer_access_token=...
customer_refresh_token=...
```

---

# 2. Критическое замечание по безопасности

В диагностике ранее были опубликованы действующие access/refresh JWT.

Перед дальнейшим тестированием необходимо:

1. Завершить текущую пользовательскую сессию.
2. Отозвать refresh token на backend.
3. Желательно выполнить «Выйти со всех устройств».
4. Войти заново.
5. Не использовать опубликованные токены повторно.
6. Не помещать JWT, cookies, bot token и internal secret в issue, commit, PR, CI log или тестовые fixture.

В тестах использовать только сгенерированные тестовые JWT.

---

# 3. Состояние временной GitHub-ветки

Временная ветка:

```text
fix/customer-telegram-account-link-auth
```

не должна быть merged или cherry-picked.

На момент составления ТЗ она:

- опережает `main` на 14 временных commit;
- не содержит готового проверенного исправления;
- содержит временные staging-файлы;
- содержит нежелательное изменение admin use case.

Изменения временной ветки относительно `main`:

```text
backend/src/application/use_cases/auth/telegram_account_linking.py
docs/.customer-telegram-fix-placeholder.txt
docs/.customer-telegram-fix/patch.rev.*
docs/customer-telegram-account-link-fix-note.md
```

## Рекомендуемая очистка

В PowerShell из локального репозитория:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main

git push origin --delete fix/customer-telegram-account-link-auth

# Выполнять только если локальная ветка существует:
git branch -D fix/customer-telegram-account-link-auth

git switch -c fix/customer-telegram-account-link-customer-realm
```

Не переносить изменения из старой ветки. Начать исправление с актуального `main`.

---

# 4. Подтверждённая root cause

## 4.1. Как авторизован customer-пользователь

Личный кабинет `my.cyber-vpn.net` использует customer auth realm.

Access token содержит claims вида:

```text
aud              = cybervpn:customer
principal_type   = customer
realm_key        = customer
scope_family     = customer
role             = mobile_user
```

Browser cookie называется:

```text
customer_access_token
```

Пользователь хранится в:

```text
mobile_users
```

и представлен моделью:

```python
MobileUserModel
```

## 4.2. Что требует новый endpoint

Сейчас route создания linking session использует:

```python
user: AdminUserModel = Depends(get_current_active_user)
```

`get_current_active_user` вызывает admin auth dependency, которая:

- разрешает admin realm;
- ищет cookie `access_token`;
- загружает `AdminUserModel`;
- не читает `customer_access_token`.

Итог:

```text
customer_access_token присутствует
access_token отсутствует
→ token=None
→ 401 Not authenticated
```

## 4.3. Почему нельзя заменить только dependency

Простая замена:

```python
get_current_active_user
```

на web dependency недостаточна.

Дальше текущий status route вызывает:

```python
TelegramAccountLinkingUseCase
```

Этот use case работает с:

```text
AdminUserRepository
AdminUserModel
oauth_accounts
admin_users.telegram_id
```

Но customer-пользователь находится в:

```text
MobileUserRepository
MobileUserModel
mobile_users.telegram_id
```

Кроме того, `oauth_accounts.user_id` имеет foreign key на `admin_users.id`. Использовать эту таблицу для customer-пользователя нельзя.

---

# 5. Целевая архитектура

## 5.1. Разделение auth-контуров

Должны остаться два независимых механизма.

### Admin linking

Существующий flow:

```text
GET  /api/v1/oauth/telegram/authorize
POST /api/v1/oauth/telegram/callback
```

должен продолжать использовать:

```text
AdminUserModel
TelegramAccountLinkingUseCase
oauth_accounts
admin_users.telegram_id
```

### Customer bot deep-link linking

Flow:

```text
POST /api/v1/oauth/telegram/account-link/magic-link
POST /api/v1/oauth/telegram/account-link/magic-link/complete
GET  /api/v1/oauth/telegram/account-link/magic-link/{token}/status
```

должен использовать:

```text
customer_access_token
get_current_mobile_user_id
MobileUserModel
MobileUserRepository
mobile_users.telegram_id
mobile_users.telegram_username
```

## 5.2. Что нельзя делать

Запрещается:

- превращать `TelegramAccountLinkingUseCase` в универсальный класс для admin и customer;
- записывать customer-пользователя в `oauth_accounts`;
- искать customer UUID в `admin_users`;
- выпускать новые JWT после привязки;
- заменять текущие auth cookies;
- вызывать `OAuthLoginUseCase`;
- создавать нового пользователя;
- использовать login magic-link `/start auth_<token>`;
- изменять `telegram_subject` данными, полученными от бота;
- удалять существующий admin linking flow.

---

# 6. Требуемые изменения по файлам

## 6.1. Новый customer use case

Создать:

```text
backend/src/application/use_cases/mobile_auth/telegram_account_linking.py
```

Рекомендуемые классы:

```python
MobileTelegramAccountLinkConflictError
MobileTelegramAccountLinkingUseCase
```

## 6.2. OAuth routes

Изменить:

```text
backend/src/presentation/api/v1/oauth/routes.py
```

Только customer account-link routes:

```text
POST /telegram/account-link/magic-link
GET  /telegram/account-link/magic-link/{token}/status
```

Bot completion route:

```text
POST /telegram/account-link/magic-link/complete
```

оставить без customer-cookie dependency, поскольку он вызывается Telegram-ботом и защищён:

```text
X-Telegram-Bot-Secret
```

## 6.3. Tests

Изменить/добавить:

```text
backend/tests/unit/api/v1/test_oauth_magic_link.py
backend/tests/unit/application/use_cases/mobile_auth/test_telegram_account_linking.py
```

Добавить integration test customer auth boundary в подходящий существующий integration test module.

Admin tests:

```text
backend/tests/unit/api/v1/test_oauth_telegram_linking.py
```

должны остаться зелёными без изменения их семантики.

---

# 7. Реализация customer use case

## 7.1. Контракт

Пример интерфейса:

```python
class MobileTelegramAccountLinkingUseCase:
    def __init__(self, session: AsyncSession) -> None:
        ...

    async def link_account(
        self,
        *,
        user_id: UUID,
        telegram_id: str | int,
        username: str | None = None,
    ) -> MobileUserModel:
        ...
```

## 7.2. Алгоритм

1. Преобразовать Telegram ID в `int`.
2. Если преобразование невозможно, выбросить контролируемую ошибку.
3. Получить текущего customer-пользователя:

   ```python
   MobileUserRepository.get_by_id(user_id)
   ```

4. Если пользователь отсутствует, не создавать нового пользователя.
5. Проверить, существует ли другой `MobileUserModel` с таким `telegram_id`.
6. Если Telegram ID принадлежит другому customer-пользователю — conflict.
7. Если у текущего пользователя уже установлен другой `telegram_id` — conflict.
8. Если установлен тот же `telegram_id` — операция идемпотентна.
9. Обновить:

   ```python
   user.telegram_id
   user.telegram_username
   ```

10. Не менять:

   ```python
   user.telegram_subject
   user.email
   user.username
   user.password_hash
   auth cookies
   sessions
   ```

11. Выполнить `flush`.
12. `commit` выполняет presentation route, согласно текущему transaction pattern.
13. `IntegrityError` от unique constraint преобразовать в domain conflict.
14. Route обязан выполнить `rollback()` после conflict/error.

## 7.3. Почему `telegram_subject` не обновляется

Bot deep-link подтверждает numeric Telegram ID, но не выдаёт OIDC `sub`.

Следовательно:

```python
telegram_subject
```

может устанавливаться только OIDC flow после валидации ID token.

## 7.4. Идемпотентность

Повторная привязка того же Telegram к тому же пользователю:

```text
user.telegram_id == confirmed telegram_id
```

должна завершаться успешно и может обновить `telegram_username`.

Привязка другого Telegram поверх существующего запрещена. Сначала пользователь должен выполнить явный unlink.

---

# 8. Изменения route создания linking session

Текущий неправильный контракт:

```python
async def create_telegram_account_link_magic_link(
    redis_client: redis.Redis = Depends(get_redis),
    user: AdminUserModel = Depends(get_current_active_user),
    current_realm: RealmResolution = Depends(get_request_web_auth_realm),
):
```

Требуемый контракт:

```python
async def create_telegram_account_link_magic_link(
    redis_client: redis.Redis = Depends(get_redis),
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
):
```

## 8.1. Session payload

Сохранять в Redis:

```json
{
  "flow": "telegram_account_link",
  "status": "pending",
  "user_id": "<mobile-user-uuid>",
  "auth_realm_id": "<customer-realm-uuid>",
  "created_at": "<UTC ISO-8601>"
}
```

Не передавать `user_id` в Telegram URL.

Telegram URL:

```text
https://t.me/<bot>?start=link_<random-token>
```

Native deep link:

```text
tg://resolve?domain=<bot>&start=link_<random-token>
```

TTL:

```text
300 seconds
```

## 8.2. Обязательные свойства token

Token должен быть:

- криптографически случайным;
- одноразовым;
- не содержать user ID;
- не логироваться полностью;
- храниться только ограниченное время.

---

# 9. Bot completion route

Route:

```text
POST /api/v1/oauth/telegram/account-link/magic-link/complete
```

сохраняет подтверждённую Telegram identity в Redis.

Его auth-механизм не менять:

```text
X-Telegram-Bot-Secret
```

## 9.1. Необходимые проверки

- internal secret корректен;
- Redis key существует;
- flow равен `telegram_account_link`;
- status равен `pending`;
- TTL положительный;
- повторный completion не перезаписывает первое подтверждение.

## 9.2. Подтверждённый payload

```json
{
  "status": "confirmed",
  "telegram": {
    "id": "123456789",
    "username": "username",
    "first_name": "Name",
    "last_name": null,
    "language_code": "ru"
  }
}
```

Backend доверяет Telegram identity только из защищённого bot completion route, не из браузера.

---

# 10. Изменения status/finalize route

Текущий неправильный dependency:

```python
user: AdminUserModel = Depends(get_current_active_user)
```

Требуемый:

```python
user_id: UUID = Depends(get_current_mobile_user_id)
current_realm: RealmResolution = Depends(get_request_customer_realm)
```

## 10.1. Проверка ownership

Перед любым изменением БД проверить:

```text
session.user_id == current customer user_id
```

## 10.2. Проверка auth realm

Дополнительно проверить:

```text
session.auth_realm_id == current customer auth_realm.id
```

Это защищает от:

- cross-realm reuse;
- случайного совпадения UUID;
- неправильного host/realm routing;
- дальнейшего расширения auth realms.

При owner или realm mismatch:

```http
403 Forbidden
```

Redis payload после claim должен быть восстановлен из `processing` обратно в `confirmed`.

## 10.3. Finalize

После получения confirmed Telegram payload:

```python
use_case = MobileTelegramAccountLinkingUseCase(db)

await use_case.link_account(
    user_id=user_id,
    telegram_id=provider_user_id,
    username=telegram_username,
)
```

Затем:

```python
await db.commit()
```

После успешного commit установить Redis terminal state:

```json
{
  "status": "linked",
  "provider_user_id": "123456789"
}
```

## 10.4. Conflict

При conflict:

```python
await db.rollback()
```

и установить terminal state:

```json
{
  "status": "conflict",
  "provider_user_id": "123456789"
}
```

HTTP response:

```http
409 Conflict
```

## 10.5. Временная DB-ошибка

При неожиданной DB-ошибке:

```python
await db.rollback()
```

Redis payload вернуть из:

```text
processing
```

в:

```text
confirmed
```

после чего пробросить ошибку.

Telegram identity не должна потеряться из-за временной ошибки PostgreSQL.

---

# 11. Согласованность с существующей customer-логикой

Существующий mobile Telegram OIDC linking после успеха выполняет customer-side effects.

Для parity после bot linking рекомендуется выполнить:

```python
await AutomateCustomerGrowthNotificationRepairUseCase(db).execute(
    mobile_user_id=user_id,
    repair_trigger="telegram_linked",
)
```

до `commit`.

После commit:

```python
await sync_auth_security_posture(db, redis_client)
```

Следовать существующему pattern из mobile auth route.

Если эти операции добавляются:

- growth repair должна быть в той же DB transaction;
- telemetry/security posture не должна менять auth cookies;
- повторная обработка должна оставаться безопасной.

---

# 12. API contract после исправления

## 12.1. Создание session

Request:

```http
POST /api/v1/oauth/telegram/account-link/magic-link
Cookie: customer_access_token=<valid customer JWT>
Host: my.cyber-vpn.net
Origin: https://my.cyber-vpn.net
```

Response:

```http
200 OK
```

```json
{
  "token": "<opaque-token>",
  "bot_url": "https://t.me/<bot>?start=link_<opaque-token>",
  "deep_link_url": "tg://resolve?domain=<bot>&start=link_<opaque-token>",
  "expires_in": 300
}
```

## 12.2. Pending status

```http
GET /api/v1/oauth/telegram/account-link/magic-link/<token>/status
```

```json
{
  "status": "pending",
  "provider": "telegram",
  "provider_user_id": null
}
```

## 12.3. Linked status

```json
{
  "status": "linked",
  "provider": "telegram",
  "provider_user_id": "123456789"
}
```

## 12.4. Expired status

```json
{
  "status": "expired",
  "provider": "telegram",
  "provider_user_id": null
}
```

## 12.5. Conflict

```http
409 Conflict
```

```json
{
  "status": "conflict",
  "provider": "telegram",
  "provider_user_id": "123456789"
}
```

## 12.6. Запрещённый owner/realm

```http
403 Forbidden
```

Не раскрывать, кому принадлежит session или Telegram identity.

---

# 13. Frontend

Для исправления текущего `401` frontend-код, вероятнее всего, менять не требуется, поскольку он уже вызывает:

```text
POST /oauth/telegram/account-link/magic-link
GET  /oauth/telegram/account-link/magic-link/{token}/status
```

Но необходимо проверить regression tests.

## 13.1. Обязательные frontend assertions

- settings не вызывает `telegramMagicLinkAuth`;
- используется `requestTelegramAccountLink`;
- payload начинается с `link_`, не с `auth_`;
- при `linked` обновляется current user query;
- `user.id` до и после привязки одинаков;
- не вызывается login result handler;
- не изменяется `isAuthenticated`;
- не устанавливаются новые auth tokens из JS;
- `expired` и `conflict` отображаются отдельно;
- polling очищается при unmount.

## 13.2. Обновление UI после успеха

После `linked`:

```text
invalidate/refetch ['settings', 'auth-user']
```

Профиль должен получить:

```text
telegram_id
telegram_username
linked_providers includes "telegram"
```

`build_mobile_user_response()` уже считает Telegram связанным, если:

```python
user.telegram_subject or user.telegram_id is not None
```

Поэтому установка `mobile_users.telegram_id` достаточна для отображения linked provider.

---

# 14. Логирование

## 14.1. Допустимые данные

Логировать:

```text
event
user_id
auth_realm_id
reason
request_id
telegram_id
```

Telegram ID допустим только согласно текущей logging policy проекта.

## 14.2. Запрещённые данные

Не логировать:

```text
полный magic token
customer_access_token
customer_refresh_token
bot token
internal secret
полный Redis payload
cookies
JWT
```

Для token correlation использовать:

```text
sha256(token)[:12]
```

## 14.3. Рекомендуемые события

```text
telegram_account_link_session_created
telegram_account_link_bot_confirmed
telegram_account_link_completed
telegram_account_link_conflict
telegram_account_link_expired
telegram_account_link_forbidden_context_mismatch
telegram_account_link_database_retry
```

---

# 15. Обязательные тесты

## 15.1. Unit tests customer use case

Создать:

```text
backend/tests/unit/application/use_cases/mobile_auth/test_telegram_account_linking.py
```

Проверить:

1. Новый Telegram ID устанавливается customer-пользователю.
2. Username обновляется.
3. Повторная привязка того же ID идемпотентна.
4. Telegram другого customer-пользователя вызывает conflict.
5. Другой Telegram поверх текущего вызывает conflict.
6. Некорректный Telegram ID не изменяет БД.
7. Отсутствующий customer-пользователь не создаётся.
8. `IntegrityError` преобразуется в conflict.
9. `telegram_subject` не изменяется.
10. `flush` вызывается, но `commit` выполняет route.

## 15.2. Route unit tests

В `test_oauth_magic_link.py`:

1. Create route использует customer dependency.
2. Для create test не override-ить `get_current_active_user`.
3. Override-ить:

   ```python
   get_current_mobile_user_id
   get_request_customer_realm
   ```

4. Проверить сохранение:

   ```text
   user_id
   auth_realm_id
   flow
   status
   TTL
   ```

5. Status wrong owner возвращает `403`.
6. Status wrong realm возвращает `403`.
7. После forbidden Redis status снова `confirmed`, не `processing`.
8. Successful finalize вызывает `MobileTelegramAccountLinkingUseCase`.
9. Successful finalize не устанавливает `Set-Cookie`.
10. Successful finalize делает один `commit`.
11. Conflict делает `rollback`.
12. DB exception делает `rollback` и восстанавливает payload.
13. Repeated linked poll идемпотентен.
14. Repeated conflict poll возвращает terminal conflict.
15. Bot completion tests продолжают проходить.

## 15.3. Integration auth boundary test

Это главный regression test, который должен поймать исходную проблему.

Нельзя полностью подменять auth dependency.

Test должен:

1. Создать `MobileUserModel` в test DB.
2. Создать корректный customer access JWT:
   - audience `cybervpn:customer`;
   - realm key `customer`;
   - principal type `customer`;
   - subject равен mobile user UUID.
3. Установить cookie:

   ```text
   customer_access_token
   ```

4. Выполнить request с:

   ```text
   Host: my.cyber-vpn.net
   Origin: https://my.cyber-vpn.net
   ```

5. Проверить:

   ```http
   POST /api/v1/oauth/telegram/account-link/magic-link
   200 OK
   ```

6. Убедиться, что `access_token` admin-cookie не требуется.

Дополнительные integration cases:

- admin cookie без customer cookie → `401`;
- customer JWT с неверным audience → `401`;
- customer JWT с неверным realm → `401`;
- отсутствующий mobile user → `401`;
- revoked JTI → `401`.

## 15.4. Admin regression tests

Без изменений должны проходить:

```text
POST /api/v1/oauth/telegram/callback
```

и существующий:

```text
TelegramAccountLinkingUseCase
```

Проверить, что admin linking продолжает:

- записывать `oauth_accounts`;
- устанавливать `admin_users.telegram_id`;
- возвращать admin conflict;
- не использует `MobileUserRepository`.

## 15.5. Bot regression tests

Должны оставаться зелёными:

- `auth_` завершает login flow;
- `link_` завершает account-link confirmation;
- неправильный bot secret возвращает `401`;
- expired link возвращает `404`;
- повторный completion возвращает `409`;
- первый Telegram payload не перезаписывается вторым.

---

# 16. Команды локальной проверки

PowerShell:

```powershell
cd <путь-к-CyberVPN>

git switch fix/customer-telegram-account-link-customer-realm
```

Установка backend:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Ruff:

```powershell
ruff check `
  src/application/use_cases/auth/telegram_account_linking.py `
  src/application/use_cases/mobile_auth/telegram_account_linking.py `
  src/presentation/api/v1/oauth/routes.py `
  tests/unit/api/v1/test_oauth_magic_link.py `
  tests/unit/api/v1/test_oauth_telegram_linking.py `
  tests/unit/application/use_cases/mobile_auth/test_telegram_account_linking.py
```

Targeted tests:

```powershell
pytest -q `
  tests/unit/api/v1/test_oauth_magic_link.py `
  tests/unit/api/v1/test_oauth_telegram_linking.py `
  tests/unit/application/use_cases/mobile_auth/test_telegram_account_linking.py
```

Затем запустить relevant integration tests customer auth.

Перед commit:

```powershell
git diff --check
git status
git diff
```

---

# 17. Ручной smoke test

## 17.1. До Telegram

1. Войти в `https://my.cyber-vpn.net`.
2. DevTools → Network.
3. Открыть Settings.
4. Нажать «Привязать Telegram».
5. Проверить:

   ```http
   POST /api/v1/oauth/telegram/account-link/magic-link
   200 OK
   ```

6. Проверить URL:

   ```text
   start=link_
   ```

7. Убедиться, что request содержит `customer_access_token`.
8. Убедиться, что response не содержит `Set-Cookie`.

## 17.2. В Telegram

1. Открыть ссылку.
2. Нажать Start.
3. Бот должен подтвердить identity.
4. Бот не должен выполнять login flow.
5. Бот не должен создавать нового пользователя.

## 17.3. После возврата в браузер

1. Poll status возвращает `linked`.
2. `/auth/me` или customer profile возвращает тот же `user.id`.
3. Появляются:

   ```text
   telegram_id
   telegram_username
   linked_providers: ["telegram"]
   ```

4. Cookies до и после операции не заменяются.
5. В `mobile_users` установлен Telegram ID.
6. В `admin_users` ничего не изменено.
7. В `oauth_accounts` customer-запись не создана.

## 17.4. Conflict

1. Войти вторым customer-пользователем.
2. Попытаться связать тот же Telegram.
3. Получить `409 Conflict`.
4. Первая связь остаётся неизменной.
5. Второй пользователь остаётся без Telegram.
6. Auth session обоих пользователей не меняется.

---

# 18. Deployment

Для исправления `401` требуется пересобрать и задеплоить backend.

Frontend и bot повторно деплоить только если их код дополнительно изменён.

Последовательность:

1. Merge проверенного PR.
2. Собрать новый immutable backend image.
3. Выполнить targeted CI tests.
4. Задеплоить backend.
5. Убедиться, что container пересоздан.
6. Выполнить health checks.
7. Выполнить customer linking smoke.
8. Проверить logs по `request_id`.
9. Проверить отсутствие новых `401` для create/status route.

Миграция БД не требуется, поскольку `mobile_users.telegram_id` и `telegram_username` уже существуют.

---

# 19. Rollback

Если после deploy обнаружена регрессия:

1. Вернуть предыдущий backend image.
2. Не откатывать БД — schema не изменяется.
3. Redis linking sessions истекут через 300 секунд.
4. Проверить login flow `auth_`.
5. Проверить admin Telegram callback.
6. Зафиксировать request IDs и terminal Redis states без публикации token.

---

# 20. Критерии приёмки

Исправление принято только если:

- [ ] Customer create route принимает `customer_access_token`.
- [ ] `POST /account-link/magic-link` возвращает `200`, а не `401`.
- [ ] Route не требует admin cookie `access_token`.
- [ ] Customer user загружается из `mobile_users`.
- [ ] Customer linking не использует `oauth_accounts`.
- [ ] Customer linking не изменяет `admin_users`.
- [ ] Admin Telegram linking продолжает работать.
- [ ] Telegram login flow продолжает работать.
- [ ] Mini App/OIDC flow не изменён.
- [ ] Session связана с customer user ID.
- [ ] Session связана с customer realm ID.
- [ ] Wrong owner и wrong realm возвращают `403`.
- [ ] Telegram другого customer-пользователя возвращает `409`.
- [ ] Тот же Telegram для того же пользователя обрабатывается идемпотентно.
- [ ] Другой Telegram поверх существующего запрещён без unlink.
- [ ] `telegram_subject` не устанавливается bot flow.
- [ ] JWT/cookies не выпускаются и не заменяются.
- [ ] Новый пользователь не создаётся.
- [ ] DB exception не теряет confirmed Redis payload.
- [ ] Полные tokens/secrets отсутствуют в logs.
- [ ] Unit tests проходят.
- [ ] Integration customer-cookie test проходит.
- [ ] Admin regression tests проходят.
- [ ] Bot regression tests проходят.
- [ ] `ruff check` проходит.
- [ ] Ручной production smoke выполнен.

---

# 21. Definition of Done

Работа считается полностью завершённой после:

1. Чистого PR из новой ветки, созданной от актуального `main`.
2. Отсутствия временных staging-файлов.
3. Review diff на предмет изменений admin/login flow.
4. Зелёного CI.
5. Деплоя нового backend image.
6. Успешного реального сценария:

   ```text
   frontend
   → customer auth
   → Redis linking session
   → Telegram bot
   → protected completion
   → customer status/finalize
   → mobile_users update
   → frontend profile refresh
   ```

7. Подтверждения, что `user.id` и auth cookies до и после привязки не изменились.
