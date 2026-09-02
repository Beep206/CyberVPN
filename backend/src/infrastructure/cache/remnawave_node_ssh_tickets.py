"""Fail-closed Redis store for CyberVPN-local Remnawave Node SSH tickets."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from uuid import UUID

import redis.asyncio as redis
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.config.settings import settings

_TICKET_RE = re.compile(r"^[A-Za-z0-9_-]{32,96}$")
_UPSTREAM_OPAQUE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_ENVELOPE_PREFIX = "v1."

_PROMOTE_LUA = """
local raw = redis.call("GET", KEYS[1])
if not raw then
  return nil
end
redis.call("DEL", KEYS[1])
redis.call("SET", KEYS[2], raw, "EX", ARGV[1])
return raw
"""

_COMPARE_DELETE_LUA = """
local raw = redis.call("GET", KEYS[1])
if raw and raw == ARGV[1] then
  return redis.call("DEL", KEYS[1])
end
return 0
"""

_POP_FIRST_LUA = """
local pending = redis.call("GET", KEYS[1])
if pending then
  redis.call("DEL", KEYS[1])
  return {pending, "pending"}
end
local active = redis.call("GET", KEYS[2])
if active then
  redis.call("DEL", KEYS[2])
  return {active, "active"}
end
return nil
"""


@dataclass(frozen=True, slots=True)
class RemnawaveNodeSshTicketRecord:
    """Decrypted in-process ticket state; Redis receives only an AEAD envelope."""

    ticket_id: str = field(repr=False)
    admin_id: str
    auth_realm_id: str
    auth_session_binding: str = field(repr=False)
    node_uuid: str
    origin: str
    issue_ip: str
    upstream_ticket: str = field(repr=False)
    upstream_credential: str = field(repr=False)
    upstream_path: str
    upstream_protocol: str
    issued_at: str
    expires_at: str
    stored_envelope: str = field(default="", repr=False, compare=False)

    @property
    def reference(self) -> str:
        return hashlib.sha256(self.ticket_id.encode("ascii")).hexdigest()[:16]


class RemnawaveNodeSshTicketError(Exception):
    """Ticket is missing, expired, corrupt, or presented outside its scope."""


class RemnawaveNodeSshTicketStore:
    """Store opaque one-use tickets with atomic promotion and revocation.

    Local ticket values are never persisted: Redis keys contain a keyed digest,
    and values are AES-256-GCM envelopes. Key separation is provided by HKDF
    over CyberVPN's existing server-only JWT secret.
    """

    pending_prefix = "remnawave:node-ssh:pending:"
    active_prefix = "remnawave:node-ssh:active:"

    def __init__(self, redis_client: redis.Redis, *, master_secret: str | None = None) -> None:
        self._redis = redis_client
        secret = master_secret if master_secret is not None else settings.jwt_secret.get_secret_value()
        if len(secret) < 32:
            raise ValueError("Node SSH ticket encryption requires a server secret of at least 32 characters")
        secret_bytes = secret.encode("utf-8")
        self._encryption_key = self._derive_key(secret_bytes, b"cybervpn/remnawave-node-ssh/envelope/v1")
        self._index_key = self._derive_key(secret_bytes, b"cybervpn/remnawave-node-ssh/index/v1")
        self._session_key = self._derive_key(secret_bytes, b"cybervpn/remnawave-node-ssh/session/v1")
        self._aead = AESGCM(self._encryption_key)

    @staticmethod
    def _derive_key(secret: bytes, info: bytes) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"cybervpn-remnawave-node-ssh-v1",
            info=info,
        ).derive(secret)

    def build_session_binding(
        self,
        *,
        admin_id: UUID,
        auth_realm_id: UUID,
        access_jti: str,
        device_cookie: str,
    ) -> str:
        if not access_jti or not device_cookie:
            raise ValueError("Node SSH session binding inputs must not be empty")
        material = "\0".join((str(admin_id), str(auth_realm_id), access_jti, device_cookie)).encode("utf-8")
        return hmac.new(self._session_key, material, hashlib.sha256).hexdigest()

    async def create(
        self,
        *,
        admin_id: UUID,
        auth_realm_id: UUID,
        auth_session_binding: str,
        node_uuid: UUID,
        origin: str,
        issue_ip: str,
        upstream_ticket: str,
        upstream_credential: str,
        upstream_path: str,
        upstream_protocol: str,
        ttl_seconds: int,
    ) -> RemnawaveNodeSshTicketRecord:
        if not 1 <= ttl_seconds <= 15:
            raise ValueError("Node SSH ticket TTL must be between 1 and 15 seconds")
        if not _SHA256_RE.fullmatch(auth_session_binding):
            raise ValueError("Node SSH auth session binding is invalid")
        if (
            not _UPSTREAM_OPAQUE_RE.fullmatch(upstream_ticket)
            or not _UPSTREAM_OPAQUE_RE.fullmatch(upstream_credential)
            or hmac.compare_digest(upstream_ticket, upstream_credential)
            or upstream_path != "/api/cybervpn/node-ssh/ws"
            or upstream_protocol != "rw-cybervpn"
        ):
            raise ValueError("Node SSH upstream broker material is invalid")
        normalized_issue_ip = self._normalize_ip(issue_ip)

        issued_at = datetime.now(UTC)
        for _attempt in range(3):
            ticket_id = secrets.token_urlsafe(32)
            record = RemnawaveNodeSshTicketRecord(
                ticket_id=ticket_id,
                admin_id=str(admin_id),
                auth_realm_id=str(auth_realm_id),
                auth_session_binding=auth_session_binding,
                node_uuid=str(node_uuid),
                origin=origin,
                issue_ip=normalized_issue_ip,
                upstream_ticket=upstream_ticket,
                upstream_credential=upstream_credential,
                upstream_path=upstream_path,
                upstream_protocol=upstream_protocol,
                issued_at=issued_at.isoformat(),
                expires_at=(issued_at + timedelta(seconds=ttl_seconds)).isoformat(),
            )
            envelope = self._seal_record(record)
            created = await self._redis.set(
                self._pending_key(ticket_id),
                envelope,
                ex=ttl_seconds,
                nx=True,
            )
            if created:
                return self._with_envelope(record, envelope)
        raise RemnawaveNodeSshTicketError("node_ssh_ticket_collision")

    async def consume(
        self,
        ticket_id: str,
        *,
        expected_admin_id: UUID,
        expected_auth_realm_id: UUID,
        expected_auth_session_binding: str,
        expected_origin: str,
        expected_issue_ip: str,
        active_ttl_seconds: int,
    ) -> RemnawaveNodeSshTicketRecord:
        if not 60 <= active_ttl_seconds <= 3600:
            raise ValueError("Node SSH active session TTL must be between 60 and 3600 seconds")
        normalized_ticket = self._normalize_ticket_id(ticket_id)
        raw = await self._redis.eval(
            _PROMOTE_LUA,
            2,
            self._pending_key(normalized_ticket),
            self._active_key(normalized_ticket),
            active_ttl_seconds,
        )
        if raw is None:
            raise RemnawaveNodeSshTicketError("node_ssh_ticket_missing")

        envelope = self._raw_text(raw)
        try:
            record = self._open_record(envelope, ticket_id=normalized_ticket)
            if record.admin_id != str(expected_admin_id):
                raise RemnawaveNodeSshTicketError("node_ssh_ticket_admin_mismatch")
            if record.auth_realm_id != str(expected_auth_realm_id):
                raise RemnawaveNodeSshTicketError("node_ssh_ticket_realm_mismatch")
            if not hmac.compare_digest(record.auth_session_binding, expected_auth_session_binding):
                raise RemnawaveNodeSshTicketError("node_ssh_ticket_session_mismatch")
            if record.origin != expected_origin:
                raise RemnawaveNodeSshTicketError("node_ssh_ticket_origin_mismatch")
            if not hmac.compare_digest(record.issue_ip, self._normalize_ip(expected_issue_ip)):
                raise RemnawaveNodeSshTicketError("node_ssh_ticket_ip_mismatch")
            if self._parse_datetime(record.expires_at) <= datetime.now(UTC):
                raise RemnawaveNodeSshTicketError("node_ssh_ticket_expired")
        except RemnawaveNodeSshTicketError:
            await self._redis.delete(self._active_key(normalized_ticket))
            raise
        return record

    async def revoke(
        self,
        ticket_id: str,
        *,
        expected_admin_id: UUID,
    ) -> tuple[RemnawaveNodeSshTicketRecord, str] | None:
        """Revoke only a ticket belonging to the authenticated ticket owner."""

        normalized_ticket = self._normalize_ticket_id(ticket_id)
        for state, key in (
            ("pending", self._pending_key(normalized_ticket)),
            ("active", self._active_key(normalized_ticket)),
        ):
            raw = await self._redis.get(key)
            if raw is None:
                continue
            envelope = self._raw_text(raw)
            try:
                record = self._open_record(envelope, ticket_id=normalized_ticket)
            except RemnawaveNodeSshTicketError:
                await self._redis.eval(_COMPARE_DELETE_LUA, 1, key, envelope)
                return None
            if record.admin_id != str(expected_admin_id):
                return None
            deleted = await self._redis.eval(_COMPARE_DELETE_LUA, 1, key, envelope)
            if int(deleted or 0) == 1:
                return record, state
        return None

    async def revoke_as_supervisor(self, ticket_id: str) -> tuple[RemnawaveNodeSshTicketRecord, str] | None:
        """Atomically revoke any ticket after the caller passed MANAGE_ADMINS."""

        normalized_ticket = self._normalize_ticket_id(ticket_id)
        popped = await self._redis.eval(
            _POP_FIRST_LUA,
            2,
            self._pending_key(normalized_ticket),
            self._active_key(normalized_ticket),
        )
        if not isinstance(popped, list | tuple) or len(popped) != 2:
            return None
        envelope = self._raw_text(popped[0])
        state = self._raw_text(popped[1])
        if state not in {"pending", "active"}:
            return None
        try:
            return self._open_record(envelope, ticket_id=normalized_ticket), state
        except RemnawaveNodeSshTicketError:
            return None

    async def finish_session(self, record: RemnawaveNodeSshTicketRecord) -> None:
        if not record.stored_envelope:
            return
        await self._redis.eval(
            _COMPARE_DELETE_LUA,
            1,
            self._active_key(record.ticket_id),
            record.stored_envelope,
        )

    async def is_session_active(self, ticket_id: str) -> bool:
        normalized_ticket = self._normalize_ticket_id(ticket_id)
        return await self._redis.get(self._active_key(normalized_ticket)) is not None

    async def revoke_unchecked(self, ticket_id: str) -> None:
        """Compensate issuance/policy failure without exposing ticket ownership."""

        normalized_ticket = self._normalize_ticket_id(ticket_id)
        await self._redis.delete(self._pending_key(normalized_ticket), self._active_key(normalized_ticket))

    def _pending_key(self, ticket_id: str) -> str:
        return f"{self.pending_prefix}{self._ticket_key_digest(ticket_id)}"

    def _active_key(self, ticket_id: str) -> str:
        return f"{self.active_prefix}{self._ticket_key_digest(ticket_id)}"

    def _ticket_key_digest(self, ticket_id: str) -> str:
        return hmac.new(self._index_key, ticket_id.encode("ascii"), hashlib.sha256).hexdigest()

    def _seal_record(self, record: RemnawaveNodeSshTicketRecord) -> str:
        payload = {
            "admin_id": record.admin_id,
            "auth_realm_id": record.auth_realm_id,
            "auth_session_binding": record.auth_session_binding,
            "node_uuid": record.node_uuid,
            "origin": record.origin,
            "issue_ip": record.issue_ip,
            "upstream_ticket": record.upstream_ticket,
            "upstream_credential": record.upstream_credential,
            "upstream_path": record.upstream_path,
            "upstream_protocol": record.upstream_protocol,
            "issued_at": record.issued_at,
            "expires_at": record.expires_at,
        }
        plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        nonce = secrets.token_bytes(12)
        ciphertext = self._aead.encrypt(nonce, plaintext, self._aad(record.ticket_id))
        encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"{_ENVELOPE_PREFIX}{encoded}"

    def _open_record(self, envelope: str, *, ticket_id: str) -> RemnawaveNodeSshTicketRecord:
        try:
            if not envelope.startswith(_ENVELOPE_PREFIX):
                raise ValueError("unsupported envelope")
            encrypted = base64.b64decode(
                envelope.removeprefix(_ENVELOPE_PREFIX),
                altchars=b"-_",
                validate=True,
            )
            if len(encrypted) <= 12:
                raise ValueError("truncated envelope")
            plaintext = self._aead.decrypt(encrypted[:12], encrypted[12:], self._aad(ticket_id))
            payload = json.loads(plaintext)
            record = RemnawaveNodeSshTicketRecord(
                ticket_id=ticket_id,
                admin_id=str(UUID(str(payload["admin_id"]))),
                auth_realm_id=str(UUID(str(payload["auth_realm_id"]))),
                auth_session_binding=str(payload["auth_session_binding"]),
                node_uuid=str(UUID(str(payload["node_uuid"]))),
                origin=str(payload["origin"]),
                issue_ip=str(payload["issue_ip"]),
                upstream_ticket=str(payload["upstream_ticket"]),
                upstream_credential=str(payload["upstream_credential"]),
                upstream_path=str(payload["upstream_path"]),
                upstream_protocol=str(payload["upstream_protocol"]),
                issued_at=str(payload["issued_at"]),
                expires_at=str(payload["expires_at"]),
                stored_envelope=envelope,
            )
            self._parse_datetime(record.issued_at)
            self._parse_datetime(record.expires_at)
            if (
                not _SHA256_RE.fullmatch(record.auth_session_binding)
                or not record.origin
                or record.issue_ip != self._normalize_ip(record.issue_ip)
                or not _UPSTREAM_OPAQUE_RE.fullmatch(record.upstream_ticket)
                or not _UPSTREAM_OPAQUE_RE.fullmatch(record.upstream_credential)
                or hmac.compare_digest(record.upstream_ticket, record.upstream_credential)
                or record.upstream_path != "/api/cybervpn/node-ssh/ws"
                or record.upstream_protocol != "rw-cybervpn"
            ):
                raise ValueError("invalid Node SSH ticket record scope")
            return record
        except (InvalidTag, KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RemnawaveNodeSshTicketError("node_ssh_ticket_corrupt") from exc

    @staticmethod
    def _with_envelope(record: RemnawaveNodeSshTicketRecord, envelope: str) -> RemnawaveNodeSshTicketRecord:
        return RemnawaveNodeSshTicketRecord(
            ticket_id=record.ticket_id,
            admin_id=record.admin_id,
            auth_realm_id=record.auth_realm_id,
            auth_session_binding=record.auth_session_binding,
            node_uuid=record.node_uuid,
            origin=record.origin,
            issue_ip=record.issue_ip,
            upstream_ticket=record.upstream_ticket,
            upstream_credential=record.upstream_credential,
            upstream_path=record.upstream_path,
            upstream_protocol=record.upstream_protocol,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
            stored_envelope=envelope,
        )

    @staticmethod
    def _normalize_ticket_id(ticket_id: str) -> str:
        normalized = ticket_id.strip()
        if not _TICKET_RE.fullmatch(normalized):
            raise RemnawaveNodeSshTicketError("node_ssh_ticket_invalid")
        return normalized

    @staticmethod
    def _aad(ticket_id: str) -> bytes:
        return f"cybervpn/remnawave-node-ssh/v1\0{ticket_id}".encode("ascii")

    @staticmethod
    def _raw_text(raw: object) -> str:
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _normalize_ip(value: str) -> str:
        try:
            return str(ip_address(value.strip()))
        except ValueError as exc:
            raise ValueError("Node SSH client IP is invalid") from exc
