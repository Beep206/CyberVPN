import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "control_plane_recovery.py"
SPEC = importlib.util.spec_from_file_location("control_plane_recovery", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ControlPlaneRecoveryTests(unittest.TestCase):
    def test_render_bundle_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openbao_nodes = temp_path / "openbao_nodes.json"
            nats_nodes = temp_path / "nats_nodes.json"
            posthog_nodes = temp_path / "posthog_nodes.json"
            talos_endpoints = temp_path / "talos_endpoints.json"
            output_dir = temp_path / "out"

            openbao_nodes.write_text(
                json.dumps(
                    {
                        "openbao-nonprod-01": {
                            "ipv4_address": "198.51.100.10",
                            "api_addr": "https://198.51.100.10:8200",
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
                            "client_addr": "198.51.100.20:4222",
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
                            "domain_name": "posthog-nonprod.example.com",
                        }
                    }
                ),
                encoding="utf-8",
            )
            talos_endpoints.write_text(json.dumps({"endpoints": ["198.51.100.40", "198.51.100.41"]}), encoding="utf-8")

            args = type(
                "Args",
                (),
                {
                    "output_dir": str(output_dir),
                    "openbao_nodes_file": str(openbao_nodes),
                    "nats_nodes_file": str(nats_nodes),
                    "posthog_nodes_file": str(posthog_nodes),
                    "talos_endpoints_file": str(talos_endpoints),
                    "environment": "nonprod",
                    "artifact_root": "/var/backups/cybervpn-platform/nonprod",
                    "openbao_cluster_id": "openbao-nonprod",
                    "nats_cluster_id": "nats-nonprod",
                    "posthog_instance_id": "posthog-nonprod",
                    "management_cluster_id": "nonprod-mgmt",
                },
            )()

            result = MODULE.command_render_bundle(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "common" / "sync-to-s3.sh").exists())
            self.assertTrue((output_dir / "openbao" / "snapshot-openbao.sh").exists())
            self.assertTrue((output_dir / "nats" / "backup-nats-account.sh").exists())
            self.assertTrue((output_dir / "posthog" / "backup-posthog-over-ssh.sh").exists())
            self.assertTrue((output_dir / "nonprod-mgmt" / "backup-etcd.sh").exists())
            self.assertTrue((output_dir / "nonprod-mgmt" / "backup-machine-configs.sh").exists())
            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())

            openbao_script = (output_dir / "openbao" / "snapshot-openbao.sh").read_text(encoding="utf-8")
            nats_script = (output_dir / "nats" / "backup-nats-account.sh").read_text(encoding="utf-8")
            posthog_script = (output_dir / "posthog" / "backup-posthog-over-ssh.sh").read_text(encoding="utf-8")
            talos_script = (output_dir / "nonprod-mgmt" / "backup-etcd.sh").read_text(encoding="utf-8")
            machine_config_script = (output_dir / "nonprod-mgmt" / "backup-machine-configs.sh").read_text(encoding="utf-8")
            readme = (output_dir / "README.md").read_text(encoding="utf-8")
            restore_notes = (output_dir / "openbao" / "restore-openbao.md").read_text(encoding="utf-8")

            self.assertIn('VAULT_ADDR="${VAULT_ADDR:-https://198.51.100.10:8200}"', openbao_script)
            self.assertIn('operator raft snapshot save', openbao_script)
            self.assertIn('account backup --consumers --check --force', nats_script)
            self.assertIn('POSTHOG_SSH_TARGET', posthog_script)
            self.assertIn('"${TALOSCTL_BIN:-talosctl}" --talosconfig "${TALOSCONFIG:?set TALOSCONFIG}" -n "$endpoint" etcd snapshot', talos_script)
            self.assertIn('198.51.100.40', machine_config_script)
            self.assertIn('198.51.100.41', machine_config_script)
            self.assertIn('openbao-nonprod', readme)
            self.assertIn('posthog-nonprod', readme)
            self.assertIn('bao operator raft snapshot restore <snapshot_file>', restore_notes)

    def test_load_endpoints_accepts_array(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "endpoints.json"
            path.write_text(json.dumps(["198.51.100.10", "198.51.100.11"]), encoding="utf-8")

            result = MODULE.load_endpoints(path)

            self.assertEqual(result, ["198.51.100.10", "198.51.100.11"])


if __name__ == "__main__":
    unittest.main()
