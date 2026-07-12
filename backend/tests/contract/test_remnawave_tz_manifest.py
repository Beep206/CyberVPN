from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "docs/plans/CyberVPN_Remnawave_2_8_0_TZ_manifest.json"
REQUIRED_BUNDLE_PATHS = {
    "docs/architecture/CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md",
    "docs/plans/README_CyberVPN_Remnawave_TZ.md",
    "docs/plans/TZ_Codex_Task1_Premium_Smart_RU_Remnawave_2_8_0.md",
    "docs/plans/TZ_Codex_Task2_SPB_Default_With_DE_Exceptions_Remnawave_2_8_0.md",
}


def test_remnawave_tz_manifest_matches_current_bundle_files() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest["files"]

    paths = [entry["path"] for entry in entries]
    assert len(paths) == len(set(paths))
    assert set(paths) == REQUIRED_BUNDLE_PATHS

    for entry in entries:
        artifact = REPO_ROOT / entry["path"]
        assert artifact.is_file(), entry["path"]
        content = artifact.read_bytes()

        assert len(content) == entry["size_bytes"], entry["path"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"], entry["path"]
        assert len(content.decode("utf-8").splitlines()) == entry["lines"], entry["path"]
