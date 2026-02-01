from datetime import datetime
from uuid import UUID

from src.domain.entities.server import Server


def map_remnawave_server(data: dict) -> Server:
    return Server(
        uuid=UUID(data["uuid"]),
        name=data["name"],
        address=data.get("address", ""),
        port=data.get("port", 0),
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
        vpn_protocol=data.get("vpnProtocol"),
    )
