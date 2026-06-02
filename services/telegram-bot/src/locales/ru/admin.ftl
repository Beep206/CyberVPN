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

# ── Handler Coverage Audit ───────────────────────────────────────────────
active = Активно
admin-access-add = Добавить администратора
admin-access-add-prompt = Отправьте Telegram ID или username, чтобы добавить администратора.
admin-access-added = Администратор { $username } ({ $admin_id }) добавлен.
admin-access-blacklist = Чёрный список
admin-access-cannot-remove-self = Нельзя удалить самого себя из администраторов.
admin-access-channel-required = Требуется подписка на канал
admin-access-edit-rules = Редактировать правила доступа
admin-access-invalid-id = Некорректный Telegram ID. Проверьте значение и попробуйте снова.
admin-access-mode = Режим доступа
admin-access-remove = Удалить администратора
admin-access-remove-prompt = Отправьте Telegram ID, чтобы удалить администратора.
admin-access-removed = Администратор { $admin_id } удалён.
admin-access-rules-enabled = Правила доступа включены
admin-access-set-channel = Указать обязательный канал
admin-access-title = 🔐 <b>Контроль доступа</b>
admin-access-whitelist = Белый список
admin-broadcast = Рассылка
admin-broadcast-audience-active = Активные подписчики
admin-broadcast-audience-all = Все пользователи
admin-broadcast-audience-inactive = Неактивные пользователи
admin-broadcast-audience-trial = Пользователи пробного периода
admin-broadcast-cancelled = Рассылка отменена.
admin-broadcast-compose-prompt = Отправьте текст рассылки. Telegram HTML поддерживается.
admin-broadcast-confirm-prompt = Отправить эту рассылку аудитории <b>{ $audience }</b>?
    Оценка получателей: <b>{ $count }</b>
admin-broadcast-history-title = 📢 <b>История рассылок</b>
admin-broadcast-no-history = Истории рассылок пока нет.
admin-broadcast-sending = Рассылка { $broadcast_id } отправляется.
admin-feature-coming-soon = Эта админ-функция появится позже.
admin-gateway-cryptomus = Cryptomus
admin-gateway-cryptomus-settings = Настройки Cryptomus
admin-gateway-details = 💳 <b>{ $name }</b>
    Тип: { $type }
    Комиссия: { $commission }
    Включён: { $is_enabled }
admin-gateway-disable = Отключить шлюз
admin-gateway-disabled = Платёжный шлюз отключён.
admin-gateway-enable = Включить шлюз
admin-gateway-enabled = Платёжный шлюз включён.
admin-gateway-stripe = Stripe
admin-gateway-stripe-settings = Настройки Stripe
admin-gateway-telegram-stars = Telegram Stars
admin-gateway-test-mode = Тестовый режим
admin-gateway-yookassa = YooKassa
admin-gateway-yookassa-settings = Настройки YooKassa
admin-gateways-title = 💳 <b>Платёжные шлюзы</b>
admin-help-access-control = Контроль доступа
admin-help-admin-panel = Открыть админ-панель
admin-help-ban-users = Бан и разбан пользователей
admin-help-broadcast = Рассылки
admin-help-broadcast-history = Просмотр истории рассылок
admin-help-cache-management = Управление кэшем
admin-help-commands = Команды
admin-help-create-plans = Создание тарифов
admin-help-create-promos = Создание промокодов
admin-help-detailed-stats = Подробная статистика
admin-help-extend-subs = Продление подписок
admin-help-footer = Используйте админ-действия только для разрешённых операционных задач.
admin-help-import-data = Импорт данных
admin-help-import-sync = Импорт и синхронизация
admin-help-manage-plans = Управление тарифами
admin-help-manage-promos = Управление промокодами
admin-help-notifications = Настройки уведомлений
admin-help-payment-gateways = Платёжные шлюзы
admin-help-plans = Тарифы
admin-help-promos = Промокоды
admin-help-referral-program = Реферальная программа
admin-help-search-users = Поиск пользователей
admin-help-send-broadcast = Отправить рассылку
admin-help-settings = Настройки
admin-help-show-help = Показать справку
admin-help-statistics = Статистика
admin-help-sync-remnawave = Синхронизация Remnawave
admin-help-system = Система
admin-help-system-health = Здоровье системы
admin-help-system-logs = Системные логи
admin-help-title = 🛠 <b>Справка администратора</b>
admin-help-user-management = Управление пользователями
admin-help-view-stats = Просмотр статистики
admin-help-view-users = Просмотр пользователей
admin-import-export-subscriptions = Экспорт подписок
admin-import-export-users = Экспорт пользователей
admin-import-idle = Ожидание
admin-import-last-error = Последняя ошибка
admin-import-last-sync = Последняя синхронизация
admin-import-refresh = Обновить статус импорта
admin-import-status = Статус
admin-import-status-title = 🔄 <b>Статус импорта</b>
admin-import-subscriptions = Импорт подписок
admin-import-subscriptions-completed = Импорт подписок завершён.
    Импортировано: { $imported }
    Обновлено: { $updated }
    Ошибок: { $errors }
admin-import-subscriptions-csv = Импорт подписок из CSV
admin-import-subscriptions-failed = Импорт подписок не удался: { $error }
admin-import-subscriptions-starting = Запускаю импорт подписок.
admin-import-sync-completed = Синхронизация Remnawave завершена.
    Пользователи: { $users }
    Подписки: { $subscriptions }
    Конфиги: { $configs }
admin-import-sync-errors = Ошибки синхронизации
admin-import-sync-failed = Синхронизация Remnawave не удалась: { $error }
admin-import-sync-remnawave = Синхронизировать Remnawave
admin-import-sync-starting = Запускаю синхронизацию Remnawave.
admin-import-sync-status = Статус синхронизации
admin-import-syncing = Синхронизация
admin-import-title = 🔄 <b>Импорт и синхронизация</b>
admin-import-users = Импорт пользователей
admin-import-users-completed = Импорт пользователей завершён.
    Импортировано: { $imported }
    Пропущено: { $skipped }
    Ошибок: { $errors }
admin-import-users-csv = Импорт пользователей из CSV
admin-import-users-failed = Импорт пользователей не удался: { $error }
admin-import-users-starting = Запускаю импорт пользователей.
admin-logs-export = Экспорт логов
admin-logs-export-completed = Экспорт логов завершён.
admin-logs-export-started = Экспорт логов запущен.
admin-logs-no-logs = Логи недоступны.
admin-logs-refresh = Обновить логи
admin-logs-title = 📝 <b>Системные логи</b>
admin-notif-expiry-days = Дней до истечения
admin-notif-expiry-enabled = Уведомления об истечении
admin-notif-payment-enabled = Уведомления об оплатах
admin-notif-referral-enabled = Уведомления о рефералах
admin-notif-system-enabled = Системные уведомления
admin-notif-test = Отправить тестовое уведомление
admin-notif-time-window = Окно отправки уведомлений
admin-notifications-disabled = Уведомления { $type } отключены.
admin-notifications-enabled = Уведомления { $type } включены.
admin-notifications-expiry = Истечение
admin-notifications-payment = Платежи
admin-notifications-referral = Рефералы
admin-notifications-title = 🔔 <b>Настройки уведомлений</b>
admin-notifications-toggle-expiry = Переключить уведомления об истечении
admin-notifications-toggle-payment = Переключить уведомления об оплатах
admin-notifications-toggle-referral = Переключить уведомления о рефералах
admin-notifications-toggle-trial = Переключить уведомления о пробном периоде
admin-notifications-trial = Пробный период
admin-plan-create-description-prompt = Отправьте описание тарифа.
admin-plan-create-price-invalid = Цена должна быть больше нуля.
admin-plan-create-price-invalid-number = Отправьте корректную числовую цену.
admin-plan-create-price-prompt = Отправьте цену тарифа.
admin-plan-created = Тариф <b>{ $name }</b> создан.
    ID: <code>{ $plan_id }</code>
    Цена: { $price }
admin-plan-disable = Отключить тариф
admin-plan-disabled = Тариф отключён.
admin-plan-edit = Редактировать тариф
admin-plan-enable = Включить тариф
admin-plan-enabled = Тариф включён.
admin-plans = Тарифы
admin-plans-create = Создать тариф
admin-promo-create-code-invalid-length = Некорректная длина промокода.
admin-promo-create-code-prompt = Отправьте промокод.
admin-promo-create-confirm = Создать промокод
admin-promo-create-discount-invalid-number = Отправьте корректное число скидки.
admin-promo-create-discount-invalid-range = Скидка должна быть в допустимом диапазоне.
admin-promo-create-discount-prompt = Отправьте размер скидки.
admin-promo-create-limit-invalid = Лимит использований должен быть нулём или больше.
admin-promo-create-limit-invalid-number = Отправьте корректный лимит использований.
admin-promo-create-limit-prompt = Отправьте лимит использований промокода.
admin-promo-create-new = Создать новый промокод
admin-promo-created = Промокод <b>{ $code }</b> создан.
    ID: <code>{ $promo_id }</code>
    Скидка: { $discount }
    Лимит: { $limit }
admin-promo-delete = Удалить промокод
admin-promo-details = 🎟 <b>{ $code }</b>
    Скидка: { $discount_type } { $discount_value }
    Использован: { $usage_count } / { $usage_limit }
    Истекает: { $expires_at }
    Активен: { $is_active }
admin-promo-disable = Отключить промокод
admin-promo-disabled = Промокод отключён.
admin-promo-discount-type = Тип скидки
admin-promo-duration-type = Тип длительности
admin-promo-edit = Редактировать промокод
admin-promo-enable = Включить промокод
admin-promo-enabled = Промокод включён.
admin-promo-stats = Статистика промокода
admin-promo-toggle = Переключить промокод
admin-promo-usage-limit = Лимит использований
admin-promos-create = Создать промокод
admin-referral-bonus-invalid-number = Отправьте корректное число бонуса.
admin-referral-bonus-invalid-range = Бонус вне допустимого диапазона.
admin-referral-bonus-updated = Реферальный бонус обновлён: { $bonus }.
admin-referral-disable = Отключить реферальную программу
admin-referral-disabled = Реферальная программа отключена.
admin-referral-edit-bonus = Изменить реферальный бонус
admin-referral-edit-bonus-prompt = Отправьте значение реферального бонуса.
admin-referral-edit-withdrawal = Изменить минимальный вывод
admin-referral-edit-withdrawal-prompt = Отправьте минимальную сумму вывода.
admin-referral-enable = Включить реферальную программу
admin-referral-enabled = Реферальная программа включена.
admin-referral-first-purchase-bonus = Бонус за первую покупку
admin-referral-first-purchase-disabled = Бонус за первую покупку отключён.
admin-referral-first-purchase-enabled = Бонус за первую покупку включён.
admin-referral-lifetime = Пожизненные рефералы
admin-referral-lifetime-disabled = Пожизненные рефералы отключены.
admin-referral-lifetime-enabled = Пожизненные рефералы включены.
admin-referral-min-withdrawal = Минимальный вывод
admin-referral-reward = Реферальная награда
admin-referral-settings-info = 👥 <b>Настройки рефералов</b>
    Включено: { $is_enabled }
    Бонус: { $bonus_percent }
    Минимальный вывод: { $min_withdrawal }
admin-referral-settings-title = 👥 <b>Настройки рефералов</b>
admin-referral-stats = Статистика рефералов
admin-referral-stats-details = 👥 <b>Статистика рефералов</b>
    Всего: { $total }
    Активных: { $active }
    В ожидании: { $pending }
    Оплачено: { $paid }
admin-referral-system-disabled = Реферальная система отключена.
admin-referral-system-enabled = Реферальная система включена.
admin-referral-type = Тип реферальной награды
admin-referral-type-fixed = Выбрана фиксированная реферальная награда.
admin-referral-type-percentage = Выбрана процентная реферальная награда.
admin-referral-withdrawal-invalid = Некорректная сумма вывода.
admin-referral-withdrawal-invalid-number = Отправьте корректную сумму вывода.
admin-referral-withdrawal-updated = Минимальный вывод обновлён: { $amount }.
admin-remnawave-refresh = Обновить статистику Remnawave
admin-remnawave-stats = 🌊 <b>Статистика Remnawave</b>
    Пользователи: { $users }
    Активные подписки: { $active_subs }
    Серверы: { $servers }
    Трафик: { $traffic }
admin-revenue = Доход
admin-search-user = Поиск пользователя
admin-settings = Настройки
admin-settings-access = Контроль доступа
admin-settings-gateways = Платёжные шлюзы
admin-settings-notifications = Уведомления
admin-settings-referral = Настройки рефералов
admin-settings-title = ⚙️ <b>Настройки администратора</b>
admin-stats = Статистика
admin-stats-detailed = Подробная статистика
admin-stats-detailed-title = 📊 <b>Подробная статистика</b>
admin-stats-overview = 📊 <b>Обзор статистики</b>
    Всего пользователей: { $total_users }
    Активные подписки: { $active_subs }
    Новых сегодня: { $new_today }
    Новых за неделю: { $new_week }
    Новых за месяц: { $new_month }
    Доход: { $revenue }
admin-stats-payments = Платежи
admin-stats-plans = Тарифы
admin-stats-referrals = Рефералы
admin-system-cache = Кэш
admin-system-cache-clear = Очистить кэш
admin-system-cache-cleared = Кэш очищен: { $count } ключей.
admin-system-cache-hit-rate = Hit rate
admin-system-cache-keys = Ключи
admin-system-cache-memory = Память
admin-system-cache-title = 💾 <b>Кэш</b>
admin-system-health-title = 🏥 <b>Здоровье системы</b>
admin-system-logs = Логи
admin-system-logs-title = 📝 <b>Системные логи</b>
admin-system-no-logs = Системные логи недоступны.
admin-system-refresh = Обновить
admin-user-ban = Заблокировать пользователя
admin-user-banned = Пользователь заблокирован.
admin-user-details = 👤 <b>Данные пользователя</b>
    ID: <code>{ $user_id }</code>
    Имя: { $first_name }
    Username: { $username }
    Язык: { $language }
    Регистрация: { $registered }
    Всего подписок: { $total_subs }
    Активные подписки: { $active_subs }
admin-user-extend-invalid-days = Количество дней должно быть больше нуля.
admin-user-extend-invalid-number = Отправьте корректное количество дней.
admin-user-extend-prompt = Отправьте количество дней для продления.
admin-user-extend-sub = Продлить подписку
admin-user-unbanned = Пользователь разблокирован.
admin-users = Пользователи
admin-users-list-recent = Последние пользователи
admin-users-list-title = 👥 <b>Список пользователей</b>
admin-users-no-users = Пользователи не найдены.
admin-users-search = Поиск пользователей
admin-users-search-no-results = По этому запросу пользователи не найдены.
admin-users-search-prompt = Отправьте Telegram ID, username или имя для поиска.
admin-users-search-results = Найдено пользователей: { $count }.
admin-users-title = 👥 <b>Управление пользователями</b>
broadcast-active-subscribers = Активные подписчики
broadcast-all-users = Все пользователи
broadcast-expired-subscribers = Подписчики с истёкшей подпиской
broadcast-no-subscription = Пользователи без подписки
broadcast-trial-users = Пользователи пробного периода
button-main-menu = Главное меню
button-next = Далее
button-prev = Назад
days = дней
error-export-failed = Экспорт не удался.
failed = Неуспешно
never = Никогда
no = Нет
pagination-next = Следующая страница
pagination-prev = Предыдущая страница
plans-create-new = Создать новый тариф
plans-durations = Длительности
plans-edit-existing = Редактировать существующий тариф
plans-pricing = Цены
plans-toggle-active = Переключить активность
plans-view-all = Все тарифы
stats-overview = Обзор
stats-revenue = Доход
stats-traffic = Трафик
stats-users = Пользователи
successful = Успешно
total = Всего
unlimited = Безлимитно
users-active = Активные пользователи
users-all = Все пользователи
users-expired = Истёкшие пользователи
users-export = Экспорт пользователей
users-search = Поиск пользователей
users-trial = Пользователи пробного периода
yes = Да
