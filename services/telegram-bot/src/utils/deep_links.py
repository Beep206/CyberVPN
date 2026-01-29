"""Deep linking utilities for Telegram bot."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

import structlog

from .constants import DEEP_LINK_SALT

logger = structlog.get_logger(__name__)


def encode_deep_link(payload: dict[str, Any], sign: bool = True) -> str:
    """
    Encode a payload into a deep link parameter.

    Args:
        payload: Dictionary to encode
        sign: Whether to sign the payload with HMAC

    Returns:
        Base64-encoded string suitable for deep linking

    Examples:
        >>> encode_deep_link({"ref": "user123", "source": "promo"})
        "eyJyZWYiOiJ1c2VyMTIzIiwic291cmNlIjoicHJvbW8ifQ..."

    Raises:
        ValueError: If payload cannot be serialized
    """
    try:
        # Serialize to JSON
        json_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        # Add HMAC signature if requested
        if sign:
            signature = hmac.new(
                DEEP_LINK_SALT.encode(),
                json_str.encode(),
                hashlib.sha256,
            ).hexdigest()[:16]
            json_str = json.dumps(
                {"d": payload, "s": signature},
                separators=(",", ":"),
                sort_keys=True,
            )

        # Base64 encode (URL-safe)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()

        # Remove padding
        encoded = encoded.rstrip("=")

        logger.debug("encoded_deep_link", payload=payload, encoded_length=len(encoded))
        return encoded

    except (TypeError, ValueError) as e:
        logger.error("deep_link_encode_failed", error=str(e), payload=payload)
        raise ValueError(f"Failed to encode deep link payload: {e}") from e


def decode_deep_link(encoded: str, verify_signature: bool = True) -> dict[str, Any]:
    """
    Decode a deep link parameter into a payload.

    Args:
        encoded: Base64-encoded deep link string
        verify_signature: Whether to verify HMAC signature

    Returns:
        Decoded dictionary payload

    Examples:
        >>> decode_deep_link("eyJyZWYiOiJ1c2VyMTIzIn0")
        {"ref": "user123"}

    Raises:
        ValueError: If decoding fails or signature is invalid
    """
    try:
        # Add padding back
        padding = (4 - len(encoded) % 4) % 4
        encoded_padded = encoded + ("=" * padding)

        # Base64 decode
        json_str = base64.urlsafe_b64decode(encoded_padded).decode()

        # Parse JSON
        data = json.loads(json_str)

        # Verify signature if present
        if verify_signature and isinstance(data, dict) and "s" in data and "d" in data:
            payload = data["d"]
            signature = data["s"]

            # Recalculate signature
            expected_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            expected_signature = hmac.new(
                DEEP_LINK_SALT.encode(),
                expected_json.encode(),
                hashlib.sha256,
            ).hexdigest()[:16]

            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(
                    "deep_link_signature_invalid",
                    encoded=encoded,
                )
                raise ValueError("Deep link signature verification failed")

            logger.debug("decoded_deep_link", payload=payload, verified=True)
            return payload

        # No signature, return data as-is
        logger.debug("decoded_deep_link", payload=data, verified=False)
        return data if isinstance(data, dict) else {"value": data}

    except (ValueError, json.JSONDecodeError, KeyError) as e:
        logger.error("deep_link_decode_failed", error=str(e), encoded=encoded)
        raise ValueError(f"Failed to decode deep link: {e}") from e


def create_referral_link(bot_username: str, user_id: int, source: str | None = None) -> str:
    """
    Create a referral deep link for a user.

    Args:
        bot_username: Bot's Telegram username (without @)
        user_id: ID of the referring user
        source: Optional source/campaign identifier

    Returns:
        Full Telegram deep link URL

    Examples:
        >>> create_referral_link("cybervpn_bot", 12345, "promo")
        "https://t.me/cybervpn_bot?start=..."
    """
    payload = {"ref": user_id, "type": "referral"}
    if source:
        payload["source"] = source

    encoded = encode_deep_link(payload)
    return f"https://t.me/{bot_username}?start={encoded}"


def create_subscription_link(
    bot_username: str,
    plan_id: str,
    duration_days: int | None = None,
) -> str:
    """
    Create a subscription deep link.

    Args:
        bot_username: Bot's Telegram username (without @)
        plan_id: Subscription plan identifier
        duration_days: Optional subscription duration

    Returns:
        Full Telegram deep link URL

    Examples:
        >>> create_subscription_link("cybervpn_bot", "premium", 30)
        "https://t.me/cybervpn_bot?start=..."
    """
    payload = {"type": "subscribe", "plan": plan_id}
    if duration_days:
        payload["days"] = duration_days

    encoded = encode_deep_link(payload)
    return f"https://t.me/{bot_username}?start={encoded}"
