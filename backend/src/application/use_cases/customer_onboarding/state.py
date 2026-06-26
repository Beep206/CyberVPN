from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.growth_codes.namespace import mask_customer_input_code, normalize_customer_input_code
from src.config.settings import settings

OnboardingStatus = Literal["disabled", "unavailable", "pending", "completed", "skipped"]

_REGISTRATION_ACCESS_TOKEN_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_ONBOARDING_FLOW_VERSION = "cot1"
_ONBOARDING_FLOW_PURPOSE = "co"
_FLOW_TOKEN_DEFAULT_TTL_SECONDS = 600
_FLOW_TOKEN_MAX_TTL_SECONDS = 900
_FLOW_TOKEN_CLOCK_SKEW_SECONDS = 30
_FLOW_TOKEN_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class CustomerOnboardingUnavailableError(RuntimeError):
    def __init__(self, *, code: str, message_key: str, status_code: int = 503) -> None:
        super().__init__(message_key)
        self.code = code
        self.message_key = message_key
        self.status_code = status_code


class CustomerOnboardingStateRepository(Protocol):
    async def get_current(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
    ) -> CustomerOnboardingCurrentState | None: ...

    async def apply_growth_code(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
        normalized_code: str,
        normalized_code_hash: str,
        masked_code: str,
        idempotency_key: str | None,
        code_applier: CustomerOnboardingCodeApplier | None = None,
    ) -> CustomerOnboardingApplyResult: ...

    async def skip(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
        idempotency_key: str | None,
    ) -> CustomerOnboardingSkipResult: ...


class CustomerOnboardingFlowTokenCodec(Protocol):
    def issue(self, *, user_id: UUID, flow_key: str, version: int) -> str: ...

    def verify(self, *, token: str, user_id: UUID, flow_key: str, version: int) -> None: ...


@dataclass(frozen=True, slots=True)
class CustomerOnboardingAppliedCode:
    result: Literal["accepted", "staged"]
    code_type: Literal["promo", "invite", "gift"]
    message_key: str
    masked_code: str
    next_destination: str = "/dashboard"
    resolved_code_id: UUID | None = None
    growth_code_id: UUID | None = None
    redemption_id: UUID | None = None
    entitlement_grant_id: UUID | None = None
    entitlement_snapshot: dict[str, object] | None = None
    safe_details: dict[str, object] | None = None


class CustomerOnboardingCodeApplier(Protocol):
    async def apply_code(
        self,
        *,
        code: str,
        user_id: UUID,
        idempotency_key: str,
        normalized_code_hash: str,
        masked_code: str,
    ) -> CustomerOnboardingAppliedCode: ...


class CustomerOnboardingFlowTokenService:
    """Signs short-lived onboarding flow tokens without persisting raw token values."""

    def __init__(
        self,
        *,
        secret: str | None = None,
        ttl_seconds: int = _FLOW_TOKEN_DEFAULT_TTL_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        configured_secret = (secret if secret is not None else settings.jwt_secret.get_secret_value()).strip()
        self._secret = configured_secret.encode("utf-8")
        self._ttl_seconds = max(1, min(ttl_seconds, _FLOW_TOKEN_MAX_TTL_SECONDS))
        self._clock = clock

    def issue(self, *, user_id: UUID, flow_key: str, version: int) -> str:
        issued_at = int(self._clock())
        payload = {
            "p": _ONBOARDING_FLOW_PURPOSE,
            "u": str(user_id),
            "f": flow_key,
            "v": version,
            "iat": issued_at,
            "exp": issued_at + self._ttl_seconds,
        }
        payload_part = _base64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature_part = self._sign(f"{_ONBOARDING_FLOW_VERSION}.{payload_part}")
        return f"{_ONBOARDING_FLOW_VERSION}.{payload_part}.{signature_part}"

    def verify(self, *, token: str, user_id: UUID, flow_key: str, version: int) -> None:
        parts = token.strip().split(".")
        if len(parts) != 3:
            raise _flow_token_error()

        token_version, payload_part, signature_part = parts
        if token_version != _ONBOARDING_FLOW_VERSION or not payload_part or not signature_part:
            raise _flow_token_error()
        if not _FLOW_TOKEN_SEGMENT_RE.fullmatch(payload_part) or not _FLOW_TOKEN_SEGMENT_RE.fullmatch(signature_part):
            raise _flow_token_error()

        expected_signature = self._sign(f"{token_version}.{payload_part}")
        if not hmac.compare_digest(signature_part, expected_signature):
            raise _flow_token_error()

        payload = _decode_flow_token_payload(payload_part)
        now = int(self._clock())
        issued_at = _payload_int(payload.get("iat"))
        expires_at = _payload_int(payload.get("exp"))
        token_flow_version = _payload_int(payload.get("v"))
        if (
            payload.get("p") != _ONBOARDING_FLOW_PURPOSE
            or payload.get("u") != str(user_id)
            or payload.get("f") != flow_key
            or token_flow_version != version
            or issued_at is None
            or expires_at is None
            or expires_at <= issued_at
            or expires_at - issued_at > _FLOW_TOKEN_MAX_TTL_SECONDS
            or issued_at > now + _FLOW_TOKEN_CLOCK_SKEW_SECONDS
        ):
            raise _flow_token_error()
        if expires_at < now:
            raise CustomerOnboardingUnavailableError(
                code="CUSTOMER_ONBOARDING_FLOW_TOKEN_EXPIRED",
                message_key="onboarding.flow_token.expired",
                status_code=403,
            )

    def _sign(self, material: str) -> str:
        digest = hmac.new(self._secret, material.encode("ascii"), hashlib.sha256).digest()
        return _base64url_encode(digest)


@dataclass(frozen=True, slots=True)
class CustomerOnboardingCurrentState:
    required: bool
    status: OnboardingStatus
    flow_key: str
    version: int
    allowed_code_types: tuple[str, ...]
    flow_token: str | None = None
    message_key: str = "onboarding.not_required"
    server_state_available: bool = False
    referral_already_attributed: bool = False


@dataclass(frozen=True, slots=True)
class CustomerOnboardingApplyResult:
    status: OnboardingStatus
    message_key: str
    masked_code: str | None = None
    next_destination: str = "/dashboard"
    commit_required: bool = True


@dataclass(frozen=True, slots=True)
class CustomerOnboardingSkipResult:
    status: OnboardingStatus
    message_key: str
    next_destination: str = "/dashboard"
    commit_required: bool = True


class GetCurrentCustomerOnboardingUseCase:
    def __init__(
        self,
        *,
        runtime_config: CustomerOnboardingRuntimeConfig,
        state_repo: CustomerOnboardingStateRepository | None = None,
        flow_tokens: CustomerOnboardingFlowTokenCodec | None = None,
    ) -> None:
        self._runtime = runtime_config
        self._state_repo = state_repo
        self._flow_tokens = flow_tokens

    async def execute(self, *, user_id: UUID) -> CustomerOnboardingCurrentState:
        if not self._runtime.post_registration_code_prompt_enabled:
            return self._disabled()
        if not self._runtime.available or self._state_repo is None:
            return self._unavailable()

        state = await self._state_repo.get_current(
            user_id=user_id,
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
        )
        if state is not None and state.required and state.flow_token is None and self._flow_tokens is not None:
            return CustomerOnboardingCurrentState(
                required=state.required,
                status=state.status,
                flow_key=state.flow_key,
                version=state.version,
                allowed_code_types=state.allowed_code_types,
                flow_token=self._flow_tokens.issue(
                    user_id=user_id,
                    flow_key=self._runtime.flow_key,
                    version=self._runtime.version,
                ),
                message_key=state.message_key,
                server_state_available=state.server_state_available,
                referral_already_attributed=state.referral_already_attributed,
            )
        return state or self._unavailable()

    def _disabled(self) -> CustomerOnboardingCurrentState:
        return CustomerOnboardingCurrentState(
            required=False,
            status="disabled",
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
            allowed_code_types=self._runtime.allowed_code_types,
            message_key="onboarding.disabled",
        )

    def _unavailable(self) -> CustomerOnboardingCurrentState:
        return CustomerOnboardingCurrentState(
            required=False,
            status="unavailable",
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
            allowed_code_types=self._runtime.allowed_code_types,
            message_key="onboarding.state_unavailable",
            server_state_available=False,
        )


class ApplyCustomerOnboardingGrowthCodeUseCase:
    def __init__(
        self,
        *,
        runtime_config: CustomerOnboardingRuntimeConfig,
        state_repo: CustomerOnboardingStateRepository | None = None,
        flow_tokens: CustomerOnboardingFlowTokenCodec | None = None,
    ) -> None:
        self._runtime = runtime_config
        self._state_repo = state_repo
        self._flow_tokens = flow_tokens

    async def execute(
        self,
        *,
        user_id: UUID,
        code: str,
        flow_token: str | None,
        idempotency_key: str | None,
        code_applier: CustomerOnboardingCodeApplier | None = None,
    ) -> CustomerOnboardingApplyResult:
        if _looks_like_registration_access_token(code):
            raise CustomerOnboardingUnavailableError(
                code="REGISTRATION_ACCESS_TOKEN_NOT_ACCEPTED",
                message_key="onboarding.code.registration_access_token_not_accepted",
                status_code=422,
            )
        if not self._runtime.post_registration_code_prompt_enabled:
            return CustomerOnboardingApplyResult(
                status="skipped",
                message_key="onboarding.disabled",
                commit_required=False,
            )
        if not self._runtime.available:
            raise CustomerOnboardingUnavailableError(
                code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
                message_key="onboarding.state_unavailable",
            )
        _require_valid_flow_token(
            flow_tokens=self._flow_tokens,
            flow_token=flow_token,
            user_id=user_id,
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
        )
        if self._state_repo is None:
            raise CustomerOnboardingUnavailableError(
                code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
                message_key="onboarding.state_unavailable",
            )
        normalized = normalize_customer_input_code(code)

        return await self._state_repo.apply_growth_code(
            user_id=user_id,
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
            normalized_code=normalized.normalized_code,
            normalized_code_hash=normalized.code_hash,
            masked_code=mask_customer_input_code(normalized.normalized_code),
            idempotency_key=_normalize_idempotency_key(idempotency_key),
            code_applier=code_applier,
        )


class SkipCustomerOnboardingUseCase:
    def __init__(
        self,
        *,
        runtime_config: CustomerOnboardingRuntimeConfig,
        state_repo: CustomerOnboardingStateRepository | None = None,
        flow_tokens: CustomerOnboardingFlowTokenCodec | None = None,
    ) -> None:
        self._runtime = runtime_config
        self._state_repo = state_repo
        self._flow_tokens = flow_tokens

    async def execute(
        self,
        *,
        user_id: UUID,
        flow_token: str | None,
        idempotency_key: str | None,
    ) -> CustomerOnboardingSkipResult:
        if not self._runtime.post_registration_code_prompt_enabled:
            return CustomerOnboardingSkipResult(
                status="skipped",
                message_key="onboarding.disabled",
                commit_required=False,
            )
        if not self._runtime.available:
            raise CustomerOnboardingUnavailableError(
                code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
                message_key="onboarding.state_unavailable",
            )
        _require_valid_flow_token(
            flow_tokens=self._flow_tokens,
            flow_token=flow_token,
            user_id=user_id,
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
        )
        if self._state_repo is None:
            raise CustomerOnboardingUnavailableError(
                code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
                message_key="onboarding.state_unavailable",
            )

        return await self._state_repo.skip(
            user_id=user_id,
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
        )


def _looks_like_registration_access_token(code: str) -> bool:
    return bool(_REGISTRATION_ACCESS_TOKEN_RE.fullmatch(code.strip()))


def _normalize_idempotency_key(value: str | None) -> str | None:
    normalized = value.strip() if value else None
    if not normalized:
        return None
    return normalized[:120]


def _require_valid_flow_token(
    *,
    flow_tokens: CustomerOnboardingFlowTokenCodec | None,
    flow_token: str | None,
    user_id: UUID,
    flow_key: str,
    version: int,
) -> None:
    normalized = flow_token.strip() if flow_token else ""
    if not normalized:
        raise CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_FLOW_TOKEN_REQUIRED",
            message_key="onboarding.flow_token.required",
            status_code=403,
        )
    if flow_tokens is None:
        raise CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_STATE_UNAVAILABLE",
            message_key="onboarding.state_unavailable",
        )
    flow_tokens.verify(token=normalized, user_id=user_id, flow_key=flow_key, version=version)


def _flow_token_error() -> CustomerOnboardingUnavailableError:
    return CustomerOnboardingUnavailableError(
        code="CUSTOMER_ONBOARDING_FLOW_TOKEN_INVALID",
        message_key="onboarding.flow_token.invalid",
        status_code=403,
    )


def _decode_flow_token_payload(payload_part: str) -> dict[str, object]:
    try:
        raw_payload = _base64url_decode(payload_part)
        decoded = json.loads(raw_payload)
    except (binascii.Error, UnicodeDecodeError, UnicodeEncodeError, ValueError, json.JSONDecodeError) as exc:
        raise _flow_token_error() from exc
    if not isinstance(decoded, dict):
        raise _flow_token_error()
    return decoded


def _payload_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, int):
        return None
    return value


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
