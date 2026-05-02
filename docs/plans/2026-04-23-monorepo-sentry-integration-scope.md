# CyberVPN Monorepo: описание проекта и область охвата интеграции с Sentry

Дата: 2026-04-23

## Цель документа

Этот документ фиксирует:

- что из себя представляет текущий монорепозиторий CyberVPN;
- какие runtime-поверхности в нём реально существуют;
- где Sentry уже внедрён, а где покрытия нет;
- что именно должно входить в полную интеграцию Sentry для всего монорепозитория;
- какие части репозитория не требуют отдельного Sentry-проекта и должны наблюдаться косвенно через consuming runtime.

Документ нужен как базовое описание проекта перед практической интеграцией, настройкой CI/CD, заведением Sentry-проектов, release-потоков, alerting и privacy-правил.

## Краткое описание проекта

CyberVPN — это полиглотный монорепозиторий платформы для VPN-бизнеса. Репозиторий не ограничивается одним Next.js-приложением: в нём одновременно живут пользовательские web-поверхности, backend API, фоновые воркеры, Telegram-бот, mobile-клиент, desktop-клиент, Android TV-приложение, control-plane сервисы и shared packages.

Текущий стек монорепозитория:

- Web: Next.js 16.2.x, React 19.2.x, TypeScript, Tailwind CSS.
- Backend/services: Python 3.13, FastAPI, TaskIQ, aiogram, structlog.
- Mobile: Flutter, Riverpod, Firebase, `sentry_flutter`.
- Desktop: React + Vite + Tauri 2, Rust.
- Control plane: Rust/Axum и Python/FastAPI сервисы.
- Infra observability: Prometheus, Grafana, Loki, Tempo, Alloy/OpenTelemetry.
- Product analytics: PostHog.

Важно: это не просто npm-workspaces monorepo. Корневой `package.json` покрывает web workspace-часть, но в репозитории есть и независимые Python, Rust, Flutter и Android Gradle-проекты. Для Sentry это означает, что интеграция должна проектироваться как multi-runtime, а не как настройка “одного фронтенда”.

## Граница ответственности Sentry в этом репозитории

Sentry в CyberVPN не должен подменять текущий observability stack.

Что уже есть и должно остаться:

- Prometheus/Grafana: системные и бизнес-метрики.
- Loki: централизованные логи.
- Tempo/OpenTelemetry/Alloy: distributed tracing и transport telemetry.
- PostHog: продуктовая аналитика, события продукта, feature flags и growth/intelligence сценарии.

Что должен закрывать Sentry:

- application error monitoring;
- crash monitoring;
- release health;
- app-level performance/tracing на пользовательских и сервисных runtime;
- session replay только там, где это оправдано и безопасно;
- source maps / debug symbols / debug files;
- минимальный и безопасный user context;
- привязка ошибок к release, environment и deploy-потоку.

Что Sentry не должен становиться источником истины для всей телеметрии:

- полные инфраструктурные логи;
- полные time-series метрики;
- низкоуровневые сетевые и transport traces;
- raw product analytics.

## Границы охвата

### В прямом охвате Sentry

Это deployable runtime-поверхности, для которых нужен отдельный Sentry coverage plan:

- `frontend/`
- `admin/`
- `partner/`
- `backend/`
- `services/task-worker/`
- `services/telegram-bot/`
- `services/node-fleet-controller/`
- `services/helix-adapter/`
- `services/helix-node/`
- `cybervpn_mobile/`
- `apps/desktop-client/`
- `apps/android-tv/`

### В косвенном охвате

Это части репозитория, которые не должны получать отдельный Sentry runtime-проект, но их ошибки будут видны через consuming applications/services:

- `packages/*`
- `SDK/`
- shared frontend/domain libraries внутри отдельных приложений

### Вне прямого охвата как самостоятельные Sentry-проекты

- `infra/`
- `platform-gitops/`
- `docs/`
- placeholder-части без готового runtime
- `apps/browser-extension/` в текущем состоянии, потому что это пока заготовка с `package.json`, а не готовое исполняемое приложение

## Карта runtime-поверхностей монорепозитория

| Поверхность | Технология | Роль в продукте | Нужен отдельный Sentry проект |
| --- | --- | --- | --- |
| `frontend` | Next.js 16 / React 19 | клиентский web surface, dashboard, Telegram Mini App/marketing/customer flows | да |
| `admin` | Next.js 16 / React 19 | административный портал | да |
| `partner` | Next.js 16 / React 19 | partner portal / product intelligence / workspace flows | да |
| `backend` | FastAPI | основной API, auth, payments, webhooks, realtime, domain logic | да |
| `services/task-worker` | Python / TaskIQ | фоновые задачи, отчёты, sync, monitoring, payments, notifications | да |
| `services/telegram-bot` | aiogram | bot-интерфейс для подписок, оплат, конфигов, referral и admin flows | да |
| `services/node-fleet-controller` | FastAPI | будущий control-plane сервис внешнего fleet lifecycle | да |
| `services/helix-adapter` | Rust / Axum | control-plane adapter, manifests, signed registry state | да |
| `services/helix-node` | Rust / Axum | node daemon, apply/rollback/health lifecycle | да |
| `cybervpn_mobile` | Flutter | мобильное приложение | да |
| `apps/desktop-client` | React/Vite + Tauri/Rust | desktop-клиент | да, лучше разбить на renderer + native |
| `apps/android-tv` | Android/Kotlin/Compose | Android TV клиент | да |
| `apps/browser-extension` | placeholder | пока нет полноценного runtime | позже, когда появится реальный код |
| `packages/*` | shared libs | shared protocol/runtime/packages | нет, косвенно |
| `infra`, `platform-gitops`, `docs` | infra/docs | не runtime-приложения | нет |

## Текущее состояние Sentry по репозиторию

### 1. Web surfaces: `frontend`, `admin`, `partner`

Текущий статус:

- Sentry уже подключён через `@sentry/nextjs`.
- В каждом приложении есть `withSentryConfig(...)` в `next.config.ts`.
- В каждом приложении есть `src/instrumentation.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`, `src/instrumentation-client.ts`.
- Есть `app/global-error.tsx` и UI error boundaries с `captureException`.
- На клиенте включены browser tracing и replay.
- Есть Sentry breadcrumbs и `Sentry.metrics.distribution(...)` для web-vitals/runtime telemetry.

Подтверждённые различия:

- `admin` и `partner` уже имеют дополнительный client runtime observability слой с sanitization и глобальным перехватом ошибок.
- `partner` дополнительно пишет breadcrumbs/metrics в продуктовой аналитике через `product-events`.
- `frontend` покрыт Sentry и web-vitals, но не имеет такого же богатого custom runtime-layer, как `admin` и `partner`.

Текущие gaps:

- `environment` на web сейчас привязан к `process.env.NODE_ENV`, что не даёт корректно различать `staging` и `production` в production-build режиме.
- staging workflow сейчас передаёт только `NEXT_PUBLIC_SENTRY_DSN`, но не передаёт server-side `SENTRY_DSN`; значит browser-side события могут уходить, а server/edge coverage может быть неполным.
- release naming и deploy markers не стандартизированы.
- pipeline для source maps подготовлен частично, но не описан единообразно на уровне всех web builds.
- если будет включаться tunneling или proxy-level исключения, для этого репозитория нужно использовать `src/proxy.ts`, а не `src/middleware.ts`.

### 2. `backend`

Текущий статус:

- `sentry-sdk[fastapi]` уже в зависимостях.
- Инициализация Sentry есть в `backend/src/main.py`.
- Подключены FastAPI/Starlette integrations.
- Есть явный `capture_exception(...)` в обработчиках исключений.
- Есть интеграционные тесты observability, которые уже проверяют наличие и работу Sentry.

Текущие gaps:

- release metadata не стандартизирована.
- `.env.example` не фиксирует `SENTRY_DSN`, хотя код его поддерживает.
- нет зафиксированной политики deploy markers / release finalization в CI.
- нет формализованной privacy-матрицы для request context на уровне документа интеграции.

### 3. `services/task-worker`

Текущий статус:

- `sentry-sdk` уже в зависимостях.
- Инициализация Sentry есть в startup path воркера.
- Уже есть environment-based sampling.

Текущие gaps:

- `.env.example` не содержит `SENTRY_DSN`, хотя код умеет его читать.
- нет зафиксированной схемы release naming.
- нет согласованного набора tags/context для task names, queue, retry, scheduler, tenant/domain context.

### 4. `services/telegram-bot`

Текущий статус:

- Sentry не подключён.
- Сейчас наблюдаемость строится на Prometheus + structlog.

Вывод:

- bot — production surface и должен входить в полное покрытие Sentry.
- интеграция здесь обязательна, а не опциональна.

### 5. `services/node-fleet-controller`

Текущий статус:

- Sentry не подключён.
- сервис уже является отдельным FastAPI runtime для control-plane foundation.

Вывод:

- как только сервис участвует в request lifecycle, workflow planning, NATS publication, OpenTofu/OpenBao orchestration и durable audit store, он должен быть покрыт Sentry отдельно.

### 6. `services/helix-adapter`

Текущий статус:

- Rust/Axum сервис без Sentry.
- Есть Prometheus и tracing, но нет crash/error/release health покрытия в Sentry.

Вывод:

- это отдельная control-plane runtime-поверхность и должна быть включена в wave после базовых Python/web/mobile частей.

### 7. `services/helix-node`

Текущий статус:

- Rust node daemon без Sentry.
- Есть health/rollback/runtime logic, но нет отдельного error/crash monitoring в Sentry.

Вывод:

- для Helix node нужна отдельная стратегия, потому что это long-running native runtime с собственным жизненным циклом.

### 8. `cybervpn_mobile`

Текущий статус:

- `sentry_flutter` уже подключён.
- Инициализация есть в `lib/main.dart`.
- Есть sanitization hooks `beforeBreadcrumb` и `beforeSend`.
- `sendDefaultPii = false`.
- Есть синхронизация user context только по `user.id`.
- Есть доменные capture points для network/security/attestation/pinning/error-boundaries.
- В CI уже есть upload Dart debug symbols в `.github/workflows/ci.yml`.

Текущие gaps:

- tag-based release workflow `mobile-release.yml` передаёт `SENTRY_DSN`, но не показывает такой же явный шаг загрузки debug symbols, как общий `ci.yml`.
- release naming и deploy markers должны быть выровнены.
- Android/iOS release pipeline должен одинаково гарантировать наличие debug files в Sentry.

### 9. `apps/desktop-client`

Текущий статус:

- desktop app состоит из двух технически разных runtime-частей: React/Vite renderer и Tauri/Rust native layer.
- Sentry не подключён ни в renderer, ни в native Rust layer.
- `desktop-release.yml` собирает и публикует релиз, но не занимается ни source maps, ни native debug symbols.

Вывод:

- desktop нельзя считать одним “простым web app”.
- интеграция должна проектироваться минимум как два потока: renderer telemetry и native/crash telemetry.

### 10. `apps/android-tv`

Текущий статус:

- это реальное Android/Kotlin/Compose приложение с отдельным release workflow.
- Sentry не подключён.
- release workflow собирает APK/AAB, но не занимается Sentry mapping/debug symbols.

Вывод:

- Android TV должен входить в прямой охват полной Sentry-интеграции.

### 11. `apps/browser-extension`

Текущий статус:

- сейчас это placeholder.

Вывод:

- отдельный Sentry project сейчас создавать рано.
- в документе он должен быть отмечен как future surface, а не как текущий blocking runtime.

## Что полная интеграция с Sentry должна охватить

### Обязательные блоки для всех runtime

- корректный `dsn`;
- корректный `environment`;
- корректный `release`;
- минимально необходимый `user context`;
- теги поверхности и доменного контекста;
- проверяемый smoke-test на отправку события;
- CI/CD шаги для release artifacts;
- privacy/scrubbing policy;
- alerting/ownership policy;
- документацию по тому, что именно считается incident-grade сигналом.

### Что должно покрываться по типам сигналов

| Тип покрытия | Что должно быть в охвате |
| --- | --- |
| Errors | unhandled exceptions, handled domain exceptions, render/runtime errors, worker task failures, bot handler failures, native crashes |
| Tracing / performance | web route transitions, server requests, background tasks, critical external calls, mobile network spans, desktop critical flows |
| Release health | все user-facing приложения и как минимум ключевые backend/services |
| Artifacts | source maps для JS/TS, Dart debug files, Android mappings/debug files, desktop native symbols, при необходимости native symbols для Rust surfaces |
| Context | environment, release, runtime surface, deployment ring, route/task/handler metadata, safe user identity |
| Privacy | scrub rules, replay privacy, payload redaction, token/header/body filtering |

### Обязательный охват по поверхностям

| Поверхность | Что именно должно быть покрыто в Sentry |
| --- | --- |
| `frontend` | browser errors, server/edge errors, App Router errors, route transitions, web-vitals, mini app/runtime events, source maps, release/environment |
| `admin` | всё из `frontend` + runtime observability events, form/guard/admin workflow errors |
| `partner` | всё из `admin` + partner portal flows, workspace/product intelligence bridges, server-side product event failures |
| `backend` | FastAPI request errors, domain exceptions, webhook failures, auth/payment/security critical paths, traces, release/deploy markers |
| `task-worker` | task failures, retries, scheduler runs, queue/broker context, external integration failures, release/deploy markers |
| `telegram-bot` | handler failures, payment/config/referral flows, webhook/polling runtime errors, backend API failures, release/environment |
| `node-fleet-controller` | API errors, workflow/reconciler failures, NATS publish failures, OpenTofu/OpenBao integration failures, durable request lifecycle |
| `helix-adapter` | Axum request failures, manifest generation/signing failures, Remnawave read failures, persistence/signature errors |
| `helix-node` | control-plane fetch failures, apply/rollback errors, runtime health failures, panic/crash coverage |
| `cybervpn_mobile` | app crashes, render/runtime exceptions, network spans, attestation/pinning issues, safe user context, debug files |
| `desktop-client` | renderer UI errors, updater/deep-link/tray flows, native Tauri/Rust failures, desktop release artifacts, JS source maps, native symbols |
| `android-tv` | app crashes, Compose/runtime errors, network/session issues, release health, ProGuard/R8 mappings/debug files |

## Рекомендуемая структура Sentry-проектов

Базовый принцип: один deployable runtime = один Sentry project. Исключение — desktop, где лучше разделить renderer и native.

Рекомендуемый набор:

- `cybervpn-frontend-web`
- `cybervpn-admin-web`
- `cybervpn-partner-web`
- `cybervpn-backend-api`
- `cybervpn-task-worker`
- `cybervpn-telegram-bot`
- `cybervpn-node-fleet-controller`
- `cybervpn-helix-adapter`
- `cybervpn-helix-node`
- `cybervpn-mobile`
- `cybervpn-desktop-renderer`
- `cybervpn-desktop-native`
- `cybervpn-android-tv`

Не рекомендовано:

- создавать один общий Sentry project на весь монорепозиторий;
- смешивать backend API и background worker в одном проекте;
- смешивать desktop renderer и desktop native layer;
- создавать отдельные Sentry projects для `packages/*`, `infra/*`, `docs/*`.

## Стандарты environment и release

### Environment

Во всех runtime нужен единый словарь:

- `development`
- `staging`
- `production`

Это особенно важно для web-приложений, где текущая привязка к `NODE_ENV` недостаточна: staging-сборка на production runtime иначе визуально сольётся с production.

### Release

Рекомендуемая схема:

- user-facing packaged apps: `<surface>@<semver>+<build>`
- backend/services: `<surface>@<git_sha>`

Примеры:

- `cybervpn-mobile@1.4.2+381`
- `cybervpn-desktop-renderer@0.1.5+20260423`
- `cybervpn-backend-api@<git_sha>`
- `cybervpn-task-worker@<git_sha>`

Release должен быть одинаково проставлен:

- в SDK init;
- в CI/CD release step;
- в deploy marker;
- в artifact upload step.

## Общие требования к тегам и контексту

Минимальный набор общих тегов:

- `environment`
- `release`
- `runtime_surface`
- `service.name`
- `deployment_ring`

Дополнительные теги по категориям:

- web: `route_group`, `locale`, `device_bucket`, `viewport_bucket`, `connection_type`
- backend: `endpoint`, `realm`, `payment_provider`, `webhook_source`
- worker: `task_name`, `queue`, `retry`, `schedule`
- bot: `handler`, `bot_mode`, `payment_provider`
- control plane: `node_id`, `operation_type`, `workflow_stage`
- mobile/desktop/tv: `platform`, `app_version`, `build_number`

Теги должны быть нормализованы и не должны содержать:

- raw UUID/token payloads без явной необходимости;
- email;
- access/refresh/session tokens;
- cookies;
- payment secrets;
- VPN config contents.

## Privacy и PII: обязательные правила

Для CyberVPN privacy-конфигурация не является вторичной задачей. Она должна быть заложена до rollout.

Обязательные правила:

- не отправлять в Sentry `Authorization`, `Cookie`, `Set-Cookie`, API keys, JWT, Telegram auth payloads, Remnawave tokens, OpenBao tokens, DB URLs и другие секреты;
- не отправлять сырой request/response body для auth, payment, wallet, webhooks, provisioning, config delivery и admin endpoints;
- не отправлять VPN-конфиги, access credentials и transport secrets;
- не отправлять email/username/ip-address по умолчанию;
- использовать только минимальный user identity, как уже сделано в mobile через `user.id`;
- session replay включать только для web surfaces и только с privacy review;
- server-side scrubbing rules в Sentry должны быть обязательной частью rollout.

Практический вывод по текущему репозиторию:

- mobile уже следует хорошей модели: `sendDefaultPii = false`, пользователь синхронизируется только по `id`;
- web нужно держать в той же философии и не слепо копировать примеры Sentry с включённым PII;
- backend и сервисы нужно сопровождать явным правилом scrub headers/query/body context.

## Artifacts и CI/CD, которые обязательно нужно довести

### Web

Нужно обеспечить:

- upload source maps для `frontend`, `admin`, `partner`;
- унифицированный набор `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`;
- release/deploy markers;
- явную передачу server-side `SENTRY_DSN`, а не только `NEXT_PUBLIC_SENTRY_DSN`.

### Backend и Python services

Нужно обеспечить:

- единый release naming;
- deploy markers на staging/production;
- environment parity между контейнерными image builds и runtime deploy;
- smoke event после старта сервиса.

### Mobile

Нужно обеспечить:

- единообразную загрузку Dart debug files не только в общем CI, но и в release workflow;
- одинаковую release-модель для Android и iOS;
- связку build number/version с Sentry release.

### Desktop

Нужно обеспечить:

- source maps для renderer;
- native debug symbols для Tauri/Rust builds;
- release/deploy markers для desktop tags;
- отдельные smoke-tests для renderer и native paths.

### Android TV

Нужно обеспечить:

- mapping/debug artifacts для release builds;
- release health;
- отдельный Sentry project;
- CI release flow с загрузкой нужных символов/маппингов.

### Rust control-plane services

Нужно обеспечить:

- отдельную release-схему для `helix-adapter` и `helix-node`;
- policy по native symbol/debug artifact handling;
- tags для control-plane операций;
- smoke-test на реальный event path.

## Приоритет rollout

### Wave 1: довести уже частично интегрированные поверхности

- `frontend`
- `admin`
- `partner`
- `backend`
- `services/task-worker`
- `cybervpn_mobile`

Цель wave:

- убрать конфигурационные дыры;
- выровнять environment/release;
- выровнять artifact upload;
- формализовать privacy;
- сделать Sentry operationally usable.

### Wave 2: закрыть критичные production surfaces без Sentry

- `services/telegram-bot`
- `services/node-fleet-controller`
- `apps/desktop-client`
- `apps/android-tv`

### Wave 3: закрыть remaining control-plane/native surfaces

- `services/helix-adapter`
- `services/helix-node`

### Future wave

- `apps/browser-extension` после появления реального runtime-кода

## Definition of Done для полной интеграции

Интеграцию можно считать завершённой только если выполнено всё ниже:

- для каждой production runtime-поверхности создан и документирован Sentry project;
- каждая поверхность успешно отправляет тестовое событие в `development`, `staging` и `production`;
- в каждом runtime есть корректные `environment` и `release`;
- source maps / debug files / mappings загружаются автоматически там, где они нужны;
- есть privacy review и server-side scrubbing rules;
- user context безопасен и минимален;
- есть понятные alert rules и ownership;
- release/deploy markers позволяют увидеть, какое изменение привело к регрессии;
- shared packages не имеют ложных “самостоятельных” Sentry projects;
- staging не смешивается с production в Sentry UI.

## Итоговый вывод

Полная интеграция Sentry для CyberVPN — это не задача “подключить SDK в Next.js”. Это задача привести к единой модели все реальные runtime-поверхности полиглотного монорепозитория: web, backend, worker, bot, mobile, desktop, Android TV и control-plane сервисы.

Сейчас проект находится в смешанном состоянии:

- часть web/mobile/backend поверхностей уже хорошо подготовлена;
- часть production runtime вообще не покрыта;
- CI, environment, release и artifact handling ещё не выровнены;
- privacy-подход уже виден в mobile и частично в web, но должен быть формализован для всей платформы.

Следовательно, “что мы должны охватить” для полной интеграции:

- все deployable runtime-поверхности;
- все release pipelines;
- все artifact pipelines;
- единый environment/release contract;
- privacy/scrubbing policy;
- operational ownership и alerting.

Без этого Sentry будет установлен частями, но не станет надёжным operational layer для всей платформы.

## Официальные источники Sentry, на которые стоит опираться при внедрении

- Next.js manual setup: <https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/>
- FastAPI integration: <https://docs.sentry.io/platforms/python/integrations/fastapi/>
- Flutter debug files upload: <https://docs.sentry.io/platforms/flutter/data-management/debug-files/upload/>
- JavaScript configuration options / environments: <https://docs.sentry.io/platforms/javascript/configuration/environments/>
- Rust releases and health guidance: <https://docs.sentry.io/platforms/rust/guides/axum/configuration/releases>
- React data collected guidance: <https://docs.sentry.io/platforms/javascript/guides/react/data-management/data-collected>
- Data scrubbing: <https://docs.sentry.io/security-legal-pii/scrubbing/>
