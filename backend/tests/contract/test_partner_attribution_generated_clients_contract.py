from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _capture_request_block(content: str) -> str:
    match = re.search(
        r"PartnerAttributionCaptureRequest: \{(?P<body>.*?)\n\s*\};\n\s*/\*\* PartnerAttributionCaptureResponse",
        content,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group("body")


def test_partner_attribution_generated_clients_type_campaign_params_as_strings() -> None:
    repo_root = _repo_root()
    for relative_path in (
        "frontend/src/lib/api/generated/types.ts",
        "admin/src/lib/api/generated/types.ts",
        "partner/src/lib/api/generated/types.ts",
    ):
        block = _capture_request_block((repo_root / relative_path).read_text(encoding="utf-8"))

        assert "sub_ids?: {" in block
        assert "campaign_params?: {" in block
        assert block.count("[key: string]: string;") >= 2
        assert "[key: string]: unknown;" not in block
