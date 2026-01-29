# Resilience and Security Features

This document describes the resilience patterns and security hardening implemented in the task-worker microservice.

## Overview

The task-worker implements four key resilience and security patterns:

1. **Security Hardening** - Secret validation and masking
2. **Circuit Breaker** - Fault tolerance for external services
3. **Task Idempotency** - Prevent duplicate task execution
4. **Rate Limiting** - Token bucket algorithm for API throttling

## 1. Security Hardening (`src/security.py`)

### Features

- **Secret Masking**: Safely log configuration values without exposing credentials
- **Secret Validation**: Check that required secrets are properly configured
- **Startup Checks**: Run security validations before starting workers

### Usage

```python
from src.security import run_security_checks, log_masked_config, mask_secret

# Run at application startup
run_security_checks()  # Logs warnings for missing/weak secrets

# Log configuration with masked values
log_masked_config()  # DATABASE_URL, tokens, etc. are masked

# Mask individual secrets
masked = mask_secret("sk_live_1234567890abcdef", visible_chars=4)
# Returns: "***cdef"
```

### Validations

The security checks validate:

- `REMNAWAVE_API_TOKEN` is set and has minimum length
- `TELEGRAM_BOT_TOKEN` is set and has valid format
- `CRYPTOBOT_TOKEN` is set and has minimum length
- `DATABASE_URL` is not using default credentials
- Production environments have proper Redis authentication

## 2. Circuit Breaker (`src/services/circuit_breaker.py`)

### States

- **CLOSED**: Normal operation, all requests pass through
- **OPEN**: Service failing, reject requests immediately
- **HALF_OPEN**: Testing recovery, allow limited requests

### State Transitions

1. `CLOSED → OPEN`: After `failure_threshold` consecutive failures
2. `OPEN → HALF_OPEN`: After `recovery_timeout` seconds
3. `HALF_OPEN → CLOSED`: After `half_open_max_calls` successful requests
4. `HALF_OPEN → OPEN`: If any request fails during testing

### Usage

```python
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerError

# Create circuit breaker
breaker = CircuitBreaker(
    name="payment_api",
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60.0,    # Wait 60s before retry
    half_open_max_calls=2     # Need 2 successes to close
)

# Wrap external calls
try:
    result = await breaker.call(payment_api.charge, user_id=123, amount=50.0)
except CircuitBreakerError:
    # Circuit is open, use fallback
    logger.warning("payment_api_unavailable")
    result = queue_for_retry(user_id, amount)

# Check circuit state
if breaker.state == CircuitState.OPEN:
    logger.error("circuit_open", name=breaker.name)
```

### Configuration Guidelines

| Service Type | Failure Threshold | Recovery Timeout | Half-Open Calls |
|-------------|-------------------|------------------|-----------------|
| Payment API | 3-5 | 60-120s | 1-2 |
| Notification | 10-20 | 30-60s | 3-5 |
| Analytics | 20-30 | 15-30s | 5-10 |

## 3. Task Idempotency (`src/utils/idempotency.py`)

### Features

- **Redis-based Locking**: Distributed idempotency across workers
- **Deterministic Keys**: SHA-256 hash of task name and arguments
- **Configurable TTL**: Set idempotency window per task
- **Automatic Cleanup**: Failed tasks release lock for retry

### Usage

```python
from src.utils.idempotency import idempotent

@idempotent(ttl=3600)  # 1 hour idempotency window
async def process_payment(payment_id: int, amount: float):
    # Process payment
    return {"status": "success", "payment_id": payment_id}

# First call executes normally
result1 = await process_payment(123, 50.0)
# Returns: {"status": "success", "payment_id": 123, "skipped": False}

# Second call within TTL is skipped
result2 = await process_payment(123, 50.0)
# Returns: {"skipped": True, "reason": "idempotent_duplicate"}
```

### Advanced Usage

```python
from src.utils.idempotency import check_idempotency, clear_idempotency

# Pre-flight check without acquiring lock
already_processed = await check_idempotency("process_payment", 123, 50.0)
if not already_processed:
    await enqueue_task("process_payment", 123, 50.0)

# Manual lock clearing (use with caution)
cleared = await clear_idempotency("process_payment", 123, 50.0)
```

### TTL Guidelines

| Task Type | Recommended TTL | Rationale |
|-----------|----------------|-----------|
| Payment Processing | 2-4 hours | Prevent duplicate charges |
| Notification Send | 10-30 minutes | Avoid spam while allowing retries |
| Data Export | 1 hour | Long-running but cacheable |
| Analytics | 5 minutes | Fast updates, short dedup window |

## 4. Rate Limiting (`src/utils/rate_limiter.py`)

### Token Bucket Algorithm

The rate limiter implements a token bucket with:
- **Rate**: Tokens added per second (requests/second)
- **Capacity**: Maximum burst size
- **Async-safe**: Uses asyncio.Lock for concurrency

### Usage

```python
from src.utils.rate_limiter import AsyncTokenBucket

# Create rate limiter: 10 req/s, burst up to 20
limiter = AsyncTokenBucket(rate=10.0, capacity=20)

# Blocking acquire (waits for tokens)
await limiter.acquire()  # Acquire 1 token
await api_call()

# Acquire multiple tokens
await limiter.acquire(tokens=5)
await batch_operation()

# Non-blocking acquire
if await limiter.try_acquire():
    await api_call()
else:
    logger.info("rate_limit_reached")

# Acquire with timeout
acquired = await limiter.acquire(tokens=1, timeout=2.0)
if not acquired:
    logger.warning("timeout_waiting_for_tokens")
```

### Integration with Remnawave Client

```python
from src.services.remnawave_client import RemnawaveClient
from src.utils.rate_limiter import AsyncTokenBucket

# Create rate limiter
rate_limiter = AsyncTokenBucket(rate=10.0, capacity=20)

# Pass to client
client = RemnawaveClient(rate_limiter=rate_limiter)

# All API calls are now rate-limited
users = await client.get_users()
```

### Rate Configuration Guidelines

| API Type | Rate (req/s) | Capacity | Rationale |
|----------|--------------|----------|-----------|
| Remnawave API | 10-20 | 30-40 | Protect backend from overload |
| Payment Gateway | 5-10 | 10-15 | Respect API limits |
| Telegram Bot | 30 | 30 | Official limit: 30 msg/sec |
| Analytics Export | 2-5 | 10 | Heavy queries, limit load |

### Dynamic Rate Adjustment

```python
# Reduce rate during high load
await limiter.set_rate(5.0)

# Reset bucket to full capacity
await limiter.reset()

# Check available tokens
available = limiter.available_tokens
```

## Combined Usage Example

```python
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerError
from src.utils.idempotency import idempotent
from src.utils.rate_limiter import AsyncTokenBucket

# Setup resilience stack
breaker = CircuitBreaker("payment_api", failure_threshold=5, recovery_timeout=60.0)
rate_limiter = AsyncTokenBucket(rate=10.0, capacity=20)

@idempotent(ttl=7200)  # 2 hour idempotency
async def process_payment_resilient(payment_id: int, amount: float):
    # 1. Rate limiting
    await rate_limiter.acquire()

    # 2. Circuit breaker protection
    async def payment_api_call():
        return await payment_api.charge(payment_id, amount)

    try:
        result = await breaker.call(payment_api_call)
        return {"status": "success", "payment_id": payment_id}

    except CircuitBreakerError:
        # Queue for retry when service recovers
        await enqueue_retry(payment_id, amount)
        return {"status": "queued"}

# First call: rate-limited, idempotent, circuit-protected
result = await process_payment_resilient(123, 50.0)
```

## Testing

Run the test suite:

```bash
# Unit tests for resilience features
pytest tests/test_resilience.py -v

# Integration tests
pytest tests/integration/ -v
```

## Examples

See `examples/resilience_usage.py` for comprehensive usage examples:

```bash
cd services/task-worker
python examples/resilience_usage.py
```

## Monitoring

All resilience features log structured events for monitoring:

### Security Checks
- `security_checks_passed` - All validations passed
- `security_check_warning` - Missing or weak configuration

### Circuit Breaker
- `circuit_breaker_opened` - Circuit opened due to failures
- `circuit_breaker_half_open` - Testing recovery
- `circuit_breaker_closed` - Circuit recovered
- `circuit_breaker_rejected_call` - Call rejected while open

### Idempotency
- `task_skipped_idempotent` - Duplicate task skipped
- `idempotency_lock_acquired` - Lock acquired successfully
- `idempotency_lock_released_on_error` - Lock released after error

### Rate Limiting
- `tokens_acquired_immediate` - Tokens available immediately
- `tokens_waiting` - Waiting for token refill
- `tokens_acquired_after_wait` - Acquired after waiting
- `token_acquisition_timeout` - Timeout waiting for tokens

## Best Practices

1. **Security Checks**: Always run `run_security_checks()` at startup
2. **Circuit Breakers**: Use for all external service calls
3. **Idempotency**: Apply to all critical operations (payments, notifications)
4. **Rate Limiting**: Configure based on API provider limits
5. **Monitoring**: Track circuit breaker states and idempotency rates
6. **Testing**: Test failure scenarios and recovery paths
7. **Fallbacks**: Always have fallback logic for open circuits

## Performance Impact

| Feature | Overhead | Notes |
|---------|----------|-------|
| Security Checks | ~5ms | One-time at startup |
| Circuit Breaker | ~0.1ms | Lock acquisition per call |
| Idempotency | ~1-2ms | Redis SET NX operation |
| Rate Limiting | ~0.1ms | Lock + arithmetic |

Total overhead per critical operation: **~2-3ms**

This is negligible compared to typical external API latency (50-500ms).

## Troubleshooting

### Circuit Breaker Stuck Open
```python
# Check circuit state
logger.info("circuit_state", state=breaker.state, failures=breaker.failure_count)

# Manual reset (use with caution)
breaker.reset()
```

### Idempotency Lock Not Releasing
```python
# Check if lock exists
exists = await check_idempotency("task_name", arg1, arg2)

# Manual clear (use with caution)
await clear_idempotency("task_name", arg1, arg2)
```

### Rate Limiter Too Restrictive
```python
# Check available tokens
available = limiter.available_tokens
logger.info("available_tokens", count=available)

# Increase rate temporarily
await limiter.set_rate(20.0)  # Double the rate
```

## References

- [Circuit Breaker Pattern - Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Token Bucket Algorithm - Wikipedia](https://en.wikipedia.org/wiki/Token_bucket)
- [Idempotency - REST API Design](https://restfulapi.net/idempotent-rest-apis/)
