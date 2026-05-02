# CyberVPN Growth Catalysts — Master Implementation Plan

Статус: Draft for execution  
Дата фиксации baseline: 2026-04-21  
Подготовлено на основе анализа репозитория, существующих модулей и внешних платформенных ограничений Telegram

---

## 1. Цель документа

Этот документ описывает полный технический и продуктовый план внедрения трех катализаторов роста в CyberVPN:

1. Telegram Mini App как основной self-service канал конверсии внутри Telegram.
2. White-Label Partner Self-Service Portal как основной B2B/B2B2C двигатель масштабирования.
3. Real-Time Network Intelligence / Speed Map как быстрый acquisition + trust + SEO слой.

Документ намеренно объемный. Его задача не только перечислить идеи, но и:

- зафиксировать текущий baseline проекта на уровне кода;
- показать, что уже существует и что нельзя переписывать с нуля;
- определить подтвержденные gap'ы;
- предложить целевую архитектуру по каждому направлению;
- разложить изменения по frontend, backend, bot/services, monitoring, data model и infra;
- задать поэтапный roadmap, риски, критерии готовности и порядок внедрения.

---

## 2. Executive Summary

### 2.1. Главный вывод

Проект уже содержит значительную часть фундаментальных блоков для всех трех инициатив. Самый важный вывод после проверки реального кода:

- Telegram Mini App у вас уже не "идея", а частично реализованный продуктовый контур.
- Partner Portal уже не "заготовка", а довольно зрелая платформа с onboarding, workspace-моделью, storefront-контекстом, reseller и integrations-консолями.
- Public `network` и `status` страницы уже существуют, но сейчас в значимой части работают как красиво оформленные placeholders, а не как настоящий live product.

Следовательно, задача не в том, чтобы начинать с нуля. Задача в том, чтобы:

- для Mini App превратить текущий разрозненный набор экранов в быстрый, телеграм-нативный канал активации и оплаты;
- для White-Label Portal использовать уже существующую partner/storefront архитектуру как основу для self-service и bot provisioning;
- для Speed Map заменить статический маркетинговый слой на публичный real-time read model, не ломая существующую observability-платформу.

### 2.2. Рекомендуемый порядок исполнения

Рекомендуемый порядок работ:

1. Запускать `#3 Speed Map MVP` и `#1 Mini App MVP` параллельно.
2. После стабилизации acquisition + activation включать `#2 White-Label Self-Service`.
3. DPI Resistance Score и managed-bot automation выводить во вторую фазу, но закладывать архитектурно уже сейчас.

### 2.3. Ключевые архитектурные решения

Ключевые решения, которые стоит принять заранее:

- Не строить Mini App как набор случайных клиентских запросов в десятки generic endpoint'ов. Нужен отдельный miniapp bootstrap/read-model слой.
- Не строить White-Label Bot Engine как "один деплой на одного партнера" в первой версии. Основной путь должен быть shared multi-tenant runtime + Telegram Managed Bots.
- Не отдавать public Speed Map напрямую из Prometheus на каждую страницу. Нужен materialized public snapshot layer с кэшем и CDN-дружелюбной выдачей.
- Не оставлять оплату цифровых VPN-услуг внутри Telegram на CryptoBot как основной сценарий. Для in-Telegram digital goods базовым платежным контуром должны стать Telegram Stars.

---

## 3. Методология и источники

### 3.1. Что было проверено в репозитории

В рамках анализа были проверены следующие зоны:

- `frontend/` как основной B2C surface.
- `partner/` как существующий B2B portal/storefront surface.
- `backend/` как API и доменная основа.
- `services/telegram-bot/` как текущая Telegram-интеграция.
- `infra/` как observability/data source слой.
- уже существующие `docs/plans/*` и связанные спецификации.

### 3.2. Какие выводы опираются на реальные файлы

Ниже перечислены некоторые важные факты, подтвержденные кодом:

- Mini App уже существует в `frontend/src/app/[locale]/miniapp/`.
- Mini App auth существует в `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`.
- Backend Mini App auth endpoint уже существует в `backend/src/presentation/api/v1/auth/routes.py`.
- Telegram bot API surface для checkout, plans, trial, entitlements и config уже существует в `backend/src/presentation/api/v1/telegram/routes.py`.
- Partner Portal уже содержит dashboard/application/reseller/integrations и runtime state layer.
- Storefront runtime в partner app пока еще во многом env/static-driven.
- Public `network` и `status` страницы в frontend уже есть, но часть данных на них сейчас mock/simulated.
- Monitoring API в backend существует, но он аутентифицирован и не предназначен как public marketing feed.

### 3.3. Внешние платформенные ограничения

Для платформенно нестабильных частей были проверены официальные документы Telegram.

Подтвержденные внешние факты:

- Согласно Telegram Payments for Digital Goods, цифровые товары и услуги внутри Telegram app ecosystem должны продаваться через Telegram Stars, а не через внешний платежный провайдер. Источник: `https://core.telegram.org/bots/payments-stars`
- Telegram Mini Apps поддерживают `startapp`, `start_param`, `openInvoice`, `BackButton`, `MainButton`, `HapticFeedback`, полноэкранный режим и прямые deep link сценарии. Источник: `https://core.telegram.org/bots/webapps`
- В Bot API 9.6 от 2026-04-03 Telegram добавил Managed Bots: `ManagedBotUpdated`, `getManagedBotToken`, `replaceManagedBotToken` и related flows. Источник: `https://core.telegram.org/bots/api-changelog`

Это критично для плана:

- `#1` должен опираться на Telegram Stars в in-Telegram checkout.
- `#2` должен проектироваться вокруг Managed Bots, а не вокруг ручного BotFather automation как primary path.

---

## 4. Текущий baseline проекта

### 4.1. Что уже сильно

У проекта уже есть сильная база:

- Next.js 16 + React 19 + TypeScript 5.9.
- 38 локалей и RTL-поддержка.
- Сильный дизайн-язык и узнаваемый frontend style.
- Telegram bot и Telegram auth flows уже существуют.
- Partner domain уже весьма развит.
- Prometheus/Grafana/Loki/Tempo стек уже поднят.
- Network / status product surface уже есть на уровне UI.

### 4.2. Что важно не сломать

При внедрении фич нельзя разрушить существующие стратегические активы:

- текущие auth realm'ы и cookie/session модель;
- уже существующий partner workspace/application/storefront контур;
- существующие checkout и entitlements use cases;
- observability слой и существующие метрики;
- i18n-модель с локализованными route space;
- Next.js 16.1+ правило проекта: использовать `src/proxy.ts`, а не `src/middleware.ts`.

### 4.3. Главный общий принцип

Все три инициативы должны быть реализованы как расширение текущей архитектуры, а не как новый параллельный стек.

Нельзя:

- делать отдельную miniapp backend-систему вне текущего backend;
- делать отдельную white-label платформу вне partner domain;
- делать public network intelligence как ad-hoc прямые Prometheus query из frontend.

Нужно:

- переиспользовать текущие доменные use case и сделать поверх них channel-specific read models;
- расширить существующие surface-модели и observability;
- построить rollout так, чтобы MVP можно было запускать поэтапно.

---

## 5. Cross-Cutting Architecture Decisions

## 5.1. Channel-specific read models вместо generic client stitching

Во всех трех инициативах нужен отдельный read model слой:

- `miniapp` read model для Telegram UX;
- `public network` read model для SEO/CDN/public traffic;
- `partner provisioning` read model для onboarding/provisioning progress.

Причина:

- generic endpoint'ы уже существуют, но они проектировались под внутренние flows;
- latency, data shape и UX контексты у каждого surface разные;
- channel-specific read models снижают число roundtrip'ов, упрощают frontend и стабилизируют rollout.

## 5.2. Surface taxonomy

Сейчас monitoring/frontend runtime схематически знает только `partner_portal` и `admin_portal`. Нужно расширить surface taxonomy.

Рекомендуемые новые surface labels:

- `customer_miniapp`
- `customer_marketing_network`
- `customer_status_public`
- `partner_storefront`
- `partner_bot_runtime`
- `partner_bot_manager`

Это потребуется для метрик, web vitals, funnel analytics и alert routing.

## 5.3. Public snapshot pattern

Все публичные real-time страницы должны читаться не из live operational источника напрямую, а из snapshot слоя.

Паттерн:

1. Внутренние данные собираются из Prometheus, Remnawave, DB и worker probes.
2. Worker агрегирует их в нормализованный snapshot.
3. Snapshot кладется в Redis/Postgres materialized store.
4. Public API отдает только snapshot.
5. Frontend SSR/ISR/streaming читает только public API.

Преимущества:

- защита Prometheus;
- предсказуемая latency;
- возможность CDN caching;
- возможность versioned payloads;
- меньше риск утечки внутренних operational деталей.

## 5.4. Multi-tenant first

Для partner white-label направления нельзя в первой версии проектировать архитектуру как "один бот = один отдельный сервис/деплой". Это слишком дорого операционно.

Первая версия должна стремиться к:

- shared codebase;
- shared runtime;
- per-partner configuration isolation;
- release-channel management;
- managed bot credential lifecycle.

---

## 6. Initiative #1 — Telegram Mini App

## 6.1. Что уже существует в коде

Проверенный baseline:

- `frontend/src/app/[locale]/miniapp/layout.tsx`
- `frontend/src/app/[locale]/miniapp/page.tsx`
- `frontend/src/app/[locale]/miniapp/home/page.tsx`
- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/payments/page.tsx`
- `frontend/src/app/[locale]/miniapp/wallet/page.tsx`
- `frontend/src/app/[locale]/miniapp/profile/page.tsx`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/devices/page.tsx`
- `frontend/src/app/[locale]/miniapp/components/MiniAppBottomNav.tsx`
- `frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts`
- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`

Что это означает practically:

- Mini App уже не пустой.
- Навигация, auth bootstrap, dashboard/plans/wallet/referral/profile уже есть.
- Frontend уже интегрирован с реальными API-клиентами для usage, entitlements, payments, referral и wallet.

## 6.2. Подтвержденные проблемы текущей реализации

### 6.2.1. Маршрутизация Mini App сейчас непоследовательна

Подтвержденный дефект:

- `frontend/src/app/[locale]/miniapp/page.tsx` редиректит на `/${locale}/home`, а не на `/${locale}/miniapp/home`.

Результат:

- корень Mini App может выбросить пользователя из miniapp route space;
- это ломает mental model, deep-linking и часть guarded UX.

### 6.2.2. Auto-auth flow выбрасывает пользователя в dashboard вне Mini App

Подтвержденный дефект:

- `TelegramMiniAppAuthProvider.tsx` после auth ведет пользователя на `/dashboard`.
- return path для 2FA тоже указывает на `/${locale}/dashboard`.

Результат:

- даже успешная miniapp-аутентификация может увести пользователя из TWA-сценария;
- это разрушает обещание "VPN внутри Telegram без выхода наружу".

### 6.2.3. Нет явного server list / server picker Mini App surface

Хотя в продуктовой идее серверы являются ключевой частью UX, в текущем `miniapp/` route tree нет явного полноценного `servers` surface с:

- live ping;
- рекомендованным выбором региона;
- one-tap config copy/open;
- protocol hints;
- status badges.

### 6.2.4. Checkout пока не приведен к Telegram-native payment contract

В репозитории уже видно сильную ориентацию на:

- external payment URLs;
- CryptoBot-сценарии;
- generic checkout payloads.

Но для цифровой VPN-подписки внутри Telegram основным каналом оплаты должен стать Telegram Stars. Это нужно проектно и контрактно закрепить.

### 6.2.5. Mini App пока слишком сильно зависит от generic API stitching

Текущий Mini App уже ходит в несколько API-клиентов. Для production-grade TWA это создает риски:

- лишние roundtrip'ы;
- дублирующая логика загрузки;
- высокая чувствительность к частичным деградациям;
- сложный cold-start в Telegram webview.

### 6.2.6. Telegram UI lifecycle реализован частично

`useTelegramWebApp` уже использует:

- `ready()`
- `expand()`
- theme access
- haptic feedback

Но полноценный lifecycle пока не выглядит завершенным:

- нет полноценного orchestration вокруг `BackButton`;
- нет MainButton-driven checkout UX как core pattern;
- нет явного viewport/safe-area контракта;
- нет четкой startapp attribution pipeline;
- нет явной session bootstrap telemetry для Telegram surface.

## 6.3. Что уже существует в backend для Mini App и Telegram

Подтвержденные backend assets:

- Mini App auth endpoint уже есть в `/api/v1/auth/telegram/miniapp`.
- Telegram bot-facing API уже имеет user bootstrap, plans, orders, entitlements, service-state, trial, referral, config, checkout quote/commit.
- Телеграм rate limiting и internal secret protection уже реализованы.

Это очень важный плюс: backend не нужно создавать с нуля.

## 6.4. Целевое видение Mini App

Mini App должен стать не "webview-версией сайта", а отдельным channel-optimized продуктом.

Целевой flow:

1. Пользователь открывает `https://t.me/<bot>?startapp=<payload>`.
2. WebApp поднимается в fullscreen.
3. Происходит мгновенный bootstrap с уже верифицированным Telegram identity.
4. Пользователь сразу видит один из трех сценариев:
   - уже активный план;
   - eligible free trial;
   - быстрый checkout.
5. Оплата происходит внутри Telegram через Stars invoice.
6. После оплаты пользователь в один тап получает конфиг, QR, deep link, device onboarding или connect-to-app guidance.
7. Referral/share flow является first-class citizen, а не спрятанной secondary screen.

## 6.5. Рекомендуемая архитектура Mini App

### 6.5.1. Новый backend namespace для Mini App

Рекомендуется добавить отдельный namespace:

- `backend/src/presentation/api/v1/miniapp/routes.py`

Он не должен дублировать core domain logic. Он должен агрегировать ее в Telegram-specific shape.

Рекомендуемые endpoint'ы:

- `GET /api/v1/miniapp/bootstrap`
- `GET /api/v1/miniapp/dashboard`
- `GET /api/v1/miniapp/servers`
- `GET /api/v1/miniapp/offers`
- `POST /api/v1/miniapp/checkout/quote`
- `POST /api/v1/miniapp/checkout/invoice`
- `POST /api/v1/miniapp/trial/activate`
- `GET /api/v1/miniapp/referral`
- `POST /api/v1/miniapp/referral/share`
- `GET /api/v1/miniapp/support`
- `POST /api/v1/miniapp/events`

Принцип:

- read-heavy data агрегируется в одном-двух bootstrap payloads;
- write endpoints остаются узкими и action-oriented;
- Mini App frontend перестает напрямую собирать себя из множества unrelated API.

### 6.5.2. Bootstrap payload

`/miniapp/bootstrap` должен возвращать единую модель:

- текущий auth/session status;
- профайл Telegram user;
- статус trial;
- текущий entitlement/subscription snapshot;
- wallet balance;
- active device summary;
- recommended server;
- primary CTA;
- unresolved payment state;
- referral code and invite URL;
- locale + rtl + theme hints;
- feature flags;
- customer support entrypoints.

Это позволит сделать TWA реально быстрым.

### 6.5.3. Mini App route map

Рекомендуемая route structure:

- `/[locale]/miniapp`
- `/[locale]/miniapp/home`
- `/[locale]/miniapp/servers`
- `/[locale]/miniapp/plans`
- `/[locale]/miniapp/wallet`
- `/[locale]/miniapp/referral`
- `/[locale]/miniapp/profile`
- `/[locale]/miniapp/payments`
- `/[locale]/miniapp/devices`
- `/[locale]/miniapp/support`

Ключевое правило:

- ни один auth redirect не должен уводить пользователя в обычный `/dashboard`, если он находится внутри Telegram Mini App flow.

### 6.5.4. Telegram-native UI orchestration

Нужно выделить отдельный orchestration layer поверх текущего `useTelegramWebApp`.

Рекомендуемые модули:

- `useMiniAppViewport`
- `useMiniAppBackButton`
- `useMiniAppMainButton`
- `useMiniAppStartParam`
- `useMiniAppTheme`
- `useMiniAppAnalytics`
- `useMiniAppInvoice`

Что должен уметь orchestration layer:

- правильно раскрывать webview;
- управлять safe area;
- синхронизировать theme с design tokens;
- поддерживать кнопку назад Telegram и внутренний router;
- открывать invoice через `openInvoice`;
- фиксировать `invoiceClosed`;
- поддерживать haptic feedback как системный UX layer;
- читать `start_param` и прокидывать его в attribution/referral pipeline.

## 6.6. Payment architecture для Mini App

### 6.6.1. Что нужно изменить концептуально

Для цифрового VPN-доступа внутри Telegram:

- Telegram Stars должны стать primary payment rail.
- CryptoBot не должен оставаться дефолтным in-Telegram checkout.

Важно:

- web/storefront outside Telegram может сохранить crypto/fiat rails;
- но Mini App и bot внутри Telegram должны строиться вокруг Telegram payment compliance.

### 6.6.2. Что нужно изменить в backend

Нужны изменения в payment domain:

- добавить payment provider `telegram_stars`;
- добавить invoice generation flow для Telegram;
- добавить webhook/confirmation handling для Telegram Stars payment completion;
- связать post-payment provisioning с Telegram invoice lifecycle;
- нормализовать `payment_method` enum across frontend/backend/generated types;
- развести checkout behavior по surface: `telegram_miniapp`, `telegram_bot`, `web`, `partner_storefront`.

### 6.6.3. Что нужно изменить в frontend Mini App

Нужно:

- убрать зависимость от внешнего payment URL как основного happy path;
- вместо этого открывать invoice внутри Telegram через WebApp API;
- после `invoiceClosed` обновлять bootstrap/dashboard;
- уметь показывать `paid`, `cancelled`, `pending`, `failed`;
- отображать оставшиеся Stars-independent бонусы, trial, upgrade hints.

## 6.7. Referral architecture для Mini App

Текущая referral страница уже существует, что отлично. Теперь ее нужно усилить до growth primitive.

Нужно:

- поддержать `startapp` attribution payloads;
- генерировать short, sharable Telegram-native invite links;
- сохранять campaign/source/referrer метаданные;
- поддержать share to chat / story сценарии;
- уметь считать Telegram-specific K-factor.

Желательная модель referral payload:

- referral code;
- inviter Telegram ID;
- campaign slug;
- surface `miniapp`;
- optional partner/storefront source;
- signed expiration metadata.

## 6.8. Onboarding и activation

Рекомендуемый MVP onboarding:

Экран 1:

- Что такое CyberVPN.
- Почему безопасно.
- CTA: "Запустить бесплатный доступ" или "Подключить за 30 секунд".

Экран 2:

- Выбор quick plan.
- Выбор recommended region.
- CTA оплаты или trial activation.

После этого:

- вывод конфигурации;
- deep link в Telegram bot / desktop / mobile client;
- QR или copy URL;
- кнопка "Проверить соединение".

## 6.9. Безопасность Mini App

Минимальные требования:

- серверная валидация `initData` остается обязательной;
- нельзя строить security-sensitive flows на `initDataUnsafe`;
- session binding должен учитывать Telegram identity и auth realm;
- реферальные и offer payload'ы должны быть signed;
- invoice completion должен быть server-authoritative;
- anti-replay и anti-spam rate limits нужны на share/checkout/trial;
- device config выдача должна быть auditable.

## 6.10. Analytics и observability для Mini App

Нужно ввести отдельную воронку:

- `miniapp_opened`
- `miniapp_bootstrap_loaded`
- `miniapp_auth_success`
- `miniapp_trial_seen`
- `miniapp_trial_started`
- `miniapp_plan_viewed`
- `miniapp_checkout_started`
- `miniapp_invoice_opened`
- `miniapp_payment_success`
- `miniapp_payment_cancelled`
- `miniapp_config_delivered`
- `miniapp_referral_shared`

Нужно также добавить web-vitals/runtime metrics для surface `customer_miniapp`.

## 6.11. Definition of Done для Mini App MVP

Mini App MVP можно считать готовым, когда:

- root route всегда остается в miniapp namespace;
- auth не выбрасывает пользователя наружу;
- cold start до первого meaningful экрана стабильно низкий;
- checkout внутри Telegram работает через Stars;
- user может пройти путь open -> pay/trial -> get access без браузерного выхода;
- share/referral flow измерим;
- есть базовые события observability;
- есть поддержка i18n хотя бы для top-10 языков из существующего набора;
- есть тесты на auth, routing, checkout, bootstrap, referral.

## 6.12. Рекомендуемая декомпозиция работ по Mini App

Поток A:

- route cleanup
- auth redirect cleanup
- unified bootstrap endpoint
- telemetry

Поток B:

- Stars payment integration
- invoice lifecycle
- entitlement refresh

Поток C:

- server picker
- onboarding polish
- referral/share polish

---

## 7. Initiative #2 — White-Label Partner Self-Service Portal

## 7.1. Что уже существует в коде

Проверенный baseline partner app:

- `partner/src/app/[locale]/(dashboard)/application/page.tsx`
- `partner/src/app/[locale]/(dashboard)/dashboard/page.tsx`
- `partner/src/app/[locale]/(dashboard)/reseller/page.tsx`
- `partner/src/features/partner-onboarding/*`
- `partner/src/features/partner-reseller/*`
- `partner/src/features/partner-integrations/*`
- `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts`
- `partner/src/features/storefront-shell/lib/runtime.ts`

Проверенный baseline backend:

- partner application repositories уже существуют;
- storefront repositories уже существуют;
- workspace profile repositories уже существуют;
- partner routes уже покрывают большой объем onboarding/workspace capabilities.

Вывод:

- партнерская платформа у вас уже есть;
- задача состоит не в создании "партнерского портала", а в превращении существующего partner platform baseline в настоящий self-service business engine.

## 7.2. Подтвержденные ограничения текущего состояния

### 7.2.1. Storefront runtime еще не полностью data-driven

`partner/src/features/storefront-shell/lib/runtime.ts` пока во многом опирается на:

- default storefront key;
- default auth realm key;
- host-derived brand name;
- static support/communication/merchant profiles.

Это означает:

- shell под white-label уже продуман;
- но end-to-end dynamic storefront provisioning еще не завершен.

### 7.2.2. Нет явного bot provisioning domain

В текущем коде не видно полноценного доменного слоя для:

- partner bot identity;
- bot credential lifecycle;
- bot release channel;
- bot branding assets;
- bot webhook/runtime state;
- managed bot provisioning status;
- partner-specific Mini App binding.

### 7.2.3. Нет автоматизированного white-label bot lifecycle

Текущая система уже богата на codes, payouts, applications, workspace state. Но нет подтверждения, что партнер может self-service образом:

- зарегистрироваться;
- пройти moderation;
- настроить бренд;
- выпустить собственного Telegram-бота;
- получить рабочий branded Mini App и checkout pipeline.

## 7.3. Ключевая стратегическая развилка

Самая важная архитектурная развилка для `#2`:

### Вариант A. "Один партнер = один отдельный бот = один отдельный деплой"

Плюсы:

- простая ментальная модель;
- локальная изоляция runtime.

Минусы:

- дорого;
- тяжело обновлять;
- сложно поддерживать сотни партнеров;
- высокий операционный шум;
- сложный release management.

### Вариант B. Managed Bots + shared multi-tenant runtime

Плюсы:

- масштабируется;
- проще деплоить;
- проще делать rollback;
- легче централизовать безопасность и observability;
- лучше соответствует платформенному направлению Telegram после появления Managed Bots.

Минусы:

- выше архитектурная дисциплина;
- нужны четкие tenant boundaries;
- нужен credential/token management layer.

Рекомендация:

- Для production roadmap выбирать Вариант B как primary architecture.
- Для раннего pilot можно допустить limited manual fallback.

## 7.4. Целевое видение White-Label системы

Партнер должен проходить следующий путь:

1. Заходит на partner landing.
2. Создает application.
3. Проходит скоринг и модерацию.
4. Получает workspace.
5. Настраивает бренд.
6. Выбирает markup, pricing и GTM assets.
7. Нажимает "Создать моего Telegram-бота".
8. Система выделяет managed bot identity и связывает его с branded storefront + miniapp.
9. Партнер получает:
   - bot username;
   - Mini App link;
   - invite links;
   - QR assets;
   - payout and finance visibility;
   - conversion analytics.

## 7.5. Рекомендуемая доменная модель

Нужно добавить новые агрегаты или эквивалентные сущности:

- `PartnerBot`
- `PartnerBotBranding`
- `PartnerBotProvisioningJob`
- `PartnerBotCredential`
- `PartnerBotRelease`
- `PartnerBotWebhookBinding`
- `PartnerBotMiniAppBinding`
- `PartnerStorefrontBrandTheme`
- `PartnerCommercialPolicy`
- `PartnerDistributionAsset`

Пример обязательных полей `PartnerBot`:

- `id`
- `workspace_id`
- `telegram_bot_id`
- `username`
- `display_name`
- `short_description`
- `miniapp_short_name`
- `status`
- `provisioning_state`
- `release_channel`
- `managed_by_bot_id`
- `managed_bot_token_ref`
- `default_locale`
- `brand_theme_id`
- `storefront_id`
- `commercial_policy_id`
- `created_at`
- `updated_at`

## 7.6. Provisioning architecture

### 7.6.1. Рекомендуемый provisioning pipeline

Предлагаемый pipeline:

1. Партнер подтвержден и имеет workspace.
2. Портал создает `PartnerBotProvisioningJob`.
3. Provisioning service резервирует managed-bot identity.
4. Создается или обновляется `PartnerBot` record.
5. Применяются branding settings.
6. Генерируются bot commands, descriptions, menu button, main mini app binding.
7. Назначается webhook/runtime registration.
8. Генерируются invite/startapp links.
9. В partner portal показывается progress и итоговые артефакты.

### 7.6.2. Какой сервис должен этим заниматься

Наиболее разумно добавить отдельный orchestration слой, а не смешивать это с request-response логикой portal.

Возможные формы:

- новый worker namespace в существующем task-worker;
- новый `partner-bot-orchestrator` service;
- либо расширение bot service, если tenancy и workload будут аккуратно изолированы.

Рекомендуемое решение:

- orchestration и provisioning держать в worker/orchestrator слое;
- runtime message handling оставлять в bot runtime слое.

## 7.7. Portal UX для self-service

Нужен отдельный многошаговый wizard внутри partner portal.

Этапы:

1. Business profile
2. Traffic source / target geo
3. Brand identity
4. Pricing / markup / margin simulation
5. Legal / KYC / risk policy
6. Bot creation
7. Storefront and launch assets
8. First campaign launch checklist

Для каждого шага нужны:

- validation rules;
- save draft capability;
- status banners;
- approval requirements;
- analytics events;
- operator override path.

## 7.8. Storefront / commerce integration

White-label система не должна жить отдельно от storefront domain.

Нужно:

- связать `PartnerBot` с существующим storefront/realm model;
- сделать brand theme реально data-driven;
- вынести support/legal/merchant/commercial profiles из статических defaults в DB-backed configuration;
- переиспользовать существующие auth realm и codes/finance модели;
- создать единый `partner commercial context`, который используют и storefront, и bot, и Mini App.

## 7.9. Telegram Mini App и White-Label пересекаются

Очень важный вывод:

- `#1` и `#2` не должны строиться как независимые продукты.

Правильная модель:

- сначала создается canonical CyberVPN Mini App runtime;
- затем тот же runtime учится работать в white-label режиме;
- дальше у каждого партнера появляется branded entrypoint поверх shared capabilities.

Это снизит стоимость разработки и поддержку.

## 7.10. Payment model для white-label партнеров

Нужно четко разделить:

- кто является merchant of record;
- кто получает выручку;
- как считается markup;
- как считается partner revenue;
- какие payment rails доступны внутри Telegram и вне Telegram;
- как отражаются Stars-транзакции в partner wallet.

Обязательные вопросы модели:

- Партнер продает "от своего имени" или "как branded distribution channel CyberVPN"?
- Кто несет refund responsibility?
- Как Stars revenue маппится в партнерский внутренний баланс?
- Какие rails доступны для partner payout: USDT, wallet, internal settlement?

## 7.11. Security, abuse и compliance

White-label self-service без guardrails превратится в abuse vector.

Нужно заложить:

- KYC / KYB tiers;
- risk scoring для новых партнеров;
- лимиты на bot creation и brand impersonation;
- запрет на dangerous/forbidden naming patterns;
- manual review для certain geographies and claims;
- moderation для logos, descriptions, landing copy;
- audit trail всех provisioning действий;
- rotate/revoke managed bot credentials;
- incident playbook на случай abuse bot.

## 7.12. Observability для partner bot platform

Нужны отдельные метрики:

- `partner_application_submitted`
- `partner_application_approved`
- `partner_workspace_activated`
- `partner_bot_provisioning_started`
- `partner_bot_provisioning_succeeded`
- `partner_bot_provisioning_failed`
- `partner_bot_release_published`
- `partner_bot_checkout_success`
- `partner_bot_checkout_failure`
- `partner_bot_referral_share`
- `partner_bot_customer_activation`

И operational metrics:

- bot provisioning duration
- token rotation count
- webhook sync failures
- tenant configuration drift
- per-bot payment success rate
- per-bot support incident rate

## 7.13. Definition of Done для White-Label MVP

White-Label MVP можно считать готовым, когда:

- новый партнер может self-service подать заявку и пройти onboarding;
- после approve создается рабочее partner workspace;
- партнер настраивает бренд и коммерческую политику;
- система выдает рабочий branded bot / branded mini app entrypoint;
- partner sees conversions, payouts and launch assets;
- есть audit, moderation и rollback;
- нет ручной правки кода/окружения под каждого нового партнера.

## 7.14. Рекомендуемая декомпозиция работ по White-Label

Поток A:

- partner commercial model hardening
- storefront runtime datafication
- brand theme model

Поток B:

- bot provisioning domain
- managed bot integration spike
- orchestrator service

Поток C:

- onboarding wizard
- launch assets
- analytics and support tooling

---

## 8. Initiative #3 — Real-Time Network Intelligence / Speed Map

## 8.1. Что уже существует в коде

Проверенный baseline:

- `frontend/src/app/[locale]/(marketing)/network/page.tsx`
- `frontend/src/app/[locale]/(marketing)/status/page.tsx`
- `frontend/src/widgets/servers/network-dashboard.tsx`
- `frontend/src/widgets/servers/global-metrics-hud.tsx`
- `frontend/src/widgets/status/status-dashboard.tsx`
- `frontend/src/widgets/status/uptime-history.ts`
- `frontend/src/widgets/status/incident-log.tsx`
- `backend/src/presentation/api/v1/monitoring/routes.py`
- `backend/src/presentation/api/v1/ws/monitoring.py`
- `backend/src/application/use_cases/monitoring/*`
- `infra/prometheus/*`
- `infra/grafana/dashboards/*`

Это означает:

- продуктовый UX слой уже намечен;
- data backbone уже частично есть;
- observability platform уже зрелая;
- но public intelligence product еще не доведен до реальности.

## 8.2. Подтвержденные gap'ы текущей реализации

### 8.2.1. Uptime history сейчас synthetic

`frontend/src/widgets/status/uptime-history.ts` генерирует историю на 90 дней через deterministic mock logic.

Следствие:

- UI хороший, но это не public proof;
- страница не может использоваться как реальное trust доказательство.

### 8.2.2. Incident log сейчас mock-based

`frontend/src/widgets/status/incident-log.tsx` использует `mockIncidents`.

Следствие:

- public status narrative пока не является operationally truthful source.

### 8.2.3. Global metrics HUD сейчас partly simulated

`frontend/src/widgets/servers/global-metrics-hud.tsx` симулирует часть динамики, например threat counter.

Следствие:

- визуально page сильная;
- но цифры не являются корректной public live metric.

### 8.2.4. Existing monitoring API не годится как public marketing API

`backend/src/presentation/api/v1/monitoring/routes.py`:

- аутентифицирован;
- завязан на `Permission.MONITORING_READ`;
- ориентирован на internal monitoring use cases;
- не дает нужного public read model per-node/per-region/per-incident.

### 8.2.5. DPI Resistance Score как продукт еще отсутствует

В текущем backend нет подтвержденного публичного DPI score contract.

Это значит:

- Level 1 Speed Map MVP можно делать быстро;
- Level 3 DPI score требует отдельного data collection workstream.

## 8.3. Целевое видение Network Intelligence

Нужен отдельный публичный продукт, а не просто маркетинговая секция.

Он должен отвечать на три вопроса:

1. Насколько быстро работает сеть CyberVPN прямо сейчас?
2. Насколько стабильно она работает в горизонте 30/90 дней?
3. Насколько хорошо она проходит DPI/censorship-sensitive среды?

## 8.4. Три уровня реализации

### Level 1. Public Speed Map MVP

Содержит:

- live overview по сети;
- leaderboard по регионам/нодам;
- public uptime snapshot;
- recent incidents;
- CTA на trial/miniapp;
- локализованный SEO-friendly контент;
- share-friendly visuals.

### Level 2. In-App Intelligence

Содержит:

- speed test в app surfaces;
- personalized recommended region;
- historical trend;
- compare before/after server switch;
- performance-based notifications.

### Level 3. DPI Resistance Intelligence

Содержит:

- protocol-by-country score;
- success/failure signals от probes;
- censorship resilience badge system;
- публичную карту "where CyberVPN works right now".

## 8.5. Рекомендуемая data architecture

### 8.5.1. Public network snapshot pipeline

Предлагаемый pipeline:

1. Worker по расписанию читает Prometheus, internal monitoring, node metadata и optional probe results.
2. Нормализует агрегаты:
   - per-node
   - per-region
   - global
   - incidents
   - uptime windows
3. Записывает snapshots в Redis/Postgres.
4. Public API отдает только снимки.
5. Frontend SSR/streaming рендерит public page.

### 8.5.2. Рекомендуемые backend endpoint'ы

Рекомендуется новый namespace:

- `backend/src/presentation/api/v1/public_network/routes.py`

Рекомендуемые endpoint'ы:

- `GET /api/v1/public/network/overview`
- `GET /api/v1/public/network/leaderboard`
- `GET /api/v1/public/network/regions`
- `GET /api/v1/public/network/incidents`
- `GET /api/v1/public/network/uptime`
- `GET /api/v1/public/network/widget`
- `GET /api/v1/public/network/seo-summary`
- `GET /api/v1/public/network/dpi-score`

Для MVP достаточно первых пяти плюс widget.

### 8.5.3. Почему нельзя просто ходить в Prometheus из public frontend

Потому что это создаст:

- лишнюю нагрузку;
- неустойчивую latency;
- риск утечки внутренних меток/лейблов;
- сложность rate limiting;
- зависимость public marketing funnel от internal monitoring query performance.

## 8.6. Frontend changes для Speed Map

Нужно заменить mock/simulated участки настоящими read models:

- `uptime-history.ts` должен принимать реальный snapshot.
- `incident-log.tsx` должен работать от public incidents feed.
- `global-metrics-hud.tsx` должен отрисовывать реальные агрегаты.
- leaderboard и map overlays должны читаться из public API.

Рекомендуемые новые модули:

- `frontend/src/lib/api/public-network.ts`
- `frontend/src/features/network-intelligence/*`
- `frontend/src/widgets/network/*`

Нужно также добавить:

- skeleton/loading states;
- last-updated marker;
- source-of-truth labels;
- degraded mode UI, если snapshot просрочен.

## 8.7. SEO strategy для Speed Map

Это не просто operational dashboard, а SEO and trust asset.

Нужно:

- SSR-рендер для основных summary-блоков;
- мета-теги и localized copy;
- OG images;
- schema.org structured data там, где уместно;
- индексация на 38 локалей по мере готовности;
- отдельные long-tail страницы по гео/протоколам позже;
- статические evergreen секции рядом с live data.

Примеры будущих SEO-кластеров:

- fastest VPN regions
- VPN latency map
- VPN uptime status
- censorship resistant VPN
- VPN works in Iran / Russia / Turkey

## 8.8. Widget / virality strategy

Нужен embeddable widget для партнеров и внешних сайтов.

Формы:

- iframe widget
- script embed
- image/OG share card

Минимальные виджеты:

- top speed locations
- current uptime
- recommended regions
- "CyberVPN live now" badge

## 8.9. DPI Resistance Score — отдельный поток работ

Это нельзя делать на догадках. Нужен измеримый scoring model.

Предлагаемая модель score:

- connection success rate
- median handshake latency
- session survival window
- fallback success by protocol
- challenge rate / block rate
- packet loss under stress
- freshness of probe

Нужен отдельный probe layer:

- worker probes из релевантных географий;
- протоколы `VLESS+Reality`, `XHTTP`, `Hysteria 2` и другие;
- периодические прогоны;
- хранение результатов;
- score aggregation.

Важно:

- DPI score должен сопровождаться дисклеймерами и временем последней проверки;
- нельзя обещать "работает в стране X" без достаточного signal quality.

## 8.10. Public status и trust model

Public status page должна стать truthful but safe.

Нужно определить:

- какой уровень инцидентов публикуется;
- как редактируется incident text;
- как считаются uptime windows;
- какой lag допустим для public snapshots;
- какие внутренние operational details никогда не раскрываются.

Рекомендуемая политика:

- публиковать агрегированную operational truth;
- не раскрывать sensitive topology / internal hostnames / capacity ceilings;
- использовать sanitized region/node labels;
- иметь ручной override для major incident communication.

## 8.11. Analytics и observability для Network Intelligence

Нужны funnel events:

- `public_network_page_view`
- `public_network_cta_click`
- `public_network_widget_embed_load`
- `public_network_share_click`
- `public_status_page_view`
- `public_network_region_drilldown`
- `public_network_to_miniapp_click`

Нужны freshness metrics:

- snapshot age
- aggregation job duration
- public feed publish failures
- stale snapshot served

## 8.12. Definition of Done для Speed Map MVP

Speed Map MVP готов, когда:

- public network page использует реальные snapshot data;
- status page показывает реальные uptime/incidents;
- Prometheus не используется как public request path;
- есть public API с sane caching;
- есть CTA into Mini App / trial;
- есть базовая SEO разметка и share cards;
- есть operational freshness monitoring.

## 8.13. Рекомендуемая декомпозиция работ по Speed Map

Поток A:

- public snapshot schema
- aggregation worker
- backend public endpoints

Поток B:

- frontend page refactor
- real data wiring
- SEO / OG / widget

Поток C:

- DPI scoring spike
- probe architecture
- later public DPI rollout

---

## 9. Shared Platform Work Across All Three Initiatives

## 9.1. Auth and identity alignment

Все три инициативы требуют привести к общему знаменателю:

- Telegram identity
- customer auth realm
- partner auth realm
- storefront identity
- bot/miniapp attribution

Особенно важно:

- Mini App, bot и partner storefront не должны расслаиваться в три несовместимых identity модели.

## 9.2. Payment surface policy

Нужно формализовать payment policy matrix:

| Surface | Primary Rail | Secondary Rail | Notes |
|---|---|---|---|
| Telegram Mini App | Telegram Stars | None inside Telegram | Для цифровых услуг внутри Telegram |
| Telegram Bot | Telegram Stars | None inside Telegram | Для цифровых услуг внутри Telegram |
| Main Web | Crypto/Fiat/Wallet | Telegram bot handoff optional | Вне Telegram экосистемы |
| Partner Storefront | Crypto/Fiat/Wallet | Telegram handoff optional | По коммерческой модели |

## 9.3. Configuration management

Нужен единый configuration strategy:

- feature flags per surface;
- partner-specific branding settings;
- public network publishing thresholds;
- locale rollout toggles;
- payment rail availability flags.

## 9.4. I18n strategy

У проекта уже есть 38 локалей. Для трех инициатив нужен pragmatic rollout:

- сначала English + Russian + Turkish + Farsi + Arabic + Uzbek + Indonesian + Spanish + German + French;
- затем остальной хвост по мере стабилизации product copy;
- обязательно проверить RTL для Mini App и public status/network.

## 9.5. Observability expansion

Нужно расширить текущий runtime observability contract:

- новые `surface` значения;
- воронки по Mini App;
- provisioning metrics по partner bots;
- public snapshot freshness;
- partner white-label monetization metrics;
- error budget по critical user paths.

---

## 10. Delivery Roadmap

## 10.1. Рекомендуемые фазы

### Phase 1. 2026-04-22 -> 2026-05-12

Цель:

- быстро вывести public trust asset и стабилизировать Telegram conversion surface.

Состав:

- Speed Map MVP
- Mini App routing/auth cleanup
- Mini App bootstrap endpoint
- Telegram Stars design and contract work

### Phase 2. 2026-05-12 -> 2026-06-09

Цель:

- завершить Mini App conversion engine;
- начать real self-service партнера.

Состав:

- Mini App checkout + referral polishing
- Partner onboarding wizard hardening
- storefront runtime datafication
- Managed Bots spike

### Phase 3. 2026-06-09 -> 2026-07-07

Цель:

- включить white-label provisioning и differentiated intelligence layer.

Состав:

- Partner bot orchestrator MVP
- branded bot / branded mini app launch flow
- DPI probe MVP
- partner launch assets / widget strategy

## 10.2. Параллельные команды/потоки

Оптимальная раздача потоков:

Команда 1:

- frontend marketing/network
- public snapshot UI
- SEO/share assets

Команда 2:

- Mini App frontend
- Mini App backend bootstrap
- Telegram Stars checkout

Команда 3:

- partner/storefront backend
- provisioning domain
- managed bot spike

Команда 4:

- observability
- worker jobs
- data pipelines

---

## 11. Concrete Change Map by Repository Area

## 11.1. `frontend/`

Нужно:

- исправить miniapp route root и auth redirects;
- добавить `servers` surface для Mini App;
- вынести Telegram lifecycle в отдельные hooks/services;
- добавить `public-network` API client;
- заменить mock-based network/status data на реальные public snapshots;
- добавить better CTA bridges из public pages в Mini App;
- подготовить OG/share assets;
- расширить telemetry на новые surfaces.

Вероятные новые модули:

- `frontend/src/lib/api/miniapp.ts`
- `frontend/src/lib/api/public-network.ts`
- `frontend/src/features/miniapp-runtime/*`
- `frontend/src/features/network-intelligence/*`

## 11.2. `backend/`

Нужно:

- добавить `api/v1/miniapp/*`;
- добавить `api/v1/public/network/*`;
- добавить `telegram_stars` payment provider path;
- расширить payment/checkout contracts по surface;
- добавить partner bot provisioning domain;
- добавить public snapshot read repositories;
- расширить observability schemas по новым surfaces.

Вероятные новые зоны:

- `backend/src/presentation/api/v1/miniapp/`
- `backend/src/presentation/api/v1/public_network/`
- `backend/src/application/use_cases/miniapp/`
- `backend/src/application/use_cases/public_network/`
- `backend/src/application/use_cases/partner_bots/`
- `backend/src/infrastructure/database/repositories/public_network_*`

## 11.3. `services/telegram-bot/`

Нужно:

- адаптировать runtime к Telegram Stars flow;
- поддержать partner-specific bot context;
- поддержать managed bot token lifecycle или совместимую abstraction layer;
- внедрить white-label branding resolution;
- добавить per-bot metrics и rollout controls.

## 11.4. `partner/`

Нужно:

- превратить onboarding flow в полный self-service wizard;
- сделать storefront runtime DB-driven;
- добавить bot provisioning status UI;
- добавить bot branding / launch assets / runtime health / release management экраны;
- добавить commercial simulation и support tooling.

## 11.5. `infra/`

Нужно:

- добавить jobs/schedules для public network snapshots;
- при необходимости выделить storage под snapshot history;
- добавить dashboard'ы для Mini App funnel, partner bot provisioning и public snapshot freshness;
- добавить alerts на stale public data и partner bot provisioning failures.

---

## 12. Risks and Hard Constraints

## 12.1. Telegram platform risk

Managed Bots являются новым направлением платформы. Нужно обязательно провести spike и подтвердить:

- доступность для вашей конкретной operational модели;
- ограничения по scale;
- ограничения по permissions;
- токенный lifecycle;
- совместимость с текущей aiogram/runtime архитектурой.

## 12.2. Payment compliance risk

Самый серьезный продуктовый риск:

- если продолжать продвигать покупку цифровой VPN-услуги внутри Telegram через внешние non-Stars rails, это будет конфликтовать с платформенными правилами.

Этот риск нужно закрывать в первую очередь.

## 12.3. Truthfulness risk for public network pages

До тех пор, пока `network` и `status` частично основаны на mock/synthetic данных, нельзя позиционировать их как реальную live transparency layer без оговорок.

## 12.4. Abuse risk for white-label onboarding

Self-service portal без moderation layers может быстро стать каналом abuse, impersonation и fraud.

## 12.5. Performance risk in Mini App

Telegram webview гораздо чувствительнее к лишним roundtrip'ам и тяжелому hydration, чем обычный desktop web.

Следовательно:

- bootstrap payload и latency discipline обязательны.

---

## 13. Recommended First Execution Slice

Если нужен самый практичный первый slice без распыления, рекомендуется начать с этого набора:

### Slice A. За 3-5 дней

- исправить Mini App root redirect;
- исправить auth redirect и 2FA return path;
- ввести `customer_miniapp` surface в observability;
- описать и согласовать Telegram Stars payment contract;
- зафиксировать public network snapshot schema.

### Slice B. За 1-2 недели

- сделать `/api/v1/miniapp/bootstrap`;
- перевести home/plans/referral Mini App на bootstrap + action endpoints;
- реализовать public `overview/leaderboard/uptime/incidents` API;
- заменить mock data на live snapshot data на `network/status`.

### Slice C. За 2-3 недели

- запустить Stars-based Mini App checkout MVP;
- добавить `servers` screen в Mini App;
- запустить embeddable speed widget;
- начать managed-bot spike в partner direction.

---

## 14. Open Questions Requiring Product Decision

### 14.1. Merchant of record policy

Нужно зафиксировать:

- кто является merchant of record для partner white-label продаж;
- какая модель settlements приемлема для Stars revenue.

### 14.2. Trial policy inside Telegram

Нужно решить:

- trial активируется автоматически или по CTA;
- какие geo / risk сегменты получают trial;
- как предотвращать Telegram-based multi-account abuse.

### 14.3. Public transparency policy

Нужно утвердить:

- какой объем incident detail вы готовы публиковать;
- что делать при полном outage;
- кто имеет право вручную редактировать public status narrative.

### 14.4. White-label brand freedom

Нужно определить:

- насколько свободно партнер может называть свой бот;
- какие обязательные cybervpn/legal references должны оставаться;
- какие категории брендов запрещены.

---

## 15. Final Recommendation

Если смотреть на кодовую базу трезво, то проект уже находится не в точке "придумать, что бы сделать", а в точке "собрать сильные куски в продукт, который можно масштабировать".

Главный practical recommendation:

- `#3 Speed Map` запускать первым как fastest visible win.
- `#1 Mini App` доводить одновременно как основной conversion engine.
- `#2 White-Label` строить не как отдельную систему, а как второй слой поверх уже существующих partner/storefront/bot активов.

Самые важные ранние решения:

- Mini App не должен выпадать в обычный dashboard flow.
- In-Telegram digital checkout должен перейти на Telegram Stars.
- White-label bot architecture должна проектироваться вокруг Managed Bots и multi-tenant runtime.
- Public network intelligence должна быть правдивой, snapshot-based и operationally safe.

При такой последовательности вы получите:

- быстрый growth-visible результат;
- улучшение конверсии внутри Telegram;
- более сильный public trust/SEO asset;
- реальный фундамент для масштабируемой partner-driven дистрибуции.

---

## Appendix A — Confirmed File Signals Used in This Analysis

Mini App:

- `frontend/src/app/[locale]/miniapp/page.tsx`
- `frontend/src/app/[locale]/miniapp/layout.tsx`
- `frontend/src/app/[locale]/miniapp/home/page.tsx`
- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/wallet/page.tsx`
- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx`
- `frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts`

Telegram / backend:

- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`
- `services/telegram-bot/src/services/api_client.py`

Partner:

- `partner/src/features/storefront-shell/lib/runtime.ts`
- `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts`
- `partner/src/features/partner-onboarding/components/*`
- `partner/src/features/partner-reseller/components/*`
- `backend/src/infrastructure/database/repositories/storefront_repo.py`
- `backend/src/infrastructure/database/repositories/partner_application_repository.py`
- `backend/src/infrastructure/database/repositories/partner_workspace_profile_repository.py`

Network intelligence:

- `frontend/src/app/[locale]/(marketing)/network/page.tsx`
- `frontend/src/app/[locale]/(marketing)/status/page.tsx`
- `frontend/src/widgets/status/uptime-history.ts`
- `frontend/src/widgets/status/incident-log.tsx`
- `frontend/src/widgets/servers/global-metrics-hud.tsx`
- `backend/src/presentation/api/v1/monitoring/routes.py`
- `backend/src/presentation/api/v1/ws/monitoring.py`
- `infra/prometheus/prometheus.yml`
- `infra/grafana/dashboards/*`

External official references:

- Telegram Mini Apps: `https://core.telegram.org/bots/webapps`
- Telegram payments for digital goods: `https://core.telegram.org/bots/payments-stars`
- Telegram Bot API changelog / Managed Bots: `https://core.telegram.org/bots/api-changelog`
