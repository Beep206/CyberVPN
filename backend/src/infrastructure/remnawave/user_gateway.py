import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from httpx import HTTPStatusError

from src.config.settings import settings
from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.client import RemnawaveClient, RemnawaveTransportError
from src.infrastructure.remnawave.contracts import (
    RemnawaveCursorPage,
    RemnawaveDeleteResponse,
    RemnawaveRawSquadResponse,
    RemnawaveUserResponse,
)
from src.infrastructure.remnawave.mappers.user_mapper import map_remnawave_user
from src.infrastructure.remnawave.response_validator import response_validator

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_EMAIL_PLACEHOLDER_SUFFIXES = (".local", ".localhost")


class RemnawaveIdentityBindingError(RuntimeError):
    """The upstream response does not match the canonical requested identity."""


class RemnawaveInventoryPaginationError(RuntimeError):
    """The upstream user inventory cursor cannot prove forward progress."""


class RemnawaveMutationAcceptedPending(RuntimeError):
    """A mutation was accepted but its requested postcondition is unproven."""

    def __init__(self, *, operation: str, numeric_user_id: int | None = None) -> None:
        self.operation = operation
        self.numeric_user_id = numeric_user_id
        super().__init__(f"Remnawave {operation} was accepted and requires reconciliation")


class RemnawaveDefaultSquadResolutionError(RuntimeError):
    """The required exact default internal squad could not be resolved."""


class RemnawavePasswordOnlyCredentialRotationSafetyDisabled(RuntimeError):
    """Password-only rotation has no authoritative postcondition or receipt."""


class RemnawaveUserGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client
        self._default_internal_squad_uuids: list[str] | None = None

    @staticmethod
    def _dump_validated_model(data: Any) -> dict[str, Any]:
        try:
            # Presence matters for mutation postconditions: a defaulted None
            # must not masquerade as an observed relationship field.
            return data.model_dump(by_alias=True, mode="json", exclude_unset=True)
        except TypeError:
            # Lightweight test doubles and the isolated rollback fixture expose
            # the older two-argument model_dump contract.
            return data.model_dump(by_alias=True, mode="json")

    async def _resolve_default_internal_squad_uuids(self) -> list[str]:
        if self._default_internal_squad_uuids is not None:
            return self._default_internal_squad_uuids

        configured_uuid = settings.remnawave_default_internal_squad_uuid.strip()
        if configured_uuid:
            try:
                configured_uuid = str(UUID(configured_uuid))
            except ValueError as exc:
                raise RemnawaveDefaultSquadResolutionError(
                    "Configured Remnawave default internal squad UUID is invalid"
                ) from exc
            self._default_internal_squad_uuids = [configured_uuid]
            return self._default_internal_squad_uuids

        configured_name = settings.remnawave_default_internal_squad_name.strip() or "Default-Squad"

        try:
            squads = await self._client.get_collection_validated(
                "/internal-squads",
                "internalSquads",
                RemnawaveRawSquadResponse,
            )
        except Exception as exc:
            logger.warning(
                "Failed to fetch Remnawave internal squads",
                extra={"error_type": type(exc).__name__},
            )
            raise RemnawaveDefaultSquadResolutionError(
                "Required Remnawave default internal squad inventory is unavailable"
            ) from exc

        named_match = [str(squad.uuid) for squad in squads if squad.uuid and squad.name == configured_name]
        if len(named_match) == 1:
            self._default_internal_squad_uuids = named_match
            return self._default_internal_squad_uuids
        if len(named_match) > 1:
            raise RemnawaveDefaultSquadResolutionError("Required Remnawave default internal squad name is ambiguous")
        raise RemnawaveDefaultSquadResolutionError(
            "Required Remnawave default internal squad was not found by exact name"
        )

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        """Rollback-only Remnawave 2.x lookup by UUID."""
        try:
            data = await self._client.get_validated(f"/api/users/{uuid}", RemnawaveUserResponse)
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        user = map_remnawave_user(self._dump_validated_model(data))
        if user.uuid != uuid:
            raise RemnawaveIdentityBindingError("Remnawave UUID response does not match the requested user")
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Remnawave numeric user id must be positive")
        try:
            data = await self._client.get_validated(f"/api/users/{user_id}", RemnawaveUserResponse)
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        user = map_remnawave_user(self._dump_validated_model(data))
        self._validate_user_binding(user, numeric_id=user_id)
        return user

    async def confirm_absent_by_id(self, user_id: int) -> bool:
        """Authoritatively confirm a numeric user is absent after an ambiguous delete."""

        if isinstance(user_id, bool) or user_id <= 0:
            raise ValueError("Remnawave numeric user id must be positive")
        try:
            data = await self._client.get_validated(f"/api/users/{user_id}", RemnawaveUserResponse)
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return True
            raise
        user = map_remnawave_user(self._dump_validated_model(data))
        self._validate_user_binding(user, numeric_id=user_id)
        return False

    async def get_by_ref(self, ref: RemnawaveUserRef) -> User | None:
        if ref.id is not None:
            user = await self.get_by_id(ref.id)
            if user is not None:
                self._validate_user_binding(user, numeric_id=ref.id, legacy_uuid=ref.legacy_uuid)
            return user
        if ref.legacy_uuid is not None:
            return await self.get_by_uuid(ref.legacy_uuid)
        return None

    async def get_by_username(self, username: str) -> User | None:
        try:
            data = await self._client.get_validated(f"/api/users/by-username/{username}", RemnawaveUserResponse)
            return map_remnawave_user(self._dump_validated_model(data))
        except Exception as exc:
            logger.warning(
                "Failed to fetch Remnawave user by username",
                extra={"error_type": type(exc).__name__},
            )
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        try:
            raw = await self._client.get(f"/api/users/by-telegram-id/{telegram_id}")
            if raw == []:
                return None
            if isinstance(raw, list):
                if len(raw) > 1:
                    raise RemnawaveIdentityBindingError("Remnawave Telegram lookup is not unique")
                raw = raw[0] if raw else None
                if raw is None:
                    return None
            data = response_validator.validate_single(
                raw,
                RemnawaveUserResponse,
                f"GET /api/users/by-telegram-id/{telegram_id}",
            )
            user = map_remnawave_user(self._dump_validated_model(data))
            if user.telegram_id != telegram_id:
                raise RemnawaveIdentityBindingError("Remnawave Telegram response does not match the lookup")
            return user
        except RemnawaveIdentityBindingError:
            raise
        except Exception as exc:
            logger.warning(
                "Failed to fetch Remnawave user by Telegram identity",
                extra={"error_type": type(exc).__name__},
            )
            return None

    async def get_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        if offset == 0:
            return await self.get_all_cursor(limit=limit)

        users = await self._client.get_collection_validated(
            "/api/users",
            "users",
            RemnawaveUserResponse,
            params={"start": offset, "size": limit},
        )
        return [map_remnawave_user(self._dump_validated_model(user)) for user in users]

    async def get_all_cursor_page(self, cursor: str | None = None, limit: int = 1000) -> RemnawaveCursorPage:
        return await self._client.get_all_users_cursor_page(cursor=cursor, limit=limit)

    async def get_all_cursor(self, *, cursor: str | None = None, limit: int = 1000) -> list[User]:
        collected: list[User] = []
        seen: set[str] = set()
        requested_cursors: set[str] = set()
        next_cursor = cursor
        page_limit = max(1, min(int(limit), 1000))

        while len(collected) < limit:
            requested_cursor = next_cursor
            if requested_cursor is not None:
                if requested_cursor in requested_cursors:
                    raise RemnawaveInventoryPaginationError("Remnawave user inventory cursor was repeated")
                requested_cursors.add(requested_cursor)

            collected_before_page = len(collected)
            page = await self.get_all_cursor_page(cursor=requested_cursor, limit=page_limit)
            for item in page.items:
                mapped = map_remnawave_user(item)
                unique_key = str(mapped.remnawave_id or mapped.uuid or mapped.username)
                if unique_key in seen:
                    continue
                seen.add(unique_key)
                collected.append(mapped)
                if len(collected) >= limit:
                    break

            if page.has_next_page is False:
                break
            if not page.items:
                if page.has_next_page is True:
                    raise RemnawaveInventoryPaginationError(
                        "Remnawave user inventory advertised another page without inventory rows"
                    )
                break

            candidate_cursor = page.next_cursor
            if not candidate_cursor:
                if page.has_next_page is True:
                    raise RemnawaveInventoryPaginationError(
                        "Remnawave user inventory advertised another page without a cursor"
                    )
                break
            if candidate_cursor == requested_cursor or candidate_cursor in requested_cursors:
                raise RemnawaveInventoryPaginationError("Remnawave user inventory cursor did not advance")
            if len(collected) == collected_before_page:
                raise RemnawaveInventoryPaginationError("Remnawave user inventory page made no unique progress")
            next_cursor = candidate_cursor

        return collected

    @staticmethod
    def _normalize_user_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(raw_payload)

        field_mapping = {
            "expire_at": "expireAt",
            "telegram_id": "telegramId",
            "data_limit": "trafficLimitBytes",
            "traffic_limit_bytes": "trafficLimitBytes",
            "hwid_device_limit": "hwidDeviceLimit",
            "external_squad_uuid": "externalSquadUuid",
            "active_internal_squads": "activeInternalSquads",
        }

        for source, target in field_mapping.items():
            if source in payload and target not in payload:
                payload[target] = payload.pop(source)

        expire_at = payload.get("expireAt")
        if isinstance(expire_at, datetime):
            payload["expireAt"] = expire_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

        if "status" in payload:
            raw_status = payload["status"]
            status_value = raw_status.value if isinstance(raw_status, UserStatus) else str(raw_status)
            normalized_status = status_value.strip().upper()
            if normalized_status not in {status.value.upper() for status in UserStatus}:
                raise ValueError("Remnawave user status is invalid")
            payload["status"] = normalized_status

        if "telegramId" in payload:
            raw_telegram_ids = payload["telegramId"]
            if raw_telegram_ids is None:
                payload.pop("telegramId")
            elif isinstance(raw_telegram_ids, int) and not isinstance(raw_telegram_ids, bool):
                payload["telegramId"] = [raw_telegram_ids]
            elif not (
                isinstance(raw_telegram_ids, list)
                and len(raw_telegram_ids) == 1
                and isinstance(raw_telegram_ids[0], int)
                and not isinstance(raw_telegram_ids[0], bool)
            ):
                raise ValueError("CyberVPN requires exactly one numeric Remnawave Telegram identity")

        if "email" in payload:
            payload["email"] = RemnawaveUserGateway._normalize_remnawave_email(
                str(payload.get("email") or ""),
                fallback_source=str(payload.get("username") or payload.get("uuid") or "user"),
            )

        # Remnawave treats a missing trafficLimitBytes as unlimited, but rejects
        # an explicit JSON null for this field.
        if payload.get("trafficLimitBytes") is None:
            payload.pop("trafficLimitBytes", None)

        # Remnawave generates protocol secrets itself; our local password field is not part
        # of the upstream contract.
        payload.pop("password", None)
        # Billing consent is owned by CyberVPN. Remnawave 3.4.x removed autoRenew
        # from create/update user request contracts, so never send either legacy spelling.
        payload.pop("auto_renew", None)
        payload.pop("autoRenew", None)
        payload.pop("allow_missing_expire_at", None)
        payload.pop("lifetime_expiry_mode", None)
        payload.pop("lifetime_expire_at", None)

        return payload

    @staticmethod
    def _normalize_remnawave_email(email: str, *, fallback_source: str) -> str:
        normalized = email.strip().lower()
        domain = normalized.rsplit("@", 1)[-1] if "@" in normalized else ""
        if _EMAIL_RE.match(normalized) and not domain.endswith(_EMAIL_PLACEHOLDER_SUFFIXES):
            return normalized

        safe_local_part = re.sub(r"[^a-z0-9._-]+", "-", fallback_source.strip().lower())
        safe_local_part = safe_local_part.strip(".-_")[:48] or "user"
        return f"{safe_local_part}@cyber-vpn.net"

    @staticmethod
    def _build_default_expire_at() -> str:
        expires_at = datetime.now(UTC) + timedelta(days=settings.remnawave_default_user_expire_days)
        return expires_at.isoformat().replace("+00:00", "Z")

    async def create(self, username: str, **kwargs) -> User:
        allow_missing_expire_at = bool(kwargs.get("allow_missing_expire_at"))
        payload = self._normalize_user_payload({"username": username, **kwargs})
        if not payload.get("expireAt") and not allow_missing_expire_at:
            payload["expireAt"] = self._build_default_expire_at()
        if not payload.get("activeInternalSquads"):
            default_internal_squad_uuids = await self._resolve_default_internal_squad_uuids()
            payload["activeInternalSquads"] = default_internal_squad_uuids
        try:
            data = await self._client.post_validated("/api/users", RemnawaveUserResponse, json=payload)
        except RemnawaveTransportError as exc:
            # There is no canonical identifier with which to reconcile a
            # potentially accepted create. Never search by mutable metadata or
            # replay the POST.
            raise RemnawaveMutationAcceptedPending(operation="create") from exc
        if data is None:
            # A create has no trustworthy lookup key until the provider
            # returns its numeric identity. Never retry or search by mutable
            # username/Telegram metadata after an ambiguous acceptance.
            raise RemnawaveMutationAcceptedPending(operation="create")
        user = map_remnawave_user(self._dump_validated_model(data))
        if user.username != username:
            raise RemnawaveIdentityBindingError("Remnawave create response does not match the requested user")
        numeric_id = self._validate_complete_created_identity(user)
        self._require_mutation_postcondition(
            user,
            payload=payload,
            numeric_id=numeric_id,
            operation="create",
            require_all_observable=False,
        )
        return user

    @staticmethod
    def _require_numeric_identifier(user_ref: int | RemnawaveUserRef) -> int:
        identifier = user_ref.require_numeric_id() if isinstance(user_ref, RemnawaveUserRef) else user_ref
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
            raise ValueError("Remnawave 3.x mutations require a reconciled numeric user id")
        return identifier

    async def update(self, user_ref: int | RemnawaveUserRef, **kwargs) -> User:
        numeric_id = self._require_numeric_identifier(user_ref)
        expected_legacy_uuid = user_ref.legacy_uuid if isinstance(user_ref, RemnawaveUserRef) else None
        await self._require_existing_target(numeric_id=numeric_id, legacy_uuid=expected_legacy_uuid)
        mutation_fields = dict(kwargs)
        mutation_fields.pop("id", None)
        mutation_fields.pop("uuid", None)
        payload = self._normalize_user_payload({**mutation_fields, "id": numeric_id})
        try:
            data = await self._client.patch_validated("/api/users", RemnawaveUserResponse, json=payload)
        except RemnawaveTransportError:
            return await self._reconcile_accepted_known_target(
                operation="update",
                numeric_id=numeric_id,
                legacy_uuid=expected_legacy_uuid,
                expected_update_payload=payload,
            )
        if data is None:
            return await self._reconcile_accepted_known_target(
                operation="update",
                numeric_id=numeric_id,
                legacy_uuid=expected_legacy_uuid,
                expected_update_payload=payload,
            )
        user = map_remnawave_user(self._dump_validated_model(data))
        self._validate_user_binding(user, numeric_id=numeric_id, legacy_uuid=expected_legacy_uuid)
        self._require_mutation_postcondition(
            user,
            payload=payload,
            numeric_id=numeric_id,
            require_all_observable=False,
        )
        return user

    async def revoke_subscription(
        self,
        user_ref: int | RemnawaveUserRef,
        *,
        revoke_only_passwords: bool = False,
    ) -> User:
        if revoke_only_passwords:
            raise RemnawavePasswordOnlyCredentialRotationSafetyDisabled(
                "Password-only Remnawave credential rotation is safety-disabled pending durable receipts"
            )
        payload = {"revokeOnlyPasswords": revoke_only_passwords}
        identifier = self._require_numeric_identifier(user_ref)
        expected_legacy_uuid = user_ref.legacy_uuid if isinstance(user_ref, RemnawaveUserRef) else None
        await self._require_existing_target(numeric_id=identifier, legacy_uuid=expected_legacy_uuid)
        try:
            data = await self._client.post_validated(
                f"/api/users/{identifier}/actions/revoke",
                RemnawaveUserResponse,
                json=payload,
            )
        except RemnawaveTransportError:
            return await self._reconcile_accepted_known_target(
                operation="revoke",
                numeric_id=identifier,
                legacy_uuid=expected_legacy_uuid,
                require_revoked_at=not revoke_only_passwords,
                require_explicit_response=revoke_only_passwords,
            )
        if data is None:
            return await self._reconcile_accepted_known_target(
                operation="revoke",
                numeric_id=identifier,
                legacy_uuid=expected_legacy_uuid,
                require_revoked_at=not revoke_only_passwords,
                require_explicit_response=revoke_only_passwords,
            )
        user = map_remnawave_user(self._dump_validated_model(data))
        self._validate_user_binding(user, numeric_id=identifier, legacy_uuid=expected_legacy_uuid)
        if not revoke_only_passwords and user.sub_revoked_at is None:
            raise RemnawaveMutationAcceptedPending(operation="revoke", numeric_user_id=identifier)
        return user

    async def delete(self, user_ref: int | RemnawaveUserRef) -> None:
        identifier = self._require_numeric_identifier(user_ref)
        expected_legacy_uuid = user_ref.legacy_uuid if isinstance(user_ref, RemnawaveUserRef) else None
        existing = await self.get_by_id(identifier)
        if existing is None:
            return
        self._validate_user_binding(existing, numeric_id=identifier, legacy_uuid=expected_legacy_uuid)
        try:
            await self._client.delete_validated(f"/api/users/{identifier}", RemnawaveDeleteResponse)
        except RemnawaveTransportError:
            if await self.confirm_absent_by_id(identifier):
                return
            raise RemnawaveMutationAcceptedPending(operation="delete", numeric_user_id=identifier) from None
        if not await self.confirm_absent_by_id(identifier):
            raise RemnawaveMutationAcceptedPending(operation="delete", numeric_user_id=identifier)

    async def _require_existing_target(self, *, numeric_id: int, legacy_uuid: UUID | None) -> User:
        existing = await self.get_by_id(numeric_id)
        if existing is None:
            raise RemnawaveIdentityBindingError("Remnawave mutation target does not exist")
        self._validate_user_binding(existing, numeric_id=numeric_id, legacy_uuid=legacy_uuid)
        return existing

    async def _reconcile_accepted_known_target(
        self,
        *,
        operation: str,
        numeric_id: int,
        legacy_uuid: UUID | None,
        expected_update_payload: dict[str, Any] | None = None,
        require_revoked_at: bool = False,
        require_explicit_response: bool = False,
    ) -> User:
        if require_explicit_response:
            raise RemnawaveMutationAcceptedPending(
                operation=operation,
                numeric_user_id=numeric_id,
            )
        user = await self.get_by_id(numeric_id)
        if user is None:
            raise RemnawaveMutationAcceptedPending(
                operation=operation,
                numeric_user_id=numeric_id,
            )
        self._validate_user_binding(user, numeric_id=numeric_id, legacy_uuid=legacy_uuid)
        if expected_update_payload is not None:
            self._require_mutation_postcondition(user, payload=expected_update_payload, numeric_id=numeric_id)
        if require_revoked_at and user.sub_revoked_at is None:
            raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)
        return user

    @staticmethod
    def _require_mutation_postcondition(
        user: User,
        *,
        payload: dict[str, Any],
        numeric_id: int,
        operation: str = "update",
        require_all_observable: bool = True,
    ) -> None:
        """Accept a mutation only when every observable requested field matches."""

        observable_fields = {
            "id",
            "username",
            "status",
            "email",
            "telegramId",
            "expireAt",
            "trafficLimitBytes",
            "hwidDeviceLimit",
            "trafficLimitStrategy",
            "activeInternalSquads",
            "externalSquadUuid",
        }
        if require_all_observable and set(payload) - observable_fields:
            raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        expected_status = payload.get("status")
        if expected_status is not None:
            try:
                normalized_status = UserStatus(str(expected_status).lower())
            except ValueError as exc:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id) from exc
            if user.status != normalized_status:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        comparisons = (
            ("username", user.username),
            ("email", user.email),
            ("trafficLimitBytes", user.traffic_limit_bytes),
            ("hwidDeviceLimit", user.hwid_device_limit),
        )
        for field_name, actual_value in comparisons:
            if field_name in payload and payload[field_name] != actual_value:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        if "telegramId" in payload:
            expected_telegram_ids = payload["telegramId"]
            if not isinstance(expected_telegram_ids, list) or expected_telegram_ids != [user.telegram_id]:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        if "expireAt" in payload:
            expected_expire_at = payload["expireAt"]
            try:
                if isinstance(expected_expire_at, datetime):
                    expected_datetime = expected_expire_at
                else:
                    expected_datetime = datetime.fromisoformat(str(expected_expire_at).replace("Z", "+00:00"))
                if (
                    expected_datetime.utcoffset() is None
                    or user.expire_at is None
                    or user.expire_at.utcoffset() is None
                ):
                    raise ValueError("expiry timestamp must be timezone-aware")
                expiry_matches = user.expire_at.astimezone(UTC) == expected_datetime.astimezone(UTC)
            except (TypeError, ValueError):
                expiry_matches = False
            if not expiry_matches:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        if "trafficLimitStrategy" in payload:
            expected_strategy = str(payload["trafficLimitStrategy"])
            if user.traffic_limit_strategy is None or expected_strategy != user.traffic_limit_strategy:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        if "activeInternalSquads" in payload:
            expected_squads = RemnawaveUserGateway._normalize_squad_postcondition(payload["activeInternalSquads"])
            if user.active_internal_squad_uuids is None or set(expected_squads) != set(
                user.active_internal_squad_uuids
            ):
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        if "externalSquadUuid" in payload:
            expected_external_squad = payload["externalSquadUuid"]
            if not user.external_squad_uuid_observed or expected_external_squad != user.external_squad_uuid:
                raise RemnawaveMutationAcceptedPending(operation=operation, numeric_user_id=numeric_id)

        # A direct, identity-bound mutation response may not expose relationship
        # inputs such as traffic strategy or squad assignments.  That does not
        # relax validation for fields the response *does* expose: accepting an
        # exact user with stale email/limits would turn an upstream partial
        # failure into a false success.  Read-back reconciliation remains
        # stricter and rejects any requested field it cannot prove.
        if not require_all_observable:
            return

    @staticmethod
    def _normalize_squad_postcondition(raw_squads: Any) -> tuple[str, ...]:
        if not isinstance(raw_squads, list):
            raise RemnawaveMutationAcceptedPending(operation="update")
        normalized: list[str] = []
        for raw_squad in raw_squads:
            if isinstance(raw_squad, str):
                squad_uuid = raw_squad
            elif isinstance(raw_squad, dict) and raw_squad.get("uuid"):
                squad_uuid = str(raw_squad["uuid"])
            else:
                raise RemnawaveMutationAcceptedPending(operation="update")
            if not squad_uuid or squad_uuid in normalized:
                raise RemnawaveMutationAcceptedPending(operation="update")
            normalized.append(squad_uuid)
        return tuple(normalized)

    @staticmethod
    def _validate_complete_created_identity(user: User) -> int:
        numeric_id = user.remnawave_id
        if isinstance(numeric_id, bool) or not isinstance(numeric_id, int) or numeric_id <= 0:
            raise RemnawaveIdentityBindingError("Remnawave create response has an incomplete 3.x identity")
        return numeric_id

    @staticmethod
    def _validate_user_binding(
        user: User,
        *,
        numeric_id: int,
        legacy_uuid: UUID | None = None,
    ) -> None:
        if (
            isinstance(user.remnawave_id, bool)
            or not isinstance(user.remnawave_id, int)
            or user.remnawave_id != numeric_id
        ):
            raise RemnawaveIdentityBindingError("Remnawave numeric response does not match the requested user")
        if legacy_uuid is not None and user.uuid is not None and user.uuid != legacy_uuid:
            raise RemnawaveIdentityBindingError("Remnawave rollback reference does not match the requested user")


class RemnawaveLegacyRollbackUserGateway:
    """Explicitly isolated Remnawave 2.x UUID mutation adapter for rollback only."""

    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def update_by_uuid(self, legacy_uuid: UUID, **kwargs: Any) -> User:
        payload = RemnawaveUserGateway._normalize_user_payload({"uuid": str(legacy_uuid), **kwargs})
        data = await self._client.patch_validated("/api/users", RemnawaveUserResponse, json=payload)
        return map_remnawave_user(RemnawaveUserGateway._dump_validated_model(data))

    async def revoke_subscription_by_uuid(
        self,
        legacy_uuid: UUID,
        *,
        revoke_only_passwords: bool = False,
    ) -> User:
        data = await self._client.post_validated(
            f"/api/users/{legacy_uuid}/actions/revoke",
            RemnawaveUserResponse,
            json={"revokeOnlyPasswords": revoke_only_passwords},
        )
        return map_remnawave_user(RemnawaveUserGateway._dump_validated_model(data))

    async def delete_by_uuid(self, legacy_uuid: UUID) -> None:
        await self._client.delete_validated(f"/api/users/{legacy_uuid}", RemnawaveDeleteResponse)
