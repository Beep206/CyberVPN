"""CryptoBot webhook handler with validation (MED-9).

Security improvements:
- Invoice ID format validation
- Duplicate invoice processing prevention (idempotency)
- Audit logging for validation failures
"""

import hashlib
import hmac
import json
import logging
import re
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CryptoBotWebhookHandler:
    """Handler for CryptoBot payment webhooks with security validation (MED-9)."""

    # CryptoBot invoice ID format: numeric string
    INVOICE_ID_PATTERN = re.compile(r"^\d{1,20}$")

    # Redis key prefix for processed invoices (idempotency)
    PROCESSED_PREFIX = "cryptobot:processed:"
    PROCESSED_TTL = 86400 * 7  # 7 days

    def __init__(self, api_token: str, redis_client: redis.Redis | None = None) -> None:
        self._secret = hashlib.sha256(api_token.encode()).digest()
        self._redis = redis_client

    def validate_signature(self, body: bytes, signature: str) -> bool:
        """Validate HMAC signature of webhook payload."""
        computed = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_payload(self, body: bytes) -> dict[str, Any]:
        """Parse webhook JSON payload."""
        return json.loads(body)

    def validate_invoice_id_format(self, invoice_id: str) -> bool:
        """Validate invoice ID matches expected CryptoBot format (MED-9).

        Args:
            invoice_id: The invoice ID to validate

        Returns:
            True if valid format, False otherwise
        """
        if not invoice_id:
            logger.warning("Payment validation failed: empty invoice_id")
            return False

        if not self.INVOICE_ID_PATTERN.match(invoice_id):
            logger.warning(
                "Payment validation failed: invalid invoice_id format",
                extra={"invoice_id": invoice_id[:50]},  # Truncate for safety
            )
            return False

        return True

    async def is_duplicate_invoice(self, invoice_id: str) -> bool:
        """Check if invoice has already been processed (idempotency - MED-9).

        Args:
            invoice_id: The invoice ID to check

        Returns:
            True if already processed, False otherwise
        """
        if self._redis is None:
            # Without Redis, can't enforce idempotency - log warning
            logger.warning("Redis not available for payment idempotency check")
            return False

        key = f"{self.PROCESSED_PREFIX}{invoice_id}"
        exists = await self._redis.exists(key)
        return exists > 0

    async def mark_invoice_processed(self, invoice_id: str) -> None:
        """Mark invoice as processed for idempotency (MED-9).

        Args:
            invoice_id: The invoice ID to mark
        """
        if self._redis is None:
            return

        key = f"{self.PROCESSED_PREFIX}{invoice_id}"
        await self._redis.setex(key, self.PROCESSED_TTL, "processed")

        logger.debug(
            "Invoice marked as processed",
            extra={"invoice_id": invoice_id},
        )

    async def validate_payment(
        self,
        invoice_id: str,
        body: bytes,
        signature: str,
    ) -> tuple[bool, str | None]:
        """Validate a payment webhook (MED-9).

        Performs full validation:
        1. Signature validation
        2. Invoice ID format validation
        3. Duplicate processing check

        Args:
            invoice_id: The invoice ID from payload
            body: Raw webhook body
            signature: HMAC signature header

        Returns:
            Tuple of (valid: bool, error_message: str | None)
        """
        # 1. Validate signature
        if not self.validate_signature(body, signature):
            logger.warning(
                "Payment validation failed: invalid signature",
                extra={"invoice_id": invoice_id[:20] if invoice_id else "N/A"},
            )
            return False, "Invalid webhook signature"

        # 2. Validate invoice ID format
        if not self.validate_invoice_id_format(invoice_id):
            return False, "Invalid invoice ID format"

        # 3. Check for duplicate processing
        if await self.is_duplicate_invoice(invoice_id):
            logger.info(
                "Payment already processed (idempotency)",
                extra={"invoice_id": invoice_id},
            )
            return False, "Invoice already processed"

        return True, None
