import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "posthog_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("posthog_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PostHogBootstrapTests(unittest.TestCase):
    def test_render_env_includes_proxy_and_security_defaults(self) -> None:
        rendered = MODULE.render_env(
            domain="posthog-nonprod.example.com",
            project_name="cybervpn-posthog-nonprod",
            posthog_app_tag="latest",
            posthog_node_tag="latest",
            posthog_repo_ref="HEAD",
            registry_url="posthog/posthog",
            opt_out_capture=True,
            proxy_cidrs="127.0.0.1",
            disable_secure_ssl_redirect=True,
        )

        self.assertIn("DOMAIN=posthog-nonprod.example.com", rendered)
        self.assertIn("IS_BEHIND_PROXY=True", rendered)
        self.assertIn("POSTHOG_SECRET=${POSTHOG_SECRET:?Set POSTHOG_SECRET from the approved secret store}", rendered)
        self.assertIn(
            "ENCRYPTION_SALT_KEYS=${ENCRYPTION_SALT_KEYS:?Set ENCRYPTION_SALT_KEYS from the approved secret store}",
            rendered,
        )
        self.assertIn("TRUSTED_PROXIES=127.0.0.1", rendered)
        self.assertIn("DISABLE_SECURE_SSL_REDIRECT=True", rendered)
        self.assertIn("OPT_OUT_CAPTURE=true", rendered)

    def test_render_bundle_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "bundle"
            args = type(
                "Args",
                (),
                {
                    "domain": "posthog-nonprod.example.com",
                    "output_dir": str(output_dir),
                    "project_name": "cybervpn-posthog-nonprod",
                    "posthog_app_tag": "latest",
                    "posthog_node_tag": "latest",
                    "posthog_repo_ref": "HEAD",
                    "registry_url": "posthog/posthog",
                    "basic_auth_username": "cyberops",
                    "basic_auth_env": "POSTHOG_BASIC_AUTH_PASSWORD",
                    "runtime_key_env": "POSTHOG_SECRET",
                    "encryption_keys_env": "ENCRYPTION_SALT_KEYS",
                    "tls_email": "ops@example.com",
                    "auth_realm": "CyberVPN PostHog nonprod",
                    "proxy_cidrs": "127.0.0.1",
                    "backup_retention_days": 7,
                    "opt_out_capture": True,
                    "disable_secure_ssl_redirect": True,
                    "admin_cidrs": ["198.51.100.10/32"],
                },
            )()

            result = MODULE.command_render_bundle(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / ".env").exists())
            self.assertTrue((output_dir / "docker-compose.override.yml").exists())
            self.assertTrue((output_dir / "install-node.sh").exists())
            self.assertTrue((output_dir / "posthog-local-backup.sh").exists())
            self.assertTrue((output_dir / "nginx" / "posthog-http.conf").exists())
            self.assertTrue((output_dir / "nginx" / "posthog-https.conf").exists())
            credentials = json.loads((output_dir / "credentials.json").read_text(encoding="utf-8"))
            self.assertEqual(credentials["basic_auth"]["username"], "cyberops")
            self.assertEqual(credentials["basic_auth"]["auth_env"], "POSTHOG_BASIC_AUTH_PASSWORD")
            self.assertNotIn("password", credentials["basic_auth"])
            self.assertEqual(credentials["runtime_key_env"], "POSTHOG_SECRET")
            self.assertEqual(credentials["encryption_keys_env"], "ENCRYPTION_SALT_KEYS")
            self.assertEqual(credentials["domain"], "posthog-nonprod.example.com")
            self.assertIn("tls_email", credentials)


if __name__ == "__main__":
    unittest.main()
