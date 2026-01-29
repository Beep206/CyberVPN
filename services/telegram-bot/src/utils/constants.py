"""Constants and configuration values for the telegram bot."""

from __future__ import annotations

# Redis key prefixes
REDIS_KEY_PREFIX_USER = "tg:user"
REDIS_KEY_PREFIX_SESSION = "tg:session"
REDIS_KEY_PREFIX_SUBSCRIPTION = "tg:sub"
REDIS_KEY_PREFIX_CACHE = "tg:cache"
REDIS_KEY_PREFIX_RATE_LIMIT = "tg:rate"

# Cache TTLs (in seconds)
CACHE_TTL_SHORT = 60  # 1 minute
CACHE_TTL_DEFAULT = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour

# Rate limits
RATE_LIMIT_MESSAGES = 30  # messages per minute per user
RATE_LIMIT_COMMANDS = 10  # commands per minute per user

# Message constraints
MAX_MESSAGE_LENGTH = 4096  # Telegram's max message length

# Pagination defaults
ITEMS_PER_PAGE = 5
MAX_PAGES = 100

# Session timeouts
SESSION_TIMEOUT = 1800  # 30 minutes

# Deep link salt (should be in env in production)
DEEP_LINK_SALT = "cybervpn_secure_salt_change_in_production"

# QR code settings
QR_CODE_VERSION = 1  # Auto-adjust
QR_CODE_ERROR_CORRECTION = "H"  # High error correction
QR_CODE_BOX_SIZE = 10
QR_CODE_BORDER = 4

# Payment settings
MIN_PAYMENT_AMOUNT = 1.0  # USD
MAX_PAYMENT_AMOUNT = 10000.0  # USD

# Subscription defaults
DEFAULT_TRIAL_DAYS = 7
DEFAULT_BANDWIDTH_LIMIT_GB = 100

# Admin settings
BROADCAST_BATCH_SIZE = 30  # Messages to send before delay
BROADCAST_BATCH_DELAY = 1.0  # Seconds between batches
