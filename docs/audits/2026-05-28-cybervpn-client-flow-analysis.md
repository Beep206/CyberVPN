# CyberVPN: анализ клиентских flow

Дата: 2026-05-28  
Контекст: S2 уже выведен в production, S3 partner surface частично включён, продолжается стабилизация пользовательского кабинета, Mini App, bot, growth/referral/gift/promo и multi-subscription.

## 1. Что проверялось

Проверка выполнена по монорепозиторию и текущему production-state, без ручного входа под всеми реальными пользователями.

Проверены области:

- публичный сайт `cyber-vpn.net`;
- пользовательский кабинет `my.cyber-vpn.net`;
- Telegram Mini App routes;
- клиентские API wrappers;
- multi-subscription state;
- referral / promo / gift / add-ons UI и backend flags;
- auth / register / OTP / OAuth / Telegram linking;
- VPN config delivery;
- pricing / checkout / wallet / subscriptions;
- частично admin / partner boundary по клиентским сценариям;
- production env-флаги без вывода секретов.

Не проверялось как доказанный e2e:

- реальный successful web payment, потому что `PAYMENTS_ENABLED=false`;
- реальный Google/GitHub OAuth success, потому что production сейчас возвращает `oauth_start_failed`;
- полноценный Telegram Bot flow от лица внешнего пользователя без интерактивного Telegram-клиента;
- все визуальные состояния светлой/тёмной темы в браузере через Playwright;
- реальные user-specific Remnawave данные для каждого пользователя без пользовательской сессии.

## 2. Краткий вывод

CyberVPN уже имеет большой клиентский surface: публичный сайт, кабинет, Mini App, bot, тарифы, trial, config delivery, referral/gift/promo, add-ons, partner-связанные элементы. Но сейчас проект находится в переходном состоянии между S1/S2/S3: часть функций уже включена в production, часть UI уже показывает возможности, а часть backend-контрактов ещё остаётся старой модели.

Главный технический риск для клиентских flow сейчас не отсутствие экранов, а несогласованность контрактов:

- часть кабинета работает через `current`;
- часть работает через `selected subscription`;
- часть growth-функций показывается через frontend flags, а backend может отвечать `403`;
- OAuth-кнопки видны, но production OAuth start не работает;
- generic payments выключены, но UI тарифов/add-ons/upgrade может выглядеть как готовый к покупке;
- bot/Mini App/web/admin должны одинаково понимать несколько подписок, но сейчас parity неполная.

## 3. Карта клиентских flow

| Flow | Текущий статус | Главный риск |
|---|---:|---|
| Публичный сайт | Работает, основные страницы отдают `200` | Светлая тема, CTA, pricing и feature-gating нужно тестировать системно |
| Регистрация email/password | Работает по коду, OTP flow есть | Нужно проверить idempotent resume/resend и UX незавершённого аккаунта |
| Login password | Работает по коду | Валидация слабее, чем на регистрации |
| Login 2FA | Реализован | Есть риск stale `pending_2fa` cookie/session и путаницы admin/customer realm |
| OAuth Google/GitHub | UI есть | Production start сейчас падает в `oauth_start_failed` |
| Telegram login/linking | Реализован | Нужно проверить весь browser -> Telegram -> browser возврат и fallback |
| Mini App auth | Реализован | После action нужен гарантированный refetch всех данных без ручной перезагрузки |
| Trial | Реализован | Нужен единый selected subscription update после activation |
| Paid plans | UI есть | Generic payments сейчас disabled, значит web checkout может быть misleading |
| Telegram Stars | Включены | Только Telegram/Mini App flow должен ясно отличаться от web checkout |
| Add-ons | Включены | Нужно ограничивать совместимостью тарифа и выбранной подписки |
| VPN config delivery | Реализован | Должен всегда привязываться к выбранной подписке и `.org` subscription URL |
| Multi-subscription | Частично реализован | Есть смешение selected/current на разных страницах |
| Wallet/orders | Есть | Должен фильтроваться/группироваться по выбранной подписке, где применимо |
| Referral | UI/backend есть | Возможны `403`, если runtime config не совпадает с frontend flags |
| Promo codes | Есть | Нужна единая модель кодов и видимость в checkout/кабинете |
| Gift codes | Есть | Возможны `403`, если policy выключена или UI не синхронизирован |
| Partner entry | Включается в S3 | В customer cabinet должен быть role-aware, не для всех |
| Delete account | Есть | Нужен единый cross-domain route, без RSC/CORS preflight проблем |

## 4. Production flags, которые влияют на клиентские flow

Текущая картина по production backend env:

| Флаг | Состояние | Влияние |
|---|---:|---|
| `REGISTRATION_ENABLED` | `true` | Открытая регистрация включена |
| `REGISTRATION_INVITE_REQUIRED` | `false` | Invite не обязателен для регистрации |
| `PAYMENTS_ENABLED` | `false` | Generic web payments выключены |
| `TELEGRAM_STARS_ENABLED` | `true` | Telegram Stars доступны как отдельный Telegram/Mini App rail |
| `STAGE1_ADDONS_ENABLED` | `true` | Add-ons включены |
| `REFERRAL_ENABLED` | `true` | Referral включён на env-уровне |
| `PROMO_CODES_ENABLED` | `true` | Promo codes включены |
| `GIFT_CODES_ENABLED` | `true` | Gift codes включены |
| `CHECKOUT_CODE_DISCOUNTS_ENABLED` | `true` | Checkout discounts кодами включены |
| `PARTNER_PORTAL_ENABLED` | `true` | Partner portal включён |
| `PARTNER_PAYOUTS_ENABLED` | `false` | Реальные партнёрские выплаты выключены |
| `PAYMENT_AUTORENEWAL_ENABLED` | `false` | Автопродление выключено |
| `POSTHOG_ENABLED` | `false` | Product analytics через PostHog не собирается |
| `OAUTH_ENABLED_LOGIN_PROVIDERS` | пусто | OAuth provider allowlist фактически не задан |

Главное несоответствие: фронтенд может показывать действие, но backend payment/OAuth/runtime policy может его отклонить.

## 5. Что работает не так

### P0/P1. OAuth-кнопки видны, но OAuth start не работает

Факт: Google/GitHub кнопки есть на странице входа/регистрации. Production request на OAuth start сейчас уходит в `oauth_start_failed`.

Вероятная причина:

- `OAUTH_ENABLED_LOGIN_PROVIDERS` пустой;
- или production credentials/callbacks не готовы;
- или provider gating на backend не синхронизирован с frontend UI.

Почему это критично:

- пользователь видит официальный способ входа;
- нажимает кнопку;
- получает отказ;
- доверие к регистрации падает сразу.

Рекомендация:

- если OAuth не готов, скрывать кнопки через backend capabilities;
- если готов, включить provider allowlist и проверить callbacks;
- UI должен показывать только реально работающие providers.

### P1. Web payments выключены, но платный UI уже выглядит активным

Факт: `PAYMENTS_ENABLED=false`, при этом тарифы, quote, add-ons и growth-commerce уже присутствуют в UI.

Почему это плохо:

- пользователь может ожидать оплату на сайте;
- quote/checkout/add-on действия могут создавать ошибки или тупиковые состояния;
- Telegram Stars включены, но это другой payment rail.

Рекомендация:

- разделить `payment_rails` в capabilities:
  - `web_checkout`;
  - `telegram_stars`;
  - `cryptobot`;
  - `manual_invoice`;
  - `autorenewal`.
- на UI показывать не “оплата доступна/недоступна”, а конкретный доступный способ.

### P1. Multi-subscription внедрён частично

Факт: в проекте есть `CustomerSubscriptionProvider` и selected subscription state. Но не все страницы кабинета используют выбранную подписку.

Уже хорошо:

- есть storage key для выбранной подписки;
- есть `customerSubscriptionsApi`;
- server access dashboard использует selected subscription;
- часть subscription cabinet использует selected subscription.

Проблемы:

- часть dashboard всё ещё вызывает `/entitlements/current`;
- часть usage/service-state всё ещё завязана на `/users/me/usage` и `/access-delivery-channels/current/service-state`;
- wallet/orders не всегда связаны с выбранной подпиской;
- Mini App config использует selected key, но не все refetch/invalidation точно попадают в query key;
- bot тоже должен уметь выбирать подписку, иначе web/Mini App и bot будут показывать разные данные;
- admin должен управлять подписками пользователя по отдельности.

Рекомендация:

- считать `selected subscription` обязательным клиентским контекстом;
- оставить `current` только как backward-compatible alias;
- все страницы кабинета должны принимать одну выбранную подписку как источник истины.

### P1. После активации trial/invite/gift нужен гарантированный refetch

Факт: ранее уже наблюдалось, что после активации подписка появляется только после перезагрузки Mini App/страницы. В коде Mini App есть риск: query key содержит `selectedSubscriptionKey`, а часть reset/invalidate может быть с `exact: true` по неполному ключу.

Почему это важно:

- activation должен сразу показывать “VPN готовится/готов”;
- пользователь не должен догадываться перезагрузить Mini App;
- это напрямую влияет на первый успешный VPN connect.

Рекомендация:

- после любого activation/redeem/purchase выполнять единый `refreshCustomerAccessState()`:
  - list subscriptions;
  - selected subscription;
  - entitlements;
  - service state;
  - usage;
  - config;
  - wallet/orders if relevant.
- показывать промежуточное состояние `Provisioning in progress`, а не “конфигурация недоступна”.

### P1. Growth UI и backend policy могут расходиться

Факт: frontend growth flags в `stage1-growth-flags.ts` по умолчанию включены, если env не равен `"false"`. Backend при этом защищает referral/gift/promo через policy и может отвечать `403`.

Почему это плохо:

- пользователь видит раздел;
- запросы получают `403`;
- это выглядит как поломка, хотя функция может быть выключена политикой.

Рекомендация:

- убрать default-on поведение для growth UI;
- UI должен читать backend capabilities;
- если feature выключена, раздел скрыт или показывает аккуратное “Скоро будет доступно”, но без API spam.

### P1. Старый `current` contract ещё живёт на странице подписок

Факт: subscriptions page использует hooks:

- `/entitlements/current`;
- `/access-delivery-channels/current/service-state`;
- `/orders/`.

Это конфликтует с идеей нескольких подписок.

Рекомендация:

- перевести страницу подписок полностью на `customer-subscriptions/{subscription_key}`;
- orders либо группировать по subscription key, либо явно показывать “общая история платежей”.

### P2. Login validation слабее, чем registration validation

Факт: регистрация уже имеет достаточно строгую email/password validation, включая предупреждения по кириллице и требованиям пароля. Login проще.

Почему это важно:

- пользователь может допустить пробел/невалидный email;
- ошибка придёт только от backend;
- UX хуже, чем на регистрации.

Рекомендация:

- использовать общую validation библиотеку для register/login/reset/change password;
- login не должен быть таким строгим по password complexity, но email должен валидироваться одинаково.

### P2. Username-only registration усложняет B2C flow

Факт: register page поддерживает режим `username` без email.

Почему это спорно:

- для публичного B2C это создаёт больше support-сценариев;
- восстановление доступа сложнее;
- email verification/receipts/support становятся менее очевидными.

Рекомендация:

- оставить функционал, но спрятать за internal/support mode;
- основной публичный flow: email + password, Telegram, Google/GitHub.

### P2. 2FA recovery и stale session требуют отдельного UX

Факт: 2FA flow реализован, но ранее уже были проблемы с “Invalid or expired 2FA login session” и stale `pending_2fa`.

Рекомендация:

- при stale pending session показывать понятную кнопку “Начать вход заново”;
- после успешного 2FA чистить `pending_2fa`;
- в настройках показать recovery codes / support recovery flow;
- для admin и customer realm не смешивать cookies и pending session.

### P2. Auth form motion может мешать вводу

Факт: `AuthFormCard` использует mouse tracking и tilt. Ранее были жалобы на лаг 3D/анимации при фокусе полей.

Рекомендация:

- при `input:focus-within` отключать tilt/mouse tracking;
- уважать `prefers-reduced-motion`;
- не трогать саму 3D-сцену, но ограничить интерактивность карточки во время ввода.

### P2. Light theme требует регрессионного visual pack

Факт: ранее в светлой теме были проблемы с чёрными прямоугольниками, серыми пунктами меню и нечитаемыми элементами в Mini App/публичных страницах.

Рекомендация:

- сделать обязательные Playwright screenshots:
  - public home;
  - pricing;
  - register;
  - login;
  - dashboard;
  - subscriptions;
  - servers;
  - referral;
  - Mini App home/plans/profile;
  - admin customers.
- проверять light/dark отдельно.

### P2. Product analytics не включена

Факт: `POSTHOG_ENABLED=false`.

Почему это важно:

- Sentry/Prometheus показывают ошибки;
- но не показывают, где пользователь бросил регистрацию/OTP/trial/payment/config.

Рекомендация:

- включить privacy-safe product events без PII;
- или сделать собственный lightweight funnel events endpoint.

### P3. Два auth/public host создают путаницу

Факт: есть `cyber-vpn.net` и `my.cyber-vpn.net`. Proxy разделяет public и cabinet routes, но auth routes могут существовать в обоих контекстах.

Рекомендация:

- выбрать один canonical auth host;
- после login всегда возвращать в `my.cyber-vpn.net`;
- public host должен быть marketing/pricing/docs/trust.

### P3. Partner entry в customer cabinet должен быть role-aware

Факт: S3 partner surface включается, но обычному пользователю не всегда нужен “Partner Dashboard”.

Рекомендация:

- показывать partner entry только если:
  - пользователь имеет partner workspace;
  - или есть pending partner application;
  - или выбран режим “Стать партнёром”.

## 6. Что можно сделать гибче

### 6.1. Ввести единый `/client/capabilities`

Сейчас клиент узнаёт доступность функций через env, route errors и частные flags. Нужно сделать один runtime endpoint.

Пример данных:

```json
{
  "auth": {
    "email_password": true,
    "magic_link": true,
    "telegram": true,
    "oauth": ["google", "github"]
  },
  "payments": {
    "web_checkout": false,
    "telegram_stars": true,
    "cryptobot": false,
    "manual_invoice": true,
    "autorenewal": false
  },
  "growth": {
    "referral": true,
    "promo_codes": true,
    "gift_codes": true,
    "checkout_discounts": true
  },
  "subscriptions": {
    "multi_subscription": true,
    "selected_subscription_required": true,
    "addons": true,
    "upgrade": true
  },
  "partner": {
    "portal": true,
    "applications": true,
    "payouts": false
  }
}
```

Польза:

- frontend не угадывает;
- UI не показывает сломанные действия;
- Mini App/bot/web получают одинаковую картину;
- можно менять поведение без redeploy frontend.

### 6.2. Сделать selected subscription backend-first

Сейчас selected subscription хранится в браузере. Это нормально как fallback, но для полноценного UX лучше иметь серверный выбор.

Рекомендация:

- `GET /customer-subscriptions/` возвращает `selected=true`;
- `POST /customer-subscriptions/{key}/select`;
- все `/current` endpoints используют selected subscription;
- frontend localStorage остаётся только быстрым cache.

Польза:

- web, Mini App и bot показывают одну выбранную подписку;
- admin/support видит, какую подписку пользователь использует;
- меньше рассинхронизации между устройствами.

### 6.3. Каталог должен возвращать `available_actions`

Для каждого плана/add-on backend должен явно сказать, что можно сделать:

```json
{
  "plan_code": "ru_start",
  "available_actions": {
    "trial": false,
    "checkout": true,
    "upgrade": true,
    "addons": ["ru_traffic_30gb", "ru_traffic_50gb", "ru_traffic_100gb"],
    "autorenewal": false
  }
}
```

Польза:

- frontend не держит бизнес-правила в нескольких местах;
- разные каналы `web`, `telegram`, `miniapp`, `partner` могут иметь разные действия;
- меньше ошибок “кнопка есть, backend отказал”.

### 6.4. Единая state machine для VPN-доступа

Сейчас UI местами показывает “No VPN config”, “Provisioning expected”, “Subscription config not found”. Лучше сделать общую модель:

| State | Что показывает клиент |
|---|---|
| `no_subscription` | Нет активной подписки, CTA trial/plan |
| `activation_pending` | План выбран, ждём оплату/активацию |
| `provisioning` | Доступ создаётся, auto-refresh |
| `ready` | Subscription URL, QR, copy/open |
| `degraded` | Доступ есть, но часть данных недоступна |
| `expired` | Подписка истекла, CTA renew |
| `failed` | Support escalation + retry |

Польза:

- меньше противоречивых сообщений;
- проще поддерживать web/Mini App/bot parity;
- понятнее support.

### 6.5. Growth hub вместо отдельных разрозненных страниц

Referral, promo, gift и invite лучше объединить в одну модель `Codes`.

Типы:

- referral code;
- promo code;
- invite code;
- gift code;
- partner code.

Пользовательский UI:

- “Мои коды”;
- “Активировать код”;
- “Подарить доступ”;
- “Реферальная ссылка”;
- “История начислений”.

Польза:

- меньше экранов;
- меньше разных ошибок;
- проще объяснить пользователю.

## 7. Что можно сделать проще, не убирая функционал

### 7.1. Один главный CTA на каждом состоянии

На главной кабинета:

- если нет подписки: `Активировать trial`;
- если trial недоступен: `Выбрать тариф`;
- если provisioning: `Подождать / Обновить статус`;
- если ready: `Скопировать ссылку подписки`;
- если expired: `Продлить`.

Дополнительные действия оставить ниже или в menu.

### 7.2. Объединить “Сеть”, “Серверы” и “VPN config” в Access page

Сейчас пользователь может попасть в “Сеть”, “Серверы”, “VPN config”, “Dashboard” и видеть разные фрагменты одного сценария.

Проще:

- `Доступ`:
  - выбранная подписка;
  - статус;
  - ссылка подписки;
  - QR;
  - инструкции по устройствам;
  - серверный регион;
  - usage.

При этом функционал не удаляется, а группируется вокруг задачи “подключиться”.

### 7.3. Скрывать advanced до момента необходимости

Обычному пользователю не нужны сразу:

- Partner Dashboard;
- partial backend sync details;
- raw diagnostics;
- service channel details;
- internal provider/channel.

Рекомендация:

- показывать краткий статус;
- advanced раскрывать через “Технические детали”.

### 7.4. Wallet сделать понятнее

Wallet сейчас может означать:

- баланс;
- история платежей;
- invoices;
- refunds;
- referral rewards;
- gift purchases.

Рекомендация:

- разделить в UI:
  - “Платежи”;
  - “Баланс”;
  - “Бонусы”;
  - “Возвраты”.

Backend может остаться тем же, меняется только представление.

## 8. Рекомендованные batch-задачи

### CFLOW-001: Client capabilities contract

Цель: backend отдаёт единый runtime-контракт доступных функций.

Входит:

- endpoint `/api/v1/client/capabilities`;
- web/Mini App/bot usage;
- feature sections скрываются по capabilities;
- больше нет frontend default-on flags для risky growth/payment/OAuth.

Acceptance:

- если provider/payment/referral/gift выключен на backend, UI не вызывает защищённые endpoints;
- OAuth-кнопки соответствуют реально включённым providers.

### CFLOW-002: OAuth and payment rail alignment

Цель: убрать mismatch между видимыми кнопками и реальной готовностью.

Входит:

- Google/GitHub show only if backend confirms enabled;
- web checkout show only if `PAYMENTS_ENABLED=true` и provider готов;
- Telegram Stars показывать только в Telegram/Mini App rail;
- manual invoice fallback, если web payment выключен.

Acceptance:

- пользователь не может нажать действие, которое гарантированно вернёт `oauth_start_failed` или payment disabled.

### CFLOW-003: Multi-subscription parity

Цель: все клиентские поверхности работают через выбранную подписку.

Входит:

- dashboard;
- subscriptions;
- servers/access;
- wallet/orders;
- settings;
- Mini App;
- Telegram Bot;
- admin customer view.

Acceptance:

- переключение подписки меняет config, usage, service-state, add-ons, upgrade quote, orders scope;
- нет смешения `/current` и selected subscription на одном экране.

### CFLOW-004: Provisioning/config refresh

Цель: после trial/invite/gift/payment пользователь сразу видит актуальное состояние.

Входит:

- единый refresh после activation;
- retry/polling provisioning state;
- correct query invalidation by selected subscription key;
- `.org` subscription URL everywhere.

Acceptance:

- после активации не требуется reload Mini App/browser;
- VPN config или понятный provisioning state появляется автоматически.

### CFLOW-005: Growth/referral/gift/promo hardening

Цель: S2 growth-функции выглядят и работают как release-ready.

Входит:

- referral code;
- referral link;
- stats;
- rewards;
- gift list/redeem;
- promo apply;
- checkout discount display;
- support/error states.

Acceptance:

- нет `403` на видимых пользователю growth actions;
- если policy выключена, UI это знает заранее.

### CFLOW-006: Auth/OTP/2FA cleanup

Цель: снизить friction регистрации и входа.

Входит:

- login email validation parity;
- OTP paste/autofocus regression tests;
- resend/resume unfinished registration;
- email activation link;
- stale 2FA pending session handling;
- recovery flow copy.

Acceptance:

- незавершённая регистрация не блокирует пользователя ошибкой `Username already exists`;
- 2FA stale session не заводит пользователя в тупик.

### CFLOW-007: Add-ons and RU traffic packs

Цель: докупка трафика 30/50/100 GB к `Россия Старт` и `Россия Базовый` работает end-to-end.

Входит:

- backend compatibility rules;
- frontend add-on catalog filtering;
- selected subscription quote;
- payment rail handling;
- post-purchase usage/quota update.

Acceptance:

- RU traffic add-ons видны только совместимым подпискам;
- quote/purchase не использует `current`, если выбрана другая подписка.

### CFLOW-008: UX/i18n/theme/performance QA pack

Цель: закрыть визуальные и performance-регрессии.

Входит:

- light/dark screenshots;
- mobile/desktop screenshots;
- Mini App viewport;
- auth form focus performance;
- text overflow across locales.

Acceptance:

- нет чёрных прямоугольников в light theme;
- нет заметного лага при вводе email/password/OTP;
- ключевые CTA читаемы во всех основных локалях.

### CFLOW-009: Product analytics

Цель: видеть клиентскую воронку, а не только ошибки.

Минимальные события:

- `register_start`;
- `otp_sent`;
- `otp_verified`;
- `login_success`;
- `trial_activate_clicked`;
- `trial_activated`;
- `checkout_quote_requested`;
- `checkout_started`;
- `payment_returned`;
- `provisioning_ready`;
- `config_copied`;
- `subscription_url_opened`;
- `addon_quote_requested`;
- `addon_purchase_started`;
- `referral_link_copied`;
- `gift_redeemed`;
- `support_opened`.

Acceptance:

- события не содержат PII;
- можно увидеть, где пользователи теряются.

### CFLOW-010: Support and recovery flows

Цель: пользователь не застревает в ошибках.

Входит:

- payment failed;
- paid but no access;
- no config;
- 2FA lost;
- Telegram link failed;
- OAuth failed;
- subscription expired;
- device limit reached.

Acceptance:

- на каждом тупиковом state есть понятный next step;
- support получает достаточно контекста без раскрытия секретов.

## 9. Приоритет выполнения

Рекомендуемый порядок:

1. CFLOW-001: capabilities contract.
2. CFLOW-002: OAuth/payment UI alignment.
3. CFLOW-003: selected subscription parity.
4. CFLOW-004: provisioning/config refresh.
5. CFLOW-007: add-ons/RU traffic packs end-to-end.
6. CFLOW-005: referral/gift/promo hardening.
7. CFLOW-006: auth/OTP/2FA cleanup.
8. CFLOW-008: visual/performance QA.
9. CFLOW-009: product analytics.
10. CFLOW-010: support/recovery flows.

## 10. Что считать “готово” по клиентским flow

Минимальный release-ready критерий:

- новый пользователь может зарегистрироваться;
- подтвердить email/OTP;
- войти повторно;
- получить trial или купить доступ доступным способом;
- увидеть выбранную подписку;
- получить `.org` subscription URL;
- скопировать QR/ссылку;
- видеть usage/quota;
- докупить совместимый add-on;
- применить promo/gift/referral code, если функция включена;
- выйти из аккаунта сразу;
- восстановить доступ или понять, куда обращаться;
- Mini App и web показывают одинаковую подписку;
- bot не отдаёт другой config для той же выбранной подписки;
- admin/support видит все подписки пользователя и может управлять конкретной подпиской.

## 11. Итоговая оценка

Клиентский продукт уже достаточно широк для S2/S3, но сейчас требует не столько новых функций, сколько выравнивания контрактов.

Ключевой принцип для следующих исправлений:

> Любая кнопка на клиенте должна быть подтверждена backend capabilities, выбранной подпиской и доступным payment/provisioning state.

Если это сделать, CyberVPN станет проще для пользователя, гибче для rollout и безопаснее для поддержки, при этом текущий функционал не нужно удалять.
