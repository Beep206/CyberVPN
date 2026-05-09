from __future__ import annotations

import asyncio

from src.application.services.config_service import ConfigService


class MissingWalletWithdrawalConfigRepository:
    async def get_value(self, key, default=None):
        assert key == "wallet.withdrawal_enabled"
        return default


def test_stage1_wallet_withdrawals_fail_closed_when_config_missing() -> None:
    result = asyncio.run(ConfigService(MissingWalletWithdrawalConfigRepository()).is_withdrawal_enabled())

    assert result is False
