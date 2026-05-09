# CyberVPN Launch Questionnaire Answers

**Дата:** 2026-04-25
**Основание:** только то, что видно в репозитории `/home/beep/projects/VPNBussiness`.
**Формат:** каждый пункт содержит исходный вопрос, ответ и обоснование.
**Правило чтения:** если бизнес-решение, credential, live-инфраструктура или внешний аккаунт не видны в репозитории, ответ: **Не знаю**.

---

## 1. Видение продукта и MVP

### 1. Вопрос

Что ты считаешь **первым успешным запуском** CyberVPN: первые платящие пользователи, закрытая beta, публичный сайт, Telegram-продажи, мобильное приложение или что-то другое?

**Ответ:**

По репозиторию самый реалистичный первый успешный запуск: invite-only/closed beta с `backend` + `frontend` customer cabinet + Telegram Bot/Mini App + Remnawave + worker + admin panel + payments.

### 2. Вопрос

Какой самый узкий MVP ты готов запустить первым: только Telegram bot/Mini App, web-кабинет + bot, web + bot + payments, или сразу полноценная экосистема?

**Ответ:**

Не знаю как решение владельца. По текущей готовности узкий MVP лучше делать как web-кабинет + bot/Mini App + payments + provisioning, без partner/native/Helix как обязательных частей.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: структуре монорепозитория, README, досье и текущих web/backend/product поверхностях, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 3. Вопрос

Какую главную проблему пользователя CyberVPN решает лучше конкурентов?

**Ответ:**

В проекте заложены акценты на privacy/no-logs, anti-censorship/private access, Telegram-first flow, multi-platform, Remnawave + Helix (кастомные протокол) + desktop and mobile app с киллер фичами

### 4. Вопрос

Для кого продукт в первую очередь: обычные пользователи, expats, digital nomads, русскоязычная аудитория, азиатские рынки, B2B, реселлеры, партнёры?

**Ответ:**

По локалям и Telegram-акценту видна широкая международная и русскоязычная ориентация; по partner-модулю также виден B2B/reseller потенциал.

### 5. Вопрос

Есть ли у проекта позиционирование: “дешёвый VPN”, “стабильный VPN”, “VPN для Telegram”, “VPN для бизнеса”, “private transport”, “anti-censorship”, “premium privacy”?

**Ответ:**

В коде и текстах есть несколько возможных позиций: privacy/no-logs, access-product, Telegram VPN, premium/private transport, partner-ready VPN platform. Одно финальное позиционирование не зафиксировано.

### 6. Вопрос

Какие 3 функции должны работать идеально в первый день запуска?

**Ответ:**

По проекту критичны: регистрация/логин, оплата, выдача VPN-доступа. Для первого дня это должны быть 3 идеально работающие функции.

**Обоснование:**

Это основано на области: структуре монорепозитория, README, досье и текущих web/backend/product поверхностях. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 7. Вопрос

Какие функции можно полностью отключить на старте без вреда для бизнеса?

**Ответ:**

На старте можно отключить partner portal, payouts, advanced growth codes, Helix, desktop/mobile/Android TV release, browser extension, broad analytics/monitoring для пользователя.

**Обоснование:**

Это основано на области: структуре монорепозитория, README, досье и текущих web/backend/product поверхностях. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 8. Вопрос

Что для тебя важнее на первом этапе: скорость запуска, техническая надёжность, юридическая чистота, revenue, набор первых пользователей или проверка гипотезы?

**Ответ:**

Не знаю. По repo видно, что для launch надо приоритизировать надежность auth/payment/provisioning и операционную доказательность, иначе launch surface слишком широкий.

### 9. Вопрос

Есть ли уже название бренда окончательно: CyberVPN, ozoxy.ru или другое?

**Ответ:**

В проекте используются `CyberVPN`

### 10. Вопрос

Какой домен будет основным публичным доменом продукта?

**Ответ:**

Не знаю окончательно.

### 11. Вопрос

Какой домен будет использоваться для админки?

**Ответ:**

Пока не знаю

### 12. Вопрос

Какой домен будет использоваться для партнёрского портала?

**Ответ:**

Пока не знаю

### 13. Вопрос

Нужно ли пользователю понимать, что под капотом используется Remnawave/Xray, или это должно быть полностью скрыто?

**Ответ:**

По продуктовой логике проекта Remnawave/Xray лучше скрывать от пользователя. В UI есть пользовательские config/QR/subscription flows, а Remnawave описан как backend/control-plane.

### 14. Вопрос

Планируется ли запускать CyberVPN как самостоятельный бренд или как white-label/partner-ready платформу?

**Ответ:**

В repo есть оба направления: самостоятельный B2C CyberVPN и partner/white-label/storefront платформа.

### 15. Вопрос

Есть ли уже сформулированное УТП в одном предложении?

**Ответ:**

Единого УТП в одном предложении нету

## 2. Целевая аудитория и рынки

### 16. Вопрос

В каких странах ты хочешь запускаться в первую очередь?

**Ответ:**

Россия, Китай, азия где это необходимо. В целом на старте у нас 38 языков

### 17. Вопрос

Какие языки реально нужны на первом запуске?

**Ответ:**

Все 38 языков и они уже готовы

### 18. Вопрос

Нужна ли поддержка английского как основного языка, если default locale сейчас `en-EN`?

**Ответ:**

Да, если не принято иное бизнес-решение: `en-EN` является default locale.

**Обоснование:**

Это основано на области: i18n-конфигурации, наборам локалей, маркетинговым страницам и отсутствию зафиксированного country launch policy. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 19. Вопрос

Нужен ли русский язык как основной для первого запуска?

**Ответ:**

Нет

### 20. Вопрос

Какие страны или регионы ты точно не хочешь обслуживать?

**Ответ:**

Запрещенные регионы/санкционные ограничения в launch policy не зафиксированы.

### 21. Вопрос

Будет ли сервис доступен пользователям из ЕС?

**Ответ:**

В UI/docs есть GDPR/Privacy Policy готовность

### 22. Вопрос

Будет ли сервис доступен пользователям из России?

**Ответ:**

Будет

### 23. Вопрос

Будет ли сервис доступен пользователям из Китая, Ирана, Турции, ОАЭ или других стран с ограничениями?

**Ответ:**

Будет, у нас независимый VPN

### 24. Вопрос

Есть ли у тебя понимание, какие протоколы и локации нужны твоей первой аудитории?

**Ответ:**

В проекте есть Remnawave/Xray, V2Ray, VPN clients, XHTTP

### 25. Вопрос

Какой тип пользователей для тебя приоритетнее: те, кто покупает через сайт, через Telegram, через партнёра или через мобильное приложение?

**Ответ:**

По repo наиболее готовый ранний канал: Telegram + web/Mini App + Сайт

### 26. Вопрос

Планируется ли запускать B2C и B2B одновременно?

**Ответ:**

Очень хотелось бы, но наверное врядли. B2C вероятнее всего в первом этапе

### 27. Вопрос

Будет ли отдельное предложение для реселлеров?

**Ответ:**

Да, в проекте есть partner/reseller/storefront/payout модель. Нужна ли на первом запуске: хотелось бы, это хороший катализатор, но врядли

### 28. Вопрос

Будут ли корпоративные аккаунты или только индивидуальные подписки?

**Ответ:**

Корпоративные/partner/workspace модели есть. Будут ли на старте: не знаю.

### 29. Вопрос

Планируешь ли ты продавать VPN как privacy-продукт или как access-продукт?

**Ответ:**

access-продукт

### 30. Вопрос

Есть ли уже тестовая группа пользователей, готовая участвовать в закрытой beta?

**Ответ:**

Есть


## 3. Тарифы, подписки и монетизация

### 31. Вопрос

Какие тарифы будут на первом запуске?

**Ответ:**

Будут публичные и приватные

### 32. Вопрос

Будут ли месячные, квартальные, годовые подписки?

**Ответ:**

Да


### 33. Вопрос

Будет ли lifetime-тариф?

**Ответ:**

Нет


### 34. Вопрос

Будет ли бесплатный trial?

**Ответ:**

Да, trial заложен: `TRIAL_ENABLED=true` в bot env example и backend `trial` API.


### 35. Вопрос

Если trial будет, оставляем ли текущую идею `2 дня / 2 GB`?

**Ответ:**

Нет, там будет фиксировано по 1 количеству устройства и 3 дня

### 36. Вопрос

Trial должен быть доступен всем или только по invite/referral?

**Ответ:**

Всем


### 37. Вопрос

Будет ли ограничение по устройствам на тариф?

**Ответ:**

Да


### 38. Вопрос

Будет ли ограничение по трафику на тариф?

**Ответ:**

Нет


### 39. Вопрос

Будет ли fair-use policy?

**Ответ:**

Нет

### 40. Вопрос

Будут ли add-ons: дополнительные устройства, трафик, premium servers, dedicated IP?

**Ответ:**

Да

### 41. Вопрос

Будут ли разные тарифы для разных стран?

**Ответ:**

Пока нет, но важно заложить данную возможность на старте


### 42. Вопрос

Будет ли цена отображаться в USD, EUR, RUB, crypto, Telegram Stars или локальной валюте?

**Ответ:**

Цена будет отображаться в USD, но на странице сайта при выборе языка будет указана местная валюта с округлением красивых цифр в большую сторону

### 43. Вопрос

Будет ли wallet полноценной системой баланса или только интерфейсом истории платежей?

**Ответ:**

По backend это полноценный wallet domain: wallets, transactions/withdrawal, referral/partner earnings.

### 44. Вопрос

Нужна ли автопролонгация подписок на первом запуске?

**Ответ:**

Да

### 45. Вопрос

Если автопролонгация нужна, через каких провайдеров она должна работать?

**Ответ:**

Не знаю

### 46. Вопрос

Что происходит, если оплата не прошла: grace period, instant disable, уведомление, ручное продление?

**Ответ:**

grace period


### 47. Вопрос

Будет ли возможность вручную выдать подписку пользователю через админку?

**Ответ:**

Да, по admin/customer operations и subscription/admin surfaces это предусмотрено

### 48. Вопрос

Нужны ли промокоды на старте?

**Ответ:**

Да, promo/growth codes сильно проработаны.

### 49. Вопрос

Нужны ли gift codes на старте?

**Ответ:**

Да

### 50. Вопрос

Нужна ли referral-программа на старте или её лучше отложить?

**Ответ:**

Да

## 4. Платежи

### 51. Вопрос

Какой платёжный провайдер должен быть основным на первом запуске?

**Ответ:**

Пока точно не определён

### 52. Вопрос

CryptoBot, Telegram Stars и YooKassa — все нужны сразу или только один-два?

**Ответ:**

Да, там все нужны будут провайдеры, не только эти

### 53. Вопрос

Есть ли уже реальные аккаунты провайдеров?

**Ответ:**

Нету

### 54. Вопрос

Есть ли sandbox/test credentials для каждого провайдера?

**Ответ:**

Нету

### 55. Вопрос

Есть ли production credentials для каждого провайдера?

**Ответ:**

Нету

### 56. Вопрос

Кто будет отвечать за сверку платежей?

**Ответ:**

В repo есть reconciliation scripts/jobs/domains, но владелец процесса не назначен.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: payment/refund/dispute/reconciliation доменам backend, worker-клиентам и env-шаблонам providers, поэтому фиксирую неизвестное состояние.

### 57. Вопрос

Как часто нужна reconciliation-сверка: вручную, ежедневно, автоматически через worker?

**Ответ:**

По worker/backend есть автоматизация reconciliation, особенно Telegram Stars/refunds/reporting. Частота как бизнес-правило обязательно.


### 58. Вопрос

Нужно ли поддерживать возвраты на старте?

**Ответ:**

Refunds есть в backend domain, UI strings и partner docs. Нужно ли поддерживать на старте: юридически да

### 59. Вопрос

Нужны ли dispute/chargeback-процессы на старте?

**Ответ:**

Payment disputes есть в backend domain. Полный chargeback/dispute process на старте нужен.

### 60. Вопрос

Какие статусы платежей должны считаться финальными?

**Ответ:**

Пока точно не утверждены

### 61. Вопрос

Что делать с платежом, если provider webhook пришёл, а provisioning VPN-доступа упал?

**Ответ:**

В проекте есть worker/retry/reconciliation и access delivery domains, значит правильный путь: payment stays paid, provisioning retries/escalates. Конкретная реализация для всех providers не подтверждена.

**Обоснование:**

Это основано на области: payment/refund/dispute/reconciliation доменам backend, worker-клиентам и env-шаблонам providers. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 62. Вопрос

Что делать, если пользователь оплатил, но аккаунт не найден?

**Ответ:**

Не знаю. Нужна orphan payment policy/support flow;


### 63. Вопрос

Что делать, если webhook пришёл дважды?

**Ответ:**

Должна быть idempotency.

### 64. Вопрос

Проверена ли idempotency-логика платежных webhook’ов?

**Ответ:**

Тесты/реализации есть частично, но я не запускал payment webhook idempotency suite.

### 65. Вопрос

Нужно ли отправлять пользователю чек, invoice или receipt?

**Ответ:**

Invoice/receipt domains и UI есть. Обязательность чеков/receipt зависит от юрлица/провайдера; не знаю.


### 66. Вопрос

Кто юридически является продавцом услуги?

**Ответ:**

Не знаю. Юридический продавец не указан.


### 67. Вопрос

Нужна ли интеграция с налоговой/фискализацией?

**Ответ:**

Нет

### 68. Вопрос

Какой минимальный платёж ты готов принимать?

**Ответ:**

Не знаю. Минимальный платеж не зафиксирован. Возможно это 1$

### 69. Вопрос

Будут ли ручные платежи, например crypto вручную, переводом или через саппорт?

**Ответ:**

В partner UI есть manual/invoice hints; ручные платежи как launch process не знаю.

### 70. Вопрос

Нужно ли ограничивать payment methods по стране пользователя?

**Ответ:**

Нет

## 5. Регистрация, auth и аккаунты

### 71. Вопрос

На старте регистрация будет открытой или invite-only?

**Ответ:**

Открытой

### 72. Вопрос

Текущая backend-конфигурация по умолчанию говорит `REGISTRATION_ENABLED=false` и `REGISTRATION_INVITE_REQUIRED=true`. Это соответствует твоему launch-подходу?

**Ответ:**

Ну хотелось бы чтобы и открытой была регистрация, так как мы потихоничку хотим привлекать пользователя.

### 73. Вопрос

Какие способы входа нужны на первом запуске: email/password, magic link, Telegram, OAuth, mobile auth?

**Ответ:**

email/password, magic link, OTP, Telegram Mini App/Bot link, OAuth, mobile auth, login/password .

### 74. Вопрос

Нужна ли обязательная email-верификация?

**Ответ:**

OTP/email verification реализована. Но у нас так же есть способ входа через login/password - что не требуется email верификацию

### 75. Вопрос

Нужна ли 2FA для обычных пользователей?

**Ответ:**

2FA да и она уже реализована

### 76. Вопрос

Нужна ли 2FA для администраторов обязательно?

**Ответ:**

Да

### 77. Вопрос

Какие OAuth-провайдеры реально нужны?

**Ответ:**

Google, Discord, GitHub, Telegram/OIDC. Уже реализовано


### 78. Вопрос

Будет ли Telegram аккаунт главным идентификатором пользователя или дополнительным linked account?

**Ответ:**

Telegram может быть primary entrypoint, но backend поддерживает и email/OAuth identities. Но здесь нужно продумать привязку аккаунта телеграм или email в один аккаунт если что.


### 79. Вопрос

Может ли один пользователь иметь несколько способов входа?

**Ответ:**

Да, по OAuth account linking и Telegram link один пользователь может иметь несколько способов входа.

### 80. Вопрос

Как решать конфликт, если email и Telegram принадлежат разным аккаунтам?

**Ответ:**

Нужно это продумать тчательно продумать и грамотно, обязательно.


### 81. Вопрос

Нужна ли функция удаления аккаунта пользователем?

**Ответ:**

Да, delete account routes/UI strings есть.


### 82. Вопрос

Нужна ли функция export data для пользователя?

**Ответ:**

В UI strings есть export data/GDPR text.

### 83. Вопрос

Какой username/display name должен видеть пользователь в кабинете?

**Ответ:**

В моделях есть email, username/display_name/telegram_username. Какой показывать финально: не знаю.

### 84. Вопрос

Нужны ли роли обычных пользователей: user, reseller, partner, admin?

**Ответ:**

Роли видны: admin roles, partner roles, user/partner flags.

### 85. Вопрос

Какой минимальный набор полей пользователя нужен для покупки подписки?

**Ответ:**

Минимум зависит от provider. По проекту можно купить через Telegram identity или email account;


## 6. VPN provisioning и Remnawave

### 86. Вопрос

Remnawave будет production-authoritative backend для VPN-доступа на старте?

**Ответ:**

Да, по проекту Remnawave является authoritative backend для VPN-доступа на старте; Helix не заменяет его.


### 87. Вопрос

Есть ли уже production Remnawave instance?

**Ответ:**

Нет.

### 88. Вопрос

Есть ли staging Remnawave instance отдельно от production?

**Ответ:**

Нет.

### 89. Вопрос

Какие VPN-протоколы ты хочешь дать пользователю на первом запуске?

**Ответ:**

Не знаю финально. Есть Remnawave/Xray/V2Ray-related code, Android/Flutter parsers, VLESS/Xray references в docs. XHTTP обязателен. Затем Helix, Verta, Beep

### 90. Вопрос

Будет ли пользователь получать QR-код, subscription URL, config file или всё сразу?

**Ответ:**

Всё сразу

### 91. Вопрос

Как быстро после оплаты должен выдаваться VPN-доступ?

**Ответ:**

По продукту доступ должен выдаваться сразу после paid/final payment, с worker retry при сбое.

### 92. Вопрос

Как backend должен реагировать, если Remnawave API недоступен?

**Ответ:**

В проекте есть retries/resilience/worker. Правильное поведение: не терять оплату, поставить provisioning в retry/support state. Конкретный финальный runbook не вижу.

### 93. Вопрос

Нужна ли очередь повторного provisioning через worker?

**Ответ:**

Да, это нужно. Worker/scheduler как раз должен закрывать повторный provisioning/reconciliation.


### 94. Вопрос

Нужно ли вручную переиздать VPN credentials из админки?

**Ответ:**

Да, по admin/customer operations и restore VPN UI это предусмотрено концептуально.

### 95. Вопрос

Нужно ли ограничивать количество устройств на уровне Remnawave или только на уровне backend?

**Ответ:**

на уровне Remnawave но на уровне backend я так понимаю тоже нужно если у нас свои протоколы будут

### 96. Вопрос

Как обрабатывать истёкшие подписки: отключать сразу, через grace period, через delayed job?

**Ответ:**

через grace period

### 97. Вопрос

Что делать, если подписка продлена, но Remnawave не обновил доступ?

**Ответ:**

Должен быть retry/reconciliation/support escalation.

### 98. Вопрос

Нужно ли показывать пользователю фактическое потребление трафика?

**Ответ:**

Да, usage/traffic API и UI есть. Фактическая точность зависит от Remnawave integration; live proof не знаю.

### 99. Вопрос

Какие серверные регионы будут доступны на старте?

**Ответ:**

Их порядка 12 шт

### 100. Вопрос

Есть ли резервные VPN-ноды, если основная локация упала?

**Ответ:**

Должны быть

### 101. Вопрос

Кто будет заниматься обслуживанием VPN-нод?

**Ответ:**

Не знаю пока что

### 102. Вопрос

Есть ли политика обновления Xray/Remnawave?

**Ответ:**

Есть `REMNAWAVE_UPGRADE_GUARDRAILS.md` и version baseline 2.7.4. Это policy skeleton; live ownership не знаю.

### 103. Вопрос

Нужно ли делать canary rollout для новых VPN-нод?

**Ответ:**

Да, для новых VPN-нод runbooks предполагают canary/edge verification.

### 104. Вопрос

Какой SLA по доступности VPN ты хочешь декларировать пользователям?

**Ответ:**

Не знаю.

### 105. Вопрос

Нужно ли скрывать технические config links от support/admin логов?

**Ответ:**

Да, это нужно. В проекте есть log sanitization/PII concerns; config links должны не попадать в logs/support. Подтвержденный audit этого не знаю.

## 7. Telegram Bot и Telegram Mini App

### 106. Вопрос

Telegram Bot — это основной канал продаж или дополнительный?

**Ответ:**

По проекту Telegram выглядит как один из основных ранних каналов продаж, не просто дополнительный. Но и сайт так же основной

### 107. Вопрос

Есть ли уже production bot token?

**Ответ:**

Не знаю. Production bot token не виден и не должен быть в repo.

### 108. Вопрос

Есть ли отдельный staging bot?

**Ответ:**

Должен быть

### 109. Вопрос

Какой user flow в Telegram должен быть главным: trial, покупка тарифа, получение конфигурации, support или всё вместе?

**Ответ:**

Всё вместе

### 110. Вопрос

Mini App должна работать как полноценный кабинет или как лёгкая витрина с оплатой?

**Ответ:**

Mini App выглядит как полноценный облегченный кабинет: home/plans/payments/devices/profile/referral/wallet.

### 111. Вопрос

Нужно ли запускать Mini App раньше web-кабинета?

**Ответ:**

Нужно вместе

### 112. Вопрос

Telegram Stars нужны как обязательный платёжный метод?

**Ответ:**

Да

### 113. Вопрос

Какой контент будет в Telegram bot: команды, меню, onboarding, FAQ, support?

**Ответ:**

В bot docs/env заложены команды, меню, payments, trial, referral, support, locales.

### 114. Вопрос

Нужно ли логировать Telegram user id в backend как основной customer id?

**Ответ:**

Telegram ID хранится в моделях и auth flows; как основной customer id юридически/продуктово: не знаю.

### 115. Вопрос

Как обрабатывать пользователя, который начал в Telegram, а потом зашёл через web?

**Ответ:**

В проекте есть Telegram account linking/bot link/OAuth flows. Конфликтный flow должен связывать аккаунты;

### 116. Вопрос

Нужна ли привязка email к Telegram-пользователю?

**Ответ:**

Обязательно

### 117. Вопрос

Нужно ли уведомлять пользователя в Telegram о скором окончании подписки?

**Ответ:**

Да, notification/subscription expiration logic видна в worker/bot areas.

### 118. Вопрос

Нужны ли Telegram-уведомления о payment failure?

**Ответ:**

В проекте есть payment failure/payment status messaging; включать ли Telegram notifications: не знаю.


### 119. Вопрос

Нужен ли anti-spam/rate-limit для Telegram bot?

**Ответ:**

Да. В backend есть Telegram rate limit dependencies, в bot/services есть rate limiting.

### 120. Вопрос

Кто будет отвечать за поддержку пользователей, пришедших через Telegram?

**Ответ:**

ИИ бот на первой линии

## 8. Клиентский web-кабинет

### 121. Вопрос

Что именно должен видеть пользователь на главной странице кабинета после входа?

**Ответ:**

По плану user cabinet: subscription health, VPN readiness, traffic, devices, wallet, payments, referrals, profile/security, notifications, diagnostics/support.

### 122. Вопрос

Какие элементы текущего dashboard выглядят слишком “операторскими” и должны быть скрыты от обычного клиента?

**Ответ:**

Operator/admin элементы: users, partner, analytics, monitoring/security, server matrix/ops telemetry, total users/nodes. Это отмечено в user cabinet plan.


### 123. Вопрос

Пользователь должен видеть список серверов или только кнопку “подключиться”?

**Ответ:**

Не знаю. В проекте есть server list ну и там же используется страница подписки то есть выдаётся link подписки

### 124. Вопрос

Нужно ли показывать technical diagnostics обычному пользователю?

**Ответ:**

Ограниченно. Diagnostics нужны, но обычному пользователю лучше показывать actionable status, а не operator metrics.


### 125. Вопрос

Нужна ли страница “Devices” на первом запуске?

**Ответ:**

Есть device credentials/devices surfaces. Ответ - ДА

### 126. Вопрос

Нужна ли страница “Wallet” на первом запуске?

**Ответ:**

Wallet уже есть. Да

### 127. Вопрос

Нужна ли страница “Referral” на первом запуске?

**Ответ:**

Referral есть. Да

### 128. Вопрос

Нужна ли страница “Monitoring” обычному пользователю?

**Ответ:**

Нет для обычного пользователя. Monitoring выглядит admin/operator-only.


### 129. Вопрос

Нужна ли страница “Analytics” обычному пользователю?

**Ответ:**

Нет для обычного пользователя. Analytics выглядит operator/admin/partner-growth surface.


### 130. Вопрос

Какой самый простой customer journey ты хочешь: register → pay → get config → connect?

**Ответ:**

Да, самый простой journey должен быть `register -> pay/trial -> get config -> connect`.

### 131. Вопрос

Нужно ли добавлять onboarding wizard?

**Ответ:**

Не знаю. По сложности продукта onboarding wizard желателен.

### 132. Вопрос

Нужно ли показывать пользователю инструкции для Windows/macOS/iOS/Android/Linux?

**Ответ:**

Да, нужны инструкции для основных платформ; marketing/docs/devices/guides уже есть.

### 133. Вопрос

Нужны ли видеоинструкции или достаточно текстовых гайдов?

**Ответ:**

Не знаю. В repo видны текстовые docs/pages; видео не вижу.

### 134. Вопрос

Нужно ли делать отдельные страницы для “Как подключиться через Telegram”, “Как подключиться на iPhone”, “Как подключиться на Android”?

**Ответ:**

Да, отдельные platform guides логичны; часть public pages уже есть. Полноту не проверял.

### 135. Вопрос

Какие состояния ошибок должны быть красиво обработаны: payment failed, provisioning failed, subscription expired, Remnawave down, no servers available?

**Ответ:**

Все перечисленные состояния должны быть обработаны. В UI уже есть часть states/errors; полное покрытие не знаю.

## 9. Админка

### 136. Вопрос

Кто будет пользоваться админкой на старте?

**Ответ:**

По ролям это owner/support/ops/finance/marketing потенциально.

### 137. Вопрос

Сколько admin-пользователей будет в первый месяц?

**Ответ:**

Не знаю.

### 138. Вопрос

Какие роли в админке нужны: owner, support, finance, ops, marketing, readonly?

**Ответ:**

В проекте есть admin roles/audit/governance, но final role matrix для launch не вижу.

### 139. Вопрос

Нужно ли включать RBAC до запуска?

**Ответ:**

Да, RBAC нужен до запуска админки.

### 140. Вопрос

Какие действия админа должны попадать в audit log?

**Ответ:**

Все privileged actions: user/subscription/payment/refund/provisioning/admin/system config/growth/partner changes. Audit log model/routes есть.

### 141. Вопрос

Можно ли через админку вручную продлить подписку?

**Ответ:**

ДА

### 142. Вопрос

Можно ли через админку вручную отключить пользователя?

**Ответ:**

ДА

### 143. Вопрос

Можно ли через админку пересоздать VPN credentials?

**Ответ:**

ДА

### 144. Вопрос

Можно ли через админку видеть payment attempts?

**Ответ:**

Да, payment attempts domain и admin/partner UI strings видны.

### 145. Вопрос

Можно ли через админку делать refund?

**Ответ:**

Refund domain есть. Может ли админ делать refund end-to-end: не знаю без проверки routes/permissions.

### 146. Вопрос

Можно ли через админку управлять promo/referral/gift codes?

**Ответ:**

Да, promo/referral/gift/growth admin operations хорошо представлены.

**Обоснование:**

Это основано на области: admin workspace, backend admin/customer operations routes, audit/system config/growth/governance surfaces. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 147. Вопрос

Нужно ли закрывать админку по IP allowlist?

**Ответ:**

Да, желательно. В repo final IP allowlist policy для admin не вижу.

### 148. Вопрос

Нужен ли отдельный admin-домен или админка должна быть за VPN/private network?

**Ответ:**

ДА

### 149. Вопрос

Нужно ли подключать SSO для админов?

**Ответ:**

Не знаю. OAuth/SSO providers есть, но admin SSO policy не зафиксирована.

### 150. Вопрос

Какие админские функции опасны и должны быть отключены на первом этапе?

**Ответ:**

Опасные функции: refunds, manual subscription grants, user disable/delete, credential regeneration, payouts, growth-code mass actions, system_config, launch controls. Их стоит flag/role-gate.

**Обоснование:**

Это основано на области: admin workspace, backend admin/customer operations routes, audit/system config/growth/governance surfaces. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

## 10. Partner portal и growth-механики

### 151. Вопрос

Партнёрский портал нужен на первом публичном запуске или это отдельная фаза?

**Ответ:**

По моей оценке лучше это в следующем этапе после тестирования, он нужен именно следующим этапам как катализатор роста сервиса

### 152. Вопрос

Есть ли уже реальные партнёры, которые ждут доступ?

**Ответ:**

Да

### 153. Вопрос

Какой тип партнёров предполагается: referral partners, resellers, storefront owners, influencers, B2B agents?

**Ответ:**

В проекте поддерживаются referral partners, resellers, storefront owners, influencers/B2B-like agents.

### 154. Вопрос

Нужны ли партнёрские storefronts на старте?

**Ответ:**

Storefronts есть. Нужны ли на старте: не знаю, но лучше позже.

### 155. Вопрос

Нужны ли partner payouts на старте?

**Ответ:**

Payouts есть в backend/partner. На старте лучше не включать без finance readiness. Бизнес-решение не знаю.

### 156. Вопрос

Если выплаты нужны, кто будет их подтверждать?

**Ответ:**

Не знаю. Finance approver не указан.

### 157. Вопрос

Какой payout cycle: weekly, monthly, manual?

**Ответ:**

Payout cycle не зафиксирован.

### 158. Вопрос

Нужны ли settlement periods/reserves сразу?

**Ответ:**

Settlement periods/reserves есть. На старте B2C MVP не нужны. Для partner launch нужны.

### 159. Вопрос

Нужна ли проверка партнёров/KYC/KYB?

**Ответ:**

Нет

### 160. Вопрос

Как бороться с fraud в referral/partner-системе?

**Ответ:**

В docs есть risk/anti-abuse specs для growth codes. Реальная live fraud process не подтверждена.

**Обоснование:**

Это основано на области: partner workspace, partner platform specs, growth code docs, payout/settlement/risk domains. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 161. Вопрос

Нужно ли ограничивать referral bonus по текущим `REFERRAL_MAX_REFERRALS=100`?

**Ответ:**

В bot env `REFERRAL_MAX_REFERRALS=100`. Финальность правила не знаю.

### 162. Вопрос

Referral bonus `3 дня` — это финальное бизнес-правило?

**Ответ:**

Нет

### 163. Вопрос

Нужно ли начислять бонус только после оплаты приглашённого пользователя?

**Ответ:**

Правильно начислять после оплаты/qualifying event; docs growth codes это предполагают. Финальное правило не знаю.

### 164. Вопрос

Нужно ли разрешить пользователю выводить деньги или только получать дни подписки?

**Ответ:**

У нас только партнёры могут выводить деньги из партнёрского портала

### 165. Вопрос

Что делать с self-referral и мультиаккаунтами?

**Ответ:**

В risk/anti-abuse docs проблема учтена; конкретное enforcement для self-referral/multi-account надо проверять.

**Обоснование:**

Это основано на области: partner workspace, partner platform specs, growth code docs, payout/settlement/risk domains. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

## 11. Mobile, Desktop, Android TV, Helix

### 166. Вопрос

Flutter mobile app нужен для первого запуска или позже?

**Ответ:**

Не обязательно для первого запуска. Flutter app большой, но лучше позже beta/store track.

### 167. Вопрос

Планируется ли публиковать iOS/Android app в сторах?

**Ответ:**

Да

### 168. Вопрос

Есть ли Apple Developer Account и Google Play Console?

**Ответ:**

Нет

### 169. Вопрос

Планируется ли использовать RevenueCat на старте?

**Ответ:**

RevenueCat (`purchases_flutter`) есть в mobile dependencies. Использовать на старте: не знаю.

### 170. Вопрос

Если mobile app запускается позже, нужен ли сейчас web-first/mobile-friendly кабинет?

**Ответ:**

Да, если mobile позже, web-first должен быть mobile-friendly; frontend already has mobile layout/performance checks.

**Обоснование:**

Это основано на области: cybervpn_mobile pubspec, desktop package/README, Android TV Gradle files и Helix adapter/node docs. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 171. Вопрос

Desktop client нужен как обязательная часть продукта или как beta?

**Ответ:**

Desktop выглядит как beta/advanced client, особенно с Helix diagnostics.

### 172. Вопрос

Android TV app нужен реальным пользователям сразу или это device expansion?

**Ответ:**

Android TV выглядит как device expansion

### 173. Вопрос

Browser extension сейчас placeholder — нужно ли вообще учитывать её в запуске?

**Ответ:**

Browser extension сейчас placeholder; учитывать в launch не надо.

### 174. Вопрос

Helix является обязательной технологической частью продукта или экспериментальным private transport?

**Ответ:**

Helix не обязательный он описан как дополнительный private transport stack, Remnawave остается authoritative.


### 175. Вопрос

Будет ли Helix доступен только beta-пользователям?

**Ответ:**

Вероятно да, Helix лучше beta/canary.

### 176. Вопрос

Нужно ли позиционировать Helix как premium feature?

**Ответ:**

Можно позиционировать как premium/private transport позже.

### 177. Вопрос

Нужна ли отдельная legal/privacy оценка для Helix?

**Ответ:**

Да, нужна отдельная legal/privacy/security оценка, если Helix влияет на traffic/logging/routing.


### 178. Вопрос

Какие OS версии должны поддерживаться desktop-клиентом?

**Ответ:**

Windows/Linux/MacOS

### 179. Вопрос

Какие Android/iOS версии должны поддерживаться mobile app?

**Ответ:**

Не знаю

### 180. Вопрос

Нужен ли auto-update механизм для desktop client до beta?

**Ответ:**

Да, для desktop beta нужен updater/release mechanism; Tauri updater dependency есть

## 12. Инфраструктура и deployment

### 181. Вопрос

Где будет размещаться production backend: VPS, cloud provider, Kubernetes, managed platform?

**Ответ:**

Не знаю. Repo содержит VPS/Hetzner/Terraform/Ansible/Kubernetes/Talos/GitOps варианты, но production backend placement не выбран явно.


### 182. Вопрос

Где будет размещаться production PostgreSQL?

**Ответ:**

Не знаю. Local Compose PostgreSQL есть; production DB location не зафиксирован.


### 183. Вопрос

Где будет размещаться Redis/Valkey?

**Ответ:**

Не знаю. Local Valkey есть; production Redis/Valkey location не зафиксирован.

### 184. Вопрос

Где будет размещаться Remnawave production?

**Ответ:**

Не знаю. Remnawave local baseline есть; production placement не подтвержден.

### 185. Вопрос

Будут ли frontend/admin/partner размещаться на Vercel, собственном сервере, Kubernetes или другом варианте?

**Ответ:**

Не знаю

### 186. Вопрос

Нужен ли Kubernetes/Talos/GitOps уже для первого запуска или можно начать с simpler controlled topology?

**Ответ:**

Для первого запуска Kubernetes/Talos/GitOps не обязателен; repo target-state содержит их, но можно стартовать simpler controlled topology.

### 187. Вопрос

Какая deployment authority будет основной: manual deploy, Docker Compose, GitHub Actions, GitOps/Flux?

**Ответ:**

Не знаю. Сейчас есть Docker Compose local, Ansible migration, GitHub Actions, GitOps scaffold. Production authority надо выбрать.

### 188. Вопрос

Будет ли staging полностью отдельным окружением?

**Ответ:**

Должен быть. Есть staging docs/stacks

### 189. Вопрос

Какие окружения нужны: local, dev, staging, production?

**Ответ:**

По repo нужны local, staging, production; dev/nonprod тоже упоминается.

### 190. Вопрос

Есть ли уже DNS-зоны и доступ к управлению DNS?

**Ответ:**

Не знаю. Cloudflare DNS stacks есть, но доступы/зоны не подтверждены.

### 191. Вопрос

Кто будет управлять TLS-сертификатами?

**Ответ:**

Не знаю. Caddy/cert-manager/Gateway API paths есть, но owner TLS не указан.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: infra README/docker-compose, platform foundation inventory, Terraform/OpenTofu, GitOps and OpenBao/NATS/PostHog scaffolds, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 192. Вопрос

Нужно ли использовать Cloudflare или другой edge/proxy?

**Ответ:**

Cloudflare DNS явно есть в Terraform. Edge/proxy/WAF решение не знаю.

### 193. Вопрос

Нужно ли защищать backend от прямого публичного доступа?

**Ответ:**

Да, backend лучше закрыть за proxy/internal network и exposed routes только через controlled ingress.

### 194. Вопрос

Нужен ли WAF/rate limiting на edge?

**Ответ:**

Да, WAF/edge rate limiting желательно. В repo есть app rate limits, edge WAF decision

### 195. Вопрос

Где будут храниться production secrets?

**Ответ:**

Target-state: OpenBao. Сейчас много `.env` surfaces.

### 196. Вопрос

OpenBao нужен на старте или позже?

**Ответ:**

Да. Target-state OpenBao есть.

### 197. Вопрос

Какие `.env` файлы сейчас являются launch-critical?

**Ответ:**

Launch-critical: `backend/.env`, `frontend/.env*`, `admin/.env*`, `partner/.env*`, `services/telegram-bot/.env`, `services/task-worker/.env`, `infra/.env`, Helix env только если Helix включен.

**Обоснование:**

Это основано на области: infra README/docker-compose, platform foundation inventory, Terraform/OpenTofu, GitOps and OpenBao/NATS/PostHog scaffolds. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 198. Вопрос

Нужно ли разделить secrets по backend, bot, worker, frontend, admin, partner?

**Ответ:**

Да, secrets нужно разделить по backend, bot, worker, frontend/admin/partner, infra, Remnawave, payments.

**Обоснование:**

Это основано на области: infra README/docker-compose, platform foundation inventory, Terraform/OpenTofu, GitOps and OpenBao/NATS/PostHog scaffolds. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 199. Вопрос

Есть ли стратегия rotation для JWT/TOTP/OAuth/Remnawave/payment secrets?

**Ответ:**

Частично: есть `docs/secret-rotation.md` и secret generation scripts. Полная production rotation strategy не подтверждена.

**Обоснование:**

Это основано на области: infra README/docker-compose, platform foundation inventory, Terraform/OpenTofu, GitOps and OpenBao/NATS/PostHog scaffolds. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 200. Вопрос

Нужно ли иметь отдельный deploy user/SSH access policy?

**Ответ:**

Да, нужен. В repo deploy user/SSH policy как final launch policy не вижу.


## 13. Backend, API и database

### 201. Вопрос

Все ли Alembic migrations применяются на чистую базу?

**Ответ:**

Не знаю. Есть `backend/alembic/versions` и `backend/migrations`, но я не запускал migrations на чистую БД.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 202. Вопрос

Есть ли seed/admin bootstrap для production?

**Ответ:**

Не знаю. Admin/bootstrap flow надо проверить отдельно.


### 203. Вопрос

Как создаётся первый admin user?

**Ответ:**

Не знаю. В docs есть admin user models/invites, но exact first-admin bootstrap не подтвержден.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 204. Вопрос

Есть ли миграции, которые опасно применять без downtime?

**Ответ:**

Не знаю

### 205. Вопрос

Нужен ли blue/green deploy для backend?

**Ответ:**

ДА

### 206. Вопрос

Нужен ли maintenance mode?

**Ответ:**

Maintenance mode полезен.

### 207. Вопрос

Нужно ли versioning API для native clients?

**Ответ:**

Да, если native clients запускаются. Сейчас API under `/api/v1`, этого достаточно как базовое versioning.

**Обоснование:**

Это основано на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 208. Вопрос

Какие backend endpoints должны быть публичными?

**Ответ:**

Public: status, legal/public network/marketing, auth/register/login, payment callbacks/webhooks, Telegram/public Mini App flows. Exact allowlist надо freeze.

**Обоснование:**

Это основано на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 209. Вопрос

Какие backend endpoints должны быть строго internal/admin-only?

**Ответ:**

Admin/system config/customer operations/payments/refunds/payouts/provisioning/monitoring/internal reconciliation должны быть admin/internal-only.

**Обоснование:**

Это основано на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 210. Вопрос

Нужно ли отключить Swagger/OpenAPI публично в production?

**Ответ:**

Да. `SWAGGER_ENABLED=false` default это поддерживает.

**Обоснование:**

Это основано на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 211. Вопрос

Проверены ли CORS origins для всех production domains?

**Ответ:**

CORS explicit config есть.

### 212. Вопрос

Проверены ли cookie domain и secure cookie settings?

**Ответ:**

Cookie settings есть (`cookie_secure`, `cookie_domain`).

### 213. Вопрос

Нужна ли защита от CSRF для cookie-based flows?

**Ответ:**

Да, для cookie-based flows CSRF нужно оценить. В явном виде full CSRF protection я не подтверждаю.


### 214. Вопрос

Есть ли rate limits для auth, payments, trial, referral, support?

**Ответ:**

Есть rate-limit middleware и endpoint-specific mobile/Telegram rate limits. И так же полное покрытие payments/trial/referral/support тоже нужно.

### 215. Вопрос

Какие задачи worker обязательны для первого запуска?

**Ответ:**

Обязательны: email/notifications if used, payment reconciliation, subscription expiry/renewal, provisioning retries, reporting/cleanup minimum. Exact jobs

**Обоснование:**

Это основано на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 216. Вопрос

Какие scheduler jobs обязательны для первого запуска?

**Ответ:**

Обязательны scheduler jobs для expiry/renewal/reconciliation/notification, Exact list

**Обоснование:**

Часть вывода основана на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout, но финальное бизнесовое или операционное решение в репозитории не закреплено. Поэтому ответ разделяет видимое техническое состояние и неизвестную часть.

### 217. Вопрос

Какие jobs можно отключить, чтобы снизить риск?

**Ответ:**

Можно отключить growth reporting, partner bots, advanced analytics, public network DPI publishing, broad notification campaigns, Helix audits if out of MVP.

**Обоснование:**

Это основано на области: backend router/settings, alembic/migrations directories, TaskIQ/Redis/NATS configuration and API layout. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 218. Вопрос

Есть ли dead-letter/retry policy для фоновых задач?

**Ответ:**

Частично: TaskIQ/Redis, retries/tenacity видны. Dead-letter policy тоже надо

### 219. Вопрос

Нужно ли использовать NATS на старте или достаточно Redis/TaskIQ?

**Ответ:**

Для старта достаточно Redis/TaskIQ. NATS target-state очень хотелось бы

### 220. Вопрос

Как backend будет отличать staging payment/webhook events от production?

**Ответ:**

Не знаю. Нужны отдельные webhook endpoints/secrets/provider modes per environment; current env structure поддерживает

## 14. Observability, monitoring и incident response

### 221. Вопрос

Какие Sentry projects уже созданы?

**Ответ:**

Не знаю

### 222. Вопрос

Нужно ли отдельное Sentry project для frontend, admin, partner, backend, bot, worker, desktop, mobile?

**Ответ:**

Да, желательно отдельные Sentry projects

**Обоснование:**

Это основано на области: Sentry configs, Prometheus/Grafana assets, observability runbooks and launch evidence notes. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 223. Вопрос

Включена ли PII scrubbing policy?

**Ответ:**

Да, PII scrubbing policy есть в docs/code (`send_default_pii=false`, before_send hooks, privacy docs). Live verification не знаю.

### 224. Вопрос

Нужно ли загружать sourcemaps для Next.js приложений?

**Ответ:**

Да, Next.js sourcemaps нужны. Sentry config has upload support when token set.

### 225. Вопрос

Какие Prometheus targets должны быть обязательными на старте?

**Ответ:**

Backend, frontend runtime route, bot, worker, Remnawave, PostgreSQL, Valkey, Helix if enabled, node health, payment/provisioning metrics.

### 226. Вопрос

Какие Grafana dashboards считаются launch-critical?

**Ответ:**

Launch-critical: API health/errors/latency, auth, payments, provisioning, VPN node health, Mini App runtime, worker queues, DB/Redis, Sentry release/errors.

### 227. Вопрос

Какие alerts должны быть настроены до запуска?

**Ответ:**

Alerts: API 5xx, auth failure spike, payment failure/reconciliation lag, provisioning failures, worker queue depth, DB/Redis down, Remnawave down, VPN node down, Sentry error spike. И возможно другие!

### 228. Вопрос

Куда должны приходить alerts: Telegram, email, Slack, Discord?

**Ответ:**

Telegram/email/Discord

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: Sentry configs, Prometheus/Grafana assets, observability runbooks and launch evidence notes, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 229. Вопрос

Кто будет on-call в первые дни запуска?

**Ответ:**

Не знаю. On-call owner не указан.

### 230. Вопрос

Какие метрики считаются критическими: payment failure rate, provisioning failure rate, API latency, VPN node health, Sentry errors?

**Ответ:**

Да: payment failure rate, provisioning failure rate, API latency/error rate, VPN node health, Sentry errors, worker queue lag.

### 231. Вопрос

Нужно ли вести launch war room во время релиза?

**Ответ:**

Да, для первого live release launch war room желателен.


### 232. Вопрос

Нужен ли статус-сайт для пользователей?

**Ответ:**

Да, status page полезен. Public `/status` route exists in marketing.

### 233. Вопрос

Страница `/status` должна быть публичной или внутренней?

**Ответ:**

Public status page для пользователей и internal monitoring отдельно.

### 234. Вопрос

Как пользователь узнает, что проблема на стороне VPN-сервиса?

**Ответ:**

Через status page, Telegram bot notifications/support banners.

### 235. Вопрос

Нужно ли логировать user journey от оплаты до provisioning?

**Ответ:**

Да, особенно payment -> provisioning. В repo есть analytics/reporting/outbox surfaces;

### 236. Вопрос

Где будут храниться release evidence packs?

**Ответ:**

В repo есть `docs/evidence/` и runbook evidence packs.

### 237. Вопрос

Нужны ли screenshots/command transcripts для каждого gate?

**Ответ:**

Да, docs прямо требуют screenshots/command transcripts/evidence для gates.

### 238. Вопрос

Как часто нужно проверять backup restore?

**Ответ:**

Не знаю. Runbooks есть; cadence should be at least before launch and periodically after.


### 239. Вопрос

Какие события должны попадать в audit log?

**Ответ:**

Privileged admin actions, auth/security changes, payment/refund/payout/provisioning changes, system config, partner/growth operations.


### 240. Вопрос

Нужна ли отдельная post-launch stabilization checklist?

**Ответ:**

Да. Есть Mini App stabilization debt note; общая post-launch checklist нужна.


## 15. Security, privacy и legal

### 241. Вопрос

Есть ли готовые Terms of Service?

**Ответ:**

Terms UI/messages/pages есть

### 242. Вопрос

Есть ли готовая Privacy Policy?

**Ответ:**

Privacy Policy pages/messages есть, но встречается placeholder `[Your Company Address]`; финальная готовность не подтверждена.

### 243. Вопрос

Есть ли Acceptable Use Policy?

**Ответ:**

Не знаю. Acceptable Use Policy как отдельный финальный документ не подтвержден.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: security settings, generated Terms/Privacy texts, GDPR/delete/export strings and missing final legal owner docs, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 244. Вопрос

Есть ли Refund Policy?

**Ответ:**

Частично. Refund mentions есть, но финальная refund policy не подтверждена.

**Обоснование:**

Это основано на области: security settings, generated Terms/Privacy texts, GDPR/delete/export strings and missing final legal owner docs. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 245. Вопрос

Есть ли Cookie Policy?

**Ответ:**

Нету но нужен!

### 246. Вопрос

Нужно ли GDPR-compliance для пользователей из ЕС?

**Ответ:**

Да

### 247. Вопрос

Какие персональные данные ты реально хочешь хранить?

**Ответ:**

Не знаю как бизнес-решение. В моделях видны email, telegram_id, username, OAuth accounts/tokens, payment metadata, device credentials, sessions, usage-related data.

### 248. Вопрос

Какие данные можно не хранить вообще?

**Ответ:**

Не знаю. Нужно минимизировать: raw browsing activity, VPN content, unnecessary IP logs, raw provider tokens.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: security settings, generated Terms/Privacy texts, GDPR/delete/export strings and missing final legal owner docs, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 249. Вопрос

Хранишь ли ты IP пользователя?

**Ответ:**

В auth/session/payment/security models есть ip_address/user_agent fields in old audit docs;

### 250. Вопрос

Хранишь ли ты VPN usage logs?

**Ответ:**

Проект заявляет no-logs в UI text

### 251. Вопрос

Хранишь ли ты connection logs?

**Ответ:**

Connection logs policy не зафиксирована.

### 252. Вопрос

Хранишь ли ты payment metadata?

**Ответ:**

Да, payment metadata/domain models есть.

### 253. Вопрос

Как долго хранятся логи?

**Ответ:**

Не знаю. Retention settings есть для some growth/reporting/cleanup, но общей log retention policy не вижу.

### 254. Вопрос

Нужно ли пользователю объяснять no-logs policy?

**Ответ:**

Да, если no-logs заявляется.

### 255. Вопрос

Если no-logs policy заявляется, подтверждается ли она архитектурно?

**Ответ:**

Да

### 256. Вопрос

Нужно ли external audit/security review до публичного запуска?

**Ответ:**

Нет

### 257. Вопрос

Кто имеет доступ к production database?

**Ответ:**

Не знаю. Production DB access policy не видна.

### 258. Вопрос

Кто имеет доступ к Remnawave?

**Ответ:**

Не знаю. Remnawave access policy не видна.

### 259. Вопрос

Кто имеет доступ к payment provider dashboards?

**Ответ:**

Не знаю. Payment dashboard access policy не видна.

### 260. Вопрос

Нужна ли политика обработки abuse-запросов?

**Ответ:**

Да, нужна. В repo есть risk/abuse docs, но legal abuse process не финализирован.

### 261. Вопрос

Что делать при жалобе на пользователя?

**Ответ:**

Не знаю. Нужен abuse runbook.


### 262. Вопрос

Что делать при запросе от правоохранительных органов?

**Ответ:**

Не знаю. Нужна law enforcement request policy.

### 263. Вопрос

Нужно ли блокировать определённые типы трафика?

**Ответ:**

Да, должен быть подключен плагин к Remnawave по блокировке torrent траффика на определённых нодах

### 264. Вопрос

Нужно ли запрещать spam, malware, credential stuffing, scraping?

**Ответ:**

Да, AUP должен запрещать spam, malware, credential stuffing, scraping/abuse.

### 265. Вопрос

Нужна ли age restriction policy?

**Ответ:**

Нет

## 16. Support и операции

### 266. Вопрос

Какой support-канал будет основным: Telegram, email, web tickets, bot, Discord?

**Ответ:**

Telegram, email, web tickets, bot

### 267. Вопрос

Кто будет отвечать пользователям в первые недели?

**Ответ:**

ИИ агент как первая линия

### 268. Вопрос

Какой SLA ответа ты хочешь держать?

**Ответ:**

Не знаю. Support SLA mentioned in UI/admin

### 269. Вопрос

Какие типовые проблемы пользователей ожидаются?

**Ответ:**

Ожидаемые проблемы: payment failed, paid but no access, config не работает, expired subscription, Telegram auth, device limit, wrong location, Remnawave/node outage.


### 270. Вопрос

Нужна ли база знаний до запуска?

**Ответ:**

Да, база знаний нужна. Public docs/guides/help routes есть.

### 271. Вопрос

Нужен ли FAQ на сайте?

**Ответ:**

Да. FAQ/help pages есть conceptually.

**Обоснование:**

Это основано на области: customer support routes, admin/customer operation surfaces, support-related UI strings and runbooks. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 272. Вопрос

Нужны ли troubleshooting guides для Windows/macOS/iOS/Android?

**Ответ:**

Да. Platform troubleshooting guides нужны.

### 273. Вопрос

Как support будет проверять статус подписки пользователя?

**Ответ:**

Через admin/customer operations/subscription/wallet/payment history.

### 274. Вопрос

Как support будет проверять успешность provisioning?

**Ответ:**

Через access delivery/provisioning/device credentials/Remnawave status. Concrete UI не подтверждаю.

**Обоснование:**

Это основано на области: customer support routes, admin/customer operation surfaces, support-related UI strings and runbooks. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 275. Вопрос

Может ли support пересоздать VPN config?

**Ответ:**

Вероятно да, по restore VPN/provisioning surfaces.

### 276. Вопрос

Может ли support видеть платежные данные?

**Ответ:**

Должен видеть ограниченно: статусы/attempts, но не raw sensitive payment data.

### 277. Вопрос

Какие данные support не должен видеть?

**Ответ:**

Support не должен видеть tokens, config links beyond needed, raw payment secrets, OAuth tokens, TOTP secrets, unnecessary IP/activity logs.


### 278. Вопрос

Нужна ли система тикетов на первом запуске?

**Ответ:**

Да

### 279. Вопрос

Customer support routes в backend уже используются или пока только заложены?

**Ответ:**

Customer support routes есть, но live usage не подтвержден.

### 280. Вопрос

Нужен ли шаблон ответа для failed payment?

**Ответ:**

Да, нужен шаблон failed payment.


### 281. Вопрос

Нужен ли шаблон ответа для “VPN не подключается”?

**Ответ:**

Да, нужен шаблон "VPN не подключается".

### 282. Вопрос

Нужен ли шаблон ответа для refund request?

**Ответ:**

Да, нужен refund request template.

### 283. Вопрос

Нужен ли шаблон ответа для expired subscription?

**Ответ:**

Да, нужен expired subscription template.

### 284. Вопрос

Нужен ли escalation process от support к technical ops?

**Ответ:**

Да, нужен escalation process support -> technical ops.

### 285. Вопрос

Нужна ли отдельная emergency-инструкция “Remnawave недоступен”?

**Ответ:**

Да, нужна emergency-инструкция "Remnawave недоступен"; похожие runbooks есть, но customer support version не вижу.

## 17. Marketing, SEO и acquisition

### 286. Вопрос

Будет ли публичный marketing site на первом запуске?

**Ответ:**

Да, marketing site уже есть в `frontend` routes. Будет ли публичный на первом запуске: не знаю.

### 287. Вопрос

Какие страницы должны быть готовы: pricing, features, devices, download, privacy, terms, trust, status, help?

**Ответ:**

Routes есть для pricing/features/devices/download/privacy/terms/trust/status/help/docs/guides. Нужно проверить готовность контента.

### 288. Вопрос

Нужен ли блог или docs-раздел до запуска?

**Ответ:**

Docs/guides sections есть. Блог как обязательный до запуска не знаю.

### 289. Вопрос

Какая первая acquisition-стратегия: Telegram channels, SEO, referrals, paid ads, partners, communities?

**Ответ:**

Не знаю. По проекту вероятные каналы: Telegram, SEO, referrals, partners.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: frontend marketing route tree, SEO content, PostHog/product-intelligence scaffolds and attribution domains, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

### 290. Вопрос

Есть ли уже список каналов, где будет анонс?

**Ответ:**

Не знаю. Список каналов анонса не виден.

### 291. Вопрос

Нужна ли landing page для закрытой beta?

**Ответ:**

Нет

### 292. Вопрос

Нужна ли waitlist?

**Ответ:**

Нет

### 293. Вопрос

Нужны ли invite codes для контроля притока пользователей?

**Ответ:**

Да, invite codes логичны и есть в backend; они помогут контролировать приток.

### 294. Вопрос

Нужно ли использовать PostHog на первом запуске?

**Ответ:**

PostHog target-state есть. Для первого MVP можно включить минимально и privacy-safe.

### 295. Вопрос

Какие product analytics события нужно собирать?

**Ответ:**

Visit/register/trial/payment/provisioned/active VPN/session expiry/support/refund/failure events

### 296. Вопрос

Как измерять конверсию: visit → register → trial → payment → active VPN user?

**Ответ:**

Через funnel: visit -> register -> trial -> payment -> provisioned -> active VPN user.

**Обоснование:**

Это основано на области: frontend marketing route tree, SEO content, PostHog/product-intelligence scaffolds and attribution domains. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 297. Вопрос

Нужна ли UTM/attribution tracking?

**Ответ:**

Да, attribution/UTM tracking есть в partner/growth domains и нужен для acquisition.

### 298. Вопрос

Какие privacy limitations будут у analytics?

**Ответ:**

Analytics не должна включать PII, raw config links, raw IP/activity logs.

### 299. Вопрос

Нужно ли A/B testing на старте или это лишнее?

**Ответ:**

На старте A/B testing лишнее, если нет трафика/стабильности. PostHog flags есть, но лучше default-off.

### 300. Вопрос

Какая главная метрика успеха первой недели?

**Ответ:**

Не знаю.

## 18. Release governance и принятие решений

### 301. Вопрос

Кто является final decision maker по запуску?

**Ответ:**

Не знаю. Final decision maker не указан.

### 302. Вопрос

Кто отвечает за backend readiness?

**Ответ:**

Не знаю.

### 303. Вопрос

Кто отвечает за frontend readiness?

**Ответ:**

Не знаю.

### 304. Вопрос

Кто отвечает за infra readiness?

**Ответ:**

Не знаю.

### 305. Вопрос

Кто отвечает за payments readiness?

**Ответ:**

Не знаю.

### 306. Вопрос

Кто отвечает за legal readiness?

**Ответ:**

Не знаю.

### 307. Вопрос

Кто отвечает за support readiness?

**Ответ:**

Не знаю.

### 308. Вопрос

Кто имеет право остановить запуск?

**Ответ:**

Не знаю.

### 309. Вопрос

Какие критерии являются hard blocker?

**Ответ:**

Hard blockers: broken auth, broken payment, broken provisioning, no rollback, no backups, no production secrets policy, no observability for critical flows, legal pages unfinished if public launch.

### 310. Вопрос

Какие критерии можно принять как known issue?

**Ответ:**

Known issues can be non-critical UI polish, partner/native/Helix disabled, advanced analytics gaps.

### 311. Вопрос

Нужен ли launch freeze для репозитория?

**Ответ:**

Да, launch freeze нужен. Текущий dirty worktree очень широкий.

### 312. Вопрос

Какой branch/tag будет считаться launch candidate?

**Ответ:**

Не знаю.

### 313. Вопрос

Нужно ли делать release notes?

**Ответ:**

Да, release notes нужны.

### 314. Вопрос

Нужно ли делать rollback notes?

**Ответ:**

Да, rollback notes нужны.

### 315. Вопрос

Какой rollback считается успешным?

**Ответ:**

Успешный rollback: восстановлена предыдущая рабочая версия без потери payments/subscriptions/provisioning state. Exact criteria не знаю.

### 316. Вопрос

Что именно откатываем при проблеме: frontend, backend, payments, Remnawave config, bot?

**Ответ:**

Depends on incident. Нужно уметь откатывать frontend/backend/bot/worker/config separately; Remnawave config changes отдельно.

### 317. Вопрос

Нужно ли feature flags для рискованных функций?

**Ответ:**

Да, feature flags нужны для risky функций. В repo есть PostHog/launch controls/system_config.

### 318. Вопрос

Какие функции должны быть выключаемыми без redeploy?

**Ответ:**

Payments, public registration, trial, referral, promo/gift/growth, partner payouts, Mini App rollout, notifications, Helix should be kill-switchable.

### 319. Вопрос

Есть ли emergency kill switch для payments/trial/referral?

**Ответ:**

Частично есть launch controls/system_config/growth controls. Emergency kill switch для всего списка надо подтвердить.

### 320. Вопрос

Есть ли emergency kill switch для public registration?

**Ответ:**

Registration kill switch есть (`REGISTRATION_ENABLED=false`). Public registration можно выключать.

## 19. Технический долг и приоритеты

### 321. Вопрос

Какие части проекта ты считаешь “готовыми”, но не проверенными в живой среде?

**Ответ:**

Mini App code-side launch package, partner/growth packages, Sentry integration, platform foundation scaffolds выглядят готовыми/частично готовыми, но не доказаны live.

### 322. Вопрос

Какие части проекта ты сам считаешь самыми рискованными?

**Ответ:**

Самые рискованные: payments, provisioning, auth/session/cookies, secrets, dirty worktree, partner/growth abuse, legal/no-logs claims, live observability.

### 323. Вопрос

Какие части проекта написаны давно и могут быть устаревшими?

**Ответ:**

Старые broad docs `docs/PROJECT_OVERVIEW.md`, `docs/CYBERVPN_FULL_DESCRIPTION.md` частично устарели по platform inventory.

### 324. Вопрос

Какие docs ты считаешь актуальными?

**Ответ:**

Актуальнее всего выглядят docs от 2026-04-21..2026-04-24 по platform foundation, Mini App debt, Sentry roadmap, user cabinet integration.

**Обоснование:**

Это основано на области: platform inventory, technical-debt docs, dirty worktree and existing audit/conformance notes. Ответ ограничен текущими файлами проекта и не подтверждает внешние аккаунты, production-доступы или решения, которых нет в репозитории.

### 325. Вопрос

Какие docs ты считаешь устаревшими?

**Ответ:**

Platform inventory сам отмечает старые overview/prompts/legacy deployment docs как migrate/retire.

### 326. Вопрос

Есть ли dirty worktree сейчас?

**Ответ:**

Да. `git status` показывает очень большой dirty worktree с modified/untracked files across repo.

### 327. Вопрос

Нужно ли отделить launch-critical код от experimental кода?

**Ответ:**

Да, обязательно.

### 328. Вопрос

Какие компоненты точно не должны попасть в первый deploy?

**Ответ:**

В первый deploy не должны попасть: Helix default path, browser extension, native clients, experimental platform migration scripts as runtime.

### 329. Вопрос

Какие компоненты можно держать в репозитории, но не включать в runtime?

**Ответ:**

Можно держать, но не включать runtime: mobile/desktop/Android TV, Helix lab, growth advanced

### 330. Вопрос

Нужно ли провести dependency audit перед запуском?

**Ответ:**

Да. Я ранее запускал `npm audit --omit=dev --audit-level=high`: high не нашел, но есть moderate PostCSS advisory through Next. Нужно полный audit по workspaces.

### 331. Вопрос

Нужно ли провести secrets scan?

**Ответ:**

Да. Нужно secrets scan всего repo.

### 332. Вопрос

Нужно ли провести frontend bundle scan на случайную утечку env/secrets?

**Ответ:**

Да. Особенно Next public env and route handlers.

### 333. Вопрос

Нужно ли проверить mobile assets на secrets?

**Ответ:**

Да. Mobile `pubspec.yaml` прямо отмечает, что `.env` не должен быть asset. Нужно проверить фактически.

### 334. Вопрос

Нужно ли проверить Sentry на отсутствие PII?

**Ответ:**

Да. Sentry PII scrubbing policy есть, но live verification нужен.

### 335. Вопрос

Какие тесты сейчас проходят стабильно?

**Ответ:**

Не знаю.

### 336. Вопрос

Какие тесты flaky?

**Ответ:**

Не знаю.

### 337. Вопрос

Какие conformance gates ты уже запускал?

**Ответ:**

Я видел conformance scripts, но в этой сессии их не запускал.

### 338. Вопрос

Какие conformance gates никогда не запускались на реальном staging?

**Ответ:**

Mini App debt doc прямо говорит, что live staging/prod evidence еще open.

### 339. Вопрос

Нужно ли ввести минимальный coverage threshold перед запуском?

**Ответ:**

Backend coverage threshold есть 60%, bot/worker 80%. Перед запуском нужен минимальный gate по critical paths.

### 340. Вопрос

Нужен ли отдельный bug bash перед beta?

**Ответ:**

Да, bug bash перед beta нужен.


## 20. Финансовая и бизнес-операционная модель

### 341. Вопрос

Какую выручку ты хочешь получить за первый месяц?

**Ответ:**

Не знаю. Revenue goal не указан.

### 342. Вопрос

Сколько платящих пользователей нужно для окупаемости инфраструктуры?

**Ответ:**

120

### 343. Вопрос

Какова себестоимость одного пользователя?

**Ответ:**

Не знаю.

### 344. Вопрос

Какова себестоимость одного GB трафика?

**Ответ:**

Не знаю.

### 345. Вопрос

Какие VPN-ноды самые дорогие?

**Ответ:**

Не знаю.

### 346. Вопрос

Какие тарифы будут убыточными при активном использовании?

**Ответ:**

Не знаю.

### 347. Вопрос

Нужно ли ограничивать heavy users?

**Ответ:**

Нет

### 348. Вопрос

Нужно ли вводить abuse detection по трафику?

**Ответ:**

Не знаю

### 349. Вопрос

Какой churn ты ожидаешь?

**Ответ:**

Не знаю.

### 350. Вопрос

Какие причины отмены подписки нужно собирать?

**Ответ:**

Cancellation reasons собирать полезно; в repo final taxonomy не вижу.


### 351. Вопрос

Нужен ли manual review для подозрительных оплат?

**Ответ:**

Да, подозрительные оплаты/refunds/referrals лучше manual review. Risk domains есть.

### 352. Вопрос

Как считать LTV/CAC на старте?

**Ответ:**

Не знаю. Partner/reporting/PostHog могут помочь, но financial model не виден.

### 353. Вопрос

Будут ли расходы на рекламу до проверки продукта?

**Ответ:**

Нет

### 354. Вопрос

Какие fixed costs у проекта: серверы, домены, Sentry, PostHog, payment fees, app stores?

**Ответ:**

Видимые fixed cost categories: servers/VPS, domains/DNS/Cloudflare, Sentry, PostHog, payment fees, app store accounts, monitoring/storage, VPN node traffic. Exact costs не знаю.

### 355. Вопрос

Какой runway у проекта?

**Ответ:**

Не знаю.

**Обоснование:**

В репозитории я не нашел подтвержденного решения, live credential, владельца процесса или production evidence по этому пункту. Видны только смежные заготовки/контуры в области: наличию billing/wallet/partner finance domains и отсутствию cost/revenue model в репозитории, поэтому фиксирую неизвестное состояние, а не додумываю за проект.

## 21. Данные, backup и disaster recovery

### 356. Вопрос

Где будут храниться backups PostgreSQL?

**Ответ:**

Local Compose stores backups under `infra/backups/postgres/`; control-plane runbooks mention `/var/backups/cybervpn/`. Production final storage не знаю.

**Обоснование:**

Часть вывода основана на области: infra backup service, backup/restore/DR runbooks and platform recovery scaffolds, но финальное бизнесовое или операционное решение в репозитории не закреплено. Поэтому ответ разделяет видимое техническое состояние и неизвестную часть.

### 357. Вопрос

Как часто нужны backups?

**Ответ:**

Local Compose daily backups. Production cadence не знаю.

### 358. Вопрос

Сколько дней хранить backups?

**Ответ:**

Local Compose retention 7 days. Production retention не знаю.

### 359. Вопрос

Нужно ли шифровать backups?

**Ответ:**

Да, production backups should be encrypted.

### 360. Вопрос

Кто имеет доступ к backups?

**Ответ:**

Не знаю.

### 361. Вопрос

Проверялся ли restore на чистое окружение?

**Ответ:**

Runbooks exist for restore drills;

### 362. Вопрос

Какой RPO допустим?

**Ответ:**

Не знаю.

### 363. Вопрос

Какой RTO допустим?

**Ответ:**

Не знаю. RTO not set.

### 364. Вопрос

Что критичнее восстановить первым: backend DB, Remnawave, payments state, user subscriptions?

**Ответ:**

Первым критично восстановить backend DB/payment/subscription state, затем Remnawave access state, then secrets/config/observability. Exact priority не зафиксирован.

### 365. Вопрос

Нужно ли бэкапить Remnawave отдельно?

**Ответ:**

Да, Remnawave нужно бэкапить отдельно или иметь rebuild/export strategy.

### 366. Вопрос

Нужно ли бэкапить secrets?

**Ответ:**

Да, secrets нужно recover/rotate, but not simply backup plaintext. OpenBao target helps.

### 367. Вопрос

Нужно ли бэкапить Grafana dashboards?

**Ответ:**

Да, dashboards should be source-controlled; many Grafana dashboards are in `infra/grafana/dashboards`.

### 368. Вопрос

Нужно ли бэкапить Sentry/PostHog настройки?

**Ответ:**

Да, Sentry/PostHog settings should be documented/exported where possible. Final policy не знаю.

### 369. Вопрос

Как действовать при потере production database?

**Ответ:**

Есть DR runbooks; exact production procedure depends on topology. Не знаю final.

### 370. Вопрос

Как действовать при компрометации JWT secret?

**Ответ:**

Нужно rotate JWT secret, revoke sessions/refresh tokens, redeploy, investigate. Exact runbook не вижу.

## 22. Финальные вопросы перед будущим планом запуска

### 371. Вопрос

Какой launch-формат ты хочешь: private alpha, closed beta, invite-only public beta, paid MVP, full public launch?

**Ответ:**

full public launch

### 372. Вопрос

Какой крайний срок запуска?

**Ответ:**

6 месяцев

### 373. Вопрос

Есть ли дата, к которой нужно обязательно показать продукт?

**Ответ:**

Через 6 месяцев

### 374. Вопрос

Есть ли бюджет на инфраструктуру первого месяца?

**Ответ:**

Не знаю.

### 375. Вопрос

Есть ли бюджет на юридические документы?

**Ответ:**

Не знаю.

### 376. Вопрос

Есть ли бюджет на paid acquisition?

**Ответ:**

Не знаю.

### 377. Вопрос

Есть ли команда или ты запускаешь один?

**Ответ:**

Не знаю.

### 378. Вопрос

Какие задачи ты хочешь делегировать мне: аудит, launch checklist, staging plan, backend review, frontend review, legal checklist, security checklist, CI/CD gates?

**Ответ:**

Тебе ? Ты мне составляешь по этапный ввод всего проекта целиком, к каждому этапу перед запуском я прилагаю документы которые необходимо составить, далее ты одобряешь, мы реализовываем - ты одобряешь документы и этап мы вводим

### 379. Вопрос

В каком формате тебе удобнее будущий план: таблица, Kanban, roadmap, чеклист, по неделям, по фазам, по владельцам?

**Ответ:**

По этапам реализации и внедрения, этап 1 (например паблик бета), этап 2 (паблик релиз), этап 3 (партнёрский раздел) и так далее

### 380. Вопрос

Что для тебя будет означать “можно запускать”?

**Ответ:**

По repo "можно запускать" должно означать: auth/payment/provisioning проходят staging и invite beta, secrets/backup/observability/legal/support готовы, есть rollback, и тд

---