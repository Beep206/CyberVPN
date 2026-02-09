"""Unit tests for Remnawave API proxy response Pydantic v2 models.

Tests cover:
- Valid instantiation with required + optional fields
- camelCase alias serialization (populate_by_name=True + alias_generator)
- from_attributes=True (ORM-style dict / SimpleNamespace construction)
- Validation rejection of invalid types
- Nested model serialization
- Edge cases: empty inputs, max values, missing optional fields
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.presentation.schemas.remnawave_responses import (
    RemnavwaveBandwidthStatsResponse,
    RemnavwaveBillingRecordResponse,
    RemnavwavePlanResponse,
    RemnawaveBaseResponse,
    RemnawaveConfigProfileResponse,
    RemnawaveHealthResponse,
    RemnawaveHostListResponse,
    RemnawaveHostResponse,
    RemnawaveInboundListResponse,
    RemnawaveInboundResponse,
    RemnawaveNodeListResponse,
    RemnawaveNodeResponse,
    RemnawavePublicKeyResponse,
    RemnawaveSettingResponse,
    RemnawaveSignPayloadResponse,
    RemnawaveSnippetResponse,
    RemnawaveSquadResponse,
    RemnawaveSubscriptionConfigResponse,
    RemnawaveSubscriptionResponse,
    RemnawaveSystemStatsResponse,
    RemnawaveUserListResponse,
    RemnawaveUserResponse,
    RemnawaveXrayConfigResponse,
    StatusMessageResponse,
)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
NOW_ISO = NOW.isoformat()


@pytest.fixture
def user_data_snake() -> dict:
    """Minimal valid user data using snake_case field names."""
    return {
        "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "username": "testuser",
        "status": "active",
        "short_uuid": "abc123",
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def user_data_camel() -> dict:
    """Minimal valid user data using camelCase aliases."""
    return {
        "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "username": "testuser",
        "status": "active",
        "shortUuid": "abc123",
        "createdAt": NOW_ISO,
        "updatedAt": NOW_ISO,
    }


@pytest.fixture
def node_data_snake() -> dict:
    """Minimal valid node data using snake_case field names."""
    return {
        "uuid": "node-uuid-1234",
        "name": "Frankfurt-01",
        "address": "10.0.0.1",
        "port": 443,
        "is_connected": True,
        "is_disabled": False,
        "is_connecting": False,
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def node_data_camel() -> dict:
    """Minimal valid node data using camelCase aliases."""
    return {
        "uuid": "node-uuid-1234",
        "name": "Frankfurt-01",
        "address": "10.0.0.1",
        "port": 443,
        "isConnected": True,
        "isDisabled": False,
        "isConnecting": False,
        "createdAt": NOW_ISO,
        "updatedAt": NOW_ISO,
    }


# ---------------------------------------------------------------------------
# RemnawaveBaseResponse
# ---------------------------------------------------------------------------


class TestRemnawaveBaseResponse:
    """Tests for the shared base response model configuration."""

    @pytest.mark.unit
    def test_from_attributes_enabled(self):
        """Verify from_attributes is True in model_config."""
        assert RemnawaveBaseResponse.model_config.get("from_attributes") is True

    @pytest.mark.unit
    def test_populate_by_name_enabled(self):
        """Verify populate_by_name is True in model_config."""
        assert RemnawaveBaseResponse.model_config.get("populate_by_name") is True


# ---------------------------------------------------------------------------
# StatusMessageResponse
# ---------------------------------------------------------------------------


class TestStatusMessageResponse:
    """Tests for the generic status + message response."""

    @pytest.mark.unit
    def test_instantiate_valid_required_only(self):
        """Arrange: provide only required 'status'. Act: instantiate. Assert: message defaults to None."""
        resp = StatusMessageResponse(status="ok")

        assert resp.status == "ok"
        assert resp.message is None

    @pytest.mark.unit
    def test_instantiate_valid_with_message(self):
        """Test instantiation with both required and optional fields."""
        resp = StatusMessageResponse(status="error", message="Something went wrong")

        assert resp.status == "error"
        assert resp.message == "Something went wrong"

    @pytest.mark.unit
    def test_validation_rejects_missing_status(self):
        """Test that omitting the required 'status' field raises ValidationError."""
        with pytest.raises(ValidationError):
            StatusMessageResponse(message="orphan message")

    @pytest.mark.unit
    def test_validation_rejects_invalid_status_type(self):
        """Test that passing a non-string for 'status' raises ValidationError."""
        with pytest.raises(ValidationError):
            StatusMessageResponse(status=["not", "a", "string"])

    @pytest.mark.unit
    def test_message_max_length_exceeded(self):
        """Test that message longer than max_length=1000 is rejected."""
        with pytest.raises(ValidationError):
            StatusMessageResponse(status="ok", message="x" * 1001)

    @pytest.mark.unit
    def test_message_at_max_length(self):
        """Test that message exactly at max_length=1000 is accepted."""
        resp = StatusMessageResponse(status="ok", message="x" * 1000)
        assert len(resp.message) == 1000

    @pytest.mark.unit
    def test_from_attributes_orm_style(self):
        """Test constructing from a SimpleNamespace (ORM-style object)."""
        obj = SimpleNamespace(status="ok", message="done")
        resp = StatusMessageResponse.model_validate(obj, from_attributes=True)

        assert resp.status == "ok"
        assert resp.message == "done"


# ---------------------------------------------------------------------------
# RemnawaveUserResponse
# ---------------------------------------------------------------------------


class TestRemnawaveUserResponse:
    """Tests for the full user response model."""

    @pytest.mark.unit
    def test_instantiate_valid_snake_case(self, user_data_snake):
        """Test instantiation with snake_case field names (populate_by_name)."""
        user = RemnawaveUserResponse(**user_data_snake)

        assert user.uuid == user_data_snake["uuid"]
        assert user.username == "testuser"
        assert user.status == "active"
        assert user.short_uuid == "abc123"
        assert user.created_at == NOW

    @pytest.mark.unit
    def test_instantiate_valid_camel_case(self, user_data_camel):
        """Test instantiation with camelCase alias names."""
        user = RemnawaveUserResponse(**user_data_camel)

        assert user.uuid == user_data_camel["uuid"]
        assert user.username == "testuser"
        assert user.short_uuid == "abc123"

    @pytest.mark.unit
    def test_optional_fields_default_to_none(self, user_data_snake):
        """Test that all optional fields default to None when not provided."""
        user = RemnawaveUserResponse(**user_data_snake)

        assert user.subscription_uuid is None
        assert user.subscription_url is None
        assert user.expire_at is None
        assert user.traffic_limit_bytes is None
        assert user.used_traffic_bytes is None
        assert user.download_bytes is None
        assert user.upload_bytes is None
        assert user.lifetime_used_traffic_bytes is None
        assert user.online_at is None
        assert user.sub_last_user_agent is None
        assert user.sub_revoked_at is None
        assert user.last_traffic_reset_at is None
        assert user.telegram_id is None
        assert user.email is None
        assert user.hwid_device_limit is None
        assert user.active_user_inbounds is None

    @pytest.mark.unit
    def test_full_user_with_all_fields(self, user_data_snake):
        """Test instantiation with every field populated."""
        full_data = {
            **user_data_snake,
            "subscription_uuid": "sub-uuid-1",
            "subscription_url": "https://vpn.example.com/sub/abc",
            "expire_at": NOW,
            "traffic_limit_bytes": 10_737_418_240,  # 10 GB
            "used_traffic_bytes": 5_000_000_000,
            "download_bytes": 3_000_000_000,
            "upload_bytes": 2_000_000_000,
            "lifetime_used_traffic_bytes": 100_000_000_000,
            "online_at": NOW,
            "sub_last_user_agent": "clash/1.0",
            "sub_revoked_at": None,
            "last_traffic_reset_at": NOW,
            "telegram_id": 123456789,
            "email": "user@example.com",
            "hwid_device_limit": 5,
            "active_user_inbounds": [{"tag": "vless-tcp", "nodeUuid": "node-1"}],
        }
        user = RemnawaveUserResponse(**full_data)

        assert user.traffic_limit_bytes == 10_737_418_240
        assert user.telegram_id == 123456789
        assert user.active_user_inbounds == [{"tag": "vless-tcp", "nodeUuid": "node-1"}]

    @pytest.mark.unit
    def test_camel_case_serialization(self, user_data_snake):
        """Test that model_dump(by_alias=True) produces camelCase keys."""
        user = RemnawaveUserResponse(**user_data_snake)
        dumped = user.model_dump(by_alias=True)

        assert "shortUuid" in dumped
        assert "createdAt" in dumped
        assert "updatedAt" in dumped
        assert "subscriptionUuid" in dumped
        assert "trafficLimitBytes" in dumped
        assert "usedTrafficBytes" in dumped
        assert "downloadBytes" in dumped
        assert "uploadBytes" in dumped
        assert "lifetimeUsedTrafficBytes" in dumped
        assert "onlineAt" in dumped
        assert "subLastUserAgent" in dumped
        assert "subRevokedAt" in dumped
        assert "lastTrafficResetAt" in dumped
        assert "telegramId" in dumped
        assert "hwidDeviceLimit" in dumped
        assert "activeUserInbounds" in dumped

    @pytest.mark.unit
    def test_validation_rejects_missing_required_uuid(self, user_data_snake):
        """Test that missing required 'uuid' raises ValidationError."""
        del user_data_snake["uuid"]
        with pytest.raises(ValidationError):
            RemnawaveUserResponse(**user_data_snake)

    @pytest.mark.unit
    def test_validation_rejects_missing_required_username(self, user_data_snake):
        """Test that missing required 'username' raises ValidationError."""
        del user_data_snake["username"]
        with pytest.raises(ValidationError):
            RemnawaveUserResponse(**user_data_snake)

    @pytest.mark.unit
    def test_validation_rejects_string_for_traffic_limit(self, user_data_snake):
        """Test that string where int expected (traffic_limit_bytes) raises ValidationError."""
        user_data_snake["traffic_limit_bytes"] = "not-a-number"
        with pytest.raises(ValidationError):
            RemnawaveUserResponse(**user_data_snake)

    @pytest.mark.unit
    def test_validation_rejects_string_for_telegram_id(self, user_data_snake):
        """Test that non-int value for telegram_id raises ValidationError."""
        user_data_snake["telegram_id"] = "not-an-int"
        with pytest.raises(ValidationError):
            RemnawaveUserResponse(**user_data_snake)

    @pytest.mark.unit
    def test_from_attributes_orm_style(self, user_data_snake):
        """Test constructing from SimpleNamespace (ORM/dataclass compat)."""
        obj = SimpleNamespace(**user_data_snake)
        user = RemnawaveUserResponse.model_validate(obj, from_attributes=True)

        assert user.uuid == user_data_snake["uuid"]
        assert user.username == "testuser"

    @pytest.mark.unit
    def test_max_traffic_value(self, user_data_snake):
        """Test with very large traffic byte values (edge case)."""
        user_data_snake["traffic_limit_bytes"] = 2**63 - 1  # max int64
        user = RemnawaveUserResponse(**user_data_snake)

        assert user.traffic_limit_bytes == 2**63 - 1


# ---------------------------------------------------------------------------
# RemnawaveUserListResponse (nested)
# ---------------------------------------------------------------------------


class TestRemnawaveUserListResponse:
    """Tests for the user list wrapper response with nested models."""

    @pytest.mark.unit
    def test_instantiate_empty_list(self):
        """Test instantiation with empty user list."""
        resp = RemnawaveUserListResponse(response=[], total=0)

        assert resp.response == []
        assert resp.total == 0

    @pytest.mark.unit
    def test_instantiate_default_factory(self):
        """Test that response defaults to empty list when omitted."""
        resp = RemnawaveUserListResponse()

        assert resp.response == []
        assert resp.total is None

    @pytest.mark.unit
    def test_nested_user_serialization(self, user_data_snake):
        """Test that nested RemnawaveUserResponse models serialize correctly."""
        resp = RemnawaveUserListResponse(
            response=[RemnawaveUserResponse(**user_data_snake)],
            total=1,
        )

        assert len(resp.response) == 1
        assert resp.response[0].username == "testuser"
        assert resp.total == 1

    @pytest.mark.unit
    def test_nested_camel_case_dump(self, user_data_snake):
        """Test that nested models produce camelCase keys via model_dump."""
        resp = RemnawaveUserListResponse(
            response=[RemnawaveUserResponse(**user_data_snake)],
            total=1,
        )
        dumped = resp.model_dump(by_alias=True)

        assert "shortUuid" in dumped["response"][0]
        assert "createdAt" in dumped["response"][0]

    @pytest.mark.unit
    def test_validation_rejects_invalid_nested_type(self):
        """Test that invalid data in the nested list raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveUserListResponse(response=["not-a-user-object"], total=1)


# ---------------------------------------------------------------------------
# RemnawaveNodeResponse
# ---------------------------------------------------------------------------


class TestRemnawaveNodeResponse:
    """Tests for the node/server response model."""

    @pytest.mark.unit
    def test_instantiate_valid_snake_case(self, node_data_snake):
        """Test instantiation with snake_case field names."""
        node = RemnawaveNodeResponse(**node_data_snake)

        assert node.uuid == "node-uuid-1234"
        assert node.name == "Frankfurt-01"
        assert node.port == 443
        assert node.is_connected is True
        assert node.is_disabled is False

    @pytest.mark.unit
    def test_instantiate_valid_camel_case(self, node_data_camel):
        """Test instantiation with camelCase alias names."""
        node = RemnawaveNodeResponse(**node_data_camel)

        assert node.is_connected is True
        assert node.is_disabled is False
        assert node.is_connecting is False

    @pytest.mark.unit
    def test_optional_fields_default_to_none(self, node_data_snake):
        """Test that optional node fields default to None."""
        node = RemnawaveNodeResponse(**node_data_snake)

        assert node.country_code is None
        assert node.traffic_limit_bytes is None
        assert node.used_traffic_bytes is None
        assert node.inbound_count is None
        assert node.users_online is None
        assert node.xray_version is None
        assert node.vpn_protocol is None
        assert node.consumption_multiplier is None
        assert node.notification_enabled is None

    @pytest.mark.unit
    def test_node_with_all_optional_fields(self, node_data_snake):
        """Test node with all optional fields populated."""
        full_data = {
            **node_data_snake,
            "country_code": "DE",
            "traffic_limit_bytes": 1_099_511_627_776,  # 1 TB
            "used_traffic_bytes": 500_000_000_000,
            "inbound_count": 3,
            "users_online": 42,
            "xray_version": "1.8.4",
            "vpn_protocol": "vless",
            "consumption_multiplier": 1.5,
            "notification_enabled": True,
        }
        node = RemnawaveNodeResponse(**full_data)

        assert node.country_code == "DE"
        assert node.consumption_multiplier == 1.5
        assert node.users_online == 42

    @pytest.mark.unit
    def test_camel_case_serialization(self, node_data_snake):
        """Test that model_dump(by_alias=True) produces camelCase keys."""
        node = RemnawaveNodeResponse(**node_data_snake)
        dumped = node.model_dump(by_alias=True)

        assert "isConnected" in dumped
        assert "isDisabled" in dumped
        assert "isConnecting" in dumped
        assert "createdAt" in dumped
        assert "updatedAt" in dumped
        assert "countryCode" in dumped
        assert "trafficLimitBytes" in dumped

    @pytest.mark.unit
    def test_validation_rejects_string_for_port(self, node_data_snake):
        """Test that string for 'port' raises ValidationError."""
        node_data_snake["port"] = "not-a-port"
        with pytest.raises(ValidationError):
            RemnawaveNodeResponse(**node_data_snake)

    @pytest.mark.unit
    def test_validation_rejects_missing_required_name(self, node_data_snake):
        """Test that missing required 'name' raises ValidationError."""
        del node_data_snake["name"]
        with pytest.raises(ValidationError):
            RemnawaveNodeResponse(**node_data_snake)

    @pytest.mark.unit
    def test_from_attributes_orm_style(self, node_data_snake):
        """Test constructing from SimpleNamespace (ORM/dataclass compat)."""
        obj = SimpleNamespace(**node_data_snake)
        node = RemnawaveNodeResponse.model_validate(obj, from_attributes=True)

        assert node.name == "Frankfurt-01"
        assert node.is_connected is True

    @pytest.mark.unit
    def test_default_values_for_optional_with_defaults(self):
        """Test that address and port have correct defaults when not provided."""
        node = RemnawaveNodeResponse(
            uuid="uuid-1",
            name="Test",
            created_at=NOW,
            updated_at=NOW,
        )

        assert node.address == ""
        assert node.port == 0
        assert node.is_connected is False
        assert node.is_disabled is False
        assert node.is_connecting is False


# ---------------------------------------------------------------------------
# RemnawaveNodeListResponse (nested)
# ---------------------------------------------------------------------------


class TestRemnawaveNodeListResponse:
    """Tests for the node list wrapper response."""

    @pytest.mark.unit
    def test_instantiate_empty_list(self):
        """Test instantiation with empty node list."""
        resp = RemnawaveNodeListResponse(response=[])
        assert resp.response == []

    @pytest.mark.unit
    def test_default_factory_produces_empty_list(self):
        """Test that response defaults to empty list."""
        resp = RemnawaveNodeListResponse()
        assert resp.response == []

    @pytest.mark.unit
    def test_nested_node_serialization(self, node_data_snake):
        """Test nested nodes serialize correctly with camelCase."""
        resp = RemnawaveNodeListResponse(
            response=[RemnawaveNodeResponse(**node_data_snake)]
        )
        dumped = resp.model_dump(by_alias=True)

        assert len(dumped["response"]) == 1
        assert "isConnected" in dumped["response"][0]


# ---------------------------------------------------------------------------
# RemnawaveInboundResponse
# ---------------------------------------------------------------------------


class TestRemnawaveInboundResponse:
    """Tests for the inbound (protocol listener) response model."""

    @pytest.mark.unit
    def test_instantiate_valid_minimal(self):
        """Test instantiation with required fields only."""
        inbound = RemnawaveInboundResponse(
            uuid="inbound-uuid-1",
            tag="vless-tcp-reality",
            protocol="vless",
            port=443,
        )

        assert inbound.uuid == "inbound-uuid-1"
        assert inbound.tag == "vless-tcp-reality"
        assert inbound.protocol == "vless"
        assert inbound.port == 443
        assert inbound.network is None
        assert inbound.settings is None
        assert inbound.stream_settings is None

    @pytest.mark.unit
    def test_instantiate_with_nested_dicts(self):
        """Test instantiation with nested dict fields."""
        inbound = RemnawaveInboundResponse(
            uuid="inbound-uuid-2",
            tag="vmess-ws",
            protocol="vmess",
            port=8080,
            network="ws",
            security="tls",
            settings={"clients": [{"id": "test-uuid"}]},
            stream_settings={"wsSettings": {"path": "/vmess"}},
            sniffing={"enabled": True, "destOverride": ["http", "tls"]},
            node_uuid="node-uuid-1",
        )

        assert inbound.settings["clients"][0]["id"] == "test-uuid"
        assert inbound.stream_settings["wsSettings"]["path"] == "/vmess"
        assert inbound.node_uuid == "node-uuid-1"

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization for inbound."""
        inbound = RemnawaveInboundResponse(
            uuid="inbound-1",
            tag="test",
            protocol="vless",
            port=443,
            stream_settings={"key": "val"},
            node_uuid="node-1",
        )
        dumped = inbound.model_dump(by_alias=True)

        assert "streamSettings" in dumped
        assert "nodeUuid" in dumped

    @pytest.mark.unit
    def test_instantiate_from_camel_case_aliases(self):
        """Test instantiation using camelCase alias names."""
        inbound = RemnawaveInboundResponse(
            uuid="inbound-1",
            tag="test",
            protocol="vless",
            port=443,
            streamSettings={"key": "val"},
            nodeUuid="node-1",
        )

        assert inbound.stream_settings == {"key": "val"}
        assert inbound.node_uuid == "node-1"

    @pytest.mark.unit
    def test_validation_rejects_missing_required_tag(self):
        """Test that missing required 'tag' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveInboundResponse(uuid="inbound-1", protocol="vless", port=443)

    @pytest.mark.unit
    def test_validation_rejects_string_for_port(self):
        """Test that non-int port raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveInboundResponse(
                uuid="inbound-1", tag="test", protocol="vless", port="not-int"
            )


# ---------------------------------------------------------------------------
# RemnawaveInboundListResponse
# ---------------------------------------------------------------------------


class TestRemnawaveInboundListResponse:
    """Tests for the inbound list wrapper response."""

    @pytest.mark.unit
    def test_default_factory(self):
        """Test that response defaults to empty list."""
        resp = RemnawaveInboundListResponse()
        assert resp.response == []

    @pytest.mark.unit
    def test_nested_serialization(self):
        """Test nested inbound models serialize correctly."""
        inbound = RemnawaveInboundResponse(
            uuid="ib-1", tag="test", protocol="vless", port=443
        )
        resp = RemnawaveInboundListResponse(response=[inbound])

        assert len(resp.response) == 1
        assert resp.response[0].tag == "test"


# ---------------------------------------------------------------------------
# RemnawaveHostResponse
# ---------------------------------------------------------------------------


class TestRemnawaveHostResponse:
    """Tests for the host entry response model."""

    @pytest.mark.unit
    def test_instantiate_valid_minimal(self):
        """Test instantiation with only the required uuid field."""
        host = RemnawaveHostResponse(uuid="host-uuid-1")

        assert host.uuid == "host-uuid-1"
        assert host.inbound_uuid is None
        assert host.remark is None
        assert host.address == ""
        assert host.port is None
        assert host.is_disabled is False
        assert host.alpn is None

    @pytest.mark.unit
    def test_instantiate_full(self):
        """Test instantiation with all fields populated."""
        host = RemnawaveHostResponse(
            uuid="host-uuid-2",
            inbound_uuid="inbound-uuid-1",
            remark="Main Entry",
            address="vpn.example.com",
            port=443,
            sni="vpn.example.com",
            host="vpn.example.com",
            path="/ws",
            alpn=["h2", "http/1.1"],
            fingerprint="chrome",
            is_disabled=False,
            security="tls",
            reality_public_key="pub-key-abc",
            reality_short_id="short-id-123",
            reality_private_key="priv-key-xyz",
        )

        assert host.remark == "Main Entry"
        assert host.alpn == ["h2", "http/1.1"]
        assert host.reality_public_key == "pub-key-abc"

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization for host."""
        host = RemnawaveHostResponse(
            uuid="host-1",
            inbound_uuid="ib-1",
            is_disabled=True,
            reality_public_key="key",
            reality_short_id="sid",
            reality_private_key="pkey",
        )
        dumped = host.model_dump(by_alias=True)

        assert "inboundUuid" in dumped
        assert "isDisabled" in dumped
        assert "realityPublicKey" in dumped
        assert "realityShortId" in dumped
        assert "realityPrivateKey" in dumped

    @pytest.mark.unit
    def test_from_attributes_orm_style(self):
        """Test constructing host from SimpleNamespace (ORM compat)."""
        obj = SimpleNamespace(
            uuid="host-1",
            inbound_uuid=None,
            remark="test",
            address="1.2.3.4",
            port=443,
            sni=None,
            host=None,
            path=None,
            alpn=None,
            fingerprint=None,
            is_disabled=False,
            security=None,
            reality_public_key=None,
            reality_short_id=None,
            reality_private_key=None,
        )
        host = RemnawaveHostResponse.model_validate(obj, from_attributes=True)

        assert host.uuid == "host-1"
        assert host.remark == "test"


# ---------------------------------------------------------------------------
# RemnawaveHostListResponse
# ---------------------------------------------------------------------------


class TestRemnawaveHostListResponse:
    """Tests for the host list wrapper response."""

    @pytest.mark.unit
    def test_default_factory(self):
        """Test that response defaults to empty list."""
        resp = RemnawaveHostListResponse()
        assert resp.response == []


# ---------------------------------------------------------------------------
# RemnawaveSubscriptionResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSubscriptionResponse:
    """Tests for the subscription template response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        sub = RemnawaveSubscriptionResponse(
            uuid="sub-uuid-1",
            name="Default Clash",
            template_type="clash",
        )

        assert sub.uuid == "sub-uuid-1"
        assert sub.name == "Default Clash"
        assert sub.template_type == "clash"
        assert sub.host_uuid is None
        assert sub.inbound_tag is None
        assert sub.flow is None
        assert sub.config_data is None

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization."""
        sub = RemnawaveSubscriptionResponse(
            uuid="sub-1",
            name="Test",
            template_type="v2ray",
            host_uuid="host-1",
            inbound_tag="vless-tcp",
            config_data={"key": "value"},
        )
        dumped = sub.model_dump(by_alias=True)

        assert "templateType" in dumped
        assert "hostUuid" in dumped
        assert "inboundTag" in dumped
        assert "configData" in dumped

    @pytest.mark.unit
    def test_instantiate_from_camel_case(self):
        """Test instantiation using camelCase alias names."""
        sub = RemnawaveSubscriptionResponse(
            uuid="sub-1",
            name="Test",
            templateType="clash",
            hostUuid="host-1",
            inboundTag="vmess-ws",
        )

        assert sub.template_type == "clash"
        assert sub.host_uuid == "host-1"
        assert sub.inbound_tag == "vmess-ws"

    @pytest.mark.unit
    def test_validation_rejects_missing_required_name(self):
        """Test that missing required 'name' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveSubscriptionResponse(uuid="sub-1", template_type="clash")


# ---------------------------------------------------------------------------
# RemnawaveSubscriptionConfigResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSubscriptionConfigResponse:
    """Tests for the generated subscription config response."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required config field."""
        resp = RemnawaveSubscriptionConfigResponse(
            config="vless://uuid@host:443?security=tls"
        )

        assert resp.config.startswith("vless://")
        assert resp.subscription_url is None

    @pytest.mark.unit
    def test_subscription_url_max_length(self):
        """Test that subscription_url exceeding max_length=5000 is rejected."""
        with pytest.raises(ValidationError):
            RemnawaveSubscriptionConfigResponse(
                config="valid-config",
                subscription_url="x" * 5001,
            )

    @pytest.mark.unit
    def test_subscription_url_at_max_length(self):
        """Test that subscription_url at exactly max_length=5000 is accepted."""
        resp = RemnawaveSubscriptionConfigResponse(
            config="valid-config",
            subscription_url="x" * 5000,
        )
        assert len(resp.subscription_url) == 5000

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias for subscriptionUrl."""
        resp = RemnawaveSubscriptionConfigResponse(
            config="config-data",
            subscription_url="https://sub.example.com/abc",
        )
        dumped = resp.model_dump(by_alias=True)

        assert "subscriptionUrl" in dumped


# ---------------------------------------------------------------------------
# RemnavwavePlanResponse
# ---------------------------------------------------------------------------


class TestRemnavwavePlanResponse:
    """Tests for the subscription plan response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        plan = RemnavwavePlanResponse(
            uuid="plan-uuid-1",
            name="Premium Monthly",
            price=9.99,
            currency="USD",
            duration_days=30,
        )

        assert plan.uuid == "plan-uuid-1"
        assert plan.name == "Premium Monthly"
        assert plan.price == 9.99
        assert plan.currency == "USD"
        assert plan.duration_days == 30
        assert plan.is_active is True  # default

    @pytest.mark.unit
    def test_optional_fields(self):
        """Test optional fields default to None."""
        plan = RemnavwavePlanResponse(
            uuid="plan-1", name="Basic", price=0.0, currency="EUR", duration_days=7
        )

        assert plan.data_limit_gb is None
        assert plan.max_devices is None
        assert plan.features is None

    @pytest.mark.unit
    def test_full_plan_with_features(self):
        """Test plan with all fields including features list."""
        plan = RemnavwavePlanResponse(
            uuid="plan-2",
            name="Ultimate",
            price=29.99,
            currency="USD",
            duration_days=365,
            data_limit_gb=None,
            max_devices=10,
            features=["unlimited_traffic", "priority_support", "dedicated_ip"],
            is_active=True,
        )

        assert plan.max_devices == 10
        assert len(plan.features) == 3
        assert "dedicated_ip" in plan.features

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization for plan."""
        plan = RemnavwavePlanResponse(
            uuid="plan-1",
            name="Test",
            price=1.0,
            currency="USD",
            duration_days=30,
            data_limit_gb=100,
            max_devices=5,
            is_active=False,
        )
        dumped = plan.model_dump(by_alias=True)

        assert "durationDays" in dumped
        assert "dataLimitGb" in dumped
        assert "maxDevices" in dumped
        assert "isActive" in dumped

    @pytest.mark.unit
    def test_validation_rejects_string_for_price(self):
        """Test that string for 'price' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnavwavePlanResponse(
                uuid="plan-1",
                name="Test",
                price="not-a-float",
                currency="USD",
                duration_days=30,
            )

    @pytest.mark.unit
    def test_validation_rejects_string_for_duration_days(self):
        """Test that string for 'duration_days' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnavwavePlanResponse(
                uuid="plan-1",
                name="Test",
                price=9.99,
                currency="USD",
                duration_days="not-an-int",
            )


# ---------------------------------------------------------------------------
# RemnawaveSettingResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSettingResponse:
    """Tests for the system setting key-value response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        setting = RemnawaveSettingResponse(
            id=1, key="MAX_CONNECTIONS", value=100
        )

        assert setting.id == 1
        assert setting.key == "MAX_CONNECTIONS"
        assert setting.value == 100
        assert setting.description is None
        assert setting.is_public is False  # default

    @pytest.mark.unit
    def test_value_accepts_any_json_type(self):
        """Test that 'value' field accepts various JSON-compatible types."""
        # Integer
        s1 = RemnawaveSettingResponse(id=1, key="k1", value=42)
        assert s1.value == 42

        # String
        s2 = RemnawaveSettingResponse(id=2, key="k2", value="hello")
        assert s2.value == "hello"

        # Boolean
        s3 = RemnawaveSettingResponse(id=3, key="k3", value=True)
        assert s3.value is True

        # List
        s4 = RemnawaveSettingResponse(id=4, key="k4", value=[1, 2, 3])
        assert s4.value == [1, 2, 3]

        # Dict
        s5 = RemnawaveSettingResponse(id=5, key="k5", value={"nested": "obj"})
        assert s5.value == {"nested": "obj"}

        # None
        s6 = RemnawaveSettingResponse(id=6, key="k6", value=None)
        assert s6.value is None

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias for isPublic."""
        setting = RemnawaveSettingResponse(
            id=1, key="test", value="val", is_public=True
        )
        dumped = setting.model_dump(by_alias=True)

        assert "isPublic" in dumped
        assert dumped["isPublic"] is True

    @pytest.mark.unit
    def test_validation_rejects_missing_required_key(self):
        """Test that missing required 'key' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveSettingResponse(id=1, value="test")

    @pytest.mark.unit
    def test_validation_rejects_string_for_id(self):
        """Test that non-int 'id' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveSettingResponse(id="not-int", key="k", value="v")


# ---------------------------------------------------------------------------
# RemnawaveSystemStatsResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSystemStatsResponse:
    """Tests for the aggregated system statistics response model."""

    @pytest.mark.unit
    def test_instantiate_defaults(self):
        """Test that all fields default to 0 when not provided."""
        stats = RemnawaveSystemStatsResponse()

        assert stats.total_users == 0
        assert stats.active_users == 0
        assert stats.total_servers == 0
        assert stats.online_servers == 0
        assert stats.total_traffic_bytes == 0

    @pytest.mark.unit
    def test_instantiate_with_values(self):
        """Test instantiation with explicit values."""
        stats = RemnawaveSystemStatsResponse(
            total_users=1000,
            active_users=750,
            total_servers=10,
            online_servers=8,
            total_traffic_bytes=5_000_000_000_000,
        )

        assert stats.total_users == 1000
        assert stats.active_users == 750
        assert stats.total_traffic_bytes == 5_000_000_000_000

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization."""
        stats = RemnawaveSystemStatsResponse(total_users=10, active_users=5)
        dumped = stats.model_dump(by_alias=True)

        assert "totalUsers" in dumped
        assert "activeUsers" in dumped
        assert "totalServers" in dumped
        assert "onlineServers" in dumped
        assert "totalTrafficBytes" in dumped

    @pytest.mark.unit
    def test_instantiate_from_camel_case(self):
        """Test instantiation using camelCase alias names."""
        stats = RemnawaveSystemStatsResponse(
            totalUsers=100, activeUsers=80, totalServers=5, onlineServers=4, totalTrafficBytes=999
        )

        assert stats.total_users == 100
        assert stats.active_users == 80

    @pytest.mark.unit
    def test_validation_rejects_string_for_total_users(self):
        """Test that string for total_users raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveSystemStatsResponse(total_users="many")


# ---------------------------------------------------------------------------
# RemnavwaveBandwidthStatsResponse
# ---------------------------------------------------------------------------


class TestRemnavwaveBandwidthStatsResponse:
    """Tests for the bandwidth analytics response model."""

    @pytest.mark.unit
    def test_instantiate_defaults(self):
        """Test that bytes_in and bytes_out default to 0."""
        bw = RemnavwaveBandwidthStatsResponse()

        assert bw.bytes_in == 0
        assert bw.bytes_out == 0
        assert bw.total_bytes is None

    @pytest.mark.unit
    def test_instantiate_with_values(self):
        """Test instantiation with explicit values."""
        bw = RemnavwaveBandwidthStatsResponse(
            bytes_in=1_000_000, bytes_out=2_000_000, total_bytes=3_000_000
        )

        assert bw.bytes_in == 1_000_000
        assert bw.bytes_out == 2_000_000
        assert bw.total_bytes == 3_000_000

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization."""
        bw = RemnavwaveBandwidthStatsResponse(bytes_in=100, bytes_out=200)
        dumped = bw.model_dump(by_alias=True)

        assert "bytesIn" in dumped
        assert "bytesOut" in dumped
        assert "totalBytes" in dumped


# ---------------------------------------------------------------------------
# RemnawaveXrayConfigResponse
# ---------------------------------------------------------------------------


class TestRemnawaveXrayConfigResponse:
    """Tests for the Xray-core configuration response model."""

    @pytest.mark.unit
    def test_instantiate_all_none(self):
        """Test instantiation with all fields as None (defaults)."""
        cfg = RemnawaveXrayConfigResponse()

        assert cfg.log is None
        assert cfg.inbounds is None
        assert cfg.outbounds is None
        assert cfg.routing is None
        assert cfg.dns is None
        assert cfg.policy is None

    @pytest.mark.unit
    def test_instantiate_with_nested_dicts(self):
        """Test instantiation with realistic Xray config data."""
        cfg = RemnawaveXrayConfigResponse(
            log={"loglevel": "warning"},
            inbounds=[{"listen": "0.0.0.0", "port": 443, "protocol": "vless"}],
            outbounds=[{"protocol": "freedom", "tag": "direct"}],
            routing={"rules": [{"type": "field", "outboundTag": "direct"}]},
            dns={"servers": ["8.8.8.8", "1.1.1.1"]},
            policy={"system": {"statsInboundUplink": True}},
        )

        assert cfg.log["loglevel"] == "warning"
        assert len(cfg.inbounds) == 1
        assert cfg.outbounds[0]["protocol"] == "freedom"
        assert cfg.routing["rules"][0]["type"] == "field"

    @pytest.mark.unit
    def test_validation_rejects_invalid_type_for_log(self):
        """Test that a non-dict type for 'log' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveXrayConfigResponse(log="not-a-dict")


# ---------------------------------------------------------------------------
# RemnavwaveBillingRecordResponse
# ---------------------------------------------------------------------------


class TestRemnavwaveBillingRecordResponse:
    """Tests for the billing / payment record response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        record = RemnavwaveBillingRecordResponse(
            uuid="billing-uuid-1",
            user_uuid="user-uuid-1",
            amount=9.99,
            currency="USD",
            status="completed",
        )

        assert record.uuid == "billing-uuid-1"
        assert record.user_uuid == "user-uuid-1"
        assert record.amount == 9.99
        assert record.payment_method is None
        assert record.created_at is None

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization for billing record."""
        record = RemnavwaveBillingRecordResponse(
            uuid="b-1",
            user_uuid="u-1",
            amount=5.0,
            currency="EUR",
            status="pending",
            payment_method="stripe",
            created_at=NOW,
        )
        dumped = record.model_dump(by_alias=True)

        assert "userUuid" in dumped
        assert "paymentMethod" in dumped
        assert "createdAt" in dumped

    @pytest.mark.unit
    def test_validation_rejects_missing_required_amount(self):
        """Test that missing required 'amount' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnavwaveBillingRecordResponse(
                uuid="b-1", user_uuid="u-1", currency="USD", status="pending"
            )

    @pytest.mark.unit
    def test_validation_rejects_string_for_amount(self):
        """Test that non-float 'amount' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnavwaveBillingRecordResponse(
                uuid="b-1",
                user_uuid="u-1",
                amount="not-a-float",
                currency="USD",
                status="pending",
            )


# ---------------------------------------------------------------------------
# RemnawaveConfigProfileResponse
# ---------------------------------------------------------------------------


class TestRemnawaveConfigProfileResponse:
    """Tests for the configuration profile response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        profile = RemnawaveConfigProfileResponse(
            uuid="profile-uuid-1",
            name="Clash Config",
            profile_type="clash",
            content="proxies:\n  - name: proxy1",
        )

        assert profile.uuid == "profile-uuid-1"
        assert profile.name == "Clash Config"
        assert profile.profile_type == "clash"
        assert profile.is_default is False  # default
        assert profile.description is None

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization."""
        profile = RemnawaveConfigProfileResponse(
            uuid="p-1",
            name="Test",
            profile_type="v2ray",
            content="{}",
            is_default=True,
        )
        dumped = profile.model_dump(by_alias=True)

        assert "profileType" in dumped
        assert "isDefault" in dumped
        assert dumped["isDefault"] is True

    @pytest.mark.unit
    def test_instantiate_from_camel_case(self):
        """Test instantiation using camelCase alias names."""
        profile = RemnawaveConfigProfileResponse(
            uuid="p-1",
            name="Test",
            profileType="clash",
            content="data",
            isDefault=True,
        )

        assert profile.profile_type == "clash"
        assert profile.is_default is True

    @pytest.mark.unit
    def test_validation_rejects_missing_required_content(self):
        """Test that missing required 'content' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveConfigProfileResponse(
                uuid="p-1", name="Test", profile_type="clash"
            )


# ---------------------------------------------------------------------------
# RemnawaveSnippetResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSnippetResponse:
    """Tests for the configuration snippet response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        snippet = RemnawaveSnippetResponse(
            uuid="snippet-uuid-1",
            name="Block Ads",
            snippet_type="routing_rule",
            content='{"rules": []}',
        )

        assert snippet.uuid == "snippet-uuid-1"
        assert snippet.name == "Block Ads"
        assert snippet.is_active is True  # default
        assert snippet.order is None

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization."""
        snippet = RemnawaveSnippetResponse(
            uuid="s-1",
            name="Test",
            snippet_type="dns",
            content="data",
            is_active=False,
        )
        dumped = snippet.model_dump(by_alias=True)

        assert "snippetType" in dumped
        assert "isActive" in dumped
        assert dumped["isActive"] is False

    @pytest.mark.unit
    def test_from_attributes_orm_style(self):
        """Test constructing from SimpleNamespace."""
        obj = SimpleNamespace(
            uuid="s-1",
            name="Test",
            snippet_type="routing",
            content="{}",
            is_active=True,
            order=5,
        )
        snippet = RemnawaveSnippetResponse.model_validate(obj, from_attributes=True)

        assert snippet.order == 5
        assert snippet.is_active is True


# ---------------------------------------------------------------------------
# RemnawaveSquadResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSquadResponse:
    """Tests for the squad (user group) response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required fields."""
        squad = RemnawaveSquadResponse(
            uuid="squad-uuid-1",
            name="Premium Users",
            squad_type="internal",
        )

        assert squad.uuid == "squad-uuid-1"
        assert squad.name == "Premium Users"
        assert squad.squad_type == "internal"
        assert squad.is_active is True  # default
        assert squad.max_members is None
        assert squad.description is None
        assert squad.member_count is None

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias serialization."""
        squad = RemnawaveSquadResponse(
            uuid="sq-1",
            name="Test",
            squad_type="external",
            max_members=50,
            is_active=False,
            member_count=10,
        )
        dumped = squad.model_dump(by_alias=True)

        assert "squadType" in dumped
        assert "maxMembers" in dumped
        assert "isActive" in dumped
        assert "memberCount" in dumped

    @pytest.mark.unit
    def test_validation_rejects_missing_required_squad_type(self):
        """Test that missing required 'squad_type' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveSquadResponse(uuid="sq-1", name="Test")


# ---------------------------------------------------------------------------
# RemnawavePublicKeyResponse
# ---------------------------------------------------------------------------


class TestRemnawavePublicKeyResponse:
    """Tests for the public key response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required public_key."""
        resp = RemnawavePublicKeyResponse(
            public_key="-----BEGIN PUBLIC KEY-----\nMIIBIjANBg..."
        )

        assert resp.public_key.startswith("-----BEGIN PUBLIC KEY-----")
        assert resp.algorithm == "RS256"  # default

    @pytest.mark.unit
    def test_custom_algorithm(self):
        """Test instantiation with custom algorithm."""
        resp = RemnawavePublicKeyResponse(
            public_key="key-data",
            algorithm="ES256",
        )

        assert resp.algorithm == "ES256"

    @pytest.mark.unit
    def test_camel_case_serialization(self):
        """Test camelCase alias for publicKey."""
        resp = RemnawavePublicKeyResponse(public_key="key-data")
        dumped = resp.model_dump(by_alias=True)

        assert "publicKey" in dumped

    @pytest.mark.unit
    def test_instantiate_from_camel_case(self):
        """Test instantiation using camelCase alias."""
        resp = RemnawavePublicKeyResponse(publicKey="key-data")

        assert resp.public_key == "key-data"

    @pytest.mark.unit
    def test_validation_rejects_missing_public_key(self):
        """Test that missing required 'public_key' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawavePublicKeyResponse(algorithm="RS256")


# ---------------------------------------------------------------------------
# RemnawaveSignPayloadResponse
# ---------------------------------------------------------------------------


class TestRemnawaveSignPayloadResponse:
    """Tests for the signed payload response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required signature."""
        resp = RemnawaveSignPayloadResponse(signature="base64-encoded-sig")

        assert resp.signature == "base64-encoded-sig"
        assert resp.algorithm == "RS256"  # default

    @pytest.mark.unit
    def test_custom_algorithm(self):
        """Test instantiation with custom algorithm."""
        resp = RemnawaveSignPayloadResponse(
            signature="sig-data",
            algorithm="ES512",
        )

        assert resp.algorithm == "ES512"

    @pytest.mark.unit
    def test_validation_rejects_missing_signature(self):
        """Test that missing required 'signature' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveSignPayloadResponse(algorithm="RS256")


# ---------------------------------------------------------------------------
# RemnawaveHealthResponse
# ---------------------------------------------------------------------------


class TestRemnawaveHealthResponse:
    """Tests for the health check response model."""

    @pytest.mark.unit
    def test_instantiate_valid(self):
        """Test instantiation with required status."""
        health = RemnawaveHealthResponse(status="ok")

        assert health.status == "ok"
        assert health.version is None
        assert health.uptime is None

    @pytest.mark.unit
    def test_instantiate_full(self):
        """Test instantiation with all fields populated."""
        health = RemnawaveHealthResponse(
            status="healthy",
            version="1.5.2",
            uptime=86400,
        )

        assert health.status == "healthy"
        assert health.version == "1.5.2"
        assert health.uptime == 86400

    @pytest.mark.unit
    def test_validation_rejects_string_for_uptime(self):
        """Test that string for 'uptime' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveHealthResponse(status="ok", uptime="long-time")

    @pytest.mark.unit
    def test_from_attributes_orm_style(self):
        """Test constructing from SimpleNamespace."""
        obj = SimpleNamespace(status="ok", version="2.0.0", uptime=3600)
        health = RemnawaveHealthResponse.model_validate(obj, from_attributes=True)

        assert health.status == "ok"
        assert health.uptime == 3600

    @pytest.mark.unit
    def test_validation_rejects_missing_status(self):
        """Test that missing required 'status' raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveHealthResponse(version="1.0")


# ---------------------------------------------------------------------------
# Cross-cutting: model_dump round-trip and JSON serialization
# ---------------------------------------------------------------------------


class TestCrossCuttingSerialization:
    """Cross-cutting tests for serialization behavior shared by all models."""

    @pytest.mark.unit
    def test_model_dump_mode_json_produces_serializable_output(self, user_data_snake):
        """Test that model_dump(mode='json') produces JSON-serializable types."""
        user = RemnawaveUserResponse(**user_data_snake)
        dumped = user.model_dump(mode="json")

        # datetime fields should be serialized as strings
        assert isinstance(dumped["created_at"], str)
        assert isinstance(dumped["updated_at"], str)

    @pytest.mark.unit
    def test_model_dump_by_alias_json_mode(self, user_data_snake):
        """Test combined by_alias + JSON mode for API-ready output."""
        user = RemnawaveUserResponse(**user_data_snake)
        dumped = user.model_dump(by_alias=True, mode="json")

        # camelCase keys with JSON-serializable values
        assert "createdAt" in dumped
        assert isinstance(dumped["createdAt"], str)

    @pytest.mark.unit
    def test_user_list_round_trip(self, user_data_snake):
        """Test that a user list can round-trip through dump and validate."""
        original = RemnawaveUserListResponse(
            response=[RemnawaveUserResponse(**user_data_snake)],
            total=1,
        )
        dumped = original.model_dump(mode="json")
        restored = RemnawaveUserListResponse.model_validate(dumped)

        assert len(restored.response) == 1
        assert restored.response[0].username == "testuser"
        assert restored.total == 1

    @pytest.mark.unit
    def test_node_list_round_trip(self, node_data_snake):
        """Test that a node list can round-trip through dump and validate."""
        original = RemnawaveNodeListResponse(
            response=[RemnawaveNodeResponse(**node_data_snake)]
        )
        dumped = original.model_dump(mode="json")
        restored = RemnawaveNodeListResponse.model_validate(dumped)

        assert len(restored.response) == 1
        assert restored.response[0].name == "Frankfurt-01"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "model_cls,data",
        [
            pytest.param(
                StatusMessageResponse,
                {"status": "ok", "message": "done"},
                id="StatusMessage",
            ),
            pytest.param(
                RemnawaveSystemStatsResponse,
                {"totalUsers": 10, "activeUsers": 5, "totalServers": 2, "onlineServers": 1, "totalTrafficBytes": 999},
                id="SystemStats",
            ),
            pytest.param(
                RemnavwaveBandwidthStatsResponse,
                {"bytesIn": 100, "bytesOut": 200, "totalBytes": 300},
                id="BandwidthStats",
            ),
            pytest.param(
                RemnawaveHealthResponse,
                {"status": "ok", "version": "1.0", "uptime": 3600},
                id="Health",
            ),
            pytest.param(
                RemnawavePublicKeyResponse,
                {"publicKey": "key-data", "algorithm": "RS256"},
                id="PublicKey",
            ),
            pytest.param(
                RemnawaveSignPayloadResponse,
                {"signature": "sig-data", "algorithm": "RS256"},
                id="SignPayload",
            ),
        ],
    )
    def test_round_trip_parametrized(self, model_cls, data):
        """Test round-trip for multiple simple models via parametrize."""
        instance = model_cls.model_validate(data)
        dumped = instance.model_dump(mode="json")
        restored = model_cls.model_validate(dumped)

        # Verify all original data keys are preserved
        for key, value in data.items():
            # Access by snake_case attribute name
            restored_dump = restored.model_dump(by_alias=True, mode="json")
            assert key in restored_dump or any(
                v == value for v in restored_dump.values()
            )

    @pytest.mark.unit
    def test_empty_input_validation_raises(self):
        """Test that empty dict for a model with required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            RemnawaveUserResponse()

        with pytest.raises(ValidationError):
            RemnawaveNodeResponse()

        with pytest.raises(ValidationError):
            RemnawaveInboundResponse()

        with pytest.raises(ValidationError):
            RemnavwaveBillingRecordResponse()
