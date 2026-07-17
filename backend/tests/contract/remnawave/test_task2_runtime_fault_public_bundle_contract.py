from pathlib import Path

from src.application.vpn_testing.task2_runtime_fault_public_bundle import (
    verify_task2_runtime_fault_public_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
BUNDLE_ROOT = REPO_ROOT / "docs" / "evidence" / "releases" / "task1-task2-20260713" / "task2-runtime-fault-v2"


def test_task2_runtime_fault_release_bundle_verifies_offline() -> None:
    verified = verify_task2_runtime_fault_public_bundle(
        BUNDLE_ROOT,
        expected_operator_public_key_sha256="fc17bd7039554d281878ae5197868c12c4a24113be8e98eb6f3b8b863a0f76a9",
        expected_manifest_sha256="bfc0c791bffb428f39c83688d3d290cec792cc1f7f5d4de3c543423c3f9198cc",
    )
    summary = verified.safe_summary()

    assert summary["status"] == "verified"
    assert summary["credentials_redacted"] is True
    assert summary["manifest_sha256"] == "bfc0c791bffb428f39c83688d3d290cec792cc1f7f5d4de3c543423c3f9198cc"
    assert summary["signed_envelope_sha256"] == "235ff362b6dfb70d02fa82eac5071550a479777d943464d09f8e509980de6e92"
    assert summary["operator_public_key_sha256"] == "fc17bd7039554d281878ae5197868c12c4a24113be8e98eb6f3b8b863a0f76a9"
    assert summary["baseline"] == {
        "run_id": "7453efab-27e5-4117-a13e-64c8172c9373",
        "execution_attempt_id": "5a2f6b567d6e2c5c1f1a6c421fd4e71d",
        "canonical_sanitized_capture_sha256": ("39bfe5140f75e0ed4d948d98622bffa5df8ba3cacff21b82ba434b39a590a6e6"),
    }
    assert summary["fault"] == {
        "run_id": "7f613d9e-dd66-4b0f-9422-d4d482841aa4",
        "execution_attempt_id": "e34f39258b1aa2dcc64187389443c394",
        "canonical_sanitized_capture_sha256": ("66c9ddcefca6073f0320a193a13f0fa0ac4b9ac34b0f07eca246c5f960d536bf"),
    }
    assert summary["post_restore"] == {
        "run_id": "60662012-1898-40d6-9dd3-47b8b8b7eb47",
        "execution_attempt_id": "91bf302c27f6f36847c4fcfe75761e6e",
        "canonical_sanitized_capture_sha256": ("756b7623ba4f45a96864c06297697a13a9c1ff284f5564a447f5d23a665b1bbc"),
    }
    assert summary["selected_outbound_count"] == 21
    assert set(summary["statuses"].values()) == {"degraded"}
