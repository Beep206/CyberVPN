# CyberVPN Telegram Bot — Админ-панель (ru)

# ── Главное меню админа ──────────────────────────────────────────────────
admin-panel-title = 🛠 <b>Панель управления CyberVPN</b>

admin-menu-stats = 📊 Статистика
admin-menu-users = 👥 Пользователи
admin-menu-broadcast = 📢 Рассылка
admin-menu-plans = 📋 Тарифы
admin-menu-promos = 🎟 Промокоды
admin-menu-system = ⚙️ Система
admin-menu-logs = 📝 Логи

# ── Статистика ───────────────────────────────────────────────────────────
admin-stats-title = 📊 <b>Статистика CyberVPN</b>

admin-stats-users = 👥 Всего пользователей: <b>{ $total }</b>
    ✅ Активных: { $active }
    📅 За сегодня: { $today }
    📅 За неделю: { $week }

admin-stats-subscriptions = 💳 Подписки:
    ✅ Активных: <b>{ $active }</b>
    ⏰ Истекающих (3 дня): { $expiring }
    ❌ Истёкших: { $expired }

admin-stats-revenue = 💰 Доход:
    📅 За сегодня: <b>{ $today }</b>
    📅 За неделю: { $week }
    📅 За месяц: { $month }
    📅 Всего: { $total }

admin-stats-traffic = 📊 Трафик:
    📤 Исходящий: { $upload }
    📥 Входящий: { $download }
    📊 Всего: { $total }

admin-stats-servers = 🖥 Серверы:
    ✅ Онлайн: { $online }
    ❌ Офлайн: { $offline }
    ⚠️ Предупреждение: { $warning }

# ── Управление пользователями ────────────────────────────────────────────
admin-user-search = 🔍 Введите Telegram ID или username для поиска:

admin-user-info = 👤 <b>Пользователь</b>

    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Username: @{ $username }
    📅 Регистрация: { $registered_at }
    💳 Подписка: { $subscription_status }
    👥 Рефералов: { $referrals }
    🌐 Язык: { $language }
    </blockquote>

admin-user-actions = Выберите действие:

admin-user-block = 🚫 Заблокировать
admin-user-unblock = ✅ Разблокировать
admin-user-extend = 📅 Продлить подписку
admin-user-message = 💬 Написать сообщение
admin-user-reset-traffic = 🔄 Сбросить трафик

admin-user-blocked = ✅ Пользователь { $username } заблокирован.
admin-user-unblocked = ✅ Пользователь { $username } разблокирован.
admin-user-extended = ✅ Подписка { $username } продлена на { $days ->
        [one] { $days } день
        [few] { $days } дня
       *[other] { $days } дней
    }.

# ── Рассылка ─────────────────────────────────────────────────────────────
admin-broadcast-title = 📢 <b>Рассылка</b>

admin-broadcast-select-audience = Выберите аудиторию:

admin-broadcast-all = 👥 Все пользователи
admin-broadcast-active = ✅ Активные подписчики
admin-broadcast-expired = ❌ С истёкшей подпиской
admin-broadcast-trial = 🎁 Пробные пользователи

admin-broadcast-enter-message = 📝 Введите текст рассылки (поддерживается HTML):

admin-broadcast-preview = 📋 <b>Предварительный просмотр:</b>

    { $message }

    Аудитория: { $audience }
    Получателей: { $count }

admin-broadcast-confirm = Отправить рассылку?

admin-broadcast-started = ✅ Рассылка запущена. Отправлено: { $sent } / { $total }

admin-broadcast-completed = ✅ <b>Рассылка завершена!</b>

    📨 Отправлено: { $sent }
    ❌ Ошибок: { $errors }
    ⏱ Время: { $duration }

# ── Управление планами ───────────────────────────────────────────────────
admin-plans-title = 📋 <b>Тарифные планы</b>

admin-plan-info = 📋 <b>{ $name }</b>
    💰 Цена: { $price }
    ⏳ Длительность: { $duration }
    📊 Трафик: { $traffic }
    ✅ Активен: { $is_active }

admin-plan-open-offer = 🔗 Открыть direct-offer

# ── Промокоды ────────────────────────────────────────────────────────────
admin-promos-title = 🎟 <b>Промокоды</b>

admin-promo-create = ➕ Создать промокод
admin-promo-list = 📋 Список промокодов

admin-promo-info = 🎟 <b>{ $code }</b>
    📋 Тип: { $type }
    📊 Использован: { $used } / { $limit }
    📅 Истекает: { $expires_at }
    ✅ Активен: { $is_active }

# ── Система ──────────────────────────────────────────────────────────────
admin-system-title = ⚙️ <b>Система</b>

admin-system-health = 🏥 <b>Здоровье системы</b>

    🟢 Backend API: { $backend_status }
    🟢 Redis: { $redis_status }
    🟢 Bot: { $bot_uptime }
    📊 Память: { $memory_usage }
