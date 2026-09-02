from datetime import datetime
from uuid import UUID

from src.domain.entities.server import Server, ServerIp


def map_remnawave_server(data: dict) -> Server:
    return Server(
        uuid=UUID(data["uuid"]),
        id=data.get("id"),
        name=data["name"],
        address=data.get("address", ""),
        port=data.get("port"),
        is_connected=data.get("isConnected", False),
        is_disabled=data.get("isDisabled", False),
        is_connecting=data.get("isConnecting", False),
        created_at=datetime.fromisoformat(data["createdAt"]),
        updated_at=datetime.fromisoformat(data["updatedAt"]),
        country_code=data.get("countryCode"),
        traffic_limit_bytes=data.get("trafficLimitBytes"),
        used_traffic_bytes=data.get("usedTrafficBytes"),
        inbound_count=data.get("inboundCount"),
        users_online=data.get("usersOnline"),
        xray_version=data.get("xrayVersion"),
        node_version=data.get("nodeVersion"),
        vpn_protocol=data.get("vpnProtocol"),
        active_plugin_uuid=UUID(data["activePluginUuid"]) if data.get("activePluginUuid") else None,
        ips=tuple(ServerIp(ip=item["ip"], status=item["status"]) for item in data.get("ips", [])),
        integration_uuids=tuple(UUID(value) for value in data.get("integrationUuids", [])),
    )
