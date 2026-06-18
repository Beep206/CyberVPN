"""Privacy helpers for auth email observability."""

import hashlib


def recipient_log_fields(email: str) -> dict[str, str]:
    """Return non-reversible recipient identifiers safe for structured logs."""
    normalized = email.strip().lower()
    domain = normalized.rsplit("@", 1)[1] if "@" in normalized else "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "recipient_hash": digest[:16],
        "recipient_domain": domain or "unknown",
    }
