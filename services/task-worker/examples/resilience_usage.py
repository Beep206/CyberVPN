"""Examples demonstrating resilience and security features.

Shows how to use:
- Security audit and secret masking
- Circuit breaker for external service calls
- Task idempotency with Redis
- Rate limiting with token bucket
"""

import asyncio

import structlog

from src.config import get_settings
from src.security import log_masked_config, run_security_checks
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerError
from src.services.remnawave_client import RemnawaveClient
from src.utils.idempotency import idempotent
from src.utils.rate_limiter import AsyncTokenBucket

logger = structlog.get_logger(__name__)


# Example 1: Security checks at startup
async def startup_security_example():
    """Run security checks at application startup."""
    logger.info("=== Security Checks Example ===")

    # Run security validation
    run_security_checks()

    # Log configuration with masked secrets
    log_masked_config()


# Example 2: Circuit breaker for external API
async def circuit_breaker_example():
    """Use circuit breaker to protect external API calls."""
    logger.info("=== Circuit Breaker Example ===")

    # Create circuit breaker for payment service
    payment_breaker = CircuitBreaker(
        name="payment_api",
        failure_threshold=5,  # Open after 5 failures
        recovery_timeout=30.0,  # Wait 30s before retry
        half_open_max_calls=2  # Need 2 successes to close
    )

    async def call_payment_api(amount: float):
        """Simulated payment API call."""
        # In production, this would be actual API call
        if amount < 0:
            raise ValueError("Invalid amount")
        return {"status": "success", "amount": amount}

    try:
        # Make call through circuit breaker
        result = await payment_breaker.call(call_payment_api, 50.0)
        logger.info("payment_processed", result=result)

    except CircuitBreakerError as e:
        logger.error("payment_circuit_open", error=str(e))
        # Handle fallback: queue for retry, use cached data, etc.

    # Check circuit state
    logger.info("circuit_state", state=payment_breaker.state.value)


# Example 3: Idempotent task processing
@idempotent(ttl=3600)  # 1 hour idempotency window
async def process_payment(payment_id: int, amount: float, currency: str = "USD"):
    """Process payment with idempotency guarantee.

    If called multiple times with same parameters within TTL,
    only the first execution will run.
    """
    logger.info("processing_payment", payment_id=payment_id, amount=amount, currency=currency)

    # Simulate payment processing
    await asyncio.sleep(0.1)

    return {
        "payment_id": payment_id,
        "amount": amount,
        "currency": currency,
        "status": "completed"
    }


async def idempotency_example():
    """Demonstrate idempotent task execution."""
    logger.info("=== Idempotency Example ===")

    # First call executes normally
    result1 = await process_payment(payment_id=12345, amount=99.99, currency="USD")
    logger.info("first_call", result=result1, skipped=result1.get("skipped", False))

    # Second call with same parameters is skipped
    result2 = await process_payment(payment_id=12345, amount=99.99, currency="USD")
    logger.info("second_call", result=result2, skipped=result2.get("skipped", False))

    # Call with different parameters executes normally
    result3 = await process_payment(payment_id=12345, amount=199.99, currency="USD")
    logger.info("different_params", result=result3, skipped=result3.get("skipped", False))


# Example 4: Rate limiting with token bucket
async def rate_limiting_example():
    """Use token bucket rate limiter for API calls."""
    logger.info("=== Rate Limiting Example ===")

    # Create rate limiter: 10 requests/second, burst up to 20
    rate_limiter = AsyncTokenBucket(rate=10.0, capacity=20)

    # Create Remnawave client with rate limiter
    client = RemnawaveClient(rate_limiter=rate_limiter)

    try:
        # Make rate-limited API calls
        for i in range(5):
            try:
                # Rate limiter ensures we don't exceed 10 req/s
                health = await client.health_check()
                logger.info("health_check", attempt=i+1, healthy=health)
            except Exception as e:
                logger.error("health_check_failed", attempt=i+1, error=str(e))

    finally:
        await client._client.aclose()


# Example 5: Combined usage - resilient payment processing
async def resilient_payment_processing():
    """Combine all resilience features for robust payment processing."""
    logger.info("=== Combined Resilience Example ===")

    # 1. Setup circuit breaker
    payment_breaker = CircuitBreaker(
        name="payment_service",
        failure_threshold=3,
        recovery_timeout=60.0
    )

    # 2. Setup rate limiter
    rate_limiter = AsyncTokenBucket(rate=5.0, capacity=10)  # 5 payments/sec max

    # 3. Create idempotent payment processor
    @idempotent(ttl=7200)  # 2 hour idempotency
    async def process_payment_resilient(payment_id: int, user_id: int, amount: float):
        """Process payment with full resilience stack."""

        # Apply rate limiting
        await rate_limiter.acquire()

        # Call payment API through circuit breaker
        async def payment_api_call():
            logger.info("calling_payment_api", payment_id=payment_id, user_id=user_id, amount=amount)
            # Simulated API call
            await asyncio.sleep(0.05)
            return {"payment_id": payment_id, "status": "success"}

        try:
            result = await payment_breaker.call(payment_api_call)
            logger.info("payment_successful", payment_id=payment_id, result=result)
            return result

        except CircuitBreakerError:
            logger.error("payment_circuit_open", payment_id=payment_id)
            # Queue for retry when service recovers
            return {"payment_id": payment_id, "status": "queued_for_retry"}

    # Process multiple payments
    payments = [
        (1001, 100, 50.00),
        (1002, 101, 75.50),
        (1001, 100, 50.00),  # Duplicate - will be skipped
    ]

    for payment_id, user_id, amount in payments:
        result = await process_payment_resilient(payment_id, user_id, amount)
        logger.info("payment_result", payment_id=payment_id, skipped=result.get("skipped", False))


# Example 6: Advanced rate limiter usage
async def advanced_rate_limiting():
    """Demonstrate advanced rate limiter features."""
    logger.info("=== Advanced Rate Limiting Example ===")

    limiter = AsyncTokenBucket(rate=10.0, capacity=20)

    # Non-blocking acquire
    if await limiter.try_acquire(tokens=5):
        logger.info("tokens_acquired_immediately")
    else:
        logger.info("tokens_not_available")

    # Acquire with timeout
    acquired = await limiter.acquire(tokens=1, timeout=2.0)
    if acquired:
        logger.info("tokens_acquired_within_timeout")
    else:
        logger.info("timeout_reached")

    # Check available tokens
    available = limiter.available_tokens
    logger.info("available_tokens", count=round(available, 2))

    # Dynamic rate adjustment
    await limiter.set_rate(5.0)  # Reduce to 5 req/s
    logger.info("rate_adjusted", new_rate=5.0)


async def main():
    """Run all examples."""
    logger.info("Starting resilience and security examples")

    # Run examples sequentially
    await startup_security_example()
    await circuit_breaker_example()
    await idempotency_example()
    await rate_limiting_example()
    await resilient_payment_processing()
    await advanced_rate_limiting()

    logger.info("All examples completed")


if __name__ == "__main__":
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    # Run examples
    asyncio.run(main())
