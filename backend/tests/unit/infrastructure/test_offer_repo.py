from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.repositories.offer_repo import _sale_channel_filter


def test_offer_sale_channel_filter_uses_jsonb_contains_on_postgres() -> None:
    stmt = select(OfferModel).where(_sale_channel_filter("web", "postgresql"))

    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "CAST(offer_versions.sale_channels AS JSONB)" in compiled
    assert "@>" in compiled
    assert "LIKE" not in compiled


def test_offer_sale_channel_filter_keeps_sqlite_tests_compilable() -> None:
    stmt = select(OfferModel).where(_sale_channel_filter("web", "sqlite"))

    compiled = str(stmt.compile(dialect=sqlite.dialect()))

    assert "CAST(offer_versions.sale_channels AS VARCHAR)" in compiled
    assert "LIKE" in compiled
