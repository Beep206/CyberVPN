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

# ── Handler Coverage Audit ───────────────────────────────────────────────
active = Active
admin-access-add = Add admin
admin-access-add-prompt = Send the Telegram ID or username to add as an admin.
admin-access-added = Admin { $username } ({ $admin_id }) added.
admin-access-blacklist = Blacklist
admin-access-cannot-remove-self = You cannot remove yourself from admins.
admin-access-channel-required = Channel subscription required
admin-access-edit-rules = Edit access rules
admin-access-invalid-id = Invalid Telegram ID. Check the value and try again.
admin-access-mode = Access mode
admin-access-remove = Remove admin
admin-access-remove-prompt = Send the Telegram ID to remove from admins.
admin-access-removed = Admin { $admin_id } removed.
admin-access-rules-enabled = Access rules enabled
admin-access-set-channel = Set required channel
admin-access-title = 🔐 <b>Access Control</b>
admin-access-whitelist = Whitelist
admin-broadcast = Broadcast
admin-broadcast-audience-active = Active subscribers
admin-broadcast-audience-all = All users
admin-broadcast-audience-inactive = Inactive users
admin-broadcast-audience-trial = Trial users
admin-broadcast-cancelled = Broadcast cancelled.
admin-broadcast-compose-prompt = Send the broadcast message. Telegram HTML is supported.
admin-broadcast-confirm-prompt = Send this broadcast to <b>{ $audience }</b>?
    Estimated recipients: <b>{ $count }</b>
admin-broadcast-history-title = 📢 <b>Broadcast history</b>
admin-broadcast-no-history = No broadcast history yet.
admin-broadcast-sending = Broadcast { $broadcast_id } is being sent.
admin-feature-coming-soon = This admin feature is coming soon.
admin-gateway-cryptomus = Cryptomus
admin-gateway-cryptomus-settings = Cryptomus settings
admin-gateway-details = 💳 <b>{ $name }</b>
    Type: { $type }
    Commission: { $commission }
    Enabled: { $is_enabled }
admin-gateway-disable = Disable gateway
admin-gateway-disabled = Gateway disabled.
admin-gateway-enable = Enable gateway
admin-gateway-enabled = Gateway enabled.
admin-gateway-stripe = Stripe
admin-gateway-stripe-settings = Stripe settings
admin-gateway-telegram-stars = Telegram Stars
admin-gateway-test-mode = Test mode
admin-gateway-yookassa = YooKassa
admin-gateway-yookassa-settings = YooKassa settings
admin-gateways-title = 💳 <b>Payment gateways</b>
admin-help-access-control = Access control
admin-help-admin-panel = Open admin panel
admin-help-ban-users = Ban or unban users
admin-help-broadcast = Broadcasts
admin-help-broadcast-history = View broadcast history
admin-help-cache-management = Cache management
admin-help-commands = Commands
admin-help-create-plans = Create plans
admin-help-create-promos = Create promo codes
admin-help-detailed-stats = Detailed statistics
admin-help-extend-subs = Extend subscriptions
admin-help-footer = Use admin actions only for authorized operational work.
admin-help-import-data = Import data
admin-help-import-sync = Import and sync
admin-help-manage-plans = Manage plans
admin-help-manage-promos = Manage promo codes
admin-help-notifications = Notification settings
admin-help-payment-gateways = Payment gateways
admin-help-plans = Plans
admin-help-promos = Promo codes
admin-help-referral-program = Referral program
admin-help-search-users = Search users
admin-help-send-broadcast = Send broadcast
admin-help-settings = Settings
admin-help-show-help = Show help
admin-help-statistics = Statistics
admin-help-sync-remnawave = Sync Remnawave
admin-help-system = System
admin-help-system-health = System health
admin-help-system-logs = System logs
admin-help-title = 🛠 <b>Admin help</b>
admin-help-user-management = User management
admin-help-view-stats = View statistics
admin-help-view-users = View users
admin-import-export-subscriptions = Export subscriptions
admin-import-export-users = Export users
admin-import-idle = Idle
admin-import-last-error = Last error
admin-import-last-sync = Last sync
admin-import-refresh = Refresh import status
admin-import-status = Status
admin-import-status-title = 🔄 <b>Import status</b>
admin-import-subscriptions = Import subscriptions
admin-import-subscriptions-completed = Subscriptions import completed.
    Imported: { $imported }
    Updated: { $updated }
    Errors: { $errors }
admin-import-subscriptions-csv = Import subscriptions from CSV
admin-import-subscriptions-failed = Subscriptions import failed: { $error }
admin-import-subscriptions-starting = Starting subscriptions import.
admin-import-sync-completed = Remnawave sync completed.
    Users: { $users }
    Subscriptions: { $subscriptions }
    Configs: { $configs }
admin-import-sync-errors = Sync errors
admin-import-sync-failed = Remnawave sync failed: { $error }
admin-import-sync-remnawave = Sync Remnawave
admin-import-sync-starting = Starting Remnawave sync.
admin-import-sync-status = Sync status
admin-import-syncing = Syncing
admin-import-title = 🔄 <b>Import and sync</b>
admin-import-users = Import users
admin-import-users-completed = Users import completed.
    Imported: { $imported }
    Skipped: { $skipped }
    Errors: { $errors }
admin-import-users-csv = Import users from CSV
admin-import-users-failed = Users import failed: { $error }
admin-import-users-starting = Starting users import.
admin-logs-export = Export logs
admin-logs-export-completed = Logs export completed.
admin-logs-export-started = Logs export started.
admin-logs-no-logs = No logs available.
admin-logs-refresh = Refresh logs
admin-logs-title = 📝 <b>System logs</b>
admin-notif-expiry-days = Expiry days
admin-notif-expiry-enabled = Expiry notifications
admin-notif-payment-enabled = Payment notifications
admin-notif-referral-enabled = Referral notifications
admin-notif-system-enabled = System notifications
admin-notif-test = Send test notification
admin-notif-time-window = Notification time window
admin-notifications-disabled = { $type } notifications disabled.
admin-notifications-enabled = { $type } notifications enabled.
admin-notifications-expiry = Expiry
admin-notifications-payment = Payments
admin-notifications-referral = Referrals
admin-notifications-title = 🔔 <b>Notification settings</b>
admin-notifications-toggle-expiry = Toggle expiry notifications
admin-notifications-toggle-payment = Toggle payment notifications
admin-notifications-toggle-referral = Toggle referral notifications
admin-notifications-toggle-trial = Toggle trial notifications
admin-notifications-trial = Trials
admin-plan-create-description-prompt = Send the plan description.
admin-plan-create-price-invalid = Price must be greater than zero.
admin-plan-create-price-invalid-number = Send a valid numeric price.
admin-plan-create-price-prompt = Send the plan price.
admin-plan-created = Plan <b>{ $name }</b> created.
    ID: <code>{ $plan_id }</code>
    Price: { $price }
admin-plan-disable = Disable plan
admin-plan-disabled = Plan disabled.
admin-plan-edit = Edit plan
admin-plan-enable = Enable plan
admin-plan-enabled = Plan enabled.
admin-plans = Plans
admin-plans-create = Create plan
admin-promo-create-code-invalid-length = Promo code length is invalid.
admin-promo-create-code-prompt = Send the promo code.
admin-promo-create-confirm = Create promo code
admin-promo-create-discount-invalid-number = Send a valid discount number.
admin-promo-create-discount-invalid-range = Discount must be within the allowed range.
admin-promo-create-discount-prompt = Send the promo discount.
admin-promo-create-limit-invalid = Usage limit must be zero or greater.
admin-promo-create-limit-invalid-number = Send a valid usage limit.
admin-promo-create-limit-prompt = Send the promo usage limit.
admin-promo-create-new = Create new promo
admin-promo-created = Promo <b>{ $code }</b> created.
    ID: <code>{ $promo_id }</code>
    Discount: { $discount }
    Limit: { $limit }
admin-promo-delete = Delete promo
admin-promo-details = 🎟 <b>{ $code }</b>
    Discount: { $discount_type } { $discount_value }
    Used: { $usage_count } / { $usage_limit }
    Expires: { $expires_at }
    Active: { $is_active }
admin-promo-disable = Disable promo
admin-promo-disabled = Promo disabled.
admin-promo-discount-type = Discount type
admin-promo-duration-type = Duration type
admin-promo-edit = Edit promo
admin-promo-enable = Enable promo
admin-promo-enabled = Promo enabled.
admin-promo-stats = Promo statistics
admin-promo-toggle = Toggle promo
admin-promo-usage-limit = Usage limit
admin-promos-create = Create promo
admin-referral-bonus-invalid-number = Send a valid bonus number.
admin-referral-bonus-invalid-range = Bonus value is outside the allowed range.
admin-referral-bonus-updated = Referral bonus updated: { $bonus }.
admin-referral-disable = Disable referral program
admin-referral-disabled = Referral program disabled.
admin-referral-edit-bonus = Edit referral bonus
admin-referral-edit-bonus-prompt = Send the referral bonus value.
admin-referral-edit-withdrawal = Edit minimum withdrawal
admin-referral-edit-withdrawal-prompt = Send the minimum withdrawal amount.
admin-referral-enable = Enable referral program
admin-referral-enabled = Referral program enabled.
admin-referral-first-purchase-bonus = First purchase bonus
admin-referral-first-purchase-disabled = First purchase bonus disabled.
admin-referral-first-purchase-enabled = First purchase bonus enabled.
admin-referral-lifetime = Lifetime referrals
admin-referral-lifetime-disabled = Lifetime referrals disabled.
admin-referral-lifetime-enabled = Lifetime referrals enabled.
admin-referral-min-withdrawal = Minimum withdrawal
admin-referral-reward = Referral reward
admin-referral-settings-info = 👥 <b>Referral settings</b>
    Enabled: { $is_enabled }
    Bonus: { $bonus_percent }
    Minimum withdrawal: { $min_withdrawal }
admin-referral-settings-title = 👥 <b>Referral settings</b>
admin-referral-stats = Referral statistics
admin-referral-stats-details = 👥 <b>Referral statistics</b>
    Total: { $total }
    Active: { $active }
    Pending: { $pending }
    Paid: { $paid }
admin-referral-system-disabled = Referral system disabled.
admin-referral-system-enabled = Referral system enabled.
admin-referral-type = Referral type
admin-referral-type-fixed = Fixed referral reward selected.
admin-referral-type-percentage = Percentage referral reward selected.
admin-referral-withdrawal-invalid = Withdrawal amount is invalid.
admin-referral-withdrawal-invalid-number = Send a valid withdrawal amount.
admin-referral-withdrawal-updated = Minimum withdrawal updated: { $amount }.
admin-remnawave-refresh = Refresh Remnawave stats
admin-remnawave-stats = 🌊 <b>Remnawave stats</b>
    Users: { $users }
    Active subscriptions: { $active_subs }
    Servers: { $servers }
    Traffic: { $traffic }
admin-revenue = Revenue
admin-search-user = Search user
admin-settings = Settings
admin-settings-access = Access control
admin-settings-gateways = Payment gateways
admin-settings-notifications = Notifications
admin-settings-referral = Referral settings
admin-settings-title = ⚙️ <b>Admin settings</b>
admin-stats = Statistics
admin-stats-detailed = Detailed statistics
admin-stats-detailed-title = 📊 <b>Detailed statistics</b>
admin-stats-overview = 📊 <b>Statistics overview</b>
    Total users: { $total_users }
    Active subscriptions: { $active_subs }
    New today: { $new_today }
    New this week: { $new_week }
    New this month: { $new_month }
    Revenue: { $revenue }
admin-stats-payments = Payments
admin-stats-plans = Plans
admin-stats-referrals = Referrals
admin-system-cache = Cache
admin-system-cache-clear = Clear cache
admin-system-cache-cleared = Cache cleared: { $count } keys.
admin-system-cache-hit-rate = Hit rate
admin-system-cache-keys = Keys
admin-system-cache-memory = Memory
admin-system-cache-title = 💾 <b>Cache</b>
admin-system-health-title = 🏥 <b>System health</b>
admin-system-logs = Logs
admin-system-logs-title = 📝 <b>System logs</b>
admin-system-no-logs = No system logs available.
admin-system-refresh = Refresh
admin-user-ban = Ban user
admin-user-banned = User banned.
admin-user-details = 👤 <b>User details</b>
    ID: <code>{ $user_id }</code>
    Name: { $first_name }
    Username: { $username }
    Language: { $language }
    Registered: { $registered }
    Total subscriptions: { $total_subs }
    Active subscriptions: { $active_subs }
admin-user-extend-invalid-days = Days must be greater than zero.
admin-user-extend-invalid-number = Send a valid number of days.
admin-user-extend-prompt = Send the number of days to extend.
admin-user-extend-sub = Extend subscription
admin-user-unbanned = User unbanned.
admin-users = Users
admin-users-list-recent = Recent users
admin-users-list-title = 👥 <b>Users list</b>
admin-users-no-users = No users found.
admin-users-search = Search users
admin-users-search-no-results = No users found for this query.
admin-users-search-prompt = Send Telegram ID, username, or name to search.
admin-users-search-results = Found users: { $count }.
admin-users-title = 👥 <b>User management</b>
broadcast-active-subscribers = Active subscribers
broadcast-all-users = All users
broadcast-expired-subscribers = Expired subscribers
broadcast-no-subscription = Users without subscription
broadcast-trial-users = Trial users
button-main-menu = Main menu
button-next = Next
button-prev = Previous
days = days
error-export-failed = Export failed.
failed = Failed
never = Never
no = No
pagination-next = Next page
pagination-prev = Previous page
plans-create-new = Create new plan
plans-durations = Durations
plans-edit-existing = Edit existing plan
plans-pricing = Pricing
plans-toggle-active = Toggle active
plans-view-all = View all plans
stats-overview = Overview
stats-revenue = Revenue
stats-traffic = Traffic
stats-users = Users
successful = Successful
total = Total
unlimited = Unlimited
users-active = Active users
users-all = All users
users-expired = Expired users
users-export = Export users
users-search = Search users
users-trial = Trial users
yes = Yes
