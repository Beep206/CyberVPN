# CyberVPN: текущее состояние invite / referral / promo / gift кодов

**Дата:** 2026-04-21  
**Статус:** current-state overview  
**Назначение:** зафиксировать, как на данный момент реально работают invite-коды, referral-коды, promo-коды и gift-механики, чтобы на это можно было опираться при внедрении в пользовательский frontend.  
**Важно:** этот документ описывает именно текущее состояние кода и API, а не старые концепты и не желаемое будущее поведение.

**Важно 2:** этот документ описывает existing implementation. Target-state документы в этом пакете определяют новую модель. Если current-state и target-state конфликтуют, после migration/cutover выигрывает target-state package.

---

## 1. Короткий итог

Сейчас в системе есть три реально работающих кодовых механизма и один смежный слой:

1. `Invite codes`  
   Есть отдельная backend-система: генерация, хранение, список моих кодов, redemption.

2. `Referral codes`  
   Есть отдельная backend-система: получение персонального кода, статистика комиссий, история комиссий, начисление денег после успешной оплаты приглашённого пользователя.

3. `Promo codes`  
   Есть отдельная backend-система: admin CRUD, validate, применение в checkout, запись факта использования после успешной оплаты.

4. `Gift`  
   Отдельной полноценной системы `gift_codes` сейчас **нет**.  
   Вместо этого gift-семантика сейчас распределена между:
   - invite-наградами;
   - growth rewards (`bonus_days`, `gift_bonus`);
   - gift-like promo codes;
   - флагом `gift_eligible` в offer/catalog модели.

Ключевой практический вывод:

- для user frontend уже можно внедрять `invite`, `referral`, `promo`;
- для `gift codes` сначала нужно выбрать, что именно продукт хочет под этим понимать, потому что отдельного gift-code API сейчас нет;
- consumer invite/referral/gift механики не стоит смешивать с каноническим partner portal.

---

## 2. Что уже реально существует

### 2.1 Invite codes

Есть:

- таблица `invite_codes`;
- redemption endpoint;
- endpoint списка моих invite-кодов;
- admin endpoint ручной генерации;
- генерация invite-кодов после успешной оплаты через `plan.invite_bundle`.

### 2.2 Referral codes

Есть:

- поле `mobile_users.referral_code`;
- поле `mobile_users.referred_by_user_id`;
- endpoint получения или генерации referral-кода;
- endpoint статистики;
- endpoint недавних комиссий;
- начисление referral commission после успешной оплаты.

### 2.3 Promo codes

Есть:

- таблицы `promo_codes` и `promo_code_usages`;
- validate endpoint;
- admin CRUD;
- применение в checkout;
- запись usage после успешной оплаты.

### 2.4 Gift

Нет:

- отдельной таблицы `gift_codes`;
- отдельного `/gift-codes/*` API;
- отдельного user-facing gift-code flow как самостоятельной сущности.

Но есть:

- growth reward types `bonus_days`, `gift_bonus`, `invite_reward`;
- `gift_eligible` в offer/catalog;
- возможность делать промокод, который ведёт себя как gift-voucher, например `100% off`, single-use, ограниченный по сроку или тарифу.

---

## 3. Главная карта понятий

Чтобы не смешивать сущности:

### 3.1 Invite code

Это одноразовый код, который даёт не денежную награду, а бонусный доступ, сейчас в первую очередь через `free_days` и growth reward `bonus_days`.

### 3.2 Referral code

Это персональный постоянный код пользователя, который нужен для реферальной привязки и последующих комиссий с оплат приглашённых.

### 3.3 Promo code

Это скидочный код для checkout: процент или фиксированная сумма.

### 3.4 Gift

Сейчас это не отдельная кодовая сущность, а общий смысловой слой для:

- бонусных дней;
- non-cash reward allocations;
- gift-like промоакций;
- gift-eligible товаров/офферов.

### 3.5 Важно: admin invite token != invite code

В кодовой базе есть ещё отдельная admin-система `invite tokens` для регистрации внутренних admin-пользователей:

- `/api/v1/admin/invites`

Это **не** пользовательские invite-коды и не часть consumer growth-механики.

---

## 4. Invite codes: как это работает сейчас

## 4.1 Что такое invite code в текущей системе

Invite code сейчас хранится как запись в `invite_codes` со следующими основными полями:

- `code`
- `owner_user_id`
- `free_days`
- `plan_id`
- `source`
- `source_payment_id`
- `is_used`
- `used_by_user_id`
- `used_at`
- `expires_at`

То есть invite-код всегда принадлежит конкретному пользователю и может быть:

- создан вручную админом;
- сгенерирован после успешной оплаты.

## 4.2 Как invite-коды создаются

Сейчас есть два реальных источника:

### A. Admin create

Админ может вручную создать invite-коды через:

- `POST /api/v1/admin/invite-codes`

При этом указывает:

- владельца кодов;
- количество;
- число бесплатных дней;
- опционально `plan_id`.

Срок жизни таких invite-кодов берётся из:

- `system_config["invite.default_expiry_days"]`

### B. Генерация после успешной оплаты

После успешной оплаты вызывается генерация invite-кодов по `plan.invite_bundle`.

Сейчас это не выглядит как отдельная глобальная конфигурация invite rules через admin API. Фактический рабочий источник для payment-generated invite-кодов в коде сейчас:

- `subscription_plan.invite_bundle`

Из него используются:

- `count`
- `friend_days`
- `expiry_days`

Если у плана нет `invite_bundle`, invite-коды не создаются.

## 4.3 Как invite-код редимится

Рабочий endpoint:

- `POST /api/v1/invites/redeem`

Текущая логика:

1. код ищется по `code`;
2. если не найден -> `404`;
3. если уже использован -> `409`;
4. если истёк -> `410`;
5. если валиден -> помечается как used;
6. фиксируются `used_by_user_id` и `used_at`;
7. создаётся growth reward allocation типа `bonus_days`.

То есть invite redemption сейчас делает две вещи:

- юридически/логически сжигает код;
- создаёт reward allocation на бонусные дни.

## 4.4 Что важно для frontend

С точки зрения user frontend invite-код уже можно:

- ввести;
- отправить на redeem;
- показать успех/ошибку;
- показать список моих invite-кодов.

Но есть важный нюанс:

в текущем `redeem` route прямо не видно отдельного шага немедленного provisioning доступа в самом маршруте. Маршрут создаёт reward allocation `bonus_days`, а не вручную активирует отдельный “gift subscription” внутри этого же endpoint.

Это значит:

- с точки зрения API redemption уже рабочий;
- если продукт ожидает мгновенное расширение доступа именно в том же запросе, это нужно проверять по downstream entitlement chain, а не предполагать по факту успешного `POST /invites/redeem`.

## 4.5 Что invite code сейчас не делает

В текущем коде invite redemption **не** создаёт автоматически реферальную связь владельца invite-кода с новым пользователем.

То есть по найденному локальному коду сейчас:

- invite = бонус/подарок в виде дней;
- referral = отдельная комиссия и отдельная связь;
- это не одна и та же операция.

## 4.6 Где это уже есть во frontend

Сейчас invite-флоу уже заведен в пользовательские surface:

- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx`

Что уже есть в UI:

- поле для ввода invite-code;
- вызов redemption;
- success/error feedback;
- вывод списка `my invites`.

---

## 5. Referral codes: как это работает сейчас

## 5.1 Что такое referral code в текущей системе

Referral code сейчас живёт на уровне пользователя в `mobile_users.referral_code`.

Реферальная связь фиксируется через:

- `mobile_users.referred_by_user_id`

То есть текущая модель разделяет:

- внешний shareable identifier;
- фактическую связь “этот пользователь был приглашён тем пользователем”.

## 5.2 Как генерируется referral code

Рабочий endpoint:

- `GET /api/v1/referral/code`

Текущая логика:

- если у пользователя уже есть `referral_code`, он возвращается;
- если нет, код лениво генерируется при первом запросе;
- код сохраняется в `mobile_users.referral_code`.

То есть referral code сейчас не обязательно создаётся на этапе регистрации. Он может появиться только при первом обращении к referral API.

## 5.3 Как считается referral commission

Комиссия создаётся после успешной оплаты приглашённого пользователя.

Рабочий use-case:

- `ProcessReferralCommissionUseCase`

Текущая логика:

1. смотрит, включена ли referral-программа;
2. читает `referral.commission_rate`;
3. читает `referral.duration_mode`;
4. проверяет eligibility;
5. считает комиссию от `base_amount`;
6. кредитует кошелёк referrer’а;
7. создаёт запись `referral_commissions`;
8. создаёт growth reward allocation типа `referral_credit`.

## 5.4 Какие режимы already supported

На стороне config service и use-case уже поддерживаются:

- `indefinite`
- `first_payment_only`
- `payment_count`
- `time_limited`

Но фактически важная деталь такая:

- `indefinite`, `first_payment_only`, `payment_count` реально обрабатываются в `_check_eligibility`;
- `time_limited` в текущем коде пока не имеет полноценной временной проверки и по факту проходит как allow-path.

Это нужно учитывать как реальное текущее состояние, а не как полностью завершённую бизнес-модель.

## 5.5 Какие referral endpoints реально есть

Рабочие user endpoints:

- `GET /api/v1/referral/status`
- `GET /api/v1/referral/code`
- `GET /api/v1/referral/stats`
- `GET /api/v1/referral/recent`

Рабочие admin analytics endpoints:

- `GET /api/v1/admin/referrals/overview`
- `GET /api/v1/admin/referrals/users/{user_id}`

## 5.6 Что именно получает user frontend

Referral frontend сейчас может получить:

- включена ли программа;
- текущую ставку комиссии;
- персональный referral code;
- total earned;
- recent commissions.

Но есть важный нюанс в текущем backend contract:

поле `total_referrals` в user stats сейчас считается как количество commission records, а не как количество уникальных приглашённых пользователей.

То есть если один и тот же приглашённый пользователь заплатил несколько раз, это число может расти как счётчик комиссий, а не как количество “уникальных друзей”.

Для UX это важно. Если в интерфейсе нужен именно count уникальных приглашённых пользователей, текущий endpoint уже не совсем соответствует названию поля.

## 5.7 Как сейчас создаётся сама referral-связь

Вот здесь находится самый важный практический шов.

В локальном коде есть признаки двух параллельных моделей:

### Модель A: canonical referral code API

- есть `mobile_users.referral_code`;
- есть `/api/v1/referral/code`;
- frontend шарит именно referral code.

### Модель B: Telegram-bot referral onboarding

Telegram bot flow сейчас явно работает через:

- `referrer_id`
- deep link вида `ref_{telegram_id}`

То есть в Telegram bot backend текущая привязка строится не по `referral_code`, а по `telegram_id` referrer’а.

Это означает:

- user-facing referral API уже есть;
- user-facing referral UI уже есть;
- но реальный acquisition path в Telegram-ветке всё ещё живёт по `referrer_id`, а не по `referral_code`.

Если коротко:

**referral как программа есть; referral как единый end-to-end consumer onboarding path пока выглядит неоднородно.**

## 5.8 Где это уже есть во frontend

Рабочие user-facing surfaces:

- `frontend/src/app/[locale]/(dashboard)/referral/*`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/profile/page.tsx`

Что уже есть:

- показ referral code;
- copy/share;
- stats;
- recent commissions.

---

## 6. Promo codes: как это работает сейчас

## 6.1 Что такое promo code в текущей системе

Promo code сейчас хранится в `promo_codes` и может иметь:

- тип скидки `percent` или `fixed`;
- значение скидки;
- `currency`;
- лимит использований;
- `is_single_use`;
- ограничение по списку планов;
- `min_amount`;
- `expires_at`;
- `is_active`.

Использования хранятся отдельно в:

- `promo_code_usages`

## 6.2 Какие promo endpoints реально есть

User endpoint:

- `POST /api/v1/promo/validate`

Admin endpoints:

- `POST /api/v1/admin/promo-codes`
- `GET /api/v1/admin/promo-codes`
- `GET /api/v1/admin/promo-codes/{promo_id}`
- `PUT /api/v1/admin/promo-codes/{promo_id}`
- `DELETE /api/v1/admin/promo-codes/{promo_id}`

## 6.3 Что делает validate

`POST /api/v1/promo/validate` сейчас:

1. ищет код;
2. проверяет `is_active`;
3. проверяет `expires_at`;
4. проверяет `max_uses`;
5. если `is_single_use=true`, проверяет, использовал ли уже этот user код;
6. если передан `plan_id`, проверяет допустимость для плана;
7. если передан `amount`, проверяет `min_amount` и считает конкретную скидку.

Возвращает:

- `promo_code_id`
- `discount_type`
- `discount_value`
- `discount_amount`
- `code`

## 6.4 Что validate НЕ делает

Очень важно:

`validate` сейчас не резервирует использование, не увеличивает счётчик и не “применяет” код окончательно.

Факт использования фиксируется только после успешной оплаты в post-payment flow:

- increment `current_uses`;
- create `promo_code_usage`.

Это правильное текущее поведение для checkout, потому что:

- preview не расходует лимит;
- failed payments не расходуют лимит;
- usage пишется только по успешной оплате.

## 6.5 Как promo код участвует в checkout

В текущем checkout promo code может участвовать в:

- `payments/checkout/quote`
- `payments/checkout/commit`
- subscription upgrade quote/commit
- add-on purchase quote/commit
- telegram bot checkout

Базовая логика:

1. берётся базовая цена;
2. если есть partner markup, он добавляется;
3. если есть promo, скидка считается от `displayed_price`;
4. затем может списываться кошелёк;
5. затем получается gateway amount.

## 6.6 Важное ограничение: promo нельзя сочетать с partner code

В текущем checkout promo code не может быть использован вместе с partner code.

Это касается не только явно введённого partner code. Это также касается случая, когда пользователь уже привязан к партнёру и активный partner code подтягивается автоматически.

Практический вывод для user frontend:

если пользователь уже partner-bound, попытка применить promo code может закончиться ошибкой:

`Promo codes cannot be combined with partner codes`

Это нужно заранее учесть в UX.

## 6.7 Где это уже есть во frontend

Promo surface уже заведён в:

- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx`

Сейчас различие такое:

### Mini App Plans

Там promo code реально участвует в quote и commit flow.

### Official Web Dashboard CodesSection

Там promo section сейчас больше похожа на utility-preview:

- пользователь вводит код;
- вызывается validate;
- показывается результат.

Но для точного checkout-поведения на frontend всё равно нужно опираться не только на `validate`, а на quote/commit endpoints, потому что именно они учитывают полный pricing context.

## 6.8 Ещё один важный нюанс

Если frontend вызывает `validate` без `plan_id` и без `amount`, то результат может быть частичным:

- fixed discount вернётся корректно как значение;
- percent discount без контекста суммы не даёт полноценного финального checkout result;
- ограничения по плану и минимуму суммы тоже могут быть проверены только частично.

Поэтому:

**для UI-предпросмотра validate полезен, но для канонического расчёта нужен quote endpoint.**

---

## 7. Gift codes: как это работает сейчас

## 7.1 Ключевой вывод

Отдельной самостоятельной системы `gift codes` сейчас нет.

Нет:

- `gift_codes` table;
- `gift_code_usages` table;
- `/api/v1/gift-codes/*`;
- dedicated user gift-code flow.

## 7.2 Что сейчас фактически играет роль gift-механики

Сейчас gift-логика размазана по нескольким слоям:

### A. Invite -> bonus days

Invite redemption даёт non-cash bonus через `bonus_days`.

### B. Growth rewards

В enum уже есть:

- `invite_reward`
- `bonus_days`
- `gift_bonus`

То есть reward layer понимает gift-like немонетарные бонусы.

### C. Offer catalog

В offers есть:

- `gift_eligible`

Это не gift-code subsystem, а признак коммерческой модели оффера.

### D. Gift-like promo codes

Если продукту нужен “подарочный код”, самый близкий текущий механизм:

- promo code с `100%` discount;
- fixed or percent;
- single-use;
- plan-restricted;
- expiring.

На практике это и есть текущий способ имитировать voucher / gift code.

## 7.3 Что это значит для user frontend

Если в user frontend нужно внедрить именно “gift code” как самостоятельный пользовательский сценарий, сначала нужно выбрать один из трёх вариантов:

1. это просто promo code со special messaging;
2. это invite-like бонус на дни/доступ;
3. это отдельная новая сущность, которой в коде пока нет.

Сейчас кодовая база не даёт одного готового canonical ответа “gift code = вот этот endpoint”.

---

## 8. Что уже можно внедрять в пользовательский frontend

## 8.1 Уже можно внедрять без изобретения backend

### Referral

Можно внедрять:

- экран referral;
- показ персонального кода;
- share/copy;
- stats;
- recent commissions.

### Invite

Можно внедрять:

- ввод invite code;
- redeem;
- список моих invite-кодов;
- отображение статусов и expiry.

### Promo

Можно внедрять:

- promo input;
- promo preview;
- quote с promo;
- commit с promo;
- обработку ошибок несовместимости.

## 8.2 Что нужно внедрять осторожно

### Referral acquisition UX

Нужно осторожно внедрять entry-flow “пользователь пришёл по referral code”, потому что текущая реализация выглядит неоднородной между:

- referral API;
- Telegram bot `referrer_id` flow;
- share link semantics.

### Gift code UX

Нельзя просто “подключить gift code endpoint”, потому что такого endpoint сейчас нет.

---

## 9. Что не стоит смешивать с partner portal

Для партнёрского портала эти механики в текущей модели не являются каноническим ядром.

В partner portal **не стоит тянуть как основные user flows**:

- consumer invite codes;
- consumer referral earnings;
- consumer gift mechanics;
- promo utility для обычного consumer checkout.

То, что относится к партнёрскому миру, это скорее:

- partner codes;
- partner pricing / markup;
- partner earnings;
- attribution;
- partner reporting.

Invite / referral / consumer gift логичнее держать в:

- official web customer dashboard;
- Telegram miniapp;
- consumer checkout flow.

Если что-то из этого когда-то попадёт в partner portal, то максимум как:

- read-only analytics;
- support context;
- cross-surface explanation.

Но не как основной operating surface партнёра.

---

## 10. Главные текущие швы и ограничения

Ниже самые важные вещи, которые надо помнить при внедрении UI.

### 10.1 Invite != referral

Сейчас invite redemption не создаёт автоматически referral-связь.

### 10.2 Referral stats немного переименованы

`total_referrals` в user stats по текущему коду ближе к числу commission records, чем к числу уникальных приглашённых пользователей.

### 10.3 Referral onboarding path неоднороден

Consumer-facing referral code API уже есть, но Telegram acquisition path всё ещё выглядит как `ref_{telegram_id}` / `referrer_id`.

### 10.4 Promo validate != promo applied

Usage промокода фиксируется только после успешной оплаты.

### 10.5 Promo может конфликтовать с partner binding

Если пользователь привязан к партнёру, promo может оказаться недоступен.

### 10.6 Gift codes как отдельной сущности нет

Есть only gift-like semantics, но нет dedicated gift-code subsystem.

### 10.7 Есть отдельные admin invite tokens

Их нельзя путать с consumer invite codes.

---

## 11. Практическая рекомендация для user frontend

Если смотреть чисто прикладно, то в пользовательский frontend я бы закладывал следующие блоки:

### Блок 1. Referral

- отдельная referral page;
- copy/share;
- stats;
- recent commissions.

### Блок 2. Promo в checkout

- promo field в checkout;
- quote before commit;
- reasoned errors;
- конфликт с partner code объяснять явно.

### Блок 3. Invite

- отдельный invite redeem block;
- список моих invite-кодов;
- статус, expiry, copy/share.

### Блок 4. Gift

Пока не делать самостоятельный universal gift-code module, пока продукт не зафиксирует один из вариантов:

- promo-as-gift;
- invite-as-gift;
- отдельный новый gift subsystem.

---

## 12. Основные backend и frontend точки

Ниже основные исходники, на которые сейчас реально опирается система.

### Backend

- `backend/src/presentation/api/v1/invites/routes.py`
- `backend/src/presentation/api/v1/invites/schemas.py`
- `backend/src/application/use_cases/invites/redeem_invite.py`
- `backend/src/application/use_cases/invites/admin_create_invite.py`
- `backend/src/application/use_cases/invites/generate_invites.py`
- `backend/src/infrastructure/database/models/invite_code_model.py`
- `backend/src/infrastructure/database/repositories/invite_code_repo.py`

- `backend/src/presentation/api/v1/referral/routes.py`
- `backend/src/presentation/api/v1/referral/schemas.py`
- `backend/src/application/use_cases/referrals/get_referral_code.py`
- `backend/src/application/use_cases/referrals/get_referral_stats.py`
- `backend/src/application/use_cases/referrals/process_referral_commission.py`
- `backend/src/infrastructure/database/repositories/referral_commission_repo.py`

- `backend/src/presentation/api/v1/promo_codes/routes.py`
- `backend/src/presentation/api/v1/promo_codes/schemas.py`
- `backend/src/application/use_cases/promo_codes/validate_promo.py`
- `backend/src/application/use_cases/promo_codes/admin_manage_promo.py`
- `backend/src/infrastructure/database/models/promo_code_model.py`
- `backend/src/infrastructure/database/repositories/promo_code_repo.py`

- `backend/src/application/use_cases/payments/checkout.py`
- `backend/src/application/use_cases/payments/post_payment.py`
- `backend/src/presentation/api/v1/payments/routes.py`
- `backend/src/presentation/api/v1/subscriptions/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`
- `backend/src/application/use_cases/growth_rewards/create_allocation.py`
- `backend/src/presentation/api/v1/growth_rewards/routes.py`
- `backend/src/application/services/invite_service.py`

### Frontend

- `frontend/src/lib/api/invites.ts`
- `frontend/src/lib/api/referral.ts`
- `frontend/src/lib/api/promo.ts`
- `frontend/src/lib/api/codes.ts`

- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/profile/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx`
- `frontend/src/app/[locale]/(dashboard)/referral/*`

---

## 13. Финальный вывод

Если кратко:

- `invite codes` уже рабочие;
- `referral codes` уже рабочие, но acquisition path ещё не идеально выровнен;
- `promo codes` уже рабочие и уже участвуют в checkout;
- `gift codes` как отдельной сущности сейчас нет.

Для user frontend это означает:

- referral, invite и promo можно внедрять уже сейчас;
- gift сначала надо продуктово определить;
- partner portal сюда тянуть не нужно, кроме очень узких пересечений и аналитических read-only сценариев.
