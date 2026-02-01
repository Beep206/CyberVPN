# CyberVPN — Полное описание проекта

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Бизнес-модель и монетизация](#2-бизнес-модель-и-монетизация)
3. [Архитектура системы](#3-архитектура-системы)
4. [Технологический стек](#4-технологический-стек)
5. [Доменные сущности и модели данных](#5-доменные-сущности-и-модели-данных)
6. [API, интеграции и платежные шлюзы](#6-api-интеграции-и-платежные-шлюзы)
7. [Telegram-бот](#7-telegram-бот)
8. [Мобильное приложение](#8-мобильное-приложение)
9. [Админ-панель и фронтенд](#9-админ-панель-и-фронтенд)
10. [Безопасность](#10-безопасность)
11. [Инфраструктура и деплой](#11-инфраструктура-и-деплой)
12. [Мониторинг и observability](#12-мониторинг-и-observability)
13. [CI/CD](#13-cicd)
14. [Планируемые фичи](#14-планируемые-фичи)
15. [Необходимые специалисты](#15-необходимые-специалисты)

---

## 1. Обзор проекта

**CyberVPN** — это полнофункциональная платформа управления VPN-бизнесом, построенная как монорепозиторий. Платформа объединяет:

- **Admin Dashboard** — панель управления для администраторов с 3D-визуализацией серверов, cyberpunk-дизайном и поддержкой 27 локалей
- **Customer Frontend** — пользовательский портал для клиентов
- **Backend API** — REST API на FastAPI с Clean Architecture и DDD
- **Telegram Bot** — основной канал взаимодействия с пользователями, продажа подписок, выдача VPN-конфигураций
- **Task Worker** — фоновый обработчик задач (синхронизация серверов, проверка платежей, уведомления)
- **Mobile App** — кроссплатформенное мобильное приложение на Flutter с встроенным VPN-клиентом

### Структура монорепозитория

```
VPNBussiness/
├── admin/                 # Next.js 16 — админ-панель
├── frontend/              # Next.js 16 — пользовательский портал
├── backend/               # FastAPI — REST API (Clean Architecture + DDD)
├── cybervpn_mobile/       # Flutter — мобильное приложение
├── services/
│   ├── telegram-bot/      # aiogram 3 — Telegram-бот
│   └── task-worker/       # TaskIQ — фоновые задачи
├── infra/                 # Docker Compose — инфраструктура
├── docs/                  # Проектная документация
└── plan/                  # Руководства по деплою
```

---

## 2. Бизнес-модель и монетизация

### Основная модель
Подписочный VPN-сервис с несколькими тарифными планами:

| Тариф | Описание |
|-------|----------|
| **Basic** | Базовый доступ к VPN |
| **Pro** | Расширенный доступ, больше трафика |
| **Ultra** | Максимальный трафик, приоритетные серверы |
| **Cyber** | Премиум-тариф с эксклюзивными возможностями |

### Периоды подписки
- 1 месяц (30 дней)
- 3 месяца (90 дней)
- 6 месяцев (180 дней)
- 12 месяцев (365 дней)

### Источники дохода
1. **Продажа подписок** — основной доход
2. **Реферальная система** — +3 дня бонус реферу при привлечении друга, до 100 рефералов
3. **Программа лояльности** (планируется) — удержание клиентов через бонусные дни и привилегии

### Пробный период (Trial)
- Длительность: 2 дня
- Лимит трафика: 2 ГБ
- Автоматическая активация при первой регистрации через бота

### Каналы оплаты
- **Telegram Stars** — нативные платежи Telegram
- **CryptoBot** — криптовалютные платежи (mainnet/testnet)
- **YooKassa** — российский платёжный шлюз (Visa, MasterCard, ЮMoney, SBP)
- **Stripe** — международные карточные платежи (определён в enum, реализация планируется)

---

## 3. Архитектура системы

### Общая архитектура: микросервисы с общей базой данных

```
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│ Admin Panel   │   │  Frontend    │   │  Mobile App      │
│ (Next.js 16)  │   │ (Next.js 16) │   │  (Flutter)       │
└──────┬───────┘   └──────┬───────┘   └────────┬─────────┘
       │                  │                     │
       └──────────────────┼─────────────────────┘
                          │ HTTP/WebSocket
                          ▼
              ┌──────────────────────┐
              │   Backend API        │
              │   (FastAPI + DDD)    │
              └──────┬──────┬───────┘
                     │      │
          ┌──────────┘      └──────────┐
          ▼                            ▼
┌─────────────────┐        ┌──────────────────┐
│  PostgreSQL 17   │        │  Valkey/Redis 8  │
│  (основная БД)   │        │  (кэш, FSM, очер)│
└─────────────────┘        └──────────────────┘
          │                            │
          ▼                            ▼
┌─────────────────┐        ┌──────────────────┐
│  Task Worker     │        │  Telegram Bot    │
│  (TaskIQ)        │        │  (aiogram 3)     │
└────────┬────────┘        └──────────────────┘
         │
         ▼
┌──────────────────┐
│  Remnawave API   │  ← VPN-бэкенд (управление нодами, конфигами, пользователями)
│  (порт 3000)     │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│  VPN Nodes       │  ← Xray-core (VLESS-Reality, XHTTP, WS-TLS)
│  (10+ локаций)   │
└──────────────────┘
```

### Backend: Clean Architecture + DDD

```
backend/src/
├── presentation/       # FastAPI роуты, middleware, exception handlers
│                       # Только HTTP-логика, никакого бизнес-кода
├── application/        # Use Cases, DTO, сервисный слой
│                       # Оркестрация бизнес-операций
├── domain/             # Entities, Value Objects, интерфейсы репозиториев
│                       # ЧИСТЫЙ Python — ноль зависимостей от фреймворков
└── infrastructure/     # SQLAlchemy репозитории, Redis, httpx-клиенты
                        # Реализация интерфейсов из domain-слоя
```

**Ключевой принцип:** Domain-слой не импортирует ничего из FastAPI, SQLAlchemy или httpx. Все зависимости направлены внутрь (Dependency Inversion).

### Frontend: Feature-Sliced Design + Atomic Design

```
admin/src/ & frontend/src/
├── app/[locale]/          # Next.js App Router с i18n-маршрутизацией
│   └── (dashboard)/       # Группы маршрутов (серверы, пользователи, аналитика)
├── 3d/scenes/             # Three.js 3D-сцены (GlobalNetwork — интерактивный глобус)
├── widgets/               # Композиции компонентов на уровне страниц
├── shared/ui/             # Библиотека компонентов (Atomic Design)
│   ├── atoms/             # CypherText, ServerStatusDot, Scanlines
│   ├── molecules/         # ServerCard
│   └── organisms/         # Таблицы, формы
├── entities/              # Доменные модели (TypeScript типы)
└── i18n/                  # Конфигурация интернационализации (27 локалей)
```

### Mobile: Clean Architecture (Flutter)

```
cybervpn_mobile/lib/features/
├── auth/
│   ├── domain/            # Use Cases, Entities, Repository интерфейсы
│   ├── data/              # Data Sources, Models, Repository реализации
│   └── presentation/      # Screens, Widgets, Providers (Riverpod)
├── servers/               # Управление VPN-серверами
├── vpn/                   # VPN-подключение (flutter_v2ray_plus)
└── subscription/          # Управление подписками
```

---

## 4. Технологический стек

### 4.1 Admin Dashboard & Frontend (Next.js)

| Технология | Версия | Назначение |
|------------|--------|------------|
| Next.js | 16.1.5 | Фреймворк (App Router) |
| React | 19.2.1 | UI-библиотека |
| React Compiler | 1.0.0 | Автоматическая мемоизация |
| TypeScript | 5.9.2 | Типобезопасность |
| Tailwind CSS | 4.1.18 | CSS-фреймворк (утилитарный подход) |
| Three.js | 0.174.0 | 3D-графика (глобус серверов) |
| @react-three/fiber | 9.1.0 | React-рендерер для Three.js |
| @react-three/drei | 10.7.7 | Хелперы для R3F |
| Motion (ex Framer Motion) | 12.29.0 | Анимации и переходы |
| next-intl | 4.7.0 | Интернационализация (27 локалей, 5 RTL) |
| TanStack Query | 5.87.4 | Серверный стейт (кэш, мутации) |
| TanStack Table | 8.21.3 | Таблицы с сортировкой/фильтрацией |
| Zustand | 5.0.10 | Клиентский стейт |
| Lucide React | 0.563.0 | Иконки |
| Lenis | 1.3.17 | Плавный скролл (только frontend) |
| ESLint | 9.x | Линтинг (flat config) |

**Дизайн-система (Cyberpunk):**
- Цвета: Matrix Green (#00ff88), Neon Cyan (#00ffff), Neon Pink (#ff00ff)
- Шрифты: Orbitron (заголовки), JetBrains Mono (код)
- Эффекты: Scanlines overlay, CypherText scramble-анимация, 3D card transforms

### 4.2 Backend API (FastAPI)

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | ≥3.13 | Рантайм |
| FastAPI | ≥0.128.0 | Web-фреймворк (async) |
| Uvicorn | ≥0.30.0 | ASGI-сервер |
| Pydantic | ≥2.6.0 | Валидация данных и сериализация |
| SQLAlchemy | ≥2.0.23 | Async ORM |
| Alembic | ≥1.13.0 | Миграции базы данных |
| asyncpg | ≥0.29.0 | Асинхронный PostgreSQL-драйвер |
| httpx | ≥0.25.0 | Асинхронный HTTP-клиент |
| redis | ≥5.0.0 | Клиент Redis/Valkey |
| PyJWT | ≥2.8.0 | JWT-аутентификация |
| argon2-cffi | ≥23.1.0 | Хеширование паролей (Argon2id) |
| pyotp | ≥2.9.0 | 2FA (TOTP) |
| slowapi | — | Rate limiting |
| Ruff | — | Линтинг + форматирование |
| mypy | — | Статическая типизация |
| pytest + pytest-asyncio | — | Тестирование |

### 4.3 Telegram Bot (aiogram 3)

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | ≥3.13 | Рантайм |
| aiogram | ≥3.24 | Telegram Bot Framework |
| httpx | ≥0.28.1 | HTTP-клиент для Backend API |
| redis[hiredis] | ≥7.1 | FSM storage (состояния диалогов) |
| structlog | ≥25.5 | Структурированное логирование (JSON) |
| qrcode[pil] | ≥8.0 | Генерация QR-кодов для VPN-конфигов |
| fluent.runtime | ≥0.4 | Интернационализация (Fluent формат, ru/en) |
| prometheus-client | ≥0.24.1 | Экспорт метрик |
| tenacity | ≥9.0 | Retry-логика |

### 4.4 Task Worker (фоновые задачи)

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | ≥3.13 | Рантайм |
| taskiq | ≥0.12.1 | Фреймворк очередей задач |
| taskiq-redis | ≥1.2.1 | Redis-брокер для TaskIQ |
| SQLAlchemy[asyncio] | ≥2.0 | Async ORM |
| httpx | ≥0.28 | HTTP-клиент |
| redis[hiredis] | ≥5.2 | Брокер сообщений |
| structlog | ≥24.4 | Логирование |
| prometheus-client | ≥0.21 | Метрики |

**Периодические задачи:**
- Синхронизация нод: каждые 5 минут
- Геолокация серверов: каждые 6 часов
- Health check серверов: каждые 2 минуты
- Мониторинг bandwidth: каждые 5 минут
- Обновление статистики трафика: каждые 10 минут
- Сброс трафика: 1-е число каждого месяца
- Конфигурации серверов: каждые 30 минут

### 4.5 Мобильное приложение (Flutter)

| Технология | Версия | Назначение |
|------------|--------|------------|
| Flutter SDK | ≥3.10.8 | Кроссплатформенный фреймворк |
| Dart | ≥3.10.8 | Язык программирования |
| flutter_riverpod | 3.0.3 | State management |
| go_router | 17.0.0 | Навигация |
| dio | 5.9.0 | HTTP-клиент |
| flutter_v2ray_plus | 1.0.11 | **Ядро VPN-клиента** (V2Ray/Xray) |
| freezed | 3.0.6 | Иммутабельные модели (кодогенерация) |
| json_serializable | 6.9.5 | JSON-сериализация |
| flutter_secure_storage | 9.2.4 | Безопасное хранилище (Keychain/Keystore) |
| local_auth | 2.3.0 | Биометрическая аутентификация |
| purchases_flutter | 9.10.8 | In-App Purchases (RevenueCat) |
| firebase_core | 3.13.0 | Firebase SDK |
| firebase_messaging | 15.2.4 | Push-уведомления |

**Поддерживаемые платформы:** Android, iOS, Linux, macOS, Windows

### 4.6 Инфраструктура

| Технология | Версия | Порт | Назначение |
|------------|--------|------|------------|
| PostgreSQL | 17.7 | 6767 | Основная база данных |
| Valkey (Redis-совместимый) | 8.1-alpine | 6379 | Кэш, FSM, очереди |
| Remnawave Backend | 2.x | 3000 | VPN-панель (управление нодами и пользователями) |
| Caddy | 2.9 | 80/443 | Reverse proxy + автоматический TLS |
| Prometheus | latest | 9090 | Сбор метрик |
| Grafana | latest | 3002 | Визуализация метрик |
| Alertmanager | latest | 9093 | Алертинг |
| Docker + Docker Compose | — | — | Контейнеризация |

### 4.7 VPN-стек

| Технология | Назначение |
|------------|------------|
| Remnawave | VPN-панель управления (provisioning, configs, traffic) |
| Xray-core | VPN-протоколы на нодах |
| VLESS-Reality | Основной протокол (анти-DPI) |
| XHTTP-Reality | Альтернативный протокол |
| WS-TLS | WebSocket-based протокол |
| Clash | Формат конфигурации клиента |
| Hiddify | Формат конфигурации клиента |
| Outline | Формат конфигурации клиента |
| Sing-box | Формат конфигурации клиента |
| V2Ray | Формат конфигурации клиента |

---

## 5. Доменные сущности и модели данных

### User (Пользователь)

| Поле | Тип | Описание |
|------|-----|----------|
| uuid | UUID | Уникальный идентификатор |
| username | str | Имя пользователя |
| email | str / None | Email (опционально) |
| telegram_id | int / None | Telegram ID |
| status | Enum | active / disabled / limited / expired |
| subscription_uuid | UUID / None | UUID подписки в Remnawave |
| expire_at | datetime / None | Дата окончания подписки |
| traffic_limit_bytes | int / None | Лимит трафика |
| used_traffic_bytes | int / None | Использованный трафик |
| subscription_url | str / None | Ссылка на подписку (VPN-конфиг) |

### SubscriptionPlan (Тарифный план)

| Поле | Тип | Описание |
|------|-----|----------|
| uuid | UUID | Уникальный идентификатор |
| name | str | Название плана |
| tier | Enum | basic / pro / ultra / cyber |
| price_usd | Decimal | Цена в USD |
| duration_days | int | Длительность в днях |
| traffic_limit_bytes | int / None | Лимит трафика |

### Payment (Платёж)

| Поле | Тип | Описание |
|------|-----|----------|
| uuid | UUID | Уникальный идентификатор |
| user_uuid | UUID | UUID пользователя |
| amount | Decimal | Сумма |
| currency | str | Валюта (RUB, USD, USDT и т.д.) |
| status | Enum | pending / completed / failed / refunded |
| provider | Enum | cryptobot / yookassa / stripe |
| subscription_days | int | Количество дней подписки |

### Server (VPN-сервер)

| Поле | Тип | Описание |
|------|-----|----------|
| uuid | UUID | Уникальный идентификатор |
| name | str | Название сервера |
| address | str | IP-адрес |
| port | int | Порт |
| country_code | str / None | Код страны (ISO) |
| status | Enum | online / offline / warning / maintenance |
| is_connected | bool | Подключён к панели |
| is_disabled | bool | Отключён администратором |
| users_online | int / None | Пользователей онлайн |

### Admin Roles (Роли администраторов)

| Роль | Описание |
|------|----------|
| super_admin | Полный доступ ко всему |
| admin | Управление пользователями и серверами |
| operator | Операционные задачи |
| support | Поддержка пользователей |
| viewer | Только просмотр |

---

## 6. API, интеграции и платежные шлюзы

### REST API эндпоинты (Backend)

#### Аутентификация
```
POST   /api/v1/auth/register          # Регистрация пользователя
POST   /api/v1/auth/login             # Вход (JWT)
POST   /api/v1/auth/refresh           # Обновление access token
POST   /api/v1/auth/logout            # Выход (инвалидация токена)
POST   /api/v1/two-factor/enable      # Включение 2FA (TOTP)
POST   /api/v1/two-factor/verify      # Подтверждение 2FA
```

#### Пользователи
```
GET    /api/v1/users                   # Список пользователей (admin)
GET    /api/v1/users/{id}              # Информация о пользователе
PATCH  /api/v1/users/{id}              # Обновление пользователя
DELETE /api/v1/users/{id}              # Удаление пользователя
```

#### Подписки
```
GET    /api/v1/plans                   # Список тарифных планов
GET    /api/v1/subscriptions           # Список подписок
POST   /api/v1/subscriptions           # Создание подписки
GET    /api/v1/subscriptions/{id}/config  # Скачать VPN-конфиг
```

#### Платежи
```
POST   /api/v1/payments/crypto/invoice # Создать крипто-инвойс (CryptoBot)
GET    /api/v1/payments/{id}           # Статус платежа
POST   /api/v1/webhooks/cryptobot      # Вебхук CryptoBot
POST   /api/v1/webhooks/yookassa       # Вебхук YooKassa
```

#### Серверы
```
GET    /api/v1/servers                 # Список VPN-серверов
GET    /api/v1/servers/{id}            # Детали сервера
GET    /api/v1/servers/{id}/stats      # Статистика сервера
```

#### Мониторинг и WebSocket
```
GET    /api/v1/monitoring/health       # Healthcheck
GET    /api/v1/monitoring/bandwidth    # Аналитика bandwidth
GET    /api/v1/monitoring/stats        # Системные статистики
WS     /api/v1/ws/monitoring           # Real-time мониторинг
WS     /api/v1/ws/notifications        # Real-time уведомления
```

#### Telegram-интеграция
```
POST   /api/v1/telegram/register       # Регистрация Telegram-пользователя
GET    /api/v1/telegram/user/{tg_id}   # Получить пользователя по Telegram ID
```

### Интеграция с Remnawave

Backend общается с Remnawave через httpx (SDK `remnawave` v2.4.4+):

```python
# Управление пользователями
await remnawave.users.create_user(username, traffic_limit_bytes, expire_at)
await remnawave.users.get_all_users_v2()
await remnawave.users.disable_user(user_uuid)
await remnawave.users.get_subscription_link(user_uuid)

# Управление серверами
await remnawave.nodes.get_all()
await remnawave.nodes.health_check(node_id)

# Системная статистика
await remnawave.system.get_stats()
await remnawave.system.get_bandwidth()
```

**Remnawave Webhooks (25+ типов событий):**
- `user.created`, `user.expired`, `user.expires_in_24_hours`
- `user.first_connected`, `user.bandwidth_usage_threshold_reached`
- `node.created`, `node.offline`, `node.online`
- `service.started`, `service.stopped`

### Платёжная система — поток обработки

```
1. Пользователь выбирает тариф и способ оплаты
2. Backend создает запись Payment (status: pending)
3. Backend запрашивает инвойс у платёжного шлюза
4. Пользователь оплачивает по ссылке/QR
5. Шлюз отправляет webhook → Backend верифицирует подпись (HMAC-SHA256)
6. Payment.status → completed
7. Task Worker: верификация платежа, активация подписки в Remnawave
8. Уведомление пользователю + выдача VPN-конфига
```

---

## 7. Telegram-бот

### Команды для пользователей

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация, главное меню |
| `/menu` | Главное меню |
| `/config` | Получить VPN-конфигурацию + QR-код |
| `/support` | Связаться с поддержкой |
| `/trial` | Активировать пробный период (2 дня, 2 ГБ) |
| `/referral` | Получить реферальную ссылку |

### Админ-команды

| Функция | Описание |
|---------|----------|
| Статистика | Пользователи, платежи, подписки |
| Рассылка (Broadcast) | Всем / активным / trial-пользователям |
| Управление пользователями | Поиск, редактирование, бан/разбан |
| Управление планами | Создание и редактирование тарифов |
| Промокоды | Создание и управление |
| Платёжные шлюзы | Конфигурация провайдеров |
| Уведомления | Шаблоны уведомлений |
| Логи | Просмотр логов бота |

### Ключевые особенности бота
- **FSM (Finite State Machine)** для диалогов с пользователем
- **Redis-backed** хранение состояний
- **Мультиязычность** (русский, английский) через Fluent i18n
- **QR-коды** для VPN-конфигураций
- **Реферальная система** — бонус 3 дня, лимит 100 рефералов
- **Prometheus-метрики** для мониторинга

---

## 8. Мобильное приложение

### Основные экраны
- **Авторизация** — вход, регистрация, биометрия
- **Список серверов** — выбор VPN-сервера по локации
- **VPN-подключение** — one-tap connect/disconnect
- **Подписка** — просмотр тарифов, In-App Purchases (RevenueCat)
- **Профиль** — настройки, статистика трафика

### Технические особенности
- **VPN-ядро:** flutter_v2ray_plus (V2Ray/Xray протоколы)
- **State management:** Riverpod
- **Иммутабельные модели:** Freezed + json_serializable (кодогенерация)
- **Безопасное хранилище:** flutter_secure_storage (Keychain на iOS, Keystore на Android)
- **Push-уведомления:** Firebase Cloud Messaging
- **In-App Purchases:** RevenueCat (purchases_flutter)

---

## 9. Админ-панель и фронтенд

### Ключевые функции админ-панели

#### 3D-глобус серверов (Three.js + React Three Fiber)
- Интерактивный глобус с серверными точками
- Линии подключений в реальном времени
- Индикаторы статуса серверов (цветовая кодировка)

#### Управление серверами
- Таблица серверов (TanStack Table) с сортировкой и фильтрацией
- Обновления статуса в реальном времени (WebSocket)
- Графики bandwidth
- Геолокация (флаги стран)

#### Управление пользователями
- Список с поиском и фильтрацией
- Статус подписки
- Мониторинг трафика
- Быстрые действия: продлить, забанить, сбросить трафик

#### Аналитика
- Статистика платежей
- Графики роста пользователей
- Отслеживание дохода
- Конверсии

### Интернационализация
- **27 локалей** через next-intl
- **5 RTL-языков:** арабский, иврит, фарси, урду, курдский
- Файлы переводов: `admin/messages/{locale}/`

---

## 10. Безопасность

### Аутентификация
- **JWT** (HS256, ротируемые секреты)
  - Access token: 15 минут TTL
  - Refresh token: 7 дней TTL
  - Чёрный список токенов в Redis
- **2FA (TOTP)** через pyotp — генерация QR для Google Authenticator
- **Пароли:** Argon2id (argon2-cffi) — рекомендация OWASP 2025
- **OAuth** — подготовлена таблица для social login

### Авторизация
- 5 ролей администраторов (super_admin → viewer) с разграничением прав
- Проверки на уровне API middleware

### Защита API
- **Rate limiting** через slowapi
- **CORS** — явный список разрешённых origins (без wildcards в production)
- **OWASP Security Headers** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Валидация входных данных** — Pydantic-схемы на границе API
- **SQL Injection** — параметризованные запросы SQLAlchemy

### Защита вебхуков
- **HMAC-SHA256 верификация подписи** для всех входящих вебхуков
- **Constant-time сравнение** (hmac.compare_digest) — защита от timing-атак
- **Минимальная длина секрета** — 32 символа

### Инфраструктурная безопасность
- UFW-firewall на серверах
- SSH только по ключам
- Non-root контейнеры (Telegram-бот)
- Basic auth на метриках Prometheus
- TLS на всех публичных эндпоинтах
- Fail2ban для SSH

---

## 11. Инфраструктура и деплой

### Docker Compose — профили сервисов

| Профиль | Сервисы | Назначение |
|---------|---------|------------|
| *(базовый)* | remnawave, postgres, valkey | Ядро системы |
| `worker` | cybervpn-worker, cybervpn-scheduler | Фоновые задачи |
| `bot` | cybervpn-telegram-bot, remnashop-redis | Telegram-бот |
| `bot-legacy` | remnashop | Устаревший бот |
| `monitoring` | prometheus, grafana, alertmanager | Мониторинг |
| `proxy` | caddy | Reverse proxy + TLS |
| `subscription` | remnawave-subscription-page | Страница подписки |

### Запуск окружения

```bash
cd infra

# Ядро
docker compose up -d

# + Фоновые задачи
docker compose --profile worker up -d

# + Telegram-бот
docker compose --profile bot up -d

# + Мониторинг
docker compose --profile monitoring up -d

# + Reverse proxy
docker compose --profile proxy up -d
```

### Production-инфраструктура (из документации)

| Компонент | Ресурсы | Расположение |
|-----------|---------|--------------|
| Основной сервер | 4 ГБ RAM, 2 vCPU, 40 ГБ SSD | Люксембург |
| VPN-ноды (10+) | 1–2 ГБ RAM каждая | Глобально |
| DNS | Cloudflare | DNS-only для VPN-нод |
| SSL | Let's Encrypt (через Caddy) | Автоматический |
| Бэкапы | Автоматические в Telegram | Ежедневно |

### Dockerfiles

- **Backend:** `python:3.13-slim`, single-stage, порт 8000
- **Task Worker:** multi-stage (builder + runtime), `python:3.13-slim`, healthcheck, 2 воркера
- **Telegram Bot:** multi-stage, non-root пользователь `botuser`, порт метрик 9092

---

## 12. Мониторинг и Observability

### Prometheus — метрики

**Scrape-конфигурация:**
| Job | Порт | Интервал |
|-----|------|----------|
| remnawave | 3001 | 15s (default) |
| cybervpn-worker | 9091 | 10s |
| cybervpn-telegram-bot | 9092 | 15s |
| prometheus | 9090 | 15s |

**Бот-метрики:**
- `bot_updates_total` — общее количество обновлений
- `bot_commands_total{command}` — использование команд
- `bot_api_requests_total{method,status}` — вызовы Backend API
- `bot_payments_total{gateway,status}` — транзакции
- `bot_errors_total{type}` — ошибки

### Alerting — правила алертов

| Алерт | Условие | Severity |
|-------|---------|----------|
| TaskWorkerDown | Недоступен 5 минут | critical |
| HighTaskErrorRate | Ошибки > 5% за 10 минут | warning |
| TaskQueueBacklog | Очередь > 100 задач за 15 минут | warning |
| HighTaskDuration | P95 > 30 секунд за 10 минут | warning |
| RedisConnectionFailing | Ошибки Redis 3 минуты | critical |
| NoTasksProcessed | Нет задач 15 минут | warning |
| HighExternalAPIFailureRate | Ошибки API > 10% за 5 минут | warning |

### Логирование
- **Формат:** Структурированный JSON (structlog)
- **Уровни:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Обогащение контекста:** user_id, request_id, task_id
- **Docker logging:** json-file драйвер (max 100MB, 5 файлов)

### Grafana
- Порт 3002, провизионированные дашборды и datasources
- Предустановленные панели для визуализации метрик

---

## 13. CI/CD

### GitHub Actions — task-worker-ci.yml

**Триггеры:**
- Push в main/develop (при изменении task-worker)
- Pull Request'ы затрагивающие task-worker

**Jobs:**

| Job | Описание |
|-----|----------|
| **lint** | Ruff — линтинг и проверка форматирования |
| **test** | pytest + coverage, загрузка в Codecov |
| **typecheck** | mypy — статическая типизация |
| **docker-build** | Сборка Docker-образа (buildx + layer caching) |
| **security** | pip-audit — сканирование зависимостей |
| **all-checks** | Агрегация — проверка что все jobs прошли |

**Примечание:** CI на данный момент только валидирует код. Автоматический деплой не настроен — деплой выполняется вручную через Docker Compose.

---

## 14. Планируемые фичи

### 14.1 Invite System (система приглашений)

**Статус:** Фаза дизайна (PRD готов)

**Механика:**
- Пользователи с оплаченной подпиской получают коды приглашений
- Приглашённый друг получает бесплатный доступ (7–30 дней в зависимости от плана)
- Реферер получает +7 дней бонуса когда друг оплачивает
- Администратор управляет правилами приглашений по тарифам
- Промо-акции (например, 2x приглашений на праздники)
- Ручная выдача доступа для партнёров и тестеров

**Планируемые таблицы БД:**
- `invite_rules` — правила для каждого тарифа
- `invites` — выданные коды (available / used / expired)

### 14.2 Loyalty Program (программа лояльности)

**Статус:** Фаза дизайна (PRD готов)

**4 уровня:**

| Уровень | Стаж | Бонус |
|---------|------|-------|
| **Bronze** | 0 месяцев | Базовый доступ |
| **Silver** | 3 месяца | +3 дня бонус |
| **Gold** | 6 месяцев | +7 дней, приоритетная поддержка |
| **Platinum** | 12 месяцев | +14 дней, премиум-ноды, ранний доступ |

**Механика:**
- Отслеживание непрерывных оплат
- Grace-период: 14 дней для сохранения уровня
- Ускоренный рост уровня для длинных подписок
- Уведомления: повышение уровня, предупреждение о grace-периоде

---

## 15. Необходимые специалисты

### 15.1 Backend Python Developer (Senior)

**Основные обязанности:**
- Разработка и поддержка REST API на FastAPI
- Реализация бизнес-логики (Clean Architecture + DDD)
- Интеграция с платёжными шлюзами и Remnawave
- Проектирование миграций БД (Alembic)

**Обязательные знания:**

| Категория | Технологии |
|-----------|------------|
| Язык | Python 3.13+, async/await, type hints |
| Фреймворк | FastAPI, Pydantic v2, Uvicorn |
| Архитектура | Clean Architecture, DDD, SOLID, Repository Pattern |
| ORM | SQLAlchemy 2.0 (async), Alembic |
| БД | PostgreSQL (оптимизация запросов, индексы, миграции) |
| Кэш | Redis / Valkey |
| HTTP-клиент | httpx (async) |
| Безопасность | JWT (PyJWT), Argon2, TOTP (pyotp), HMAC, OWASP |
| Тестирование | pytest, pytest-asyncio, моки, fixtures |
| Код-стиль | Ruff, mypy (strict) |
| API-дизайн | REST, OpenAPI, версионирование API |

**Желательные знания:**
- TaskIQ или аналоги (Celery, Dramatiq) для фоновых задач
- Docker, Docker Compose
- Prometheus (экспорт метрик)
- Structlog (структурированное логирование)
- aiogram (базовое понимание Telegram Bot API)
- VPN-протоколы (Xray, V2Ray) — хотя бы на уровне понимания

---

### 15.2 Frontend React/Next.js Developer (Middle–Senior)

**Основные обязанности:**
- Разработка админ-панели и пользовательского портала
- Реализация 3D-визуализаций (глобус серверов)
- Интернационализация (27 локалей, RTL)
- Работа с real-time данными (WebSocket)

**Обязательные знания:**

| Категория | Технологии |
|-----------|------------|
| Фреймворк | Next.js 16 (App Router, Server Components, RSC) |
| UI | React 19, TypeScript 5.x |
| Стилизация | Tailwind CSS 4.x |
| 3D-графика | Three.js, React Three Fiber (@react-three/fiber, drei) |
| Анимации | Motion (Framer Motion) |
| Стейт | Zustand (клиентский), TanStack Query (серверный) |
| Таблицы | TanStack Table |
| i18n | next-intl (27 локалей, RTL support) |
| Архитектура | Feature-Sliced Design, Atomic Design |
| Код-стиль | ESLint 9 (flat config), TypeScript strict |

**Желательные знания:**
- WebSocket-интеграция
- Оптимизация производительности React (React Compiler, memoization)
- SEO и Web Vitals
- Доступность (a11y)
- Storybook для компонентного каталога

---

### 15.3 Flutter Mobile Developer (Middle–Senior)

**Основные обязанности:**
- Разработка кроссплатформенного мобильного приложения
- Интеграция VPN-ядра (V2Ray)
- Реализация In-App Purchases
- Push-уведомления

**Обязательные знания:**

| Категория | Технологии |
|-----------|------------|
| Фреймворк | Flutter ≥3.10, Dart |
| State management | Riverpod |
| Навигация | go_router |
| Сеть | dio (HTTP-клиент) |
| Кодогенерация | freezed, json_serializable, build_runner |
| Безопасность | flutter_secure_storage, local_auth (биометрия) |
| Платежи | purchases_flutter (RevenueCat) |
| Push | Firebase Messaging |
| Clean Architecture | Разделение domain/data/presentation |

**Желательные знания:**
- Опыт с VPN-клиентами (V2Ray, Xray, WireGuard)
- flutter_v2ray_plus или аналогичные VPN-библиотеки
- Публикация в App Store и Google Play
- Platform channels (Kotlin/Swift interop)
- Работа с background services (VPN-тоннель в фоне)

---

### 15.4 DevOps / Infrastructure Engineer (Middle–Senior)

**Основные обязанности:**
- Деплой и управление инфраструктурой (10+ VPN-нод глобально)
- Настройка мониторинга и алертинга
- CI/CD пайплайны
- Безопасность серверов
- Бэкапы и восстановление

**Обязательные знания:**

| Категория | Технологии |
|-----------|------------|
| Контейнеризация | Docker, Docker Compose (profiles, multi-stage builds) |
| ОС | Linux (Ubuntu), systemd, UFW, Fail2ban |
| Мониторинг | Prometheus, Grafana, Alertmanager |
| Reverse proxy | Caddy (или Nginx) + Let's Encrypt |
| CI/CD | GitHub Actions |
| Сеть | DNS (Cloudflare), TLS/SSL, iptables |
| Скриптинг | Bash, Python |
| Безопасность | SSH hardening, firewall, secrets management |

**Желательные знания:**
- Terraform / Ansible (IaC — пока не внедрено, но планируется)
- Kubernetes (для масштабирования)
- VPN-протоколы (Xray, VLESS-Reality) — на уровне деплоя
- Remnawave панель — установка и обслуживание
- PostgreSQL-администрирование (бэкапы, репликация)
- Опыт работы с VPS-провайдерами (Hetzner, DigitalOcean, AWS)

---

### 15.5 Telegram Bot Developer (Middle)

**Основные обязанности:**
- Разработка и поддержка Telegram-бота
- Реализация платёжных flow через бота
- Админ-панель внутри бота
- Интеграция с Backend API

**Обязательные знания:**

| Категория | Технологии |
|-----------|------------|
| Фреймворк | aiogram 3.x |
| Язык | Python 3.13+, async/await |
| FSM | Redis-backed Finite State Machine |
| Платежи | Telegram Stars, CryptoBot API |
| i18n | Fluent (fluent.runtime) |
| HTTP-клиент | httpx (async) |
| Мониторинг | prometheus-client |
| Retry | tenacity |
| QR | qrcode[pil] |

**Желательные знания:**
- Telegram Bot API (webhooks, inline keyboards, payments)
- Structlog (JSON-логирование)
- Docker (деплой бота)
- Ruff, mypy

---

### 15.6 QA Engineer (Middle)

**Основные обязанности:**
- Тестирование всех компонентов системы
- Написание и поддержка автотестов
- Тестирование платёжных flow
- Нагрузочное тестирование

**Обязательные знания:**

| Категория | Технологии |
|-----------|------------|
| Backend-тесты | pytest, pytest-asyncio, httpx (TestClient) |
| Frontend-тесты | Jest / Vitest, React Testing Library, Playwright |
| Mobile-тесты | Flutter testing, integration tests |
| API-тестирование | Postman / Bruno, REST API |
| Стратегия | Unit → Integration → E2E (пирамида тестирования) |
| VPN-тестирование | Проверка подключений, утечек DNS, kill switch |

**Желательные знания:**
- Нагрузочное тестирование (k6, Locust)
- Тестирование Telegram-ботов
- Docker (тестовые окружения)
- CI/CD (GitHub Actions — запуск тестов)
- Тестирование платёжных систем (sandbox-окружения)

---

### 15.7 UI/UX Designer (Middle)

**Основные обязанности:**
- Дизайн интерфейсов (админ-панель, мобильное приложение, лендинг)
- Поддержка cyberpunk-дизайн-системы
- Прототипирование пользовательских flow
- Адаптив и RTL-вёрстка

**Обязательные знания:**

| Категория | Требования |
|-----------|------------|
| Инструменты | Figma (компоненты, авто-лейаут, прототипы) |
| Стиль | Cyberpunk / Sci-fi эстетика, неоновая палитра, 3D-элементы |
| Платформы | Web (responsive), Mobile (iOS/Android), Telegram Mini Apps |
| RTL | Опыт с RTL-лейаутами (арабский, иврит) |
| Дизайн-системы | Atomic Design, токены, компонентные библиотеки |
| Анимации | Motion design (transitions, micro-interactions) |

**Желательные знания:**
- 3D-визуализация (Blender, Spline)
- Tailwind CSS (понимание utility-first подхода)
- Опыт с VPN-продуктами или B2C SaaS
- Работа с i18n (адаптация UI под разные языки)

---

### 15.8 Product Manager / Business Analyst

**Основные обязанности:**
- Управление продуктовым роадмапом
- Написание PRD и спецификаций
- Анализ метрик и конверсий
- Работа с конкурентным окружением VPN-рынка

**Обязательные знания:**

| Категория | Требования |
|-----------|------------|
| Продукт | Опыт B2C SaaS / подписочных продуктов |
| Аналитика | Метрики: LTV, CAC, Churn, MRR, ARPU |
| Инструменты | Jira / Linear, Task Master, Figma |
| Методологии | Agile/Scrum, User Story Mapping, Jobs-to-be-done |
| Рынок | Понимание VPN-рынка, конкуренты, регуляции |

**Желательные знания:**
- Telegram-маркетинг и продвижение ботов
- Работа с криптоплатежами
- Ценообразование подписочных продуктов
- A/B-тестирование
- Опыт с реферальными и лояльностными программами

---

### Сводная таблица специалистов

| Роль | Уровень | Приоритет | Ключевые технологии |
|------|---------|-----------|---------------------|
| Backend Python Developer | Senior | Критичный | Python 3.13, FastAPI, SQLAlchemy, DDD, PostgreSQL |
| Frontend Next.js Developer | Middle–Senior | Критичный | Next.js 16, React 19, Three.js, TypeScript, Tailwind |
| Flutter Mobile Developer | Middle–Senior | Высокий | Flutter, Riverpod, V2Ray, RevenueCat |
| DevOps Engineer | Middle–Senior | Высокий | Docker, Prometheus, Grafana, Linux, CI/CD |
| Telegram Bot Developer | Middle | Высокий | aiogram 3, Redis, Telegram API, Python |
| QA Engineer | Middle | Средний | pytest, Playwright, API testing |
| UI/UX Designer | Middle | Средний | Figma, Cyberpunk design, Mobile, RTL |
| Product Manager | Middle–Senior | Средний | B2C SaaS, VPN-рынок, аналитика |

---

*Документ сгенерирован на основе анализа кодовой базы проекта VPNBussiness. Актуален на 31 января 2026 года.*
