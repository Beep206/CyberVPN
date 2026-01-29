# CyberVPN Telegram Bot — Messages (en)

# ── Welcome and Onboarding ───────────────────────────────────────────────
welcome = 👋 <b>Welcome to CyberVPN, { $name }!</b>

    🔐 Fast, secure VPN access to the internet.
    Choose an action from the menu below.

welcome-back = 🔄 <b>Welcome back, { $name }!</b>

    Good to see you again.

# ── Profile ──────────────────────────────────────────────────────────────
profile-title = 👤 <b>Your Profile</b>

profile-info =
    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Name: { $name }
    📅 Registered: { $registered_at }
    🌐 Language: { $language }
    </blockquote>

# ── Subscription Status ──────────────────────────────────────────────────
subscription-status-active = ✅ <b>Subscription Active</b>

    📋 Plan: <b>{ $plan_name }</b>
    ⏳ Expires: { $expires_at }
    📊 Traffic: { $traffic_used } / { $traffic_limit }
    🔗 <a href="{ $subscription_link }">Connection link</a>

subscription-status-expired = ❌ <b>Subscription Expired</b>

    Your subscription ended on { $expired_at }.
    Renew to continue using VPN.

subscription-status-limited = ⚠️ <b>Traffic Exhausted</b>

    You've used all available traffic.
    Upgrade your plan or wait for the limit to reset.

subscription-status-disabled = 🚫 <b>Subscription Disabled</b>

    Contact support for more information.

subscription-status-none = 📭 <b>No Active Subscription</b>

    Choose a plan to start using VPN.

# ── Trial ────────────────────────────────────────────────────────────────
trial-offer = 🎁 <b>Free Trial!</b>

    Try CyberVPN free for { $days ->
        [one] { $days } day
       *[other] { $days } days
    }!

    📊 Traffic limit: { $traffic_gb } GB

trial-activated = ✅ <b>Trial Activated!</b>

    Duration: { $days ->
        [one] { $days } day
       *[other] { $days } days
    }
    Traffic: { $traffic_gb } GB

trial-already-used = ℹ️ You've already used your free trial.

trial-unavailable = ⚠️ Free trial is temporarily unavailable.

# ── Subscription and Plans ───────────────────────────────────────────────
plans-title = 💳 <b>Choose a Plan</b>

    Available plans:

plan-item = { $icon } <b>{ $name }</b>
    { $description }
    Starting from: <b>{ $price_from }</b>

duration-title = ⏰ <b>Select Duration</b>

    Plan: <b>{ $plan_name }</b>

duration-item = { $duration_days ->
        [one] { $duration_days } day
       *[other] { $duration_days } days
    } — <b>{ $price }</b>

payment-title = 💰 <b>Select Payment Method</b>

    Plan: <b>{ $plan_name }</b>
    Duration: { $duration }
    Amount: <b>{ $amount }</b>

payment-processing = ⏳ Processing payment...

payment-success = ✅ <b>Payment Successful!</b>

    Thank you for your purchase. Your subscription is now active.

payment-failed = ❌ <b>Payment Failed</b>

    Unfortunately, the payment didn't go through. Please try again or choose a different payment method.

payment-cancelled = 🔄 Payment cancelled.

# ── Referral System ──────────────────────────────────────────────────────
referral-title = 👥 <b>Referral Program</b>

    Invite friends and earn bonuses!

referral-info =
    <blockquote>
    👥 Invited: { $count }
    🎁 Days earned: { $bonus_days }
    🔗 Your link:
    <code>{ $link }</code>
    </blockquote>

referral-share = 📨 Share your link with friends:

    { $link }

referral-new-joined = 🎉 A new user registered via your link!

referral-reward = 🎁 You earned a bonus: { $days ->
        [one] { $days } day
       *[other] { $days } days
    } added to your subscription!

# ── Promo Codes ──────────────────────────────────────────────────────────
promo-enter = 🎟 Enter promo code:

promo-success = ✅ Promo code <b>{ $code }</b> activated successfully!
    { $description }

promo-invalid = ❌ Promo code is invalid or expired.

promo-already-used = ℹ️ You've already used this promo code.

# ── Support ──────────────────────────────────────────────────────────────
support-message = 🆘 <b>Support</b>

    For any questions contact: @{ $username }

# ── Devices / Config ─────────────────────────────────────────────────────
config-title = 📱 <b>Connection</b>

    Choose a format to get your configuration:

config-link = 🔗 <b>Connection link:</b>

    <code>{ $link }</code>

    Copy and paste into your VPN app.

config-qr = 📷 QR code is ready. Scan it in your VPN app.

config-instruction = 📖 <b>Connection Guide:</b>

    1️⃣ Download an app (V2rayNG / Hiddify / Streisand)
    2️⃣ Copy the link above
    3️⃣ Import the configuration
    4️⃣ Connect!

# ── Access / Conditions ──────────────────────────────────────────────────
access-rules = 📜 <b>Terms of Use</b>

    Please review the terms before using:
    { $rules_url }

access-channel-required = 📢 <b>Subscribe to Channel</b>

    You need to subscribe to our channel to continue.

access-channel-not-member = ❌ You haven't subscribed to the channel yet. Subscribe and click "Check".

access-maintenance = 🔧 <b>Maintenance</b>

    The bot is temporarily unavailable. Please try again later.

access-invite-only = 🔒 This bot is invite-only.

# ── Language ─────────────────────────────────────────────────────────────
language-select = 🌐 <b>Select language / Выберите язык:</b>

language-changed = ✅ Language changed to <b>English</b>.
