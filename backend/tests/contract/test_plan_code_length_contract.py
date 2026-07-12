from __future__ import annotations

import json
from pathlib import Path

from src.domain.entities.subscription_plan import PLAN_CODE_MAX_LENGTH
from src.main import app

PLAN_CODE_REQUEST_SCHEMAS = (
    "AdminCustomerManualSubscriptionRequest",
    "CreatePlanRequest",
    "UpdatePlanRequest",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _string_variant(property_schema: dict) -> dict:
    if property_schema.get("type") == "string":
        return property_schema
    return next(item for item in property_schema["anyOf"] if item.get("type") == "string")


def test_plan_code_request_bounds_match_database_limit_in_live_and_exported_openapi() -> None:
    exported_schema = json.loads((_repo_root() / "backend/docs/api/openapi.json").read_text(encoding="utf-8"))

    for schema in (app.openapi(), exported_schema):
        components = schema["components"]["schemas"]
        for schema_name in PLAN_CODE_REQUEST_SCHEMAS:
            plan_code = _string_variant(components[schema_name]["properties"]["plan_code"])
            assert plan_code["maxLength"] == PLAN_CODE_MAX_LENGTH
