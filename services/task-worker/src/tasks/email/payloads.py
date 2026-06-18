"""Sensitive auth email payload indirection for TaskIQ tasks."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Literal

from redis.asyncio import Redis

from src.config import get_settings

EMAIL_TASK_PAYLOAD_KEY_PREFIX = "cybervpn:email-task-payload:"
EMAIL_TASK_PAYLOAD_SCHEMA_VERSION = 1
EMAIL_TASK_PAYLOAD_CLAIM_TTL_SECONDS = 300

EmailPayloadKind = Literal["otp", "magic_link", "password_reset"]


class EmailTaskPayloadError(RuntimeError):
    """Email task payload reference is invalid, expired, or malformed."""


class EmailTaskPayloadAlreadyClaimedError(EmailTaskPayloadError):
    """Email task payload is already being processed by another worker."""


@dataclass(frozen=True)
class EmailTaskPayload:
    """Sensitive auth email payload resolved from Redis."""

    kind: EmailPayloadKind
    email: str
    locale: str = "en-EN"
    otp_code: str = ""
    token: str = ""
    is_resend: bool = False
    channel: str = "web"


def validate_email_task_payload_ref(payload_ref: str) -> str:
    """Restrict payload resolution to the auth email namespace and UUID keys."""
    if not payload_ref.startswith(EMAIL_TASK_PAYLOAD_KEY_PREFIX):
        msg = "email_task_payload_ref_outside_namespace"
        raise EmailTaskPayloadError(msg)
    ref_id = payload_ref.removeprefix(EMAIL_TASK_PAYLOAD_KEY_PREFIX)
    try:
        uuid.UUID(ref_id)
    except ValueError as exc:
        msg = "email_task_payload_ref_invalid_id"
        raise EmailTaskPayloadError(msg) from exc
    return payload_ref


def _decode_payload(raw_payload: str | bytes | None, *, expected_kind: EmailPayloadKind) -> EmailTaskPayload:
    if raw_payload is None:
        msg = "email_task_payload_missing_or_expired"
        raise EmailTaskPayloadError(msg)

    if isinstance(raw_payload, bytes):
        raw_payload = raw_payload.decode("utf-8")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        msg = "email_task_payload_invalid_json"
        raise EmailTaskPayloadError(msg) from exc

    if not isinstance(payload, dict):
        msg = "email_task_payload_invalid_shape"
        raise EmailTaskPayloadError(msg)
    if payload.get("version") != EMAIL_TASK_PAYLOAD_SCHEMA_VERSION:
        msg = "email_task_payload_invalid_version"
        raise EmailTaskPayloadError(msg)
    if payload.get("kind") != expected_kind:
        msg = "email_task_payload_kind_mismatch"
        raise EmailTaskPayloadError(msg)

    email = str(payload.get("email") or "").strip()
    if not email:
        msg = "email_task_payload_missing_recipient"
        raise EmailTaskPayloadError(msg)

    return EmailTaskPayload(
        kind=expected_kind,
        email=email,
        locale=str(payload.get("locale") or "en-EN"),
        otp_code=str(payload.get("otp_code") or ""),
        token=str(payload.get("token") or ""),
        is_resend=bool(payload.get("is_resend", False)),
        channel=str(payload.get("channel") or "web"),
    )


def _redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def claim_email_task_payload(payload_ref: str) -> None:
    """Claim a payload reference before provider send to prevent duplicate sends."""
    payload_ref = validate_email_task_payload_ref(payload_ref)
    redis = _redis_client()
    try:
        claimed = await redis.set(
            f"{payload_ref}:claim",
            "1",
            ex=EMAIL_TASK_PAYLOAD_CLAIM_TTL_SECONDS,
            nx=True,
        )
    finally:
        await redis.aclose()
    if claimed is not True:
        msg = "email_task_payload_already_claimed"
        raise EmailTaskPayloadAlreadyClaimedError(msg)


async def resolve_email_task_payload(payload_ref: str, *, expected_kind: EmailPayloadKind) -> EmailTaskPayload:
    """Resolve a sensitive email payload by reference."""
    payload_ref = validate_email_task_payload_ref(payload_ref)
    redis = _redis_client()
    try:
        return _decode_payload(await redis.get(payload_ref), expected_kind=expected_kind)
    finally:
        await redis.aclose()


async def consume_email_task_payload(payload_ref: str) -> None:
    """Delete payload and claim after successful provider send."""
    payload_ref = validate_email_task_payload_ref(payload_ref)
    redis = _redis_client()
    try:
        await redis.delete(payload_ref, f"{payload_ref}:claim")
    finally:
        await redis.aclose()


async def release_email_task_payload(payload_ref: str) -> None:
    """Release claim after a failed provider send so retry can use the same secret."""
    payload_ref = validate_email_task_payload_ref(payload_ref)
    redis = _redis_client()
    try:
        await redis.delete(f"{payload_ref}:claim")
    finally:
        await redis.aclose()


def legacy_email_task_payload(
    *,
    kind: EmailPayloadKind,
    email: str,
    locale: str,
    otp_code: str = "",
    token: str = "",
    is_resend: bool = False,
    channel: str = "web",
) -> EmailTaskPayload:
    """Build a payload for pre-hardening in-flight messages and unit tests."""
    return EmailTaskPayload(
        kind=kind,
        email=email,
        locale=locale,
        otp_code=otp_code,
        token=token,
        is_resend=is_resend,
        channel=channel,
    )
