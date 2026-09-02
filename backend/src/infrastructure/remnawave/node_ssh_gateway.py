"""Least-privilege boundary for CyberVPN's scoped Remnawave Node SSH broker."""

from __future__ import annotations

import re
from contextlib import AbstractAsyncContextManager
from typing import Literal
from urllib.parse import urlparse, urlunparse
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as websocket_connect
from websockets.typing import Subprotocol

from src.config.settings import settings

REMNAWAVE_SSH_BROKER_TICKET_PATH = "/api/cybervpn/node-ssh/tickets"
REMNAWAVE_SSH_WS_PATH = "/api/cybervpn/node-ssh/ws"
REMNAWAVE_SSH_WS_PROTOCOL = "rw-cybervpn"
REMNAWAVE_SSH_BROKER_HEADER = "X-CyberVPN-Node-Ssh-Broker-Secret"
MAX_SSH_WS_MESSAGE_BYTES = 1 << 20
_BROKER_SECRET_RE = re.compile(r"^[a-f0-9]{128}$")


def is_valid_remnawave_node_ssh_broker_secret(secret: SecretStr | str) -> bool:
    raw = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
    return _BROKER_SECRET_RE.fullmatch(raw.strip()) is not None


def is_valid_remnawave_node_ssh_broker_url(value: str) -> bool:
    try:
        _validated_endpoints(value)
    except ValueError:
        return False
    return True


class RemnawaveUpstreamSshTicket(BaseModel):
    """Opaque, one-time broker material that must never cross to the browser."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ticket: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")
    credential: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")
    path: Literal["/api/cybervpn/node-ssh/ws"]
    protocol: Literal["rw-cybervpn"]
    expires_in_seconds: Literal[10] = Field(validation_alias="expiresInSeconds")

    @model_validator(mode="after")
    def require_distinct_opaque_values(self) -> RemnawaveUpstreamSshTicket:
        if self.ticket == self.credential:
            raise ValueError("Scoped Node SSH ticket and credential must differ")
        return self


class _RemnawaveUpstreamSshTicketEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: RemnawaveUpstreamSshTicket


class RemnawaveUpstreamVaultEvaluation(BaseModel):
    """Compatibility type; the scoped broker deliberately has no vault endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    evaluated: str = Field(min_length=1, max_length=512, pattern=r"^[A-Za-z0-9+/]*={0,2}$")


class RemnawaveNodeSshScopedBrokerUnavailable(RuntimeError):
    """The dedicated broker is disabled or incompletely configured."""


class RemnawaveNodeSshGateway:
    """Use only the dedicated broker secret; never reuse Remnawave admin auth."""

    def __init__(
        self,
        *,
        remnawave_url: str,
        broker_secret: SecretStr | str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if remnawave_url.strip():
            self._base_url, self._websocket_url = _validated_endpoints(remnawave_url)
        else:
            self._base_url, self._websocket_url = "", ""
        raw_secret = (
            broker_secret.get_secret_value() if isinstance(broker_secret, SecretStr) else broker_secret
        ).strip()
        self._broker_secret = raw_secret
        self._client = http_client
        self._owns_client = http_client is None

    @property
    def is_configured(self) -> bool:
        return (
            bool(self._base_url)
            and bool(self._websocket_url)
            and is_valid_remnawave_node_ssh_broker_secret(self._broker_secret)
        )

    async def _get_client(self) -> httpx.AsyncClient:
        self._require_configured()
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(10.0, connect=5.0, read=10.0, write=5.0, pool=5.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                trust_env=False,
            )
            self._owns_client = True
        if "authorization" in self._client.headers:
            raise RemnawaveNodeSshScopedBrokerUnavailable(
                "Scoped Node SSH broker client must not carry generic Remnawave authorization"
            )
        return self._client

    async def create_ticket(self, node_uuid: str, *, actor_reference: str) -> RemnawaveUpstreamSshTicket:
        """Exchange an already-authorized admin UUID for one node-bound pair."""

        self._require_configured()
        try:
            normalized_node_uuid = str(UUID(node_uuid))
            normalized_actor_reference = str(UUID(actor_reference))
        except ValueError as exc:
            raise ValueError("Scoped Node SSH node and actor references must be UUIDs") from exc

        client = await self._get_client()
        response = await client.post(
            f"{REMNAWAVE_SSH_BROKER_TICKET_PATH}/{normalized_node_uuid}",
            headers={REMNAWAVE_SSH_BROKER_HEADER: self._broker_secret},
            json={"actorReference": normalized_actor_reference},
        )
        response.raise_for_status()
        if response.status_code != 201:
            raise ValueError("Scoped Node SSH broker returned an unexpected success status")
        return _RemnawaveUpstreamSshTicketEnvelope.model_validate(response.json()).response

    async def evaluate_vault(self, blinded: str) -> RemnawaveUpstreamVaultEvaluation:
        _ = blinded
        raise RemnawaveNodeSshScopedBrokerUnavailable(
            "The scoped Node SSH broker deliberately provides no privileged vault endpoint"
        )

    def connect(self, ticket: RemnawaveUpstreamSshTicket) -> AbstractAsyncContextManager[ClientConnection]:
        self._require_configured()
        # The custom upstream selects only rw-cybervpn and atomically consumes
        # the remaining pair. No broker secret, API token, APP_SECRET, or JWT is
        # sent on the WebSocket handshake.
        return websocket_connect(
            self._websocket_url,
            subprotocols=[
                Subprotocol(ticket.protocol),
                Subprotocol(ticket.ticket),
                Subprotocol(ticket.credential),
            ],
            compression=None,
            proxy=None,
            open_timeout=10,
            close_timeout=10,
            max_size=MAX_SSH_WS_MESSAGE_BYTES,
            max_queue=16,
        )

    async def close(self) -> None:
        if self._owns_client and self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise RemnawaveNodeSshScopedBrokerUnavailable(
                "Remnawave Node SSH is disabled without a dedicated scoped broker secret"
            )


def _validated_endpoints(remnawave_url: str) -> tuple[str, str]:
    normalized = remnawave_url.strip().rstrip("/").removesuffix("/api")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("REMNAWAVE_URL must be an absolute HTTP(S) URL for Node SSH")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("REMNAWAVE_URL must not contain credentials, query, or fragment for Node SSH")
    if parsed.path not in {"", "/"}:
        raise ValueError("REMNAWAVE_URL must not contain a path other than /api for Node SSH")

    base_url = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    websocket_scheme = "wss" if parsed.scheme == "https" else "ws"
    websocket_url = urlunparse((websocket_scheme, parsed.netloc, REMNAWAVE_SSH_WS_PATH, "", "", ""))
    return base_url, websocket_url


def _validated_websocket_endpoint(remnawave_url: str) -> tuple[str, str, int]:
    """Compatibility helper retained for the existing SSRF-focused tests."""

    _, websocket_url = _validated_endpoints(remnawave_url)
    parsed = urlparse(websocket_url)
    hostname = parsed.hostname
    if hostname is None:  # defensive; _validated_endpoints already establishes this
        raise ValueError("REMNAWAVE_URL must identify a Node SSH hostname")
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    return websocket_url, hostname, port


remnawave_node_ssh_gateway = RemnawaveNodeSshGateway(
    remnawave_url=settings.remnawave_node_ssh_broker_url,
    broker_secret=settings.remnawave_node_ssh_broker_secret,
)
