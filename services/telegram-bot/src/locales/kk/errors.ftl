# CyberVPN Telegram Bot — Errors (en)

# ── General ───────────────────────────────────────────────────────────────
error-generic = ⚠️ Something went wrong. Please try again shortly.
error-registration-failed = ❌ Unable to register your account. Please try later or contact support.
error-no-plans = ⚠️ No plans are available right now. Please try later.
error-config-not-ready = ⏳ Your configuration is not ready yet. Try again in a couple of minutes.
error-trial-activation-failed = ❌ Couldn't activate the free trial. Please try again later.
error-withdrawal-failed = ❌ Unable to withdraw bonuses. Try again later or contact support.

# ── API ──────────────────────────────────────────────────────────────────
error-api-unavailable = ⚠️ Service temporarily unavailable. Please try again later.

error-api-timeout = ⏰ Request timed out. Please try again.

error-api-unknown = ❌ An unexpected error occurred. Please try later or contact support.

error-api-not-found = ❌ Requested resource not found.

error-api-forbidden = 🚫 Access denied.

error-api-conflict = ⚠️ Data conflict. Please try again.

# ── Payments ─────────────────────────────────────────────────────────────
error-payment-gateway = ❌ Payment gateway error. Please try a different payment method.

error-payment-amount = ❌ Invalid payment amount.

error-payment-expired = ⏰ Payment expired. Please create a new payment.

error-payment-cancelled = 🔄 Payment was cancelled.

error-payment-duplicate = ℹ️ This payment has already been processed.

error-payment-creation-failed = ❌ Couldn't create a payment. Please try a different method.
error-payment-confirmation-failed = ⚠️ Payment succeeded but confirmation didn't arrive. Please check status again.

# ── User ─────────────────────────────────────────────────────────────────
error-user-not-registered = ❌ You are not registered. Press /start to register.

error-user-blocked = 🚫 Your account has been blocked. Contact support.

error-user-no-subscription = ❌ You don't have an active subscription.

# ── Rate limiting ────────────────────────────────────────────────────────
error-rate-limit = ⏳ Too many requests. Please wait { $seconds ->
        [one] { $seconds } second
       *[other] { $seconds } seconds
    }.

# ── Access ───────────────────────────────────────────────────────────────
error-access-denied = 🚫 Access denied. You don't have permission for this action.

error-admin-only = 🔒 This command is available to administrators only.

# ── Validation ───────────────────────────────────────────────────────────
error-invalid-input = ❌ Invalid input. Please try again.

error-invalid-promo = ❌ Invalid promo code.

error-session-expired = ⏰ Session expired. Please start over.
