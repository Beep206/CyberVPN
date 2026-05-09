> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 PRD — Product Requirements and User Flows

## Product objective

Stage 1 должен проверить B2C-продукт CyberVPN как access-продукт с privacy/no-logs коммуникацией, Telegram-first возможностью и web-first mobile-friendly кабинетом.

## Personas

| Persona | Цель | Что должно работать |
|---|---|---|
| Visitor | Понять продукт и цену | Marketing pages, pricing, devices, legal, status |
| New user | Быстро получить VPN | Register/login, trial/pay, config delivery, guides |
| Telegram user | Всё сделать через Telegram | Bot, Mini App, Telegram linking, Stars/payment, config delivery |
| Paying user | Продлить/контролировать доступ | Subscription, wallet/payment history, renewal/grace, devices |
| Support user | Решить проблему | Ticket, bot support, error states, escalation |
| Support/admin | Помочь пользователю | Subscription/payment/provisioning status, safe credential reset, audit |

## Positioning for Stage 1

Рабочее позиционирование Stage 1:

> CyberVPN — access-first VPN-сервис с быстрым получением доступа через сайт или Telegram, прозрачным trial, удобной выдачей конфигураций и безопасной поддержкой.

Это временное УТП для Stage 1. Финальное публичное УТП должно быть утверждено до Stage 2.

## Languages and localization

- Default locale: `en-EN`.
- Русский язык доступен, но не является основным по ответам владельца.
- Всего заявлено 38 языков; Stage 1 должен проверить critical-path переводы, а не только наличие файлов.
- Цена хранится/рассчитывается как USD source of truth.
- На сайте допустимо показывать локальную валюту по выбранному языку/региону, но это должно быть только display layer, если billing provider фактически списывает в другой валюте.
- Округление “красивых цифр” вверх должно быть описано в pricing rule, чтобы не возникали расхождения checkout vs pricing page.

## Plans and monetization rules

| Правило | Stage 1 requirement |
|---|---|
| Тарифы | Публичные и приватные |
| Периоды | Monthly, quarterly, yearly |
| Lifetime | Disabled |
| Trial | Enabled: 3 дня / 1 устройство / всем пользователям |
| Traffic limits | Disabled по бизнес-решению |
| Device limits | Enabled; enforcement минимум на Remnawave, при необходимости также backend |
| Fair-use policy | Не заявлять как active policy, если heavy users не ограничиваются |
| Add-ons | Можно заложить архитектурно, но production enable только после отдельного requirement |
| Country pricing | Не включать как сложную биллинговую модель в Stage 1; заложить extension point |
| Autoprolongation | Не обещать в S1; manual renewal + expiry reminders/renewal invoice links только если протестированы |
| Grace period | Enabled для failed renewal/expired subscription: 72 hours |
| Promo/gift/referral | Disabled-by-default в S1; manual audited support grants allowed |

## Primary user journey

### Flow UJ-S1-001 — Website registration to trial

1. Пользователь открывает сайт.
2. Видит pricing/features/devices/legal/status/help.
3. Регистрируется через approved auth method.
4. Получает trial 3 дня / 1 устройство.
5. Backend создаёт subscription/trial state.
6. Worker/backend создаёт VPN access в Remnawave.
7. Пользователь получает QR-code, subscription URL и config file.
8. Пользователь открывает platform guide и подключается.
9. Кабинет показывает subscription health, device limit, VPN readiness, traffic usage если доступно.

Acceptance:

- Trial нельзя активировать повторно через простой multi-account abuse path без detection или documented risk acceptance.
- Trial activation writes audit/security/product event.
- Config links не попадают в logs.

### Flow UJ-S1-002 — Website registration to paid subscription

1. Пользователь выбирает tariff period.
2. Checkout показывает сумму и валюту без расхождения с pricing page.
3. Пользователь оплачивает через approved provider.
4. Provider webhook приходит в backend.
5. Backend проверяет signature/secret/provider mode.
6. Backend применяет provider-specific status mapping из `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`; для production enablement mapping должен быть подтверждён real callback evidence.
7. Payment event обрабатывается идемпотентно.
8. Subscription активируется или продлевается.
9. Provisioning выполняется immediately или queued retry.
10. Пользователь видит payment success и VPN access.
11. Wallet/payment history показывает статус.

Acceptance:

- Duplicate webhook не создаёт duplicate subscription/transaction.
- Paid payment не теряется при provisioning failure.
- Orphan payment попадает в support/reconciliation flow; no unresolved paid-but-no-access/orphan older than 24h.
- Refund/dispute status имеет documented behavior.

### Flow UJ-S1-003 — Telegram user to trial/payment/config

1. Пользователь открывает Telegram Bot или Mini App.
2. Backend получает Telegram identity.
3. Пользователь может начать trial, купить тариф, посмотреть devices/profile/wallet/help; referral/promo/gift surfaces hidden/default-off in S1.
4. Если email обязателен для linking, Mini App запрашивает привязку email.
5. Если пользователь позже входит через web, account linking не создаёт duplicate user без подтверждённого flow.
6. Пользователь получает config через Bot/Mini App.

Acceptance:

- Telegram ID хранится как identity, но не обязан быть юридическим customer id.
- Email linking обязателен по решению владельца; конфликтный flow должен быть описан.
- Telegram spam/rate limit включён.
- Telegram support escalation работает.

### Flow UJ-S1-004 — Expired subscription and grace period

1. Subscription истекает или renewal payment fails.
2. Пользователь получает уведомление в web/Telegram/email, если каналы включены.
3. Включается grace period.
4. Во время grace period пользователь видит понятный статус и CTA на оплату.
5. После окончания grace period доступ отключается через worker/provisioning job.
6. При оплате доступ восстанавливается.

Acceptance:

- Grace period duration зафиксирован owner decision: 72 hours.
- Worker job не отключает пользователя раньше срока.
- Support видит причину expired/grace state.

### Flow UJ-S1-005 — Support for “paid but no access”

1. Пользователь обращается через Telegram/email/web ticket/bot.
2. Support/AI agent запрашивает безопасный идентификатор: email, Telegram username/id, payment id или order id.
3. Support видит payment status, subscription status, provisioning status.
4. Если payment paid и provisioning failed, support запускает retry или escalates to ops.
5. Пользователь получает понятное сообщение и ETA-free статус: “доступ восстанавливается / заявка передана”.

Acceptance:

- Support не видит raw secrets, OAuth tokens, TOTP secrets, raw provider secrets.
- Manual credential regeneration доступна только role-gated и audit-logged.
- Все privileged actions записываются в audit log.

## Account linking requirements

Stage 1 обязан описать и реализовать безопасный account linking:

| Scenario | Required behavior |
|---|---|
| Telegram first, then web email login | User can link email only after proof of Telegram session and verified email flow |
| Email first, then Telegram | User can link Telegram only after authenticated web session and validated Telegram identity |
| Same email from OAuth and password | Merge only after verified email or provider trust rule |
| Telegram identity already linked to another account | Block automatic merge; require support/escalation |
| Email belongs to existing account, Telegram Mini App starts new flow | No silent email merge; link only through explicit verified flow or support escalation |
| User wants deletion/export | GDPR/delete/export flows available or manual support procedure documented |

## User cabinet requirements

User dashboard should show:

- Subscription status: active, trial, grace, expired, payment pending, provisioning pending.
- VPN readiness: ready, provisioning, retrying, failed, Remnawave unavailable.
- Devices and device limit.
- QR-code, subscription URL and config file delivery.
- Wallet/payment history.
- Referrals/promo/gift hidden or disabled in S1 unless a later approved evidence gate enables them.
- Profile/security: password/2FA/sessions/linked accounts.
- Notifications.
- Support/diagnostics with actionable states, not operator metrics.

Must hide from ordinary users:

- Operator analytics.
- User totals.
- Node telemetry details.
- Admin/server matrix.
- Security monitoring.
- Internal reconciliation.

## Error states that must be user-friendly

| Error | User message requirement | Internal requirement |
|---|---|---|
| Payment failed | Explain retry/support path | Store attempt and provider status |
| Paid but provisioning failed | Show access is being prepared/retried | Queue retry and alert if lag exceeds threshold |
| Subscription expired | Show renewal CTA and grace state | Worker expiry state consistent |
| Remnawave down | Show service issue/status link | Alert ops; no payment loss |
| No servers available | Show temporary unavailability or fallback | Node health alert |
| Device limit reached | Explain limit and add-on/upgrade path if enabled | Enforce in Remnawave/backend |
| Telegram link conflict | Show safe account linking prompt | Block unsafe merge |
| Config not working | Provide platform guide and support CTA | Support can inspect provisioning status |

## Platform guides required for Stage 1

Minimum guides:

- Windows.
- macOS.
- iOS.
- Android.
- Linux.
- Telegram/Mini App connection flow.

Video guides are not required for Stage 1, but text guides must be accurate and tested against the actual generated config types.

## Product analytics events

Minimum privacy-safe events:

- `visit_pricing`.
- `register_started`.
- `register_completed`.
- `trial_started`.
- `checkout_started`.
- `payment_succeeded`.
- `payment_failed`.
- `provisioning_started`.
- `provisioning_succeeded`.
- `provisioning_failed`.
- `vpn_config_viewed` without logging raw config URL.
- `support_ticket_created`.
- `subscription_expired`.
- `grace_started`.
- `renewal_succeeded`.

Analytics must not include raw config links, raw IP activity, browsing activity, provider secrets, OAuth tokens or TOTP secrets.
