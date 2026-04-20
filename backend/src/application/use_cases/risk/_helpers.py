from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

from src.config.settings import settings
from src.domain.enums import RiskIdentifierType, RiskLinkType

_BLOCKING_IDENTIFIER_TYPES = {
    RiskIdentifierType.EMAIL.value,
    RiskIdentifierType.DEVICE_ID.value,
    RiskIdentifierType.TELEGRAM_ID.value,
    RiskIdentifierType.PAYMENT_FINGERPRINT.value,
}


def normalize_identifier_value(*, identifier_type: RiskIdentifierType, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Risk identifier value must not be empty")

    if identifier_type in {
        RiskIdentifierType.EMAIL,
        RiskIdentifierType.DEVICE_ID,
        RiskIdentifierType.PAYMENT_FINGERPRINT,
    }:
        return normalized.lower()
    if identifier_type == RiskIdentifierType.TELEGRAM_ID:
        return normalized.removeprefix("@").strip().lower()
    return normalized


def hash_identifier_value(value: str) -> str:
    secret = settings.jwt_secret.get_secret_value().encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


def build_value_preview(*, identifier_type: RiskIdentifierType, value: str) -> str:
    if identifier_type == RiskIdentifierType.EMAIL and "@" in value:
        local_part, domain = value.split("@", 1)
        masked_local = local_part[:1] + "***" if local_part else "***"
        return f"{masked_local}@{domain}"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def derive_link_type(identifier_type: RiskIdentifierType) -> RiskLinkType:
    return {
        RiskIdentifierType.EMAIL: RiskLinkType.SHARED_EMAIL,
        RiskIdentifierType.DEVICE_ID: RiskLinkType.SHARED_DEVICE_ID,
        RiskIdentifierType.TELEGRAM_ID: RiskLinkType.SHARED_TELEGRAM_ID,
        RiskIdentifierType.PAYMENT_FINGERPRINT: RiskLinkType.SHARED_PAYMENT_FINGERPRINT,
        RiskIdentifierType.IP_ADDRESS: RiskLinkType.SHARED_IP_ADDRESS,
    }[identifier_type]


def canonical_subject_pair(left_subject_id: UUID, right_subject_id: UUID) -> tuple[UUID, UUID]:
    if str(left_subject_id) <= str(right_subject_id):
        return left_subject_id, right_subject_id
    return right_subject_id, left_subject_id


def is_blocking_identifier_type(identifier_type: str) -> bool:
    return identifier_type in _BLOCKING_IDENTIFIER_TYPES


def reason_code_for_identifier(identifier_type: str) -> str:
    return f"shared_{identifier_type}_link_detected"

