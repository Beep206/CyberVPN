import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "openbao_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("openbao_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class OpenBaoBootstrapTests(unittest.TestCase):
    def test_render_seal_env_uses_current_aws_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "openbao.env"
            args = type(
                "Args",
                (),
                {
                    "output": str(output),
                    "kms_key_id": "alias/openbao/nonprod/seal",
                    "aws_region": "eu-central-1",
                    "address": "https://127.0.0.1:8200",
                    "ca_cert": "/etc/openbao/tls/ca.pem",
                },
            )()

            with mock.patch.dict(
                "os.environ",
                {
                    "AWS_ACCESS_KEY_ID": "AKIAEXAMPLE",
                    "AWS_SECRET_ACCESS_KEY": "secret",
                    "AWS_SESSION_TOKEN": "session",
                },
                clear=False,
            ):
                result = MODULE.command_render_seal_env(args)

            self.assertEqual(result, 0)
            content = output.read_text(encoding="utf-8")
            self.assertIn("VAULT_SEAL_TYPE=awskms", content)
            self.assertIn("VAULT_AWSKMS_SEAL_KEY_ID=alias/openbao/nonprod/seal", content)
            self.assertIn("AWS_ACCESS_KEY_ID=AKIAEXAMPLE", content)
            self.assertIn("AWS_SESSION_TOKEN=session", content)

    @mock.patch.object(MODULE, "run_bao")
    def test_apply_baseline_enables_mounts_and_policies(self, run_bao: mock.Mock) -> None:
        def fake_run(_context, command, *, stdin=None):
            if command[:3] == ["namespace", "list", "-format=json"]:
                return mock.Mock(stdout=json.dumps({"data": {"keys": []}}))
            if command[:3] == ["auth", "list", "-format=json"]:
                return mock.Mock(stdout=json.dumps({}))
            if command[:3] == ["secrets", "list", "-format=json"]:
                return mock.Mock(stdout=json.dumps({}))
            if command[:4] == ["kv", "get", "-mount=kv-shared", "-field=value"]:
                return mock.Mock(stdout="ok")
            return mock.Mock(stdout=json.dumps({}))

        run_bao.side_effect = fake_run

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "token.txt"
            token_file.write_text("root-token", encoding="utf-8")
            args = type(
                "Args",
                (),
                {
                    "bao_bin": "bao",
                    "address": "https://127.0.0.1:8200",
                    "ca_cert": "/etc/openbao/tls/ca.pem",
                    "token": None,
                    "token_file": str(token_file),
                    "platform_namespace": "platform",
                    "policy_dir": str(MODULE.DEFAULT_POLICY_DIR),
                    "oidc_config": None,
                    "jwt_mounts": None,
                    "pki_k8s_max_ttl": "43800h",
                    "pki_infra_max_ttl": "43800h",
                    "issue_bootstrap_token_output": None,
                    "bootstrap_token_policy": "root-human-operators-admin",
                    "bootstrap_token_ttl": "8h",
                    "run_smoke_secret_check": True,
                    "revoke_root_token": False,
                },
            )()
            result = MODULE.command_apply_baseline(args)

        self.assertEqual(result, 0)
        rendered_calls = [" ".join(call.args[1]) for call in run_bao.call_args_list]
        self.assertTrue(any("namespace create platform/" in call for call in rendered_calls))
        self.assertTrue(any("auth enable -path=oidc-operators" in call for call in rendered_calls))
        self.assertTrue(any("auth enable -path=cert-fleet" in call for call in rendered_calls))
        self.assertTrue(any("secrets enable -path=kv-apps" in call for call in rendered_calls))
        self.assertTrue(any("policy write root-human-operators-admin" in call for call in rendered_calls))


if __name__ == "__main__":
    unittest.main()
