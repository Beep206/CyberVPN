"""Unit tests for deep linking utilities."""

from __future__ import annotations

import pytest

from src.utils.deep_links import (
    create_referral_link,
    create_subscription_link,
    decode_deep_link,
    encode_deep_link,
)


class TestEncodeDeepLink:
    """Test deep link encoding."""

    def test_encode_simple_payload(self) -> None:
        """Test encoding a simple payload."""
        payload = {"ref": "user123", "source": "promo"}
        encoded = encode_deep_link(payload)

        assert isinstance(encoded, str)
        assert len(encoded) > 0
        assert "=" not in encoded  # Padding should be removed

    def test_encode_with_signature(self) -> None:
        """Test encoding with HMAC signature."""
        payload = {"ref": 12345}
        encoded = encode_deep_link(payload, sign=True)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_without_signature(self) -> None:
        """Test encoding without signature."""
        payload = {"type": "test"}
        encoded = encode_deep_link(payload, sign=False)

        assert isinstance(encoded, str)
        # Decode to verify it's just the payload without signature wrapper
        decoded = decode_deep_link(encoded, verify_signature=False)
        assert decoded == payload

    def test_encode_complex_payload(self) -> None:
        """Test encoding complex nested payload."""
        payload = {
            "type": "subscribe",
            "plan": "premium",
            "duration": 30,
            "meta": {"source": "email", "campaign": "summer2024"},
        }
        encoded = encode_deep_link(payload)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_empty_payload(self) -> None:
        """Test encoding empty payload."""
        payload = {}
        encoded = encode_deep_link(payload)

        assert isinstance(encoded, str)
        decoded = decode_deep_link(encoded)
        assert decoded == payload

    def test_encode_raises_on_unserializable(self) -> None:
        """Test that unserializable objects raise ValueError."""

        class CustomObject:
            pass

        payload = {"obj": CustomObject()}

        with pytest.raises(ValueError, match="Failed to encode"):
            encode_deep_link(payload)


class TestDecodeDeepLink:
    """Test deep link decoding."""

    def test_decode_simple_payload(self) -> None:
        """Test decoding a simple payload."""
        payload = {"ref": "user123"}
        encoded = encode_deep_link(payload, sign=False)
        decoded = decode_deep_link(encoded, verify_signature=False)

        assert decoded == payload

    def test_decode_with_signature_verification(self) -> None:
        """Test decoding with valid signature."""
        payload = {"ref": 12345, "type": "referral"}
        encoded = encode_deep_link(payload, sign=True)
        decoded = decode_deep_link(encoded, verify_signature=True)

        assert decoded == payload

    def test_decode_invalid_signature_raises(self) -> None:
        """Test that invalid signature raises ValueError."""
        payload = {"ref": 12345}
        encoded = encode_deep_link(payload, sign=True)

        # Tamper with the encoded string
        tampered = encoded[:-5] + "XXXXX"

        with pytest.raises(ValueError):
            decode_deep_link(tampered, verify_signature=True)

    def test_decode_without_verification(self) -> None:
        """Test decoding signed payload without verification."""
        payload = {"ref": 99999}
        encoded = encode_deep_link(payload, sign=True)

        # Should still decode even if we skip verification
        decoded = decode_deep_link(encoded, verify_signature=False)
        # When signed, payload is wrapped, so we get the wrapper
        assert "d" in decoded or decoded == payload

    def test_decode_invalid_base64_raises(self) -> None:
        """Test that invalid base64 raises ValueError."""
        invalid_encoded = "!@#$%^&*()"

        with pytest.raises(ValueError, match="Failed to decode"):
            decode_deep_link(invalid_encoded)

    def test_decode_invalid_json_raises(self) -> None:
        """Test that invalid JSON raises ValueError."""
        import base64

        # Create valid base64 but invalid JSON
        invalid_json = base64.urlsafe_b64encode(b"{invalid json}").decode()

        with pytest.raises(ValueError, match="Failed to decode"):
            decode_deep_link(invalid_json)

    def test_roundtrip_encode_decode(self) -> None:
        """Test complete encode/decode roundtrip."""
        original = {"user_id": 123, "action": "subscribe", "plan": "pro"}

        encoded = encode_deep_link(original, sign=True)
        decoded = decode_deep_link(encoded, verify_signature=True)

        assert decoded == original

    def test_decode_non_dict_payload(self) -> None:
        """Test decoding non-dict values."""
        import base64
        import json

        # Encode a simple string
        value = "test_value"
        json_str = json.dumps(value)
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")

        decoded = decode_deep_link(encoded, verify_signature=False)
        # Non-dict values get wrapped
        assert decoded == {"value": value}


class TestCreateReferralLink:
    """Test referral link creation."""

    def test_create_basic_referral_link(self) -> None:
        """Test creating a basic referral link."""
        link = create_referral_link("cybervpn_bot", 12345)

        assert link.startswith("https://t.me/cybervpn_bot?start=")
        assert "ref_" not in link  # Should use encoded format

    def test_create_referral_link_with_source(self) -> None:
        """Test creating referral link with source."""
        link = create_referral_link("cybervpn_bot", 12345, source="promo")

        assert link.startswith("https://t.me/cybervpn_bot?start=")

        # Extract and decode the payload
        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["ref"] == 12345
        assert decoded["type"] == "referral"
        assert decoded["source"] == "promo"

    def test_create_referral_link_without_source(self) -> None:
        """Test creating referral link without source."""
        link = create_referral_link("testbot", 99999)

        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["ref"] == 99999
        assert decoded["type"] == "referral"
        assert "source" not in decoded

    def test_referral_link_decode_roundtrip(self) -> None:
        """Test that referral links can be decoded."""
        user_id = 54321
        source = "email_campaign"
        link = create_referral_link("mybot", user_id, source)

        # Extract payload
        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["ref"] == user_id
        assert decoded["source"] == source


class TestCreateSubscriptionLink:
    """Test subscription link creation."""

    def test_create_basic_subscription_link(self) -> None:
        """Test creating a basic subscription link."""
        link = create_subscription_link("cybervpn_bot", "premium")

        assert link.startswith("https://t.me/cybervpn_bot?start=")

        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["type"] == "subscribe"
        assert decoded["plan"] == "premium"

    def test_create_subscription_link_with_duration(self) -> None:
        """Test creating subscription link with duration."""
        link = create_subscription_link("cybervpn_bot", "pro", duration_days=90)

        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["type"] == "subscribe"
        assert decoded["plan"] == "pro"
        assert decoded["days"] == 90

    def test_create_subscription_link_without_duration(self) -> None:
        """Test creating subscription link without duration."""
        link = create_subscription_link("testbot", "basic")

        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["type"] == "subscribe"
        assert decoded["plan"] == "basic"
        assert "days" not in decoded

    def test_subscription_link_decode_roundtrip(self) -> None:
        """Test subscription link roundtrip encoding/decoding."""
        plan_id = "enterprise"
        duration = 365
        link = create_subscription_link("mybot", plan_id, duration)

        encoded = link.split("start=")[1]
        decoded = decode_deep_link(encoded)

        assert decoded["type"] == "subscribe"
        assert decoded["plan"] == plan_id
        assert decoded["days"] == duration


class TestDeepLinkIntegration:
    """Integration tests for deep link workflows."""

    def test_referral_workflow(self) -> None:
        """Test complete referral deep link workflow."""
        # User A shares referral link
        user_a_id = 11111
        link = create_referral_link("bot", user_a_id, source="telegram")

        # User B clicks the link - extract start parameter
        start_param = link.split("start=")[1]

        # Bot receives /start command with parameter
        decoded = decode_deep_link(start_param)

        # Verify referral data
        assert decoded["ref"] == user_a_id
        assert decoded["type"] == "referral"
        assert decoded["source"] == "telegram"

    def test_promo_subscription_workflow(self) -> None:
        """Test subscription link from promo campaign."""
        link = create_subscription_link("bot", "premium_annual", 365)

        start_param = link.split("start=")[1]
        decoded = decode_deep_link(start_param)

        assert decoded["type"] == "subscribe"
        assert decoded["plan"] == "premium_annual"
        assert decoded["days"] == 365

    def test_unknown_type_handling(self) -> None:
        """Test handling unknown deep link types."""
        # Manually create unknown type
        payload = {"type": "unknown_action", "data": "test"}
        encoded = encode_deep_link(payload)

        decoded = decode_deep_link(encoded)

        # Should still decode successfully
        assert decoded["type"] == "unknown_action"
        assert decoded["data"] == "test"
