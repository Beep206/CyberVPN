from __future__ import annotations

import json
from pathlib import Path

from src.main import app


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _capture_request_schema(schema: dict) -> dict:
    return schema["components"]["schemas"]["PartnerAttributionCaptureRequest"]["properties"]


def _nullable_object_schema(property_schema: dict) -> dict:
    return next(item for item in property_schema["anyOf"] if item.get("type") == "object")


def test_partner_attribution_capture_schema_bounds_match_live_and_exported_openapi() -> None:
    live_schema = app.openapi()
    exported_schema = json.loads((_repo_root() / "backend/docs/api/openapi.json").read_text(encoding="utf-8"))

    for schema in (live_schema, exported_schema):
        properties = _capture_request_schema(schema)
        sub_ids = _nullable_object_schema(properties["sub_ids"])
        campaign_params = _nullable_object_schema(properties["campaign_params"])

        assert sub_ids["maxProperties"] == 16
        assert sub_ids["additionalProperties"] == {"type": "string"}
        assert campaign_params["maxProperties"] == 24
        assert campaign_params["additionalProperties"] == {"type": "string"}


def test_partner_attribution_capture_documents_runtime_error_statuses() -> None:
    live_schema = app.openapi()
    exported_schema = json.loads((_repo_root() / "backend/docs/api/openapi.json").read_text(encoding="utf-8"))

    for schema in (live_schema, exported_schema):
        capture_responses = schema["paths"]["/api/v1/partner-attribution/capture"]["post"]["responses"]
        assert {"400", "428", "429", "503"}.issubset(capture_responses)
        for status_code in ("400", "428", "429", "503"):
            response_ref = capture_responses[status_code]["content"]["application/json"]["schema"]["$ref"]
            assert response_ref == "#/components/schemas/PartnerAttributionErrorResponse"


def test_readiness_schema_remains_backward_compatible_object_map() -> None:
    live_schema = app.openapi()
    exported_schema = json.loads((_repo_root() / "backend/docs/api/openapi.json").read_text(encoding="utf-8"))

    for schema in (live_schema, exported_schema):
        readiness_schema = schema["paths"]["/readiness"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert readiness_schema["type"] == "object"
        assert readiness_schema["additionalProperties"] is True
