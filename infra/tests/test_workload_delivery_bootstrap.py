import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "workload_delivery_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("workload_delivery_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorkloadDeliveryBootstrapTests(unittest.TestCase):
    def test_render_scaffold_writes_expected_source_and_gitops_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "delivery"
            args = type(
                "Args",
                (),
                {
                    "output_dir": str(output_dir),
                    "source_repo_name": "VPNBussiness",
                    "source_repository_slug": "beep/vpnbussiness",
                    "gitops_repo_name": "platform-gitops",
                    "workload_cluster_name": "nonprod-hetzner-hel1-core",
                },
            )()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)

            source_repo_dir = output_dir / "source-repo"
            gitops_repo_dir = output_dir / "platform-gitops"
            backend_chart_dir = source_repo_dir / "charts" / "cybervpn-backend"
            worker_chart_dir = source_repo_dir / "charts" / "cybervpn-task-worker"
            apps_dir = gitops_repo_dir / "apps" / "nonprod-hetzner-hel1-core" / "platform-workloads"
            cluster_dir = gitops_repo_dir / "clusters" / "nonprod-hetzner-hel1-core"

            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "scripts" / "check-workload-delivery.sh").exists())
            self.assertTrue((source_repo_dir / ".github" / "workflows" / "platform-workload-delivery.yml").exists())
            self.assertTrue((backend_chart_dir / "Chart.yaml").exists())
            self.assertTrue((backend_chart_dir / "templates" / "deployment.yaml").exists())
            self.assertTrue((backend_chart_dir / "templates" / "service.yaml").exists())
            self.assertTrue((worker_chart_dir / "Chart.yaml").exists())
            self.assertTrue((worker_chart_dir / "templates" / "deployment.yaml").exists())
            self.assertFalse((worker_chart_dir / "templates" / "service.yaml").exists())
            self.assertTrue((cluster_dir / "platform-workloads.yaml").exists())
            self.assertTrue((apps_dir / "kustomization.yaml").exists())
            self.assertTrue((apps_dir / "namespace.yaml").exists())
            self.assertTrue((apps_dir / "backend" / "ocirepository.yaml").exists())
            self.assertTrue((apps_dir / "backend" / "helmrelease.yaml").exists())
            self.assertTrue((apps_dir / "task-worker" / "ocirepository.yaml").exists())
            self.assertTrue((apps_dir / "task-worker" / "helmrelease.yaml").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            workflow = (
                source_repo_dir / ".github" / "workflows" / "platform-workload-delivery.yml"
            ).read_text(encoding="utf-8")
            backend_values = (backend_chart_dir / "values.yaml").read_text(encoding="utf-8")
            worker_values = (worker_chart_dir / "values.yaml").read_text(encoding="utf-8")
            backend_deployment = (backend_chart_dir / "templates" / "deployment.yaml").read_text(encoding="utf-8")
            worker_deployment = (worker_chart_dir / "templates" / "deployment.yaml").read_text(encoding="utf-8")
            platform_apps_readme = (apps_dir / "README.md").read_text(encoding="utf-8")
            backend_oci = (apps_dir / "backend" / "ocirepository.yaml").read_text(encoding="utf-8")
            backend_release = (apps_dir / "backend" / "helmrelease.yaml").read_text(encoding="utf-8")
            worker_release = (apps_dir / "task-worker" / "helmrelease.yaml").read_text(encoding="utf-8")
            versions = (output_dir / "versions.env").read_text(encoding="utf-8")

            self.assertIn("GitHub Actions -> OCI Helm -> GitOps PR -> Flux", root_readme)
            self.assertIn("source repository slug: `beep/vpnbussiness`", root_readme)
            self.assertIn("`helix-adapter` is intentionally excluded", root_readme)
            self.assertIn("helm push", workflow)
            self.assertIn("gh pr create", workflow)
            self.assertIn("platform-workload-release-${{ matrix.component.name }}", workflow)
            self.assertIn("TARGET_CLUSTER=\"${TARGET_CLUSTER:-nonprod-hetzner-hel1-core}\"", workflow)
            self.assertIn("GITOPS_REPOSITORY=\"${GITOPS_REPOSITORY:-REPLACE_ME_OWNER/platform-gitops}\"", workflow)
            self.assertIn("digest: sha256:REPLACE_ME_BACKEND_IMAGE_DIGEST", backend_values)
            self.assertIn("extractKey: kv-apps/data/nonprod/platform/backend", backend_values)
            self.assertIn("digest: sha256:REPLACE_ME_TASK_WORKER_IMAGE_DIGEST", worker_values)
            self.assertIn("extractKey: kv-apps/data/nonprod/platform/task-worker", worker_values)
            self.assertIn('path: /health', backend_deployment)
            self.assertIn("healthcheck.py", worker_deployment)
            self.assertIn("OCIRepository", platform_apps_readme)
            self.assertIn("oci://ghcr.io/beep/vpnbussiness/charts/cybervpn-backend", backend_oci)
            self.assertIn("layerSelector:", backend_oci)
            self.assertIn("secretRef:", backend_oci)
            self.assertIn("chartRef:", backend_release)
            self.assertIn("repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/backend", backend_release)
            self.assertIn("cybervpn.io/source-commit", backend_release)
            self.assertIn("repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker", worker_release)
            self.assertIn("SOURCE_REPOSITORY_SLUG=beep/vpnbussiness", versions)

    def test_render_workload_ocirepository_uses_flux_oci_chart_contract(self) -> None:
        rendered = MODULE.render_workload_ocirepository(
            chart_repo_name="cybervpn-backend-chart",
            chart_name="cybervpn-backend",
            source_repository_slug="beep/vpnbussiness",
        )
        flux_kustomization = MODULE.render_cluster_flux_kustomization(
            workload_cluster_name="nonprod-hetzner-hel1-core"
        )

        self.assertIn("kind: OCIRepository", rendered)
        self.assertIn("application/vnd.cncf.helm.chart.content.v1.tar+gzip", rendered)
        self.assertIn("tag: REPLACE_ME_CHART_VERSION", rendered)
        self.assertIn("path: ./apps/nonprod-hetzner-hel1-core/platform-workloads", flux_kustomization)
        self.assertIn("platform-openbao-integration", flux_kustomization)
        self.assertIn("platform-alloy", flux_kustomization)


if __name__ == "__main__":
    unittest.main()
