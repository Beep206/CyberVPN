from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.servers.remove_inbound import RemoveInboundUseCase


@pytest.mark.unit
async def test_execute_uses_validated_delete():
    client = AsyncMock()
    inbound_uuid = uuid4()

    await RemoveInboundUseCase(client).execute(inbound_uuid)

    client.delete_validated.assert_awaited_once_with(f"/api/inbounds/{inbound_uuid}", ANY)
