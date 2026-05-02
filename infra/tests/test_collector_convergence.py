import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "collector_convergence.py"
SPEC = importlib.util.spec_from_file_location("collector_convergence", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CollectorConvergenceTests(unittest.TestCase):
    def test_render_report_classifies_tracked_and_unexpected_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            output_dir = Path(temp_dir) / "out"
            (repo_root / "infra").mkdir(parents=True, exist_ok=True)
            (repo_root / "services" / "foo").mkdir(parents=True, exist_ok=True)
            (repo_root / "docs" / "plans").mkdir(parents=True, exist_ok=True)

            (repo_root / "infra" / "docker-compose.yml").write_text("promtail:\n  image: grafana/promtail:3.4.2\n", encoding="utf-8")
            (repo_root / "docs" / "plans" / "legacy.md").write_text("otel-collector remains here for legacy notes\n", encoding="utf-8")
            (repo_root / "services" / "foo" / "config.py").write_text("OTEL = 'http://otel-collector:4317'\n", encoding="utf-8")

            args = type(
                "Args",
                (),
                {
                    "repo_root": str(repo_root),
                    "output_dir": str(output_dir),
                },
            )()

            result = MODULE.command_render_report(args)
            self.assertEqual(result, 0)

            report_json = output_dir / "collector-convergence-report.json"
            report_md = output_dir / "collector-convergence-report.md"
            self.assertTrue(report_json.exists())
            self.assertTrue(report_md.exists())

            payload = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertGreaterEqual(payload["summary"]["total_matches"], 3)
            self.assertGreaterEqual(payload["summary"]["tracked_legacy_matches"], 2)
            self.assertEqual(payload["summary"]["unexpected_matches"], 1)
            self.assertEqual(payload["unexpected_matches"][0]["path"], "services/foo/config.py")

            markdown = report_md.read_text(encoding="utf-8")
            self.assertIn("Unexpected matches", markdown)
            self.assertIn("services/foo/config.py:1", markdown)

    def test_validate_returns_nonzero_when_unexpected_matches_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            (repo_root / "services").mkdir(parents=True, exist_ok=True)
            (repo_root / "services" / "bad.py").write_text("collector = 'promtail'\n", encoding="utf-8")

            args = type("Args", (), {"repo_root": str(repo_root)})()
            result = MODULE.command_validate(args)
            self.assertEqual(result, 1)

    def test_validate_passes_with_only_tracked_legacy_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            (repo_root / "infra" / "prometheus").mkdir(parents=True, exist_ok=True)
            (repo_root / "infra" / "prometheus" / "prometheus.yml").write_text(
                "job_name: 'otel-collector'\n",
                encoding="utf-8",
            )

            args = type("Args", (), {"repo_root": str(repo_root)})()
            result = MODULE.command_validate(args)
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
