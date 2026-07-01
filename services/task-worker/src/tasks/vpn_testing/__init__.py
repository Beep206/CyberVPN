"""VPN Tester task registrations."""

from src.tasks.vpn_testing.run_checks import (
    cleanup_vpn_tester_artifacts,
    process_vpn_tester_queue,
    run_vpn_tester_all_tariffs,
    run_vpn_tester_balancer_preview,
    run_vpn_tester_deep,
    run_vpn_tester_lightweight,
)

__all__ = [
    "cleanup_vpn_tester_artifacts",
    "process_vpn_tester_queue",
    "run_vpn_tester_all_tariffs",
    "run_vpn_tester_balancer_preview",
    "run_vpn_tester_deep",
    "run_vpn_tester_lightweight",
]
