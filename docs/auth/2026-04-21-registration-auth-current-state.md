# Регистрация и авторизация: текущее состояние

Дата среза: 2026-04-21

Документ описывает фактическую реализацию регистрации и авторизации в четырех зонах проекта:

- frontend: `frontend/`
- backend: `backend/`
- Telegram bot: `services/telegram-bot/`
- mobile app: `cybervpn_mobile/`

Это не целевая архитектура из PRD, а срез того, что реально работает в коде на момент анализа.

## 1. Коротко о модели auth

Сейчас основная модель авторизации построена вокруг `httpOnly` cookie, которые выставляет backend.

- access token и refresh token кладутся backend в cookie с `path=/api`
- frontend ходит в backend через `Next.js` rewrite `/api/v1/* -> http://localhost:8000/api/v1/*`
- клиентский Zustand store не хранит реальные токены; `tokenStorage` оставлен как legacy shim
- при `401` frontend пытается вызвать `/auth/refresh`, затем повторяет исходный запрос
- защищенные dashboard-роуты проверяют сессию через `/auth/session`

Ключевые файлы:

- frontend: `frontend/next.config.ts`
- frontend: `frontend/src/lib/api/client.ts`
- frontend: `frontend/src/lib/api/auth.ts`
- frontend: `frontend/src/stores/auth-store.ts`
- frontend: `frontend/src/features/auth/components/AuthGuard.tsx`
- backend: `backend/src/presentation/api/v1/auth/cookies.py`
- backend: `backend/src/presentation/dependencies/auth.py`

## 2. Компоненты и роли

### 2.1 Frontend

Frontend отвечает за:

- UI логина, регистрации, OTP, magic link, OAuth
- bootstrap сессии после загрузки приложения
- локальную auth-state-модель в Zustand
- BFF-маршруты для OAuth start/callback и для завершения pending 2FA

Важные точки:

- глобальный bootstrap сессии: `frontend/src/app/[locale]/layout.tsx`
- protected layout: `frontend/src/app/[locale]/(dashboard)/layout.tsx`
- auth layout: `frontend/src/app/[locale]/(auth)/layout.tsx`
- middleware в проекте auth не делает; `src/proxy.ts` занимается только locale

### 2.2 Backend

Backend отвечает за:

- регистрацию, логин, refresh, logout
- email OTP verification
- magic link по email
- password reset
- OAuth login/callback
- Telegram Web Widget auth
- Telegram Mini App auth
- Telegram magic-link handshake
- 2FA setup/verify/complete
- хранение refresh sessions и revocation

Важные точки:

- auth routes: `backend/src/presentation/api/v1/auth/routes.py`
- registration route: `backend/src/presentation/api/v1/auth/registration.py`
- OAuth routes: `backend/src/presentation/api/v1/oauth/routes.py`
- 2FA routes: `backend/src/presentation/api/v1/two_factor/routes.py`
- login use case: `backend/src/application/use_cases/auth/login.py`
- register use case: `backend/src/application/use_cases/auth/register.py`
- OAuth login use case: `backend/src/application/use_cases/auth/oauth_login.py`

### 2.3 Telegram bot

Telegram bot отвечает не только за chat UX, но и за часть auth-handshake для Telegram magic-link.

Бот:

- при обычных апдейтах подтягивает или создает Telegram-пользователя через backend
- кеширует пользователя в Redis на 5 минут
- разбирает deep links `/start auth_*`, `/start ref_*`, `/start promo_*`
- завершает browser-to-bot magic-link логин, вызывая backend внутренним секретом

Важные точки:

- bot init: `services/telegram-bot/src/bot.py`
- auth middleware: `services/telegram-bot/src/middlewares/auth.py`
- start handler: `services/telegram-bot/src/handlers/start.py`
- API client: `services/telegram-bot/src/services/api_client.py`

## 3. Сессии, cookie и realm

### 3.1 Cookie-модель

Backend выставляет cookie через `set_auth_cookies(...)`.

- cookie names по умолчанию: `access_token`, `refresh_token`
- path: `/api`
- `httpOnly=true`
- `sameSite=lax`
- `secure` и `domain` зависят от настроек

Если используется не legacy admin namespace, backend умеет namespaced cookie.

Файл:

- `backend/src/presentation/api/v1/auth/cookies.py`

### 3.2 Realm-модель

Запросы auth идут через `RealmResolution`. Для `/api/v1/auth/*` сейчас по умолчанию используется admin realm.

Файлы:

- `backend/src/presentation/dependencies/auth_realms.py`
- `backend/src/application/use_cases/auth_realms/resolve_realm.py`

Следствие:

- audience / realm_key / cookie namespace определяются не только user, но и текущим realm-контекстом
- `/2fa/complete` тоже завершает сессию уже в контексте realm

## 4. Frontend flow: bootstrap и guard

После загрузки приложения `AuthSessionBootstrap` делает попытку восстановить сессию через `/auth/session`.

- если cookie валидны, store получает `user` и `isAuthenticated=true`
- если нет, store очищается без hard error

Для dashboard-зоны используется `AuthGuard`.

- guard вызывает `/auth/session`
- при `401/403` редиректит на локализованный `/login?redirect=...`
- redirect path сохраняется

Файлы:

- `frontend/src/app/providers/auth-provider.tsx`
- `frontend/src/features/auth/components/AuthGuard.tsx`
- `frontend/src/features/auth/lib/session.ts`

Тесты:

- `frontend/src/features/auth/components/__tests__/AuthGuard.test.tsx`

## 5. Регистрация

### 5.1 Email registration

### Что делает frontend

Страница регистрации: `frontend/src/app/[locale]/(auth)/register/page.tsx`

Store-метод:

- `useAuthStore.register(identifier, password, { mode: 'email' })`

Запрос:

- `POST /auth/register`
- payload: `login`, `email`, `password`, `tos_accepted`, `marketing_consent`

Важно:

- frontend сам генерирует `login` из левой части email: `email.split('@')[0]`
- после успешной регистрации frontend не считает пользователя авторизованным
- пользователь переводится на `/verify?email=...`

### Что делает backend

Регистрация обрабатывается двумя слоями:

- route: `backend/src/presentation/api/v1/auth/registration.py`
- use case: `backend/src/application/use_cases/auth/register.py`

Фактическое поведение:

1. Проверяется `settings.registration_enabled`
2. Если `settings.registration_invite_required=True`, нужен `invite_token`
3. Invite token валидируется и одноразово consume-ится
4. Проверяются уникальность `login` и `email`
5. Требуется `tos_accepted=True`
6. Создается `AdminUserModel` с:
   - `is_active=False`
   - `is_email_verified=False`
7. Генерируется OTP для `email_verification`
8. Email с OTP уходит через task dispatcher

Что получает frontend:

- `RegisterResponse`
- пользователь создан, но сессии еще нет

### Подтверждение email

Frontend:

- страница: `frontend/src/app/[locale]/(auth)/verify/page.tsx`
- форма: `frontend/src/features/auth/components/OtpVerificationForm.tsx`
- запрос: `POST /auth/verify-otp`

Backend:

- route aliases: `/auth/verify-otp` и `/auth/verify-email`

Поведение backend:

1. проверяет OTP
2. ставит `is_active=True`
3. ставит `is_email_verified=True`
4. best-effort создает пользователя в Remnawave
5. сразу выдает access/refresh
6. сразу ставит auth cookies

Итог:

- подтверждение email одновременно завершает активацию и сразу авторизует пользователя

### 5.2 Username-only registration

Frontend поддерживает второй режим регистрации без email.

Поведение:

- frontend отправляет только `login`, `password`, `tos_accepted`, `marketing_consent`
- backend создает пользователя сразу активным
- OTP/email verification в этом режиме нет
- frontend после успешной регистрации переводит на `/login?registered=true`

Backend-логика:

- `is_active=True`
- `is_email_verified=True`

Ключевой нюанс:

- backend логин действительно умеет `login_or_email`
- но текущая login форма на frontend использует `<input type="email">`
- то есть username-only режим в backend существует, а frontend UX остается email-first

Файлы:

- frontend: `frontend/src/app/[locale]/(auth)/login/login-client.tsx`
- backend schema: `backend/src/presentation/api/v1/auth/schemas.py`
- backend use case: `backend/src/application/use_cases/auth/login.py`

## 6. Обычный логин, refresh и logout

### 6.1 Password login

Frontend:

- страница: `frontend/src/app/[locale]/(auth)/login/login-client.tsx`
- store action: `useAuthStore.login(...)`
- запрос: `POST /auth/login`

Backend:

- route: `backend/src/presentation/api/v1/auth/routes.py`
- use case: `backend/src/application/use_cases/auth/login.py`

Фактическое поведение backend:

1. ищет пользователя по `login_or_email`
2. требует:
   - `is_active=True`
   - `is_email_verified=True`
3. проверяет пароль
4. обновляет sign-in metadata
5. если у пользователя включен TOTP:
   - не выдает полноценную сессию
   - выдает короткий pending token `tfa_token`
6. если TOTP нет:
   - выдает access/refresh
   - сохраняет refresh session
   - ставит cookie
7. route дополнительно защищен login protection; при серии неудачных попыток может вернуть `423 Locked`

### 6.2 Pending 2FA flow

На frontend pending 2FA реализован через отдельный BFF слой.

Схема:

1. backend login или OAuth callback возвращает `requires_2fa=true` и `tfa_token`
2. frontend кладет pending token в подписанную `httpOnly` cookie `pending_2fa`
3. пользователь попадает на `/login?2fa=true`
4. форма 2FA отправляет код в `POST /api/auth/2fa/complete`
5. Next route читает pending cookie и проксирует запрос в backend `/api/v1/2fa/complete`
6. backend проверяет TOTP и только после этого ставит обычные auth cookies

Файлы:

- frontend cookie staging: `frontend/src/app/api/auth/2fa/pending/route.ts`
- frontend completion: `frontend/src/app/api/auth/2fa/complete/route.ts`
- frontend helper: `frontend/src/features/auth/lib/pending-twofa.ts`
- backend completion: `backend/src/presentation/api/v1/two_factor/routes.py`

### 6.3 Session, refresh, logout

Основные endpoints backend:

- `GET /auth/me`
- `GET /auth/session`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/logout-all`
- `GET /auth/devices`
- `DELETE /auth/devices/{device_id}`

Frontend:

- работает через `authApi.session()`, `authApi.refresh()`, `authApi.logout()`
- `axios` interceptor сам пробует refresh при `401`

Тесты:

- `backend/tests/integration/api/v1/auth/test_auth_flows.py`
- `backend/tests/integration/api/v1/auth/test_logout_all.py`

## 7. Magic link и password reset

### 7.1 Email magic link

Frontend:

- request page: `frontend/src/app/[locale]/(auth)/magic-link/page.tsx`
- verify page: `frontend/src/app/[locale]/(auth)/magic-link/verify/page.tsx`

Backend endpoints:

- `POST /auth/magic-link`
- `POST /auth/magic-link/verify`
- `POST /auth/magic-link/verify-otp`

Фактическое поведение:

- backend не раскрывает факт существования email
- стандартный ответ на request одинаковый: "If this email is registered, a login link has been sent."
- кроме клика по ссылке поддерживается OTP fallback
- если пользователь не найден, verify-flow умеет auto-register активного и verified пользователя с random password
- после verify backend сразу выдает сессию и ставит cookie

### 7.2 Forgot / reset password

Backend endpoints:

- `POST /auth/forgot-password`
- `POST /auth/reset-password`

Поведение:

- forgot-password тоже не раскрывает, существует ли email
- reset-password использует OTP-код из email

Frontend:

- `frontend/src/app/[locale]/(auth)/forgot-password/page.tsx`
- `frontend/src/app/[locale]/(auth)/reset-password/page.tsx`

## 8. OAuth login через frontend BFF

Telegram-кнопка на login/register сейчас не идет через общий OAuth start/callback flow. Для Telegram используется отдельный magic-link сценарий, описанный ниже.

Для остальных провайдеров схема такая:

1. frontend вызывает `/api/oauth/start/{provider}?locale=...&return_to=...`
2. Next BFF создает подписанную cookie `oauth_tx`
3. BFF получает authorize URL у backend `GET /api/v1/oauth/{provider}/login`
4. браузер уходит на провайдера
5. провайдер возвращает пользователя в frontend callback `/api/oauth/callback/{provider}`
6. Next BFF валидирует `oauth_tx`
7. BFF вызывает backend `POST /api/v1/oauth/{provider}/login/callback`
8. backend либо:
   - выдает готовую сессию и cookie
   - либо возвращает `requires_2fa`
9. BFF пробрасывает `Set-Cookie` в браузер и делает redirect в нужный route

Файлы:

- frontend start route: `frontend/src/app/api/oauth/start/[provider]/route.ts`
- frontend callback route: `frontend/src/app/api/oauth/callback/[provider]/route.ts`
- frontend transaction cookie: `frontend/src/features/auth/lib/oauth-transaction.ts`
- backend OAuth routes: `backend/src/presentation/api/v1/oauth/routes.py`

Поддерживаемые login providers в backend:

- `google`
- `discord`
- `facebook`
- `apple`
- `microsoft`
- `twitter`
- `github`

Особенности backend OAuth login:

- существующая связка ищется по `(provider, provider_user_id)`
- если связки нет, возможен auto-link по email
- auto-link по email разрешен только для trusted providers с trusted verified email
- для новых пользователей создается активный viewer-account с random password

## 9. Telegram auth

В проекте сейчас есть несколько разных Telegram-сценариев.

### 9.1 Telegram Web Widget auth

Endpoint backend:

- `POST /auth/telegram/web`

Frontend:

- store action: `useAuthStore.telegramAuth(...)`

Поведение:

- backend валидирует payload Telegram Login Widget
- ищет пользователя по `telegram_id`
- если пользователя нет, auto-register
- создает access/refresh и ставит cookie

Где реально используется:

- прямой store method существует
- для login page основная Telegram-кнопка сейчас запускает не widget flow, а magic-link flow
- widget сейчас особенно важен для linking Telegram-аккаунта из профиля

Файлы:

- backend use case: `backend/src/application/use_cases/auth/telegram_web_auth.py`
- frontend method: `frontend/src/stores/auth-store.ts`

### 9.2 Telegram Mini App auth

Endpoint backend:

- `POST /auth/telegram/miniapp`

Frontend:

- `TelegramMiniAppAuthProvider` автоматически пытается залогинить пользователя, если страница открыта внутри Telegram Mini App
- источник данных: `window.Telegram.WebApp.initData`

Файлы:

- frontend provider: `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
- backend use case: `backend/src/application/use_cases/auth/telegram_miniapp.py`

Фактическое поведение:

1. frontend видит контекст Mini App
2. вызывает backend с `initData`
3. backend валидирует HMAC и freshness
4. ищет пользователя по `telegram_id`
5. если пользователь не найден, auto-register активного viewer
6. backend сразу создает access/refresh и ставит cookie

Важно:

- response contract и frontend код умеют обработать `requires_2fa`
- но текущие use case `telegram_miniapp.py` и `telegram_web_auth.py` 2FA-гейт сейчас не делают
- то есть Mini App/Web Telegram login в текущем коде выдают полную сессию напрямую, даже если у пользователя включен TOTP

Это наблюдаемое расхождение между контрактом/клиентом и реальной реализацией.

### 9.3 Telegram magic-link login: browser -> bot -> backend -> browser

Это основной Telegram login flow, который сейчас привязан к Telegram-кнопке на auth-страницах frontend.

### Шаги frontend

Кнопка Telegram на `login/register` вызывает `oauthLogin('telegram')`, а store переводит это в `telegramMagicLinkAuth()`.

Файлы:

- `frontend/src/features/auth/components/SocialAuthButtons.tsx`
- `frontend/src/stores/auth-store.ts`

Flow:

1. frontend вызывает `GET /oauth/telegram/magic-link`
2. backend создает Redis-сессию со статусом `pending` и TTL 5 минут
3. frontend получает:
   - `token`
   - `bot_url`
   - `deep_link_url`
4. frontend открывает Telegram deep link `tg://resolve?...start=auth_<token>`
5. frontend сам уходит на `/{locale}/telegram-link?magic=<token>`
6. страница `telegram-link` начинает poll `GET /oauth/telegram/magic-link/{token}/status`

### Шаги Telegram bot

Бот получает `/start auth_<token>`.

Особенность middleware:

- `AuthMiddleware` специально bypass-ит обычный user bootstrap для payload `auth_...`
- это нужно, чтобы magic-link мог завершиться даже без уже подготовленного bot-user state

Дальше `start.py`:

1. извлекает token
2. вызывает backend `POST /oauth/telegram/magic-link/complete`
3. backend принимает запрос только от:
   - либо аутентифицированного пользователя
   - либо trusted bot с `X-Telegram-Bot-Secret`
4. в Redis вместо `pending` сохраняется Telegram user info
5. бот отвечает пользователю, что можно возвращаться в браузер

### Завершение в backend и browser

Когда browser poll-ит `status`:

1. backend читает Redis-статус
2. если там уже user info, backend делает `OAuthLoginUseCase(provider='telegram')`
3. если это новый пользователь:
   - создается активный viewer-account
   - email считается verified по possession-based модели
4. backend ставит auth cookies
5. frontend либо:
   - сразу применяет auth result и редиректит в dashboard
   - либо, если backend вернул `requires_2fa`, staging pending 2FA и отправляет на `/login?2fa=true`

Ключевые файлы:

- backend magic-link routes: `backend/src/presentation/api/v1/oauth/routes.py`
- frontend page: `frontend/src/app/[locale]/(auth)/telegram-link/telegram-link-client.tsx`
- frontend session helper: `frontend/src/features/auth/lib/telegram-magic-link-session.ts`
- bot handler: `services/telegram-bot/src/handlers/start.py`

Именно этот flow сейчас является основным Telegram login flow для web frontend.

### 9.4 Telegram bot-link login

В коде остается еще один Telegram сценарий: одноразовый bot-link token.

Backend endpoints:

- `POST /auth/telegram/bot-link`
- `POST /auth/telegram/generate-login-link`

Поведение:

- backend умеет сгенерировать одноразовый deep link вида `https://t.me/<bot>?start=login_<token>`
- token хранится в Redis примерно 5 минут
- exchange endpoint `POST /auth/telegram/bot-link` consume-ит token и ищет пользователя по `telegram_id`
- если включен TOTP, этот flow уже корректно уходит в `requires_2fa=true`

Frontend:

- страница `telegram-link` все еще умеет обработать legacy query `?token=...`

Backend use case:

- `backend/src/application/use_cases/auth/telegram_bot_link.py`

## 10. Linking Telegram к уже существующему аккаунту

Это не login, а account linking.

Frontend:

- профильный блок: `frontend/src/features/profile/components/LinkedAccountsSection.tsx`
- запрашивает `state` через `/oauth/telegram/authorize`
- получает Telegram Login Widget payload
- отправляет payload и `state` в `/oauth/telegram/callback`

Backend:

- link routes живут в `backend/src/presentation/api/v1/oauth/routes.py`
- backend привязывает `provider='telegram'` к текущему user

Ограничение unlink:

- unlink Telegram допускается только если у пользователя есть альтернативный способ входа
- на frontend это выражено проверкой наличия verified email

## 11. Как Telegram bot создает пользователя в системе

Помимо login-веток, у Telegram bot есть свой постоянный bootstrap пользователя через внутренний backend API.

Backend internal endpoints:

- `GET /telegram/bot/user/{telegram_id}`
- `POST /telegram/bot/user`
- `PATCH /telegram/bot/user/{telegram_id}`

Они защищены заголовком:

- `X-Telegram-Bot-Secret`

Логика middleware бота:

1. пытается взять пользователя из Redis cache
2. если cache miss, делает `GET /telegram/bot/user/{telegram_id}`
3. если backend вернул `404`, делает `POST /telegram/bot/user`
4. кеширует результат на 300 секунд
5. пробрасывает `data['user']` в handler

Тесты:

- `services/telegram-bot/tests/unit/test_middlewares/test_auth.py`

### Важное доменное различие

При `POST /telegram/bot/user` backend не ограничивается auth-профилем.

Он поддерживает два слоя идентичности:

- `AdminUserModel` для auth / portal / session identity
- `MobileUserModel` для продуктовой Telegram/customer/subscription области

Внутренний bootstrap через `/telegram/bot/user`:

- создает или обновляет `AdminUserModel`
- затем вызывает `_ensure_mobile_user(...)`

Это важная деталь: Telegram user в продуктовой части и auth-user для портала живут как связанные, но не полностью тождественные сущности.

Файл:

- `backend/src/presentation/api/v1/telegram/routes.py`

## 12. Ключевые настройки

Настройки находятся в `backend/src/config/settings.py`.

На auth-flow особенно влияют:

- `registration_enabled = False` по умолчанию
- `registration_invite_required = True` по умолчанию
- `access_token_expire_minutes = 15`
- `refresh_token_expire_days = 7`
- `telegram_auth_max_age_seconds = 86400`
- `telegram_bot_internal_secret`
- `cookie_domain`
- `cookie_secure`
- `oauth_enabled_login_providers`
- `oauth_trusted_email_link_providers`
- `oauth_web_base_url`

Следствие:

- публичная регистрация в текущей backend-конфигурации скорее закрыта по умолчанию
- invite token является обязательным, если флаг invite-only включен

## 13. Наблюдаемые расхождения и важные нюансы

### 13.1 Username-only регистрация есть, username-first login UI нет

Backend поддерживает:

- username-only registration
- login по `login_or_email`

Но текущая login форма frontend:

- маркирована как email
- использует `type="email"`

Итог:

- сценарий username-only technically поддержан backend
- frontend UX для него сейчас неполный

### 13.2 Telegram Mini App/Web и 2FA расходятся по контракту и реализации

Frontend и response schemas умеют работать с `requires_2fa`.

Но в текущих use case:

- `backend/src/application/use_cases/auth/telegram_miniapp.py`
- `backend/src/application/use_cases/auth/telegram_web_auth.py`

логика pending 2FA не реализована. Эти сценарии сразу выпускают полноценную сессию.

В то же время:

- обычный password login
- OAuth callback
- Telegram bot-link

pending 2FA обрабатывают корректно.

### 13.3 Auth guard работает через API, а не через `src/proxy.ts`

Это осознанно связано с тем, что auth cookie имеют `path=/api`.

Поэтому:

- `src/proxy.ts` занимается только locale routing
- проверка авторизации делается клиентским guard-слоем и вызовом `/auth/session`

## 14. Файлы, которые стоит читать первыми

Если нужно быстро зайти в код auth-цепочки, порядок такой:

1. `frontend/src/stores/auth-store.ts`
2. `frontend/src/lib/api/auth.ts`
3. `frontend/src/app/[locale]/(auth)/login/login-client.tsx`
4. `frontend/src/app/[locale]/(auth)/telegram-link/telegram-link-client.tsx`
5. `backend/src/presentation/api/v1/auth/routes.py`
6. `backend/src/presentation/api/v1/auth/registration.py`
7. `backend/src/presentation/api/v1/oauth/routes.py`
8. `backend/src/presentation/api/v1/two_factor/routes.py`
9. `services/telegram-bot/src/middlewares/auth.py`
10. `services/telegram-bot/src/handlers/start.py`

## 15. Тесты, которые подтверждают текущие сценарии

Backend:

- `backend/tests/integration/api/v1/auth/test_register.py`
- `backend/tests/integration/api/v1/auth/test_auth_flows.py`
- `backend/tests/integration/api/v1/auth/test_magic_link.py`
- `backend/tests/integration/api/v1/auth/test_telegram_miniapp_flow.py`
- `backend/tests/integration/api/v1/auth/test_telegram_bot_link_flow.py`
- `backend/tests/integration/api/v1/two_factor/test_2fa_cycle.py`

Frontend:

- `frontend/src/features/auth/components/__tests__/AuthGuard.test.tsx`
- `frontend/src/stores/__tests__/auth-store-miniapp.test.ts`
- `frontend/src/app/api/oauth/__tests__/oauth-web-flow.test.ts`
- `frontend/src/app/api/auth/2fa/complete/route.test.ts`

Telegram bot:

- `services/telegram-bot/tests/unit/test_middlewares/test_auth.py`
- `services/telegram-bot/tests/unit/test_handlers/test_start.py`

## 16. Итог

Текущая auth-система уже не token-in-localStorage, а cookie-first архитектура с backend-driven session management.

Основные рабочие ветки сейчас такие:

- email registration -> OTP verify -> auto-login
- username-only registration -> отдельный login
- password login -> optional pending 2FA -> session cookies
- email magic link -> auto-login
- OAuth via frontend BFF -> optional pending 2FA
- Telegram magic-link через bot -> основной Telegram web login flow
- Telegram Mini App -> auto-login по `initData`
- Telegram bot bootstrap -> внутреннее создание/обновление Telegram user

Самые заметные текущие шероховатости:

- frontend login UI отстает от backend username-only login capability
- Telegram Mini App/Web 2FA-контракт подготовлен, но в use case пока не доведен до той же строгости, что обычный login/OAuth

## 17. Mobile auth в `cybervpn_mobile`

### 17.1 Базовая модель

Мобильное приложение использует не cookie-first веб-модель, а обычную mobile token-модель:

- access token и refresh token хранятся в secure storage
- `AuthInterceptor` добавляет `Authorization: Bearer ...`
- при `401` приложение делает refresh и повторяет запрос
- login/register/refresh дополнительно привязаны к устройству через `device_id`

Ключевые файлы:

- `cybervpn_mobile/lib/core/network/auth_interceptor.dart`
- `cybervpn_mobile/lib/core/storage/secure_storage.dart`
- `cybervpn_mobile/lib/features/auth/data/datasources/auth_remote_ds.dart`
- `cybervpn_mobile/lib/features/auth/data/repositories/auth_repository_impl.dart`
- `backend/src/presentation/api/v1/mobile_auth/routes.py`

### 17.2 Что backend выделяет специально для mobile

У backend есть отдельный mobile namespace:

- `POST /mobile/auth/register`
- `POST /mobile/auth/login`
- `POST /mobile/auth/refresh`
- `POST /mobile/auth/logout`
- `GET /mobile/auth/me`
- `POST /mobile/auth/device`
- `POST /mobile/auth/telegram/callback`

Mobile request почти всегда несет `device`:

- `device_id`
- `platform` = `ios | android`
- `platform_id`
- `os_version`
- `app_version`
- `device_model`
- `push_token?`

Файлы:

- `backend/src/presentation/api/v1/mobile_auth/schemas.py`
- `backend/src/application/use_cases/mobile_auth/register.py`
- `backend/src/application/use_cases/mobile_auth/login.py`
- `backend/src/application/use_cases/mobile_auth/refresh.py`

### 17.3 Текущие mobile flow

Email/password mobile flow отличается от web/admin auth:

- mobile registration сразу создает активного `MobileUserModel`
- email OTP verification в mobile registration сейчас нет
- после mobile registration токены выдаются сразу
- mobile login сейчас работает только по `email + password`
- refresh дополнительно проверяет, что `device_id` действительно привязан к пользователю

Следствие:

- mobile auth уже жизнеспособен как отдельный customer/mobile контур
- но он не повторяет веб-сценарий `register -> verify OTP -> auto-login`
- login-time pending 2FA в mobile use case сейчас не реализован так же полно, как в web auth

### 17.4 Что уже есть на стороне нативных устройств

В `cybervpn_mobile` уже подготовлена нормальная native-база:

- secure storage для токенов: `flutter_secure_storage`
- биометрия: `local_auth`
- native Google Sign-In: `google_sign_in`
- Apple Sign-In код присутствует через `sign_in_with_apple`, но provider скрыт из активных mobile entry points
- deep link plumbing настроен для `cybervpn://...`
- universal links / app links настроены на `https://cybervpn.app`

Файлы:

- `cybervpn_mobile/pubspec.yaml`
- `cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart`
- `cybervpn_mobile/lib/core/routing/deep_link_parser.dart`
- `cybervpn_mobile/android/app/src/main/AndroidManifest.xml`
- `cybervpn_mobile/ios/Runner/Info.plist`
- `cybervpn_mobile/ios/Runner/Runner.entitlements`

## 18. Telegram auth на mobile и native SDK

### 18.1 Что говорит официальный Telegram

По официальной документации Telegram Login:

- Telegram теперь описывает новый login flow как `OpenID Connect`
- для mobile developers Telegram отдельно предоставляет native SDK для iOS и Android
- официальный flow использует `Authorization Code Flow` с `PKCE`
- приложение может запросить `phone` scope и получить в `id_token` `phone_number`

Официальный source:

- https://core.telegram.org/bots/telegram-login

Ключевой вывод из docs:

- текущий целевой Telegram flow для mobile это уже не только legacy widget/HMAC
- Telegram прямо рекомендует native SDK для iOS/Android и OIDC-модель с `id_token`

### 18.2 Как Telegram login реально сделан сейчас в `cybervpn_mobile`

Текущая мобильная реализация Telegram не использует официальный native SDK.

Сейчас flow такой:

1. приложение проверяет, установлен ли Telegram через `tg://resolve`
2. открывает внешний URL `https://oauth.telegram.org/auth?...`
3. ждет deep link `cybervpn://telegram/callback?auth_data=...`
4. отправляет `auth_data` в `POST /mobile/auth/telegram/callback`
5. backend валидирует payload по HMAC-схеме старого Telegram Login Widget
6. backend создает или находит `MobileUserModel`, регистрирует device и выдает токены

Файлы:

- `cybervpn_mobile/lib/core/services/telegram_auth_service.dart`
- `cybervpn_mobile/lib/features/auth/presentation/providers/telegram_auth_provider.dart`
- `backend/src/application/services/telegram_auth.py`
- `backend/src/application/use_cases/mobile_auth/telegram_auth.py`

Это важное различие:

- mobile Telegram login уже существует
- но это не native SDK integration в официальном новом смысле
- и backend сейчас ожидает legacy `auth_data`, а не OIDC `code -> token -> id_token` цепочку

### 18.3 Что происходит с пользователем после Telegram login

В mobile Telegram flow backend:

- валидирует Telegram payload
- ищет пользователя по `telegram_id`
- если пользователя нет, создает `MobileUserModel`
- использует placeholder email вида `tg<id>@telegram.local`
- ставит `password_hash=None`
- обновляет/регистрирует устройство
- выдает `access_token` и `refresh_token`

Это значит:

- Telegram может быть полноценным login-методом для mobile user даже без email/password
- но текущая модель заточена под legacy widget-style payload, а не под новый OIDC-native контракт

## 19. Насколько проект готов к Telegram Native SDK для iOS/Android

### 19.1 Что уже готово

Под новый native Telegram login уже есть хорошая база:

- существует отдельное нативное приложение `cybervpn_mobile`
- есть глубокая интеграция deep links и universal links
- есть mobile backend namespace с bearer-token auth
- есть device-aware session model
- есть Telegram entry point в UI
- есть backend-пайплайн создания/поиска mobile user по Telegram identity

Иными словами:

- инфраструктурно проект частично готов
- продуктово Telegram login уже присутствует

### 19.2 Что пока не готово

Для полной поддержки официального Telegram Native SDK сейчас не хватает нескольких вещей:

- в Flutter app нет интеграции с официальными native Telegram SDK для iOS/Android
- текущий backend Telegram mobile flow не реализован как OIDC `code + PKCE + token exchange + id_token validation`
- backend валидирует legacy HMAC `auth_data`, а не `id_token` через Telegram JWKS
- в текущем коде нет выделенного слоя для обработки OIDC claims `iss/aud/exp/sub/phone_number`
- mobile auth-контракты местами гибридные: часть кода ходит в `/auth/*`, часть в `/mobile/auth/*`
- login-time 2FA для mobile остается неполным, особенно вокруг OAuth/social сценариев
- end-to-end тесты для реального native Telegram flow по сути еще не доведены до рабочего покрытия

Особенно заметный практический нюанс:

- `cybervpn_mobile` уже использует `POST /mobile/auth/telegram/callback`
- но обычные `login/register/refresh/me` в заметной части mobile-кода все еще завязаны на `ApiConstants` с `/api/v1/auth/*`
- то есть mobile auth-контракт выглядит частично мигрированным, а не полностью выровненным

### 19.3 Инженерная оценка готовности

Если разделить вопрос на два слоя, картина такая:

- готовность к mobile auth в целом: средняя, база уже есть и рабочая
- готовность именно к официальному Telegram Native SDK login: ниже средней

Практически это означает:

- быстро сделать proof-of-concept вполне реально
- но до production-ready интеграции нового Telegram Native SDK еще нужен отдельный backend/mobile refactor

Оценка по текущему коду:

- mobile auth platform readiness: примерно `60-70%`
- Telegram Native SDK readiness: примерно `35-45%`

Это не формальная метрика, а инженерная оценка по коду на дату среза.

### 19.4 Что нужно сделать, чтобы стать реально готовыми

Минимальный план перехода выглядит так:

1. Выбрать целевую Telegram схему для mobile: официальный native SDK + OIDC, а не legacy `auth_data`.
2. Добавить iOS/Android native integration слой в `cybervpn_mobile` и обернуть его для Flutter.
3. Расширить backend mobile auth под OIDC callback:
   - `code`/`state`/`code_verifier` или готовый `id_token`
   - валидация `id_token` через Telegram JWKS
   - проверка `iss`, `aud`, `exp`, `sub`
4. Решить, как маппить `phone_number`, `preferred_username`, `telegram_id` и placeholder email.
5. Довести mobile login-time 2FA policy до того же уровня строгости, что web OAuth/password login.
6. Убрать гибридность `/auth/*` vs `/mobile/auth/*` и зафиксировать единый mobile контракт.
7. Добавить реальные e2e tests для iOS/Android callback и unhappy-path сценариев.
