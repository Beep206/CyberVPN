"""S1 payment webhook idempotency helpers.

The helpers are intentionally provider-agnostic and side-effect oriented:
one provider event may be accepted multiple times, but wallet transactions,
subscription extension and provisioning jobs must be applied once per
provider/payment/status operation.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any

from src.presentation.api.shared.stage1_payment_mapping import Stage1PaymentProvider, normalize_provider_status


class Stage1WebhookSideEffect(StrEnum):
    """Launch-critical side effects guarded by S1 webhook idempotency."""

    PAYMENT_STATUS_UPDATE = "payment_status_update"
    WALLET_TRANSACTION = "wallet_transaction"
    SUBSCRIPTION_EXTENSION = "subscription_extension"
    PROVISIONING_JOB = "provisioning_job"
    SUPPORT_ESCALATION = "support_escalation"


class Stage1WebhookIdempotencyResult(StrEnum):
    """Result of accepting a provider webhook into the S1 idempotency guard."""

    ACCEPTED_NEW = "accepted_new"
    ACCEPTED_ALREADY_APPLIED = "accepted_already_applied"
    DUPLICATE_ACCEPTED = "duplicate_accepted"


DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS: tuple[Stage1WebhookSideEffect, ...] = (
    Stage1WebhookSideEffect.PAYMENT_STATUS_UPDATE,
    Stage1WebhookSideEffect.WALLET_TRANSACTION,
    Stage1WebhookSideEffect.SUBSCRIPTION_EXTENSION,
    Stage1WebhookSideEffect.PROVISIONING_JOB,
)


@dataclass(frozen=True, slots=True)
class Stage1WebhookIdentity:
    """Canonical identity for a payment-provider webhook event."""

    provider: Stage1PaymentProvider
    provider_payment_id: str
    normalized_status: str
    event_type: str | None = None
    provider_event_id: str | None = None
    account_scope: str | None = None

    @property
    def idempotency_key(self) -> str:
        """Exact event key, hashed so logs/evidence do not expose provider IDs."""

        return _hashed_key(
            "s1:webhook:event",
            (
                self.provider.value,
                self.account_scope or "default",
                self.provider_event_id or "",
                self.provider_payment_id,
                self.event_type or "",
                self.normalized_status,
            ),
        )

    @property
    def operation_key(self) -> str:
        """Payment/status operation key used to suppress repeated side effects."""

        return _hashed_key(
            "s1:webhook:operation",
            (
                self.provider.value,
                self.account_scope or "default",
                self.provider_payment_id,
                self.normalized_status,
            ),
        )

    def to_safe_dict(self) -> dict[str, str | bool | None]:
        """Serialize without raw payload, signatures, tokens or provider secrets."""

        return {
            "provider": self.provider.value,
            "normalized_status": self.normalized_status,
            "event_type": self.event_type,
            "provider_event_id_present": self.provider_event_id is not None,
            "account_scope": self.account_scope,
            "idempotency_key": self.idempotency_key,
            "operation_key": self.operation_key,
        }


@dataclass(frozen=True, slots=True)
class Stage1WebhookIdempotencyDecision:
    """Decision returned by the S1 idempotency guard."""

    result: Stage1WebhookIdempotencyResult
    identity: Stage1WebhookIdentity
    side_effect_keys: tuple[tuple[Stage1WebhookSideEffect, str], ...]
    side_effects_allowed: tuple[Stage1WebhookSideEffect, ...]
    side_effects_already_applied: tuple[Stage1WebhookSideEffect, ...]

    @property
    def duplicate(self) -> bool:
        return self.result == Stage1WebhookIdempotencyResult.DUPLICATE_ACCEPTED

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize for tests, evidence and future internal diagnostics APIs."""

        return {
            "result": self.result.value,
            "duplicate": self.duplicate,
            "identity": self.identity.to_safe_dict(),
            "side_effects_allowed": [effect.value for effect in self.side_effects_allowed],
            "side_effects_already_applied": [effect.value for effect in self.side_effects_already_applied],
            "side_effect_keys": {effect.value: key for effect, key in self.side_effect_keys},
        }


@dataclass(slots=True)
class Stage1InMemoryWebhookIdempotencyGuard:
    """In-memory guard for local tests/evidence.

    Production code must back the same key contract with Redis and/or database
    uniqueness before any paid provider is enabled.
    """

    _seen_event_keys: set[str] = field(default_factory=set)
    _seen_side_effect_keys: set[str] = field(default_factory=set)

    def record(
        self,
        identity: Stage1WebhookIdentity,
        side_effects: Sequence[Stage1WebhookSideEffect] = DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS,
    ) -> Stage1WebhookIdempotencyDecision:
        side_effect_key_pairs = build_stage1_webhook_side_effect_keys(identity, side_effects)

        if identity.idempotency_key in self._seen_event_keys:
            return Stage1WebhookIdempotencyDecision(
                result=Stage1WebhookIdempotencyResult.DUPLICATE_ACCEPTED,
                identity=identity,
                side_effect_keys=side_effect_key_pairs,
                side_effects_allowed=(),
                side_effects_already_applied=tuple(effect for effect, _ in side_effect_key_pairs),
            )

        self._seen_event_keys.add(identity.idempotency_key)

        allowed: list[Stage1WebhookSideEffect] = []
        already_applied: list[Stage1WebhookSideEffect] = []
        for effect, side_effect_key in side_effect_key_pairs:
            if side_effect_key in self._seen_side_effect_keys:
                already_applied.append(effect)
                continue

            self._seen_side_effect_keys.add(side_effect_key)
            allowed.append(effect)

        result = (
            Stage1WebhookIdempotencyResult.ACCEPTED_NEW
            if allowed
            else Stage1WebhookIdempotencyResult.ACCEPTED_ALREADY_APPLIED
        )
        return Stage1WebhookIdempotencyDecision(
            result=result,
            identity=identity,
            side_effect_keys=side_effect_key_pairs,
            side_effects_allowed=tuple(allowed),
            side_effects_already_applied=tuple(already_applied),
        )


def build_stage1_webhook_identity(
    provider: Stage1PaymentProvider | str,
    *,
    provider_payment_id: Any,
    raw_status: Any,
    event_type: Any = None,
    provider_event_id: Any = None,
    account_scope: str | None = None,
) -> Stage1WebhookIdentity:
    """Build a canonical webhook identity from known provider fields."""

    provider_enum = _coerce_provider(provider)
    payment_id = _required_text(provider_enum, "provider_payment_id", provider_payment_id)
    status = _required_text(provider_enum, "raw_status", raw_status)

    return Stage1WebhookIdentity(
        provider=provider_enum,
        provider_payment_id=payment_id,
        normalized_status=normalize_provider_status(status),
        event_type=_text_or_none(event_type),
        provider_event_id=_text_or_none(provider_event_id),
        account_scope=account_scope,
    )


def build_stage1_webhook_side_effect_keys(
    identity: Stage1WebhookIdentity,
    side_effects: Sequence[Stage1WebhookSideEffect] = DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS,
) -> tuple[tuple[Stage1WebhookSideEffect, str], ...]:
    """Build hashed side-effect keys independent of provider event retry IDs."""

    return tuple(
        (
            effect,
            _hashed_key(
                "s1:webhook:effect",
                (
                    identity.provider.value,
                    identity.account_scope or "default",
                    identity.provider_payment_id,
                    identity.normalized_status,
                    effect.value,
                ),
            ),
        )
        for effect in side_effects
    )


def extract_stage1_webhook_identity(
    provider: Stage1PaymentProvider | str,
    payload: Mapping[str, Any],
    *,
    account_scope: str | None = None,
) -> Stage1WebhookIdentity:
    """Extract an S1 webhook identity from supported provider payload shapes."""

    provider_enum = _coerce_provider(provider)
    if provider_enum == Stage1PaymentProvider.PAYRAM:
        return _extract_payram_identity(payload, account_scope=account_scope)
    if provider_enum == Stage1PaymentProvider.NOWPAYMENTS:
        return _extract_nowpayments_identity(payload, account_scope=account_scope)
    if provider_enum == Stage1PaymentProvider.CRYPTOBOT:
        return _extract_cryptobot_identity(payload, account_scope=account_scope)
    if provider_enum == Stage1PaymentProvider.TELEGRAM_STARS:
        return _extract_telegram_stars_identity(payload, account_scope=account_scope)
    if provider_enum == Stage1PaymentProvider.DIGISELLER:
        return _extract_digiseller_identity(payload, account_scope=account_scope)
    if provider_enum == Stage1PaymentProvider.YOOKASSA:
        return _extract_yookassa_identity(payload, account_scope=account_scope)

    raise ValueError("Unsupported S1 payment provider")


def _extract_payram_identity(payload: Mapping[str, Any], *, account_scope: str | None) -> Stage1WebhookIdentity:
    return build_stage1_webhook_identity(
        Stage1PaymentProvider.PAYRAM,
        provider_payment_id=_first_value(
            payload,
            "reference_id",
            "referenceID",
            "referenceId",
            "reference",
            "payment_id",
            "paymentID",
            "invoice_id",
            "invoiceID",
            "id",
        ),
        raw_status=_first_value(payload, "payment_state", "paymentState", "status"),
        event_type=_first_value(payload, "event_type", "event"),
        provider_event_id=_first_value(payload, "event_id", "eventID", "webhook_id", "webhookId", "notification_id"),
        account_scope=account_scope,
    )


def _extract_nowpayments_identity(payload: Mapping[str, Any], *, account_scope: str | None) -> Stage1WebhookIdentity:
    return build_stage1_webhook_identity(
        Stage1PaymentProvider.NOWPAYMENTS,
        provider_payment_id=_first_value(payload, "payment_id", "paymentId", "invoice_id", "invoiceId", "order_id"),
        raw_status=_first_value(payload, "payment_status", "paymentStatus", "status"),
        event_type=_first_value(payload, "event_type", "event"),
        provider_event_id=_first_value(payload, "event_id", "ipn_id", "notification_id", "id"),
        account_scope=account_scope,
    )


def _extract_cryptobot_identity(payload: Mapping[str, Any], *, account_scope: str | None) -> Stage1WebhookIdentity:
    invoice = _mapping_or_empty(payload.get("payload"))
    update_type = _first_value(payload, "update_type", "event")
    return build_stage1_webhook_identity(
        Stage1PaymentProvider.CRYPTOBOT,
        provider_payment_id=_first_value(invoice, "invoice_id", "invoiceId") or _first_value(payload, "invoice_id"),
        raw_status=update_type or _first_value(invoice, "status"),
        event_type=update_type,
        provider_event_id=_first_value(payload, "update_id", "id") or _first_value(invoice, "hash"),
        account_scope=account_scope,
    )


def _extract_telegram_stars_identity(payload: Mapping[str, Any], *, account_scope: str | None) -> Stage1WebhookIdentity:
    message = _mapping_or_empty(payload.get("message"))
    successful_payment = _mapping_or_empty(payload.get("successful_payment")) or _mapping_or_empty(
        message.get("successful_payment")
    )
    raw_status = _first_value(payload, "event", "update_type", "status") or (
        "successful_payment" if successful_payment else None
    )
    return build_stage1_webhook_identity(
        Stage1PaymentProvider.TELEGRAM_STARS,
        provider_payment_id=_first_value(successful_payment, "telegram_payment_charge_id", "charge_id"),
        raw_status=raw_status,
        event_type=raw_status,
        provider_event_id=_first_value(payload, "update_id", "id") or _first_value(message, "message_id"),
        account_scope=account_scope,
    )


def _extract_digiseller_identity(payload: Mapping[str, Any], *, account_scope: str | None) -> Stage1WebhookIdentity:
    return build_stage1_webhook_identity(
        Stage1PaymentProvider.DIGISELLER,
        provider_payment_id=_first_value(payload, "invoice_id", "invoiceID", "inv", "id_i", "id", "payment_id"),
        raw_status=_first_value(payload, "status", "payment_status", "paymentStatus"),
        event_type=_first_value(payload, "event_type", "event"),
        provider_event_id=_first_value(payload, "event_id", "notification_id", "id_operation"),
        account_scope=account_scope,
    )


def _extract_yookassa_identity(payload: Mapping[str, Any], *, account_scope: str | None) -> Stage1WebhookIdentity:
    payment_object = _mapping_or_empty(payload.get("object"))
    event = _first_value(payload, "event")
    return build_stage1_webhook_identity(
        Stage1PaymentProvider.YOOKASSA,
        provider_payment_id=_first_value(payment_object, "id") or _first_value(payload, "payment_id", "id"),
        raw_status=event or _first_value(payment_object, "status") or _first_value(payload, "status"),
        event_type=event or _first_value(payload, "type"),
        provider_event_id=_first_value(payload, "notification_id", "event_id"),
        account_scope=account_scope,
    )


def _coerce_provider(provider: Stage1PaymentProvider | str) -> Stage1PaymentProvider:
    if isinstance(provider, Stage1PaymentProvider):
        return provider
    return Stage1PaymentProvider(str(provider))


def _first_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def _required_text(provider: Stage1PaymentProvider, field_name: str, value: Any) -> str:
    text = _text_or_none(value)
    if text is None:
        raise ValueError(f"Missing {field_name} in {provider.value} webhook payload")
    return text


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return None


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _hashed_key(prefix: str, parts: Sequence[str]) -> str:
    key_material = json.dumps(list(parts), ensure_ascii=True, separators=(",", ":"))
    return f"{prefix}:{sha256(key_material.encode('utf-8')).hexdigest()}"
