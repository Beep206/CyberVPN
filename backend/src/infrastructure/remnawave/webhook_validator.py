import hashlib
import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class WebhookValidationResult:
    is_valid: bool
    reason: str | None = None


class RemnawaveWebhookValidator:
    def __init__(
        self,
        secret: str,
        *,
        max_age_seconds: int = 300,
        future_skew_seconds: int = 60,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._secret = secret.encode()
        self._max_age_seconds = max_age_seconds
        self._future_skew_seconds = future_skew_seconds
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def validate_signature(self, body: bytes, signature: str) -> bool:
        computed = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def validate_request(
        self,
        body: bytes,
        signature: str | None,
        timestamp: str | None,
        *,
        allow_missing_timestamp: bool = False,
    ) -> WebhookValidationResult:
        if not signature:
            return WebhookValidationResult(is_valid=False, reason="missing_signature")

        if not self.validate_signature(body, signature):
            return WebhookValidationResult(is_valid=False, reason="invalid_signature")

        if not timestamp:
            if allow_missing_timestamp:
                return WebhookValidationResult(is_valid=True)
            return WebhookValidationResult(is_valid=False, reason="missing_timestamp")

        parsed_timestamp = self._parse_timestamp(timestamp)
        if parsed_timestamp is None:
            return WebhookValidationResult(is_valid=False, reason="invalid_timestamp")

        now = self._now_provider()
        age_seconds = (now - parsed_timestamp).total_seconds()

        if age_seconds < -self._future_skew_seconds:
            return WebhookValidationResult(is_valid=False, reason="future_timestamp")

        if age_seconds > self._max_age_seconds:
            return WebhookValidationResult(is_valid=False, reason="stale_timestamp")

        return WebhookValidationResult(is_valid=True)

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime | None:
        normalized = timestamp.strip()
        if not normalized:
            return None

        if normalized.isdigit():
            try:
                return datetime.fromtimestamp(int(normalized), UTC)
            except (OverflowError, ValueError):
                return None

        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)
