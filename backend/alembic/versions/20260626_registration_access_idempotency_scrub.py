"""Scrub raw registration-access idempotency keys.

Revision ID: 20260626_reg_access_idem
Revises: 20260626_onboard_idem
Create Date: 2026-06-26
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "20260626_reg_access_idem"
down_revision: str | Sequence[str] | None = "20260626_onboard_idem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


registration_access_grants = sa.table(
    "registration_access_grants",
    sa.column("id", sa.Uuid()),
    sa.column("registration_idempotency_key", sa.String()),
    sa.column("metadata", sa.JSON()),
)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            registration_access_grants.c.id,
            registration_access_grants.c.registration_idempotency_key,
            registration_access_grants.c.metadata,
        )
    ).fetchall()
    for row in rows:
        metadata = row.metadata if isinstance(row.metadata, Mapping) else {}
        scrubbed_metadata, metadata_changed = _scrub_metadata(metadata)
        registration_idempotency_key = row.registration_idempotency_key
        scrubbed_registration_key = _legacy_hash(registration_idempotency_key)
        registration_key_changed = scrubbed_registration_key != registration_idempotency_key
        if metadata_changed or registration_key_changed:
            bind.execute(
                registration_access_grants.update()
                .where(registration_access_grants.c.id == row.id)
                .values(
                    metadata=scrubbed_metadata,
                    registration_idempotency_key=scrubbed_registration_key,
                )
            )


def downgrade() -> None:
    # Raw idempotency keys are intentionally unrecoverable after this scrub.
    return


def _scrub_metadata(metadata: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    scrubbed = dict(metadata)
    raw_value = scrubbed.pop("exchange_idempotency_key", None)
    if raw_value in (None, ""):
        return scrubbed, False
    raw_string = str(raw_value)
    scrubbed["exchange_idempotency_key_present"] = True
    scrubbed["exchange_idempotency_key_legacy_sha256"] = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
    return scrubbed, True


def _legacy_hash(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    raw = str(value)
    if raw.startswith(("hmac:", "sha256:")):
        return raw
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"
