# PRD: CyberVPN Platform Improvements

**Version**: 1.0
**Date**: 2026-02-10
**Author**: Auto-generated based on codebase audit
**Status**: Draft

---

## 1. Executive Summary

CyberVPN -- VPN-платформа с кибепанк-тематикой, включающая admin-панель (Next.js 16), REST API (FastAPI), мобильное приложение (Flutter) и инфраструктуру (Docker Compose). Аудит кодовой базы выявил критические проблемы безопасности, архитектурные пробелы, незавершённую функциональность и области для улучшения качества кода. Данный документ описывает все необходимые улучшения, сгруппированные по приоритету и области.

---

## 2. Current State

| Компонент | Стек | Состояние |
|-----------|------|-----------|
| Frontend (admin) | Next.js 16, React 19, TypeScript 5.9, Tailwind 4, Three.js | Активная разработка, 7 тестов |
| Backend | Python 3.13, FastAPI 0.128+, SQLAlchemy 2.0, PostgreSQL 17.7 | Активная разработка, 60+ тестов |
| Mobile | Flutter (Dart 3.10), Riverpod, go_router, V2Ray | Активная разработка, 195 тестов |
| Infrastructure | Docker Compose, PostgreSQL, Valkey/Redis, Prometheus/Grafana | Рабочее состояние |

---

## 3. Improvements

### 3.1 CRITICAL -- Security

---

#### SEC-01: Утечка секретов в репозитории

**Severity**: CRITICAL
**Component**: Infrastructure
**File**: `/infra/APIToken.txt`

**Текущее состояние**:
Файл `APIToken.txt` содержит реальные production-креденшалы в открытом виде:
- JWT API-токен
- Telegram Bot Token
- Admin User ID
- Support Bot Username

Эти данные доступны всем, кто имеет доступ к репозиторию, и сохраняются в истории git.

**Ожидаемый результат**:
- Все скомпрометированные токены отозваны и перевыпущены
- Файл удалён из истории git (`git filter-branch` или `git-filter-repo`)
- Паттерн `APIToken.txt` добавлен в `.gitignore`
- Документирован процесс ротации секретов

**Acceptance Criteria**:
- [ ] Токены отозваны в Remnawave и Telegram BotFather
- [ ] Файл удалён из всех коммитов в истории
- [ ] `.gitignore` обновлён
- [ ] Новые токены сгенерированы и сохранены в `.env` (не в git)

---

#### SEC-02: Certificate Pinning в мобильном приложении

**Severity**: CRITICAL
**Component**: Mobile
**File**: `cybervpn_mobile/lib/core/network/api_client.dart:56`

**Текущее состояние**:
Certificate pinning помечен как TODO. Без него приложение уязвимо к MITM-атакам -- злоумышленник может подменить сертификат и перехватить весь трафик между приложением и API.

**Ожидаемый результат**:
- Сконфигурированы SHA-256 fingerprints для production-сертификатов
- Реализован fallback-механизм при ротации сертификатов
- Тесты на отклонение невалидных сертификатов

**Acceptance Criteria**:
- [ ] Certificate fingerprints настроены для production и staging
- [ ] Приложение отклоняет соединения с невалидными сертификатами
- [ ] Задокументирован процесс обновления fingerprints при ротации сертификатов
- [ ] Интеграционные тесты покрывают pinning-логику

---

#### SEC-03: Platform Attestation (App Integrity)

**Severity**: CRITICAL
**Component**: Mobile
**File**: `cybervpn_mobile/lib/core/security/app_attestation.dart:220`

**Текущее состояние**:
Функция attestation -- заглушка. Нет проверки, что запросы приходят от подлинного приложения, а не от модифицированной копии или скрипта.

**Ожидаемый результат**:
- Интеграция с Google Play Integrity API (Android)
- Интеграция с Apple App Attest / DeviceCheck (iOS)
- Backend валидирует attestation-токены

**Acceptance Criteria**:
- [ ] Android: Play Integrity API интегрирован
- [ ] iOS: App Attest / DeviceCheck интегрирован
- [ ] Backend проверяет attestation-токены при аутентификации
- [ ] Graceful degradation для неподдерживаемых устройств

---

### 3.2 HIGH -- Incomplete Features

---

#### FEAT-01: Password Reset Flow

**Severity**: HIGH
**Component**: Backend + Frontend + Mobile

**Текущее состояние**:
Эндпоинты `POST /api/v1/auth/forgot-password` и `POST /api/v1/auth/reset-password` не реализованы в бэкенде. В мобильном приложении роуты на них указывают (`cybervpn_mobile/lib/core/constants/api_constants.dart:135-136`), но получат 404.

**Ожидаемый результат**:
- Backend: эндпоинты forgot-password (отправка email/OTP) и reset-password (установка нового пароля)
- Frontend: страница сброса пароля в auth-флоу
- Mobile: подключение существующего UI к реальному API

**Acceptance Criteria**:
- [ ] `POST /api/v1/auth/forgot-password` -- принимает email, отправляет reset-токен
- [ ] `POST /api/v1/auth/reset-password` -- принимает токен + новый пароль
- [ ] Reset-токены истекают через 15 минут
- [ ] Rate limiting на forgot-password (макс. 3 запроса в 10 минут)
- [ ] Frontend: страница `/[locale]/(auth)/reset-password`
- [ ] Mobile: экран сброса пароля подключен к API
- [ ] E2E-тесты на полный флоу

---

#### FEAT-02: Реальная интеграция подписок для мобильных пользователей

**Severity**: HIGH
**Component**: Backend
**Files**:
- `backend/src/application/use_cases/mobile_auth/login.py:127`
- `backend/src/application/use_cases/mobile_auth/telegram_auth.py:98`
- `backend/src/application/use_cases/mobile_auth/me.py:47`

**Текущее состояние**:
В трёх use-case'ах мобильной аутентификации данные подписки замоканы (TODO: Fetch actual subscription from Remnawave). Мобильные пользователи получают неактуальные данные о своих подписках.

**Ожидаемый результат**:
- Реальные запросы к Remnawave API для получения данных подписки
- Кеширование подписок в Redis с TTL
- Fallback-логика при недоступности Remnawave

**Acceptance Criteria**:
- [ ] `login` use-case получает реальную подписку из Remnawave
- [ ] `telegram_auth` use-case получает реальную подписку из Remnawave
- [ ] `me` use-case получает реальную подписку из Remnawave
- [ ] Результаты кешируются (TTL 5 минут)
- [ ] При недоступности Remnawave -- graceful degradation (кешированные данные или пустой объект)
- [ ] Unit-тесты с моками Remnawave API

---

#### FEAT-03: Delete Account

**Severity**: HIGH
**Component**: Frontend + Backend
**File**: `frontend/src/app/[locale]/delete-account/page.tsx:37`

**Текущее состояние**:
UI для удаления аккаунта реализован, но API-вызов отсутствует (TODO: Implement actual API call to backend). Пользователь видит форму, но ничего не происходит при отправке.

**Ожидаемый результат**:
- Backend: `DELETE /api/v1/users/me` или `POST /api/v1/users/me/delete`
- Frontend: подключение UI к API
- Подтверждение по email/OTP перед удалением
- Soft-delete с grace period (30 дней)

**Acceptance Criteria**:
- [ ] Backend-эндпоинт для удаления аккаунта
- [ ] Требуется подтверждение (пароль или OTP)
- [ ] Soft-delete: данные помечаются как удалённые, но хранятся 30 дней
- [ ] Отмена удаления через повторный логин в grace period
- [ ] Frontend вызывает API и показывает confirmation/success
- [ ] Удаление подписок и VPN-ключей при финальном удалении
- [ ] GDPR-совместимость: полное удаление персональных данных после grace period

---

### 3.3 HIGH -- Code Quality

---

#### QUAL-01: Типизация ответов Backend API

**Severity**: HIGH
**Component**: Backend

**Текущее состояние**:
46 из 73 эндпоинтов (63%) возвращают нетипизированный `dict`. В основном это прокси-маршруты к Remnawave. Это означает:
- Нет валидации ответов
- Нет автогенерации OpenAPI-документации для ответов
- Нет контракта между frontend и backend

**Ожидаемый результат**:
- Pydantic response-модели для всех эндпоинтов
- OpenAPI-документация генерируется автоматически
- Валидация ответов от Remnawave перед пробросом клиенту

**Acceptance Criteria**:
- [ ] Все эндпоинты имеют `response_model` в FastAPI-декораторе
- [ ] Pydantic-модели покрывают все поля ответов Remnawave
- [ ] OpenAPI-схема полная и корректная
- [ ] Тесты на response-модели

---

#### QUAL-02: Покрытие тестами Frontend

**Severity**: HIGH
**Component**: Frontend

**Текущее состояние**:
7 тестовых файлов для фронтенда при ~50+ компонентах и десятках модулей. Нет тестов для:
- Zustand stores (state management)
- API client (`lib/api/`)
- Utility-функции (`lib/`)
- Виджеты (`widgets/`)
- 3D-компоненты (`3d/`)
- i18n-логика

**Ожидаемый результат**:
- Минимум 60% покрытия тестами (line coverage)
- Тесты для всех stores
- Тесты для API-клиента (с моками)
- Тесты для критических UI-компонентов

**Acceptance Criteria**:
- [ ] Покрытие >= 60% (enforced в CI)
- [ ] Zustand stores: unit-тесты для всех actions/selectors
- [ ] API-клиент: тесты с MSW (Mock Service Worker)
- [ ] Виджеты: snapshot/integration тесты
- [ ] CI-pipeline блокирует merge при падении покрытия

---

#### QUAL-03: TypeScript Type Safety

**Severity**: HIGH
**Component**: Frontend
**Files**:
- `frontend/src/shared/ui/scramble-text.tsx` -- Timer ref type mismatch
- `frontend/src/middleware.ts` -- unsafe `any` types

**Текущее состояние**:
- Используется `NodeJS.Timeout` для browser `setInterval`/`setTimeout` (должен быть `number` или `ReturnType<typeof setInterval>`)
- `any` в middleware нарушает type safety

**Ожидаемый результат**:
- Все `any` типы заменены на конкретные
- Timer-типы исправлены
- Включён strict mode в `tsconfig.json` (если ещё не включён)

**Acceptance Criteria**:
- [ ] Zero `any` в продакшн-коде (допускается в тестах с обоснованием)
- [ ] Timer-типы исправлены на `ReturnType<typeof setInterval>`
- [ ] `npm run lint` и `npm run build` проходят без ошибок типов
- [ ] ESLint-правило `@typescript-eslint/no-explicit-any` включено как error

---

### 3.4 MEDIUM -- Code Hygiene

---

#### HYG-01: Удаление console.log из production-кода

**Severity**: MEDIUM
**Component**: Frontend
**Files**:
- `frontend/src/3d/shaders/CyberSphereShaderV2.ts:5`
- `frontend/src/lib/analytics/index.ts:34,39,44`
- `frontend/src/features/auth/components/TelegramLoginButton.tsx:32`
- `frontend/src/components/ui/InceptionButton.tsx:50`
- `frontend/src/shared/ui/error-boundary.tsx:25`
- `frontend/src/i18n/request.ts:45`

**Текущее состояние**:
`console.log` и `console.error` в production-коде. Могут утекать чувствительные данные в DevTools и загрязняют консоль.

**Ожидаемый результат**:
- Все `console.log` удалены или заменены на conditional logging
- Только `console.error` допускается в error-boundary с sanitized-данными
- ESLint-правило `no-console` настроено как warning/error

**Acceptance Criteria**:
- [ ] Все `console.log` удалены из production-кода
- [ ] `console.error` допускается только в error-boundary и с фильтрацией данных
- [ ] ESLint `no-console` правило: `error` для `log`, `warn` для `error`
- [ ] Альтернатива: conditional logger (`if (process.env.NODE_ENV === 'development')`)

---

#### HYG-02: Очистка временных и debug-файлов

**Severity**: MEDIUM
**Component**: Root / Frontend

**Текущее состояние**:
В корне проекта и в `frontend/src/` находятся файлы, которые не должны быть в репозитории:
- `test_perm.txt`, `test_perm2.txt` -- тестовые файлы в корне
- `frontend/src/test3.txt` -- тестовый файл в source
- `_apply.sh`, `_filter.jq`, `_fix.js`, `_fix_all.js`, `_update.js`, `_update_subtasks.py` -- скрипты-утилиты в корне
- `list_tasks_tmp.py` -- временный скрипт
- `opencode.json.backup-*` -- бэкап конфигов

**Ожидаемый результат**:
- Временные файлы удалены
- Utility-скрипты перемещены в `scripts/` или удалены
- `.gitignore` обновлён для предотвращения повторного добавления

**Acceptance Criteria**:
- [ ] `test_perm.txt`, `test_perm2.txt`, `test3.txt` удалены
- [ ] `list_tasks_tmp.py` удалён
- [ ] `opencode.json.backup-*` удалён, паттерн добавлен в `.gitignore`
- [ ] Utility-скрипты (`_fix.js`, `_update.js` и т.д.) перемещены в `scripts/` или удалены

---

### 3.5 MEDIUM -- Performance

---

#### PERF-01: Мемоизация React-компонентов

**Severity**: MEDIUM
**Component**: Frontend

**Текущее состояние**:
В ряде компонентов отсутствуют `useMemo`, `useCallback` и `React.memo`, что вызывает ненужные ре-рендеры, особенно критично для:
- Компонентов с Three.js (3D-сцены)
- Таблиц с большим количеством данных (TanStack Table)
- Компонентов с анимациями (motion)

**Ожидаемый результат**:
- Профилирование с React DevTools Profiler
- `React.memo` для leaf-компонентов в таблицах и списках
- `useMemo` для вычисляемых данных
- `useCallback` для обработчиков, передаваемых в дочерние компоненты

**Acceptance Criteria**:
- [ ] Профилирование проведено, bottleneck-компоненты определены
- [ ] Мемоизация добавлена в критические компоненты
- [ ] Нет ухудшения UX (FPS на dashboard >= 30)
- [ ] Нет regression: все существующие тесты проходят

---

### 3.6 MEDIUM -- Accessibility

---

#### A11Y-01: Доступность интерфейса

**Severity**: MEDIUM
**Component**: Frontend

**Текущее состояние**:
- Отсутствуют ARIA-атрибуты на интерактивных элементах
- Недостаточная семантическая HTML-разметка
- Не протестирована навигация с клавиатуры
- Контрастность cyberpunk-темы может быть недостаточной

**Ожидаемый результат**:
- WCAG 2.1 Level AA compliance для основных флоу
- ARIA-атрибуты на всех интерактивных элементах
- Полная навигация с клавиатуры
- Достаточная контрастность текста

**Acceptance Criteria**:
- [ ] Аудит с axe-core / Lighthouse Accessibility
- [ ] Все интерактивные элементы имеют `aria-label` или `aria-labelledby`
- [ ] Формы имеют связанные `<label>` элементы
- [ ] Focus management корректен (видимый focus ring, логичный tab order)
- [ ] Контрастность текста >= 4.5:1 (AA standard)
- [ ] Screen reader тестирование основных флоу (login, dashboard)

---

### 3.7 MEDIUM -- Architecture

---

#### ARCH-01: Consumer-Driven Contract Tests

**Severity**: MEDIUM
**Component**: Backend + Frontend + Mobile

**Текущее состояние**:
Нет contract-тестов между frontend/mobile и backend API. Изменение API может сломать клиентов без предупреждения.

**Ожидаемый результат**:
- OpenAPI-спецификация генерируется автоматически из FastAPI
- Contract-тесты (Pact или OpenAPI-based) в CI
- Breaking changes обнаруживаются до деплоя

**Acceptance Criteria**:
- [ ] OpenAPI-спецификация экспортируется в файл и версионируется
- [ ] CI проверяет, что спецификация актуальна
- [ ] Frontend и Mobile используют сгенерированные типы из OpenAPI
- [ ] Breaking changes блокируют merge

---

#### ARCH-02: Missing Backend Endpoints для Mobile

**Severity**: MEDIUM
**Component**: Backend
**File**: `cybervpn_mobile/lib/core/constants/api_constants.dart`

**Текущее состояние**:
24+ эндпоинтов в мобильном приложении помечены как TODO -- backend их не реализует:
- Status endpoint (`/api/v1/status`)
- FCM token management
- User profile updates
- Usage statistics
- Referral system
- Payment methods management
- Trial functionality
- WebSocket verification

**Ожидаемый результат**:
- Приоритизация: определить, какие из 24 эндпоинтов необходимы для MVP мобильного приложения
- Реализация приоритетных эндпоинтов
- Документирование API-контракта для остальных

**Acceptance Criteria**:
- [ ] Список эндпоинтов приоритизирован (must-have vs nice-to-have)
- [ ] Must-have эндпоинты реализованы с тестами
- [ ] OpenAPI-документация обновлена
- [ ] Mobile-клиент подключён к реальным эндпоинтам

---

### 3.8 LOW -- DevEx & Tooling

---

#### DX-01: CI/CD Pipeline Improvements

**Severity**: LOW
**Component**: Infrastructure / DevOps

**Текущее состояние**:
CI/CD pipelines (`.github/`) существуют, но не включают:
- Обязательные проверки покрытия тестами
- Security scanning (SAST/DAST)
- Dependency vulnerability scanning

**Ожидаемый результат**:
- GitHub Actions: lint + typecheck + test + coverage gate
- Dependabot или Renovate для обновления зависимостей
- CodeQL или Snyk для security scanning

**Acceptance Criteria**:
- [ ] PR checks: lint, typecheck, tests проходят
- [ ] Coverage gate: PR блокируется если покрытие падает
- [ ] Security scanning в CI (CodeQL, Snyk, или trivy)
- [ ] Dependabot настроен для npm, pip, pub

---

#### DX-02: Unified Logging Strategy

**Severity**: LOW
**Component**: Frontend + Backend

**Текущее состояние**:
- Backend: `structlog` (структурированное логирование) -- хорошо
- Frontend: `console.log/error` -- неструктурированно
- Mobile: разрозненные подходы

**Ожидаемый результат**:
- Frontend: интеграция с сервисом мониторинга ошибок (Sentry)
- Единый формат логов для корреляции запросов (request ID)
- Dashboards в Grafana для ошибок frontend/backend

**Acceptance Criteria**:
- [ ] Frontend: Sentry SDK интегрирован (errors + performance)
- [ ] Backend: request ID проставляется и логируется
- [ ] Frontend передаёт request ID в заголовках
- [ ] Grafana dashboard для ошибок

---

## 4. Priority Matrix

| ID | Название | Severity | Компонент | Тип |
|----|----------|----------|-----------|-----|
| SEC-01 | Утечка секретов | CRITICAL | Infra | Security |
| SEC-02 | Certificate Pinning | CRITICAL | Mobile | Security |
| SEC-03 | Platform Attestation | CRITICAL | Mobile | Security |
| FEAT-01 | Password Reset | HIGH | Full-stack | Feature |
| FEAT-02 | Mobile Subscriptions | HIGH | Backend | Feature |
| FEAT-03 | Delete Account | HIGH | Frontend + Backend | Feature |
| QUAL-01 | Response Models | HIGH | Backend | Quality |
| QUAL-02 | Frontend Tests | HIGH | Frontend | Quality |
| QUAL-03 | TypeScript Safety | HIGH | Frontend | Quality |
| HYG-01 | Console Cleanup | MEDIUM | Frontend | Hygiene |
| HYG-02 | Temp Files Cleanup | MEDIUM | Root | Hygiene |
| PERF-01 | React Memoization | MEDIUM | Frontend | Performance |
| A11Y-01 | Accessibility | MEDIUM | Frontend | UX |
| ARCH-01 | Contract Tests | MEDIUM | Full-stack | Architecture |
| ARCH-02 | Missing Endpoints | MEDIUM | Backend + Mobile | Architecture |
| DX-01 | CI/CD Improvements | LOW | DevOps | Tooling |
| DX-02 | Unified Logging | LOW | Full-stack | Tooling |

---

## 5. Dependencies Between Items

```
SEC-01 (Утечка секретов) -- нет зависимостей, делать ПЕРВЫМ

SEC-02 (Cert Pinning) --> SEC-03 (Attestation)
  (Pinning можно делать независимо, attestation -- после)

FEAT-01 (Password Reset) -- нет зависимостей
FEAT-02 (Subscriptions) --> ARCH-02 (Missing Endpoints)
  (Подписки -- часть большей задачи по API-эндпоинтам)
FEAT-03 (Delete Account) -- нет зависимостей

QUAL-01 (Response Models) --> ARCH-01 (Contract Tests)
  (Сначала типизировать ответы, потом contract-тесты)
QUAL-02 (Frontend Tests) -- нет зависимостей
QUAL-03 (TypeScript Safety) -- нет зависимостей

HYG-01 + HYG-02 -- нет зависимостей, можно параллельно

PERF-01 --> QUAL-02 (тесты нужны для regression check)
```

---

## 6. Out of Scope

Следующие задачи НЕ входят в текущий PRD:
- Новая функциональность, не связанная с выявленными пробелами
- Миграция на другой стек/фреймворк
- Редизайн UI/UX (только accessibility-улучшения)
- Масштабирование инфраструктуры (horizontal scaling)
- CrewAI orchestrator improvements
- Landing page и user portal (apps/)

---

## 7. Success Metrics

| Метрика | Текущее | Целевое |
|---------|---------|---------|
| Security issues (CRITICAL) | 3 | 0 |
| Backend response type coverage | 16% | 90%+ |
| Frontend test coverage | ~5% | 60%+ |
| Backend test coverage | ~70% | 80%+ |
| Console.log в production | 10+ | 0 |
| Unsafe `any` в TypeScript | 5+ | 0 |
| Incomplete features (HIGH) | 3 | 0 |
| WCAG 2.1 AA compliance | No | Yes (core flows) |
