# CyberVPN Project Audit — 2026-02-14

## 1. Backend (Auth Service)

### 1.1 Структура auth-сервиса

**Стек**: FastAPI + SQLAlchemy 2.0 async + asyncpg + PostgreSQL 17.7

**Основные модели**:

| Модель | Таблица | Ключевые поля |
|--------|---------|---------------|
| `AdminUserModel` | `admin_users` | UUID PK, login, email (unique, nullable), password_hash (nullable — passwordless), role (enum), is_active, is_email_verified, telegram_id (unique), totp_secret, totp_enabled, backup_codes_hash, display_name, language, timezone, trial_activated_at |
| `MobileUserModel` | `mobile_users` | UUID PK, email, password_hash, telegram_id (BigInteger, unique, indexed), telegram_username, referral_code, referred_by_user_id, is_partner |
| `RefreshToken` | `refresh_tokens` | UUID PK, FK→admin_users (cascade), token_hash (SHA-256), expires_at, device_id, ip_address, user_agent, last_used_at, revoked_at |
| `OAuthAccount` | `oauth_accounts` | UUID PK, FK→admin_users (cascade), provider (enum), provider_user_id, access_token, refresh_token (encrypted), unique(provider, provider_user_id) |
| `OtpCodeModel` | `otp_codes` | FK→admin_users, 6-digit code, purpose (email_verification/password_reset/login_2fa), expires_at, attempt count |

**Ключевые файлы**:
- `backend/src/application/services/auth_service.py` — JWT + Argon2id хэширование
- `backend/src/application/services/magic_link_service.py` — Passwordless токены (288-bit entropy)
- `backend/src/application/services/otp_service.py` — 6-digit OTP коды
- `backend/src/infrastructure/database/models/admin_user_model.py` — User ORM
- `backend/src/infrastructure/database/models/refresh_token_model.py` — Сессии
- `backend/src/infrastructure/database/models/oauth_account_model.py` — OAuth связки
- `backend/src/config/settings.py` — Конфигурация

### 1.2 JWT: выдача и валидация

**Выдача**:
- Access token: **15 мин** (configurable `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token: **7 дней** (configurable `REFRESH_TOKEN_EXPIRE_DAYS`)
- Алгоритм: HS256 (допустимы HS384, HS512, RS256, RS384, RS512, ES256)
- Каждый токен содержит уникальный `jti` (UUID) для индивидуальной ревокации
- Пароли хэшируются **Argon2id** (OWASP 2025): memory 19 MiB, time 2, hash 32 bytes

**Валидация** (`backend/src/presentation/dependencies/auth.py`):
- `get_current_user()` — принимает JWT из Authorization Bearer header (mobile/API) **ИЛИ** httpOnly cookie `access_token` (web)
- Проверяет подпись, expiration, type, **ревокацию через Redis** (JWTRevocationService)
- `get_current_active_user()` — дополнительно проверяет `is_active`
- `optional_user()` — не бросает исключения при отсутствии токена
- `get_current_mobile_user_id()` — возвращает UUID, JSON-формат ошибок для мобильных

**Ревокация**: Redis-based blacklist по `jti`. Поддерживается single token logout и logout-all.

**Brute Force Protection** (LoginProtectionService):
- Progressive lockout через Redis
- Constant-time response (min 100ms + jitter)
- Предотвращает user enumeration

### 1.3 БД и ORM

- **PostgreSQL 17.7** — `postgresql+asyncpg://cybervpn:cybervpn@localhost:6767/cybervpn`
- **SQLAlchemy 2.0** async с mapped_column
- Миграции: `initial_admin_users` → `mobile_auth` → `otp_codes` → `refresh_tokens`

### 1.4 OAuth провайдеры

**7 провайдеров реализовано** в `backend/src/infrastructure/oauth/`:

| Провайдер | Метод | Config keys |
|-----------|-------|-------------|
| **GitHub** | OAuth 2.0 code flow | `github_client_id`, `github_client_secret` |
| **Google** | OAuth 2.0 + PKCE | `google_client_id`, `google_client_secret` |
| **Discord** | OAuth 2.0 code flow | `discord_client_id`, `discord_client_secret` |
| **Microsoft** | Azure AD OAuth + PKCE | `microsoft_client_id/secret/tenant_id` |
| **Apple** | JWT-based Sign In | `apple_client_id/team_id/key_id/private_key` |
| **Twitter/X** | OAuth 2.0 + PKCE | `twitter_client_id`, `twitter_client_secret` |
| **Telegram** | HMAC-SHA256 (Mini App) + one-time bot link | `telegram_bot_token`, `telegram_bot_username` |

Все реализации: хранят provider tokens в зашифрованных OAuthAccount записях, поддерживают account linking, авто-создание пользователя при первом OAuth-логине.

### 1.5 Email-сервис

**Архитектура**: Fire-and-forget через **TaskIQ + Redis Streams**

```
POST /auth/register → OtpService.generate() → EmailTaskDispatcher
→ redis.xadd("taskiq", {...}) → task-worker (отдельный микросервис)
→ send_otp_email → Resend (primary) / Brevo (fallback)
```

- **Resend** — основной провайдер для первичных отправок
- **Brevo** — fallback для повторных отправок
- Task-worker — отдельный Docker-сервис (`cybervpn-worker`)
- Файл: `backend/src/infrastructure/tasks/email_task_dispatcher.py`

### 1.6 Эндпоинты Auth

| Endpoint | Method | Назначение |
|----------|--------|------------|
| `/auth/login` | POST | Email/password → access + refresh tokens |
| `/auth/refresh` | POST | Обновление access token (device binding) |
| `/auth/logout` | POST | Инвалидация refresh token |
| `/auth/logout-all` | POST | Выход со всех устройств |
| `/auth/me` | GET | Текущий пользователь |
| `/auth/me` | DELETE | Soft-delete аккаунта |
| `/auth/verify-otp` | POST | Верификация email → auto-login |
| `/auth/resend-otp` | POST | Повторная отправка OTP (rate limited) |
| `/auth/magic-link` | POST | Запрос magic link |
| `/auth/magic-link/verify` | POST | Верификация magic link → auto-login + auto-register |
| `/auth/magic-link/verify-otp` | POST | Верификация OTP из magic link email |
| `/auth/telegram/miniapp` | POST | Telegram Mini App auth |
| `/auth/telegram/bot-link` | POST | Telegram bot one-time link login |
| `/auth/forgot-password` | POST | Запрос сброса пароля |
| `/auth/reset-password` | POST | Сброс пароля с OTP |
| `/auth/change-password` | POST | Смена пароля (нужен текущий) |
| `/auth/devices` | GET | Список активных сессий |
| `/auth/devices/{device_id}` | DELETE | Удалённый logout устройства |
| `/mobile/auth/register` | POST | Регистрация мобильного пользователя |
| `/mobile/auth/login` | POST | Мобильный логин |
| `/mobile/auth/refresh` | POST | Обновление токенов (мобильный) |

---

## 2. Frontend

### 2.1 Auth страницы

Все в `frontend/src/app/[locale]/(auth)/`:

| Страница | Файл | Описание |
|----------|------|----------|
| Login | `login/page.tsx` | Email/password + OAuth кнопки + magic link |
| Register | `register/page.tsx` | Email или username-only режим + OAuth |
| Verify OTP | `verify/page.tsx` | 6-digit OTP после регистрации |
| Magic Link | `magic-link/page.tsx` | Запрос + ввод OTP-кода |
| Magic Link Verify | `magic-link/verify/page.tsx` | Верификация токена из URL |
| Forgot Password | `forgot-password/page.tsx` | Запрос OTP на сброс пароля |
| Reset Password | `reset-password/page.tsx` | Сброс с OTP |
| OAuth Callback | `oauth/callback/page.tsx` | Обработка OAuth редиректа |
| Telegram Link | `telegram-link/page.tsx` | Привязка Telegram аккаунта |

### 2.2 Хранение токенов

**httpOnly cookies (SEC-01)** — токены НЕ доступны из JavaScript:

```python
# Backend устанавливает куки:
response.set_cookie(key="access_token", httponly=True, secure=True, samesite="lax", path="/api", max_age=15*60)
response.set_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax", path="/api", max_age=7*86400)
```

Frontend `tokenStorage` — **no-op shim** для обратной совместимости. Реальные токены отправляются автоматически через `withCredentials: true`.

### 2.3 Refresh Token Interceptor

Файл: `frontend/src/lib/api/client.ts`

1. Запрос получает 401 (access token истёк)
2. Interceptor вызывает `POST /auth/refresh` (httpOnly cookie отправляется автоматически)
3. Backend валидирует refresh token, устанавливает новые куки
4. Оригинальный запрос повторяется с новым access cookie
5. Параллельные 401 ставятся в очередь (`failedQueue`) и повторяются после refresh
6. Если refresh не удался → очистка localStorage legacy → redirect на `/{locale}/login?redirect=...`

### 2.4 Auth Store (Zustand)

Файл: `frontend/src/stores/auth-store.ts` (472 строки)

**State**: `user`, `isLoading`, `isAuthenticated`, `isNewTelegramUser`, `isMiniApp`, `error`, `rateLimitUntil`

**Actions**: `login`, `register`, `verifyOtpAndLogin`, `logout`, `fetchUser`, `telegramAuth`, `telegramMiniAppAuth`, `loginWithBotLink`, `oauthLogin`, `oauthCallback`, `requestMagicLink`, `verifyMagicLink`, `verifyMagicLinkOtp`, `deleteAccount`

**Session restore**: `AuthProvider` вызывает `fetchUser()` → `GET /auth/me` при загрузке приложения.

**AuthGuard**: Валидирует сессию через `/auth/me` на mount, редиректит на login при отсутствии.

---

## 3. Telegram Bot

### 3.1 Авторизация пользователя

**Framework**: aiogram 3.25+ (async Python)

**Процесс**:
1. Пользователь отправляет `/start`
2. `AuthMiddleware` извлекает `telegram_id` из Telegram User
3. Пробует загрузить пользователя из Redis-кэша (TTL: 5 мин)
4. При cache miss — вызов Backend API: `GET /telegram/users/{telegram_id}`
5. Если 404 — `POST /telegram/users` для авто-регистрации
6. Результат кэшируется, `data['user']` инжектится в handler

**Deep links**: `/start ref_{referrer_id}` (реферал), `/start promo_{code}` (промокод)

### 3.2 Привязка Telegram ID к User

**Да, привязан**. В таблице `mobile_users`:
- `telegram_id: BigInteger` — unique, indexed, nullable
- `telegram_username: String(100)` — nullable

В таблице `admin_users`:
- `telegram_id` — unique, indexed

### 3.3 Возможности бота

**Пользовательские**: /start, подписки, оплата (CryptoBot/YooKassa/Telegram Stars), VPN-конфиги с QR, рефералы, триалы, промокоды, профиль, поддержка

**Админские**: управление пользователями, рассылки, статистика, планы подписок, промокоды, настройки доступа, шлюзы, импорт/синхронизация с Remnawave, логи

**Middleware stack**: Logging → Metrics → Throttling → Auth → Access Control → i18n

**Resilience**: Circuit breaker (5 failures → 30s cooldown), retry с exponential backoff (до 3 попыток)

---

## 4. Mobile App

### 4.1 Framework

**Flutter 3.x** + Dart 3.10.8+

Ключевые зависимости:
- **flutter_riverpod 3.2.1** — state management
- **go_router 17.0.0** — навигация
- **dio 5.9.0** — HTTP клиент
- **freezed 3.2.5** — иммутабельные модели
- **flutter_secure_storage** — шифрованное хранилище

### 4.2 Хранение токенов

**flutter_secure_storage** (зашифровано платформой):
- iOS: Keychain Services + Secure Enclave
- Android: EncryptedSharedPreferences + AES256-GCM (Android Keystore)

```dart
// Атомарное сохранение пары токенов
Future<void> setTokens({required String accessToken, required String refreshToken}) async {
  await Future.wait([
    write(key: 'access_token', value: accessToken),
    write(key: 'refresh_token', value: refreshToken),
  ]);
}
```

In-memory кэш с TTL для быстрого доступа (< 50ms).

### 4.3 Auth Flow

**Методы аутентификации**: Email/password, Google OAuth, Apple OAuth, Telegram bot link, Biometric (fingerprint/face)

**State management**: Riverpod `AsyncNotifier<AuthState>` (app-scoped, НЕ autoDispose)

```dart
@freezed
sealed class AuthState with _$AuthState {
  const factory AuthState.loading() = AuthLoading;
  const factory AuthState.authenticated(UserEntity user) = AuthAuthenticated;
  const factory AuthState.unauthenticated() = AuthUnauthenticated;
  const factory AuthState.error(String message) = AuthError;
}
```

**Token refresh**:
1. **Проактивный**: `TokenRefreshScheduler` — за 5 мин до истечения access token
2. **Реактивный**: `AuthInterceptor` (Dio) — при 401, Completer-based mutex для concurrent requests

**Безопасность**: Certificate pinning (MITM prevention), HTTPS enforcement в production, Sentry PII redaction

---

## 5. Infrastructure

### 5.1 Redis

**Valkey 8.1-alpine** (Redis-compatible):
- Port: 6379 (localhost only)
- **Zero persistence**: `--save "" --appendonly no` (данные эфемерны)
- Max memory: 128mb + LRU eviction
- DB 0: Backend (JWT revocation, magic links, OTP, brute force protection, rate limiting)
- DB 1: Telegram bot (FSM storage, user cache)
- TaskIQ queue: Redis Streams для async task dispatch

### 5.2 Deployment (Docker Compose)

| Сервис | Назначение | Порт | Профиль |
|--------|-----------|------|---------|
| remnawave | Backend API (FastAPI) | 3005→3000 | default |
| remnawave-db | PostgreSQL 17.7 | 6767→5432 | default |
| remnawave-redis | Valkey 8.1 | 6379 | default |
| db-backup | Daily PostgreSQL backups | - | default |
| cybervpn-worker | TaskIQ worker (email, OTP) | 9091 | worker |
| cybervpn-scheduler | TaskIQ scheduler | - | worker |
| cybervpn-telegram-bot | Telegram bot (aiogram) | 9092 | bot |
| Caddy | SSL/TLS reverse proxy | 80, 443 | proxy |
| Prometheus/Grafana/Loki | Observability | 9090-9121 | monitoring |
| mailpit (x3) | Email testing cluster | 8025-8027 | email-test |

Resource limits: 256M-1G RAM, 0.25-1.0 CPU per container. Healthchecks на всех сервисах.

Networks: `cybervpn-frontend`, `cybervpn-backend`, `cybervpn-data`, `cybervpn-monitoring`

---

## 6. Бизнес-требования

### 6.1 OAuth провайдеры

| Провайдер | Статус |
|-----------|--------|
| Google | Реализован |
| Apple | Реализован |
| GitHub | Реализован |
| Telegram Login | Реализован (Mini App + Bot Link) |
| Discord | Реализован |
| Microsoft | Реализован |
| Twitter/X | Реализован |

**Telegram — приоритетный** провайдер. PRD v1.1.0 описывает Telegram-first onboarding (skip email verification для Telegram-регистраций).

### 6.2 2FA

**TOTP реализован** (Google Authenticator, Authy и т.д.):
- Setup: re-authenticate → generate pending secret (Redis) → QR code → verify code → persist to DB
- Rate limit: 5 попыток за 15 мин
- 8 backup codes при setup
- Disable: password + TOTP code required
- Файл: `backend/src/presentation/api/v1/two_factor/routes.py`

**SMS 2FA — НЕТ** (только TOTP через приложения-аутентификаторы)

### 6.3 Верификация email

**Реализована**:
- OTP expires: 3 часа
- Max attempts: 5
- Max resends: 3 в час, cooldown 30 сек
- При регистрации через Telegram: верификация email **пропускается** (`is_email_verified=true` автоматически)

### 6.4 Роли и permissions

**5 ролей для админ-панели** (иерархия):

| Роль | Уровень | Permissions |
|------|---------|-------------|
| SUPER_ADMIN | 5 | Все 22 (unrestricted) |
| ADMIN | 4 | 17/22 (без MANAGE_ADMINS) |
| OPERATOR | 3 | 12/22 (user, server, payment, subscription, analytics) |
| SUPPORT | 2 | 4/22 (user read/update, server read, monitoring) |
| VIEWER | 1 | 4/22 (read-only) |

**22 permissions**: USER_READ/CREATE/UPDATE/DELETE, SERVER_READ/CREATE/UPDATE/DELETE, PAYMENT_READ/CREATE, MONITORING_READ, AUDIT_READ, WEBHOOK_READ, MANAGE_ADMINS, MANAGE_PLANS, MANAGE_INVITES, SUBSCRIPTION_CREATE, VIEW_ANALYTICS

**End users** (mobile): без явной роли, статус через `UserStatus` enum: ACTIVE, DISABLED, LIMITED, EXPIRED

### 6.5 Мультитенантность

**НЕ реализована**. Нет `tenant_id`, `workspace_id`, `organization_id`. Single-tenant архитектура для одного VPN-бизнеса. Изоляция пользователей через подписки/планы.

### 6.6 Платёжные шлюзы

| Шлюз | Где используется |
|------|------------------|
| CryptoBot | Telegram bot |
| YooKassa | Telegram bot |
| Telegram Stars | Telegram bot |
| Stripe | Планируется |

**Подписки**: BASIC, PRO, ULTRA, CYBER

**Реферальная система**: реферальные коды, партнёрская программа, комиссии, кошелёк с выводом (CryptoBot/Manual)

---

## Архитектурная диаграмма

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENTS                                │
├──────────────┬──────────────┬─────────────┬──────────────────┤
│  Frontend    │  Mobile App  │  Telegram   │  Admin Dashboard │
│  (Next.js)   │  (Flutter)   │  Bot        │  (Next.js)       │
│  httpOnly     │  Bearer JWT  │  (aiogram)  │  httpOnly        │
│  cookies      │  + SecureStore│  API Key    │  cookies         │
└──────┬───────┴──────┬───────┴──────┬──────┴────────┬─────────┘
       │              │              │               │
       ▼              ▼              ▼               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Caddy (TLS Proxy)                          │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (port 3000)                    │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────────────────┐  │
│  │Auth API │ │Mobile API│ │OAuth   │ │Telegram API       │  │
│  │/auth/*  │ │/mobile/* │ │/oauth/*│ │/telegram/*        │  │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └────────┬──────────┘  │
│       └───────────┴───────────┴────────────────┘             │
│       ▼ Dependencies: JWT validation, RBAC, Rate Limiting     │
└────────┬────────────────────┬────────────────────────────────┘
         │                    │
    ┌────▼────┐         ┌────▼──────┐
    │PostgreSQL│         │  Redis    │
    │  17.7    │         │  (Valkey) │
    │  :6767   │         │   :6379   │
    └─────────┘         └─────┬─────┘
                              │
                    ┌─────────▼──────────┐
                    │  TaskIQ Worker     │
                    │  (email, OTP)      │
                    │  Resend + Brevo    │
                    └────────────────────┘
```
