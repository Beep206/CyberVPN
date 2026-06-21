"""Require partner code public slugs after link backfill.

Revision ID: 20260621_partner_slug_required
Revises: 20260621_partner_comm_contracts
Create Date: 2026-06-21
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa

from alembic import op

revision: str = "20260621_partner_slug_required"
down_revision: str | Sequence[str] | None = "20260621_partner_comm_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    _backfill_missing_public_slugs(bind)
    _backfill_missing_public_token_hashes(bind)
    _strip_transfer_tokens_from_destination_urls(bind)
    op.alter_column(
        "partner_codes",
        "public_slug",
        existing_type=sa.String(length=80),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "partner_codes",
        "public_slug",
        existing_type=sa.String(length=80),
        nullable=True,
    )


def _backfill_missing_public_slugs(bind: sa.Connection) -> None:
    existing_slugs = {
        str(row[0])
        for row in bind.execute(
            sa.text(
                """
                SELECT public_slug
                FROM partner_codes
                WHERE public_slug IS NOT NULL
                """
            )
        )
        if row[0]
    }
    rows = bind.execute(
        sa.text(
            """
            SELECT id
            FROM partner_codes
            WHERE public_slug IS NULL
            ORDER BY created_at, id
            """
        )
    ).mappings()
    for row in rows:
        public_slug = _unique_slug(row_id=str(row["id"]), existing_slugs=existing_slugs)
        bind.execute(
            sa.text(
                """
                UPDATE partner_codes
                SET public_slug = :public_slug,
                    public_token_hash = COALESCE(public_token_hash, :public_token_hash)
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "public_slug": public_slug,
                "public_token_hash": hashlib.sha256(public_slug.encode("utf-8")).hexdigest(),
            },
        )


def _backfill_missing_public_token_hashes(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT id, public_slug
            FROM partner_codes
            WHERE public_slug IS NOT NULL
              AND public_token_hash IS NULL
            ORDER BY created_at, id
            """
        )
    ).mappings()
    for row in rows:
        bind.execute(
            sa.text(
                """
                UPDATE partner_codes
                SET public_token_hash = :public_token_hash
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "public_token_hash": hashlib.sha256(str(row["public_slug"]).encode("utf-8")).hexdigest(),
            },
        )


def _unique_slug(*, row_id: str, existing_slugs: set[str]) -> str:
    attempt = 0
    slug = _generate_public_slug(row_id=row_id, attempt=attempt)
    while slug in existing_slugs:
        attempt += 1
        slug = _generate_public_slug(row_id=row_id, attempt=attempt)
    existing_slugs.add(slug)
    return slug


def _generate_public_slug(*, row_id: str, attempt: int) -> str:
    digest = hashlib.sha256(f"partner-code-public-slug:{row_id}:{attempt}".encode()).hexdigest()
    body = digest[:24]
    return f"px_{body}"


def _strip_transfer_tokens_from_destination_urls(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT id, destination_url
            FROM partner_attribution_sessions
            WHERE destination_url LIKE '%pat=%'
            """
        )
    ).mappings()
    for row in rows:
        sanitized_url = _strip_pat_query_param(str(row["destination_url"]))
        if sanitized_url != row["destination_url"]:
            bind.execute(
                sa.text(
                    """
                    UPDATE partner_attribution_sessions
                    SET destination_url = :destination_url
                    WHERE id = :id
                    """
                ),
                {"id": row["id"], "destination_url": sanitized_url},
            )


def _strip_pat_query_param(url: str) -> str:
    parsed = urlsplit(url)
    query_items = [
        (key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() != "pat"
    ]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query_items), parsed.fragment))
