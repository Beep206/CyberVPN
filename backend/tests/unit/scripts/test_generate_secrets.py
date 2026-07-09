import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "generate_secrets.py"
SPEC = importlib.util.spec_from_file_location("generate_secrets", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _sandbox_secret_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    private_root = repo_root / ".private"
    monkeypatch.setattr(MODULE, "REPO_ROOT", repo_root)
    monkeypatch.setattr(MODULE, "DEFAULT_OUTPUT", private_root / "generated" / "backend-secrets.env")
    return private_root


def test_generate_secrets_prints_only_metadata_and_writes_raw_values_under_private(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_root = _sandbox_secret_store(monkeypatch, tmp_path)
    output_path = private_root / "generated" / "backend-secrets.env"
    generated_values = {
        "JWT_SECRET": "unit-jwt-material-value",
        "TOTP_ENCRYPTION_KEY": "unit-totp-material-value",
        "REMNAWAVE_TOKEN": "unit-remnawave-material-value",
        "REMNAWAVE_WEBHOOK_SECRET": "unit-remnawave-webhook-material-value",
    }
    monkeypatch.setattr(MODULE, "generate_backend_secrets", lambda: generated_values)
    monkeypatch.setattr(sys, "argv", ["generate_secrets.py", "--output", str(output_path)])

    MODULE.main()

    stdout = capsys.readouterr().out
    assert "raw_values_printed=false" in stdout
    for value in generated_values.values():
        assert value not in stdout

    stored_values = output_path.read_text(encoding="utf-8")
    for name, value in generated_values.items():
        assert f"{name}={value}" in stored_values


def test_generate_secrets_rejects_raw_output_outside_private_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _sandbox_secret_store(monkeypatch, tmp_path)
    outside_private = tmp_path / "tracked-secrets.env"
    monkeypatch.setattr(sys, "argv", ["generate_secrets.py", "--output", str(outside_private)])

    with pytest.raises(SystemExit, match="Raw secret output must stay under"):
        MODULE.main()

    assert not outside_private.exists()


def test_generate_secrets_refuses_to_overwrite_without_force(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private_root = _sandbox_secret_store(monkeypatch, tmp_path)
    output_path = private_root / "generated" / "backend-secrets.env"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("existing=true\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["generate_secrets.py", "--output", str(output_path)])

    with pytest.raises(SystemExit, match="already exists"):
        MODULE.main()

    assert output_path.read_text(encoding="utf-8") == "existing=true\n"
