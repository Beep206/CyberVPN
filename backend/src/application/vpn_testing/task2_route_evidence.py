"""Task2 selected-outbound route evidence collector store."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator
from redis.exceptions import RedisError

from src.shared.async_compat import resolve_maybe_awaitable

TASK2_XRAY_WEBHOOK_SECRET_HEADER = "X-CyberVPN-Task2-Xray-Webhook-Secret"  # noqa: S105

TASK2_ROUTE_EVIDENCE_EXPECTATION_PREFIX = "vpn_tester:premium_spb_de_exceptions_v1:task2_route_evidence:expectation:"
TASK2_ROUTE_EVIDENCE_RESULT_PREFIX = "vpn_tester:premium_spb_de_exceptions_v1:task2_route_evidence:result:"
TASK2_ROUTE_EVIDENCE_TARGET_DIGEST_CONTEXT = "cybervpn-task2-route-evidence-target:v1"
TASK2_ROUTE_EVIDENCE_RESULT_DIGEST_CONTEXT = "cybervpn-task2-route-evidence-result:v1"

TASK2_ROUTE_EVIDENCE_ALLOWED_INBOUND_TAGS = frozenset(
    {
        "SPB_EXCEPTIONS_REALITY_443",
        "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
    }
)
TASK2_ROUTE_EVIDENCE_ALLOWED_NETWORKS = frozenset({"tcp", "udp"})
TASK2_ROUTE_EVIDENCE_ALLOWED_OUTBOUNDS = frozenset({"DE_EXCEPTIONS_BRIDGE", "DIRECT", "BLOCK"})

_SAFE_KEY_PATTERN = r"^[A-Za-z0-9_.:-]+$"
_HMAC_SHA256_PATTERN = r"^[a-f0-9]{64}$"


class Task2RouteEvidenceRejected(Exception):
    """Webhook evidence was invalid or could not be correlated safely."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Task2RouteEvidenceUnavailable(Exception):
    """Evidence store is unavailable; callers must fail closed."""


class _RedisStore(Protocol):
    def delete(self, *names: str) -> Any: ...

    def get(self, name: str) -> Any: ...

    def getdel(self, name: str) -> Any: ...

    def set(self, name: str, value: str, *, ex: int, nx: bool = False) -> Any: ...


class Task2RouteEvidenceExpectation(BaseModel):
    """One-shot expectation keyed by target digest, with no raw route target."""

    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str = Field(..., min_length=1, max_length=80, pattern=_SAFE_KEY_PATTERN)
    route_key: str = Field(..., min_length=1, max_length=120, pattern=_SAFE_KEY_PATTERN)
    target_digest: str = Field(..., pattern=_HMAC_SHA256_PATTERN)
    expected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT", "BLOCK"]
    expected_inbound_tag: Literal[
        "SPB_EXCEPTIONS_REALITY_443",
        "SPB_EXCEPTIONS_XHTTP_REALITY_8443",
    ]
    expected_network: Literal["tcp", "udp"]


class Task2RouteEvidenceResult(BaseModel):
    """Persisted safe selected-outbound evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str = Field(..., min_length=1, max_length=80, pattern=_SAFE_KEY_PATTERN)
    route_key: str = Field(..., min_length=1, max_length=120, pattern=_SAFE_KEY_PATTERN)
    selected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT", "BLOCK"]
    verdict: Literal["pass", "fail"]
    digest: str = Field(..., pattern=_HMAC_SHA256_PATTERN)


class Task2XrayRoutingWebhook(BaseModel):
    """Official Xray routing webhook payload accepted for Task2 evidence."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, strict=True)

    email: str | None = Field(default=None, max_length=128)
    level: int | None = None
    protocol: str | None = Field(default=None, max_length=32)
    network: str = Field(..., min_length=1, max_length=8)
    source: str | None = Field(default=None, max_length=256)
    destination: str = Field(..., min_length=1, max_length=256)
    route_target: str | None = Field(default=None, alias="routeTarget", max_length=256)
    original_target: str | None = Field(default=None, alias="originalTarget", max_length=256)
    inbound_tag: str | None = Field(default=None, alias="inboundTag", max_length=120)
    inbound_name: str | None = Field(default=None, alias="inboundName", max_length=120)
    inbound_local: str | None = Field(default=None, alias="inboundLocal", max_length=256)
    outbound_tag: str | None = Field(default=None, alias="outboundTag", max_length=120)
    ts: int = Field(..., ge=0)

    @field_validator(
        "email",
        "protocol",
        "network",
        "source",
        "destination",
        "route_target",
        "original_target",
        "inbound_tag",
        "inbound_name",
        "inbound_local",
        "outbound_tag",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("network", mode="after")
    @classmethod
    def normalize_network(cls, value: str) -> str:
        return value.lower()

    def correlation_target(self) -> str:
        for value in (self.original_target, self.destination, self.route_target):
            if value:
                return value
        raise Task2RouteEvidenceRejected("missing_target")

    def timestamp_seconds(self) -> int:
        return self.ts


def task2_route_evidence_target_digest(webhook_secret: str, target: str) -> str:
    """Return an HMAC digest for correlating a raw target without storing it."""

    secret = webhook_secret.strip()
    target_value = target.strip()
    if not secret:
        raise Task2RouteEvidenceUnavailable("missing_webhook_secret")
    if not target_value:
        raise Task2RouteEvidenceRejected("missing_target")
    payload = f"{TASK2_ROUTE_EVIDENCE_TARGET_DIGEST_CONTEXT}\n{target_value}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def task2_route_evidence_result_digest(
    webhook_secret: str,
    *,
    run_id: str,
    route_key: str,
    selected_outbound: str,
    verdict: str,
    target_digest: str,
) -> str:
    """Return the stored evidence digest over only allowlisted safe fields."""

    secret = webhook_secret.strip()
    if not secret:
        raise Task2RouteEvidenceUnavailable("missing_webhook_secret")
    payload = json.dumps(
        {
            "context": TASK2_ROUTE_EVIDENCE_RESULT_DIGEST_CONTEXT,
            "route_key": route_key,
            "run_id": run_id,
            "selected_outbound": selected_outbound,
            "target_digest": target_digest,
            "verdict": verdict,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class Task2RouteEvidenceStore:
    """Redis-backed one-shot expectation/result store for Task2 route evidence."""

    def __init__(
        self,
        redis_client: _RedisStore,
        *,
        expectation_ttl_seconds: int,
        result_ttl_seconds: int,
        webhook_secret: str,
    ) -> None:
        self._redis = redis_client
        self._expectation_ttl_seconds = expectation_ttl_seconds
        self._result_ttl_seconds = result_ttl_seconds
        self._webhook_secret = webhook_secret.strip()

    async def create_expectation(self, expectation: Task2RouteEvidenceExpectation) -> None:
        key = self.expectation_key(expectation.target_digest)
        payload = expectation.model_dump_json()
        try:
            await resolve_maybe_awaitable(
                self._redis.delete(self.result_key(expectation.run_id, expectation.target_digest))
            )
            stored = await resolve_maybe_awaitable(
                self._redis.set(key, payload, ex=self._expectation_ttl_seconds, nx=True)
            )
        except RedisError as exc:
            raise Task2RouteEvidenceUnavailable("redis_unavailable") from exc
        if not stored:
            raise Task2RouteEvidenceRejected("expectation_already_exists")

    async def delete_expectations(self, target_digests: list[str]) -> None:
        if not target_digests:
            return
        try:
            await resolve_maybe_awaitable(
                self._redis.delete(*(self.expectation_key(digest) for digest in target_digests))
            )
        except RedisError as exc:
            raise Task2RouteEvidenceUnavailable("redis_unavailable") from exc

    async def get_result_for_target_digest(
        self,
        run_id: str,
        target_digest: str,
    ) -> Task2RouteEvidenceResult | None:
        try:
            raw = await resolve_maybe_awaitable(self._redis.get(self.result_key(run_id, target_digest)))
        except RedisError as exc:
            raise Task2RouteEvidenceUnavailable("redis_unavailable") from exc
        if raw is None:
            return None
        return Task2RouteEvidenceResult.model_validate_json(raw)

    async def record_xray_routing_webhook(
        self,
        webhook: Task2XrayRoutingWebhook,
        *,
        synthetic_user: str,
        max_skew_seconds: int,
        now_epoch_seconds: int,
    ) -> Task2RouteEvidenceResult:
        self._validate_webhook(
            webhook,
            synthetic_user=synthetic_user,
            max_skew_seconds=max_skew_seconds,
            now=now_epoch_seconds,
        )

        target_digest = task2_route_evidence_target_digest(self._webhook_secret, webhook.correlation_target())
        expectation_key = self.expectation_key(target_digest)
        try:
            expectation_raw = await resolve_maybe_awaitable(self._redis.getdel(expectation_key))
        except RedisError as exc:
            raise Task2RouteEvidenceUnavailable("redis_unavailable") from exc
        if expectation_raw is None:
            raise Task2RouteEvidenceRejected("expectation_not_found")

        expectation = Task2RouteEvidenceExpectation.model_validate_json(expectation_raw)
        if not hmac.compare_digest(expectation.target_digest, target_digest):
            raise Task2RouteEvidenceRejected("expectation_digest_mismatch")
        if webhook.inbound_tag != expectation.expected_inbound_tag:
            raise Task2RouteEvidenceRejected("expectation_inbound_mismatch")
        if webhook.network != expectation.expected_network:
            raise Task2RouteEvidenceRejected("expectation_network_mismatch")

        selected_outbound_raw = webhook.outbound_tag
        if selected_outbound_raw is None:
            raise Task2RouteEvidenceRejected("missing_outbound")
        selected_outbound = cast(Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT", "BLOCK"], selected_outbound_raw)
        verdict: Literal["pass", "fail"] = "pass" if selected_outbound == expectation.expected_outbound else "fail"
        digest = task2_route_evidence_result_digest(
            self._webhook_secret,
            run_id=expectation.run_id,
            route_key=expectation.route_key,
            selected_outbound=selected_outbound,
            verdict=verdict,
            target_digest=target_digest,
        )
        result = Task2RouteEvidenceResult(
            run_id=expectation.run_id,
            route_key=expectation.route_key,
            selected_outbound=selected_outbound,
            verdict=verdict,
            digest=digest,
        )
        try:
            stored = await resolve_maybe_awaitable(
                self._redis.set(
                    self.result_key(expectation.run_id, target_digest),
                    result.model_dump_json(),
                    ex=self._result_ttl_seconds,
                    nx=True,
                )
            )
        except RedisError as exc:
            raise Task2RouteEvidenceUnavailable("redis_unavailable") from exc
        if not stored:
            raise Task2RouteEvidenceRejected("result_already_exists")
        return result

    @staticmethod
    def expectation_key(target_digest: str) -> str:
        return f"{TASK2_ROUTE_EVIDENCE_EXPECTATION_PREFIX}{target_digest}"

    @staticmethod
    def result_key(run_id: str, target_digest: str) -> str:
        return f"{TASK2_ROUTE_EVIDENCE_RESULT_PREFIX}{run_id}:{target_digest}"

    @staticmethod
    def _validate_webhook(
        webhook: Task2XrayRoutingWebhook,
        *,
        synthetic_user: str,
        max_skew_seconds: int,
        now: int,
    ) -> None:
        configured_synthetic_user = synthetic_user.strip()
        if not configured_synthetic_user or webhook.email is None:
            raise Task2RouteEvidenceRejected("invalid_synthetic_user")
        if not hmac.compare_digest(webhook.email, configured_synthetic_user):
            raise Task2RouteEvidenceRejected("invalid_synthetic_user")

        skew = webhook.timestamp_seconds() - now
        if skew < -max_skew_seconds or skew > max_skew_seconds:
            raise Task2RouteEvidenceRejected("timestamp_out_of_window")
        if webhook.inbound_tag not in TASK2_ROUTE_EVIDENCE_ALLOWED_INBOUND_TAGS:
            raise Task2RouteEvidenceRejected("invalid_inbound")
        if webhook.network not in TASK2_ROUTE_EVIDENCE_ALLOWED_NETWORKS:
            raise Task2RouteEvidenceRejected("invalid_network")
        if webhook.outbound_tag not in TASK2_ROUTE_EVIDENCE_ALLOWED_OUTBOUNDS:
            raise Task2RouteEvidenceRejected("invalid_outbound")
