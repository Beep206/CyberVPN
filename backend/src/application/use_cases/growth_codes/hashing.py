from __future__ import annotations

import hashlib
import hmac

from src.config.settings import settings


def normalize_growth_code_value(raw_code: str) -> str:
    normalized = raw_code.strip()
    if not normalized:
        raise ValueError("Growth code value must not be empty")
    return normalized


def hash_growth_code(raw_code: str) -> str:
    normalized = normalize_growth_code_value(raw_code)
    configured_secret = settings.growth_code_hash_secret.get_secret_value().strip()
    secret = (configured_secret or settings.jwt_secret.get_secret_value()).encode("utf-8")
    return hmac.new(secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def build_growth_code_prefix(raw_code: str) -> str:
    normalized = normalize_growth_code_value(raw_code).upper()
    return normalized[:8]
