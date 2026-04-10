from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "generate_inventory.py"
SPEC = importlib.util.spec_from_file_location("generate_inventory", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class BuildInventoryTests(unittest.TestCase):
    def test_build_inventory_groups_hosts_by_role_and_location(self) -> None:
        inventory = MODULE.build_inventory(
            edge_nodes={
                "fi-01": {
                    "ip": "198.51.100.11",
                    "ssh_port": 22022,
                    "role": "remnawave",
                    "location": "hel1",
                    "server_type": "cx22",
                    "labels": {"environment": "staging"},
                },
                "de-01": {
                    "ip": "198.51.100.22",
                    "ssh_port": 22,
                    "role": "helix",
                    "location": "fsn1",
                    "server_type": "cx22",
                    "labels": {"environment": "staging"},
                },
            },
            environment="staging",
            ansible_user="cyberops",
        )

        children = inventory["all"]["children"]
        self.assertIn("edge_staging", children)
        self.assertIn("helix_edge_staging", children)
        self.assertIn("remnawave_edge_staging", children)
        self.assertIn("fsn1_staging", children)
        self.assertIn("hel1_staging", children)

        hostvars = children["edge_staging"]["hosts"]["fi-01"]
        self.assertEqual(hostvars["ansible_host"], "198.51.100.11")
        self.assertEqual(hostvars["ansible_port"], 22022)
        self.assertEqual(hostvars["ansible_user"], "cyberops")
        self.assertEqual(hostvars["node_role"], "remnawave")

    def test_parse_edge_nodes_payload_rejects_non_object(self) -> None:
        with self.assertRaises(RuntimeError):
            MODULE.parse_edge_nodes_payload('["not-an-object"]')

    def test_build_prometheus_targets_uses_metrics_port_and_labels(self) -> None:
        targets = MODULE.build_prometheus_targets(
            edge_nodes={
                "fi-01": {
                    "ip": "198.51.100.11",
                    "labels": {"environment": "staging"},
                    "location": "hel1",
                    "role": "remnawave",
                    "server_type": "cx22",
                    "ssh_port": 22,
                }
            },
            environment="staging",
            metrics_port=9100,
        )

        self.assertEqual(targets[0]["targets"], ["198.51.100.11:9100"])
        self.assertEqual(targets[0]["labels"]["job"], "alloy-edge")
        self.assertEqual(targets[0]["labels"]["hostname"], "fi-01")


class ScriptExecutionTests(unittest.TestCase):
    def test_script_writes_inventory_snapshot_from_fake_terraform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            terraform_dir = temp_path / "terraform-stack"
            terraform_dir.mkdir()
            prometheus_output_path = temp_path / "alloy-edge.json"

            fake_tf = temp_path / "terraform"
            fake_tf.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import sys

                    if sys.argv[1:] != ["output", "-json", "edge_nodes"]:
                        raise SystemExit(2)

                    print(json.dumps({
                        "fi-01": {
                            "id": "1001",
                            "ip": "198.51.100.11",
                            "labels": {"environment": "staging", "role": "remnawave"},
                            "location": "hel1",
                            "role": "remnawave",
                            "server_type": "cx22",
                            "ssh_port": 22022
                        }
                    }))
                    """
                )
            )
            fake_tf.chmod(fake_tf.stat().st_mode | stat.S_IEXEC)

            output_path = temp_path / "generated.hosts.json"
            subprocess.run(
                [
                    os.environ.get("PYTHON", "python"),
                    str(SCRIPT_PATH),
                    "--terraform-bin",
                    str(fake_tf),
                    "--terraform-dir",
                    str(terraform_dir),
                    "--output",
                    str(output_path),
                    "--environment",
                    "staging",
                    "--ansible-user",
                    "cyberops",
                    "--prometheus-output",
                    str(prometheus_output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_path.read_text())
            target_payload = json.loads(prometheus_output_path.read_text())
            self.assertIn("all", payload)
            self.assertIn("edge_staging", payload["all"]["children"])
            self.assertIn("fi-01", payload["all"]["children"]["edge_staging"]["hosts"])
            self.assertEqual(target_payload[0]["targets"], ["198.51.100.11:9100"])

    def test_script_writes_inventory_snapshot_from_fixture_file(self) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "edge_nodes.sample.json"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            terraform_dir = temp_path / "terraform-stack"
            terraform_dir.mkdir()
            output_path = temp_path / "generated.hosts.json"
            prometheus_output_path = temp_path / "alloy-edge.json"

            subprocess.run(
                [
                    os.environ.get("PYTHON", "python"),
                    str(SCRIPT_PATH),
                    "--terraform-dir",
                    str(terraform_dir),
                    "--terraform-output-file",
                    str(fixture_path),
                    "--output",
                    str(output_path),
                    "--environment",
                    "staging",
                    "--ansible-user",
                    "cyberops",
                    "--prometheus-output",
                    str(prometheus_output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output_path.read_text())
            target_payload = json.loads(prometheus_output_path.read_text())
            edge_hosts = payload["all"]["children"]["edge_staging"]["hosts"]
            self.assertIn("helix-fi-01", edge_hosts)
            self.assertEqual(edge_hosts["helix-fi-01"]["node_role"], "helix")
            self.assertEqual(target_payload[0]["labels"]["job"], "alloy-edge")


if __name__ == "__main__":
    unittest.main()
