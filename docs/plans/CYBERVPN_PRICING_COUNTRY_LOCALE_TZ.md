# Техническое задание: гибкая система тарифов, цен, addons, локалей, валют и определения страны пользователя для CyberVPN

**Проект:** CyberVPN
**Формат:** функциональное ТЗ без примеров кода
**Версия:** 1.0
**Дата:** 2026-05-30

---

## 1. Назначение документа

Документ описывает целевую функциональную архитектуру системы, которая позволит CyberVPN гибко управлять тарифами, ценами, addons, валютами, локалями и правилами отображения предложений для разных стран и каналов продаж.

Система должна работать для всех пользовательских поверхностей проекта:

- Customer Frontend;
- Admin Panel;
- Partner Portal;
- Telegram Bot;
- Telegram Mini App;
- Mobile App;
- Desktop Client;
- Backend API;
- Task Worker;
- Remnawave-интеграция.

Главная цель — сделать единый backend-управляемый коммерческий контур, где frontend, Telegram Bot, Mini App, mobile и partner-поверхности получают одни и те же эффективные тарифы из backend, а не рассчитывают цены самостоятельно.

---

## 2. Главная идея решения

CyberVPN должен иметь отдельную доменную систему **Commercial Catalog / Pricing Engine**, которая отвечает за:

- тарифы;
- версии тарифов;
- цены;
- валюты;
- страны;
- группы стран;
- addons;
- скидки и промо;
- trial-настройки;
- доступность тарифов по странам;
- доступность addons по странам;
- каналы продаж;
- quote перед оплатой;
- snapshot условий покупки;
- выдачу VPN-доступа через Remnawave после успешной оплаты.

Ключевое правило:

**Frontend, Telegram Bot, Telegram Mini App, mobile и desktop не должны быть источником тарифной логики. Источник истины — backend.**

---

## 3. Основные цели

### 3.1. Бизнес-цели

Система должна позволять:

1. Управлять тарифами из Admin Panel.
2. Задавать глобальные значения по умолчанию.
3. Переопределять цены и настройки для конкретных стран.
4. Переопределять цены и настройки для групп стран.
5. Настраивать разные валюты для разных стран.
6. Включать и отключать тарифы по странам.
7. Включать и отключать addons по странам.
8. Настраивать addons отдельно от основных тарифов.
9. Управлять trial-периодами.
10. Управлять промокодами и скидками.
11. Поддерживать разные каналы продаж: web, Telegram, Mini App, mobile, desktop, partner.
12. Гарантировать, что при одинаковом context пользователь видит одинаковую цену во всех каналах.
13. После оплаты автоматически создавать или обновлять VPN-доступ через Remnawave.
14. Сохранять snapshot условий покупки, чтобы старые подписки не ломались при изменении тарифов.

### 3.2. Технические цели

Система должна быть:

- backend-authoritative;
- versioned;
- fallback-safe;
- channel-aware;
- country-aware;
- currency-aware;
- locale-aware;
- addon-aware;
- idempotent для платежей и provisioning;
- удобной для администрирования;
- устойчивой к ошибкам внешних сервисов;
- понятной для масштабирования.

---

## 4. Что система не должна делать

Система не должна:

1. Хранить цены в frontend как источник истины.
2. Рассчитывать цену на стороне Telegram Bot.
3. Рассчитывать цену на стороне Telegram Mini App.
4. Определять страну пользователя только по языку интерфейса.
5. Определять валюту пользователя только по языку интерфейса.
6. Считать IP-страну абсолютной истиной.
7. Менять цену уже созданной подписки без отдельной бизнес-логики продления.
8. Создавать дубли VPN-пользователей в Remnawave при повторном webhook.
9. Зависеть от Remnawave как от источника цен.
10. Требовать отдельную тарифную реализацию для каждого канала продаж.

---

## 5. Разделение понятий: locale, country, currency

Для правильной работы нужно разделить несколько разных понятий.

| Понятие | Что означает | Где используется |
|---|---|---|
| UI Locale | Язык и регион интерфейса | Переводы, формат дат, формат чисел, RTL/LTR |
| Display Country | Страна, которую пользователь видит как текущую страну сайта | Country selector, первичный показ каталога |
| Pricing Country | Страна, по которой выбираются цены и доступность тарифов | Catalog, prices, addons, trial, promo |
| Payment Country | Страна, связанная с оплатой или платежным методом | Финальная проверка quote перед оплатой |
| Currency | Валюта показа и списания | Price display, checkout, invoice/receipt |
| Channel | Канал продаж | Web, Telegram Bot, Mini App, mobile, desktop, partner |
| User Segment | Сегмент пользователя | Новый пользователь, действующий пользователь, партнерский пользователь, referral-user |

Главное правило:

**Locale не равен стране. Страна не равна валюте. IP-страна не равна гарантированной стране пользователя.**

---

## 6. Участники системы

### 6.1. Customer Frontend

Customer Frontend отображает пользователю тарифы, addons, валюту, страну, checkout-flow и личный кабинет.

Frontend должен получать от backend:

- текущий commercial context;
- список доступных тарифов;
- цены;
- валюту;
- доступные addons;
- доступные billing periods;
- доступные payment methods;
- quote перед оплатой;
- статус подписки;
- результат provisioning.

### 6.2. Admin Panel

Admin Panel управляет:

- тарифами;
- версиями тарифов;
- addons;
- странами;
- группами стран;
- валютами;
- country overrides;
- channel overrides;
- partner overrides;
- price books;
- промо;
- trial;
- Remnawave provisioning profiles;
- публикацией изменений;
- rollback;
- просмотром эффективного каталога.

### 6.3. Partner Portal

Partner Portal использует те же backend API, но может иметь собственные partner overrides:

- особые цены;
- особые промокоды;
- ограниченный набор тарифов;
- partner-specific storefront;
- отдельную аналитику.

### 6.4. Telegram Bot

Telegram Bot должен:

- получать catalog из backend;
- не хранить цены локально;
- создавать quote через backend;
- показывать пользователю тарифы;
- передавать оплату в backend/payment flow;
- получать subscription URL после provisioning;
- отправлять уведомления.

### 6.5. Telegram Mini App

Telegram Mini App должен работать как отдельная frontend-поверхность, но использовать общий backend context и общий catalog API.

Mini App должен:

- отправлять Telegram initData на backend для проверки;
- получать locale hint из Telegram;
- получать country/currency context из backend;
- отображать тарифы из backend;
- создавать quote через backend.

### 6.6. Mobile App

Mobile App должен:

- получать catalog из backend;
- показывать те же тарифы при том же context;
- поддерживать mobile-specific channel rules;
- учитывать отдельные правила для in-app purchase, если они используются;
- получать VPN-конфигурации после provisioning.

### 6.7. Desktop Client

Desktop Client должен:

- получать статус подписки из backend;
- получать доступные планы и upgrade-flow из backend;
- не хранить тарифную логику локально;
- получать VPN-доступ после активации подписки.

### 6.8. Backend API

Backend API является главным источником истины для:

- тарифов;
- цен;
- валют;
- addons;
- country settings;
- quote;
- order;
- subscription;
- payment webhook;
- provisioning orchestration;
- Remnawave sync.

### 6.9. Task Worker

Task Worker выполняет фоновые задачи:

- обработка успешных платежей;
- provisioning в Remnawave;
- retries;
- reconciliation;
- уведомления;
- обновление статусов подписок;
- expiration handling;
- analytics aggregation.

### 6.10. Remnawave

Remnawave используется для управления VPN-доступом:

- пользователи;
- подписки;
- subscription URL;
- traffic limits;
- device limits;
- squads/groups;
- доступ к нодам;
- VPN-конфигурации.

Remnawave не должен быть источником бизнес-цен.

---

## 7. Общая схема работы

Целевая цепочка:

**Пользователь → Frontend/Bot/Mini App/Mobile/Desktop → Backend Context Resolver → Pricing Catalog → Quote → Payment Provider → Backend Webhook → Subscription Service → Provisioning Worker → Remnawave → VPN Access**

### 7.1. Первый вход пользователя

1. Пользователь открывает сайт, Mini App, Bot, mobile или desktop.
2. Frontend или клиентская поверхность передает backend доступные сигналы:
   - locale из URL;
   - cookie;
   - browser language;
   - Telegram language hint;
   - выбранную пользователем страну;
   - session ID;
   - user ID, если пользователь авторизован.
3. Backend определяет commercial context.
4. Backend возвращает:
   - UI locale;
   - display country;
   - pricing country;
   - currency;
   - confidence level;
   - доступные payment methods;
   - флаги, нужны ли пользователю ручной выбор страны или подтверждение.
5. Frontend запрашивает effective catalog.
6. Backend возвращает тарифы, цены и addons.

### 7.2. Выбор тарифа

1. Пользователь выбирает тариф.
2. Пользователь выбирает billing period.
3. Пользователь выбирает addons.
4. Frontend отправляет выбранные параметры в backend.
5. Backend создает quote.
6. Quote фиксирует сумму, валюту, страну тарифа, тариф, addons и срок действия quote.

### 7.3. Оплата

1. Backend создает payment session у выбранного payment provider.
2. Пользователь оплачивает.
3. Payment provider отправляет webhook в backend.
4. Backend проверяет webhook.
5. Backend переводит order/subscription в нужное состояние.
6. Backend публикует событие для provisioning.
7. Task Worker выдает или обновляет VPN-доступ через Remnawave.
8. Пользователь получает доступ.

### 7.4. Изменение страны или валюты

Если пользователь меняет страну или валюту:

1. Frontend сообщает backend.
2. Backend пересчитывает commercial context.
3. Backend возвращает новый catalog.
4. Старый quote становится неактуальным или требует пересоздания.
5. Пользователь видит новые цены до оплаты.

---

## 8. Доменная модель

### 8.1. Plan

Plan — базовый тарифный продукт.

Примеры смысловых тарифов:

- Basic;
- Plus;
- Premium;
- Family;
- Business;
- Trial.

Plan должен иметь:

| Поле | Назначение |
|---|---|
| Plan SKU | Стабильный идентификатор тарифа |
| Name key | Ключ перевода названия |
| Description key | Ключ перевода описания |
| Status | draft, active, deprecated, archived |
| Default billing periods | Месяц, квартал, год и другие периоды |
| Default entitlements | Базовые возможности тарифа |
| Compatible addons | Список совместимых addons |
| Default provisioning profile | Профиль выдачи доступа в Remnawave |
| Sort order | Порядок отображения |
| Highlight flag | Флаг “популярный тариф” |

### 8.2. Plan Version

Plan Version нужна, чтобы безопасно менять состав тарифа.

Например, тариф Premium может со временем получить больше устройств или другой лимит трафика. Для этого создается новая версия, а старые подписки остаются на старом snapshot.

Plan Version должна хранить:

- version number;
- active period;
- entitlement profile;
- compatible addons;
- provisioning profile;
- display metadata;
- status.

### 8.3. Entitlement Profile

Entitlement Profile описывает, что получает пользователь.

Поля:

| Поле | Назначение |
|---|---|
| Duration | Срок доступа |
| Traffic limit | Лимит трафика, если используется |
| Device limit | Количество устройств |
| Speed profile | Профиль скорости, если используется |
| Node groups | Группы серверов |
| Premium locations | Доступ к premium-локациям |
| Family seats | Количество мест в семейном тарифе |
| Support level | Уровень поддержки |
| Renewal behavior | Как продлевать доступ |

### 8.4. Addon

Addon — дополнительная покупаемая опция.

Типы addons:

| Тип addon | Пример |
|---|---|
| Traffic addon | Дополнительный трафик |
| Device addon | Дополнительные устройства |
| Location addon | Premium-локации |
| Family addon | Дополнительные семейные места |
| Duration addon | Дополнительное время |
| Support addon | Приоритетная поддержка |
| Profile addon | Отдельный VPN-профиль |

Addon должен иметь:

- Addon SKU;
- name key;
- description key;
- status;
- type;
- billing mode;
- compatibility rules;
- country availability;
- channel availability;
- provisioning behavior.

### 8.5. Addon Version

Addon Version нужна для безопасного изменения логики addon.

Она должна фиксировать:

- версию addon;
- параметры addon;
- совместимость с тарифами;
- влияние на entitlements;
- Remnawave mapping;
- статус версии.

### 8.6. Offer

Offer — конкретное коммерческое предложение.

Offer объединяет:

- plan;
- plan version;
- billing period;
- availability rules;
- price reference;
- channel;
- country/group rules;
- trial availability;
- promo compatibility.

### 8.7. Price Book

Price Book — версионированный набор цен.

Price Book должен иметь:

- draft version;
- published version;
- active version;
- scheduled version;
- rollback support;
- validation status;
- publication history.

### 8.8. Country Settings

Country Settings описывает настройки конкретной страны.

Поля:

| Поле | Назначение |
|---|---|
| Country code | Код страны |
| Country name key | Ключ перевода названия страны |
| Status | enabled, hidden, disabled |
| Country group | Группа страны |
| Default locale | Локаль по умолчанию |
| Supported locales | Допустимые локали интерфейса |
| Default currency | Валюта по умолчанию |
| Allowed currencies | Валюты, которые можно показывать или принимать |
| Payment providers | Доступные payment providers |
| Available plans | Какие тарифы доступны |
| Available addons | Какие addons доступны |
| Trial policy | Доступность trial |
| Promo policy | Доступность промо |
| Sort priority | Приоритет страны в selector |
| Display mode | Показывать, скрывать, показывать как coming soon |

### 8.9. Country Group

Country Group нужна для массового управления странами.

Примеры групп:

- Global Default;
- Europe;
- CIS;
- LATAM;
- MENA;
- Asia;
- Tier 1;
- Tier 2;
- Tier 3.

Группа может задавать:

- валюту по умолчанию;
- базовые цены;
- доступные тарифы;
- доступные addons;
- payment providers;
- trial-настройки;
- promo-настройки.

### 8.10. Price Rule

Price Rule задает цену для конкретного контекста.

Измерения Price Rule:

- plan;
- addon;
- billing period;
- country;
- country group;
- channel;
- partner;
- user segment;
- currency;
- promotion;
- effective date.

### 8.11. Promotion Rule

Promotion Rule описывает скидки и промо-механики.

Поля:

- promo code;
- discount type;
- discount value;
- applicable plans;
- applicable addons;
- applicable countries;
- applicable channels;
- start date;
- end date;
- usage limit;
- per-user limit;
- stackability;
- status.

### 8.12. Quote

Quote — предварительный расчет перед оплатой.

Quote фиксирует:

- user/session;
- plan;
- plan version;
- addons;
- billing period;
- pricing country;
- currency;
- final amount;
- discount;
- payment provider;
- quote expiration;
- snapshot используемых правил;
- статус.

### 8.13. Order

Order — попытка покупки.

Order связывает:

- quote;
- user;
- payment session;
- payment provider;
- payment status;
- subscription;
- webhook events.

### 8.14. Subscription

Subscription — активная или историческая подписка пользователя.

Поля:

- subscription ID;
- user ID;
- plan snapshot;
- addons snapshot;
- start date;
- end date;
- status;
- renewal mode;
- Remnawave user reference;
- Remnawave subscription reference;
- provisioning status.

### 8.15. Subscription Snapshot

Subscription Snapshot — неизменяемая копия условий покупки.

Он должен хранить:

- plan SKU;
- plan version;
- plan name key;
- billing period;
- addons;
- price;
- currency;
- country;
- discount;
- entitlement profile;
- provisioning profile;
- created timestamp.

### 8.16. Provisioning Profile

Provisioning Profile описывает, как CyberVPN-тариф превращается в Remnawave-доступ.

Поля:

- profile ID;
- plan version;
- addon version;
- Remnawave user settings;
- duration mapping;
- traffic limit mapping;
- device limit mapping;
- squads/groups mapping;
- node access mapping;
- metadata mapping;
- renewal behavior;
- addon behavior.

### 8.17. Provisioning Job

Provisioning Job — задача на создание или обновление VPN-доступа.

Поля:

- job ID;
- subscription ID;
- user ID;
- desired state;
- current state;
- Remnawave reference;
- retry count;
- last error;
- status;
- created at;
- updated at.

### 8.18. User Commercial Context

User Commercial Context — результат определения текущего коммерческого контекста пользователя.

Поля:

- user ID или anonymous session ID;
- UI locale;
- display country;
- pricing country;
- selected currency;
- channel;
- partner ID;
- user segment;
- confidence level;
- flags;
- source priority;
- updated at.

---

## 9. Fallback-логика

### 9.1. Главный принцип

Для каждой настройки должно быть понятно:

- значение задано явно;
- значение наследуется;
- значение отключено;
- список полностью заменен;
- элемент добавлен к наследуемому списку;
- элемент удален из наследуемого списка.

Нельзя путать отсутствие значения и явное отключение.

### 9.2. Порядок применения fallback

Рекомендуемый порядок:

1. Global default.
2. Plan default.
3. Country group override.
4. Country override.
5. Channel override.
6. Partner override.
7. User segment override.
8. Promotion override.
9. Payment provider compatibility.

Самое специфичное правило побеждает, но только для тех полей, которые оно явно задает.

### 9.3. Если для страны нет отдельных настроек

Если для страны нет country override:

1. Использовать настройки country group.
2. Если у группы нет настройки — использовать global default.
3. Если цена не задана для страны — использовать group/global price.
4. Если валюта не задана — использовать group/global currency.
5. Если addons не заданы — использовать inherited addons.
6. Если payment providers не заданы — использовать inherited providers.
7. Если тариф явно disabled на уровне страны — не показывать его.

### 9.4. Состояния настройки

| Состояние | Значение |
|---|---|
| inherit | Наследовать от родителя |
| override | Использовать локальное значение |
| disabled | Отключить в данном context |
| replace | Полностью заменить список |
| append | Добавить к унаследованному списку |
| remove | Убрать из унаследованного списка |

---

## 10. Price Book и публикация цен

### 10.1. Общая модель

Все цены должны редактироваться в draft-версии Price Book.

После проверки draft публикуется как новая active version.

Active version не редактируется напрямую.

### 10.2. Состояния Price Book

| Состояние | Назначение |
|---|---|
| Draft | Редактируется |
| Validating | Проверяется системой |
| Ready | Готов к публикации |
| Scheduled | Запланирован к публикации |
| Active | Используется пользователями |
| Rolled back | Откатан |
| Archived | Архивирован |

### 10.3. Валидация перед публикацией

Перед публикацией нужно проверить:

- у активных тарифов есть цены;
- у цен есть валюта;
- валюта разрешена для страны или группы;
- billing period корректен;
- addon price задан, если addon продается отдельно;
- addon совместим с тарифом;
- active offer имеет provisioning profile;
- нет пересекающихся правил для одного context;
- нет отрицательных цен;
- скидка не делает цену ниже допустимого минимума;
- все названия тарифов и addons имеют translation keys;
- effective catalog можно построить для всех включенных стран.

### 10.4. Rollback

Admin должен иметь возможность откатить активный Price Book на предыдущую опубликованную версию.

Rollback должен:

- быть атомарным;
- не менять существующие subscription snapshots;
- обновлять catalog cache;
- логировать действие.

---

## 11. Pricing rules

### 11.1. Что можно настраивать

Для каждого тарифа можно настраивать:

- цену;
- валюту;
- billing period;
- trial;
- доступность страны;
- доступность канала;
- порядок отображения;
- recommended/highlight flag;
- совместимые addons;
- promo compatibility.

Для каждого addon можно настраивать:

- цену;
- валюту;
- совместимые тарифы;
- доступность страны;
- доступность канала;
- recurring или one-time режим;
- provisioning behavior.

### 11.2. Хранение денег

Суммы должны храниться:

- в minor units;
- без floating point;
- с отдельным currency code;
- с отдельной стратегией округления;
- со snapshot на момент quote/order/subscription.

### 11.3. Renewal price

Для продлений нужно отдельно определить бизнес-правила:

| Вариант | Описание |
|---|---|
| Snapshot price | Пользователь продлевается по цене первой покупки |
| Current price | Пользователь продлевается по текущей цене |
| Grace migration | Пользователь остается на старой цене до заданной даты |
| Manual migration | Пользователь переводится на новую цену через отдельное действие |

Решение должно быть задаваемым в Admin Panel, а не зашитым в коде.

---

## 12. Addons

### 12.1. Общие требования

Addons должны управляться отдельно от основных тарифов.

Система должна поддерживать:

- one-time addons;
- recurring addons;
- addons, которые покупаются только вместе с тарифом;
- addons, которые можно докупить к активной подписке;
- addons, которые доступны только в отдельных странах;
- addons, которые доступны только в отдельных каналах;
- addons, которые изменяют Remnawave-параметры.

### 12.2. Совместимость addons

Для каждого addon нужно задать:

- совместимые plans;
- несовместимые plans;
- минимальный billing period;
- доступность во время trial;
- доступность после окончания подписки;
- возможность покупки несколько раз;
- максимальное количество;
- влияние на subscription snapshot;
- влияние на provisioning.

### 12.3. Addon lifecycle

Покупка addon должна проходить такую цепочку:

1. Пользователь выбирает addon.
2. Backend проверяет совместимость.
3. Backend создает quote.
4. Пользователь оплачивает.
5. Backend обновляет subscription snapshot или addon snapshot.
6. Task Worker создает provisioning job.
7. Remnawave обновляется.
8. Пользователь получает обновленный доступ.

### 12.4. Addon fallback

Addon должен использовать такую же fallback-логику, как тариф:

1. Global addon default.
2. Country group override.
3. Country override.
4. Channel override.
5. Partner override.
6. User segment override.
7. Promotion override.

---

## 13. Определение страны пользователя

### 13.1. Главный принцип

Страна пользователя определяется не одним источником, а набором сигналов.

Так как пользователь может зайти через VPN, proxy, мобильную сеть или другой нестандартный маршрут, IP-страна должна использоваться как подсказка, а не как единственный источник истины.

Система должна строить **country context** с уровнем уверенности и давать пользователю возможность вручную выбрать страну для показа тарифов.

### 13.2. Источники сигналов

| Источник | Для чего использовать | Приоритет |
|---|---|---|
| Страна из профиля пользователя | Default display/pricing country | Высокий |
| Последняя страна успешной покупки | Default pricing country | Высокий |
| Явный выбор страны пользователем | Display/pricing country | Высокий |
| Country selector в UI | Display/pricing country | Высокий |
| Edge/IP GeoIP | Первичная подсказка | Средний |
| VPN/proxy detection | Понижение уверенности IP-сигнала | Средний |
| Browser Accept-Language | Подсказка для locale, не для страны | Низкий |
| Telegram language_code | Подсказка для locale, не для страны | Низкий |
| Payment provider country hint | Проверка перед оплатой | Высокий |
| Mobile app/store context | Подсказка для mobile flow | Средний/высокий |

### 13.3. Confidence levels

Backend должен возвращать confidence level.

| Level | Значение |
|---|---|
| verified | Страна подтверждена предыдущей успешной покупкой или профилем |
| high | Несколько сигналов совпадают |
| medium | Есть нормальный IP/country signal и нет конфликтов |
| low | Только слабый сигнал или пользователь через VPN/proxy |
| unknown | Страна не определена |
| conflicted | Сигналы противоречат друг другу |

### 13.4. Поведение при низкой уверенности

Если confidence low, unknown или conflicted:

1. Не блокировать пользователя.
2. Показать country selector.
3. Предложить выбрать страну для цен.
4. Использовать global/default catalog до выбора.
5. После выбора пересчитать catalog.
6. Перед оплатой пересоздать quote при необходимости.

### 13.5. Поведение при VPN/proxy

Если система видит, что пользователь может быть через VPN/proxy:

1. IP-страна не должна считаться надежной.
2. Backend понижает confidence.
3. Frontend показывает понятный country selector.
4. Пользователь может выбрать страну вручную.
5. Backend строит pricing country на основе выбора или профиля.
6. На checkout quote может быть пересчитан, если payment context отличается.

### 13.6. Разделение стран в context

Backend должен отдельно хранить:

| Поле | Назначение |
|---|---|
| display_country | Страна, которую пользователь видит в UI |
| pricing_country | Страна, по которой рассчитаны тарифы |
| payment_country | Страна, связанная с оплатой |
| previous_purchase_country | Страна предыдущей успешной покупки |
| user_selected_country | Последний ручной выбор пользователя |

---

## 14. Определение locale для frontend

### 14.1. Главный принцип

Locale нужна для языка интерфейса, переводов, формата чисел, формата дат и RTL/LTR.

Locale не должна быть источником цены, валюты или страны.

### 14.2. Приоритет locale resolver

Рекомендуемый порядок определения locale:

1. Locale в URL.
2. Locale в профиле авторизованного пользователя.
3. Locale cookie после ручного выбора языка.
4. Telegram language hint для Telegram Bot/Mini App.
5. Browser Accept-Language.
6. Default locale выбранной страны.
7. Global default locale.

### 14.3. Требования к frontend

Frontend должен:

- поддерживать все 39 локалей проекта;
- поддерживать RTL для соответствующих языков;
- иметь language switcher;
- сохранять ручной выбор пользователя;
- не менять язык неожиданно во время checkout;
- использовать locale-aware форматирование чисел, дат и валют;
- получать цены из backend;
- не использовать translations как источник тарифных данных;
- не считать язык страной пользователя.

### 14.4. Требования к URL structure

Рекомендуется использовать locale routing.

Примеры смысловых вариантов:

- locale prefix в URL;
- cookie для сохранения выбранной locale;
- fallback на default locale;
- корректный canonical behavior для страниц.

В проекте важно учитывать правило Next.js 16.1+: middleware/proxy-конфигурацию держать в `src/proxy.ts`, а не в `src/middleware.ts`.

### 14.5. Locale для Telegram

Для Telegram Bot и Mini App:

1. Если у пользователя есть CyberVPN profile locale — использовать ее.
2. Если нет — использовать Telegram language hint.
3. Если Telegram locale не поддерживается — применить fallback matching.
4. Если locale не найдена — использовать global default locale.

Telegram language hint не должен использоваться как страна тарифа.

---

## 15. Определение валюты пользователя

### 15.1. Главный принцип

Валюта определяется коммерческим context, а не языком интерфейса.

### 15.2. Приоритет currency resolver

Рекомендуемый порядок:

1. Валюта активной подписки, если пользователь продлевает или обновляет подписку.
2. Валюта quote, если quote уже создан.
3. Валюта последней успешной покупки.
4. Валюта выбранной пользователем страны.
5. Валюта из country settings.
6. Валюта из country group.
7. Global default currency.

### 15.3. Требования к валютам

Система должна:

- хранить currency code отдельно от amount;
- хранить amount в minor units;
- поддерживать валюты на уровне country settings;
- поддерживать несколько разрешенных валют для страны;
- проверять совместимость валюты с payment provider;
- показывать пользователю финальную валюту до оплаты;
- сохранять валюту в quote snapshot;
- сохранять валюту в subscription snapshot.

### 15.4. Переключение валюты пользователем

Пользователь может выбрать валюту только из списка разрешенных валют для текущего context.

При смене валюты:

1. Backend пересчитывает catalog.
2. Старый quote становится неактуальным.
3. Пользователь видит новые цены.
4. Checkout должен использовать новый quote.

---

## 16. Effective Catalog

### 16.1. Назначение

Effective Catalog — это результат применения всех правил для конкретного пользователя или session.

Он должен включать:

- доступные plans;
- доступные plan versions;
- доступные billing periods;
- цены;
- валюту;
- discounts;
- trial settings;
- addons;
- payment providers;
- display metadata;
- country selector data;
- flags для UI.

### 16.2. Входные параметры

Для построения effective catalog backend использует:

- user ID или anonymous session ID;
- channel;
- locale;
- display country;
- pricing country;
- currency;
- partner ID;
- user segment;
- promo code;
- active subscription state;
- payment provider availability.

### 16.3. Выходные данные

Backend должен вернуть frontend:

- catalog version;
- price book version;
- country context;
- currency context;
- список тарифов;
- список addons;
- ограничения;
- reasons для скрытых или disabled вариантов, если UI должен их показывать;
- expiration/cache metadata.

### 16.4. Catalog consistency

При одинаковом input context все каналы должны получать одинаковый catalog.

Это означает:

- web и Mini App показывают одинаковые цены;
- Telegram Bot и frontend используют одни rules;
- partner portal получает отличия только через partner override;
- mobile получает отличия только через mobile channel rules.

---

## 17. Quote

### 17.1. Назначение

Quote фиксирует конкретное предложение перед оплатой.

Quote нужен, чтобы цена на checkout не “плавала” и чтобы payment provider получал сумму из backend, а не из frontend.

### 17.2. Требования к quote

Quote должен:

- создаваться только backend;
- иметь срок действия;
- быть привязанным к user/session;
- хранить selected plan;
- хранить selected addons;
- хранить pricing country;
- хранить currency;
- хранить final amount;
- хранить discount;
- хранить payment provider;
- хранить snapshot примененных правил;
- быть invalidated при смене страны, валюты, тарифа, addons или payment provider;
- быть единственным источником суммы для оплаты.

### 17.3. Repricing

Quote должен пересоздаваться или пересчитываться, если:

- пользователь изменил страну;
- пользователь изменил валюту;
- пользователь изменил addons;
- пользователь применил промокод;
- payment provider не поддерживает выбранную валюту;
- price book был обновлен до оплаты;
- quote expired.

### 17.4. Quote states

| State | Назначение |
|---|---|
| draft | Quote создан, но не используется в оплате |
| active | Quote готов к оплате |
| expired | Истек срок действия |
| invalidated | Условия изменились |
| paid | Оплата успешна |
| cancelled | Пользователь отменил checkout |

---

## 18. Checkout и платежный flow

### 18.1. Общая схема

1. Пользователь выбирает тариф и addons.
2. Backend создает quote.
3. Пользователь выбирает payment method.
4. Backend проверяет совместимость payment method с currency/country/channel.
5. Backend создает payment session.
6. Пользователь оплачивает.
7. Payment provider отправляет webhook.
8. Backend активирует order/subscription.
9. Worker запускает provisioning.
10. Пользователь получает VPN-доступ.

### 18.2. Payment provider compatibility

Для каждого payment provider нужно настроить:

- доступные страны;
- доступные валюты;
- минимальную сумму;
- максимальную сумму;
- recurring support;
- one-time support;
- refund support;
- webhook settings;
- channel compatibility.

### 18.3. Idempotency

Backend должен быть устойчив к повторным webhook.

Повторный webhook не должен:

- создавать второй order;
- создавать вторую subscription;
- создавать второго Remnawave user;
- продлевать доступ дважды;
- покупать addon дважды.

---

## 19. Subscription lifecycle

### 19.1. Состояния подписки

| State | Описание |
|---|---|
| pending_payment | Ожидает оплаты |
| paid_pending_provisioning | Оплата есть, доступ еще не выдан |
| active | Активна |
| grace_period | Временный период после окончания оплаты |
| expired | Истекла |
| cancelled | Отменена |
| refunded | Возврат |
| suspended | Приостановлена |
| provisioning_failed | Не удалось выдать доступ |
| retrying_provisioning | Идет повторная выдача доступа |

### 19.2. Создание подписки

Подписка создается только после успешной оплаты или после отдельного trial-flow.

При создании подписки нужно:

- сохранить subscription snapshot;
- сохранить plan version;
- сохранить addons snapshot;
- сохранить entitlements;
- создать provisioning job;
- отправить событие в worker;
- уведомить пользователя после успешного provisioning.

### 19.3. Продление подписки

Продление должно учитывать:

- текущий subscription state;
- renewal policy;
- current price или snapshot price;
- активные addons;
- выбранную валюту;
- payment provider;
- provisioning extension в Remnawave.

### 19.4. Upgrade и downgrade

Система должна поддерживать:

- upgrade на более высокий тариф;
- downgrade на следующий период;
- пересчет разницы, если такая бизнес-логика включена;
- изменение Remnawave entitlements;
- обновление subscription snapshot.

---

## 20. Remnawave provisioning

### 20.1. Главная роль Remnawave

Remnawave отвечает за VPN-доступ, но не за цены.

CyberVPN backend отвечает за:

- тарифы;
- цены;
- оплату;
- подписки;
- addons;
- snapshot;
- бизнес-состояние пользователя.

Remnawave отвечает за:

- технический VPN-доступ;
- пользователей VPN;
- subscription URL;
- node/squad access;
- traffic limits;
- device limits;
- config delivery.

### 20.2. Mapping CyberVPN → Remnawave

Для каждого Plan Version должен быть Provisioning Profile.

Mapping должен описывать:

- какие Remnawave groups/squads назначить;
- какой срок доступа установить;
- какой traffic limit установить;
- какой device limit установить;
- какой subscription URL создать;
- какие metadata передать;
- как продлевать доступ;
- как применять addons.

### 20.3. Provisioning command

После успешной оплаты backend должен сформировать desired state:

- user ID;
- subscription ID;
- plan version;
- addons;
- entitlements;
- start/end date;
- Remnawave profile;
- operation type.

Worker должен привести Remnawave к этому desired state.

### 20.4. Idempotency в Remnawave

Каждая операция должна иметь уникальный idempotency key.

Если операция повторяется:

- worker должен найти существующий Remnawave user;
- проверить текущее состояние;
- применить только недостающие изменения;
- не создавать дубли.

### 20.5. Reconciliation

Нужен периодический sync:

1. Backend получает список активных subscriptions.
2. Worker сверяет Remnawave state.
3. Если есть расхождение — создает repair job.
4. Admin видит расхождения в панели.
5. Admin может вручную повторить provisioning.

### 20.6. Provisioning failures

Если provisioning не удался:

1. Subscription получает состояние `provisioning_failed` или `retrying_provisioning`.
2. Worker делает retry по backoff-стратегии.
3. Пользователь видит понятный статус.
4. Admin видит ошибку.
5. После успешного retry пользователь получает доступ.

---

## 21. Admin Panel

### 21.1. Основные разделы

Admin Panel должен иметь разделы:

1. Dashboard.
2. Plans.
3. Plan Versions.
4. Entitlement Profiles.
5. Addons.
6. Addon Compatibility.
7. Countries.
8. Country Groups.
9. Currencies.
10. Price Books.
11. Country Overrides.
12. Channel Overrides.
13. Partner Overrides.
14. Promotions.
15. Trials.
16. Payment Providers.
17. Remnawave Provisioning Profiles.
18. Effective Catalog Preview.
19. Subscriptions.
20. Orders.
21. Provisioning Jobs.
22. Audit Log.
23. Rollback.

### 21.2. Effective Catalog Preview

Admin должен уметь симулировать catalog для любого context.

Параметры preview:

- country;
- locale;
- currency;
- channel;
- partner;
- user segment;
- promo code;
- active subscription state;
- VPN/proxy flag;
- payment provider.

Preview должен показывать:

- доступные тарифы;
- доступные addons;
- итоговые цены;
- валюту;
- billing periods;
- trial;
- примененные fallback rules;
- откуда пришло значение;
- почему тариф скрыт или отключен;
- какой Remnawave profile будет использован.

### 21.3. Управление странами

Admin должен уметь:

- добавлять страну;
- отключать страну;
- скрывать страну из selector;
- назначать group;
- задавать default locale;
- задавать supported locales;
- задавать default currency;
- задавать allowed currencies;
- задавать payment providers;
- включать/отключать plans;
- включать/отключать addons;
- настраивать trial;
- настраивать promo.

### 21.4. Управление тарифами

Admin должен уметь:

- создавать plan;
- создавать plan version;
- архивировать plan;
- менять display metadata;
- задавать entitlements;
- задавать billing periods;
- задавать default price;
- задавать country/group prices;
- назначать provisioning profile;
- preview перед публикацией.

### 21.5. Управление addons

Admin должен уметь:

- создавать addon;
- создавать addon version;
- задавать compatibility matrix;
- задавать prices;
- задавать availability;
- задавать provisioning behavior;
- архивировать addon;
- preview влияния addon на subscription.

### 21.6. Publish workflow

Workflow:

1. Admin редактирует draft.
2. Система валидирует draft.
3. Admin смотрит preview.
4. Admin публикует Price Book.
5. Backend инвалидирует cache.
6. Новый catalog становится активным.
7. Старые subscription snapshots не меняются.

### 21.7. Audit Log

Audit Log должен фиксировать:

- кто изменил настройку;
- что изменилось;
- старое значение;
- новое значение;
- время изменения;
- тип действия;
- связанную сущность.

Audit Log нужен для внутренней прозрачности и отката изменений.

---

## 22. Backend modules

### 22.1. Catalog module

Отвечает за:

- plans;
- plan versions;
- offers;
- display metadata;
- availability;
- translation keys.

### 22.2. Pricing module

Отвечает за:

- price books;
- price rules;
- country/group overrides;
- channel overrides;
- partner overrides;
- discount application;
- fallback calculation;
- effective price.

### 22.3. Addon module

Отвечает за:

- addons;
- addon versions;
- compatibility;
- addon pricing;
- addon provisioning behavior.

### 22.4. Context Resolver module

Отвечает за:

- locale resolution;
- country resolution;
- currency resolution;
- channel detection;
- user segment detection;
- confidence level;
- context persistence.

### 22.5. Quote module

Отвечает за:

- quote creation;
- quote expiration;
- quote invalidation;
- quote snapshot;
- repricing;
- checkout handoff.

### 22.6. Billing module

Отвечает за:

- orders;
- payment sessions;
- payment providers;
- webhook handling;
- payment status;
- refunds, если включены.

### 22.7. Subscription module

Отвечает за:

- subscription lifecycle;
- renewals;
- upgrades;
- downgrades;
- cancellations;
- grace period;
- subscription snapshot.

### 22.8. Provisioning module

Отвечает за:

- provisioning profiles;
- provisioning jobs;
- Remnawave commands;
- retries;
- reconciliation;
- repair actions.

### 22.9. Admin module

Отвечает за:

- admin CRUD;
- preview;
- validation;
- publish;
- rollback;
- audit log.

### 22.10. Localization module

Отвечает за:

- supported locales;
- locale metadata;
- RTL/LTR;
- locale fallback;
- translation keys validation.

---

## 23. API-контуры

### 23.1. Public Context API

Назначение:

- вернуть текущий commercial context;
- принять ручной выбор страны;
- принять ручной выбор валюты;
- принять ручной выбор языка;
- вернуть confidence flags.

### 23.2. Public Catalog API

Назначение:

- вернуть effective catalog;
- вернуть plans;
- вернуть addons;
- вернуть prices;
- вернуть available billing periods;
- вернуть payment methods.

### 23.3. Quote API

Назначение:

- создать quote;
- обновить quote;
- применить promo;
- добавить addon;
- удалить addon;
- пересчитать quote;
- отменить quote.

### 23.4. Checkout API

Назначение:

- создать payment session;
- проверить quote;
- выбрать payment provider;
- вернуть redirect/payment data;
- показать итоговую сумму.

### 23.5. Webhook API

Назначение:

- принять webhook payment provider;
- проверить событие;
- обновить order;
- активировать subscription;
- создать provisioning job.

### 23.6. Subscription API

Назначение:

- получить текущую подписку;
- получить историю подписок;
- продлить подписку;
- купить addon;
- отменить подписку;
- получить VPN-доступ;
- получить subscription URL/QR.

### 23.7. Admin Pricing API

Назначение:

- управлять price books;
- управлять price rules;
- публиковать;
- откатывать;
- валидировать;
- preview.

### 23.8. Admin Country API

Назначение:

- управлять странами;
- управлять группами стран;
- управлять country overrides;
- управлять currency settings;
- управлять availability.

### 23.9. Admin Provisioning API

Назначение:

- управлять provisioning profiles;
- смотреть jobs;
- повторять failed jobs;
- запускать reconciliation;
- смотреть Remnawave mapping.

---

## 24. Frontend requirements

### 24.1. Pricing page

Pricing page должен:

- получить context из backend;
- получить catalog из backend;
- показать country selector;
- показать currency selector, если доступен;
- показать tariffs;
- показать billing period switcher;
- показать addons;
- показать скидки;
- показать trial, если доступен;
- показать финальную цену;
- создать quote через backend.

### 24.2. Country selector

Country selector должен:

- быть доступен на pricing page;
- быть доступен в checkout;
- быть доступен в profile settings;
- показывать текущую страну;
- позволять пользователю изменить страну;
- после изменения страны пересчитывать catalog;
- не менять страну неожиданно без действия пользователя.

### 24.3. Currency selector

Currency selector должен:

- показываться только если доступно несколько валют;
- использовать список валют из backend;
- пересчитывать catalog через backend;
- инвалидировать старый quote;
- показывать финальную валюту до оплаты.

### 24.4. Language switcher

Language switcher должен:

- работать независимо от страны и валюты;
- сохранять выбор пользователя;
- менять только UI locale;
- не менять pricing country автоматически;
- не менять currency автоматически.

### 24.5. Checkout page

Checkout page должен:

- использовать quote ID;
- получать итоговую сумму из backend;
- показывать выбранный plan;
- показывать addons;
- показывать валюту;
- показывать billing period;
- показывать payment methods;
- не рассчитывать сумму локально;
- реагировать на expired/invalidated quote;
- предлагать пересоздать quote при изменении context.

---

## 25. Telegram Bot и Telegram Mini App

### 25.1. Общие требования

Telegram-каналы должны использовать общий backend catalog.

Нельзя делать отдельную Telegram-таблицу цен.

### 25.2. Telegram Bot flow

1. Пользователь запускает bot.
2. Bot получает Telegram language hint.
3. Bot отправляет user/session context в backend.
4. Backend возвращает commercial context.
5. Bot показывает тарифы из backend.
6. Пользователь выбирает тариф.
7. Bot создает quote через backend.
8. Пользователь оплачивает.
9. Backend получает webhook.
10. Worker выдает доступ через Remnawave.
11. Bot отправляет пользователю subscription URL/QR.

### 25.3. Telegram Mini App flow

1. Пользователь открывает Mini App.
2. Mini App передает initData в backend.
3. Backend проверяет initData.
4. Backend определяет locale/country/currency context.
5. Mini App получает catalog.
6. Пользователь выбирает тариф/addons.
7. Mini App создает quote.
8. Checkout проходит через backend/payment provider.
9. После оплаты Mini App получает статус подписки.

### 25.4. Locale в Telegram

Telegram language hint используется только как подсказка языка.

Страна тарифа определяется через backend context и country selector.

---

## 26. Partner Portal

### 26.1. Partner-specific catalog

Partner Portal должен получать catalog через тот же backend, но с partner context.

Partner overrides могут задавать:

- доступные tariffs;
- специальные prices;
- специальные addons;
- специальные promo;
- storefront visibility;
- partner-specific trial;
- partner revenue metadata.

### 26.2. Partner pricing rules

Partner override должен применяться после country/channel rules, если он более специфичен.

Порядок:

1. Global default.
2. Country group.
3. Country.
4. Channel.
5. Partner.
6. Segment.
7. Promo.

### 26.3. Partner preview

Admin должен уметь preview catalog для конкретного partner.

---

## 27. Mobile и Desktop

### 27.1. Mobile

Mobile App должен:

- получать catalog из backend;
- использовать mobile channel;
- показывать country/currency/locale из context;
- поддерживать subscription status;
- получать VPN configuration после provisioning;
- учитывать отдельный flow для in-app purchases, если он включен.

### 27.2. Desktop

Desktop Client должен:

- получать subscription status;
- показывать upgrade/renewal options из backend;
- не хранить цены локально;
- получать VPN access data после provisioning;
- корректно реагировать на expired/suspended/provisioning_failed.

---

## 28. Кэширование

### 28.1. Catalog cache

Effective catalog можно кэшировать по ключу:

- price book version;
- country;
- currency;
- locale;
- channel;
- partner;
- segment;
- promo state.

### 28.2. Cache invalidation

Cache должен инвалидироваться при:

- публикации нового Price Book;
- rollback;
- изменении country settings;
- изменении addon settings;
- изменении payment provider settings;
- изменении promotion rules.

### 28.3. Quote не должен быть обычным cache

Quote — transactional object.

Он должен храниться отдельно, иметь expiration и snapshot.

---

## 29. Events

Система должна публиковать доменные события:

- PriceBookPublished;
- PriceBookRolledBack;
- CountrySettingsChanged;
- CatalogResolved;
- QuoteCreated;
- QuoteInvalidated;
- QuoteExpired;
- CheckoutStarted;
- PaymentSucceeded;
- PaymentFailed;
- SubscriptionCreated;
- SubscriptionActivated;
- SubscriptionExpired;
- AddonPurchased;
- ProvisioningRequested;
- ProvisioningSucceeded;
- ProvisioningFailed;
- RemnawaveSyncRequested;
- RemnawaveSyncSucceeded;
- RemnawaveSyncFailed;
- UserCountryChanged;
- UserCurrencyChanged;
- UserLocaleChanged.

---

## 30. Observability

### 30.1. Метрики

Нужно собирать:

- catalog resolution latency;
- quote creation latency;
- checkout start count;
- payment success rate;
- payment failure rate;
- country selector usage;
- currency selector usage;
- fallback usage rate;
- unknown country rate;
- low confidence country rate;
- quote invalidation rate;
- quote expiration rate;
- addon attach rate;
- plan conversion rate;
- provisioning success rate;
- provisioning failure rate;
- provisioning retry count;
- Remnawave sync lag;
- Price Book publish errors.

### 30.2. Dashboards

Нужны dashboards:

- Pricing health;
- Checkout health;
- Payment health;
- Provisioning health;
- Country performance;
- Addon performance;
- Telegram sales;
- Web sales;
- Partner sales;
- Remnawave sync.

### 30.3. Логи

Логи должны помогать понять:

- какой catalog был выбран;
- почему применился fallback;
- почему тариф скрыт;
- почему quote invalidated;
- почему provisioning failed;
- какой Remnawave operation был выполнен.

---

## 31. Безопасность и устойчивость

### 31.1. Минимальные требования

Система должна:

- проверять payment webhooks;
- использовать idempotency keys;
- ограничивать частую смену страны при подозрительном поведении;
- защищать Admin API;
- логировать admin changes;
- валидировать Telegram initData;
- не доверять суммам с frontend;
- не доверять тарифам с frontend;
- не доверять currency с frontend без backend validation;
- не отдавать пользователю чужую subscription data.

### 31.2. Abuse protection

Нужно предусмотреть:

- rate limit на создание quote;
- rate limit на country/currency switching;
- per-user promo usage limits;
- per-session quote limits;
- protection от повторного применения одного webhook;
- protection от покупки несовместимых addons;
- protection от повторной выдачи одного и того же addon.

---

## 32. Тестирование

### 32.1. Unit tests

Проверить:

- fallback global → group → country;
- explicit disabled;
- replace/append/remove behavior;
- price calculation;
- currency selection;
- locale resolver;
- country resolver;
- addon compatibility;
- promotion application;
- quote expiration;
- quote invalidation;
- subscription snapshot;
- provisioning profile selection.

### 32.2. Integration tests

Проверить:

- frontend получает catalog из backend;
- Telegram Bot получает тот же catalog при том же context;
- Mini App получает тот же catalog при том же context;
- quote создается из effective catalog;
- payment webhook активирует subscription;
- provisioning job создает или обновляет Remnawave user;
- повторный webhook не создает дубли;
- addon purchase обновляет subscription;
- country change invalidates quote;
- currency change invalidates quote;
- Price Book rollback возвращает предыдущие цены.

### 32.3. E2E scenarios

Обязательные сценарии:

1. Пользователь без страны открывает pricing page.
2. Пользователь выбирает страну вручную.
3. Пользователь из страны без override получает default price.
4. Пользователь из страны с override получает country price.
5. Пользователь меняет валюту.
6. Пользователь покупает месячный тариф.
7. Пользователь покупает годовой тариф.
8. Пользователь применяет promo code.
9. Пользователь покупает addon вместе с тарифом.
10. Пользователь докупает addon к активной подписке.
11. Telegram Bot показывает те же цены, что web.
12. Telegram Mini App показывает те же цены, что web.
13. RTL locale отображается корректно.
14. Quote истекает и пересоздается.
15. Payment webhook приходит дважды.
16. Remnawave provisioning падает и повторяется.
17. Admin публикует новый Price Book.
18. Admin делает rollback.
19. Existing subscription сохраняет старый snapshot.
20. Partner получает partner-specific catalog.

---

## 33. Acceptance criteria

Система считается готовой, если:

1. Все цены приходят из backend.
2. Frontend не содержит тарифной бизнес-логики.
3. Telegram Bot не содержит тарифной бизнес-логики.
4. Telegram Mini App не содержит тарифной бизнес-логики.
5. Для страны без override применяется default.
6. Для страны с override применяется override.
7. Addons поддерживают country/channel availability.
8. Для каждого active offer есть цена и валюта.
9. Для каждого active offer есть provisioning profile.
10. Quote создается backend и имеет expiration.
11. Quote invalidated при смене страны, валюты или addons.
12. Payment provider получает сумму из quote.
13. Повторный webhook не создает дубли.
14. Subscription snapshot сохраняется после оплаты.
15. Старые subscription snapshots не меняются после изменения Price Book.
16. Remnawave provisioning idempotent.
17. Worker умеет retry provisioning.
18. Admin может preview effective catalog.
19. Admin может publish Price Book.
20. Admin может rollback Price Book.
21. Locale определяется отдельно от страны.
22. Currency определяется отдельно от locale.
23. VPN/proxy signal снижает confidence IP-страны.
24. Пользователь может выбрать страну вручную.
25. Web, Bot, Mini App, Mobile и Partner получают catalog из единого backend.

---

## 34. Поэтапная реализация

### 34.1. Этап 1 — Core catalog MVP

Реализовать:

- Plan;
- Plan Version;
- Addon;
- Country Settings;
- Country Group;
- Price Book;
- basic fallback;
- Public Catalog API;
- Admin CRUD;
- global default prices.

Результат этапа:

- backend отдает единый catalog;
- frontend показывает цены из backend;
- country override уже работает для базовых случаев.

### 34.2. Этап 2 — Context Resolver

Реализовать:

- locale resolver;
- country resolver;
- currency resolver;
- confidence levels;
- country selector;
- currency selector;
- profile/cookie persistence;
- Telegram language hint support.

Результат этапа:

- пользователь видит корректную локаль;
- пользователь может выбрать страну;
- валюта выбирается через backend rules.

### 34.3. Этап 3 — Quote и checkout

Реализовать:

- Quote API;
- quote expiration;
- quote invalidation;
- payment provider compatibility;
- checkout handoff;
- webhook idempotency;
- subscription snapshot.

Результат этапа:

- оплата идет только через backend quote;
- сумма не берется с frontend;
- подписка получает snapshot.

### 34.4. Этап 4 — Remnawave provisioning

Реализовать:

- Provisioning Profile;
- Provisioning Job;
- worker command;
- Remnawave user creation/update;
- idempotency;
- retry;
- reconciliation;
- admin repair action.

Результат этапа:

- после оплаты доступ выдается автоматически;
- ошибки provisioning видны и исправляемы.

### 34.5. Этап 5 — Addons full flow

Реализовать:

- addon compatibility matrix;
- addon country/channel pricing;
- addon purchase quote;
- addon provisioning;
- addon snapshot;
- addon admin preview.

Результат этапа:

- addons можно покупать вместе с тарифом и отдельно;
- addons корректно меняют Remnawave-доступ.

### 34.6. Этап 6 — Multi-channel rollout

Подключить:

- Customer Frontend;
- Telegram Bot;
- Telegram Mini App;
- Partner Portal;
- Mobile App;
- Desktop Client.

Результат этапа:

- все каналы используют единый catalog и quote flow.

### 34.7. Этап 7 — Observability и оптимизация

Реализовать:

- metrics;
- dashboards;
- catalog cache;
- pricing health reports;
- provisioning health reports;
- country/currency analytics;
- conversion analytics.

Результат этапа:

- команда видит качество работы pricing, checkout и provisioning.

---

## 35. Рекомендуемая приоритетность разработки

### Высший приоритет

1. Backend Catalog API.
2. Admin Price Book.
3. Country Settings.
4. Currency Settings.
5. Fallback engine.
6. Quote API.
7. Subscription Snapshot.
8. Remnawave Provisioning Profile.
9. Web pricing page integration.

### Средний приоритет

1. Addons full flow.
2. Telegram Bot pricing integration.
3. Telegram Mini App pricing integration.
4. Partner overrides.
5. Catalog preview.
6. Rollback.
7. Reconciliation worker.

### Позже

1. Advanced segmentation.
2. Advanced promotion stacking.
3. Complex upgrade/downgrade math.
4. Partner-specific storefront customization.
5. Deep analytics.
6. A/B testing price experiments.

---

## 36. Итоговая целевая модель

Целевая модель CyberVPN должна быть такой:

1. **Backend управляет тарифами, ценами, странами, валютами, addons и quote.**
2. **Admin Panel управляет настройками через draft/publish/rollback.**
3. **Frontend, Telegram Bot, Mini App, Mobile, Desktop и Partner Portal только отображают effective catalog.**
4. **Locale определяется отдельно от страны.**
5. **Валюта определяется отдельно от языка.**
6. **Страна пользователя определяется через context resolver и может быть изменена пользователем вручную.**
7. **Если пользователь зашел через VPN/proxy, IP используется только как слабая подсказка.**
8. **Quote фиксирует цену перед оплатой.**
9. **Payment provider получает сумму только из backend quote.**
10. **После оплаты subscription получает immutable snapshot.**
11. **Remnawave используется для технической выдачи VPN-доступа.**
12. **Provisioning выполняется через worker, idempotency, retry и reconciliation.**
13. **Addons управляются так же гибко, как основные тарифы.**
14. **Country/group/channel/partner overrides дают гибкую настройку без отдельной логики в каждом приложении.**
15. **Все каналы продаж работают через единый commercial backend.**

Такое решение позволит CyberVPN масштабировать 39 локалей, разные страны, разные валюты, гибкие тарифы, addons, Telegram-сценарии, partner-продажи и Remnawave provisioning без расхождения цен между каналами и без ручного дублирования логики.
