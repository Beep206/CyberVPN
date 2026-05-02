import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "prod_control_plane_cutover.py"
SPEC = importlib.util.spec_from_file_location("prod_control_plane_cutover", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProdControlPlaneCutoverTests(unittest.TestCase):
    def test_render_scaffold_writes_expected_production_cutover_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "prod-control-plane-cutover"
            args = type("Args", (), {"output_dir": str(output_dir)})()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)
            cluster_dir = output_dir / "platform-gitops" / "clusters" / MODULE.WORKLOAD_CLUSTER_NAME
            progressive_dir = output_dir / "platform-gitops" / "infrastructure" / MODULE.WORKLOAD_CLUSTER_NAME / "progressive-delivery"
            data_dir = output_dir / "platform-gitops" / "infrastructure" / MODULE.WORKLOAD_CLUSTER_NAME / "data"
            apps_dir = output_dir / "platform-gitops" / "apps" / MODULE.WORKLOAD_CLUSTER_NAME / "platform-workloads"

            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "spec-manifest.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-prod-control-plane-cutover.sh").exists())
            self.assertTrue((cluster_dir / "platform-production-progressive-delivery.yaml").exists())
            self.assertTrue((cluster_dir / "platform-production-backend.yaml").exists())
            self.assertTrue((progressive_dir / "flagger" / "helmrelease.yaml").exists())
            self.assertTrue((data_dir / "cnpg" / "cluster.yaml").exists())
            self.assertTrue((data_dir / "cnpg" / "podmonitor.yaml").exists())
            self.assertTrue((apps_dir / "backend" / "canary.yaml").exists())
            self.assertTrue((apps_dir / "backend" / "helmrelease.yaml").exists())
            self.assertTrue((apps_dir / "task-worker" / "helmrelease.yaml").exists())
            self.assertTrue((apps_dir / "task-scheduler" / "helmrelease.yaml").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            versions_env = (output_dir / "versions.env").read_text(encoding="utf-8")
            flagger_release = (progressive_dir / "flagger" / "helmrelease.yaml").read_text(encoding="utf-8")
            cnpg_cluster = (data_dir / "cnpg" / "cluster.yaml").read_text(encoding="utf-8")
            cnpg_podmonitor = (data_dir / "cnpg" / "podmonitor.yaml").read_text(encoding="utf-8")
            backend_release = (apps_dir / "backend" / "helmrelease.yaml").read_text(encoding="utf-8")
            backend_canary = (apps_dir / "backend" / "canary.yaml").read_text(encoding="utf-8")
            worker_release = (apps_dir / "task-worker" / "helmrelease.yaml").read_text(encoding="utf-8")
            scheduler_release = (apps_dir / "task-scheduler" / "helmrelease.yaml").read_text(encoding="utf-8")
            backend_kustomization = (cluster_dir / "platform-production-backend.yaml").read_text(encoding="utf-8")

            self.assertIn("`prod-mgmt`", root_readme)
            self.assertIn("`prod-hetzner-fsn1-core`", root_readme)
            self.assertIn("Flagger", root_readme)
            self.assertIn("CloudNativePG", root_readme)
            self.assertIn("FIRST_PROGRESSIVE_RELEASE=backend", versions_env)
            self.assertIn("meshProvider: gatewayapi:v1", flagger_release)
            self.assertIn("enablePodMonitor: false", cnpg_cluster)
            self.assertIn("cnpg.io/cluster: cybervpn-control-plane-db", cnpg_podmonitor)
            self.assertIn(f"extractKey: {MODULE.BACKEND_SECRET_KEY}", backend_release)
            self.assertIn("provider: gatewayapi:v1", backend_canary)
            self.assertIn("gatewayRefs:", backend_canary)
            self.assertIn("api.REPLACE_ME_PRODUCTION_DOMAIN", backend_canary)
            self.assertIn("replicaCount: 3", worker_release)
            self.assertIn(f"extractKey: {MODULE.TASK_WORKER_SECRET_KEY}", worker_release)
            self.assertIn("mode: scheduler", scheduler_release)
            self.assertIn("platform-production-data", backend_kustomization)
            self.assertIn("platform-production-progressive-delivery", backend_kustomization)

    def test_validate_accepts_current_repo_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        args = type("Args", (), {"repo_root": str(repo_root)})()
        result = MODULE.command_validate(args)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
