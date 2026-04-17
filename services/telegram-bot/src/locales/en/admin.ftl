# CyberVPN Telegram Bot — Admin Panel (en)

# ── Admin Main Menu ──────────────────────────────────────────────────────
admin-panel-title = 🛠 <b>CyberVPN Control Panel</b>

admin-menu-stats = 📊 Statistics
admin-menu-users = 👥 Users
admin-menu-broadcast = 📢 Broadcast
admin-menu-plans = 📋 Plans
admin-menu-promos = 🎟 Promo Codes
admin-menu-system = ⚙️ System
admin-menu-logs = 📝 Logs

# ── Statistics ───────────────────────────────────────────────────────────
admin-stats-title = 📊 <b>CyberVPN Statistics</b>

admin-stats-users = 👥 Total users: <b>{ $total }</b>
    ✅ Active: { $active }
    📅 Today: { $today }
    📅 This week: { $week }

admin-stats-subscriptions = 💳 Subscriptions:
    ✅ Active: <b>{ $active }</b>
    ⏰ Expiring (3 days): { $expiring }
    ❌ Expired: { $expired }

admin-stats-revenue = 💰 Revenue:
    📅 Today: <b>{ $today }</b>
    📅 This week: { $week }
    📅 This month: { $month }
    📅 Total: { $total }

admin-stats-traffic = 📊 Traffic:
    📤 Upload: { $upload }
    📥 Download: { $download }
    📊 Total: { $total }

admin-stats-servers = 🖥 Servers:
    ✅ Online: { $online }
    ❌ Offline: { $offline }
    ⚠️ Warning: { $warning }

# ── User Management ──────────────────────────────────────────────────────
admin-user-search = 🔍 Enter Telegram ID or username to search:

admin-user-info = 👤 <b>User</b>

    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Username: @{ $username }
    📅 Registered: { $registered_at }
    💳 Subscription: { $subscription_status }
    👥 Referrals: { $referrals }
    🌐 Language: { $language }
    </blockquote>

admin-user-actions = Choose an action:

admin-user-block = 🚫 Block
admin-user-unblock = ✅ Unblock
admin-user-extend = 📅 Extend Subscription
admin-user-message = 💬 Send Message
admin-user-reset-traffic = 🔄 Reset Traffic

admin-user-blocked = ✅ User { $username } has been blocked.
admin-user-unblocked = ✅ User { $username } has been unblocked.
admin-user-extended = ✅ Subscription for { $username } extended by { $days ->
        [one] { $days } day
       *[other] { $days } days
    }.

# ── Broadcast ────────────────────────────────────────────────────────────
admin-broadcast-title = 📢 <b>Broadcast</b>

admin-broadcast-select-audience = Select audience:

admin-broadcast-all = 👥 All Users
admin-broadcast-active = ✅ Active Subscribers
admin-broadcast-expired = ❌ Expired Subscriptions
admin-broadcast-trial = 🎁 Trial Users

admin-broadcast-enter-message = 📝 Enter broadcast message (HTML supported):

admin-broadcast-preview = 📋 <b>Preview:</b>

    { $message }

    Audience: { $audience }
    Recipients: { $count }

admin-broadcast-confirm = Send broadcast?

admin-broadcast-started = ✅ Broadcast started. Sent: { $sent } / { $total }

admin-broadcast-completed = ✅ <b>Broadcast Complete!</b>

    📨 Sent: { $sent }
    ❌ Errors: { $errors }
    ⏱ Duration: { $duration }

# ── Plan Management ──────────────────────────────────────────────────────
admin-plans-title = 📋 <b>Subscription Plans</b>

admin-plan-info = 📋 <b>{ $name }</b>
    💰 Price: { $price }
    ⏳ Duration: { $duration }
    📊 Traffic: { $traffic }
    ✅ Active: { $is_active }

admin-plan-open-offer = 🔗 Open Direct Offer

# ── Promo Codes ──────────────────────────────────────────────────────────
admin-promos-title = 🎟 <b>Promo Codes</b>

admin-promo-create = ➕ Create Promo Code
admin-promo-list = 📋 Promo Code List

admin-promo-info = 🎟 <b>{ $code }</b>
    📋 Type: { $type }
    📊 Used: { $used } / { $limit }
    📅 Expires: { $expires_at }
    ✅ Active: { $is_active }

# ── System ───────────────────────────────────────────────────────────────
admin-system-title = ⚙️ <b>System</b>

admin-system-health = 🏥 <b>System Health</b>

    🟢 Backend API: { $backend_status }
    🟢 Redis: { $redis_status }
    🟢 Bot: { $bot_uptime }
    📊 Memory: { $memory_usage }
