import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "realtime_delivery_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("realtime_delivery_bootstrap", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RealtimeDeliveryBootstrapTests(unittest.TestCase):
    def test_render_scaffold_writes_gateway_and_delivery_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "realtime-delivery"
            args = type("Args", (), {"output_dir": str(output_dir)})()

            result = MODULE.command_render_scaffold(args)

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "README.md").exists())
            self.assertTrue((output_dir / "versions.env").exists())
            self.assertTrue((output_dir / "spec-manifest.yaml").exists())
            self.assertTrue((output_dir / "scripts" / "check-realtime-delivery.sh").exists())
            self.assertTrue((output_dir / "backend" / "realtime-gateway" / "README.md").exists())
            self.assertTrue((output_dir / "backend" / "realtime-gateway" / "channel-registry.yaml").exists())
            self.assertTrue(
                (output_dir / "backend" / "realtime-gateway" / "projections" / "partner-workspace-feed.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "backend" / "realtime-gateway" / "delivery" / "sse-endpoints.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "backend" / "realtime-gateway" / "delivery" / "websocket-endpoints.yaml").exists()
            )
            self.assertTrue(
                (output_dir / "backend" / "realtime-gateway" / "delivery" / "browser-event-contract.yaml").exists()
            )
            self.assertTrue((output_dir / "backend" / "realtime-gateway" / "legacy-boundaries.yaml").exists())
            self.assertTrue((output_dir / "frontend" / "legacy-ui-notes.md").exists())

            root_readme = (output_dir / "README.md").read_text(encoding="utf-8")
            channel_registry = (
                output_dir / "backend" / "realtime-gateway" / "channel-registry.yaml"
            ).read_text(encoding="utf-8")
            sse_endpoints = (
                output_dir / "backend" / "realtime-gateway" / "delivery" / "sse-endpoints.yaml"
            ).read_text(encoding="utf-8")
            websocket_endpoints = (
                output_dir / "backend" / "realtime-gateway" / "delivery" / "websocket-endpoints.yaml"
            ).read_text(encoding="utf-8")
            projection_contract = (
                output_dir / "backend" / "realtime-gateway" / "projections" / "partner-workspace-feed.yaml"
            ).read_text(encoding="utf-8")
            legacy_notes = (output_dir / "frontend" / "legacy-ui-notes.md").read_text(encoding="utf-8")

            self.assertIn("primary browser delivery protocol: `SSE`", root_readme)
            self.assertIn("existing monitoring websocket remains operational-only", root_readme)
            self.assertIn("channel_name: partner.workspace.feed", channel_registry)
            self.assertIn("source_stream: PARTNER_EVENTS", channel_registry)
            self.assertIn("browser_delivery_primary: sse", channel_registry)
            self.assertIn("status: operational_only", channel_registry)
            self.assertIn("path: /api/v1/realtime/partner/events", sse_endpoints)
            self.assertIn("content_type: text/event-stream", sse_endpoints)
            self.assertIn("last_event_id_supported: true", sse_endpoints)
            self.assertIn("path: /api/v1/ws/realtime/partner", websocket_endpoints)
            self.assertIn("status: operational_only_existing_surface", websocket_endpoints)
            self.assertIn("consumer_name: realtime_gateway_projection", projection_contract)
            self.assertIn("browser_protocol: sse", projection_contract)
            self.assertIn("operational-only", legacy_notes)

    def test_validate_accepts_current_repo_baseline(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        args = type("Args", (), {"repo_root": str(repo_root)})()
        result = MODULE.command_validate(args)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
