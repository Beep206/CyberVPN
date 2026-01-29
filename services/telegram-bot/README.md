# CyberVPN Telegram Bot

Production-ready Telegram bot service for CyberVPN subscription management, built with aiogram 3 and Clean Architecture principles.

## Overview

The CyberVPN Telegram Bot provides a complete VPN subscription management interface for users through Telegram. It handles user registration, subscription purchases, payment processing across multiple gateways, config delivery, referral system, and admin dashboard.

### Key Features

- User registration and authentication with CyberVPN Backend API
- Multi-payment gateway support (Telegram Stars, CryptoBot, YooKassa)
- Subscription plan selection and management
- WireGuard config delivery with QR codes
- Referral system with bonus rewards
- Trial subscriptions (2 days, 2GB traffic)
- Multi-language support (i18n with Fluent) - Russian and English
- Admin panel for user management, broadcasts, and statistics
- Prometheus metrics for monitoring
- Redis-backed FSM (Finite State Machine) for conversation flows
- Structured logging with `structlog`
- Circuit breaker pattern for API resilience

## Architecture

The bot follows **Clean Architecture** with clear separation of concerns:

```
src/
├── handlers/          # Message and callback query handlers
│   ├── start.py       # /start command, user registration
│   ├── menu.py        # Main menu navigation
│   ├── subscription.py # Subscription purchase flow
│   ├── payment.py     # Payment processing
│   ├── config.py      # Config delivery, QR generation
│   ├── referral.py    # Referral link generation
│   ├── admin/         # Admin panel handlers
│   │   ├── stats.py   # Statistics dashboard
│   │   ├── broadcast.py # Broadcast messages
│   │   └── users.py   # User management
│
├── services/          # Business logic and external integrations
│   └── api_client.py  # CyberVPN Backend API client (httpx + tenacity)
│
├── middlewares/       # aiogram middlewares
│   ├── i18n.py        # Fluent i18n middleware
│   ├── auth.py        # User authentication
│   └── logging.py     # Request/response logging
│
├── models/            # Pydantic DTOs
│   ├── user.py        # UserDTO, UserStatus
│   ├── subscription.py # SubscriptionPlan, PlanDuration
│   └── payment.py     # PaymentDTO, PaymentMethod
│
├── states/            # FSM state groups
│   ├── subscription.py # SubscriptionStates (selecting_plan, selecting_duration, ...)
│   └── admin.py       # BroadcastStates, UserManagementStates
│
├── keyboards/         # Inline keyboard builders
│   ├── menu.py        # Main menu keyboard
│   ├── subscription.py # Plan and duration selection
│   └── payment.py     # Payment gateway selection
│
├── filters/           # aiogram custom filters
│   └── admin.py       # IsAdmin filter (checks ADMIN_IDS)
│
├── locales/           # Fluent .ftl translation files
│   ├── ru/            # Russian translations
│   │   └── main.ftl
│   └── en/            # English translations
│       └── main.ftl
│
├── config.py          # pydantic-settings configuration
├── main.py            # Application entrypoint
└── utils/             # Utility functions (QR generation, etc.)
```

### Request Flow

1. **User sends message/callback** → aiogram Dispatcher
2. **Middleware chain** → i18n, auth, logging
3. **Handler** → processes user input, updates FSM state
4. **Service layer** → calls Backend API via `api_client.py`
5. **Response** → handler sends message/keyboard to user

## Tech Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| **aiogram** | 3.24+ | Telegram Bot framework |
| **pydantic-settings** | 2.12+ | Type-safe configuration |
| **httpx** | 0.28.1+ | Async HTTP client |
| **redis** | 7.1+ | FSM storage and caching |
| **structlog** | 25.5+ | Structured logging |
| **fluent.runtime** | 0.4+ | i18n (Fluent localization) |
| **prometheus-client** | 0.24.1+ | Metrics export |
| **tenacity** | 9.0+ | Retry logic with exponential backoff |
| **qrcode** | 8.0+ | QR code generation for configs |
| **orjson** | 3.10+ | Fast JSON serialization |

## Prerequisites

- **Python 3.13+**
- **Redis 7.1+** (or Valkey)
- **CyberVPN Backend API** (running and accessible)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))

## Quick Start

### 1. Clone and Install

```bash
cd services/telegram-bot
pip install -e ".[dev]"
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**Required variables:**

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_MODE=polling
BACKEND_API_URL=http://localhost:8000/api/v1
BACKEND_API_KEY=your-backend-api-key
REDIS_URL=redis://localhost:6379
ADMIN_IDS=123456789,987654321
```

### 3. Run Locally

```bash
# Start Redis (if not running)
redis-server

# Run bot in polling mode
python -m src.main
```

Or using the installed script:

```bash
cybervpn-bot
```

## Configuration

All configuration is managed via environment variables (see `.env.example` for full list).

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | *required* | Telegram bot token from BotFather |
| `BOT_MODE` | `polling` | Bot mode: `polling` or `webhook` |
| `ENVIRONMENT` | `development` | Environment: `development`, `staging`, `production` |

### Backend API

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_API_URL` | *required* | CyberVPN Backend API base URL |
| `BACKEND_API_KEY` | *required* | API key for authentication |
| `BACKEND_TIMEOUT` | `30` | Request timeout in seconds |
| `BACKEND_MAX_RETRIES` | `3` | Max retry attempts |
| `BACKEND_RETRY_BACKOFF` | `0.5` | Exponential backoff factor |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `REDIS_DB` | `1` | Redis database number |
| `REDIS_PASSWORD` | *(empty)* | Redis password (if required) |
| `REDIS_KEY_PREFIX` | `cybervpn:bot:` | Key prefix for namespacing |
| `REDIS_TTL_SECONDS` | `3600` | Default TTL for cached keys |

### Payment Gateways

**CryptoBot:**

```env
CRYPTOBOT_ENABLED=true
CRYPTOBOT_TOKEN=your-cryptobot-token
CRYPTOBOT_NETWORK=mainnet
```

**YooKassa:**

```env
YOOKASSA_ENABLED=false
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
YOOKASSA_TEST_MODE=false
```

**Telegram Stars:**

```env
TELEGRAM_STARS_ENABLED=true
```

### Trial and Referral

```env
TRIAL_ENABLED=true
TRIAL_DAYS=2
TRIAL_TRAFFIC_GB=2

REFERRAL_ENABLED=true
REFERRAL_BONUS_DAYS=3
REFERRAL_MAX_REFERRALS=100
```

### Admin

```env
ADMIN_IDS=123456789,987654321  # Comma-separated Telegram user IDs
SUPPORT_USERNAME=CyberVPNSupport
```

### i18n

```env
DEFAULT_LANGUAGE=ru
AVAILABLE_LANGUAGES=ru,en
```

### Monitoring

```env
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics
```

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m e2e          # End-to-end tests

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Lint with ruff
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type checking with mypy
mypy src/
```

### Project Structure Conventions

- **Handlers**: One file per feature (subscription, payment, config, etc.)
- **Models**: Pydantic DTOs for type safety
- **Services**: Business logic and external API calls
- **States**: FSM state groups for conversation flows
- **Keyboards**: Reusable keyboard builders
- **Locales**: Fluent .ftl files for i18n (one per language)

## Docker

### Build Image

```bash
docker build -t cybervpn-bot:latest .
```

### Run Container

```bash
docker run -d \
  --name cybervpn-bot \
  --env-file .env \
  cybervpn-bot:latest
```

### Docker Compose

The bot is included in the project's Docker Compose stack:

```bash
# From repo root
cd infra

# Start all services including bot
docker compose --profile bot up -d

# View bot logs
docker compose logs -f cybervpn-bot

# Stop services
docker compose --profile bot down
```

**Services started:**
- `cybervpn-bot` - Telegram bot
- `remnawave` - Backend API (port 3000)
- `postgres` - Database (port 6767)
- `valkey` - Redis-compatible cache (port 6379)

**Optional profiles:**
- `--profile monitoring` - Prometheus + Grafana
- `--profile bot` - Telegram bot service

## Available Commands

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start bot, register user |
| `/menu` | Show main menu |
| `/config` | Get VPN configuration |
| `/support` | Contact support |

### Admin Commands

Admin users (configured in `ADMIN_IDS`) have access to:

| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |
| **Statistics** | View user, payment, subscription stats |
| **Broadcast** | Send messages to all/active/trial users |
| **User Management** | Search users, edit discounts, ban/unban |
| **Logs** | View recent bot logs |

## i18n (Internationalization)

The bot uses **Fluent** for localization with support for:

- **Russian** (`ru`) - default
- **English** (`en`)

### Translation Files

Fluent `.ftl` files are located in `src/locales/{locale}/main.ftl`:

```ftl
# src/locales/ru/main.ftl
welcome = Добро пожаловать в CyberVPN!
select-plan = Выберите план подписки:

# src/locales/en/main.ftl
welcome = Welcome to CyberVPN!
select-plan = Select subscription plan:
```

### Adding a New Language

1. Create directory: `src/locales/{locale}/`
2. Add `main.ftl` file with translations
3. Update `AVAILABLE_LANGUAGES` in `.env`:
   ```env
   AVAILABLE_LANGUAGES=ru,en,de
   ```

## Monitoring

### Prometheus Metrics

The bot exposes metrics at `http://localhost:9090/metrics` (if `PROMETHEUS_ENABLED=true`):

**Metrics:**
- `bot_updates_total` - Total updates received
- `bot_commands_total{command}` - Commands processed
- `bot_api_requests_total{method,status}` - Backend API calls
- `bot_payments_total{gateway,status}` - Payment transactions
- `bot_errors_total{type}` - Error counts

### Grafana Dashboards

Import the dashboard from `infra/grafana/dashboards/telegram-bot.json` to visualize:
- Active users
- Payment success rates
- API latency
- Error rates

### Logs

Structured JSON logs are written to stdout:

```json
{
  "event": "user_registered",
  "telegram_id": 123456789,
  "username": "john_doe",
  "language": "ru",
  "timestamp": "2026-01-29T12:34:56.789Z",
  "level": "info"
}
```

Configure log level via `LOG_LEVEL` env var.

## API Dependencies

The bot communicates with CyberVPN Backend API for:

### User Management
- `POST /users` - Register new user
- `GET /users/{telegram_id}` - Get user details
- `PATCH /users/{telegram_id}` - Update user

### Subscriptions
- `GET /plans` - List available plans
- `POST /subscriptions` - Create subscription
- `GET /subscriptions/{id}` - Get subscription details
- `GET /subscriptions/{id}/config` - Download VPN config

### Payments
- `POST /payments` - Create payment
- `GET /payments/{id}` - Get payment status
- `POST /payments/{id}/verify` - Verify payment completion

### Webhooks
- `POST /webhooks/cryptobot` - CryptoBot payment callback
- `POST /webhooks/yookassa` - YooKassa payment callback

### Admin
- `GET /admin/stats/{type}` - Statistics (users, payments, etc.)
- `POST /admin/broadcasts` - Create broadcast
- `GET /admin/users/search` - Search users
- `PATCH /admin/users/{id}` - Update user (admin action)

## Troubleshooting

### Bot doesn't start

1. Check `.env` file exists and has correct values
2. Verify `BOT_TOKEN` is valid (test with `curl https://api.telegram.org/bot<TOKEN>/getMe`)
3. Check Redis is running: `redis-cli ping` (should return `PONG`)
4. Check Backend API is accessible: `curl <BACKEND_API_URL>/health`

### Payment issues

1. Verify payment gateway credentials in `.env`
2. Check webhook URLs are configured in gateway dashboards
3. Review logs for payment errors: `docker compose logs cybervpn-bot | grep payment`

### i18n not working

1. Ensure locale files exist in `src/locales/{locale}/main.ftl`
2. Check `AVAILABLE_LANGUAGES` includes the locale
3. Verify user's Telegram language is in available languages

## Contributing

1. Follow existing code structure (Clean Architecture)
2. Add tests for new features (unit + integration)
3. Run `ruff check` and `mypy` before committing
4. Update this README if adding new features

## License

MIT

---

**CyberVPN Telegram Bot** — Built with aiogram 3.24, Python 3.13, and Clean Architecture principles.
