"""Messaging value objects and validation helpers."""

from __future__ import annotations

import hashlib
from uuid import UUID

MAX_MESSAGE_BODY_CHARS = 4000
MAX_SUBJECT_CHARS = 160
MAX_IDEMPOTENCY_KEY_CHARS = 160


def normalize_message_body(body: str, *, max_chars: int = MAX_MESSAGE_BODY_CHARS) -> str:
    normalized = body.strip()
    if not normalized:
        raise ValueError("Message body is required")
    if len(normalized) > max_chars:
        raise ValueError(f"Message body exceeds {max_chars} characters")
    return normalized


def normalize_subject(subject: str) -> str:
    normalized = " ".join(subject.strip().split())
    if not normalized:
        raise ValueError("Conversation subject is required")
    if len(normalized) > MAX_SUBJECT_CHARS:
        raise ValueError(f"Conversation subject exceeds {MAX_SUBJECT_CHARS} characters")
    return normalized


def build_message_idempotency_key(
    *,
    actor_type: str,
    actor_id: UUID | None,
    conversation_id: UUID,
    client_message_id: str | None,
    header_idempotency_key: str | None = None,
) -> str:
    source = (header_idempotency_key or client_message_id or "").strip()
    if not source:
        raise ValueError("client_message_id or Idempotency-Key is required")

    actor_ref = str(actor_id) if actor_id is not None else "system"
    raw = f"messaging_message:{actor_type}:{actor_ref}:{conversation_id}:{source}"
    if len(raw) <= MAX_IDEMPOTENCY_KEY_CHARS:
        return raw

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"messaging_message:{digest}"


def assert_relative_action_url(action_url: str | None) -> None:
    if action_url is None:
        return
    normalized = action_url.strip()
    if not normalized:
        return
    if not normalized.startswith("/") or normalized.startswith("//") or "://" in normalized:
        raise ValueError("Notification action_url must be a relative application URL")
