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

# ── Меню ─────────────────────────────────────────────────────────────────
menu-main-title = 🏠 <b>Главное меню</b>

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

    📊 Лимит трафика: { $traffic_gb } ГБ

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

# ── Подписка и планы ─────────────────────────────────────────────────────
subscription-select-plan = 💳 <b>Выберите тариф</b>

    Можно сменить позже.

subscription-select-duration = ⏰ <b>Выберите длительность</b>

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

# ── Поддержка ────────────────────────────────────────────────────────────
support-message = 🆘 <b>Поддержка</b>

    По всем вопросам: { $contact }

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
status = Статус
expires = Истекает
currency = RUB
