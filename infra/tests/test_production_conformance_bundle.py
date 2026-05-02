import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "production_conformance_bundle.py"
SPEC = importlib.util.spec_from_file_location("production_conformance_bundle", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProductionConformanceBundleTests(unittest.TestCase):
    def test_render_bundle_writes_expected_conformance_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "conformance"
            args = type("Args", (), {"output_dir": str(output_dir)})()

            result = MODULE.command_render_bundle(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "spec-manifest.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-production-conformance-bundle.sh").exists())
            self.assertTrue((output_dir / "run-order.md").exists())
            self.assertTrue((output_dir / "gate-d-evidence-outline.md").exists())
            self.assertTrue((output_dir / "scorecard" / "gate-d-scorecard-snapshot.md").exists())
            self.assertTrue((output_dir / "scorecard" / "drill-to-criteria-map.yaml").exists())
            self.assertTrue((output_dir / "domains" / "openbao.md").exists())
            self.assertTrue((output_dir / "domains" / "nats.md").exists())
            self.assertTrue((output_dir / "domains" / "cnpg.md").exists())
            self.assertTrue((output_dir / "domains" / "gitops.md").exists())
            self.assertTrue((output_dir / "domains" / "posthog.md").exists())
            self.assertTrue((output_dir / "domains" / "fleet.md").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            run_order = (output_dir / "run-order.md").read_text(encoding="utf-8")
            scorecard = (output_dir / "scorecard" / "gate-d-scorecard-snapshot.md").read_text(encoding="utf-8")
            drill_map = (output_dir / "scorecard" / "drill-to-criteria-map.yaml").read_text(encoding="utf-8")
            fleet_domain = (output_dir / "domains" / "fleet.md").read_text(encoding="utf-8")

            self.assertIn("`Gate D`", root_readme)
            self.assertIn("`prod-hetzner-fsn1-core`", root_readme)
            self.assertIn("OpenBao", run_order)
            self.assertIn("Node Fleet Controller", run_order)
            self.assertIn("| `C01` | `3` | `TBD` | `TBD` | fill in |", scorecard)
            self.assertIn("| `C15` | `3` | `TBD` | `TBD` | fill in |", scorecard)
            self.assertIn("openbao:", drill_map)
            self.assertIn("posthog:", drill_map)
            self.assertIn("guarded failover", fleet_domain)
            self.assertIn("`C10`", fleet_domain)

    def test_validate_accepts_current_repo_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        args = type("Args", (), {"repo_root": str(repo_root)})()
        result = MODULE.command_validate(args)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
