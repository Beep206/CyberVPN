import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "nonprod_mgmt_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("nonprod_mgmt_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class NonprodMgmtBootstrapTests(unittest.TestCase):
    def test_render_clusterctl_yaml_pins_talos_provider_assets(self) -> None:
        rendered = MODULE.render_clusterctl_yaml(cabpt_version="v0.6.11", cacppt_version="v0.5.12")

        self.assertIn("cluster-api-bootstrap-provider-talos/releases/download/v0.6.11/bootstrap-components.yaml", rendered)
        self.assertIn("cluster-api-control-plane-provider-talos/releases/download/v0.5.12/control-plane-components.yaml", rendered)
        self.assertIn('name: "talos"', rendered)

    def test_render_bundle_writes_install_scripts_and_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "bundle"
            args = type(
                "Args",
                (),
                {
                    "cluster_name": "nonprod-mgmt",
                    "kubeconfig_path": "/secure/nonprod-mgmt.kubeconfig",
                    "output_dir": str(output_dir),
                    "capi_version": "v1.13.0",
                    "cabpt_version": "v0.6.11",
                    "cacppt_version": "v0.5.12",
                    "caph_branch": "v1.1.x",
                    "caph_components_url": None,
                },
            )()

            result = MODULE.command_render_bundle(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "clusterctl" / "clusterctl.yaml").exists())
            self.assertTrue((output_dir / "install-capi-core.sh").exists())
            self.assertTrue((output_dir / "install-caph.sh").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "README.md").exists())

            install_core = (output_dir / "install-capi-core.sh").read_text(encoding="utf-8")
            install_caph = (output_dir / "install-caph.sh").read_text(encoding="utf-8")
            readme = (output_dir / "README.md").read_text(encoding="utf-8")

            self.assertIn("clusterctl init", install_core)
            self.assertIn("--core cluster-api:v1.13.0", install_core)
            self.assertIn("--bootstrap talos:v0.6.11", install_core)
            self.assertIn("--control-plane talos:v0.5.12", install_core)
            self.assertIn("CAPH_COMPONENTS_URL must point to a validated infrastructure-components.yaml", install_caph)
            self.assertIn("v1.0.x", readme)
            self.assertIn("nonprod-mgmt", readme)


if __name__ == "__main__":
    unittest.main()
