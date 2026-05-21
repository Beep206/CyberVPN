# ruff: noqa: S101

"""S1 payment runtime kill-switch checks."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.config.settings import settings
from src.presentation.api.shared.stage1_payment_runtime import (
    PAYMENTS_DISABLED_DETAIL,
    TELEGRAM_STARS_DISABLED_DETAIL,
    require_stage1_payments_enabled,
    require_stage1_telegram_stars_enabled,
)


def test_stage1_payments_enabled_allows_generic_paid_flows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "payments_enabled", True)

    require_stage1_payments_enabled()


def test_stage1_payments_disabled_blocks_generic_paid_flows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "payments_enabled", False)

    with pytest.raises(HTTPException) as exc_info:
        require_stage1_payments_enabled()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == PAYMENTS_DISABLED_DETAIL


def test_stage1_telegram_stars_disabled_blocks_new_stars_invoices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_stars_enabled", False)

    with pytest.raises(HTTPException) as exc_info:
        require_stage1_telegram_stars_enabled()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == TELEGRAM_STARS_DISABLED_DETAIL


def test_stage1_telegram_stars_can_be_enabled_while_generic_payments_stay_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "payments_enabled", False)
    monkeypatch.setattr(settings, "telegram_stars_enabled", True)

    require_stage1_telegram_stars_enabled()
