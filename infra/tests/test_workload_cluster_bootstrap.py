import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "workload_cluster_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("workload_cluster_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorkloadClusterBootstrapTests(unittest.TestCase):
    def test_render_scaffold_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "gitops"
            args = type(
                "Args",
                (),
                {
                    "output_dir": str(output_dir),
                    "management_cluster_name": "nonprod-mgmt",
                    "workload_cluster_name": "nonprod-hetzner-hel1-core",
                    "region": "hel1",
                    "kubernetes_version": "v1.35.0",
                    "talos_version": "v1.11.4",
                    "control_plane_replicas": 3,
                    "worker_replicas": 2,
                    "control_plane_machine_type": "cpx31",
                    "worker_machine_type": "cpx21",
                    "gateway_class_name": "cilium",
                },
            )()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)
            management_dir = output_dir / "infrastructure" / "nonprod-mgmt" / "workload-clusters" / "nonprod-hetzner-hel1-core"
            network_dir = output_dir / "infrastructure" / "nonprod-hetzner-hel1-core" / "network"
            cluster_dir = output_dir / "clusters" / "nonprod-hetzner-hel1-core"
            apps_dir = output_dir / "apps" / "nonprod-hetzner-hel1-core"

            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((management_dir / "README.md").exists())
            self.assertTrue((management_dir / "workload-cluster-inputs.env").exists())
            self.assertTrue((management_dir / "render-workload-cluster.sh").exists())
            self.assertTrue((cluster_dir / "README.md").exists())
            self.assertTrue((apps_dir / "README.md").exists())
            self.assertTrue((network_dir / "README.md").exists())
            self.assertTrue((network_dir / "edge-baseline.env").exists())
            self.assertTrue((network_dir / "cilium-values.yaml").exists())
            self.assertTrue((network_dir / "cert-manager-values.yaml").exists())
            self.assertTrue((network_dir / "trust-manager-values.yaml").exists())
            self.assertTrue((output_dir / "versions.env").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            inputs_env = (management_dir / "workload-cluster-inputs.env").read_text(encoding="utf-8")
            render_script = (management_dir / "render-workload-cluster.sh").read_text(encoding="utf-8")
            cilium_values = (network_dir / "cilium-values.yaml").read_text(encoding="utf-8")
            cert_manager_values = (network_dir / "cert-manager-values.yaml").read_text(encoding="utf-8")
            edge_baseline = (network_dir / "edge-baseline.env").read_text(encoding="utf-8")

            self.assertIn("nonprod-hetzner-hel1-core", root_readme)
            self.assertIn("Cloudflare", root_readme)
            self.assertIn("CAPH_TEMPLATE_URL=REQUIRED", inputs_env)
            self.assertIn("clusterctl generate cluster", render_script)
            self.assertIn('CAPH_TEMPLATE_URL must point to an operator-validated CAPH workload-cluster template', render_script)
            self.assertIn("gatewayAPI:", cilium_values)
            self.assertIn("enabled: true", cilium_values)
            self.assertIn("crds:", cert_manager_values)
            self.assertIn("PUBLIC_EDGE_PROVIDER=cloudflare", edge_baseline)
            self.assertIn("LOADBALANCER_STRATEGY=provider-native-l4", edge_baseline)

    def test_render_trust_manager_values_is_intentionally_minimal(self) -> None:
        rendered = MODULE.render_trust_manager_values()

        self.assertIn("Secret targets disabled", rendered)
        self.assertIn("{}", rendered)


if __name__ == "__main__":
    unittest.main()
