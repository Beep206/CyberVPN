"""S1 payment webhook signature verification contracts.

The functions in this module are intentionally small and provider-specific:
they verify transport authenticity only. Payment finality, amount/currency
matching and idempotency are separate S1 gates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider


class Stage1WebhookSignatureScheme(StrEnum):
    """Provider webhook authenticity scheme used in S1."""

    CRYPTOBOT_HMAC_SHA256_BODY_TOKEN_HASH = "cryptobot_hmac_sha256_body_token_hash"  # noqa: S105
    NOWPAYMENTS_HMAC_SHA512_SORTED_JSON = "nowpayments_hmac_sha512_sorted_json"
    PAYRAM_API_KEY_HEADER = "payram_api_key_header"
    TELEGRAM_SECRET_TOKEN_HEADER = "telegram_secret_token_header"  # noqa: S105
    DIGISELLER_HMAC_SHA256_SORTED_FIELDS = "digiseller_hmac_sha256_sorted_fields"
    YOOKASSA_PROVIDER_STATUS_IP_RECHECK = "yookassa_provider_status_ip_recheck"


class Stage1WebhookSignatureStatus(StrEnum):
    """Safe verification status for evidence, logs and API guards."""

    VALID = "valid"
    INVALID = "invalid"
    MISSING_SIGNATURE = "missing_signature"
    MISSING_SECRET = "missing_secret"  # noqa: S105
    REQUIRES_PROVIDER_RECHECK = "requires_provider_recheck"


@dataclass(frozen=True, slots=True)
class Stage1WebhookSignatureDecision:
    """Decision produced by the S1 webhook authenticity gate.

    This object never stores raw payload, signatures, tokens, API keys or
    provider secrets. It is safe to serialize into redacted evidence.
    """

    provider: Stage1PaymentProvider
    scheme: Stage1WebhookSignatureScheme
    status: Stage1WebhookSignatureStatus
    signature_location: str | None
    signature_present: bool
    secret_configured: bool
    provider_recheck_required: bool = False
    provider_recheck_confirmed: bool = False

    @property
    def accepted(self) -> bool:
        """Whether downstream payment processing may continue."""

        return self.status == Stage1WebhookSignatureStatus.VALID

    def to_safe_dict(self) -> dict[str, str | bool | None]:
        """Serialize without leaking provider secrets or raw identifiers."""

        return {
            "provider": self.provider.value,
            "scheme": self.scheme.value,
            "status": self.status.value,
            "accepted": self.accepted,
            "signature_location": self.signature_location,
            "signature_present": self.signature_present,
            "secret_configured": self.secret_configured,
            "provider_recheck_required": self.provider_recheck_required,
            "provider_recheck_confirmed": self.provider_recheck_confirmed,
        }


def verify_stage1_webhook_signature(
    provider: Stage1PaymentProvider | str,
    *,
    body: bytes = b"",
    headers: Mapping[str, Any] | None = None,
    secret: str | None = None,
    payload: Mapping[str, Any] | None = None,
    provider_recheck_confirmed: bool = False,
) -> Stage1WebhookSignatureDecision:
    """Verify an S1 provider webhook authenticity contract.

    `secret` means the provider-specific verifier secret:
    CryptoBot app token, NOWPayments IPN secret, PayRam project API key,
    Telegram webhook `secret_token`, or Digiseller secret key.
    YooKassa does not document an HMAC webhook signature; S1 requires a
    provider status/IP recheck before downstream paid-access processing.
    """

    provider_enum = _coerce_provider(provider)
    normalized_headers = _normalize_headers(headers or {})

    if provider_enum == Stage1PaymentProvider.CRYPTOBOT:
        return _verify_cryptobot(body=body, headers=normalized_headers, secret=secret, provider=provider_enum)
    if provider_enum == Stage1PaymentProvider.NOWPAYMENTS:
        return _verify_nowpayments(
            body=body,
            headers=normalized_headers,
            secret=secret,
            provider=provider_enum,
            payload=payload,
        )
    if provider_enum == Stage1PaymentProvider.PAYRAM:
        return _verify_static_header(
            headers=normalized_headers,
            secret=secret,
            provider=provider_enum,
            scheme=Stage1WebhookSignatureScheme.PAYRAM_API_KEY_HEADER,
            header_name="api-key",
            signature_location="API-Key",
        )
    if provider_enum == Stage1PaymentProvider.TELEGRAM_STARS:
        return _verify_static_header(
            headers=normalized_headers,
            secret=secret,
            provider=provider_enum,
            scheme=Stage1WebhookSignatureScheme.TELEGRAM_SECRET_TOKEN_HEADER,
            header_name="x-telegram-bot-api-secret-token",
            signature_location="X-Telegram-Bot-Api-Secret-Token",
        )
    if provider_enum == Stage1PaymentProvider.DIGISELLER:
        return _verify_digiseller(provider=provider_enum, secret=secret, payload=payload)
    if provider_enum == Stage1PaymentProvider.YOOKASSA:
        return _verify_yookassa_recheck(provider=provider_enum, provider_recheck_confirmed=provider_recheck_confirmed)

    raise ValueError("Unsupported S1 payment provider")


def _verify_cryptobot(
    *,
    body: bytes,
    headers: Mapping[str, str],
    secret: str | None,
    provider: Stage1PaymentProvider,
) -> Stage1WebhookSignatureDecision:
    scheme = Stage1WebhookSignatureScheme.CRYPTOBOT_HMAC_SHA256_BODY_TOKEN_HASH
    signature = _header(headers, "crypto-pay-api-signature")
    missing = _missing_signature_decision(
        provider,
        scheme,
        "crypto-pay-api-signature",
        signature,
        secret_configured=_configured_secret(secret) is not None,
    )
    if missing is not None:
        return missing

    configured_secret = _configured_secret(secret)
    if configured_secret is None:
        return _decision(
            provider,
            scheme,
            Stage1WebhookSignatureStatus.MISSING_SECRET,
            "crypto-pay-api-signature",
            signature_present=True,
            secret_configured=False,
        )

    hmac_secret = hashlib.sha256(configured_secret.encode("utf-8")).digest()
    expected = hmac.new(hmac_secret, body, hashlib.sha256).hexdigest()
    return _hmac_decision(provider, scheme, "crypto-pay-api-signature", signature, expected)


def _verify_nowpayments(
    *,
    body: bytes,
    headers: Mapping[str, str],
    secret: str | None,
    provider: Stage1PaymentProvider,
    payload: Mapping[str, Any] | None,
) -> Stage1WebhookSignatureDecision:
    scheme = Stage1WebhookSignatureScheme.NOWPAYMENTS_HMAC_SHA512_SORTED_JSON
    signature = _header(headers, "x-nowpayments-sig")
    missing = _missing_signature_decision(
        provider,
        scheme,
        "x-nowpayments-sig",
        signature,
        secret_configured=_configured_secret(secret) is not None,
    )
    if missing is not None:
        return missing

    configured_secret = _configured_secret(secret)
    if configured_secret is None:
        return _decision(
            provider,
            scheme,
            Stage1WebhookSignatureStatus.MISSING_SECRET,
            "x-nowpayments-sig",
            signature_present=True,
            secret_configured=False,
        )

    request_payload = payload if payload is not None else _json_body_or_none(body)
    if request_payload is None:
        return _decision(
            provider,
            scheme,
            Stage1WebhookSignatureStatus.INVALID,
            "x-nowpayments-sig",
            signature_present=True,
            secret_configured=True,
        )

    canonical_body = json.dumps(_sort_json_value(request_payload), ensure_ascii=False, separators=(",", ":"))
    expected = hmac.new(configured_secret.encode("utf-8"), canonical_body.encode("utf-8"), hashlib.sha512).hexdigest()
    return _hmac_decision(provider, scheme, "x-nowpayments-sig", signature, expected)


def _verify_static_header(
    *,
    headers: Mapping[str, str],
    secret: str | None,
    provider: Stage1PaymentProvider,
    scheme: Stage1WebhookSignatureScheme,
    header_name: str,
    signature_location: str,
) -> Stage1WebhookSignatureDecision:
    signature = _header(headers, header_name)
    missing = _missing_signature_decision(
        provider,
        scheme,
        signature_location,
        signature,
        secret_configured=_configured_secret(secret) is not None,
    )
    if missing is not None:
        return missing

    configured_secret = _configured_secret(secret)
    if configured_secret is None:
        return _decision(
            provider,
            scheme,
            Stage1WebhookSignatureStatus.MISSING_SECRET,
            signature_location,
            signature_present=True,
            secret_configured=False,
        )

    status = (
        Stage1WebhookSignatureStatus.VALID
        if hmac.compare_digest(signature or "", configured_secret)
        else Stage1WebhookSignatureStatus.INVALID
    )
    return _decision(
        provider,
        scheme,
        status,
        signature_location,
        signature_present=True,
        secret_configured=True,
    )


DIGISELLER_UNSIGNED_FIELDS = frozenset(
    {
        "signature",
        "error",
        "integrator",
        "amount_out",
        "currency_out",
        "description",
        "lang",
        "email",
        "return_url",
    }
)


def _verify_digiseller(
    *,
    provider: Stage1PaymentProvider,
    secret: str | None,
    payload: Mapping[str, Any] | None,
) -> Stage1WebhookSignatureDecision:
    scheme = Stage1WebhookSignatureScheme.DIGISELLER_HMAC_SHA256_SORTED_FIELDS
    signature_location = "payload.signature"
    signature = _text_or_none((payload or {}).get("signature"))
    missing = _missing_signature_decision(
        provider,
        scheme,
        signature_location,
        signature,
        secret_configured=_configured_secret(secret) is not None,
    )
    if missing is not None:
        return missing

    configured_secret = _configured_secret(secret)
    if configured_secret is None:
        return _decision(
            provider,
            scheme,
            Stage1WebhookSignatureStatus.MISSING_SECRET,
            signature_location,
            signature_present=True,
            secret_configured=False,
        )

    if payload is None:
        return _decision(
            provider,
            scheme,
            Stage1WebhookSignatureStatus.INVALID,
            signature_location,
            signature_present=True,
            secret_configured=True,
        )

    material = _digiseller_signature_material(payload)
    expected = hmac.new(configured_secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()
    return _hmac_decision(provider, scheme, signature_location, signature, expected)


def _verify_yookassa_recheck(
    *,
    provider: Stage1PaymentProvider,
    provider_recheck_confirmed: bool,
) -> Stage1WebhookSignatureDecision:
    return _decision(
        provider,
        Stage1WebhookSignatureScheme.YOOKASSA_PROVIDER_STATUS_IP_RECHECK,
        Stage1WebhookSignatureStatus.VALID
        if provider_recheck_confirmed
        else Stage1WebhookSignatureStatus.REQUIRES_PROVIDER_RECHECK,
        signature_location=None,
        signature_present=False,
        secret_configured=True,
        provider_recheck_required=True,
        provider_recheck_confirmed=provider_recheck_confirmed,
    )


def _hmac_decision(
    provider: Stage1PaymentProvider,
    scheme: Stage1WebhookSignatureScheme,
    signature_location: str,
    signature: str | None,
    expected: str,
) -> Stage1WebhookSignatureDecision:
    normalized_signature = (signature or "").strip().lower()
    status = (
        Stage1WebhookSignatureStatus.VALID
        if hmac.compare_digest(normalized_signature, expected.lower())
        else Stage1WebhookSignatureStatus.INVALID
    )
    return _decision(
        provider,
        scheme,
        status,
        signature_location,
        signature_present=True,
        secret_configured=True,
    )


def _missing_signature_decision(
    provider: Stage1PaymentProvider,
    scheme: Stage1WebhookSignatureScheme,
    signature_location: str,
    signature: str | None,
    *,
    secret_configured: bool,
) -> Stage1WebhookSignatureDecision | None:
    if signature:
        return None

    return _decision(
        provider,
        scheme,
        Stage1WebhookSignatureStatus.MISSING_SIGNATURE,
        signature_location,
        signature_present=False,
        secret_configured=secret_configured,
    )


def _decision(
    provider: Stage1PaymentProvider,
    scheme: Stage1WebhookSignatureScheme,
    status: Stage1WebhookSignatureStatus,
    signature_location: str | None,
    *,
    signature_present: bool,
    secret_configured: bool,
    provider_recheck_required: bool = False,
    provider_recheck_confirmed: bool = False,
) -> Stage1WebhookSignatureDecision:
    return Stage1WebhookSignatureDecision(
        provider=provider,
        scheme=scheme,
        status=status,
        signature_location=signature_location,
        signature_present=signature_present,
        secret_configured=secret_configured,
        provider_recheck_required=provider_recheck_required,
        provider_recheck_confirmed=provider_recheck_confirmed,
    )


def _normalize_headers(headers: Mapping[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value).strip() for key, value in headers.items()}


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return _text_or_none(headers.get(name.lower()))


def _configured_secret(secret: str | None) -> str | None:
    return _text_or_none(secret)


def _json_body_or_none(body: bytes) -> Mapping[str, Any] | None:
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _sort_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _sort_json_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_json_value(item) for item in value]
    return value


def _digiseller_signature_material(payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    normalized_items = sorted((str(key), value) for key, value in payload.items())
    for key, value in normalized_items:
        if key in DIGISELLER_UNSIGNED_FIELDS:
            continue
        text_value = _text_or_none(value)
        if text_value is None:
            continue
        parts.append(f"{key}:{text_value};")
    return "".join(parts)


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_provider(provider: Stage1PaymentProvider | str) -> Stage1PaymentProvider:
    if isinstance(provider, Stage1PaymentProvider):
        return provider
    return Stage1PaymentProvider(str(provider))
