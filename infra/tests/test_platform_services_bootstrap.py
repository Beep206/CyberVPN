import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "platform_services_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("platform_services_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PlatformServicesBootstrapTests(unittest.TestCase):
    def test_render_scaffold_writes_expected_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "platform-gitops"
            args = type(
                "Args",
                (),
                {
                    "output_dir": str(output_dir),
                    "management_cluster_name": "nonprod-mgmt",
                    "workload_cluster_name": "nonprod-hetzner-hel1-core",
                    "openbao_server": "https://openbao-nonprod.example.internal:8200",
                    "cert_manager_version": "v1.20.2",
                    "trust_manager_version": "v0.15.0",
                    "external_secrets_version": "2.3.0",
                    "kube_prometheus_stack_version": "83.6.0",
                    "loki_version": "6.46.0",
                    "tempo_version": "1.24.4",
                    "alloy_chart_version": "1.7.0",
                    "alloy_image_tag": "v1.15.1",
                },
            )()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)

            cluster_dir = output_dir / "clusters" / "nonprod-hetzner-hel1-core"
            services_dir = output_dir / "infrastructure" / "nonprod-hetzner-hel1-core" / "platform-services"

            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((cluster_dir / "kustomization.yaml").exists())
            self.assertTrue((services_dir / "README.md").exists())
            self.assertTrue((services_dir / "versions.env").exists())
            self.assertTrue((services_dir / "sources" / "external-secrets-repository.yaml").exists())
            self.assertTrue((services_dir / "openbao-integration" / "clustersecretstore-openbao-shared.yaml").exists())
            self.assertTrue((services_dir / "openbao-integration" / "clusterissuer-openbao-internal.yaml").exists())
            self.assertTrue((services_dir / "alloy" / "daemonset-helmrelease.yaml").exists())
            self.assertTrue((services_dir / "alloy" / "otlp-gateway-helmrelease.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-platform-services.sh").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            platform_readme = (services_dir / "README.md").read_text(encoding="utf-8")
            clustersecretstore = (
                services_dir / "openbao-integration" / "clustersecretstore-openbao-shared.yaml"
            ).read_text(encoding="utf-8")
            clusterissuer = (
                services_dir / "openbao-integration" / "clusterissuer-openbao-internal.yaml"
            ).read_text(encoding="utf-8")
            versions = (services_dir / "versions.env").read_text(encoding="utf-8")
            daemonset = (services_dir / "alloy" / "daemonset-helmrelease.yaml").read_text(encoding="utf-8")
            gateway = (services_dir / "alloy" / "otlp-gateway-helmrelease.yaml").read_text(encoding="utf-8")

            self.assertIn("there is **no** separate ingress-controller chart", root_readme)
            self.assertIn("External Secrets Operator", root_readme)
            self.assertIn("archived `openbao-secrets-operator`", root_readme)
            self.assertIn("Cilium Gateway API", root_readme)
            self.assertIn("architecture boundary stays the same", platform_readme)
            self.assertIn('path: "jwt-k8s-nonprod-hetzner-hel1-core"', clustersecretstore)
            self.assertIn('namespace: "platform"', clustersecretstore)
            self.assertIn('role: "k8s-nonprod-hetzner-hel1-core-external-secrets-openbao-jwt"', clustersecretstore)
            self.assertIn("mountPath: /v1/auth/jwt-k8s-nonprod-hetzner-hel1-core", clusterissuer)
            self.assertIn('role: "k8s-nonprod-hetzner-hel1-core-cert-manager-openbao-issuer"', clusterissuer)
            self.assertIn("INGRESS_CONTROLLER=none-cilium-gateway-api-is-the-substrate", versions)
            self.assertIn("controller:\n      type: daemonset", daemonset)
            self.assertIn("serviceMonitor:\n      enabled: true", daemonset)
            self.assertIn("controller:\n      type: deployment", gateway)
            self.assertIn("serviceMonitor:\n      enabled: true", gateway)
            self.assertIn('port: 4317', gateway)
            self.assertIn('port: 4318', gateway)
            self.assertNotIn("prometheus.remote_write", gateway)

    def test_sources_and_trust_bundle_render_expected_components(self) -> None:
        sources = MODULE.render_sources_kustomization()
        namespaces = MODULE.render_namespace_objects()
        bundle = MODULE.render_bundle_openbao_k8s_ca()

        self.assertIn("external-secrets-repository.yaml", sources)
        self.assertIn("alloy-repository.yaml", sources)
        self.assertIn("name: external-secrets", namespaces)
        self.assertIn("name: observability", namespaces)
        self.assertIn("kind: Bundle", bundle)
        self.assertIn("cybervpn.io/trust-bundle", bundle)


if __name__ == "__main__":
    unittest.main()
