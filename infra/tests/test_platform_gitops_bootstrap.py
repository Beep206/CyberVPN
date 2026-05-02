from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "infra" / "scripts" / "platform_gitops_bootstrap.py"


class PlatformGitopsBootstrapTests(unittest.TestCase):
    def render_repo(self, target: Path) -> None:
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "render-repo",
                "--output-dir",
                str(target),
            ],
            check=True,
        )

    def test_render_repo_creates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.render_repo(target)

            expected = {
                ".gitignore",
                "README.md",
                "versions.env",
                "clusters/nonprod-mgmt/README.md",
                "infrastructure/nonprod-mgmt/README.md",
                "apps/nonprod-mgmt/README.md",
                "scripts/bootstrap-flux-github.sh",
                "scripts/check-nonprod-mgmt.sh",
            }

            actual = {
                str(path.relative_to(target))
                for path in target.rglob("*")
                if path.is_file()
            }

            self.assertEqual(expected, actual)

    def test_bootstrap_script_uses_github_ssh_bootstrap_guardrails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.render_repo(target)

            bootstrap = (target / "scripts" / "bootstrap-flux-github.sh").read_text(encoding="utf-8")
            self.assertIn("flux bootstrap", bootstrap)
            self.assertIn("--token-auth=false", bootstrap)
            self.assertIn('--repository="$REPOSITORY"', bootstrap)
            self.assertIn('--path="$CLUSTER_PATH"', bootstrap)
            self.assertIn('FLUX_VERSION="${FLUX_VERSION:-v2.8.6}"', bootstrap)
            self.assertNotIn("image-automation-controller", bootstrap)

            readme = (target / "README.md").read_text(encoding="utf-8")
            self.assertIn("read-only", readme)
            self.assertIn("secret **values** are never committed here", readme)
            self.assertIn("clusters/nonprod-mgmt", readme)


if __name__ == "__main__":
    unittest.main()
