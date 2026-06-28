# CyberVPN Telegram Bot — Сообщения (ru)

# ── Приветствие и онбординг ──────────────────────────────────────────────
welcome-message = 👋 <b>Добро пожаловать в CyberVPN, { $name }!</b>

    🔐 Быстрый, приватный доступ к интернету.

    <b>Быстрый старт:</b>
    1) Выберите тариф или активируйте пробный период
    2) Получите конфиг (ссылка/QR)
    3) Подключитесь в приложении

    Выберите действие ниже.

welcome = 👋 <b>Добро пожаловать в CyberVPN, { $name }!</b>

    🔐 Быстрый, приватный доступ к интернету.

    <b>Быстрый старт:</b>
    1) Выберите тариф или активируйте пробный период
    2) Получите конфиг (ссылка/QR)
    3) Подключитесь в приложении

    Выберите действие ниже.

welcome-back = 🔄 <b>С возвращением, { $name }!</b>

    Что хотите сделать дальше?

welcome-referral-bonus = 🎁 За регистрацию по приглашению вы получите бонусные дни после первой покупки.

promo-activated = ✅ Промокод <b>{ $code }</b> применён.

telegram-auth-link-success = ✅ <b>Telegram подтверждён</b>

    Вернитесь в браузер, чтобы завершить вход.

telegram-auth-link-invalid = ⚠️ <b>Эта ссылка входа через Telegram недействительна или истекла.</b>

    Запустите новый вход через Telegram на сайте.

telegram-auth-link-legacy-unsupported = ⚠️ <b>Эта ссылка входа через Telegram больше не поддерживается.</b>

    Запустите новый вход через Telegram на сайте.

# ── Меню ─────────────────────────────────────────────────────────────────
menu-main-title = 🏠 <b>Главное меню</b>
growth-menu-title = 🎁 <b>Награды</b>

    Быстрые действия доступны прямо в боте. Для подарков, полного списка уведомлений и сложных сценариев откройте Mini App.

growth-disabled = 🎁 <b>Награды временно недоступны</b>

    Сейчас сервис не отдаёт активные возможности наград для этого канала.

finance-menu-title = 💰 <b>Финансы</b>

    Кошелёк, история платежей и платёжные детали доступны в Mini App. В боте платежи отсюда не запускаются.

miniapp-unavailable = Mini App URL не настроен для этого бота.

# ── Профиль ──────────────────────────────────────────────────────────────
profile-title = 👤 <b>Ваш профиль</b>

profile-info =
    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Username: { $username }
    🌐 Язык: { $language }
    📅 Регистрация: { $registered }
    </blockquote>

profile-details =
    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Имя: { $first_name }
    🧾 Username: { $username }
    🌐 Язык: { $language }
    📅 Регистрация: { $registered }
    </blockquote>

# ── Статус подписки ──────────────────────────────────────────────────────
subscription-active = ✅ <b>Подписка активна</b>

    📋 План: <b>{ $plan }</b>
    ⏳ Истекает: { $expires }

    Нажмите «Получить конфиг», чтобы подключиться, или продлите подписку.

subscription-none = 📭 <b>Подписки нет</b>

    Выберите тариф или активируйте пробный период, чтобы начать пользоваться VPN.

subscription-status-active = ✅ <b>Подписка активна</b>

    📋 План: <b>{ $plan_name }</b>
    ⏳ Истекает: { $expires_at }
    📊 Трафик: { $traffic_used } / { $traffic_limit }
    🔗 <a href="{ $subscription_link }">Ссылка подключения</a>

subscription-status-expired = ❌ <b>Подписка истекла</b>

    Ваша подписка закончилась { $expired_at }.
    Продлите подписку, чтобы продолжить пользоваться VPN.

subscription-status-limited = ⚠️ <b>Трафик исчерпан</b>

    Вы использовали весь доступный трафик.
    Обновите план или дождитесь обновления лимита.

subscription-status-disabled = 🚫 <b>Подписка отключена</b>

    Обратитесь в поддержку для получения информации.

subscription-status-none = 📭 <b>У вас нет подписки</b>

    Выберите план, чтобы начать пользоваться VPN.

# ── Trial ────────────────────────────────────────────────────────────────
trial-offer = 🎁 <b>Бесплатный пробный период!</b>

    Попробуйте CyberVPN бесплатно на { $days ->
        [one] { $days } день
        [few] { $days } дня
       *[other] { $days } дней
    }!

    📱 1 устройство
    🌐 Только shared-серверы
    📊 Безлимитный трафик по fair use

trial-activated = ✅ <b>Пробный период активирован!</b>

    Длительность: { $duration ->
        [one] { $duration } день
        [few] { $duration } дня
       *[other] { $duration } дней
    }
    Истекает: { $expires }

trial-eligible = ✅ Вы можете активировать пробный период.

trial-not-eligible-used = ℹ️ Пробный период уже использован.
trial-not-eligible-active = ℹ️ У вас уже есть активная подписка.
trial-not-eligible-unavailable = ⚠️ Пробный период сейчас недоступен.
trial-not-eligible-unknown = ⚠️ Сейчас нельзя активировать пробный период. Попробуйте позже.

trial-already-used = ℹ️ Вы уже использовали пробный период.

trial-unavailable = ⚠️ Пробный период временно недоступен.

subscription-hidden-plan-unavailable = ⚠️ Это предложение сейчас недоступно.

# ── Привязка Telegram ───────────────────────────────────────────────────
telegram-account-link-success = ✅ <b>Telegram подтверждён.</b>

    Вернитесь в браузер, чтобы завершить привязку к аккаунту.

telegram-account-link-expired = ⚠️ Эта ссылка Telegram недействительна или истекла.

    Создайте новую ссылку в настройках аккаунта.

telegram-account-link-already-used = ⚠️ Эта ссылка Telegram уже использована.

    Создайте новую ссылку в настройках аккаунта.

telegram-account-link-conflict = ⚠️ Этот Telegram уже привязан к другому аккаунту CyberVPN.

telegram-account-link-rate-limited = ⏳ Слишком много попыток привязки Telegram. Подождите и попробуйте снова.

telegram-account-link-service-unavailable = ⚠️ Привязка Telegram временно недоступна. Попробуйте позже.

# ── Подписка и планы ─────────────────────────────────────────────────────
subscription-select-plan = 💳 <b>Выберите тариф</b>

    Можно сменить позже.

subscription-select-duration = ⏰ <b>Выберите длительность</b>

subscription-direct-offer = 🔓 <b>Специальное предложение: { $plan }</b>

    Этот тариф доступен только по прямому предложению.
    Выберите период, чтобы продолжить.

subscription-direct-offer-duration = Запрошенный период: { $duration_days ->
        [one] { $duration_days } день
        [few] { $duration_days } дня
       *[other] { $duration_days } дней
    }

subscription-select-payment = 💰 <b>Выберите способ оплаты</b>

    План: <b>{ $plan }</b>
    Длительность: { $duration ->
        [one] { $duration } день
        [few] { $duration } дня
       *[other] { $duration } дней
    }
    Сумма: <b>{ $price }</b>

    После оплаты отправлю конфигурацию.

subscription-cancelled = ✅ Покупка отменена. Возвращаю в меню.

plans-title = 💳 <b>Выберите план</b>

    Доступные тарифные планы:

plan-item = { $icon } <b>{ $name }</b>
    { $description }
    Цена от: <b>{ $price_from }</b>

duration-title = ⏰ <b>Выберите длительность</b>

    План: <b>{ $plan_name }</b>

duration-item = { $duration_days ->
        [one] { $duration_days } день
        [few] { $duration_days } дня
       *[other] { $duration_days } дней
    } — <b>{ $price }</b>

payment-title = 💰 <b>Выберите способ оплаты</b>

    План: <b>{ $plan_name }</b>
    Длительность: { $duration }
    Сумма: <b>{ $amount }</b>

payment-processing = ⏳ Обработка платежа...

payment-success = ✅ <b>Оплата успешна!</b>

    Подписка активирована. Теперь получите конфиг для подключения.

payment-failed = ❌ <b>Ошибка оплаты</b>

    Платёж не прошёл. Попробуйте снова или выберите другой способ.

payment-cancelled = 🔄 Платёж отменён.

subscription-payment = Подписка CyberVPN
subscription-payment-title = Подписка CyberVPN
subscription-payment-description = Доступ к VPN и настройкам подключения

payment-open-link = Открыть оплату
payment-check-status = Проверить оплату
payment-external-instructions = 💳 <b>Оплата</b>

    1) Нажмите «Открыть оплату»
    2) Завершите платёж
    3) Вернитесь и нажмите «Проверить оплату»

    Если окно оплаты закрыто, откройте его снова.

payment-pending = ⏳ Платёж в обработке. Проверьте статус через минуту.
payment-status-unknown = ℹ️ Статус пока неизвестен. Попробуйте ещё раз чуть позже.

# ── Реферальная система ──────────────────────────────────────────────────
referral-title = 👥 <b>Реферальная программа</b>

    Приглашайте друзей и получайте бонусы!

referral-info =
    <blockquote>
    👥 Приглашено: { $count }
    🎁 Заработано дней: { $bonus_days }
    🔗 Ваша ссылка:
    <code>{ $link }</code>
    </blockquote>

referral-info-with-code =
    <blockquote>
    👥 Приглашено: { $count }
    🎁 Заработано дней: { $bonus_days }
    🎟 Ваш код: <code>{ $code }</code>
    🔗 Ваша ссылка:
    <code>{ $link }</code>
    </blockquote>

referral-share = 📨 Поделитесь ссылкой с друзьями и получите бонусные дни:

    { $link }

referral-share-button = Поделиться ссылкой

referral-new-joined = 🎉 По вашей ссылке зарегистрировался новый пользователь!

referral-reward = 🎁 Вы получили бонус: { $days ->
        [one] { $days } день
        [few] { $days } дня
       *[other] { $days } дней
    } к подписке!

referral-withdraw-insufficient = ⚠️ Для вывода нужно минимум { $min } бонусов.

referral-withdraw-success = ✅ Запрос на вывод создан.

    Сумма: { $amount }
    Статус: { $status }

my-invites-info = 🎟 <b>Мои инвайты</b>

    Всего: <b>{ $count }</b>
    Активных: <b>{ $active_count }</b>

    { $items }

my-invites-empty = Инвайт-коды ещё не выданы вашему аккаунту.

my-invites-item = <blockquote>
    Код: <code>{ $code }</code>
    Статус: { $status }
    Бонус: { $days ->
        [one] { $days } день
        [few] { $days } дня
       *[other] { $days } дней
    }
    Истекает: { $expires }
    Выдан: { $created }
    </blockquote>

my-invites-status-active = активен
my-invites-status-used = использован
my-invites-status-expired = истёк

# ── Промокоды ────────────────────────────────────────────────────────────
promo-enter = 🎟 Введите промокод:

promo-success = ✅ Промокод <b>{ $code }</b> успешно активирован!
    { $description }

promo-invalid = ❌ Промокод недействителен или просрочен.

promo-already-used = ℹ️ Вы уже использовали этот промокод.

promocode-enter-prompt = 🎟 Введите промокод (например, CYBER10):
promocode-activated = ✅ Промокод <b>{ $code }</b> активирован! Скидка: <b>{ $discount }</b>
promocode-not-found = ❌ Промокод не найден.
promocode-expired = ❌ Срок действия промокода истёк.
promocode-already-used = ℹ️ Вы уже использовали этот промокод.
promocode-usage-limit = ⚠️ Лимит использования промокода исчерпан.
promocode-cancelled = ✅ Ввод промокода отменён.
code-enter-prompt = 🎟 Введите код. Сервис определит тип кода и доступное действие.
code-activated = ✅ Код <b>{ $code }</b> активирован! Результат: <b>{ $discount }</b>
code-not-found = ❌ Код не найден.
bot-onboarding-code-apply-unavailable = ❌ Сейчас этот код нельзя применить из Telegram. Откройте CyberVPN и попробуйте ещё раз или обратитесь в поддержку.
code-expired = ❌ Срок действия кода истёк.
code-already-used = ℹ️ Этот код уже использован.
code-usage-limit = ⚠️ Лимит использования кода исчерпан.
code-cancelled = ✅ Ввод кода отменён.

# ── Поддержка ────────────────────────────────────────────────────────────
support-message = 🆘 <b>Поддержка</b>

    По всем вопросам: { $contact }
    Чтобы создать обращение, отправьте: <code>/support ваш вопрос</code>

support-first-line-payment = 💳 <b>Поддержка по оплате</b>

    Я зафиксировал вопрос как платёжный. В следующем сообщении поддержке укажите способ оплаты и примерное время платежа.

support-first-line-provisioning = 🔐 <b>Поддержка по доступу</b>

    Я зафиксировал вопрос как проблему выдачи доступа/конфига. Не отправляйте полный VPN config link здесь; поддержка найдёт обращение по reference.

support-first-line-connectivity = 🌐 <b>Поддержка подключения</b>

    Попробуйте сменить сервер/локацию и перезапустить VPN-приложение. Если проблема останется, поддержке понадобятся ОС, приложение и текст ошибки.

support-first-line-account = 👤 <b>Поддержка аккаунта</b>

    Я зафиксировал вопрос как проблему аккаунта/логина. Поддержка может попросить подтвердить Telegram-аккаунт или email.

support-first-line-legal_abuse = ⚠️ <b>Нужна эскалация</b>

    Такой запрос должен пройти owner/support review.

support-first-line-general = 🆘 <b>Поддержка</b>

    Здесь я могу ответить только на базовые вопросы launch-beta. По вопросам аккаунта обращайтесь в поддержку.

support-first-line-without-escalation = { $first_line }

    Reference: <code>{ $reference }</code>
    Контакт: { $contact }

support-escalation-created = ✅ Передано в поддержку.

    Reference: <code>{ $reference }</code>
    Контакт: { $contact }

support-escalation-fallback = ⚠️ Не удалось автоматически создать запись поддержки.

    Отправьте этот reference в { $contact }: <code>{ $reference }</code>

# ── Устройства / Конфиг ──────────────────────────────────────────────────
config-title = 📱 <b>Подключение</b>

    Выберите формат для получения конфигурации:

config-link = 🔗 <b>Ссылка подключения:</b>

    <code>{ $link }</code>

    Скопируйте и вставьте в ваше VPN-приложение.

config-qr = 📷 QR-код готов. Отсканируйте в VPN-приложении.

config-instruction = 📖 <b>Инструкция по подключению:</b>

    1️⃣ Скачайте приложение (V2rayNG / Hiddify / Streisand)
    2️⃣ Скопируйте ссылку выше
    3️⃣ Импортируйте конфигурацию
    4️⃣ Подключитесь!

config-delivery-prompt = ✅ <b>Готово!</b> Как получить конфиг?

config-link-message = 🔗 <b>Ссылка подключения</b>

    <code>{ $url }</code>

    Скопируйте ссылку и импортируйте в VPN-приложение.

config-qr-caption = 📷 Отсканируйте QR-код в вашем VPN-приложении.

config-instructions = 📖 <b>Инструкция по подключению</b>

    1) Установите приложение (V2rayNG / Hiddify / Streisand)
    2) Скопируйте ссылку подключения
    3) Импортируйте конфигурацию
    4) Подключитесь

# ── Growth Connection UX ─────────────────────────────────────────────────
bot-onboarding-code-applied = ✅ Код <b>{ $code }</b> принят.
bot-onboarding-code-child-invites = 🎟 Выдано инвайт-кодов: <b>{ $count }</b>, доступно: <b>{ $available }</b>.

bot-onboarding-connection-ready = 🔐 <b>VPN-доступ готов</b>

    Профиль: <b>{ $profile }</b>
    Выберите, как добавить его в VPN-приложение. Ссылка и QR доступны только в этом личном чате.

bot-onboarding-connection-profile-default = CyberVPN
bot-onboarding-connection-no-active-entitlement = Для этого Telegram-аккаунта не найден активный VPN-доступ. Сначала примените код или выберите тариф.
bot-onboarding-connection-pending-config = Доступ активен, но VPN-профиль ещё готовится. Попробуйте через минуту.
bot-onboarding-connection-config-unavailable = VPN-профиль пока недоступен. Попробуйте позже или обратитесь в поддержку.
bot-onboarding-connection-disabled = Выдача VPN-подключения временно недоступна.
bot-onboarding-connection-private-chat-required = Откройте этого бота в личном чате, чтобы получить VPN-ссылку или QR-код.
bot-onboarding-connection-session-expired = Эта сессия подключения истекла. Отправьте /connect ещё раз.
bot-onboarding-connection-link-message = 🔗 <b>Ссылка подключения</b>

    <code>{ $url }</code>

    Скопируйте её в VPN-приложение. Не пересылайте эту ссылку.

bot-onboarding-connection-qr-caption = Отсканируйте этот QR-код в VPN-приложении. Не пересылайте его.
bot-onboarding-connection-mark-connected-confirmed = ✅ Подключение записано. Вы можете вернуться сюда за ссылкой или инструкцией.
bot-onboarding-connection-dashboard-message = Откройте приложение CyberVPN или Mini App, чтобы управлять подпиской и устройствами.
bot-onboarding-connection-help = <b>Помощь по подключению CyberVPN</b>

    Используйте /code, чтобы применить invite, gift или promo-код.
    Используйте /connect, чтобы получить приватную VPN-ссылку или QR-код.
    Используйте /instructions, чтобы открыть инструкции снова.

bot-onboarding-connection-instructions-generic = 📖 <b>Инструкция подключения</b>

    1) Установите Hiddify, Streisand, V2rayNG или другое совместимое VPN-приложение.
    2) Нажмите Link или QR в этом чате.
    3) Импортируйте профиль.
    4) Подключитесь и проверьте, что трафик идёт через VPN.

bot-onboarding-connection-instructions-ios = 📖 <b>iOS</b>

    1) Установите Streisand или Hiddify из App Store.
    2) Нажмите Link или QR в этом чате.
    3) Импортируйте профиль в приложение.
    4) Разрешите VPN-профиль, когда iOS спросит.
    5) Подключитесь.

bot-onboarding-connection-instructions-android = 📖 <b>Android</b>

    1) Установите Hiddify или V2rayNG.
    2) Нажмите Link или QR в этом чате.
    3) Импортируйте профиль в приложение.
    4) Подключитесь и разрешите приложению работу в фоне.

bot-onboarding-connection-instructions-windows = 📖 <b>Windows</b>

    1) Установите Hiddify или Nekoray.
    2) Нажмите Link и скопируйте URL подключения.
    3) Импортируйте из буфера обмена в приложении.
    4) Подключитесь.

bot-onboarding-connection-instructions-macos = 📖 <b>macOS</b>

    1) Установите Streisand или Hiddify.
    2) Нажмите Link или QR в этом чате.
    3) Импортируйте профиль в приложение.
    4) Подключитесь.

bot-onboarding-connection-instructions-linux = 📖 <b>Linux</b>

    1) Установите Hiddify или Nekoray.
    2) Нажмите Link и скопируйте URL подключения.
    3) Импортируйте из буфера обмена в приложении.
    4) Подключитесь.

bot-onboarding-connection-open-link-button = 🔗 Link
bot-onboarding-connection-show-qr-button = 📷 QR
bot-onboarding-connection-mark-connected-button = ✅ Я подключился
bot-onboarding-connection-dashboard-button = 📊 Кабинет
bot-onboarding-connection-open-private-chat-button = Открыть личный чат
bot-onboarding-connection-connect-button = Подключить VPN
bot-onboarding-connection-instructions-button = Инструкция
bot-onboarding-connection-platform-ios = iOS
bot-onboarding-connection-platform-android = Android
bot-onboarding-connection-platform-windows = Windows
bot-onboarding-connection-platform-macos = macOS
bot-onboarding-connection-platform-linux = Linux

# ── Доступ / Условия ────────────────────────────────────────────────────
access-rules = 📜 <b>Правила использования</b>

    Перед использованием ознакомьтесь с правилами:
    { $rules_url }

access-channel-required = 📢 <b>Подпишитесь на канал</b>

    Для продолжения необходимо подписаться на наш канал.

access-channel-not-member = ❌ Вы ещё не подписаны на канал. Подпишитесь и нажмите «Проверить».

access-maintenance = 🔧 <b>Технические работы</b>

    Бот временно недоступен. Попробуйте позже.

access-invite-only = 🔒 Бот доступен только по приглашениям.

# ── Язык ─────────────────────────────────────────────────────────────────
language-select = 🌐 <b>Выберите язык / Select language:</b>

language-select-prompt = 🌐 <b>Выберите язык:</b>

language-changed = ✅ Язык изменён на { $language ->
        [ru] <b>Русский</b>
        [en] <b>English</b>
       *[other] <b>{ $language }</b>
    }.

# ── История подписок ─────────────────────────────────────────────────────
subscriptions-title = 📦 <b>Ваши подписки</b>
subscriptions-none = 📭 У вас пока нет подписок.
config-select-subscription = 📦 <b>Выберите подписку</b>

    У вас несколько активных подписок. Выберите, для какой подписки отправить VPN-конфигурацию.
status = Статус
expires = Истекает
currency = RUB
