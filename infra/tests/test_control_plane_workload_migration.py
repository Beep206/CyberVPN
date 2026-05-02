import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "control_plane_workload_migration.py"
SPEC = importlib.util.spec_from_file_location("control_plane_workload_migration", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ControlPlaneWorkloadMigrationTests(unittest.TestCase):
    def test_render_scaffold_writes_initial_workload_runtime_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "control-plane-workloads"
            args = type("Args", (), {"output_dir": str(output_dir)})()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "spec-manifest.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-control-plane-workloads.sh").exists())
            self.assertTrue(
                (output_dir / "source-repo" / "charts" / "cybervpn-backend" / "templates" / "migration-job.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "source-repo" / "charts" / "cybervpn-backend" / "templates" / "servicemonitor.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "source-repo" / "charts" / "cybervpn-task-worker" / "values-scheduler.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "source-repo" / "charts" / "cybervpn-task-worker" / "templates" / "servicemonitor.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "platform-gitops" / "apps" / MODULE.WORKLOAD_CLUSTER_NAME / "platform-workloads" / "backend" / "helmrelease.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "platform-gitops" / "apps" / MODULE.WORKLOAD_CLUSTER_NAME / "platform-workloads" / "task-worker" / "helmrelease.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "platform-gitops" / "apps" / MODULE.WORKLOAD_CLUSTER_NAME / "platform-workloads" / "task-scheduler" / "helmrelease.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "platform-gitops" / "clusters" / MODULE.WORKLOAD_CLUSTER_NAME / "platform-control-plane-backend.yaml").exists()
            )

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            backend_values = (
                output_dir / "source-repo" / "charts" / "cybervpn-backend" / "values.yaml"
            ).read_text(encoding="utf-8")
            backend_migration_job = (
                output_dir / "source-repo" / "charts" / "cybervpn-backend" / "templates" / "migration-job.yaml"
            ).read_text(encoding="utf-8")
            worker_values = (
                output_dir / "source-repo" / "charts" / "cybervpn-task-worker" / "values.yaml"
            ).read_text(encoding="utf-8")
            scheduler_values = (
                output_dir / "source-repo" / "charts" / "cybervpn-task-worker" / "values-scheduler.yaml"
            ).read_text(encoding="utf-8")
            worker_release = (
                output_dir
                / "platform-gitops"
                / "apps"
                / MODULE.WORKLOAD_CLUSTER_NAME
                / "platform-workloads"
                / "task-worker"
                / "helmrelease.yaml"
            ).read_text(encoding="utf-8")
            scheduler_release = (
                output_dir
                / "platform-gitops"
                / "apps"
                / MODULE.WORKLOAD_CLUSTER_NAME
                / "platform-workloads"
                / "task-scheduler"
                / "helmrelease.yaml"
            ).read_text(encoding="utf-8")
            backend_kustomization = (
                output_dir
                / "platform-gitops"
                / "clusters"
                / MODULE.WORKLOAD_CLUSTER_NAME
                / "platform-control-plane-backend.yaml"
            ).read_text(encoding="utf-8")

            self.assertIn("`backend`", root_readme)
            self.assertIn("`task-scheduler`", root_readme)
            self.assertIn("`helix-adapter`", root_readme)
            self.assertIn("`telegram-bot`", root_readme)
            self.assertIn(f"extractKey: {MODULE.BACKEND_SECRET_KEY}", backend_values)
            self.assertIn("servicePort: 9091", backend_values)
            self.assertIn("- alembic", backend_values)
            self.assertIn("- head", backend_values)
            self.assertIn("helm.sh/hook: pre-install,pre-upgrade", backend_migration_job)
            self.assertIn("mode: worker", worker_values)
            self.assertIn("PROMETHEUS_MULTIPROC_DIR", worker_values)
            self.assertIn(f"extractKey: {MODULE.TASK_WORKER_SECRET_KEY}", worker_values)
            self.assertIn("mode: scheduler", scheduler_values)
            self.assertIn("- taskiq", scheduler_values)
            self.assertIn("cybervpn-task-worker-chart", worker_release)
            self.assertIn("targetName: task-worker-runtime", worker_release)
            self.assertIn("cybervpn-task-scheduler", scheduler_release)
            self.assertIn("targetName: task-scheduler-runtime", scheduler_release)
            self.assertIn("dependsOn:", backend_kustomization)
            self.assertIn("platform-workloads-namespace", backend_kustomization)
            self.assertIn("platform-kube-prometheus-stack", backend_kustomization)

    def test_validate_accepts_current_repo_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        args = type("Args", (), {"repo_root": str(repo_root)})()
        result = MODULE.command_validate(args)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
