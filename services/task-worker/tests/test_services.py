"""Tests for service client modules."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from tests.remnawave_fixtures import load_remnawave_fixture


def test_remnawave_client_ignores_ambient_proxy_environment(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("ALL_PROXY", "http://proxy.invalid:3128")
    with patch("src.services.remnawave_client.httpx.AsyncClient") as client_cls:
        from src.services.remnawave_client import RemnawaveClient

        RemnawaveClient()

    assert client_cls.call_args.kwargs["trust_env"] is False


@pytest.mark.asyncio
async def test_remnawave_client_get_users():
    """Test RemnawaveClient get_users returns user list."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": [{"id": 1, "name": "User 1"}]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            users = await client.get_users()

            assert len(users) == 1
            assert users[0]["name"] == "User 1"


@pytest.mark.asyncio
async def test_remnawave_client_get_users_normalizes_aliases():
    """Test RemnawaveClient get_users normalizes 3.4.3 payloads."""
    user_payload = load_remnawave_fixture("user_3_4_1.json")

    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": [user_payload]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            users = await client.get_users()

            assert users[0]["status"] == "active"
            assert users[0]["expiresAt"] == "2027-12-31T23:59:59+00:00"
            assert users[0]["isOnline"] is True
            assert users[0]["dataLimit"] == 1024
            assert users[0]["dataUsed"] == 64


@pytest.mark.asyncio
async def test_remnawave_client_get_nodes_normalizes_aliases():
    """Test RemnawaveClient get_nodes normalizes node metadata and traffic aliases."""
    node_payload = load_remnawave_fixture("node_3_4_1.json")

    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"nodes": [node_payload]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            nodes = await client.get_nodes()

            assert nodes[0]["is_connected"] is True
            assert nodes[0]["isConnected"] is True
            assert nodes[0]["node_id"] == 17
            assert nodes[0]["node_version"] == "3.4.1"
            assert nodes[0]["xrayVersion"] == "26.7.31"
            assert nodes[0]["active_plugin_uuid"] == node_payload["activePluginUuid"]
            assert nodes[0]["integrationUuids"] == node_payload["integrationUuids"]
            assert nodes[0]["ips"] == node_payload["ips"]


@pytest.mark.asyncio
async def test_remnawave_client_get_inbounds_returns_inbound_list():
    """Test RemnawaveClient get_inbounds returns the upstream inbound collection."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"inbounds": [{"uuid": "inbound-1", "protocol": "vless", "port": 443}]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            inbounds = await client.get_inbounds()

            assert len(inbounds) == 1
            assert inbounds[0]["uuid"] == "inbound-1"
            assert inbounds[0]["protocol"] == "vless"


@pytest.mark.asyncio
async def test_remnawave_client_get_hosts_returns_host_list():
    """Test RemnawaveClient get_hosts returns the upstream host collection."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hosts": [{"uuid": "host-1", "inboundUuid": "inbound-1", "address": "edge.example.com"}]
        }
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            hosts = await client.get_hosts()

            assert len(hosts) == 1
            assert hosts[0]["uuid"] == "host-1"
            assert hosts[0]["address"] == "edge.example.com"


@pytest.mark.asyncio
async def test_remnawave_client_get_user_normalizes_single_payload():
    """Test RemnawaveClient get_user normalizes a single user payload."""
    user_payload = load_remnawave_fixture("user_3_4_1.json")

    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        user_payload["id"] = 43
        user_payload["trafficLimitBytes"] = 2048
        user_payload["userTraffic"]["usedTrafficBytes"] = 512
        mock_response.json.return_value = user_payload
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            user = await client.get_user(43)

            assert user["user_id"] == 43
            assert user["status"] == "active"
            assert user["dataLimit"] == 2048
            assert user["dataUsed"] == 512


@pytest.mark.asyncio
async def test_remnawave_client_get_user_rejects_mismatched_numeric_identity():
    user_payload = load_remnawave_fixture("user_3_4_1.json")
    user_payload["id"] = 44

    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = user_payload
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveAPIError, RemnawaveClient

        async with RemnawaveClient() as client:
            with pytest.raises(RemnawaveAPIError, match="user_identity_mismatch") as exc_info:
                await client.get_user(43)

        assert exc_info.value.status_code == 502
        mock_client.request.assert_called_once_with("GET", "/api/users/43", params=None)


@pytest.mark.asyncio
async def test_remnawave_client_disables_implicit_transport_retries():
    with (
        patch("src.services.remnawave_client.httpx.AsyncHTTPTransport") as transport_factory,
        patch("src.services.remnawave_client.httpx.AsyncClient") as client_factory,
    ):
        from src.services.remnawave_client import RemnawaveClient

        client_factory.return_value.aclose = AsyncMock()
        async with RemnawaveClient():
            pass

    transport_factory.assert_called_once_with(retries=0)


@pytest.mark.asyncio
async def test_remnawave_client_disable_user():
    """Test RemnawaveClient disable_user uses the numeric 3.x route."""
    response_payload = load_remnawave_fixture("user_3_4_1.json")
    response_payload["id"] = 123
    response_payload["status"] = "DISABLED"
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = response_payload
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await client.disable_user(123)

            assert result["status"] == "disabled"
            mock_client.request.assert_called_with(
                "POST",
                "/api/users/123/actions/disable",
                json=None,
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "action", "expected_status"),
    [
        ("disable_user", "disable", "disabled"),
        ("enable_user", "enable", "active"),
    ],
)
async def test_remnawave_client_reconciles_no_body_user_status(method_name, action, expected_status):
    user_payload = load_remnawave_fixture("user_3_4_1.json")
    user_payload["id"] = 123
    user_payload["status"] = expected_status.upper()
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        accepted = MagicMock(is_success=True, status_code=204, content=b"")
        readback = MagicMock(is_success=True, status_code=200, content=b"json")
        readback.json.return_value = user_payload
        mock_client.request.side_effect = [accepted, readback]
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await getattr(client, method_name)(123)

        assert result["status"] == expected_status
        assert mock_client.request.call_args_list == [
            call("POST", f"/api/users/123/actions/{action}", json=None),
            call("GET", "/api/users/123", params=None),
        ]


@pytest.mark.asyncio
async def test_remnawave_client_reconciles_ambiguous_disable_timeout_without_replay():
    user_payload = load_remnawave_fixture("user_3_4_1.json")
    user_payload["id"] = 123
    user_payload["status"] = "DISABLED"
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        request = httpx.Request("POST", "https://remnawave.test/api/users/123/actions/disable")
        readback = MagicMock(is_success=True, status_code=200, content=b"json")
        readback.json.return_value = user_payload
        mock_client.request.side_effect = [httpx.ReadTimeout("ambiguous", request=request), readback]
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await client.disable_user(123)

        assert result["status"] == "disabled"
        assert mock_client.request.call_args_list == [
            call("POST", "/api/users/123/actions/disable", json=None),
            call("GET", "/api/users/123", params=None),
        ]


@pytest.mark.asyncio
async def test_remnawave_client_rejects_no_body_disable_with_stale_readback():
    user_payload = load_remnawave_fixture("user_3_4_1.json")
    user_payload["id"] = 123
    user_payload["status"] = "ACTIVE"
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        accepted = MagicMock(is_success=True, status_code=202, content=b"")
        readback = MagicMock(is_success=True, status_code=200, content=b"json")
        readback.json.return_value = user_payload
        mock_client.request.side_effect = [accepted, readback]
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveAPIError, RemnawaveClient

        async with RemnawaveClient() as client:
            with pytest.raises(RemnawaveAPIError, match="user_status_postcondition_mismatch"):
                await client.disable_user(123)

        assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_remnawave_client_api_error():
    """Test RemnawaveClient raises error on non-2xx response."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "User not found"}
        mock_response.text = ""
        mock_response.reason_phrase = "Not Found"
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveAPIError, RemnawaveClient

        with pytest.raises(RemnawaveAPIError) as exc_info:
            async with RemnawaveClient() as client:
                await client.get_user(999)

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_remnawave_client_accepts_successful_no_body_bulk_response():
    """A 204 with no body is success, not a JSON parsing failure."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 204
        mock_response.content = b""
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await client.bulk_extend_expiration_date([41, 42], 30)

        assert result is None
        mock_client.request.assert_called_once_with(
            "POST",
            "/api/users/bulk/extend-expiration-date",
            json={"userIds": [41, 42], "extendDays": 30},
        )


@pytest.mark.asyncio
async def test_remnawave_client_rejects_successful_empty_collection_response():
    """No-body is valid for mutations, never as an empty GET collection."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.content = b""
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveAPIError, RemnawaveClient

        async with RemnawaveClient() as client:
            with pytest.raises(RemnawaveAPIError, match="invalid_users_stream_response"):
                await client.get_users()


@pytest.mark.asyncio
async def test_remnawave_client_consumes_every_user_cursor_page() -> None:
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        first = MagicMock(is_success=True, status_code=200, content=b"json")
        first.json.return_value = {
            "users": [{"id": 41, "username": "first"}],
            "nextCursor": "41",
            "hasNextPage": True,
        }
        second = MagicMock(is_success=True, status_code=200, content=b"json")
        second.json.return_value = {
            "users": [{"id": 42, "username": "second"}],
            "hasNextPage": False,
        }
        mock_client = AsyncMock()
        mock_client.request.side_effect = [first, second]
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            users = await client.get_users()

    assert [user["id"] for user in users] == [41, 42]
    assert mock_client.request.await_args_list[0].kwargs["params"] == {"size": 1000}
    assert mock_client.request.await_args_list[1].kwargs["params"] == {"size": 1000, "cursor": "41"}


@pytest.mark.asyncio
async def test_remnawave_client_rejects_repeated_user_cursor_before_partial_processing() -> None:
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        first = MagicMock(is_success=True, status_code=200, content=b"json")
        first.json.return_value = {
            "users": [{"id": 41, "username": "first"}],
            "nextCursor": "41",
            "hasNextPage": True,
        }
        repeated = MagicMock(is_success=True, status_code=200, content=b"json")
        repeated.json.return_value = {
            "users": [{"id": 42, "username": "second"}],
            "nextCursor": "41",
            "hasNextPage": True,
        }
        mock_client = AsyncMock()
        mock_client.request.side_effect = [first, repeated]
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveAPIError, RemnawaveClient

        async with RemnawaveClient() as client:
            with pytest.raises(RemnawaveAPIError, match="repeated_users_stream_cursor"):
                await client.get_users()


@pytest.mark.asyncio
async def test_remnawave_client_rejects_legacy_uuid_user_identity():
    with patch("src.services.remnawave_client.httpx.AsyncClient") as client_cls:
        from src.services.remnawave_client import RemnawaveClient

        client_cls.return_value.aclose = AsyncMock()
        async with RemnawaveClient() as client:
            with pytest.raises(ValueError, match="positive integer"):
                await client.get_user("legacy-uuid")


@pytest.mark.asyncio
async def test_remnawave_client_health_check():
    """Test RemnawaveClient health_check returns True when healthy."""
    with patch("src.services.remnawave_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.remnawave_client import RemnawaveClient

        async with RemnawaveClient() as client:
            result = await client.health_check()

            assert result is True


def test_remnawave_client_normalize_base_url_strips_api_suffix():
    from src.services.remnawave_client import RemnawaveClient

    assert RemnawaveClient._normalize_base_url("http://localhost:3005/api") == "http://localhost:3005"
    assert RemnawaveClient._normalize_base_url("http://localhost:3005") == "http://localhost:3005"


def test_remnawave_client_normalize_path_prefixes_api_once():
    from src.services.remnawave_client import RemnawaveClient

    assert RemnawaveClient._normalize_path("/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("/api/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("node-plugins") == "/api/node-plugins"


@pytest.mark.asyncio
async def test_telegram_client_send_message():
    """Test TelegramClient send_message sends request."""
    with patch("src.services.telegram_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.telegram_client import TelegramClient

        async with TelegramClient() as client:
            result = await client.send_message(123456, "Test message")

            assert result["message_id"] == 123
            assert "sent_at" in result


@pytest.mark.asyncio
async def test_telegram_client_send_admin_alert():
    """Test TelegramClient send_admin_alert broadcasts to admins."""
    with (
        patch("src.services.telegram_client.httpx.AsyncClient") as mock_client_cls,
        patch("src.services.telegram_client.get_settings") as mock_settings,
    ):
        mock_settings.return_value.admin_telegram_ids = [111, 222]

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from src.services.telegram_client import TelegramClient

        async with TelegramClient() as client:
            results = await client.send_admin_alert("Alert message", severity="warning")

            assert len(results) == 2


@pytest.mark.asyncio
async def test_telegram_client_rate_limit_retry():
    """Test TelegramClient retries on 429 error."""
    with (
        patch("src.services.telegram_client.httpx.AsyncClient") as mock_client_cls,
        patch("src.services.telegram_client.asyncio.sleep") as mock_sleep,
    ):
        mock_client = AsyncMock()
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        mock_error_response.json.return_value = {"ok": False, "parameters": {"retry_after": 1}}

        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {"ok": True, "result": {"message_id": 123}}

        mock_client.request.side_effect = [
            httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=mock_error_response),
            mock_success_response,
        ]
        mock_client_cls.return_value = mock_client

        from src.services.telegram_client import TelegramClient

        async with TelegramClient() as client:
            result = await client.send_message(123456, "Test")

            assert result["message_id"] == 123
            mock_sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_cryptobot_client_get_invoices():
    """Test CryptoBotClient get_invoices returns invoice list."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"items": [{"id": 1, "amount": 10.5}]}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from pydantic import SecretStr

        from src.services.cryptobot_client import CryptoBotClient

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            invoices = await client.get_invoices(status="active")

            assert len(invoices) == 1
            assert invoices[0]["amount"] == 10.5


@pytest.mark.asyncio
async def test_cryptobot_client_create_invoice():
    """Test CryptoBotClient create_invoice sends POST request."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"invoice_id": "inv-123"}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from pydantic import SecretStr

        from src.services.cryptobot_client import CryptoBotClient

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            invoice = await client.create_invoice(amount=50.0, currency="USDT", description="Test payment")

            assert invoice["invoice_id"] == "inv-123"


@pytest.mark.asyncio
async def test_cryptobot_client_create_invoice_uses_fiat_contract_for_usd():
    """Test CryptoBotClient uses Crypto Pay fiat contract for USD invoices."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"invoice_id": "inv-123"}}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from pydantic import SecretStr

        from src.services.cryptobot_client import CryptoBotClient

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            await client.create_invoice(amount=50.0, currency="USD", description="Test payment")

        _, _, kwargs = mock_client.request.mock_calls[0]
        assert kwargs["json"]["currency_type"] == "fiat"
        assert kwargs["json"]["fiat"] == "USD"
        assert "asset" not in kwargs["json"]


@pytest.mark.asyncio
async def test_cryptobot_client_uses_testnet_base_url():
    """Test CryptoBotClient can be pointed at the official testnet endpoint."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        from pydantic import SecretStr

        from src.services.cryptobot_client import CryptoBotClient

        async with CryptoBotClient(token=SecretStr("test-token"), network="testnet") as client:
            assert client.network == "testnet"
            assert client.base_url == "https://testnet-pay.crypt.bot/api"

        _, kwargs = mock_client_cls.call_args
        assert kwargs["base_url"] == "https://testnet-pay.crypt.bot/api"


def test_cryptobot_client_rejects_unknown_network():
    """Test CryptoBotClient does not accept arbitrary payment API endpoints."""
    from pydantic import SecretStr

    from src.services.cryptobot_client import CryptoBotClient

    with pytest.raises(ValueError, match="Unsupported CryptoBot network"):
        CryptoBotClient(token=SecretStr("test-token"), network="sandbox")


@pytest.mark.asyncio
async def test_cryptobot_client_health_check():
    """Test CryptoBotClient health_check returns True when healthy."""
    with patch("src.services.cryptobot_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": [{"currency": "USDT", "amount": "100.0"}]}
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from pydantic import SecretStr

        from src.services.cryptobot_client import CryptoBotClient

        async with CryptoBotClient(token=SecretStr("test-token")) as client:
            result = await client.health_check()

            assert result is True


@pytest.mark.asyncio
async def test_cache_service_get_set():
    """Test CacheService get and set operations."""
    from src.services.cache_service import CacheService

    mock_redis = AsyncMock()
    mock_redis.get.return_value = b'{"key": "value"}'
    mock_redis.set.return_value = None

    cache = CacheService(mock_redis)

    # Test set
    await cache.set("test_key", {"key": "value"}, ttl=60)
    mock_redis.set.assert_called_once()

    # Test get
    result = await cache.get("test_key")
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_cache_service_delete():
    """Test CacheService delete operation."""
    from src.services.cache_service import CacheService

    mock_redis = AsyncMock()
    mock_redis.delete.return_value = 1

    cache = CacheService(mock_redis)

    result = await cache.delete("test_key")
    assert result is True


@pytest.mark.asyncio
async def test_redis_client_check():
    """Test redis_client check_redis returns True when healthy."""
    with patch("src.services.redis_client.Redis") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_cls.from_pool.return_value = mock_redis

        from src.services.redis_client import check_redis

        result = await check_redis()

        assert result is True
        mock_redis.ping.assert_called_once()
        mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_redis_client_check_failure():
    """Test redis_client check_redis returns False on failure."""
    with patch("src.services.redis_client.Redis") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis_cls.from_pool.return_value = mock_redis

        from src.services.redis_client import check_redis

        result = await check_redis()

        assert result is False
