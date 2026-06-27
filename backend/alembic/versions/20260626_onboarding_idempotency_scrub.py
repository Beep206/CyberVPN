"""Scrub raw onboarding idempotency keys from support payloads.

Revision ID: 20260626_onboard_idem
Revises: 20260626_growth_res_capacity
Create Date: 2026-06-26
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "20260626_onboard_idem"
down_revision: str | Sequence[str] | None = "20260626_growth_res_capacity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


onboarding_states = sa.table(
    "customer_onboarding_states",
    sa.column("id", sa.Uuid()),
    sa.column("result_payload", sa.JSON()),
)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(onboarding_states.c.id, onboarding_states.c.result_payload)).fetchall()
    for row in rows:
        payload = row.result_payload
        if not isinstance(payload, Mapping):
            continue
        scrubbed, changed = _scrub_payload(payload)
        if changed:
            bind.execute(
                onboarding_states.update().where(onboarding_states.c.id == row.id).values(result_payload=scrubbed),
            )


def downgrade() -> None:
    # Raw idempotency keys are intentionally unrecoverable after the scrub.
    return


def _scrub_payload(value: Any) -> tuple[Any, bool]:
    if isinstance(value, Mapping):
        changed = False
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"idempotency_key", "raw_idempotency_key"}:
                changed = True
                prefix = "raw_idempotency_key" if key == "raw_idempotency_key" else "idempotency_key"
                raw_value = str(item) if item not in (None, "") else None
                scrubbed[f"{prefix}_present"] = raw_value is not None
                if raw_value is not None:
                    scrubbed[f"{prefix}_hash"] = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()
                continue
            nested, nested_changed = _scrub_payload(item)
            scrubbed[str(key)] = nested
            changed = changed or nested_changed
        return scrubbed, changed
    if isinstance(value, list):
        changed = False
        items: list[Any] = []
        for item in value:
            nested, nested_changed = _scrub_payload(item)
            items.append(nested)
            changed = changed or nested_changed
        return items, changed
    return value, False
