"""Deployment contracts for TaskIQ schedule registration."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ENTRYPOINT = "src.scheduler:scheduler"
UNSAFE_ENTRYPOINT = "src.broker:scheduler"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_scheduler_runtime_descriptors_use_registration_entrypoint() -> None:
    runtime_descriptors = (
        "infra/docker-compose.yml",
        "infra/deploy/stage1/docker-compose.stage1.yml",
        "infra/ansible/roles/control_plane_stack/templates/docker-compose.yml.j2",
        "infra/scripts/prod_control_plane_cutover.py",
        "infra/scripts/control_plane_workload_migration.py",
    )

    for relative_path in runtime_descriptors:
        content = _read(relative_path)
        assert PRODUCTION_ENTRYPOINT in content, relative_path
        assert UNSAFE_ENTRYPOINT not in content, relative_path


def test_scheduler_entrypoint_eagerly_imports_schedule_definitions() -> None:
    entrypoint = _read("services/task-worker/src/scheduler.py")

    assert "from src.schedules import definitions" in entrypoint
    assert "from src.broker import scheduler" in entrypoint
