"""Utilities for partner attribution tokens, codes, and public URLs."""

from __future__ import annotations

import hashlib
import re
import secrets
from uuid import UUID

PARTNER_ATTRIBUTION_COOKIE_NAME = "cv_partner_attribution"
PARTNER_ATTRIBUTION_TTL_DAYS = 30
PARTNER_ATTRIBUTION_MAX_AGE_SECONDS = PARTNER_ATTRIBUTION_TTL_DAYS * 24 * 60 * 60
PARTNER_ATTRIBUTION_STORAGE_VERSION = 1
PARTNER_PUBLIC_ORIGIN = "https://cyber-vpn.net"
CUSTOMER_PUBLIC_ORIGIN = "https://my.cyber-vpn.net"

_CODE_RE = re.compile(r"^[A-Z0-9_-]{4,30}$")


def normalize_partner_code(code: str) -> str:
    normalized = (code or "").strip().upper()
    if not _CODE_RE.fullmatch(normalized):
        raise ValueError("Partner code must contain 4-30 uppercase letters, digits, underscores or hyphens")
    return normalized


def normalize_optional_partner_code(code: str | None) -> str | None:
    if code is None or not code.strip():
        return None
    return normalize_partner_code(code)


def generate_partner_code(prefix: str = "P") -> str:
    body = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(9))
    return normalize_partner_code(f"{prefix}{body}")


def build_public_token_for_code_id(code_id: UUID) -> str:
    return f"px_{str(code_id).replace('-', '')}"


def hash_partner_attribution_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_share_url(raw_public_token: str) -> str:
    return f"{PARTNER_PUBLIC_ORIGIN}/p/{raw_public_token}"


def build_customer_register_url(transfer_token: str, locale: str = "ru-RU") -> str:
    return f"{CUSTOMER_PUBLIC_ORIGIN}/{locale}/register?pat={transfer_token}"


def mask_partner_code(code: str | None) -> str:
    if not code:
        return "n/a"
    normalized = code.strip()
    if len(normalized) <= 4:
        return normalized[0:1] + "***"
    return f"{normalized[:3]}***{normalized[-2:]}"


def clamp_optional(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped[:max_length]


def generate_transfer_token() -> str:
    return secrets.token_urlsafe(32)
