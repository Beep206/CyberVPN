import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "nats_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("nats_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class NatsBootstrapTests(unittest.TestCase):
    def test_render_accounts_block_generates_passwords(self) -> None:
        credentials: dict[str, dict[str, str]] = {}
        block = MODULE.render_accounts_block(
            {
                "system_account": "SYS",
                "accounts": [
                    {
                        "name": "SYS",
                        "users": [
                            {
                                "name": "ops-admin",
                                "username": "ops-admin",
                                "permissions": {
                                    "publish": [">"],
                                    "subscribe": [">"],
                                },
                            }
                        ],
                    }
                ],
            },
            credentials,
        )

        self.assertIn("accounts {", block)
        self.assertIn("ops-admin", block)
        self.assertIn("permissions", block)
        self.assertIn("SYS", credentials)
        self.assertIn("ops-admin", credentials["SYS"])
        self.assertTrue(credentials["SYS"]["ops-admin"])

    @mock.patch.object(MODULE, "build_ca_bundle")
    @mock.patch.object(MODULE, "build_node_cert")
    def test_render_bundle_writes_cluster_artifacts(self, build_node_cert: mock.Mock, build_ca_bundle: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nodes_file = temp_path / "nodes.json"
            accounts_file = temp_path / "accounts.json"
            output_dir = temp_path / "out"

            nodes_file.write_text(
                json.dumps(
                    {
                        "nats-nonprod-01": {"ipv4_address": "198.51.100.10"},
                        "nats-nonprod-02": {"ipv4_address": "198.51.100.11"},
                        "nats-nonprod-03": {"ipv4_address": "198.51.100.12"},
                    }
                ),
                encoding="utf-8",
            )
            accounts_file.write_text(
                json.dumps(
                    {
                        "system_account": "SYS",
                        "accounts": [
                            {
                                "name": "SYS",
                                "users": [
                                    {
                                        "name": "ops-admin",
                                        "username": "ops-admin",
                                        "permissions": {
                                            "publish": [">"],
                                            "subscribe": [">"],
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            fake_ca_key = output_dir / "ca" / "ca.key"
            fake_ca_crt = output_dir / "ca" / "ca.crt"

            def fake_build_ca(out_dir, _cluster_name):
                (out_dir / "ca").mkdir(parents=True, exist_ok=True)
                fake_ca_key.write_text("key", encoding="utf-8")
                fake_ca_crt.write_text("crt", encoding="utf-8")
                return fake_ca_key, fake_ca_crt

            build_ca_bundle.side_effect = fake_build_ca

            args = type(
                "Args",
                (),
                {
                    "cluster_name": "nats-nonprod",
                    "nodes_file": str(nodes_file),
                    "accounts_file": str(accounts_file),
                    "output_dir": str(output_dir),
                    "client_port": 4222,
                    "cluster_port": 6222,
                    "monitor_port": 8222,
                    "exporter_port": 7777,
                    "jetstream_store_dir": "/var/lib/nats/jetstream",
                    "jetstream_max_file_store": 21474836480,
                    "jetstream_max_memory_store": 268435456,
                },
            )()

            result = MODULE.command_render_bundle(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "credentials.json").exists())
            self.assertTrue((output_dir / "prometheus" / "nats-nonprod-targets.json").exists())
            self.assertTrue((output_dir / "nats-nonprod-01" / "nats-server.conf").exists())
            self.assertTrue((output_dir / "nats-nonprod-01" / "nats-exporter.env").exists())
            self.assertTrue((output_dir / "nats-nonprod-01" / "install-node.sh").exists())
            rendered = (output_dir / "nats-nonprod-01" / "nats-server.conf").read_text(encoding="utf-8")
            self.assertIn("server_name", rendered)
            self.assertIn("system_account", rendered)
            self.assertIn("routes:", rendered)
            self.assertGreaterEqual(build_node_cert.call_count, 3)


if __name__ == "__main__":
    unittest.main()
