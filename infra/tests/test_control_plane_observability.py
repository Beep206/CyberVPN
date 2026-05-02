import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "control_plane_observability.py"
SPEC = importlib.util.spec_from_file_location("control_plane_observability", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ControlPlaneObservabilityTests(unittest.TestCase):
    def test_render_bundle_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openbao_nodes = temp_path / "openbao_nodes.json"
            nats_nodes = temp_path / "nats_nodes.json"
            posthog_nodes = temp_path / "posthog_nodes.json"
            output_dir = temp_path / "out"

            openbao_nodes.write_text(
                json.dumps(
                    {
                        "openbao-nonprod-01": {
                            "ipv4_address": "198.51.100.10",
                            "metrics_addr": "https://198.51.100.10:9102/v1/sys/metrics?format=prometheus",
                        }
                    }
                ),
                encoding="utf-8",
            )
            nats_nodes.write_text(
                json.dumps(
                    {
                        "nats-nonprod-01": {
                            "ipv4_address": "198.51.100.20",
                            "exporter_addr": "http://198.51.100.20:7777/metrics",
                        }
                    }
                ),
                encoding="utf-8",
            )
            posthog_nodes.write_text(
                json.dumps(
                    {
                        "posthog-nonprod-01": {
                            "ipv4_address": "198.51.100.30",
                            "https_url": "https://posthog-nonprod.example.com",
                        }
                    }
                ),
                encoding="utf-8",
            )

            args = type(
                "Args",
                (),
                {
                    "output_dir": str(output_dir),
                    "openbao_nodes_file": str(openbao_nodes),
                    "nats_nodes_file": str(nats_nodes),
                    "posthog_nodes_file": str(posthog_nodes),
                    "environment": "nonprod",
                    "openbao_cluster_id": "openbao-nonprod",
                    "nats_cluster_id": "nats-nonprod",
                    "posthog_instance_id": "posthog-nonprod",
                    "loki_url": "http://loki:3100/loki/api/v1/push",
                    "loki_basic_auth_username": "",
                    "loki_basic_auth_password": "",
                    "loki_bearer_token": "",
                    "alloy_http_port": 9100,
                },
            )()

            result = MODULE.command_render_bundle(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "hosts" / "openbao-nonprod-01" / "config.alloy").exists())
            self.assertTrue((output_dir / "hosts" / "nats-nonprod-01" / "config.alloy").exists())
            self.assertTrue((output_dir / "hosts" / "posthog-nonprod-01" / "config.alloy").exists())
            self.assertTrue((output_dir / "prometheus" / "control-plane-alloy-nonprod.json").exists())
            self.assertTrue((output_dir / "prometheus" / "openbao-nonprod-targets.json").exists())

            openbao_config = (output_dir / "hosts" / "openbao-nonprod-01" / "config.alloy").read_text(encoding="utf-8")
            nats_config = (output_dir / "hosts" / "nats-nonprod-01" / "config.alloy").read_text(encoding="utf-8")
            posthog_config = (output_dir / "hosts" / "posthog-nonprod-01" / "config.alloy").read_text(encoding="utf-8")
            readme = (output_dir / "README.md").read_text(encoding="utf-8")

            self.assertIn('matches = "_SYSTEMD_UNIT=openbao.service"', openbao_config)
            self.assertIn('project     = "cybervpn"', openbao_config)
            self.assertIn('matches = "_SYSTEMD_UNIT=nats-exporter.service"', nats_config)
            self.assertIn('/var/lib/docker/containers/*/*-json.log', posthog_config)
            self.assertIn("Talos cluster add-on observability remains a later packet", readme)
            self.assertIn("not valid target collectors", readme)

            targets_payload = json.loads(
                (output_dir / "prometheus" / "control-plane-alloy-nonprod.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(targets_payload), 3)
            self.assertEqual(targets_payload[0]["labels"]["job"], "alloy-control-plane")
            self.assertEqual(targets_payload[0]["labels"]["project"], "cybervpn")

            openbao_targets_payload = json.loads(
                (output_dir / "prometheus" / "openbao-nonprod-targets.json").read_text(encoding="utf-8")
            )
            self.assertEqual(openbao_targets_payload[0]["targets"], ["198.51.100.10:9102"])
            self.assertEqual(openbao_targets_payload[0]["labels"]["job"], "openbao")
            self.assertEqual(openbao_targets_payload[0]["labels"]["project"], "cybervpn")

            install_script = (output_dir / "hosts" / "openbao-nonprod-01" / "install-alloy.sh").read_text(encoding="utf-8")
            self.assertIn("usermod -a -G adm,systemd-journal alloy || true", install_script)

    def test_render_bundle_rejects_partial_loki_basic_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_payload = {"node-01": {"ipv4_address": "198.51.100.10", "metrics_addr": "https://198.51.100.10:9102/v1/sys/metrics?format=prometheus"}}
            for filename in ("openbao.json", "nats.json", "posthog.json"):
                (temp_path / filename).write_text(json.dumps(input_payload), encoding="utf-8")

            args = type(
                "Args",
                (),
                {
                    "output_dir": str(temp_path / "out"),
                    "openbao_nodes_file": str(temp_path / "openbao.json"),
                    "nats_nodes_file": str(temp_path / "nats.json"),
                    "posthog_nodes_file": str(temp_path / "posthog.json"),
                    "environment": "nonprod",
                    "openbao_cluster_id": "openbao-nonprod",
                    "nats_cluster_id": "nats-nonprod",
                    "posthog_instance_id": "posthog-nonprod",
                    "loki_url": "http://loki:3100/loki/api/v1/push",
                    "loki_basic_auth_username": "ops",
                    "loki_basic_auth_password": "",
                    "loki_bearer_token": "",
                    "alloy_http_port": 9100,
                },
            )()

            with self.assertRaises(SystemExit):
                MODULE.command_render_bundle(args)


if __name__ == "__main__":
    unittest.main()
