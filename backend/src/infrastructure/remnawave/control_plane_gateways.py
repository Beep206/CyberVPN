"""Fail-closed Remnawave 3.4.3 host and template mutation gateways."""

from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import HTTPException

from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveProtocolError,
    RemnawaveTransportError,
)
from src.infrastructure.remnawave.control_plane_contracts import (
    RemnawaveHostV34Response,
    RemnawaveSubscriptionTemplateV34Response,
)

_HOST_LIST_TO_SCALAR_FIELDS = frozenset(
    {
        "path",
        "sni",
        "host",
        "fingerprint",
        "pinnedPeerCertSha256",
        "verifyPeerCertByName",
    }
)


def _mutation_failure_requires_readback(exc: Exception) -> bool:
    if isinstance(exc, (RemnawaveTransportError, RemnawaveProtocolError)):
        return True
    if isinstance(exc, RemnawaveHTTPStatusError):
        return exc.response.status_code >= 500
    # Response validation happens only after a successful provider response;
    # its stable 502 therefore means the mutation may already have applied.
    return isinstance(exc, HTTPException) and exc.status_code == 502


class RemnawaveHostCreateSafetyDisabled(RuntimeError):
    """Host create is closed until a durable attempt can settle ambiguity."""

    error_code = "remnawave_host_create_safety_disabled"


class RemnawaveHostMutationAcceptedPending(RuntimeError):
    """A host update was not proven against authoritative provider state."""

    error_code = "remnawave_host_mutation_accepted_pending"

    def __init__(self, host_uuid: UUID) -> None:
        self.host_uuid = host_uuid
        super().__init__("Remnawave host update requires authoritative reconciliation")


class RemnawaveSubscriptionTemplateCreateSafetyDisabled(RuntimeError):
    """Template create is closed until a durable attempt can settle ambiguity."""

    error_code = "remnawave_subscription_template_create_safety_disabled"


class RemnawaveSubscriptionTemplateMutationAcceptedPending(RuntimeError):
    """A template update was not proven against authoritative provider state."""

    error_code = "remnawave_subscription_template_mutation_accepted_pending"

    def __init__(self, template_uuid: UUID) -> None:
        self.template_uuid = template_uuid
        super().__init__("Remnawave subscription-template update requires authoritative reconciliation")


class RemnawaveHostControlPlaneGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def create(self, payload: dict[str, Any]) -> NoReturn:
        del payload
        # The target API has neither a caller-supplied immutable identifier nor
        # an idempotency key. Never emit a POST that a caller could replay after
        # a lost response until CyberVPN owns a durable settlement record.
        raise RemnawaveHostCreateSafetyDisabled

    async def update(self, host_uuid: UUID, payload: dict[str, Any]) -> RemnawaveHostV34Response:
        upstream_payload = {"uuid": str(host_uuid), **payload}
        try:
            result = await self._client.patch_validated(
                "/hosts",
                RemnawaveHostV34Response,
                json=upstream_payload,
            )
        except (RemnawaveHTTPStatusError, RemnawaveProtocolError, RemnawaveTransportError, HTTPException) as exc:
            if not _mutation_failure_requires_readback(exc):
                raise
            result = None

        if result is None:
            result = await self._readback(host_uuid)

        self._require_postcondition(result, host_uuid=host_uuid, payload=upstream_payload)
        return result

    async def _readback(self, host_uuid: UUID) -> RemnawaveHostV34Response:
        try:
            return await self._client.get_validated(f"/hosts/{host_uuid}", RemnawaveHostV34Response)
        except (RemnawaveHTTPStatusError, RemnawaveProtocolError, RemnawaveTransportError, HTTPException) as exc:
            raise RemnawaveHostMutationAcceptedPending(host_uuid) from exc

    @staticmethod
    def _require_postcondition(
        result: RemnawaveHostV34Response,
        *,
        host_uuid: UUID,
        payload: dict[str, Any],
    ) -> None:
        observed = result.model_dump(by_alias=True, mode="json", exclude_unset=True)
        if result.uuid != host_uuid:
            raise RemnawaveHostMutationAcceptedPending(host_uuid)

        for field, expected in payload.items():
            if field == "uuid":
                continue
            if field not in observed:
                raise RemnawaveHostMutationAcceptedPending(host_uuid)
            if field in _HOST_LIST_TO_SCALAR_FIELDS:
                expected = ",".join(expected) if expected else None
            if observed[field] != expected:
                raise RemnawaveHostMutationAcceptedPending(host_uuid)


class RemnawaveSubscriptionTemplateControlPlaneGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def create(self, payload: dict[str, Any]) -> NoReturn:
        del payload
        raise RemnawaveSubscriptionTemplateCreateSafetyDisabled

    async def update(
        self,
        template_uuid: UUID,
        payload: dict[str, Any],
    ) -> RemnawaveSubscriptionTemplateV34Response:
        upstream_payload = {"uuid": str(template_uuid), **payload}
        try:
            result = await self._client.patch_validated(
                "/subscription-templates",
                RemnawaveSubscriptionTemplateV34Response,
                json=upstream_payload,
            )
        except (RemnawaveHTTPStatusError, RemnawaveProtocolError, RemnawaveTransportError, HTTPException) as exc:
            if not _mutation_failure_requires_readback(exc):
                raise
            result = None

        if result is None:
            result = await self._readback(template_uuid)

        self._require_postcondition(result, template_uuid=template_uuid, payload=upstream_payload)
        return result

    async def _readback(self, template_uuid: UUID) -> RemnawaveSubscriptionTemplateV34Response:
        try:
            return await self._client.get_validated(
                f"/subscription-templates/{template_uuid}",
                RemnawaveSubscriptionTemplateV34Response,
            )
        except (RemnawaveHTTPStatusError, RemnawaveProtocolError, RemnawaveTransportError, HTTPException) as exc:
            raise RemnawaveSubscriptionTemplateMutationAcceptedPending(template_uuid) from exc

    @staticmethod
    def _require_postcondition(
        result: RemnawaveSubscriptionTemplateV34Response,
        *,
        template_uuid: UUID,
        payload: dict[str, Any],
    ) -> None:
        observed = result.model_dump(by_alias=True, mode="json", exclude_unset=True)
        if result.uuid != template_uuid:
            raise RemnawaveSubscriptionTemplateMutationAcceptedPending(template_uuid)

        for field, expected in payload.items():
            if field == "uuid":
                continue
            if field not in observed or observed[field] != expected:
                raise RemnawaveSubscriptionTemplateMutationAcceptedPending(template_uuid)
