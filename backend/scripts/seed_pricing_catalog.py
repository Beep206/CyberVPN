#!/usr/bin/env python3
"""Preview or apply the canonical Phase 1 pricing catalog seed."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import sys
import types
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _BACKEND_ROOT / "src"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
if "src" not in sys.modules:
    src_package = types.ModuleType("src")
    src_package.__file__ = str(_SRC_ROOT / "__init__.py")
    src_package.__path__ = [str(_SRC_ROOT)]
    sys.modules["src"] = src_package

try:
    from src.application.services.pricing_catalog_seed import (  # noqa: E402
        build_addon_seed_specs,
        build_plan_seed_specs,
        seed_pricing_catalog,
    )
    from src.infrastructure.database.session import AsyncSessionLocal  # noqa: E402
except ModuleNotFoundError:
    importlib.invalidate_caches()
    sys.modules.pop("src", None)
    seed_module = importlib.import_module("src.application.services.pricing_catalog_seed")
    session_module = importlib.import_module("src.infrastructure.database.session")
    build_addon_seed_specs = seed_module.build_addon_seed_specs
    build_plan_seed_specs = seed_module.build_plan_seed_specs
    seed_pricing_catalog = seed_module.seed_pricing_catalog
    AsyncSessionLocal = session_module.AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed_pricing_catalog")


def _build_preview_payload() -> dict[str, object]:
    plan_specs = build_plan_seed_specs()
    addon_specs = build_addon_seed_specs()
    return {
        "plan_count": len(plan_specs),
        "addon_count": len(addon_specs),
        "public_plan_families": sorted({spec.plan_code for spec in plan_specs if spec.catalog_visibility == "public"}),
        "hidden_plan_families": sorted({spec.plan_code for spec in plan_specs if spec.catalog_visibility == "hidden"}),
        "sample_prices": {
            spec.name: str(spec.price_usd)
            for spec in plan_specs
            if spec.name in {"basic_365", "plus_365", "pro_365", "max_365", "test_365", "development_365"}
        },
        "addons": {
            spec.code: {
                "price_usd": str(spec.price_usd),
                "requires_location": spec.requires_location,
            }
            for spec in addon_specs
        },
    }


async def _apply_seed() -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        summary = await seed_pricing_catalog(session)
        await session.commit()
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or apply the canonical pricing catalog seed.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upsert plans and add-ons into the configured database.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print preview/apply output as JSON.",
    )
    args = parser.parse_args()

    if not args.apply:
        payload = _build_preview_payload()
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        logger.info("Preview only. No database changes were applied.")
        logger.info("Plans: %s | Add-ons: %s", payload["plan_count"], payload["addon_count"])
        logger.info("Public families: %s", ", ".join(payload["public_plan_families"]))
        logger.info("Hidden families: %s", ", ".join(payload["hidden_plan_families"]))
        for sku, price in payload["sample_prices"].items():
            logger.info("Sample price: %s -> %s USD", sku, price)
        for code, addon in payload["addons"].items():
            logger.info(
                "Addon: %s -> %s USD%s",
                code,
                addon["price_usd"],
                " (location-bound)" if addon["requires_location"] else "",
            )
        return

    summary = asyncio.run(_apply_seed())
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    logger.info("Pricing catalog seed applied: %s", summary)


if __name__ == "__main__":
    main()
