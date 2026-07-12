from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "docs/plans/CyberVPN_Remnawave_2_8_0_TZ_manifest.json"


def test_remnawave_tz_manifest_matches_current_bundle_files() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest["files"]

    paths = [entry["path"] for entry in entries]
    assert len(paths) == len(set(paths))

    for entry in entries:
        artifact = REPO_ROOT / entry["path"]
        assert artifact.is_file(), entry["path"]
        content = artifact.read_bytes()

        assert len(content) == entry["size_bytes"], entry["path"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"], entry["path"]
        assert len(content.decode("utf-8").splitlines()) == entry["lines"], entry["path"]
