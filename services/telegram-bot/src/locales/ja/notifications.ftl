# CyberVPN Telegram Bot — Notifications (en)

# ── Subscription Expiry ──────────────────────────────────────────────────
notify-expiring-soon = ⏰ <b>Subscription Expiring!</b>

    Your subscription will expire in { $days ->
        [one] { $days } day
       *[other] { $days } days
    }.

    Renew now to keep your access.

notify-expired = ❌ <b>Subscription Expired</b>

    Your CyberVPN subscription has ended.
    Renew to restore access.

# ── Traffic ──────────────────────────────────────────────────────────────
notify-traffic-warning = ⚠️ <b>Traffic Running Low!</b>

    Remaining: { $remaining }
    Upgrade your plan or wait for the limit to reset.

notify-traffic-exhausted = 🚫 <b>Traffic Exhausted</b>

    You've used all available traffic.
    Upgrade your plan to continue.

# ── Referral System ──────────────────────────────────────────────────────
notify-referral-joined = 🎉 <b>New Referral!</b>

    User { $name } registered via your link.

notify-referral-reward = 🎁 <b>Referral Bonus!</b>

    You earned { $days ->
        [one] { $days } day
       *[other] { $days } days
    } of subscription for inviting { $name }.

notify-referral-reward-error = ⚠️ <b>Bonus Error</b>

    Failed to apply referral bonus. Please contact support.

# ── Payments ─────────────────────────────────────────────────────────────
notify-payment-received = ✅ <b>Payment Received!</b>

    Amount: { $amount }
    Subscription activated.

notify-payment-refunded = 💸 <b>Refund Processed</b>

    Refunded: { $amount }

# ── System ───────────────────────────────────────────────────────────────
notify-maintenance-start = 🔧 <b>Maintenance</b>

    The bot will be temporarily unavailable for updates.
    We apologize for the inconvenience.

notify-maintenance-end = ✅ <b>Maintenance Complete</b>

    The bot is back online. Thank you for your patience!

# ── Broadcasts ───────────────────────────────────────────────────────────
notify-broadcast-default = 📢 <b>CyberVPN Notification</b>

    { $message }
