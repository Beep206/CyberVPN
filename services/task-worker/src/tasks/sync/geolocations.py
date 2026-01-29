"""Sync server geolocations from Remnawave for 3D map visualization."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.broker import broker
from src.database.session import get_session_factory
from src.models.server_geolocation import ServerGeolocationModel
from src.services.remnawave_client import RemnawaveClient
from src.utils.country_coords import COUNTRY_COORDS

logger = structlog.get_logger(__name__)


@broker.task(task_name="sync_server_geolocations", queue="sync")
async def sync_server_geolocations() -> dict:
    """Sync server geolocations from Remnawave for 3D map visualization.

    Fetches all nodes from Remnawave API, determines lat/lng from country_code
    using a static mapping, and upserts into server_geolocations table.

    Returns:
        Dictionary with synced count
    """
    session_factory = get_session_factory()
    synced = 0

    try:
        async with RemnawaveClient() as rw:
            nodes = await rw.get_nodes()

        async with session_factory() as session:
            for node in nodes:
                node_uuid = node.get("uuid")
                country_code = node.get("countryCode", "").upper()
                city = node.get("city")

                if not node_uuid or not country_code:
                    logger.warning("missing_node_data", node=node.get("name"), uuid=node_uuid)
                    continue

                # Lookup coordinates
                coords = COUNTRY_COORDS.get(country_code)
                if not coords:
                    logger.warning("unknown_country_code", country=country_code, node=node.get("name"))
                    continue

                latitude, longitude = coords

                try:
                    # Parse UUID
                    uuid_obj = UUID(node_uuid)

                    # Upsert using PostgreSQL INSERT ... ON CONFLICT
                    stmt = insert(ServerGeolocationModel).values(
                        node_uuid=uuid_obj,
                        country_code=country_code,
                        city=city,
                        latitude=latitude,
                        longitude=longitude,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["node_uuid"],
                        set_={
                            "country_code": country_code,
                            "city": city,
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                    )
                    await session.execute(stmt)
                    synced += 1

                except (ValueError, TypeError) as e:
                    logger.warning("invalid_node_uuid", uuid=node_uuid, error=str(e))
                    continue

            await session.commit()

    except Exception as e:
        logger.exception("geolocation_sync_failed", error=str(e))
        raise

    logger.info("geolocations_synced", count=synced)
    return {"synced": synced}
