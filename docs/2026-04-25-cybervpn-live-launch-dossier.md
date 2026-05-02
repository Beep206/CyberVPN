# CyberVPN Live Launch Dossier

**Дата актуализации:** 2026-04-25  
**Репозиторий:** `VPNBussiness`  
**Назначение документа:** дать полную рабочую картину проекта CyberVPN и зафиксировать поэтапный план вывода в живую эксплуатацию.

---

## 1. Короткий вывод

CyberVPN уже не является только фронтендом или экспериментальным VPN-дашбордом. По текущему состоянию репозитория это многоуровневая платформа для VPN-бизнеса:

- клиентский кабинет и Telegram Mini App в `frontend/`;
- отдельная админ-панель в `admin/`;
- отдельный партнерский портал и storefront-слой в `partner/`;
- FastAPI backend с большим доменным API в `backend/`;
- Telegram bot в `services/telegram-bot/`;
- TaskIQ worker и scheduler в `services/task-worker/`;
- Remnawave как authoritative VPN-control backend в локальном/операторском контуре;
- Helix как отдельный private transport stack вокруг Remnawave, desktop runtime и node daemon;
- Flutter mobile app в `cybervpn_mobile/`;
- Android TV app в `apps/android-tv/`;
- Tauri desktop client в `apps/desktop-client/`;
- GitOps, OpenBao, NATS, PostHog, Talos/Kubernetes, backup/restore и production drill планы в `infra/`, `platform-gitops/`, `docs/`.

Главная практическая оценка: **кодовая база сильно продвинута, но live launch нужно делать фазами, с отдельными gates для staging evidence, секретов, платежей, observability, legal/compliance и production rollback.** Ряд документов прямо фиксирует: часть кода готова к handoff, но реальная production-доказательность еще требует живых окружений, реальных credential’ов и release window.

---

## 2. Что это за продукт

CyberVPN — платформа для запуска коммерческого VPN-сервиса с несколькими пользовательскими и операторскими поверхностями.

### Основные пользовательские сценарии

- регистрация и вход через web, mobile, Telegram Mini App, OAuth и Telegram;
- покупка подписки или активация trial;
- получение VPN-конфигурации, QR-кода или device credentials;
- просмотр серверов, протоколов, статуса сети, лимитов, трафика и устройств;
- управление платежами, кошельком, возвратами, историей оплат;
- referral, invite, promo, gift и growth-code механики;
- support, уведомления, security settings, 2FA, linked accounts;
- мобильное/desktop/Android TV подключение к VPN.

### Операторские сценарии

- управление пользователями, подписками, планами, оплатами и возвратами;
- управление серверами, Remnawave/Xray/Helix инвентарем и rollout-состояниями;
- ростовые кампании: invite/referral/promo/gift codes, customer-growth notifications;
- partner program: партнерские кабинеты, storefront, attribution, statements, payouts;
- мониторинг runtime, Sentry, Prometheus/Grafana, PostHog, NATS/outbox;
- staging smoke, conformance runs, evidence packs, canary и rollback.

### Бизнес-модель

В репозитории заложена подписочная VPN-модель:

- тарифы, подписки, add-ons, entitlement grants;
- trial: в bot env указан `TRIAL_DAYS=2`, `TRIAL_TRAFFIC_GB=2`;
- referral: в bot env указан `REFERRAL_BONUS_DAYS=3`, `REFERRAL_MAX_REFERRALS=100`;
- платежи: CryptoBot, Telegram Stars, YooKassa в bot env, backend payment domain, checkout sessions, payment attempts, refunds, disputes;
- партнерская модель: storefronts, partner workspaces, statements, payouts, attribution, reporting.

---

## 3. Монорепозиторий и зоны ответственности

| Путь | Роль | Текущий смысл для запуска |
|---|---|---|
| `frontend/` | Next.js клиентский продукт | основной web-кабинет, marketing pages, Telegram Mini App, customer dashboard |
| `admin/` | Next.js admin workspace | операционная панель для управления бизнесом, ростом, governance, инфраструктурой |
| `partner/` | Next.js partner workspace | портал партнеров, storefront, commercial/finance/compliance/reporting |
| `backend/` | FastAPI API | центральная бизнес-логика, auth, subscriptions, payments, partners, wallet, Remnawave facade |
| `services/telegram-bot/` | aiogram bot | продажи, поддержка, Telegram auth/payment/customer entrypoint |
| `services/task-worker/` | TaskIQ worker/scheduler | фоновые задачи, email, analytics, reporting, reconciliation, notifications |
| `services/helix-adapter/` | Rust control-plane adapter | manifest/rollout layer для Helix без мутации Remnawave |
| `services/helix-node/` | Rust node daemon | получение assignments, health-gated apply, rollback last-known-good |
| `services/node-fleet-controller/` | Python service | целевой контур управления lifecycle внешних node/fleet workflow |
| `cybervpn_mobile/` | Flutter mobile app | iOS/Android клиент, VPN core, auth, subscriptions, push, secure storage |
| `apps/android-tv/` | Kotlin Android TV app | TV-клиент с VpnService, parser, local server manager, Room/DataStore |
| `apps/desktop-client/` | Tauri desktop client | desktop VPN/Helix runtime, diagnostics, automation, release gates |
| `apps/browser-extension/` | placeholder extension | сейчас минимальный package, не production-ready |
| `packages/helix-contract/` | shared JSON schemas | contract fixtures/validation for Helix |
| `packages/flutter_v2ray_plus/` | local Flutter VPN package | локальный override для mobile VPN core |
| `infra/` | local/target infrastructure | Docker Compose, Terraform/OpenTofu, Ansible, OpenBao/NATS/PostHog/Talos helpers |
| `platform-gitops/` | GitOps scaffold | Kubernetes workload delivery shape for backend/task-worker/task-scheduler |
| `docs/` | plans/runbooks/evidence/specs | большое количество execution packs, runbooks, readiness docs |

---

## 4. Технологический стек

### Web apps: `frontend`, `admin`, `partner`

- Next.js `^16.2.3`;
- React `^19.2.4`;
- TypeScript `^5.9.3`;
- Tailwind CSS `^4.2.2`;
- next-intl `^4.9.1`;
- React Compiler enabled;
- `cacheComponents: true`;
- Sentry Next.js `^10.47.0`;
- TanStack Query `^5.96.2`;
- TanStack Table `^8.21.3`;
- Zustand `^5.0.12`;
- Motion `^12.38.0`;
- Three.js `^0.174.0`, React Three Fiber `^9.5.0`;
- Vitest, Testing Library, MSW, eslint flat config.

Important project rule: **Next.js 16 proxy uses `src/proxy.ts`, not `src/middleware.ts`.** This is already true for `frontend/src/proxy.ts`, `admin/src/proxy.ts`, and `partner/src/proxy.ts`.

### Backend

- Python `>=3.13`;
- FastAPI `0.135.3`, Starlette `1.0.0`;
- Uvicorn `0.44.0`;
- Pydantic `2.12.5`, pydantic-settings `2.13.1`;
- SQLAlchemy async, asyncpg, Alembic;
- Redis/Valkey;
- TaskIQ integration;
- NATS optional partner event backbone;
- Sentry, Prometheus metrics, OpenTelemetry;
- JWT, Argon2, TOTP, OAuth provider token encryption;
- Ruff, pytest, coverage threshold.

### Bot and worker

- Telegram bot: Python `>=3.13`, aiogram `3.27.0`, Redis, Sentry, Prometheus, fluent i18n, qrcode, tenacity.
- Task worker: Python `>=3.13`, TaskIQ, Redis, SQLAlchemy async, httpx, Sentry, Prometheus.

### Native clients and transport

- Mobile: Flutter/Dart `^3.10.8`, Riverpod 3, go_router 17, Dio, Drift, Firebase, RevenueCat, Sentry, `flutter_v2ray_plus`.
- Android TV: Kotlin 2.0, Android Gradle Plugin 8.4.1, Compose TV, Hilt, Room, Ktor, Sentry Android.
- Desktop: Tauri 2, Vite 7, React 19.1, TypeScript 5.8, Rust backend, Sentry renderer/native split, Vitest + cargo test.
- Helix: Rust services and Rust packages for contract/runtime/protocol experimentation.

---

## 5. Runtime architecture

### Current practical architecture

```text
Users
  |
  | web / mobile / desktop / Android TV / Telegram
  v
frontend / admin / partner / mobile / desktop / bot
  |
  | HTTP, BFF routes, same-origin /api/v1 rewrites, Telegram APIs
  v
backend FastAPI
  |
  | DB, cache, queue, external providers
  +--> PostgreSQL
  +--> Valkey/Redis
  +--> TaskIQ worker/scheduler
  +--> payment providers
  +--> OAuth providers
  +--> Sentry / Prometheus / OTEL
  +--> Remnawave API
          |
          +--> VPN nodes / Xray / service delivery
  |
  +--> Helix adapter
          |
          +--> Helix nodes
          +--> desktop Helix runtime
```

### Target-state platform direction

The platform foundation docs show a staged move from local/VM/manual operations toward:

- OpenBao for secrets delivery;
- NATS JetStream for canonical event backbone;
- PostHog for product intelligence;
- Talos management clusters;
- Flux/GitOps workload delivery;
- CloudNativePG and Velero-style data protection;
- Alloy as target collector direction;
- Node Fleet Controller replacing manual/semi-manual edge rollout.

Important: `docs/plans/2026-04-21-platform-foundation-monorepo-inventory.md` marks older Compose/Ansible/runtime assumptions as mixed `keep`, `migrate`, or `retire`. Treat Docker Compose as local development/reference topology, not the final production authority.

---

## 6. Backend domain surface

The backend router exposes a broad API under `/api/v1`. Current domains include:

- auth, registration, OAuth, two-factor, security, realms, policies, legal documents;
- users, profile, notifications, servers, subscriptions, plans, addons;
- offers, pricebooks, program eligibility, merchant/invoice/billing descriptors;
- attribution, commercial bindings, growth rewards, growth notifications, gifts;
- renewal orders, policy evaluation, reporting;
- quotes, checkout sessions, orders, payment attempts, refunds, payment disputes;
- traffic declarations, creative approvals, dispute cases, pilot cohorts;
- earning events/holds, partner bots, partner statements, payouts, settlement periods, reserves;
- service identities, entitlements, provisioning profiles, device credentials, access delivery channels;
- Helix, usage, trial;
- payments and billing;
- invite codes, promo codes, referral, partners, partner realtime, wallet, Mini App;
- status, monitoring, public network, admin routes, customer support/operations;
- webhooks, Telegram routes, FCM;
- hosts, config profiles, inbounds, node plugins, squads, snippets, keygen, xray, settings;
- websocket routes for monitoring, notifications and tickets.

The domain model is extensive: there are entities and database models for users, mobile users, admin users, subscriptions, plans, wallet, payments, partners, storefronts, referrals, promo/growth codes, legal documents, policy versions, risk subjects/reviews, settlements, payouts, device credentials, entitlements and many partner/growth/reporting records.

### Security posture in backend config

Important production defaults and requirements visible in `backend/src/config/settings.py` and `backend/.env.example`:

- `REGISTRATION_ENABLED=false` and `REGISTRATION_INVITE_REQUIRED=true` by default;
- `SWAGGER_ENABLED=false` by default;
- `DEBUG=false`;
- JWT secret must be at least 32 characters;
- weak JWT secrets are rejected in production;
- `TOTP_ENCRYPTION_KEY` is required in production;
- OAuth token encryption key is required in production unless a reviewed fallback exists;
- rate-limit fail-open is false by default;
- CORS defaults to explicit configured origins;
- cookies default to secure;
- log sanitization is enabled.

---

## 7. Frontend surfaces

### `frontend/` customer product

Main areas:

- public marketing: pricing, features, devices, download, security, privacy, terms, trust, status, docs/guides/help;
- auth: login, register, verify, magic link, reset password, OAuth callback, Telegram link;
- protected dashboard: dashboard, servers, subscriptions, wallet, payment history, referral, settings, users, partner, analytics, monitoring;
- Telegram Mini App: home, plans, payments, devices, profile, referral, wallet;
- API routes for analytics, auth, OAuth and observability.

The current `docs/plans/2026-04-24-user-cabinet-frontend-integration-plan.md` states that the protected dashboard is technically wired to authenticated backend APIs, but still partly reads like an operator command center. Production customer launch should prioritize turning it into a customer-first cabinet.

### `admin/`

Standalone admin app runs by default on `localhost:3001`. Feature areas include:

- admin shell;
- commerce;
- customers;
- governance;
- growth;
- infrastructure;
- integrations;
- security;
- servers;
- analytics/observability routes.

Production origin in README: `https://admin.ozoxy.ru`.

### `partner/`

Standalone partner app runs by default on `localhost:3002`. Feature areas include:

- partner shell/workspace/state;
- storefront public surface;
- onboarding;
- commercial, finance, compliance, legal, operations, reporting;
- reseller settings;
- integrations;
- product intelligence through PostHog server-side bridge and same-origin browser event route.

Production origin in README: `https://partner.ozoxy.ru`.

### i18n

The web apps use locale-prefixed routing. In `frontend/src/i18n/config.ts`:

- default locale: `en-EN`;
- high priority: `en-EN`, `ru-RU`, `zh-CN`, `hi-IN`, `id-ID`, `vi-VN`, `th-TH`, `ja-JP`, `ko-KR`;
- medium priority: `ar-SA`, `fa-IR`, `tr-TR`, `ur-PK`;
- low/additional/fallback locales include `bn-BD`, `ms-MY`, `es-ES`, `kk-KZ`, `be-BY`, `my-MM`, `uz-UZ`, `ha-NG`, `yo-NG`, `ku-IQ`, `am-ET`, `fr-FR`, `tk-TM`, `zh-Hant`, `he-IL`, `de-DE`, `pt-PT`, `it-IT`, `nl-NL`, `pl-PL`, `fil-PH`, `uk-UA`, `cs-CZ`, `ro-RO`, `hu-HU`, `sv-SE`;
- RTL locales: `ar-SA`, `he-IL`, `fa-IR`, `ur-PK`, `ku-IQ`.

---

## 8. Telegram Mini App

Mini App files live under `frontend/src/app/[locale]/miniapp/`.

Current route coverage:

- home;
- plans;
- payments;
- devices;
- profile;
- referral;
- wallet;
- bottom navigation and shared components;
- tests for core pages/components.

The launch debt document `docs/plans/2026-04-22-miniapp-production-launch-and-stabilization-technical-debt.md` states:

- code-side launch package is considered ready for handoff;
- staging smoke, evidence pack, live Prometheus/Grafana proof, canary cutover and stabilization are still open because they require real environments and credentials.

Useful commands:

- `npm run conformance:miniapp-launch`;
- `npm run evidence:miniapp-launch:init -- <date> <environment> <run-id> <release-window> "<operator>"`;
- `npm run staging:miniapp-launch:smoke`.

---

## 9. Infrastructure and local runtime

### Local Docker Compose

`infra/docker-compose.yml` provides local/reference topology:

- Remnawave backend `remnawave/backend:2.7.4`;
- PostgreSQL `17.7` on localhost `6767`;
- Valkey `8.1` on localhost `6379`;
- daily Postgres backup container;
- CyberVPN worker and scheduler under `worker` profile;
- Helix adapter and Helix lab nodes under `helix` / `helix-lab` profiles;
- Caddy proxy profile;
- Remnawave subscription page profile;
- Telegram bot profile;
- Prometheus/Grafana/monitoring-related services.

Local endpoints from `infra/README.md`:

- Remnawave panel: `http://localhost:3000`;
- Remnawave metrics: `http://localhost:3001/metrics`;
- Postgres: `localhost:6767`;
- subscription page: `http://localhost:3010`;
- Prometheus: `http://localhost:9094`;
- Grafana: `http://localhost:3002`;
- Helix adapter: `http://localhost:8088/healthz`;
- Helix lab node: `http://localhost:8091/healthz`;
- Helix lab node 02: `http://localhost:8092/healthz`.

### Infrastructure target assets

Current infra scaffolds include:

- staging and production foundation/DNS/edge/control-plane Terraform/OpenTofu directories;
- staging OpenBao, NATS, PostHog and nonprod management cluster;
- production management cluster scaffold;
- scripts for OpenBao/NATS/PostHog bootstrap;
- scripts for platform GitOps bootstrap;
- scripts for control-plane observability/recovery;
- scripts for workload cluster, platform services, collector convergence, backups, workload delivery, event backbone, realtime delivery, control-plane workload migration, production cutover and conformance.

### GitOps

`platform-gitops/` currently mirrors the target GitOps repo shape for initial control-plane workload migration:

1. namespace;
2. backend;
3. task-worker;
4. task-scheduler.

---

## 10. Observability

Current observability surfaces:

- Sentry in frontend/admin/partner/backend/bot/worker/desktop/Helix services;
- Prometheus metrics in backend, bot, worker, Helix adapter/node and local infra;
- Grafana dashboards under `infra/grafana/dashboards/`;
- OpenTelemetry in backend;
- product intelligence through PostHog target scaffolding;
- conformance and governance CI for Sentry acceptance/privacy/release proof;
- runbooks for Mini App runtime observability, partner portal observability, control-plane backup/restore and production edge canary.

Important drift:

- older docs mention `promtail` and standalone `otel-collector`;
- platform inventory marks those as migration/retire surfaces;
- target direction is Alloy-oriented collector convergence and governed PostHog/NATS integration.

For launch claims, do not rely only on local dashboards. Archive release evidence:

- Sentry release visible;
- source maps uploaded where applicable;
- backend and frontend runtime events visible without PII leakage;
- Prometheus targets healthy;
- Grafana dashboards populated during staging smoke;
- alert routes verified.

---

## 11. CI, release and conformance

GitHub workflow files currently cover:

- Android TV CI/release;
- backend CI/security;
- frontend CI;
- admin/partner conformance;
- customer growth notification/reporting conformance and staging smoke;
- desktop client CI/release;
- Helix adapter/node CI;
- infrastructure CI;
- mobile CI/release;
- node-fleet-controller CI;
- platform workload delivery;
- Sentry acceptance/governance/privacy/release-proof;
- task-worker and telegram-bot CI;
- Verta UDP verification/release evidence.

Root npm scripts expose major gates:

- `npm run build`, `npm run lint`;
- `npm run build:admin`, `npm run lint:admin`;
- `npm run build:partner`, `npm run lint:partner`;
- `npm run conformance:partner-admin`;
- `npm run conformance:partner-observability`;
- `npm run conformance:miniapp-launch`;
- `npm run conformance:customer-growth-notifications`;
- `npm run conformance:customer-growth-reporting-governance`;
- staging smoke commands for partner/admin, Mini App, customer growth notification/reporting governance.

---

## 12. Current readiness by component

| Component | Current posture | Launch interpretation |
|---|---|---|
| `frontend` customer web | strong implementation base, many tests, but cabinet IA still partly operator-oriented | launch after customer-first cabinet gate and staging smoke |
| Telegram Mini App | code-side launch package marked ready, live evidence still open | good candidate for early staged launch after real staging proof |
| `admin` | standalone app with growth/governance/infrastructure/admin features | use internally first; do not expose broadly before RBAC/security evidence |
| `partner` | large partner portal/storefront surface with PostHog/product intelligence work | later launch phase after core paid VPN is stable |
| `backend` | broad API and domain model, security defaults present | central launch blocker; needs staging/prod env, migrations, secrets, payment verification |
| Telegram bot | production-shaped aiogram service with payments/trial/referral env | good early channel, but must validate provider credentials and backend integration |
| task-worker/scheduler | production-shaped worker for async jobs | required for email, notifications, reporting, reconciliation |
| Remnawave | local baseline pinned to `2.7.4` with runbooks | required VPN authority; upgrade/edge runbooks must be followed |
| Helix | advanced lab/private transport stack | not required for first paid MVP; launch as beta/lab/canary later |
| mobile app | broad Flutter app, secure storage, tests, VPN package override | later beta/release track after backend and subscriptions stable |
| desktop client | Tauri app with release/smoke gates and Helix diagnostics | later beta track, especially for Helix |
| Android TV | Kotlin/Compose app with VPN service/parser/local state | later device expansion track |
| infra/GitOps | extensive target-state scaffolding | migrate gradually; first launch can use simpler controlled topology if gates are explicit |

---

## 13. Recommended phased live launch

### Phase 0: freeze and launch governance

Goal: stop uncontrolled drift before live launch.

Required:

- pick a release branch or launch branch;
- decide which surfaces are in the first live launch: recommended MVP is `frontend` customer cabinet + backend + Telegram bot/Mini App + Remnawave;
- freeze production domains and subdomains;
- inventory all `.env` and secrets;
- choose staging/prod deployment authority for Phase 1;
- create release owner, incident owner and rollback owner roles;
- define evidence archive path in `docs/evidence/`;
- run current conformance gates on a clean branch if possible.

Exit gate:

- documented MVP scope;
- no unknown production secrets;
- staging environment exists or is scheduled;
- launch checklist has named owners.

### Phase 1: staging foundation

Goal: prove backend, web, bot, worker and Remnawave integration in staging.

Required:

- deploy backend with real staging PostgreSQL/Valkey;
- deploy frontend customer app with same-origin API routing;
- deploy admin internally;
- deploy worker/scheduler;
- connect Remnawave staging API;
- configure Sentry release/environment for every deployed runtime;
- configure Prometheus/Grafana targets;
- run backend migrations;
- validate auth, registration/invite mode, OTP/magic link, Telegram login;
- validate VPN config provisioning;
- run Mini App staging smoke;
- archive logs, screenshots, dashboard evidence and command transcripts.

Exit gate:

- staging smoke passes;
- errors observable in Sentry;
- metrics visible;
- VPN config can be issued and used by a test account;
- rollback path tested.

### Phase 2: closed beta / invite-only launch

Goal: run real users under controlled access.

Recommended scope:

- customer cabinet;
- Telegram Mini App;
- Telegram bot;
- basic subscription/trial;
- limited payment provider set, ideally one primary and one fallback;
- manual support path;
- limited server regions.

Required:

- keep registration invite-gated;
- use production-like secrets and cookie settings;
- run payment sandbox or low-volume live payment tests;
- validate refund/dispute operational procedure;
- verify email/Telegram notifications;
- run customer support escalation path;
- monitor Sentry, API latency, provisioning failures and payment failures daily.

Exit gate:

- no critical auth/payment/provisioning defects during beta window;
- support can resolve failed provisioning;
- payment reconciliation is understood;
- backup/restore procedure has at least nonprod evidence.

### Phase 3: paid MVP public launch

Goal: sell VPN subscriptions publicly with controlled risk.

Recommended scope:

- public marketing/pricing pages;
- customer cabinet;
- Telegram bot and Mini App;
- production backend;
- Remnawave production nodes;
- subscriptions, trial, wallet/payment history;
- referral/promo only if anti-abuse and reporting are verified;
- admin internal operations.

Defer:

- broad partner marketplace;
- Helix as default path;
- mobile app store launch if VPN/backend payment lifecycle is not proven;
- aggressive multi-locale paid acquisition until support/legal are ready.

Exit gate:

- production canary succeeds;
- first stabilization window complete;
- payment/provider dashboards reconcile with backend records;
- support and refund process works;
- production rollback is documented and tested where feasible.

### Phase 4: growth and partner program

Goal: activate acquisition/partner mechanics after core product is stable.

Scope:

- invite/referral/promo/gift/growth code lifecycle;
- partner portal;
- storefronts;
- attribution;
- statements, payouts, settlement periods;
- customer growth notifications and reporting governance;
- PostHog product intelligence;
- NATS/outbox/realtime convergence as needed.

Exit gate:

- conformance runs pass for partner/admin and growth packages;
- anti-abuse/risk review process is operational;
- payout/settlement dry-run evidence exists;
- partner observability runbook is executable.

### Phase 5: client expansion

Goal: expand beyond web/Telegram.

Tracks:

- Flutter mobile app internal testing, then closed testing/store rollout;
- desktop client beta;
- Android TV beta;
- Helix lab/canary rollout for selected users;
- browser extension only after it becomes a real app, currently it is a placeholder.

Exit gate:

- app-specific release workflows pass;
- native crash reporting is verified;
- VPN connect/disconnect/recovery works on target OS versions;
- privacy/security review passes per platform.

### Phase 6: platform maturity

Goal: move from launch-capable to operator-resilient.

Scope:

- OpenBao production secrets;
- GitOps/Flux workload promotion;
- Kubernetes/Talos management and workload clusters;
- CloudNativePG/backup/restore;
- NATS event backbone;
- Alloy collector convergence;
- Node Fleet Controller for edge lifecycle;
- production drills and conformance scorecards.

Exit gate:

- production drills completed;
- Gate D or equivalent scorecard accepted;
- incident response and DR evidence archived;
- manual deployment paths retired or explicitly exception-tracked.

---

## 14. Launch-critical risks

### Highest priority risks

1. **Dirty worktree and high drift.** `git status` currently shows many modified and untracked files across backend, frontend, admin, partner, infra, docs and apps. Before a real launch, freeze a branch and separate launch-critical work from experimental changes.
2. **Existing overview docs are partially stale.** The platform inventory marks broad old docs as needing migration because they encode older observability/runtime assumptions.
3. **Secrets are still local/env-file oriented in several surfaces.** Production should not depend on workstation-local `.env` files.
4. **Live evidence is missing for some completed code packages.** Mini App docs explicitly say production launch proof requires real staging/prod credentials and release window.
5. **Customer cabinet IA still needs final launch shaping.** Current frontend has strong functionality but needs customer-first cockpit readiness before public launch.
6. **Payment providers need real integration proof.** CryptoBot, Telegram Stars and YooKassa appear in config, but launch requires actual provider accounts, webhook verification, reconciliation and refund procedure.
7. **Observability must be proven live.** Sentry/Prometheus/Grafana code exists, but production claims require release evidence.
8. **Partner/growth systems increase abuse and financial risk.** Launch those after core paid VPN is stable.
9. **Helix is advanced but should not block MVP.** Treat it as later beta/canary unless your business launch explicitly depends on it.

### Security and privacy checklist before production

- `ENVIRONMENT=production`;
- `DEBUG=false`;
- `SWAGGER_ENABLED=false`;
- production JWT secret, TOTP encryption key and OAuth token encryption key;
- production CORS origin list;
- secure cookie settings and correct domain;
- no secrets in frontend bundle or Flutter assets;
- Sentry PII scrubbing verified;
- OAuth redirect allowlist reviewed;
- Telegram bot internal secret configured;
- Remnawave webhook secret separated from Remnawave token;
- rate limits fail closed in production;
- backup/restore verified;
- access logs and support tooling avoid leaking tokens/config URLs.

---

## 15. Commands that matter

### Root web commands

```bash
npm install
npm run dev
npm run dev:admin
npm run dev:partner
npm run build
npm run build:admin
npm run build:partner
npm run lint
npm run lint:admin
npm run lint:partner
```

### Frontend commands

```bash
cd frontend
npm run dev
npm run build
npm run lint
npm run test:run
npm run check:mobile
npm run check:seo
```

### Local infra

```bash
cd infra
docker compose up -d
docker compose --profile worker up -d
docker compose --profile bot up -d
docker compose --profile monitoring up -d
docker compose --profile helix-lab --profile monitoring --profile worker up -d
```

### Conformance and smoke

```bash
npm run conformance:miniapp-launch
npm run staging:miniapp-launch:smoke
npm run conformance:partner-admin
npm run conformance:partner-observability
npm run conformance:customer-growth-notifications
npm run conformance:customer-growth-reporting-governance
```

### Native clients

```bash
cd apps/desktop-client
npm run test
npm run test:release-gate
npm run smoke:release
```

```bash
cd cybervpn_mobile
flutter test
```

```bash
cd apps/android-tv
./gradlew test
```

---

## 16. Recommended immediate next actions

1. Create a launch branch and stop mixing product launch work with platform experiments.
2. Decide MVP launch scope: recommended first live scope is backend + frontend customer cabinet + Telegram Mini App/bot + Remnawave + worker.
3. Run and archive `npm run conformance:miniapp-launch`.
4. Execute the user cabinet Phase 0/1 plan from `docs/plans/2026-04-24-user-cabinet-frontend-integration-plan.md`.
5. Build a staging environment with real secrets and staging payment credentials.
6. Run Mini App staging smoke and archive evidence.
7. Validate auth/payment/provisioning end to end with a real test user.
8. Set production gates: security, observability, backup/restore, rollback, support and payment reconciliation.
9. Launch invite-only beta before public paid traffic.
10. Only after stabilization, activate partner/growth/client expansion.

---

## 17. Source documents and files reviewed

Key local sources used for this dossier:

- `README.md`;
- `AGENTS.md`;
- `package.json`;
- `frontend/package.json`;
- `frontend/next.config.ts`;
- `frontend/src/i18n/config.ts`;
- `frontend/src/proxy.ts`;
- `admin/package.json`, `admin/README.md`, `admin/src/proxy.ts`;
- `partner/package.json`, `partner/README.md`, `partner/src/proxy.ts`;
- `backend/pyproject.toml`;
- `backend/.env.example`;
- `backend/src/config/settings.py`;
- `backend/src/main.py`;
- `backend/src/presentation/api/v1/router.py`;
- `services/telegram-bot/pyproject.toml`;
- `services/telegram-bot/.env.example`;
- `services/task-worker/pyproject.toml`;
- `services/task-worker/.env.example`;
- `services/helix-adapter/README.md`;
- `services/helix-node/README.md`;
- `apps/desktop-client/package.json`;
- `apps/desktop-client/README.md`;
- `cybervpn_mobile/pubspec.yaml`;
- `apps/android-tv/gradle/libs.versions.toml`;
- `apps/browser-extension/package.json`;
- `packages/helix-contract/package.json`;
- `infra/docker-compose.yml`;
- `infra/README.md`;
- `platform-gitops/README.md`;
- `docs/project-audit-2026-02-14.md`;
- `docs/plans/2026-04-21-platform-foundation-monorepo-inventory.md`;
- `docs/plans/2026-04-22-miniapp-production-launch-and-stabilization-technical-debt.md`;
- `docs/plans/2026-04-24-user-cabinet-frontend-integration-plan.md`;
- `docs/runbooks/*`;
- `.github/workflows/*`.

---

## 18. Final launch posture

CyberVPN is best treated as a **multi-phase commercial VPN platform**, not as a single app release.

For the first live launch, keep the product narrow:

- sell and provision VPN access reliably;
- support users quickly;
- observe every critical path;
- keep registration/payment/provisioning controlled;
- defer partner/growth/native-client/Helix breadth until the core subscription business survives real traffic.

The repository already contains many of the right building blocks. The remaining work is less about inventing more features and more about **freezing scope, proving live operations, controlling secrets, reducing launch surface area, and collecting evidence for each gate before widening traffic.**
