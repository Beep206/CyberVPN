"""Provider-state reconciliation for Telegram Stars refunds."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

import structlog

from src.broker import broker
from src.config import get_settings
from src.services.backend_api_client import BackendAPIClient
from src.services.telegram_client import TelegramClient

logger = structlog.get_logger(__name__)

MAX_TRANSACTION_PAGES = 3
TRANSACTION_PAGE_SIZE = 100


@broker.task(task_name="reconcile_telegram_stars_refunds", queue="payments")
async def reconcile_telegram_stars_refunds() -> dict[str, Any]:
    """Sync outgoing Telegram Stars refund transactions back into backend state."""
    settings = get_settings()
    if not settings.backend_api_url or settings.backend_internal_secret is None:
        logger.info("telegram_stars_reconciliation_skipped", reason="backend_api_not_configured")
        return {"skipped": True, "reason": "backend_api_not_configured"}

    checked = 0
    errors = 0
    actions: Counter[str] = Counter()

    async with TelegramClient() as telegram, BackendAPIClient() as backend:
        if not backend.enabled:
            logger.info("telegram_stars_reconciliation_skipped", reason="backend_api_disabled")
            return {"skipped": True, "reason": "backend_api_disabled"}

        offset = 0
        for _page in range(MAX_TRANSACTION_PAGES):
            page = await telegram.get_star_transactions(offset=offset, limit=TRANSACTION_PAGE_SIZE)
            transactions = list(page.get("transactions", []))
            if not transactions:
                break

            for item in _iter_refund_transactions(transactions):
                checked += 1
                try:
                    response = await backend.reconcile_telegram_stars_refund(item)
                except Exception as exc:
                    errors += 1
                    logger.warning(
                        "telegram_stars_reconciliation_item_failed",
                        telegram_payment_charge_id=item.get("telegram_payment_charge_id"),
                        error=str(exc),
                    )
                    continue
                actions[str(response.get("action") or "unknown")] += 1

            if len(transactions) < TRANSACTION_PAGE_SIZE:
                break
            offset += len(transactions)

    result = {
        "checked": checked,
        "errors": errors,
        "actions": dict(actions),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    logger.info("telegram_stars_reconciliation_complete", **result)
    return result


def _iter_refund_transactions(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for transaction in transactions:
        receiver = transaction.get("receiver")
        if not isinstance(receiver, dict):
            continue
        if receiver.get("type") != "user":
            continue
        if receiver.get("transaction_type") != "invoice_payment":
            continue

        invoice_payload = str(receiver.get("invoice_payload") or "")
        if not invoice_payload.startswith("stars:"):
            continue

        user = receiver.get("user")
        telegram_id = user.get("id") if isinstance(user, dict) else None
        transaction_id = str(transaction.get("id") or "").strip()
        amount = transaction.get("amount")
        refunded_at = transaction.get("date")

        if not isinstance(telegram_id, int) or not transaction_id or not isinstance(amount, int) or amount <= 0:
            continue

        refunded_at_iso = None
        if isinstance(refunded_at, int) and refunded_at > 0:
            refunded_at_iso = datetime.fromtimestamp(refunded_at, tz=UTC).isoformat()

        payloads.append(
            {
                "telegram_id": telegram_id,
                "telegram_payment_charge_id": transaction_id,
                "transaction_id": transaction_id,
                "amount": amount,
                "refunded_at": refunded_at_iso,
                "invoice_payload": invoice_payload,
                "raw_transaction": transaction,
            }
        )
    return payloads
