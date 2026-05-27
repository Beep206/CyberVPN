# CyberVPN Multi-Subscription Cabinet Plan

Дата: 2026-05-27  
Статус: локальная подготовка перед deploy/push  
Scope: личный кабинет клиента, backend selection contract, несколько подписок у одного клиента

## Цель

Сделать кабинет, где клиент может иметь несколько подписок, выбрать активную подписку для просмотра и управлять каждой подпиской отдельно: статус, тариф, лимиты, usage, VPN import kit, платежи, продление, upgrade/downgrade и support-контекст.

Текущий проект в основном построен вокруг `current`-контракта:

- `GET /api/v1/entitlements/current`
- `POST /api/v1/access-delivery-channels/current/service-state`
- `GET /api/v1/subscriptions/current/entitlements`
- `POST /api/v1/subscriptions/current/upgrade/quote`
- frontend query keys вида `current-entitlements`

Поэтому multi-subscription нельзя делать только селектором на frontend. Нужен backend contract, который проверяет, что выбранная подписка принадлежит текущему customer realm.

## Важное ограничение текущей архитектуры

В `service_identities` сейчас есть уникальность:

`customer_account_id + auth_realm_id + provider_name`

Это означает, что на текущем контракте Remnawave/VPN identity фактически account-level, а не subscription-level. Поэтому первый безопасный batch:

- даёт список подписок;
- даёт выбор подписки в кабинете;
- применяет выбранный `subscription_key` к entitlement/order/UI context;
- не ломает текущий `/current` fallback;
- явно показывает, что VPN identity пока общий для аккаунта, если у подписки нет собственной service identity.

Полностью независимые VPN-конфигурации, лимиты и provisioning на каждую подписку требуют отдельной миграции `MSUB-08`.

## Термины

- `subscription_key` - стабильный публичный ключ подписки для frontend и API.
- `selected_subscription_key` - выбранная пользователем подписка в кабинете.
- `default_subscription_key` - backend fallback, если пользователь ещё ничего не выбрал.
- `entitlement_grant` - canonical paid/trial/reward access record.
- `service_identity` - VPN/provider identity, сейчас в основном account-level.

## MSUB-00: Contract And Safety Boundary

Задача: зафиксировать контракт до кода.

Решения:

- Не переиспользовать admin `GET /api/v1/entitlements/` для клиента.
- Добавить отдельный customer-facing API namespace.
- Сохранить `/current` endpoints как backward compatible fallback.
- Все selected-subscription endpoints должны проверять ownership по `customer_account_id` и `auth_realm_id`.
- Frontend хранит selection в browser storage, но backend всегда валидирует `subscription_key`.

Exit criteria:

- Есть этот документ.
- Есть список backend/frontend стадий.
- Определено, что `MSUB-08` является отдельной миграцией для настоящего per-subscription VPN identity.

## MSUB-01: Backend Customer Subscription Read Model

Задача: добавить безопасный customer-facing список подписок.

Новый API:

`GET /api/v1/customer-subscriptions/`

Ответ:

- `items[]`
- `selected_subscription_key`
- `default_subscription_key`
- `limitations[]`

Каждый `items[]`:

- `subscription_key`
- `kind`: `entitlement_grant`, `trial`, `legacy_payment`
- `status`
- `display_name`
- `plan_uuid`
- `plan_code`
- `expires_at`
- `created_at`
- `source_type`
- `source_order_id`
- `entitlement_grant_id`
- `service_identity_id`
- `provider_name`
- `effective_entitlements`
- `invite_bundle`
- `is_trial`
- `addons`
- `can_manage`
- `can_deliver_config`
- `management_scope`

Правила ключей:

- `grant:<entitlement_grant_id>`
- `trial:<customer_account_id>`
- `legacy-payment:<payment_id>`

Exit criteria:

- Клиент видит все свои canonical entitlement grants.
- Если canonical grants отсутствуют, старый payment/trial fallback не теряется.
- Нет утечки чужих подписок.

## MSUB-02: Backend Selected Subscription Resolver

Задача: добавить backend resolver для выбранной подписки.

Новый API:

- `GET /api/v1/customer-subscriptions/{subscription_key}`
- `GET /api/v1/customer-subscriptions/{subscription_key}/entitlements`

Правила:

- `subscription_key` валидируется только в рамках текущего customer realm.
- Если выбранная подписка не найдена или не принадлежит пользователю, вернуть `404`, а не чужие данные.
- Если `subscription_key` не передан на старых `/current` маршрутах, поведение остаётся прежним.

Exit criteria:

- Frontend может читать entitlement snapshot по выбранной подписке.
- Старые `current` маршруты не сломаны.

## MSUB-03: Frontend Selected Subscription State

Задача: добавить общий state выбранной подписки для кабинета.

Компоненты:

- `CustomerSubscriptionProvider`
- `useSelectedCustomerSubscription`
- `CustomerSubscriptionSwitcher`

Хранение:

- `localStorage` key с учётом customer id/realm, чтобы не смешивать разных пользователей.
- Если сохранённый ключ больше не доступен, выбрать `default_subscription_key`.

UX:

- Селектор показывается в общем header/sidebar личного кабинета.
- На каждой странице явно видно, какая подписка сейчас выбрана.
- Если подписок несколько, переключение не требует logout/reload.

Exit criteria:

- Выбор сохраняется между reload.
- Query keys включают `subscription_key`.
- При смене selection инвалидируются нужные queries.

## MSUB-04: Cabinet Surface Integration

Задача: применить выбранную подписку к ключевым страницам.

Страницы:

- Dashboard: статус, тариф, срок, лимиты, import kit.
- Subscriptions: quote/upgrade/renew для выбранной подписки.
- Servers/Network: VPN config/import kit для выбранной подписки или честный account-level fallback.
- Wallet/Payments: показывать общую историю, но выделять платежи выбранной подписки, если backend умеет связать order.
- Settings: support/security/account settings остаются account-level, но support context показывает выбранную подписку.

Exit criteria:

- Нет страниц, где пользователь видит данные одной подписки, а действие выполняется над другой.
- Account-level действия визуально отделены от subscription-level действий.

## MSUB-05: Local Test Pack

Задача: доказать контракт локально.

Backend tests:

- клиент с двумя entitlement grants видит две подписки;
- чужая подписка не доступна;
- selected entitlement endpoint возвращает snapshot выбранной подписки;
- legacy fallback работает, если grants отсутствуют.

Frontend tests/build:

- selector render;
- selected key persistence;
- dashboard/subscriptions query keys не используют общий `current` без selection там, где уже доступен selected API.

Exit criteria:

- Backend targeted tests green.
- Frontend lint/build или минимальный targeted test green.

## MSUB-06: Production Deploy And Smoke

Задача: задеплоить после локальной проверки.

Порядок:

1. Backend deploy.
2. Frontend deploy.
3. Smoke: `GET /api/v1/customer-subscriptions/` под customer token.
4. Smoke: открыть `https://my.cyber-vpn.net` и проверить selector.
5. Проверить, что старые `/current` маршруты отвечают как раньше.

Exit criteria:

- Production не потерял текущий S1/S2/S3 flow.
- Multi-subscription selector доступен.
- Ошибок 401/404 от новых путей нет для авторизованного клиента.

## MSUB-07: GitLab/GitHub Push And Evidence

Задача: после production smoke зафиксировать результат.

Порядок:

1. Evidence doc с командами и redacted output.
2. Commit в `main`.
3. Push GitLab first.
4. Push GitHub mirror.

Exit criteria:

- `main` синхронизирован.
- Evidence лежит в `docs/evidence/releases/...`.

## MSUB-08: Per-Subscription VPN Identity Migration

Задача: сделать настоящую независимую VPN-конфигурацию и provisioning на каждую подписку.

Это отдельный batch, потому что он меняет provider/provisioning model.

Варианты:

1. Добавить `customer_subscriptions` как явную доменную сущность, а `service_identities` связать с ней.
2. Ослабить уникальность `service_identities` с account-level на subscription-level.
3. Добавить `subscription_key`/`entitlement_grant_id` в provisioning profiles/device credentials/access delivery channels.
4. Перевести Remnawave provisioning на per-subscription identity.

Exit criteria:

- У каждой подписки может быть отдельный subscription URL.
- Лимиты, device count и usage считаются отдельно.
- Отключение одной подписки не ломает остальные подписки клиента.

## Рекомендованный порядок выполнения сейчас

1. `MSUB-01`
2. `MSUB-02`
3. `MSUB-03`
4. `MSUB-04`
5. `MSUB-05`
6. `MSUB-06`
7. `MSUB-07`

`MSUB-08` выполнять следующим отдельным решением, если после первого batch подтверждаем, что пользователю нужно несколько полностью независимых VPN-доступов, а не только несколько коммерческих подписок в одном аккаунте.
