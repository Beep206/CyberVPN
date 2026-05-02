import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cluster_backup_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("cluster_backup_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ClusterBackupBootstrapTests(unittest.TestCase):
    def test_render_scaffold_writes_expected_backup_contract_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "platform-gitops"
            args = type(
                "Args",
                (),
                {
                    "output_dir": str(output_dir),
                    "workload_cluster_name": "nonprod-hetzner-hel1-core",
                    "cnpg_chart_version": "0.27.0",
                    "barman_plugin_version": "v0.12.0",
                    "velero_chart_version": "11.3.2",
                    "database_namespace": "platform-data",
                    "database_cluster_name": "platform-core-postgres",
                    "objectstore_name": "platform-core-postgres-store",
                    "storage_class_placeholder": "REPLACE_ME_STORAGE_CLASS",
                    "volume_snapshot_class_placeholder": "REPLACE_ME_VOLUME_SNAPSHOT_CLASS",
                },
            )()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)

            cluster_dir = output_dir / "clusters" / "nonprod-hetzner-hel1-core"
            protection_dir = output_dir / "infrastructure" / "nonprod-hetzner-hel1-core" / "data-protection"
            templates_dir = protection_dir / "backup-policies" / "templates"

            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((cluster_dir / "kustomization.yaml").exists())
            self.assertTrue((cluster_dir / "platform-backup-policies.yaml").exists())
            self.assertTrue((protection_dir / "README.md").exists())
            self.assertTrue((protection_dir / "versions.env").exists())
            self.assertTrue((protection_dir / "sources" / "cnpg-repository.yaml").exists())
            self.assertTrue((protection_dir / "cnpg-operator" / "helmrelease.yaml").exists())
            self.assertTrue((protection_dir / "barman-plugin" / "manifest.yaml").exists())
            self.assertTrue((protection_dir / "barman-plugin" / "sync-official-manifest.sh").exists())
            self.assertTrue((protection_dir / "velero" / "helmrelease.yaml").exists())
            self.assertTrue((protection_dir / "backup-policies" / "backup-storage-location.yaml").exists())
            self.assertTrue((protection_dir / "backup-policies" / "volume-snapshot-location.yaml").exists())
            self.assertTrue((templates_dir / "cnpg-objectstore.yaml").exists())
            self.assertTrue((templates_dir / "cnpg-scheduledbackup-plugin.yaml").exists())
            self.assertTrue((templates_dir / "cnpg-scheduledbackup-volume-snapshot.yaml").exists())
            self.assertTrue((templates_dir / "cnpg-cluster-backup-snippet.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-data-protection.sh").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            protection_readme = (protection_dir / "README.md").read_text(encoding="utf-8")
            backup_policies_readme = (protection_dir / "backup-policies" / "README.md").read_text(encoding="utf-8")
            versions_env = (protection_dir / "versions.env").read_text(encoding="utf-8")
            barman_env = (protection_dir / "barman-plugin" / "upstream.env").read_text(encoding="utf-8")
            velero_release = (protection_dir / "velero" / "helmrelease.yaml").read_text(encoding="utf-8")
            velero_schedule = (
                protection_dir / "backup-policies" / "velero-schedule-platform-cluster-backup.yaml"
            ).read_text(encoding="utf-8")
            objectstore_template = (templates_dir / "cnpg-objectstore.yaml").read_text(encoding="utf-8")
            plugin_backup_template = (templates_dir / "cnpg-scheduledbackup-plugin.yaml").read_text(encoding="utf-8")
            snapshot_backup_template = (
                templates_dir / "cnpg-scheduledbackup-volume-snapshot.yaml"
            ).read_text(encoding="utf-8")
            cluster_backup_snippet = (templates_dir / "cnpg-cluster-backup-snippet.yaml").read_text(
                encoding="utf-8"
            )

            self.assertIn("CloudNativePG + Barman Cloud Plugin + WAL archive", root_readme)
            self.assertIn("Barman Cloud Plugin", protection_readme)
            self.assertIn("defaultVolumesToFsBackup` is set to `false`", protection_readme)
            self.assertIn("velero/velero-cloud-credentials", backup_policies_readme)
            self.assertIn("CNPG_CHART_VERSION=0.27.0", versions_env)
            self.assertIn("VELERO_PROVIDER_PLUGIN_IMAGE=REQUIRED_OPERATOR_PIN", versions_env)
            self.assertIn("BARMAN_PLUGIN_MANIFEST_URL=https://github.com/cloudnative-pg/plugin-barman-cloud/releases/download/v0.12.0/manifest.yaml", barman_env)
            self.assertIn("existingSecret: velero-cloud-credentials", velero_release)
            self.assertIn("velero-plugin-for-aws", velero_release)
            self.assertIn("deployNodeAgent: true", velero_release)
            self.assertIn("features: EnableCSI", velero_release)
            self.assertIn("defaultSnapshotMoveData: true", velero_release)
            self.assertIn("defaultVolumesToFsBackup: false", velero_schedule)
            self.assertIn("snapshotMoveData: true", velero_schedule)
            self.assertIn("kind: ObjectStore", objectstore_template)
            self.assertIn("kind: ScheduledBackup", plugin_backup_template)
            self.assertIn("method: plugin", plugin_backup_template)
            self.assertIn("pluginConfiguration:", plugin_backup_template)
            self.assertIn("method: volumeSnapshot", snapshot_backup_template)
            self.assertIn("isWALArchiver: true", cluster_backup_snippet)
            self.assertIn("className: REPLACE_ME_VOLUME_SNAPSHOT_CLASS", cluster_backup_snippet)

    def test_rendered_backup_templates_keep_object_store_and_snapshot_paths_separate(self) -> None:
        plugin_backup = MODULE.render_cnpg_scheduledbackup_plugin_template(
            database_namespace="platform-data",
            database_cluster_name="platform-core-postgres",
        )
        snapshot_backup = MODULE.render_cnpg_scheduledbackup_snapshot_template(
            database_namespace="platform-data",
            database_cluster_name="platform-core-postgres",
        )
        cluster_snippet = MODULE.render_cnpg_cluster_backup_snippet(
            database_namespace="platform-data",
            database_cluster_name="platform-core-postgres",
            objectstore_name="platform-core-postgres-store",
            storage_class="fast-ssd",
            snapshot_class="csi-fast-ssd",
        )

        self.assertIn("method: plugin", plugin_backup)
        self.assertIn("name: barman-cloud.cloudnative-pg.io", plugin_backup)
        self.assertIn("method: volumeSnapshot", snapshot_backup)
        self.assertIn("volumeSnapshot:", cluster_snippet)
        self.assertIn("barmanObjectName: platform-core-postgres-store", cluster_snippet)
        self.assertIn("className: csi-fast-ssd", cluster_snippet)


if __name__ == "__main__":
    unittest.main()
