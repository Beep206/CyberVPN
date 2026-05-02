import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "event_backbone_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("event_backbone_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EventBackboneBootstrapTests(unittest.TestCase):
    def test_render_scaffold_writes_backend_and_service_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "event-backbone"
            repo_root = Path(__file__).resolve().parents[2]
            args = type(
                "Args",
                (),
                {
                    "repo_root": str(repo_root),
                    "output_dir": str(output_dir),
                },
            )()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "spec-manifest.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-event-backbone.sh").exists())
            self.assertTrue((output_dir / "backend" / "dispatcher" / "stream-declarations.yaml").exists())
            self.assertTrue((output_dir / "backend" / "dispatcher" / "subject-route-map.yaml").exists())
            self.assertTrue((output_dir / "backend" / "dispatcher" / "dispatcher-runtime.env.example").exists())
            self.assertTrue((output_dir / "backend" / "dispatcher" / "consumers" / "analytics-mart.yaml").exists())
            self.assertTrue((output_dir / "backend" / "dispatcher" / "consumers" / "operational-replay.yaml").exists())
            self.assertTrue((output_dir / "backend" / "replay" / "replay-plan.example.yaml").exists())
            self.assertTrue(
                (output_dir / "services" / "task-worker" / "reserved-consumers" / "notification-delivery.yaml").exists()
            )
            self.assertTrue(
                (
                    output_dir
                    / "services"
                    / "task-worker"
                    / "reserved-consumers"
                    / "realtime-gateway-projection.yaml"
                ).exists()
            )

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            stream_declarations = (
                output_dir / "backend" / "dispatcher" / "stream-declarations.yaml"
            ).read_text(encoding="utf-8")
            subject_routes = (output_dir / "backend" / "dispatcher" / "subject-route-map.yaml").read_text(
                encoding="utf-8"
            )
            analytics_consumer = (
                output_dir / "backend" / "dispatcher" / "consumers" / "analytics-mart.yaml"
            ).read_text(encoding="utf-8")
            replay_plan = (output_dir / "backend" / "replay" / "replay-plan.example.yaml").read_text(
                encoding="utf-8"
            )
            services_readme = (output_dir / "services" / "task-worker" / "README.md").read_text(encoding="utf-8")
            notification_consumer = (
                output_dir / "services" / "task-worker" / "reserved-consumers" / "notification-delivery.yaml"
            ).read_text(encoding="utf-8")

            self.assertIn("PARTNER_EVENTS", root_readme)
            self.assertIn("operational_replay", root_readme)
            self.assertIn("reserved for `P2.7`", root_readme)
            self.assertIn("deduplication_header: Nats-Msg-Id", stream_declarations)
            self.assertIn("stream_name: PARTNER_EVENTS", stream_declarations)
            self.assertIn("partner.growth_code.issued.v1", stream_declarations)
            self.assertIn("partner.settlement.payout.execution.requested.v1", subject_routes)
            self.assertIn("consumer_mode: durable_pull", analytics_consumer)
            self.assertIn("idempotency_store: postgres.outbox_publications", analytics_consumer)
            self.assertIn("replay_mode: durable_pull_rebuild", replay_plan)
            self.assertIn("notification_delivery", services_readme)
            self.assertIn("status: reserved_for_p2_7", notification_consumer)
            self.assertIn("side_effect_type: email_telegram_or_sms_delivery", notification_consumer)

    def test_validate_accepts_current_repo_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        args = type("Args", (), {"repo_root": str(repo_root)})()
        result = MODULE.command_validate(args)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
