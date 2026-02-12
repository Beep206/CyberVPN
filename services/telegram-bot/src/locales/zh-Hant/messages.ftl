# CyberVPN Telegram Bot — Messages (en)

# ── Welcome and Onboarding ───────────────────────────────────────────────
welcome-message = 👋 <b>Welcome to CyberVPN, { $name }!</b>

    🔐 Fast, private access to the internet.

    <b>Quick start:</b>
    1) Choose a plan or start a free trial
    2) Get your config (link/QR)
    3) Connect in your VPN app

    Pick an option below.

welcome = 👋 <b>Welcome to CyberVPN, { $name }!</b>

    🔐 Fast, private access to the internet.

    <b>Quick start:</b>
    1) Choose a plan or start a free trial
    2) Get your config (link/QR)
    3) Connect in your VPN app

    Pick an option below.

welcome-back = 🔄 <b>Welcome back, { $name }!</b>

    What would you like to do next?

welcome-referral-bonus = 🎁 You'll get bonus days after your first purchase with a referral.

promo-activated = ✅ Promo code <b>{ $code }</b> applied.

# ── Menu ─────────────────────────────────────────────────────────────────
menu-main-title = 🏠 <b>Main menu</b>

# ── Profile ──────────────────────────────────────────────────────────────
profile-title = 👤 <b>Your Profile</b>

profile-info =
    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Username: { $username }
    🌐 Language: { $language }
    📅 Registered: { $registered }
    </blockquote>

profile-details =
    <blockquote>
    🆔 ID: <code>{ $telegram_id }</code>
    👤 Name: { $first_name }
    🧾 Username: { $username }
    🌐 Language: { $language }
    📅 Registered: { $registered }
    </blockquote>

# ── Subscription Status ──────────────────────────────────────────────────
subscription-active = ✅ <b>Subscription active</b>

    📋 Plan: <b>{ $plan }</b>
    ⏳ Expires: { $expires }

    Tap “Get config” to connect or extend your plan.

subscription-none = 📭 <b>No active subscription</b>

    Choose a plan or start a free trial to begin using VPN.

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

    Duration: { $duration ->
        [one] { $duration } day
       *[other] { $duration } days
    }
    Expires: { $expires }

trial-eligible = ✅ You can activate a free trial.

trial-not-eligible-used = ℹ️ Your free trial has already been used.
trial-not-eligible-active = ℹ️ You already have an active subscription.
trial-not-eligible-unavailable = ⚠️ Free trial is currently unavailable.
trial-not-eligible-unknown = ⚠️ Trial can't be activated right now. Please try later.

trial-already-used = ℹ️ You've already used your free trial.

trial-unavailable = ⚠️ Free trial is temporarily unavailable.

# ── Subscription and Plans ───────────────────────────────────────────────
subscription-select-plan = 💳 <b>Choose a plan</b>

    You can change it later.

subscription-select-duration = ⏰ <b>Select duration</b>

subscription-select-payment = 💰 <b>Select payment method</b>

    Plan: <b>{ $plan }</b>
    Duration: { $duration ->
        [one] { $duration } day
       *[other] { $duration } days
    }
    Amount: <b>{ $price }</b>

    We'll send your config after payment.

subscription-cancelled = ✅ Purchase cancelled. Back to menu.

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

    Your subscription is active. Get your config to connect.

payment-failed = ❌ <b>Payment Failed</b>

    The payment didn't go through. Try again or choose another method.

payment-cancelled = 🔄 Payment cancelled.

subscription-payment = CyberVPN subscription
subscription-payment-title = CyberVPN subscription
subscription-payment-description = VPN access and connection setup

payment-open-link = Open payment link
payment-check-status = Check payment
payment-external-instructions = 💳 <b>Payment</b>

    1) Tap “Open payment”
    2) Complete the payment
    3) Return and tap “Check payment”

    If the payment page was closed, open it again.

payment-pending = ⏳ Payment is processing. Check again in a minute.
payment-status-unknown = ℹ️ Status isn't updated yet. Try again shortly.

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

referral-share = 📨 Share your link and earn bonus days:

    { $link }

referral-share-button = Share link

referral-new-joined = 🎉 A new user registered via your link!

referral-reward = 🎁 You earned a bonus: { $days ->
        [one] { $days } day
       *[other] { $days } days
    } added to your subscription!

referral-withdraw-insufficient = ⚠️ You need at least { $min } bonus points to withdraw.

referral-withdraw-success = ✅ Withdrawal request created.

    Amount: { $amount }
    Status: { $status }

# ── Promo Codes ──────────────────────────────────────────────────────────
promo-enter = 🎟 Enter promo code:

promo-success = ✅ Promo code <b>{ $code }</b> activated successfully!
    { $description }

promo-invalid = ❌ Promo code is invalid or expired.

promo-already-used = ℹ️ You've already used this promo code.

promocode-enter-prompt = 🎟 Enter promo code (e.g., CYBER10):
promocode-activated = ✅ Promo code <b>{ $code }</b> activated! Discount: <b>{ $discount }</b>
promocode-not-found = ❌ Promo code not found.
promocode-expired = ❌ Promo code has expired.
promocode-already-used = ℹ️ You've already used this promo code.
promocode-usage-limit = ⚠️ Promo code usage limit reached.
promocode-cancelled = ✅ Promo code entry cancelled.

# ── Support ──────────────────────────────────────────────────────────────
support-message = 🆘 <b>Support</b>

    Contact us: { $contact }

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

config-delivery-prompt = ✅ <b>All set!</b> How do you want to receive your config?

config-link-message = 🔗 <b>Connection link</b>

    <code>{ $url }</code>

    Copy the link and import it in your VPN app.

config-qr-caption = 📷 Scan the QR code in your VPN app.

config-instructions = 📖 <b>Connection guide</b>

    1) Install an app (V2rayNG / Hiddify / Streisand)
    2) Copy the connection link
    3) Import the configuration
    4) Connect

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

language-select-prompt = 🌐 <b>Select language:</b>

language-changed = ✅ Language changed to { $language ->
        [ru] <b>Русский</b>
        [en] <b>English</b>
        [hi] <b>हिन्दी</b>
        [id] <b>Bahasa Indonesia</b>
        [zh] <b>中文</b>
        [zh-Hant] <b>繁體中文</b>
        [ar] <b>العربية</b>
        [fa] <b>فارسی</b>
        [tr] <b>Türkçe</b>
        [vi] <b>Tiếng Việt</b>
        [ur] <b>اردو</b>
        [th] <b>ไทย</b>
        [bn] <b>বাংলা</b>
        [ms] <b>Bahasa Melayu</b>
        [es] <b>Español</b>
        [kk] <b>Қазақша</b>
        [be] <b>Беларуская</b>
        [my] <b>မြန်မာ</b>
        [uz] <b>Oʻzbekcha</b>
        [ha] <b>Hausa</b>
        [yo] <b>Yorùbá</b>
        [ku] <b>Kurdî</b>
        [am] <b>አማርኛ</b>
        [fr] <b>Français</b>
        [tk] <b>Türkmençe</b>
        [ja] <b>日本語</b>
        [ko] <b>한국어</b>
        [he] <b>עברית</b>
        [de] <b>Deutsch</b>
        [pt] <b>Português</b>
        [it] <b>Italiano</b>
        [nl] <b>Nederlands</b>
        [pl] <b>Polski</b>
        [fil] <b>Filipino</b>
        [uk] <b>Українська</b>
        [cs] <b>Čeština</b>
        [ro] <b>Română</b>
        [hu] <b>Magyar</b>
        [sv] <b>Svenska</b>
       *[other] <b>{ $language }</b>
    }.

# ── Subscription History ─────────────────────────────────────────────────
subscriptions-title = 📦 <b>Your subscriptions</b>
subscriptions-none = 📭 No subscriptions yet.
status = Status
expires = Expires
currency = USD
