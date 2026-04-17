# CyberVPN: Канонический стандарт тарифов и дорожная карта внедрения

**Дата:** 2026-04-16  
**Статус:** Каноническое продуктовое решение для внедрения  
**Предшествующий документ:** `docs/plans/2026-04-16-pricing-plans-and-partner-program-discovery.md`

---

## 1. Что фиксирует этот документ

Этот документ больше не исследовательский. Он фиксирует **целевую каноническую модель** тарифов CyberVPN, которую нужно внедрить по всему монорепозиторию:

- `backend`
- `frontend`
- `admin`
- `services/telegram-bot`

Ключевое решение:

- **никакого временного mapping старых tier в новые названия не будет**;
- проект сразу переводится на новый стандарт коммерческого каталога;
- старый `basic / pro / ultra / cyber` считается legacy-моделью и подлежит замене.

---

## 2. Непересматриваемые продуктовые решения

## 2.1 Публичная линейка

Публичная линейка CyberVPN на первом релизе внедрения:

- `Basic`
- `Plus`
- `Pro`
- `Max`

## 2.2 Скрытые планы

Дополнительно вводятся скрытые планы:

- `Start`
- `Test`
- `Development`

Эти планы не показываются в публичной витрине по умолчанию.

## 2.3 Базовая модель продажи

Коммерческая модель строится как:

- `4 public plans`
- `4 periods`
- `2 add-ons v1`

Периоды:

- `30 дней`
- `90 дней`
- `180 дней`
- `365 дней`

Add-ons v1:

- `Extra Device`
- `Dedicated IP`

## 2.4 Базовые принципы позиционирования

- Все **paid-планы** имеют полноценный базовый VPN-слой.
- На витрине не продаются жёсткие data caps вида `50/100/200 GB`.
- Пользователь видит `Unlimited / Fair use`.
- Реальная экономическая защита реализуется через:
  - `fair_use_policy`
  - `QoS`
  - `server_pool`
  - `priority routing`
  - скрытые internal-limits
- Разница между планами строится не через “есть ли нормальный VPN”, а через:
  - количество устройств
  - качество пулов серверов
  - connection modes
  - anti-DPI / stealth
  - manual / advanced profiles
  - dedicated IP
  - support SLA
  - family / premium сценарии

---

## 3. Канонический каталог планов

## 3.1 Плановые коды

Новая каноническая модель plan family:

| Code | Visibility | Назначение |
|---|---|---|
| `start` | hidden | скрытый entry-plan с 1 устройством |
| `basic` | public | базовый публичный план |
| `plus` | public | основной массовый тариф |
| `pro` | public | power-user тариф |
| `max` | public | premium / family / flagship |
| `test` | hidden | скрытый Max-подобный план с новыми протоколами |
| `development` | hidden | внутренний / безлимитный план без ограничений |

Ключевое техническое решение:

- legacy `PlanTier` заменяется новым каноническим `PlanCode`;
- план больше не трактуется как abstract tier, а как часть продуктового каталога;
- каждый SKU это `plan_code + duration_days`.

## 3.2 Публичная матрица планов

| Plan | Для кого | Devices | Traffic | Connection Modes | Server Pool | Dedicated IP | Support |
|---|---|---|---|---|---|---|---|
| `Basic` | один пользователь / старт | `2` | `Unlimited / fair use` | `Standard` | `Shared` | `add-on` | `Standard` |
| `Plus` | основной массовый тариф | `5` | `Unlimited / fair use` | `Standard + Stealth` | `Shared+` | `add-on` | `Standard` |
| `Pro` | активный пользователь / power use | `10` | `Unlimited / fair use` | `Standard + Stealth + Manual/Advanced` | `Premium Shared` | `add-on` | `Priority` |
| `Max` | семья / premium / flagship | `15` | `Unlimited / fair use` | `All modes` | `Premium + Exclusive` | `1 included` | `VIP` |

## 3.3 Скрытая матрица планов

| Plan | Visibility | Основа | Devices | Traffic | Connection Modes | Server Pool | Dedicated IP | Support | Канал |
|---|---|---|---|---|---|---|---|---|---|
| `Start` | hidden | `Basic`-lite | `1` | `Unlimited / fair use` | `Standard` | `Shared` | `add-on` | `Standard` | admin / direct / campaign |
| `Test` | hidden | `Max` + experimental | `15` | `Unlimited / fair use` | `All modes + Experimental` | `Premium + Exclusive + Beta` | `1 included` | `VIP` | allowlist / internal beta |
| `Development` | hidden | internal unlimited | `unlimited` | `Unlimited` | `All modes + Experimental + Internal` | `All pools + Internal` | `unlimited/internal` | `Internal` | admin only |

Пояснения:

- `Start` отличается от `Basic` только устройствами и скрытостью.
- `Test` отличается от `Max` доступом к новым протоколам и beta-mode.
- `Development` не является consumer-offer и не должен попадать в публичные каналы продажи.

---

## 4. Периоды и SKU

## 4.1 Канонические периоды

Для каталога вводятся только 4 стандартных периода:

- `30`
- `90`
- `180`
- `365`

Каждый период должен существовать как отдельный SKU:

- `basic_30`
- `basic_90`
- `basic_180`
- `basic_365`
- `plus_30`
- `plus_90`
- `plus_180`
- `plus_365`
- `pro_30`
- `pro_90`
- `pro_180`
- `pro_365`
- `max_30`
- `max_90`
- `max_180`
- `max_365`

Скрытые планы также поддерживают стандартные периоды, если не указано иное в админке.

## 4.2 Правила SKU

- Период является частью SKU, а не вычисляемой опцией поверх одной записи плана.
- Годовые perks и invite bundles задаются на уровне конкретного SKU.
- Add-ons наследуют срок базовой подписки.
- Upgrade применяется сразу.
- Downgrade применяется со следующего renewal.

---

## 5. Add-ons v1

## 5.1 Extra Device

Это первый обязательный add-on.

Правила:

- `+1 устройство` за единицу add-on;
- stackable;
- срок действия наследуется от активной подписки;
- по умолчанию продлевается вместе с базовой подпиской;
- итоговый device limit должен пересчитываться в entitlement snapshot;
- пользователь должен видеть устройства и освобождать слот self-service.

Стартовые лимиты:

| Plan | Max extra devices |
|---|---|
| `start` | `+1` |
| `basic` | `+2` |
| `plus` | `+3` |
| `pro` | `+5` |
| `max` | `+10` |
| `test` | `+10` |
| `development` | `0 / not needed` |

## 5.2 Dedicated IP

Это второй обязательный add-on v1.

Правила:

- доступен на всех paid-планах;
- `1 add-on = 1 dedicated IP / 1 location`;
- на `Max` один dedicated IP включён;
- на `Test` один dedicated IP включён;
- на `Development` dedicated IP считается internal/unlimited;
- на остальных планах dedicated IP покупается отдельно.

Дополнительные ограничения:

- привязка к локации обязательна;
- inventory dedicated IP должен контролироваться отдельно от plan catalog;
- quote должен показывать итоговый `dedicated_ip_count`.

## 5.3 Что не входит в add-ons v1

На первом релизе **не вводим**:

- premium support как отдельный add-on;
- protocol packs как платный конструктор;
- traffic boosters;
- anti-DPI packs как отдельную upsell-сущность;
- мелкие micro-add-ons, раздувающие checkout.

---

## 6. Invite policy как часть плана

Invite-механика не является главным аргументом карточки плана, но является важным бонусом для long-term SKU.

Главное решение:

- invite bundle становится частью plan config;
- админ назначает его **прямо в плане**, а не через разрозненный глобальный rule-set;
- текущий `invite.plan_rules` считается legacy-механикой и подлежит замене/депрекации.

## 6.1 Стартовая матрица invite bundles

| SKU | Invite count | Friend days | Expiry days |
|---|---|---|---|
| `start_30` | `0` | `0` | `0` |
| `start_90` | `0` | `0` | `0` |
| `start_180` | `0` | `0` | `0` |
| `start_365` | `1` | `7` | `30` |
| `basic_30` | `0` | `0` | `0` |
| `basic_90` | `0` | `0` | `0` |
| `basic_180` | `0` | `0` | `0` |
| `basic_365` | `1` | `7` | `30` |
| `plus_30` | `0` | `0` | `0` |
| `plus_90` | `0` | `0` | `0` |
| `plus_180` | `1` | `7` | `30` |
| `plus_365` | `2` | `14` | `60` |
| `pro_30` | `0` | `0` | `0` |
| `pro_90` | `0` | `0` | `0` |
| `pro_180` | `1` | `14` | `60` |
| `pro_365` | `2` | `14` | `60` |
| `max_30` | `0` | `0` | `0` |
| `max_90` | `0` | `0` | `0` |
| `max_180` | `1` | `14` | `60` |
| `max_365` | `3` | `14` | `60` |
| `test_365` | `3` | `14` | `60` |
| `development_*` | `0` | `0` | `0` |

Это стартовый seed. В админке значения должны быть изменяемыми.

---

## 7. Trial policy

Канонический trial для CyberVPN:

- `7 дней`
- `1 устройство`
- только `Shared pool`
- только `Standard mode`
- без `Dedicated IP`
- без `Premium / Exclusive nodes`
- без add-ons
- без доступа к `Test` / `Development`-режимам

Следствия для реализации:

- trial должен быть привязан к `mobile_users`, а не к `admin_users`;
- trial не должен переиспользовать consumer paid entitlements;
- trial должен иметь собственный entitlement snapshot;
- trial copy во всех каналах должна быть одинаковой.

---

## 8. Канонический entitlements contract

## 8.1 Принцип

Frontend, Mini App, Telegram bot и admin должны работать не с “сырой features-кашей”, а с единым **effective entitlements snapshot**.

Это означает:

- публичный каталог отдаёт product-level атрибуты;
- quote считает итог после add-ons;
- текущая активная подписка отдаёт уже применённые effective entitlements;
- hidden plans по умолчанию не попадают в публичный каталог.

## 8.2 Каноническая plan schema

```json
{
  "plan_code": "max",
  "display_name": "Max",
  "catalog_visibility": "public",
  "is_active": true,
  "duration_days": 365,
  "price_usd": 99.0,
  "price_rub": null,
  "devices_included": 15,
  "traffic_policy": {
    "mode": "fair_use",
    "display_label": "Unlimited",
    "enforcement_profile": "premium_consumer"
  },
  "connection_modes": [
    "standard",
    "stealth",
    "manual_config",
    "dedicated_ip"
  ],
  "server_pool": [
    "premium",
    "exclusive"
  ],
  "support_sla": "vip",
  "dedicated_ip": {
    "included": 1,
    "eligible": true
  },
  "invite_bundle": {
    "count": 3,
    "friend_days": 14,
    "expiry_days": 60
  },
  "sale_channels": [
    "web",
    "miniapp",
    "telegram_bot",
    "admin"
  ],
  "trial_eligible": false,
  "marketing_badge": "Most Complete"
}
```

## 8.3 Каноническая addon schema

```json
{
  "code": "extra_device",
  "display_name": "+1 device",
  "duration_mode": "inherits_subscription",
  "is_stackable": true,
  "quantity_step": 1,
  "max_quantity_by_plan": {
    "start": 1,
    "basic": 2,
    "plus": 3,
    "pro": 5,
    "max": 10,
    "test": 10
  },
  "delta_entitlements": {
    "device_limit": 1
  },
  "is_active": true
}
```

```json
{
  "code": "dedicated_ip",
  "display_name": "Dedicated IP",
  "duration_mode": "inherits_subscription",
  "is_stackable": true,
  "quantity_step": 1,
  "requires_location": true,
  "delta_entitlements": {
    "dedicated_ip_count": 1
  },
  "is_active": true
}
```

## 8.4 Канонический quote response

```json
{
  "plan_code": "plus",
  "display_name": "Plus",
  "period_days": 365,
  "base_price": 79.0,
  "addons": [
    { "code": "extra_device", "qty": 2, "amount": 12.0 },
    { "code": "dedicated_ip", "qty": 1, "amount": 24.0 }
  ],
  "promo_code": null,
  "wallet_amount": 0,
  "gateway_amount": 115.0,
  "effective_entitlements": {
    "device_limit": 7,
    "traffic_policy": "fair_use",
    "display_traffic_label": "Unlimited",
    "connection_modes": ["standard", "stealth"],
    "server_pool": ["shared_plus"],
    "support_sla": "standard",
    "dedicated_ip_count": 1
  }
}
```

---

## 9. API-стандарт, который нужно внедрить

## 9.1 Общий принцип

Источником истины для коммерческого каталога становится **CyberVPN backend**, а не proxy-ответ Remnawave.

Следствие:

- `/plans` больше не должен быть thin proxy в upstream Remnawave;
- Remnawave остаётся транспортной / infra-системой;
- pricing catalog, add-ons, quote, entitlements и hidden visibility живут в CyberVPN backend.

## 9.2 Обязательные API поверхности

### Public / authenticated consumer

- `GET /plans`
- `GET /plans/{plan_code}`
- `GET /addons/catalog`
- `POST /checkout/quote`
- `POST /checkout/commit`
- `GET /subscriptions/current/entitlements`
- `POST /subscriptions/current/addons`
- `POST /subscriptions/current/upgrade`
- `GET /trial/status`
- `POST /trial/activate`

### Admin

- `GET /admin/plans`
- `POST /admin/plans`
- `PUT /admin/plans/{plan_id}`
- `POST /admin/plans/{plan_id}/clone-periods`
- `GET /admin/addons`
- `POST /admin/addons`
- `PUT /admin/addons/{addon_id}`
- `GET /admin/invites/policy`
- `PUT /admin/invites/policy`

Можно сохранить старые маршруты как временно deprecated aliases, но целевой стандарт должен быть именно таким.

---

## 10. Правила по каналам

## 10.1 Frontend: маркетинговая pricing page

Показывает только:

- `Basic`
- `Plus`
- `Pro`
- `Max`

Не показывает:

- `Start`
- `Test`
- `Development`

Страница должна продавать:

- 4 плана;
- 4 периода;
- 2 add-ons;
- `Unlimited / fair use`;
- понятные connection modes;
- dedicated IP как premium option;
- `Max` как flagship с 1 included dedicated IP.

Технические детали протоколов в карточках не показываются.

## 10.2 Frontend: Mini App plans

Mini App должен:

- получать consumer catalog;
- уметь строить quote;
- показывать add-ons;
- оформлять purchase/upgrade через entitlements-driven flow;
- показывать итоговые права пользователя после покупки.

## 10.3 Admin

Админка должна уметь:

- видеть public и hidden планы;
- редактировать visibility;
- редактировать invite bundle прямо на плане;
- задавать connection modes, server pool, support SLA, dedicated IP eligibility/included;
- управлять add-ons catalog;
- управлять hidden-планами `start`, `test`, `development`;
- не смешивать manual invite batch flow с канонической plan-based invite policy.

## 10.4 Telegram bot

Бот по умолчанию показывает только public catalog:

- `Basic`
- `Plus`
- `Pro`
- `Max`

Hidden-планы доступны только если:

- пользователь пришёл по специальному deep-link;
- план открыт для конкретного sale channel;
- админ/оператор выдаёт или активирует его вручную.

Trial в боте должен соответствовать канонической модели `7d / 1 device / shared only`.

---

## 11. Что меняется в модели данных

## 11.1 Что уходит в legacy

Считаются legacy и подлежат замене:

- `PlanTier = basic|pro|ultra|cyber`
- публичный каталог, завязанный на Remnawave `/plans`
- `features: list[str]` как единственный способ описания тарифа
- `invite.plan_rules` как основной источник invite-политики
- trial, завязанный на `admin_users`

## 11.2 Что становится standard

Новый стандарт:

- `PlanCode`
- `catalog_visibility`
- `sale_channels`
- `traffic_policy`
- `connection_modes`
- `server_pool`
- `support_sla`
- `dedicated_ip.{included, eligible}`
- `invite_bundle`
- `PlanAddon`
- `effective_entitlements`

---

## 12. Дорожная карта внедрения

Реализация разбивается на 3 большие фазы.

## 12.1 Фаза 1: Backend foundation

Документ: `docs/plans/2026-04-16-phase-1-pricing-domain-and-backend-foundation-implementation-plan.md`

Что входит:

- новая модель plan catalog;
- hidden/public visibility;
- add-ons catalog;
- quote / commit / entitlements;
- plan-based invite bundles;
- trial на `mobile_users`;
- OpenAPI и backend regression coverage.

## 12.2 Фаза 2: Frontend + Admin rollout

Документ: `docs/plans/2026-04-16-phase-2-frontend-admin-pricing-rollout-implementation-plan.md`

Что входит:

- новая pricing page;
- новый miniapp purchase flow;
- admin plan editor и plans console под новый стандарт;
- админское управление add-ons и invite bundles;
- пересборка typed clients и UI copy.

## 12.3 Фаза 3: Telegram bot + migration + go-live

Документ: `docs/plans/2026-04-16-phase-3-telegram-bot-migration-go-live-implementation-plan.md`

Что входит:

- новый bot contract;
- bot purchase flow и quote summary;
- harmonized trial flow;
- hidden plan handling;
- seed/migration/go-live checklist;
- cross-channel QA.

---

## 13. Критерии завершения программы

Программа считается завершённой, когда:

- `/plans` отдаёт только новый consumer catalog;
- hidden-планы не попадают в публичные surfaces по умолчанию;
- admin редактирует invite bundle прямо на плане;
- add-ons работают через quote и entitlements;
- `Max` включает 1 dedicated IP;
- trial везде одинаковый;
- frontend pricing page, miniapp, admin и bot используют один и тот же pricing standard;
- legacy tier-модель больше не является источником истины.

---

## 14. Главный архитектурный вывод

CyberVPN нужно внедрять не как “ещё одну страницу тарифов”, а как **полную pricing-platform migration**:

- новый каталог,
- новый продуктовый контракт,
- новая entitlement-модель,
- новые admin controls,
- новые каналы продажи.

Это больше работы, чем косметический rename, но это правильный путь: он убирает legacy-расхождения и сразу даёт платформу для будущих consumer, partner и hidden-offer сценариев.
