# CyberVPN - описание проекта

Дата обновления: 2026-05-28

## Кратко

**CyberVPN** - это монорепозиторий для запуска и управления VPN-бизнесом. Проект объединяет клиентские приложения, административные панели, backend API, Telegram-бот, фоновые сервисы, VPN/transport-интеграции, инфраструктурные шаблоны и документацию для staging/production rollout.

Главная идея проекта - дать пользователю понятный способ купить, активировать и использовать VPN-подписку, а команде - управлять пользователями, подписками, платежами, серверами, партнерами, промокодами, рефералами, мониторингом и релизами из единой платформы.

## Целевая роль проекта

CyberVPN закрывает несколько бизнес-задач:

- продажа VPN-подписок через web, Telegram и мобильные сценарии;
- автоматическая выдача VPN-доступа и конфигураций пользователям;
- управление подписками, пробными периодами, продлениями и ограничениями;
- поддержка реферальных, партнерских и промо-механик роста;
- контроль VPN-инфраструктуры, серверов, нод и транспортных профилей;
- сбор операционных метрик, событий, отчетов и evidence-документации;
- подготовка платформы к staging, production, canary, backup/restore и DR-процессам.

## Основные пользовательские поверхности

### Customer Frontend

Основное пользовательское web-приложение на Next.js. В нем находятся публичные страницы, личный кабинет, подписки, billing-сценарии, referral cabinet, серверный доступ, настройки, страницы загрузки клиента и Telegram Mini App сценарии.

Фронтенд использует Feature-Sliced Design, Next.js App Router, TypeScript, React 19, Tailwind CSS 4, next-intl и 3D/анимационные элементы. В `frontend/src/i18n/config.ts` настроено 39 локалей, включая RTL-языки.

### Admin Panel

Отдельное Next.js-приложение в `admin/` для административных операций. Его роль - управлять внутренними процессами: пользователями, подписками, поддержкой, операционными данными, отчетностью и контрольными сценариями.

Локальный запуск: `npm run dev:admin`.

### Partner Portal

Отдельное Next.js-приложение в `partner/` для партнерских сценариев: workspace партнеров, отчетность, аналитика, referral/growth codes, storefront/settlement-процессы и PostHog-backed product intelligence.

Локальный запуск: `npm run dev:partner`.

### Telegram Bot

Сервис в `services/telegram-bot/` на aiogram 3. Он отвечает за пользовательский Telegram-интерфейс: регистрацию, покупку подписки, оплату, получение конфигурации, QR-коды, referral flow, trial flow, админ-команды, уведомления и метрики.

### Mobile App

Flutter-приложение в `cybervpn_mobile/`. Это VPN-клиент с Riverpod, Clean Architecture, secure storage, локальной БД, Firebase/Sentry-интеграциями, in-app purchase возможностями и `flutter_v2ray_plus` как VPN-core зависимостью.

### Desktop Client

Tauri + React + TypeScript приложение в `apps/desktop-client/`. Оно связано с desktop-first transport stack, diagnostic/perf lab сценариями, Sentry-контрактом и Helix runtime.

## Backend и доменная логика

Backend находится в `backend/` и построен на FastAPI с Clean Architecture и DDD-подходом.

Основные слои:

- `presentation/` - HTTP API, роуты, middleware, схемы и зависимости FastAPI;
- `application/` - use cases, DTO, сервисная оркестрация и прикладные интерфейсы;
- `domain/` - доменные сущности, value objects, события, исключения и интерфейсы репозиториев;
- `infrastructure/` - SQLAlchemy, Redis/Valkey, Remnawave, Helix, платежные интеграции, messaging, мониторинг и внешние клиенты.

Backend работает с PostgreSQL, Redis/Valkey, NATS/event backbone, платежными шлюзами, Remnawave API, observability-инструментами и внутренними сервисами платформы.

## Фоновые сервисы

### Task Worker

`services/task-worker/` - production-grade TaskIQ worker для фоновых задач:

- уведомления и broadcast;
- мониторинг серверов и очередей;
- обработка подписок, истечений и автопродлений;
- платежные проверки и retries;
- analytics aggregation;
- cleanup старых данных;
- sync с внешними системами;
- отчеты и bulk-операции.

### Node Fleet Controller

`services/node-fleet-controller/` отвечает за fleet-control направление: управление состоянием нод, инфраструктурные проверки и подготовку платформы к более зрелой модели управления VPN/edge-ресурсами.

### Helix Adapter и Helix Node

`services/helix-adapter/` и `services/helix-node/` добавляют private transport stack вокруг основной модели, где Remnawave остается authoritative source для пользователей, подписок и VPN-инвентаря.

Helix отвечает за manifests, rollout policy, canary evidence, health-gated apply, rollback и lab/perf сценарии.

## VPN и transport слой

Проект опирается на Remnawave как основной VPN backend для управления нодами, пользователями, конфигурациями и VPN-доступом. В инфраструктуре также присутствуют VLESS/Xray-oriented сценарии, edge rollout и Helix/Verta/Beep protocol workspaces для развития transport-направления.

Связанные пакеты:

- `packages/flutter_v2ray_plus/` - локальный Flutter VPN plugin/package;
- `packages/helix-runtime/` - runtime transport logic;
- `packages/helix-contract/` - контрактные схемы Helix;
- `packages/verta-protocol/` - protocol specs, Rust workspace, fuzzing, release docs;
- `packages/beep-protocol/` - дополнительные transport/protocol материалы.

## Инфраструктура

`infra/` содержит локальный Docker Compose stack и staging/production IaC scaffolding.

Локальный stack включает:

- PostgreSQL 17;
- Redis/Valkey;
- Remnawave;
- optional monitoring через Prometheus/Grafana;
- optional bot/worker/proxy/subscription profiles;
- Helix lab profiles.

Также в репозитории есть:

- Terraform/OpenTofu layout в `infra/terraform/`;
- Ansible playbooks в `infra/ansible/`;
- OpenBao policy assets;
- NATS/PostHog/control-plane bootstrap helpers;
- GitOps scaffold в `platform-gitops/`;
- runbooks, evidence packs и deployment-документация в `docs/`.

## Технологический стек

### Web

- Next.js 16.2.x;
- React 19.2.x;
- TypeScript 5.9.x;
- Tailwind CSS 4.2.x;
- next-intl;
- TanStack Query и TanStack Table;
- Zustand;
- Three.js, React Three Fiber, Drei;
- Motion;
- Sentry;
- Vitest, Testing Library, MSW, ESLint.

Важное правило для Next.js 16.1+ в этом проекте: middleware-конфигурацию нужно размещать в `src/proxy.ts`, а не в `src/middleware.ts`.

### Backend

- Python 3.13;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2;
- Alembic;
- asyncpg;
- Redis client;
- NATS;
- PyJWT, Argon2, TOTP/2FA;
- Prometheus, Sentry, OpenTelemetry;
- Ruff, pytest, pytest-asyncio.

### Mobile

- Flutter;
- Dart 3.10.x;
- Riverpod 3;
- GoRouter;
- Dio;
- Drift/SQLite;
- secure storage;
- Firebase;
- Sentry;
- in-app purchases;
- `flutter_v2ray_plus`.

### Desktop и protocol work

- Tauri;
- React + TypeScript;
- Rust workspaces для protocol/runtime направлений;
- perf/diagnostics scripts для Helix lab.

## Архитектурная схема

```text
Users
  |
  |-- Web / Mini App / Mobile / Desktop / Telegram
  |
  v
Frontend apps and bot
  |
  v
Backend API
  |
  |-- PostgreSQL
  |-- Redis / Valkey
  |-- NATS / event backbone
  |-- Task Worker
  |-- Payment providers
  |-- Telegram integration
  |
  v
Remnawave API
  |
  v
VPN nodes / transport layer
  |
  |-- Helix adapter and nodes
  |-- Verta / Beep protocol workspaces
```

## Структура репозитория

```text
VPNBussiness/
├── frontend/              # Customer frontend, Telegram Mini App, cabinet, public pages
├── admin/                 # Standalone admin web app
├── partner/               # Standalone partner portal
├── backend/               # FastAPI backend API
├── services/              # Telegram bot, task worker, node fleet, Helix services
├── cybervpn_mobile/       # Flutter mobile VPN client
├── apps/                  # Desktop client, browser extension, Android TV app
├── packages/              # Shared packages, VPN/protocol/runtime packages
├── infra/                 # Docker Compose, OpenTofu/Terraform, Ansible, bootstrap scripts
├── platform-gitops/       # GitOps platform scaffold
├── SDK/                   # Vendored/reference SDK materials
├── docs/                  # Plans, runbooks, audits, evidence, launch docs
└── scripts/               # Local automation and conformance helpers
```

## Команды разработки

Из корня репозитория:

```bash
npm install
npm run dev
npm run build
npm run lint
```

Отдельные web-приложения:

```bash
npm run dev:admin
npm run dev:partner
```

Инфраструктура:

```bash
cd infra
docker compose up -d
docker compose --profile monitoring up -d
docker compose --profile bot up -d
```

Mobile:

```bash
cd cybervpn_mobile
flutter pub get
flutter run
```

## Сильные стороны проекта

- Платформа строится как полноценный VPN-бизнес, а не как один frontend.
- Есть разделение customer/admin/partner поверхностей.
- Backend следует Clean Architecture и DDD-границам.
- Присутствуют Telegram, mobile и desktop каналы.
- В репозитории много production-oriented материалов: runbooks, evidence, CI/CD, backup/restore, security docs, observability, staging/prod rollout.
- VPN control-plane не завязан на один UI: есть worker, bot, API, infrastructure и transport workspaces.
- Интернационализация заложена глубоко: 39 web-локалей и RTL-направления.

## Текущий фокус проекта

По структуре репозитория и документации видно, что проект находится в стадии активной подготовки и стабилизации платформы: customer flows, Mini App, партнерские сценарии, подписки, referral/growth mechanics, инфраструктурные rollout-процессы, observability, security hardening и VPN/transport evolution развиваются параллельно.

На практике это уже не просто MVP VPN-сайта, а многоуровневая платформа с заделом на коммерческий запуск, партнерскую сеть, управляемую инфраструктуру и расширение клиентских приложений.
