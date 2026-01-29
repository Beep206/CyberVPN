# CyberVPN Task Worker

Production-grade asynchronous task worker for the CyberVPN platform, built on TaskIQ with Redis Stream broker.

## Overview

The Task Worker is a microservice responsible for executing background tasks across the CyberVPN platform. It handles:

- **Notifications** - Telegram message delivery and broadcast notifications
- **Monitoring** - Server health checks, bandwidth tracking, queue depth monitoring
- **Subscriptions** - Expiration checks, auto-renewal, traffic resets
- **Analytics** - Daily/hourly stats aggregation, real-time metrics
- **Payments** - Payment verification, webhook retries
- **Cleanup** - Old records, expired tokens, audit logs, cache cleanup
- **Sync** - Node configurations, geolocations, user statistics
- **Reports** - Daily/weekly reports, anomaly detection
- **Bulk Operations** - User operations, exports, broadcasts

## Architecture

### Technology Stack

- **TaskIQ 0.12+** - Asynchronous distributed task queue
- **Redis Stream Broker** - Durable message broker with consumer groups
- **SQLAlchemy 2.0** - Async ORM for PostgreSQL
- **Structlog** - Structured JSON logging
- **Prometheus** - Metrics and monitoring
- **Python 3.13** - Modern async/await patterns

### Key Components

- **Broker** (`src/broker.py`) - TaskIQ broker with Redis backend, middleware chain, and lifecycle hooks
- **Scheduler** (`src/schedules/definitions.py`) - Cron-based task scheduling (30 scheduled tasks)
- **Middleware** (`src/middleware/`) - Logging, metrics, error handling, retry logic
- **Tasks** (`src/tasks/`) - 40+ background task implementations organized by category
- **Services** (`src/services/`) - Business logic for Telegram, payments, analytics, etc.
- **Models** (`src/models/`) - SQLAlchemy models for database entities

### Directory Structure

```
services/task-worker/
├── src/
│   ├── broker.py              # TaskIQ broker configuration
│   ├── config.py              # Pydantic settings
│   ├── logging_config.py      # Structured logging setup
│   ├── metrics.py             # Prometheus metrics definitions
│   ├── metrics_server.py      # HTTP server for /metrics endpoint
│   ├── types.py               # Shared type aliases
│   ├── py.typed               # PEP 561 type marker
│   ├── database/
│   │   ├── base.py            # SQLAlchemy Base
│   │   └── session.py         # Async session factory
│   ├── middleware/
│   │   ├── error_handler.py   # Error handling and alerting
│   │   ├── logging.py         # Request/response logging
│   │   ├── metrics.py         # Task timing and counters
│   │   └── retry.py           # Exponential backoff retry
│   ├── models/                # SQLAlchemy models
│   │   ├── notification_queue.py
│   │   ├── payment.py
│   │   ├── server.py
│   │   ├── subscription.py
│   │   └── user.py
│   ├── schedules/
│   │   └── definitions.py     # Cron schedule assignments
│   ├── services/              # Business logic layer
│   │   ├── analytics_service.py
│   │   ├── notification_service.py
│   │   ├── payment_service.py
│   │   ├── report_service.py
│   │   ├── subscription_service.py
│   │   └── telegram_client.py
│   ├── tasks/                 # Task implementations
│   │   ├── analytics/         # Stats aggregation (4 tasks)
│   │   ├── bulk/              # Bulk operations (4 tasks)
│   │   ├── cleanup/           # Data retention (7 tasks)
│   │   ├── monitoring/        # Health checks (6 tasks)
│   │   ├── notifications/     # Message delivery (3 tasks)
│   │   ├── payments/          # Payment processing (3 tasks)
│   │   ├── reports/           # Reporting (3 tasks)
│   │   ├── subscriptions/     # Subscription lifecycle (4 tasks)
│   │   └── sync/              # External sync (4 tasks)
│   └── utils/
│       └── constants.py       # Queue names, schedules, retry policies
├── tests/
│   ├── integration/           # Integration smoke tests
│   │   ├── test_broker.py     # Broker lifecycle tests
│   │   ├── test_schedules.py  # Schedule registration tests
│   │   └── test_e2e.py        # End-to-end smoke tests
│   └── unit/                  # Unit tests by category
│       ├── tasks/
│       ├── middleware/
│       └── services/
├── docs/                      # Additional documentation
├── examples/                  # Usage examples
├── Dockerfile                 # Multi-stage production build
├── pyproject.toml            # Hatchling build, dependencies, tools
├── healthcheck.py            # Docker healthcheck script
└── README.md                 # This file
```

## Setup

### Prerequisites

- Python 3.13+
- Docker and Docker Compose (for infrastructure)
- Redis 5.2+ or Valkey
- PostgreSQL 17+

### Local Development

1. **Install dependencies:**

```bash
cd services/task-worker
pip install -e ".[dev]"  # Install with dev dependencies
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start infrastructure (from repo root):**

```bash
cd infra
docker compose up -d  # PostgreSQL + Redis + Remnawave API
```

4. **Run database migrations:**

```bash
# Migrations are managed by the main Remnawave backend
# See backend documentation for migration commands
```

### Docker Deployment

**Build image:**

```bash
docker build -t cybervpn-task-worker:latest .
```

**Run worker:**

```bash
docker run -d \
  --name task-worker \
  --env-file .env \
  -p 9090:9090 \
  cybervpn-task-worker:latest
```

**Run scheduler:**

```bash
docker run -d \
  --name task-scheduler \
  --env-file .env \
  cybervpn-task-worker:latest \
  taskiq scheduler src.broker:scheduler
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | - | Yes |
| `REDIS_URL` | Redis connection string | - | Yes |
| `REMNAWAVE_URL` | Remnawave API base URL | - | Yes |
| `REMNAWAVE_API_TOKEN` | API authentication token | - | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for notifications | - | Yes |
| `ADMIN_TELEGRAM_IDS` | Comma-separated admin Telegram IDs | - | Yes |
| `CRYPTOBOT_TOKEN` | CryptoBot API token for payments | - | No |
| `WORKER_CONCURRENCY` | Number of worker processes | `2` | No |
| `RESULT_TTL_SECONDS` | Task result retention time | `3600` | No |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` | No |
| `ENVIRONMENT` | Environment name (dev/staging/prod) | `development` | No |
| `NOTIFICATION_MAX_RETRIES` | Max retry attempts for notifications | `5` | No |
| `NOTIFICATION_BATCH_SIZE` | Notifications per batch | `50` | No |
| `HEALTH_CHECK_INTERVAL_SECONDS` | Health check frequency | `120` | No |
| `CLEANUP_AUDIT_RETENTION_DAYS` | Audit log retention | `90` | No |
| `CLEANUP_WEBHOOK_RETENTION_DAYS` | Webhook log retention | `30` | No |
| `BULK_BATCH_SIZE` | Bulk operation batch size | `50` | No |
| `METRICS_PORT` | Prometheus metrics HTTP port | `9090` | No |

## Task Categories and Schedules

### Notifications (Queue: `notifications`)

- `process_notification_queue` - Every 30 seconds
- `send_notification` - On-demand via API
- `broadcast_notification` - On-demand via API

### Monitoring (Queue: `monitoring`)

- `check_server_health` - Every 2 minutes
- `check_external_services` - Every 2 minutes
- `collect_bandwidth_snapshot` - Every 5 minutes
- `monitor_queue_depth` - Every 1 minute
- `monitor_connection_pools` - On-demand
- `monitor_memory_usage` - On-demand

### Subscriptions (Queue: `subscriptions`)

- `check_expiring_subscriptions` - Every hour
- `disable_expired_users` - Every 15 minutes
- `auto_renew_subscriptions` - Every 30 minutes
- `reset_monthly_traffic` - 1st of month at 00:00 UTC

### Analytics (Queue: `analytics`)

- `aggregate_daily_stats` - Every hour at :05
- `aggregate_financial_stats` - Daily at 00:30 UTC
- `aggregate_hourly_bandwidth` - Every hour at :05
- `update_realtime_metrics` - Every 30 seconds

### Payments (Queue: `payments`)

- `verify_pending_payments` - Every 5 minutes
- `retry_failed_webhooks` - Every 30 minutes
- `process_payment_completion` - On-demand via webhook

### Cleanup (Queue: `cleanup`)

- `cleanup_old_records` - Daily at 2 AM UTC
- `cleanup_expired_tokens` - Daily at 2 AM UTC
- `cleanup_audit_logs` - Sunday at 3 AM UTC
- `cleanup_webhook_logs` - Daily at 2 AM UTC
- `cleanup_notifications` - Daily at 1 AM UTC
- `cleanup_cache` - Daily at 4 AM UTC
- `cleanup_export_files` - On-demand

### Sync (Queue: `sync`)

- `sync_node_configs` - Every 5 minutes
- `sync_server_geolocations` - Every 6 hours
- `sync_user_stats` - Every 10 minutes
- `sync_node_configurations` - Every 30 minutes

### Reports (Queue: `reports`)

- `send_daily_report` - Daily at 6 AM UTC (9 AM MSK)
- `generate_weekly_report` - Monday at 7 AM UTC
- `check_anomalies` - Every 5 minutes

### Bulk Operations (Queue: `bulk`)

- `process_bulk_operation` - On-demand via API
- `bulk_user_operation` - On-demand via API
- `export_users` - On-demand via API
- `broadcast_message` - On-demand via API

## Development Commands

### Run Worker

```bash
# Single worker (development)
taskiq worker src.broker:broker --fs-discover

# Multiple workers (production)
taskiq worker src.broker:broker --workers 4 --fs-discover
```

### Run Scheduler

```bash
taskiq scheduler src.broker:scheduler
```

### Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/ -m integration

# With coverage
pytest --cov=src --cov-report=html --cov-report=term

# Specific test file
pytest tests/unit/tasks/test_notifications.py -v
```

### Linting and Type Checking

```bash
# Ruff linting
ruff check src/

# Ruff formatting
ruff format src/

# Type checking with mypy
mypy src/ --ignore-missing-imports
```

### Manual Task Execution

```bash
# Python shell
python

# Execute task
from src.tasks.notifications.process_queue import process_notification_queue
await process_notification_queue.kiq()  # Enqueue task
result = await process_notification_queue()  # Direct call
```

## Monitoring

### Prometheus Metrics

Metrics are exposed on `http://localhost:9090/metrics`:

- `taskiq_task_duration_seconds` - Task execution time histogram
- `taskiq_task_success_total` - Successful task completions counter
- `taskiq_task_errors_total` - Task errors counter
- `taskiq_task_retries_total` - Task retry attempts counter
- `taskiq_worker_info` - Worker version and configuration info

### Grafana Dashboard

Pre-configured dashboards available in the main repository:

- Task execution rates and durations
- Error rates by task type
- Queue depth trends
- Worker resource utilization

### Logs

Structured JSON logs to stdout:

```json
{
  "event": "task_started",
  "task_name": "process_notification_queue",
  "task_id": "abc123",
  "timestamp": "2026-01-29T12:00:00Z",
  "level": "info"
}
```

View logs:

```bash
# Docker
docker logs task-worker -f

# Local development
taskiq worker src.broker:broker | jq
```

## Resilience Features

- **Exponential backoff retry** - Configurable per task category
- **Circuit breaker** - Automatic failure detection and recovery
- **Rate limiting** - Prevents external API overload
- **Graceful shutdown** - SIGTERM handling with in-flight task completion
- **Health checks** - Docker healthcheck via Redis PING
- **Result persistence** - Task results stored in Redis with TTL
- **Dead letter queue** - Failed tasks logged for manual review
- **Idempotency** - Tasks designed for safe retries

## Performance

- **Concurrency** - Configurable worker count (default: 2)
- **Batch processing** - Notifications, bulk operations processed in batches
- **Connection pooling** - SQLAlchemy and httpx connection reuse
- **Async I/O** - Non-blocking database and HTTP operations
- **Redis Streams** - Durable, ordered message delivery
- **Result caching** - Task results cached in Redis (1 hour TTL)

## Security

- **Environment variables** - Secrets loaded from `.env`, never committed
- **Token validation** - API tokens verified for external integrations
- **SQL injection protection** - SQLAlchemy parameterized queries
- **Rate limiting** - External API calls throttled
- **Audit logging** - All critical operations logged to database
- **Error sanitization** - Stack traces excluded from external logs

## Troubleshooting

### Worker won't start

```bash
# Check Redis connectivity
redis-cli -u $REDIS_URL ping

# Check database connectivity
psql $DATABASE_URL -c "SELECT 1"

# View worker logs
docker logs task-worker -f
```

### Tasks not executing

```bash
# Check scheduler is running
docker ps | grep scheduler

# Check schedule definitions loaded
python -c "import src.schedules.definitions; src.schedules.definitions.register_schedules()"

# Check Redis queue
redis-cli -u $REDIS_URL XLEN taskiq:stream
```

### High error rate

```bash
# Check Prometheus metrics
curl http://localhost:9090/metrics | grep taskiq_task_errors

# Check logs for errors
docker logs task-worker 2>&1 | grep ERROR | jq

# Review failed tasks in database
psql $DATABASE_URL -c "SELECT * FROM task_results WHERE status='failed' ORDER BY created_at DESC LIMIT 10"
```

## Contributing

1. Create feature branch from `main`
2. Write tests for new tasks (`tests/unit/tasks/`)
3. Follow existing code patterns and type hints
4. Run linting: `ruff check src/`
5. Run tests: `pytest`
6. Update this README if adding new task categories
7. Submit PR with clear description

## License

Proprietary - CyberVPN Platform

## Support

- Documentation: `/docs` directory
- API Reference: Remnawave backend `/api/docs`
- Issues: GitHub Issues
- Contact: System administrators
