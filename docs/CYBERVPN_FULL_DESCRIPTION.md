# CyberVPN — Полное техническое описание платформы

> **Версия документа:** 2.0 · **Дата:** 8 апреля 2026  
> **Цель:** Исчерпывающее описание архитектуры, стека, протоколов, возможностей платформы и стратегии внедрения собственного VPN-протокола (Helix)

---

## Содержание

1. [Обзор и миссия проекта](#1-обзор-и-миссия-проекта)
2. [Архитектура монорепозитория](#2-архитектура-монорепозитория)
3. [Технологический стек (полный)](#3-технологический-стек-полный)
4. [VPN-протоколы и транспорты](#4-vpn-протоколы-и-транспорты)
5. [Remnawave 2.7.x — ядро управления VPN](#5-remnawave-27x--ядро-управления-vpn)
6. [Helix — наш собственный transport stack](#6-helix--наш-собственный-transport-stack)
7. [Backend API (FastAPI + DDD)](#7-backend-api-fastapi--ddd)
8. [Frontend Dashboard (Next.js 16)](#8-frontend-dashboard-nextjs-16)
9. [Desktop Client (Tauri + Rust)](#9-desktop-client-tauri--rust)
10. [Mobile Client (Flutter)](#10-mobile-client-flutter)
11. [Telegram Bot (aiogram 3)](#11-telegram-bot-aiogram-3)
12. [Task Worker (TaskIQ)](#12-task-worker-taskiq)
13. [Инфраструктура и Docker](#13-инфраструктура-и-docker)
14. [Observability (мониторинг, трейсинг, логи)](#14-observability)
15. [Безопасность и аутентификация](#15-безопасность-и-аутентификация)
16. [Бизнес-модель и монетизация](#16-бизнес-модель-и-монетизация)
17. [Доменные сущности](#17-доменные-сущности)
18. [Internationalization (38 локалей)](#18-internationalization)
19. [Стратегия разработки собственного протокола](#19-стратегия-разработки-собственного-протокола)
20. [Roadmap и планируемые фичи](#20-roadmap)

---

## 1. Обзор и миссия проекта

**CyberVPN** — полнофункциональная платформа для управления VPN-бизнесом корпоративного и потребительского уровня. Проект объединяет:

- **Admin Dashboard** — панель с 3D-визуализацией серверов в стиле Cyberpunk
- **Backend API** — REST API на FastAPI (Clean Architecture + DDD)
- **Desktop VPN Client** — нативный клиент на Tauri/Rust с BGP split tunneling
- **Mobile App** — кроссплатформенное приложение на Flutter
- **Telegram Bot** — канал продаж, поддержки и управления подписками
- **Task Worker** — фоновая обработка (синхронизация, платежи, рассылки)
- **Helix Platform** — собственный desktop-first private transport stack

Платформа ориентирована на модель **"VPN Business in a Box"** — быстрый запуск VPN-бизнеса с премиальным UX, устойчивостью к блокировкам и глобальной локализацией.

---

## 2. Архитектура монорепозитория

```
VPNBussiness/
├── frontend/                  # Next.js 16 — Admin Dashboard + Landing
├── backend/                   # FastAPI — REST API (Clean Architecture + DDD)
│   └── src/
│       ├── presentation/      # HTTP-слой (38 роутеров, middleware)
│       ├── application/       # Use Cases, DTO, сервисный слой
│       ├── domain/            # Entities, Value Objects, Enums
│       └── infrastructure/    # SQLAlchemy, Redis, httpx, Remnawave SDK
├── apps/
│   └── desktop-client/        # Tauri + Rust + React (VPN desktop client)
│       ├── src/               # React UI (Vite)
│       └── src-tauri/src/     # Rust: engine, bgp, ipc, tray
│           ├── engine/        # VPN ProcessManager, parser, diagnostics
│           │   └── helix/     # Helix runtime (137KB sidecar, benchmark, config)
│           └── bgp/           # BGP Speaker (split tunneling)
├── cybervpn_mobile/           # Flutter + Dart (iOS/Android/TV)
│   └── lib/features/          # 22 feature-модуля (Clean Architecture)
├── services/
│   ├── telegram-bot/          # aiogram 3 — Telegram Bot
│   ├── task-worker/           # TaskIQ — фоновые задачи
│   ├── helix-adapter/         # Rust — control-plane для Helix (Axum)
│   └── helix-node/            # Rust — node daemon (health-gated apply)
├── infra/                     # Docker Compose (1070 строк, 25+ сервисов)
├── docs/                      # PRD, планы, security, API docs
├── packages/                  # Shared libraries (placeholder)
└── SDK/                       # SDK для интеграций
```

**Принцип:** npm workspaces монорепозиторий. Каждый компонент автономен, но разделяет общую инфраструктуру (PostgreSQL, Valkey/Redis, Prometheus).

---

## 3. Технологический стек (полный)

### 3.1 Frontend (Next.js 16)

| Технология | Версия | Назначение |
|---|---|---|
| Next.js | 16.1.5 | App Router, Server Components, RSC |
| React | 19.2.1 | UI-библиотека |
| React Compiler | 1.0.0 | Автоматическая мемоизация |
| TypeScript | 5.9.2 | Типобезопасность |
| Tailwind CSS | 4.1.18 | Утилитарный CSS |
| Three.js | 0.174.0 | 3D-графика (глобус серверов) |
| React Three Fiber | 9.1.0 | React-рендерер для Three.js |
| @react-three/drei | 10.7.7 | Хелперы R3F |
| Motion | 12.29.0 | Анимации и переходы |
| next-intl | 4.7.0 | i18n (38 локалей, RTL) |
| TanStack Query | 5.87.4 | Серверный стейт |
| TanStack Table | 8.21.3 | Таблицы |
| Zustand | 5.0.10 | Клиентский стейт |
| Lenis | 1.3.17 | Плавный скролл |

### 3.2 Backend (FastAPI)

| Технология | Версия | Назначение |
|---|---|---|
| Python | 3.13.13 | Рантайм baseline (Docker/CI/WSL) |
| FastAPI | ≥0.128.0 | Async Web Framework |
| Pydantic | ≥2.6.0 | Валидация + сериализация |
| SQLAlchemy | ≥2.0.23 | Async ORM |
| Alembic | ≥1.13.0 | Миграции БД |
| asyncpg | ≥0.29.0 | PostgreSQL драйвер |
| httpx | ≥0.25.0 | Async HTTP-клиент |
| PyJWT | ≥2.8.0 | JWT-аутентификация |
| argon2-cffi | ≥23.1.0 | Хеширование паролей (Argon2id) |
| pyotp | ≥2.9.0 | 2FA (TOTP) |
| slowapi | latest | Rate limiting |
| prometheus-client | latest | Метрики |

### 3.3 Desktop Client (Tauri + Rust)

| Технология | Назначение |
|---|---|
| Tauri 2 | Нативная оболочка (Windows/macOS/Linux) |
| Rust | Бэкенд-логика: VPN engine, BGP, IPC, diagnostics |
| React + Vite | Frontend UI десктопного клиента |
| sing-box / xray-core | VPN runtime (прокси-ядра) |
| reqwest | HTTP-клиент (Rust) |
| sysinfo | Мониторинг процессов |
| i18next | Локализация (38 языков) |

### 3.4 Mobile Client (Flutter)

| Технология | Версия | Назначение |
|---|---|---|
| Flutter SDK | ≥3.10.8 | Кроссплатформенный фреймворк |
| flutter_riverpod | 3.0.3 | State management |
| go_router | 17.0.0 | Навигация |
| dio | 5.9.0 | HTTP-клиент |
| flutter_v2ray_plus | 1.0.11 | VPN-ядро (V2Ray/Xray) |
| freezed | 3.0.6 | Иммутабельные модели |
| flutter_secure_storage | 9.2.4 | Keychain/Keystore |
| purchases_flutter | 9.10.8 | In-App Purchases (RevenueCat) |
| firebase_messaging | 15.2.4 | Push-уведомления |

### 3.5 Telegram Bot (aiogram 3)

| Технология | Версия | Назначение |
|---|---|---|
| aiogram | ≥3.24 | Telegram Bot Framework |
| httpx | ≥0.28.1 | HTTP-клиент |
| redis[hiredis] | ≥7.1 | FSM storage |
| structlog | ≥25.5 | JSON-логирование |
| fluent.runtime | ≥0.4 | i18n (Fluent) |
| prometheus-client | ≥0.24.1 | Метрики |
| qrcode[pil] | ≥8.0 | QR-коды для конфигов |

### 3.6 Helix Services (Rust)

| Сервис | Фреймворк | Назначение |
|---|---|---|
| helix-adapter | Axum + SQLx | Control-plane: manifests, rollout, signing |
| helix-node | Axum + Tokio | Node daemon: health-gated apply + rollback |

### 3.7 Инфраструктура

| Технология | Версия | Порт | Назначение |
|---|---|---|---|
| PostgreSQL | 17.7 | 6767 | Основная БД |
| Valkey | 8.1-alpine | 6379 | Кэш, FSM, очереди |
| Remnawave | 2.7.4 | 3005 | VPN-панель |
| Caddy | 2.9 | 80/443 | Reverse proxy + TLS |
| Prometheus | v3.2.1 | 9094 | Сбор метрик |
| Grafana | 11.5.2 | 3002 | Визуализация |
| Alertmanager | v0.28.1 | 9093 | Алертинг |
| Tempo | 2.7.2 | 3200 | Distributed tracing |
| Loki | 3.4.2 | 3100 | Агрегация логов |
| Promtail | 3.4.2 | — | Сбор логов |
| OTel Collector | 0.121.0 | 4317/4318 | OTLP gRPC/HTTP |

---

## 4. VPN-протоколы и транспорты

### 4.1 Поддерживаемые протоколы (через Xray-core)

| Протокол | Описание | Анти-DPI |
|---|---|---|
| **VLESS + Reality + Vision** | Основной стек. Reality заимствует TLS-сертификат легитимного сайта, Vision устраняет сигнатуру TLS-in-TLS | ★★★★★ |
| **VLESS + XHTTP** | HTTP/2-based транспорт для relay/chain конфигураций | ★★★★☆ |
| **Trojan** | Маскируется под обычный HTTPS-трафик | ★★★★☆ |
| **VMess** | Оригинальный протокол V2Ray с шифрованием | ★★★☆☆ |
| **Shadowsocks (2022)** | Современная AEAD-версия с blake3 | ★★★☆☆ |
| **Hysteria 2** | UDP-based (QUIC), port hopping, обфускация | ★★★★☆ |
| **WireGuard** | Классический VPN-протокол, kernel-level | ★★☆☆☆ |

### 4.2 Транспортные режимы

| Транспорт | Протоколы | Применение |
|---|---|---|
| TCP | VLESS, VMess, Trojan | Стандартный |
| WebSocket (WS) | VLESS, VMess | Обход CDN/прокси |
| gRPC | VLESS, VMess | Multiplexing |
| XHTTP | VLESS | Relay/chain |
| mKCP | VMess | UDP-based, low latency |
| QUIC | Hysteria 2 | UDP с port hopping |

### 4.3 Форматы конфигураций клиентов

| Формат | Клиенты | Enum в backend |
|---|---|---|
| Clash | Clash, ClashX, Clash Verge | `clash` |
| Hiddify | Hiddify | `hiddify` |
| Outline | Outline Client | `outline` |
| Sing-box | SFI, sing-box, наш Desktop Client | `sing_box` |
| V2Ray | v2rayN, v2rayNG, Nekobox | `v2ray` |

### 4.4 Xray-core в 2026 — ключевые нововведения

- **Finalmask** — продвинутая обфускация трафика (мимикрия под XICMP, XDNS и пр.)
- **TUN Inbound** — поддержка TUN-интерфейсов на всех платформах
- **Post-Quantum Cryptography** — начало интеграции ML-KEM768 в key exchange
- **Process-based routing** — маршрутизация по имени/пути процесса

---

## 5. Remnawave 2.7.x — ядро управления VPN

### 5.1 Архитектура Remnawave

```
┌───────────────────┐
│  Remnawave Panel   │  NestJS + PostgreSQL
│  (Control Plane)   │  Порт: 3000 (внутри Docker)
└────────┬──────────┘
         │ mTLS / xtls-sdk gRPC
         ▼
┌───────────────────┐  ┌───────────────────┐
│  Remnawave Node 1  │  │  Remnawave Node N  │
│  (xray-core)       │  │  (xray-core)       │
│  Порт: 443         │  │  Порт: 443         │
└───────────────────┘  └───────────────────┘
```

**Ключевой принцип:** Panel не содержит xray-core. Ноды — отдельные серверы с xray-core, подключённые к панели через gRPC (xtls-sdk).

### 5.2 Возможности Remnawave 2.7.0+

| Категория | Возможности |
|---|---|
| **Nodes** | Неограниченное кол-во нод, mTLS-подключение, health checks, system info (RAM, load avg), node plugins, executor |
| **Users** | CRUD, traffic limits, expiration, squads, config profiles, HWID device limits |
| **Subscriptions** | Кастомная страница подписки, multi-lang инструкции, branding |
| **Auth** | Passkeys, Generic OAuth2 (замена встроенного Telegram login) |
| **Monitoring** | Torrent blocker reports, session explorer, IP stats в активных сессиях, Prometheus metrics |
| **API** | Полноценный REST API (NestJS), TypeScript SDK, Python SDK (`remnawave-api`) |
| **Webhooks** | 25+ типов событий (user.created, node.offline, и т.д.) |

### 5.3 Breaking changes в 2.7.0

| Изменение | Действие |
|---|---|
| Удалён метод `2022-blake3-aes-128-gcm` | Удалить inbound'ы с этим методом до обновления |
| Telegram login → Generic OAuth2 | Отключить старый Telegram login, настроить OAuth2 |
| Prometheus label cardinality | `node_name`, `provider_name`, `tags` вынесены в info-метрики |
| Node API response | `cpuCount`/`cpuModel`/`totalRam` заменены на `versions`/`system` |
| NET_ADMIN capability | Все ноды требуют `cap_add: - NET_ADMIN` |
| Аллокатор памяти | Переход с jemalloc на mimalloc |

### 5.4 Наша интеграция с Remnawave

Backend общается с Remnawave через `infrastructure/remnawave/` (httpx SDK):

```python
# Управление пользователями
await remnawave.users.create_user(username, traffic_limit, expire_at)
await remnawave.users.get_all_users_v2()
await remnawave.users.disable_user(uuid)
await remnawave.users.get_subscription_link(uuid)

# Ноды
await remnawave.nodes.get_all()
# Статистика
await remnawave.system.get_stats()
await remnawave.system.get_bandwidth()
```

---

## 6. Helix — наш собственный transport stack

### 6.1 Зачем нужен Helix?

Helix — это **desktop-first private transport stack**, который расширяет платформу собственным протоколом без модификации Remnawave. Remnawave остаётся **authoritative** по пользователям, подпискам и инвентарю нод.

**Мотивация:**
- Полный контроль над транспортным протоколом (независимость от xray-core)
- Канареечные обновления (canary rollouts) с автоматическим откатом
- Подписанные манифесты для безопасной доставки конфигураций
- Бенчмарки и диагностика на уровне runtime

### 6.2 Компоненты Helix

```
┌──────────────────────────────────────────────────────────┐
│                    Desktop Client                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  engine/helix/                                      │  │
│  │  • sidecar.rs (137KB) — runtime orchestration       │  │
│  │  • config.rs (32KB)   — конфигурация Helix          │  │
│  │  • benchmark.rs (55KB)— perf lab                    │  │
│  │  • process.rs (9KB)   — process management          │  │
│  │  • health.rs          — health polling              │  │
│  │  • client.rs          — adapter HTTP client         │  │
│  └────────────────────────────┬───────────────────────┘  │
│                               │ HTTP                      │
└───────────────────────────────┼───────────────────────────┘
                                ▼
              ┌─────────────────────────────────┐
              │  helix-adapter (Rust/Axum)       │
              │  Порт: 8088                      │
              │                                  │
              │  • Node Registry (PostgreSQL)    │
              │  • Transport Profiles            │
              │  • Manifest Renderer + Signer    │
              │  • Rollout Policy + Canary       │
              │  • Assignment Store              │
              │  • Read-only Remnawave client    │
              └──────────┬──────────────────────┘
                         │ HTTP polling
              ┌──────────┴──────────────────────┐
              │  helix-node daemon (Rust/Axum)   │
              │  Порт: 8091                      │
              │                                  │
              │  • Fetch assignments             │
              │  • Health-gated apply            │
              │  • Rollback to last-known-good   │
              │  • Heartbeat reporting           │
              │  • /healthz, /readyz, /metrics   │
              └─────────────────────────────────┘
```

### 6.3 Жизненный цикл Helix Assignment

1. **helix-adapter** читает инвентарь нод из Remnawave (read-only)
2. Рендерит и подписывает **manifest** (Ed25519, `manifest_signing_key`)
3. Сохраняет assignments + rollout metadata в PostgreSQL (schema `helix`)
4. **helix-node** daemon polling: `fetch_assignment()` каждые N секунд
5. **sync_assignment()**: Health Gate → Apply → Report snapshot
6. При сбое: автоматический **rollback на last-known-good bundle**
7. **Heartbeat**: latency_ms + runtime state → helix-adapter

### 6.4 Desktop Helix Runtime

Файл `engine/helix/sidecar.rs` (137KB) — крупнейший модуль десктопного клиента:

- **Orchestration**: запуск/остановка Helix sidecar-процесса
- **Health polling**: каждые 750ms опрос `/healthz` (bytes_sent/received)
- **Degradation events**: `helix-runtime-degraded` → UI fallback
- **Benchmark**: встроенный perf lab для сравнения транспортов
- **Diagnostics**: структурированные события через `DiagnosticLevel`
- **Failover**: автоматический переход на stable cores (sing-box/xray)

---

## 7. Backend API (FastAPI + DDD)

### 7.1 Архитектура

```
presentation/ → HTTP-роуты (38 модулей), middleware, exception handlers
application/  → Use Cases, DTO, сервисный слой
domain/       → Entities, Value Objects, Enums (чистый Python, 0 зависимостей)
infrastructure/ → SQLAlchemy, Redis, httpx, Remnawave, OAuth, payments, monitoring
```

### 7.2 API-модули (38 роутеров)

**Auth (6):** auth, registration, mobile_auth, oauth, two_factor, security  
**Core (6):** users, profile, notifications, servers, subscriptions, plans  
**Helix (1):** helix (authenticated facade для desktop + admin)  
**Payments (2):** payments, billing  
**Codes/Wallet (5):** invite_codes, promo_codes, referral, partners, wallet  
**VPN Management (7):** hosts, config_profiles, inbounds, node_plugins, squads, snippets, xray  
**Monitoring (2):** status, monitoring  
**Integrations (4):** webhooks, telegram, keygen, fcm  
**Admin (3):** admin, invites (admin), settings  
**WebSocket (3):** ws/monitoring, ws/notifications, ws/tickets  
**Other (2):** usage, trial, snippets  

### 7.3 OAuth 2.0 PKCE

Поддерживаемые провайдеры: **Google, GitHub, Discord v10, X/Twitter**, Telegram Magic Links  
Все провайдеры используют **PKCE** (Proof Key for Code Exchange) — стандарт безопасности 2026.

---

## 8. Frontend Dashboard (Next.js 16)

### 8.1 Feature-Sliced Design + Atomic Design

```
app/[locale]/              # App Router с i18n
  (dashboard)/             # Серверы, пользователи, аналитика
3d/scenes/                 # GlobalNetwork.tsx (интерактивный 3D-глобус)
widgets/                   # cyber-sidebar, terminal-header, servers-data-grid
shared/ui/atoms/           # CypherText, ServerStatusDot, Scanlines
shared/ui/molecules/       # ServerCard
shared/ui/organisms/       # Tables, forms
entities/                  # Server, User (TypeScript types)
```

### 8.2 Cyberpunk Design System

- **Цвета:** Matrix Green (#00ff88), Neon Cyan (#00ffff), Neon Pink (#ff00ff)
- **Шрифты:** Orbitron (display), JetBrains Mono (code)
- **Эффекты:** Scanlines overlay, CypherText scramble, 3D card transforms, glassmorphism
- **3D:** InstancedMesh для оптимизации, persistent WebGL context

---

## 9. Desktop Client (Tauri + Rust)

### 9.1 VPN Engine (Rust)

**ProcessManager** — ядро управления VPN-процессом:
- Запуск sing-box / xray-core / helix как child process
- Парсинг stdout/stderr (regex для трафика, routing failures, tracker blocking)
- UAC elevation (Windows) / pkexec (Linux) для TUN-режима
- Watchdog: детект неожиданного завершения → `vpn-process-died`
- System proxy management и kill switch (SentinelGuard)

### 9.2 BGP Speaker (Split Tunneling)

Встроенный **BGP Speaker на Rust** для умной маршрутизации:
- Динамическое получение списков заблокированных IP
- Маршрутизация только целевого трафика через VPN
- Модификация системных routing tables (требует NET_ADMIN)

### 9.3 Privacy Protection

Встроенный блокировщик трекеров:
- Парсинг логов runtime на правила `adblock-standard` / `block`
- Счётчик заблокированных угроз (`threats_blocked`)
- Эмиты в UI: `tracker-blocked`, `routing-suggestion`

### 9.4 Diagnostics

Полная диагностическая подсистема (`diagnostics.rs`, 34KB):
- Уровни: Info, Warn, Error
- Структурированные JSON-события
- Core runtime logs (stdout/stderr)
- Helix health state tracking

---

## 10. Mobile Client (Flutter)

### 22 Feature-модуля (Clean Architecture):

auth, config_import, diagnostics, navigation, notifications, onboarding, partner, profile, quick_actions, quick_setup, referral, review, routing, security, servers, settings, splash, subscription, vpn, vpn_profiles, wallet, widgets

**VPN-ядро:** flutter_v2ray_plus (V2Ray/Xray)  
**Платформы:** Android, iOS, Linux, macOS, Windows, Android TV/Fire TV

---

## 11. Telegram Bot (aiogram 3)

**Пользовательские команды:** /start, /menu, /config, /support, /trial, /referral  
**Админ-функции:** статистика, broadcast, управление пользователями/планами, промокоды, логи  
**Особенности:** FSM (Redis-backed), QR-коды, Fluent i18n, Prometheus metrics, retry (tenacity)

---

## 12. Task Worker (TaskIQ)

**Периодические задачи:**

| Задача | Интервал |
|---|---|
| Синхронизация нод | 5 минут |
| Health check серверов | 2 минуты |
| Геолокация серверов | 6 часов |
| Bandwidth мониторинг | 5 минут |
| Обновление трафика | 10 минут |
| Конфигурации серверов | 30 минут |
| Сброс трафика | 1-е число месяца |

---

## 13. Инфраструктура и Docker

### Docker Compose: 25+ сервисов, 4 сети, 13 volumes

**Сети:**
- `cybervpn-frontend` — Caddy ↔ Remnawave
- `cybervpn-backend` — Backend ↔ Worker ↔ Bot ↔ Helix
- `cybervpn-data` — PostgreSQL ↔ Redis
- `cybervpn-monitoring` — Prometheus ↔ Grafana ↔ Loki ↔ Tempo

**Профили:**

| Профиль | Сервисы |
|---|---|
| *(базовый)* | remnawave, postgres, valkey, db-backup |
| `worker` | cybervpn-worker, cybervpn-scheduler |
| `bot` | cybervpn-telegram-bot |
| `helix` | helix-adapter |
| `helix-lab` | helix-adapter, 2× helix-node, bench-target, stable-http-proxy |
| `monitoring` | prometheus, grafana, alertmanager, tempo, loki, promtail, otel-collector, node/redis/pg exporters, cadvisor, auth-metrics-seed |
| `proxy` | caddy |
| `subscription` | remnawave-subscription-page |
| `email-test` | 3× mailpit (SMTP rotation testing) |

---

## 14. Observability

### Полный стек:
- **Metrics:** Prometheus → Grafana (scrape: remnawave, worker, bot, node/redis/pg exporters, cadvisor)
- **Traces:** OpenTelemetry Collector → Tempo → Grafana
- **Logs:** Promtail → Loki → Grafana
- **Alerts:** Prometheus Rules → Alertmanager (TaskWorkerDown, HighTaskErrorRate, RedisConnectionFailing и др.)

### Grafana Dashboards:
- Auth dashboard (регистрации, OAuth, email verification, ошибки)
- Worker metrics
- Infrastructure (node/redis/pg exporters)

---

## 15. Безопасность и аутентификация

| Механизм | Реализация |
|---|---|
| Пароли | Argon2id (OWASP 2025) |
| JWT | HS256, Access: 15 мин, Refresh: 7 дней, blacklist в Redis |
| 2FA | TOTP (pyotp), QR для Google Authenticator |
| OAuth | PKCE: Google, GitHub, Discord v10, X/Twitter |
| Anti-bruteforce | 423 Locked status |
| GDPR | Terms of Service consent, marketing consent tracking |
| Rate limiting | slowapi |
| Webhook security | HMAC-SHA256, constant-time compare |
| Helix manifests | Ed25519 signing |
| CORS | Explicit allowed origins |

---

## 16. Бизнес-модель и монетизация

**Тарифы:** Basic → Pro → Ultra → Cyber  
**Периоды:** 1 / 3 / 6 / 12 месяцев  
**Trial:** 2 дня, 2 ГБ  
**Реферальная система:** +3 дня бонус, до 100 рефералов  

**Платёжные шлюзы:**
- Telegram Stars (нативные)
- CryptoBot (USDT, BTC, TON, mainnet + testnet)
- YooKassa (Visa, MasterCard, ЮMoney, SBP)
- Stripe (планируется)

**Wallet-система:** пополнение, вывод, комиссии, реферальные начисления, партнёрские заработки

---

## 17. Доменные сущности

**14 entities:** User, Server, SubscriptionPlan, Payment, Referral, Partner, PromoCode, InviteCode, Wallet, Withdrawal, FCMToken, SystemConfig, Subscription  
**12 enums:** UserStatus, ServerStatus, PaymentStatus, PaymentProvider, AdminRole, PlanTier, TemplateType, InviteSource, DiscountType, WalletTxType, WalletTxReason, WithdrawalStatus, WithdrawalMethod, ReferralDurationMode

---

## 18. Internationalization (38 локалей)

**Локали:** en-EN, ru-RU, zh-CN, hi-IN, id-ID, vi-VN, th-TH, ja-JP, ko-KR, ar-SA, fa-IR, tr-TR, ur-PK, bn-BD, ms-MY, es-ES, kk-KZ, be-BY, my-MM, uz-UZ, ha-NG, yo-NG, ku-IQ, am-ET, fr-FR, tk-TM, he-IL, de-DE, pt-PT, it-IT, nl-NL, pl-PL, fil-PH, uk-UA, cs-CZ, ro-RO, hu-HU, sv-SE

**RTL:** ar-SA, he-IL, fa-IR  
**Frontend:** next-intl · **Desktop:** i18next · **Mobile:** Flutter l10n · **Bot:** Fluent i18n

---

## 19. Стратегия разработки собственного протокола

### 19.1 Текущее состояние Helix

Helix уже реализован как **transport delivery и runtime management layer**. Следующий шаг — замена xray-core/sing-box собственным data-plane runtime.

### 19.2 Точки интеграции (куда подключать свой протокол)

| Слой | Файл/Модуль | Что менять |
|---|---|---|
| **Desktop Runtime** | `engine/helix/sidecar.rs` | Замена child process на собственный transport binary |
| **Desktop Config** | `engine/helix/config.rs` | Генерация конфига для нового протокола |
| **Adapter Manifests** | `helix-adapter/src/manifests/` | Формат manifest'ов под новый протокол |
| **Adapter Transport** | `helix-adapter/src/transport_profiles/` | Профили для нового транспорта |
| **Node Daemon** | `helix-node/src/runtime/` | Runtime coordinator для нового binary |
| **Backend Facade** | `backend/api/v1/helix/` | API для desktop + admin flows |
| **Frontend UI** | `frontend/entities/server/model/types.ts` | Добавить `helix` в `VpnProtocol` |

### 19.3 Рекомендуемый план внедрения

**Фаза 1 — Протокол (Rust library):**
- Разработать core transport library на Rust
- Multiplexed sessions, AEAD encryption, traffic padding
- Anti-fingerprint: рандомизация TLS Client Hello, domain fronting

**Фаза 2 — Sidecar Binary:**
- Собрать standalone binary из Rust library
- Health endpoint `/healthz` (bytes_sent, bytes_received)
- Конфигурация через JSON/YAML

**Фаза 3 — Desktop Integration:**
- Интеграция в `engine/helix/sidecar.rs` (уже готов orchestration)
- Benchmark: сравнение с sing-box/xray через встроенный perf lab
- Canary rollout через helix-adapter

**Фаза 4 — Server-side Node:**
- Обновить `helix-node` daemon для запуска нового runtime
- Health-gated apply с rollback на last-known-good

**Фаза 5 — Mobile + Telegram:**
- FFI-биндинги Rust → Dart (Flutter)
- Обновить конфиг-генератор в боте

### 19.4 Существующая инфраструктура для безболезненного внедрения

| Готовый механизм | Описание |
|---|---|
| Canary rollout | helix-adapter уже поддерживает channel-based rollouts |
| Manifest signing | Ed25519 подписи для безопасной доставки конфигов |
| Health gates | helix-node применяет конфиг только после прохождения health check |
| Auto-rollback | При сбое — откат на last-known-good bundle |
| Benchmark lab | Встроенный в Desktop Client performance comparison |
| Diagnostics | Структурированные события + core runtime logs |
| Fallback | Автоматический переход на stable cores (sing-box/xray) |

---

## 20. Roadmap

### Ближайшие цели
- [ ] Invite System (система приглашений) — PRD готов
- [ ] Loyalty Program (4 уровня: Bronze → Platinum) — PRD готов
- [ ] Helix data-plane runtime (собственный протокол)
- [ ] Android TV / Fire TV (фазы 1-9 запланированы)
- [ ] Stripe integration
- [ ] Kubernetes для горизонтального масштабирования
- [ ] Terraform / Ansible (IaC)

---

*Документ подготовлен на основе полного анализа кодовой базы VPNBussiness. Актуален на 8 апреля 2026.*
