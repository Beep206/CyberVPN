# Frontend SEO / GEO / AEO Growth Plan

**Date:** 2026-03-30

**Goal:** превратить публичный frontend в сильный acquisition-канал, который:
- стабильно индексируется поисковиками;
- хорошо цитируется и понимается AI/search-системами;
- приводит не просто трафик, а регистрации, trial-активации и покупки.

**Primary domain assumption:** `https://vpn.ozoxy.ru`

**Scope:** `frontend/`, публичные маркетинговые страницы, metadata, i18n, sitemap/robots, content architecture, structured data, CWV, analytics, conversion layer.

## 1. Executive Summary

Сейчас у проекта уже есть сильная база для роста:
- Next.js App Router;
- статическая/partial prerender сборка;
- много публичных маркетинговых страниц;
- базовый JSON-LD;
- Web Vitals telemetry через Sentry;
- help/docs/pricing/security/download/network как зачатки content surface.

Но в текущем состоянии frontend не готов к агрессивному SEO/GEO/AEO росту. Главные причины:
- критические ошибки в canonical/hreflang;
- некорректные `robots` и `sitemap`;
- публичные test/debug маршруты;
- слишком много client-side bailout на маркетинговых страницах;
- слабая keyword/intent ориентация metadata и visible copy;
- 39 локалей без жёсткой стратегии качества и приоритизации;
- мало trust/entity signals для ниши privacy/security;
- слабая измеримость SEO-to-conversion цепочки.

Если коротко: сначала надо вылечить индексацию и HTML-семантику, потом перевести маркетинг в server-first knowledge surface, потом расширять контентные кластеры и authority layer. Иначе любой контент-маркетинг и линкбилдинг будут литься в дырявое ведро.

## 2. What I Found In The Current Frontend

### 2.1 Critical technical issues

- `frontend/src/app/sitemap.ts`
  - используется `https://vpn-admin.example.com`, а не `https://vpn.ozoxy.ru`;
  - в sitemap попадают только `/{locale}/`, `/{locale}/login`, `/{locale}/register`;
  - реальные маркетинговые URL (`/pricing`, `/features`, `/download`, `/help`, `/docs`, `/security`, `/network`, `/status`, `/contact`) туда не попадают.

- `frontend/src/app/robots.ts`
  - `sitemap` указывает на `https://vpn-admin.example.com/sitemap.xml`;
  - `disallow: ['/dashboard/', '/miniapp/']` не соответствует реальным locale-prefixed путям вида `/{locale}/dashboard`;
  - фактически служебные и приватные разделы не защищены от индексации так, как команда, вероятно, ожидает.

- `frontend/src/app/[locale]/layout.tsx`
  - canonical всегда `/${locale}`;
  - `alternates.languages` тоже указывают только на locale root;
  - для дочерних страниц это означает, что `/en-EN/help`, `/en-EN/docs`, `/en-EN/pricing`, `/en-EN/security` и другие страницы получают canonical на `/en-EN`, что очень плохо для индексации и распределения relevance.

- `frontend/src/app/layout.tsx`
  - `<html lang="en">` захардкожен;
  - для многоязычного сайта это ломает корректный языковой сигнал на уровне документа;
  - `WebSite` JSON-LD содержит `SearchAction` на `/search`, но такого route сейчас нет.

- `frontend/src/app/[locale]/test-animation/page.tsx`
- `frontend/src/app/[locale]/test-error/page.tsx`
  - публичные тестовые маршруты собираются в production по всем локалям;
  - build подтвердил, что они реально пререндерятся и могут расходовать crawl budget.

### 2.2 Render/crawl issues

- Продакшен build показал `1846` сгенерированных страниц.
- Для `en-EN` минимум `22` публичных/auth страниц содержат `BAILOUT_TO_CLIENT_SIDE_RENDERING`, включая:
  - `api.html`
  - `contact.html`
  - `docs.html`
  - `download.html`
  - `features.html`
  - `help.html`
  - `network.html`
  - `pricing.html`
  - `privacy.html`
  - `security.html`
  - `status.html`
  - `terms.html`
  - а также auth routes.

Это значит, что значимая часть acquisition surface не отдаёт плотный, чистый, server-rendered HTML слой как базовый источник истины. Для SEO это не всегда фатально, но для AI citation, crawl efficiency и стабильности snippet extraction это слабая архитектура.

### 2.3 Content/metadata issues

- Titles и descriptions сейчас брендово-стилизованные, но часто слабо заточены под реальный query intent:
  - `ACCESS TIERS`
  - `Core Capabilities`
  - `Neural Archives`
  - `Global Infrastructure`
  - `TRANSPARENCY PROTOCOL`
- Это хорошо для visual identity, но слабо для захвата реальных запросов и для понятности AI systems.

- Hero на landing уже содержит сильные смыслы (`VLESS-REALITY`, `bypass DPI`, `HTTPS masquerade`), но visible copy и metadata пока не разложены по полноценным intent clusters:
  - продуктовые;
  - use-case;
  - device/platform;
  - comparison;
  - educational/how-to.

- `frontend/src/widgets/landing-hero.tsx`
  - primary CTAs рендерятся через `<Button>`, а не через crawlable `<a>`/`Link`;
  - это плохо и для internal link graph, и для аналитики CTA-path, и для прозрачности пользовательского пути.

- `frontend/src/widgets/footer.tsx`
  - social links сейчас `href: '#'`;
  - это снижает trust и entity clarity.

### 2.4 International SEO issues

- `frontend/src/i18n/config.ts` содержит `39` локалей.
- В конфиге прямо есть группа, помеченная как "Нежизнеспособные (но требуются)".
- Для SEO это красный флаг: если локали отдаются публично, но не поддерживаются качественным контентом, то мы масштабируем thin/weak variants.
- Сейчас также отсутствует `x-default` fallback strategy.

### 2.5 Trust and conversion issues

Для ниши privacy/security/VPN мало просто быть красивыми. Нужны доказательные trust signals:
- понятная identity;
- прозрачные policy pages;
- audit / methodology / evidence pages;
- реальные контактные данные и соцссылки;
- понятные pricing/comparison claims;
- machine-readable entity data;
- чёткий переход из search intent в trial/purchase.

Сейчас frontend выглядит сильно как product experience, но ещё не как search-first trust asset.

## 3. Strategic Principles

### 3.1 Не гонимся сразу за head terms

Запросы вроде `best vpn`, `free vpn`, `vpn app` перегреты и обычно забиты крупными review-сайтами, агрегаторами и брендами с огромной link authority.

Начинать нужно с кластеров, где у CyberVPN есть реальное product differentiation:
- `VLESS Reality VPN`
- `DPI bypass VPN`
- `VPN for Telegram`
- `RAM-only no logs VPN`
- `how to bypass censorship with VPN`
- `VPN for Windows / Android / iPhone / macOS`
- `VPN kill switch`
- `VPN without logs`
- `how VLESS Reality works`
- `WireGuard vs VLESS Reality`

### 3.2 SEO, GEO и AEO здесь одна задача

Для этого проекта нет смысла разделять:
- классический SEO;
- AI recommendation / citation;
- answer engine optimization.

Практически это один и тот же фундамент:
- crawlable HTML;
- корректная metadata;
- сильная internal linking graph;
- structured data;
- trustworthy entity layer;
- snippet-friendly content;
- быстрые страницы;
- доступная и понятная семантика.

### 3.3 Marketing pages должны быть server-first, effects second

3D, motion, scramble, smooth scroll и cyberpunk-оформление можно сохранить.
Но они не должны быть причиной того, что:
- основной контент отсутствует в HTML;
- help/docs/faq не видны без hydration;
- важные CTA теряют link semantics;
- Core Web Vitals уходят в красную зону.

### 3.4 Не индексируем всё подряд

Надо жёстко разделить:

**Indexable acquisition surface**
- home
- pricing
- features
- download
- security
- privacy
- network
- status
- docs
- help
- contact
- будущие guides / comparisons / device pages / use-case pages

**Non-indexable / protected surface**
- dashboard
- miniapp
- auth flows
- oauth callbacks
- verify/reset/magic-link
- test/debug routes
- любые чисто transactional/utility pages без search value

## 4. Priority Workstreams

## 4.1 Workstream A: Crawl Control And Index Hygiene

**Priority:** P0

### Objectives

- убрать мусор и конфликты из индекса;
- сделать robots/sitemap соответствующими реальной routing-модели;
- перестать каннибализировать все страницы на locale root canonical.

### Required changes

- Переписать `frontend/src/app/sitemap.ts`:
  - использовать `SITE_URL`;
  - включать все indexable public routes;
  - исключать dashboard/miniapp/auth/test routes;
  - проставлять page-specific `lastModified`;
  - при необходимости разбить на sitemap index + child sitemaps по локалям или типам страниц.

- Переписать `frontend/src/app/robots.ts`:
  - боевой домен в `sitemap`;
  - locale-aware `disallow`;
  - при необходимости отдельные правила под specific bots;
  - сверить с OpenAI/Google crawl policy.

- Добавить `robots` metadata per route:
  - `index: false` для auth/test/utility страниц;
  - `index: true` только для страниц с реальным acquisition intent.

- Убрать или закрыть:
  - `frontend/src/app/[locale]/test-animation/page.tsx`
  - `frontend/src/app/[locale]/test-error/page.tsx`

### Success criteria

- в индексе остаются только целевые public pages;
- no unwanted test/auth/dashboard URLs in Search Console;
- sitemap отражает реальную публичную архитектуру;
- crawl budget не тратится на служебные страницы.

## 4.2 Workstream B: Canonical, Hreflang, Locale Correctness

**Priority:** P0

### Objectives

- у каждой публичной страницы должен быть свой canonical;
- hreflang должен указывать на page-equivalent alternate, а не на locale root;
- документ должен отдавать корректный `lang` и `dir`.

### Required changes

- Пересобрать metadata model:
  - `frontend/src/shared/lib/site-metadata.ts`
  - `frontend/src/app/[locale]/layout.tsx`
  - все `generateMetadata` в `frontend/src/app/[locale]/(marketing)/*/page.tsx`

- Для каждого indexable route:
  - canonical = полный URL именно этой страницы;
  - alternates.languages = full page equivalents на других локалях;
  - добавить `x-default`.

- Исправить `<html lang>` и `dir`:
  - root layout должен стать locale-aware;
  - RTL локали должны отдавать правильный `dir`.

- Сократить публичный crawl surface по локалям:
  - выделить tier-1 локали;
  - пока локаль не поддержана качественным human-reviewed контентом, не включать её в indexable growth surface.

### Success criteria

- `/en-EN/help` canonicalizes to `/en-EN/help`, а не `/en-EN`;
- hreflang корректен для каждой страницы;
- locale root не каннибализирует дочерние страницы;
- Google Search Console не показывает canonical conflicts по основным money pages.

## 4.3 Workstream C: Server-First Marketing Rendering

**Priority:** P0/P1

### Objectives

- вернуть marketing/help/docs pages к server-readable HTML;
- сохранить визуальный стиль, но убрать зависимость search value от hydration.

### Required changes

- Найти и устранить верхнеуровневые причины `BAILOUT_TO_CLIENT_SIDE_RENDERING`:
  - `frontend/src/app/[locale]/(marketing)/layout.tsx`
  - `frontend/src/app/providers/smooth-scroll-provider.tsx`
  - `frontend/src/widgets/help-faq.tsx`
  - `frontend/src/widgets/help-categories.tsx`
  - `frontend/src/widgets/docs-container.tsx`
  - `frontend/src/widgets/docs-content.tsx`
  - `frontend/src/widgets/contact-form.tsx`
  - dashboard-like interactive widgets внутри marketing routes.

- Принцип:
  - hero/title/description/FAQ answers/guides/feature copy должны существовать в HTML без JS;
  - motion/3D/interactive controls должны быть progressive enhancement;
  - heavy scenes должны быть deferred below fold or idle.

- Для help/docs:
  - отдать knowledge content как server-rendered sections;
  - интерактивные фильтры и animated viewers оставить клиентскими поверх уже существующего HTML.

- Для landing/features/pricing/download/security/network/status:
  - вынести critical copy в server components;
  - client widgets использовать там, где они реально добавляют UX, а не где они держат весь смысл страницы.

### Success criteria

- HTML маркетинговых страниц содержит основной контент без hydration;
- help/docs/faq читаемы и цитируемы ботами;
- CWV не ухудшаются из-за 3D и motion;
- не менее 90% acquisition pages обходятся без top-level bailout.

## 4.4 Workstream D: Metadata Rewrite For Search Intent

**Priority:** P1

### Objectives

- переписать titles, descriptions, H1 и intro paragraphs под реальный спрос;
- сохранить cyberpunk-tone в UI, но не жертвовать ясностью для search/AI.

### Rules

- metadata должна отвечать на вопрос: "по какому намерению мы хотим ранжироваться?"
- H1 и первый экран должны за 3-5 секунд объяснять:
  - что это;
  - для кого;
  - почему лучше альтернатив;
  - что делать дальше.

### Example direction

Вместо:
- `ACCESS TIERS`

Нужно что-то ближе к:
- `VPN Pricing Plans | Free Trial, No-Logs, VLESS Reality | CyberVPN`

Вместо:
- `Core Capabilities`

Нужно:
- `VPN Features | No-Logs, Kill Switch, RAM-Only Servers, DPI Bypass`

Вместо:
- `Neural Archives`

Нужно:
- `VPN Help Center | Setup, Troubleshooting, Billing, Security`

### Pages to rewrite first

- landing `/`
- `/pricing`
- `/features`
- `/download`
- `/help`
- `/docs`
- `/security`
- `/network`
- `/privacy`
- `/status`

### Success criteria

- каждый title/description/H1 отражает intent, а не только стиль;
- CTR по brand + non-brand queries растёт;
- AI systems получают короткие, понятные, quoteable summaries.

## 4.5 Workstream E: Information Architecture For Organic Growth

**Priority:** P1

### Objectives

- построить hub-and-spoke структуру;
- перестать зависеть только от нескольких showcase pages;
- покрыть решение пользователя по всему funnel.

### Future content architecture

**Money pages**
- Home
- Pricing
- Features
- Download
- Security
- Privacy
- Network

**Trust pages**
- No-logs policy
- Independent audit / security methodology
- Refund policy
- Payment methods
- Company / contact / support SLA
- Why trust CyberVPN

**Device pages**
- VPN for Windows
- VPN for macOS
- VPN for Android
- VPN for iPhone / iOS
- VPN for Linux

**Use-case pages**
- VPN for Telegram
- VPN for bypassing DPI
- VPN for streaming
- VPN for gaming
- VPN for public Wi-Fi
- VPN for travel / censorship-heavy regions

**Comparison pages**
- VLESS Reality vs WireGuard
- VLESS Reality vs OpenVPN
- CyberVPN vs generic no-logs VPN
- RAM-only VPN vs traditional VPN infrastructure

**Educational pages**
- What is VLESS Reality
- How DPI blocking works
- What no-logs really means
- What a kill switch does
- How to choose a VPN safely

### Success criteria

- сайт покрывает commercial + informational + comparison intent;
- появляется естественная внутренняя перелинковка между explanation pages и money pages;
- AI systems получают больше страниц, которые удобно цитировать по конкретным вопросам.

## 4.6 Workstream F: Structured Data And Entity Layer

**Priority:** P1

### Objectives

- дать машинам факты, а не только стилизованный copy;
- усилить понимание бренда, продукта и страницы.

### Required structured data

- `Organization` or `OnlineStore`
  - name
  - logo
  - url
  - sameAs
  - support/contact points
  - legal identity where possible

- `WebSite`
  - оставить только если есть реальный search endpoint;
  - иначе убрать `SearchAction`.

- `BreadcrumbList`
  - на всех marketing/content pages.

- `FAQPage`
  - на help/pricing/support pages, если markup полностью соответствует visible content.

- `SoftwareApplication`
  - для download/device pages.

- `Product` / `Offer`
  - для pricing, если бизнес-структура и checkout это позволяют.

- `HowTo`
  - для setup/tutorial pages.

- `Article`
  - для будущих guides/comparison pages.

### Validation

- Rich Results Test;
- Search Console enhancement reports;
- manual URL inspection.

### Success criteria

- структурированные данные валидны;
- schema соответствует реальному visible content;
- knowledge extraction для поисковиков и AI становится устойчивее.

## 4.7 Workstream G: GEO / AEO / AI Citation Optimization

**Priority:** P1

### Objectives

- сделать сайт удобным для цитирования, summarization и recommendation engines;
- не опираться на мифические "секретные AI hacks".

### Practical rules

- писать краткие factual answer blocks в начале секций;
- использовать таблицы, списки, сравнения, glossary blocks;
- добавлять "what it is / why it matters / when to use / limitations";
- делать claims доказуемыми;
- помечать даты обновления;
- указывать authorship / review ownership там, где это уместно;
- повышать accessibility и ARIA quality;
- не блокировать `OAI-SearchBot`, если страницы должны цитироваться ChatGPT;
- отдельно управлять GPTBot policy, если нужна развязка между discovery и training.

### AI-ready page format

Каждая важная knowledge page должна содержать:
- 1 короткий summary paragraph;
- 3-7 bullet answers;
- comparison or decision table;
- links на next-step money pages;
- structured data, если уместно;
- last updated;
- explicit scope and caveats.

### What not to do

- не делать `llms.txt` основным проектом;
- не уповать на keyword stuffing;
- не заворачивать ответный контент в красивые, но client-only терминалы;
- не плодить десятки weak pages без entity/supporting evidence.

### Success criteria

- ChatGPT/AI search referral traffic измеряется;
- help/docs/use-case pages начинают приносить non-brand traffic;
- страницы становятся удобными для цитирования в ответах.

## 4.8 Workstream H: Core Web Vitals And Page Experience

**Priority:** P1

### Objectives

- закрепить good page experience по главным acquisition pages;
- не давать 3D/motion ломать LCP/INP/CLS.

### Budgets

- LCP < 2.5s
- INP < 200ms
- CLS < 0.1

### Required changes

- критический контент и CTA рендерить server-first;
- heavy 3D scenes:
  - lazy load;
  - below the fold where possible;
  - reduced-motion fallback;
  - mobile-specific downgrade.

- отключить ненужный smooth scroll на low-end/mobile contexts;
- не допускать, чтобы decorative widgets были LCP candidates;
- выделить performance budgets на:
  - hero
  - pricing
  - download
  - help/docs

- соединить Sentry Web Vitals с route-level reporting и SEO dashboard.

### Success criteria

- marketing routes выходят в зелёную зону по field data;
- LCP перестаёт зависеть от декоративных слоёв;
- mobile organic landing pages не проигрывают из-за эстетики.

## 4.9 Workstream I: Conversion Architecture

**Priority:** P1

### Objectives

- сделать organic/AI traffic конвертируемым;
- убрать разрывы между content intent и next action.

### Required changes

- `frontend/src/widgets/landing-hero.tsx`
  - заменить primary CTA на реальные `Link`/`a`;
  - дать понятные destination URLs.

- `frontend/src/widgets/footer.tsx`
  - заполнить реальные social/entity links;
  - превратить newsletter / updates block в рабочий conversion asset или убрать.

- На каждой money/information page добавить явный next step:
  - try free
  - view pricing
  - download app
  - open Telegram bot
  - compare protocols

- Между help/docs/security/use-case pages и conversion pages построить внутренние CTA-мосты.

- Для pricing:
  - акцент на trial / best plan / social proof / FAQs / refund clarity.

- Для download:
  - platform pages;
  - install steps;
  - checksums / version history / release notes;
  - why download from CyberVPN.

### Success criteria

- растёт CTA CTR с landing/help/docs;
- растёт trial activation from organic;
- органика перестаёт быть "информационным трафиком без денег".

## 4.10 Workstream J: Measurement And Attribution

**Priority:** P0/P1

### Current gap

`frontend/src/lib/analytics/index.ts` сейчас даёт interface, но без реального production provider это почти пустой слой.

### Required stack

- Google Search Console
- Bing Webmaster Tools
- GA4
- product analytics provider for funnel events
- Sentry for CWV/performance
- utm normalization

### Must-track dashboards

**SEO**
- indexed pages
- excluded pages
- impressions
- clicks
- CTR
- avg position
- branded vs non-branded traffic
- route-group traffic

**AI / referral**
- `utm_source=chatgpt.com`
- AI-assistant referral sessions
- landing page to signup conversion from AI referrals

**Conversion**
- home CTA click-through
- pricing to checkout
- docs/help to trial
- download to install
- install to activation

**Content**
- top landing pages
- low CTR pages
- low conversion pages
- pages with impressions but weak click yield

### Success criteria

- SEO and product metrics соединены;
- видно, какие страницы дают не только трафик, но и деньги;
- AI referrals отслеживаются отдельно.

## 5. 30 / 60 / 90 Day Roadmap

## Phase 0: Emergency Fixes (48-72 hours)

**Goal:** прекратить SEO self-harm.

- Исправить `robots.ts`
- Исправить `sitemap.ts`
- Ввести noindex для auth/test/utility
- Убрать public test pages из prod surface
- Исправить canonical/hreflang architecture
- Убрать fake `SearchAction` или реализовать реальный search route
- Подключить Search Console / Bing Webmaster / GA4

**Expected outcome**
- индекс перестаёт засоряться;
- исчезают самые опасные canonical conflicts;
- search systems получают корректную crawl map.

## Phase 1: Technical SEO Foundation (Week 1-2)

**Goal:** сделать indexable pages корректными и machine-readable.

- Сделать locale-aware `lang` / `dir`
- Устранить top-level CSR bailout на help/docs/pricing/download/features/network/security
- Переписать metadata и H1/intro для 8-10 core pages
- Добавить page-specific OG/Twitter assets
- Ввести `BreadcrumbList` + базовые page schemas
- Исправить CTA links и footer entity links

**Expected outcome**
- страницы начинают выглядеть как search assets, а не только как app showcase.

## Phase 2: Content Surface Expansion (Week 3-6)

**Goal:** расширить intent coverage.

- Запустить device pages
- Запустить use-case pages
- Запустить comparison pages
- Развернуть SSR help/docs knowledge pages с отдельными slug-структурами
- Добавить HowTo / FAQ / SoftwareApplication / Product/Offer schemas where appropriate
- Встроить internal linking graph

**Expected outcome**
- появляется long-tail coverage;
- органика начинает расти не только по бренду.

## Phase 3: Authority And Conversion Program (Week 7-12)

**Goal:** укрепить trust и превратить трафик в выручку.

- Добавить trust center / audit / methodology / transparency pages
- Раскатать локали по tier-модели, а не all-at-once
- Запустить CRO experiments на landing/pricing/download/help
- Настроить регулярное обновление контента
- Начать monthly refresh program по топовым страницам

**Expected outcome**
- растут quality signals, AI citability и conversion rate.

## 6. KPI Board

## Technical SEO KPIs

- 100% intended public pages имеют correct canonical
- 100% intended public pages имеют page-specific hreflang
- 0 indexed test/debug pages
- 0 indexed dashboard/miniapp/auth utility pages
- 100% public marketing pages в актуальном sitemap
- 0 critical structured data errors

## Performance KPIs

- p75 LCP < 2.5s
- p75 INP < 200ms
- p75 CLS < 0.1
- no top-level CSR bailout on core acquisition pages

## Search KPIs

- рост non-brand impressions
- рост CTR на core pages
- рост clicks on pricing/download/help/docs
- рост traffic share from long-tail informational and comparison queries

## AI / GEO KPIs

- рост sessions с `utm_source=chatgpt.com`
- рост AI referral landing pages
- рост conversion from AI referral traffic

## Business KPIs

- organic -> registration conversion rate
- organic -> trial activation rate
- organic -> purchase conversion rate
- docs/help -> signup assist rate
- pricing page CVR

## 7. Recommended File Map For Implementation

### P0 file set

- `frontend/src/app/sitemap.ts`
- `frontend/src/app/robots.ts`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/[locale]/layout.tsx`
- `frontend/src/shared/lib/site-metadata.ts`
- `frontend/src/app/[locale]/test-animation/page.tsx`
- `frontend/src/app/[locale]/test-error/page.tsx`
- all `generateMetadata` under `frontend/src/app/[locale]/(marketing)/`

### P1 file set

- `frontend/src/widgets/landing-hero.tsx`
- `frontend/src/widgets/footer.tsx`
- `frontend/src/widgets/help-faq.tsx`
- `frontend/src/widgets/help-categories.tsx`
- `frontend/src/widgets/docs-container.tsx`
- `frontend/src/widgets/docs-content.tsx`
- `frontend/src/widgets/pricing/*`
- `frontend/src/widgets/download/*`
- `frontend/src/widgets/features/*`
- `frontend/src/widgets/security/*`
- `frontend/src/widgets/servers/*`
- `frontend/src/app/providers/smooth-scroll-provider.tsx`

### Content source files

- `frontend/messages/en-EN/landing.json`
- `frontend/messages/en-EN/Features.json`
- `frontend/messages/en-EN/Pricing.json`
- `frontend/messages/en-EN/HelpCenter.json`
- `frontend/messages/en-EN/Network.json`
- `frontend/messages/en-EN/Privacy.json`
- `frontend/messages/en-EN/Security.json`
- `frontend/messages/en-EN/Download.json`

## 8. Hard Recommendations

- Не пытаться "SEO-шить" всё сразу на 39 локалей.
- Не инвестировать в новый контент, пока не исправлены canonical/hreflang/robots/sitemap.
- Не оставлять help/docs/faq в client-only presentation.
- Не пытаться выиграть рынок только head-term страницами.
- Не маскировать отсутствие trust signals красивым интерфейсом.

## 9. Sources Consulted

- Next.js `generateMetadata` docs:
  - https://nextjs.org/docs/15/app/api-reference/functions/generate-metadata
- Next.js `robots` metadata file docs:
  - https://nextjs.org/docs/app/api-reference/file-conventions/metadata/robots
- Google Search Central, structured data:
  - https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- Google Search Central, Core Web Vitals:
  - https://developers.google.com/search/docs/appearance/core-web-vitals
- Google Search Central, localized versions / hreflang:
  - https://developers.google.com/search/docs/specialty/international/localized-versions
- Google Search Central blog, AI experiences:
  - https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search
- OpenAI Publishers and Developers FAQ:
  - https://help.openai.com/en/articles/12627856-publishers-and-web-search

## 10. Recommended Next Step

Следующий правильный шаг не "писать SEO-тексты", а выполнить **P0 remediation sprint**:
- index hygiene;
- canonical/hreflang repair;
- locale correctness;
- removal/noindex of wrong pages;
- server-first rendering of core marketing/help/docs.

После этого уже имеет смысл делать детальный implementation plan по задачам и файлам.
