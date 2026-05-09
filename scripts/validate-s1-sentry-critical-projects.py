#!/usr/bin/env python3
"""Validate the repo-local S1 Sentry critical project contract.

This is a static, dependency-free gate. It does not prove that live Sentry
projects exist; it proves the monorepo has the runtime/build config, env
template keys and privacy hooks needed before real DSNs are provisioned.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Surface:
    name: str
    sentry_project: str
    env_example: Path
    required_env_keys: tuple[str, ...]
    required_files: tuple[Path, ...]
    required_snippets: tuple[tuple[Path, str], ...]
    forbidden_snippets: tuple[tuple[Path, str], ...] = ()


SURFACES: tuple[Surface, ...] = (
    Surface(
        name="frontend",
        sentry_project="web-frontend",
        env_example=Path("frontend/.env.example"),
        required_env_keys=(
            "NEXT_PUBLIC_SENTRY_DSN",
            "SENTRY_DSN",
            "SENTRY_ORG",
            "SENTRY_PROJECT",
            "SENTRY_AUTH_TOKEN",
            "NEXT_PUBLIC_APP_ENV",
            "APP_ENV",
            "NEXT_PUBLIC_SENTRY_RELEASE",
            "SENTRY_RELEASE",
            "FRONTEND_OBSERVABILITY_INTERNAL_SECRET",
        ),
        required_files=(
            Path("frontend/src/instrumentation-client.ts"),
            Path("frontend/sentry.server.config.ts"),
            Path("frontend/sentry.edge.config.ts"),
            Path("frontend/next.config.ts"),
            Path("frontend/src/shared/lib/sentry-privacy.ts"),
            Path("frontend/src/app/api/observability/sentry-contract/route.ts"),
        ),
        required_snippets=(
            (Path("frontend/src/instrumentation-client.ts"), "sendDefaultPii: false"),
            (Path("frontend/src/instrumentation-client.ts"), "beforeSend(event)"),
            (Path("frontend/src/instrumentation-client.ts"), "NEXT_PUBLIC_SENTRY_DSN"),
            (Path("frontend/src/instrumentation-client.ts"), "NEXT_PUBLIC_SENTRY_RELEASE"),
            (Path("frontend/next.config.ts"), "SENTRY_AUTH_TOKEN"),
            (Path("frontend/next.config.ts"), "SENTRY_ORG"),
            (Path("frontend/next.config.ts"), "SENTRY_PROJECT"),
            (Path("frontend/next.config.ts"), "widenClientFileUpload: true"),
            (Path("frontend/src/app/api/observability/sentry-contract/route.ts"), "runtimeSurface: 'frontend'"),
            (Path("frontend/src/shared/lib/sentry-privacy.ts"), "authorization"),
        ),
        forbidden_snippets=(
            (Path("frontend/src/instrumentation-client.ts"), "process.env.APP_ENV"),
            (Path("frontend/src/instrumentation-client.ts"), "process.env.SENTRY_RELEASE"),
        ),
    ),
    Surface(
        name="admin",
        sentry_project="web-admin",
        env_example=Path("admin/.env.example"),
        required_env_keys=(
            "NEXT_PUBLIC_SENTRY_DSN",
            "SENTRY_DSN",
            "SENTRY_ORG",
            "SENTRY_PROJECT",
            "SENTRY_AUTH_TOKEN",
            "NEXT_PUBLIC_APP_ENV",
            "APP_ENV",
            "NEXT_PUBLIC_SENTRY_RELEASE",
            "SENTRY_RELEASE",
            "FRONTEND_OBSERVABILITY_INTERNAL_SECRET",
        ),
        required_files=(
            Path("admin/src/instrumentation-client.ts"),
            Path("admin/sentry.server.config.ts"),
            Path("admin/sentry.edge.config.ts"),
            Path("admin/next.config.ts"),
            Path("admin/src/shared/lib/sentry-privacy.ts"),
            Path("admin/src/app/api/observability/sentry-contract/route.ts"),
        ),
        required_snippets=(
            (Path("admin/src/instrumentation-client.ts"), "sendDefaultPii: false"),
            (Path("admin/src/instrumentation-client.ts"), "beforeSend(event)"),
            (Path("admin/src/instrumentation-client.ts"), "NEXT_PUBLIC_SENTRY_DSN"),
            (Path("admin/src/instrumentation-client.ts"), "NEXT_PUBLIC_SENTRY_RELEASE"),
            (Path("admin/next.config.ts"), "SENTRY_AUTH_TOKEN"),
            (Path("admin/next.config.ts"), "SENTRY_ORG"),
            (Path("admin/next.config.ts"), "SENTRY_PROJECT"),
            (Path("admin/next.config.ts"), "widenClientFileUpload: true"),
            (Path("admin/src/app/api/observability/sentry-contract/route.ts"), "runtimeSurface: 'admin'"),
            (Path("admin/src/shared/lib/sentry-privacy.ts"), "authorization"),
        ),
        forbidden_snippets=(
            (Path("admin/src/instrumentation-client.ts"), "process.env.APP_ENV"),
            (Path("admin/src/instrumentation-client.ts"), "process.env.SENTRY_RELEASE"),
        ),
    ),
    Surface(
        name="backend",
        sentry_project="backend-api",
        env_example=Path("backend/.env.example"),
        required_env_keys=("SENTRY_DSN", "SENTRY_RELEASE", "ENVIRONMENT"),
        required_files=(
            Path("backend/src/main.py"),
            Path("backend/src/config/settings.py"),
            Path("backend/src/shared/observability.py"),
        ),
        required_snippets=(
            (Path("backend/src/main.py"), "sentry_sdk.init"),
            (Path("backend/src/main.py"), "send_default_pii=False"),
            (Path("backend/src/main.py"), "max_request_body_size=\"never\""),
            (Path("backend/src/main.py"), "include_local_variables=False"),
            (Path("backend/src/main.py"), "before_send=before_send"),
            (Path("backend/src/main.py"), "FastApiIntegration"),
            (Path("backend/src/shared/observability.py"), "authorization"),
            (Path("backend/src/shared/observability.py"), "remnawave"),
        ),
    ),
    Surface(
        name="telegram-bot",
        sentry_project="telegram-bot",
        env_example=Path("services/telegram-bot/.env.example"),
        required_env_keys=(
            "SENTRY_DSN",
            "SENTRY_RELEASE",
            "ENVIRONMENT",
            "TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET",
        ),
        required_files=(
            Path("services/telegram-bot/src/main.py"),
            Path("services/telegram-bot/src/config.py"),
        ),
        required_snippets=(
            (Path("services/telegram-bot/src/main.py"), "sentry_sdk.init"),
            (Path("services/telegram-bot/src/main.py"), "send_default_pii=False"),
            (Path("services/telegram-bot/src/main.py"), "max_request_body_size=\"never\""),
            (Path("services/telegram-bot/src/main.py"), "include_local_variables=False"),
            (Path("services/telegram-bot/src/main.py"), "before_send=_before_send"),
            (Path("services/telegram-bot/src/main.py"), "/observability/sentry-contract"),
            (Path("services/telegram-bot/src/config.py"), "observability_internal_secret"),
        ),
    ),
    Surface(
        name="task-worker",
        sentry_project="task-worker",
        env_example=Path("services/task-worker/.env.example"),
        required_env_keys=("SENTRY_DSN", "SENTRY_RELEASE", "ENVIRONMENT"),
        required_files=(
            Path("services/task-worker/src/broker.py"),
            Path("services/task-worker/src/config.py"),
            Path("services/task-worker/src/observability.py"),
        ),
        required_snippets=(
            (Path("services/task-worker/src/broker.py"), "sentry_sdk.init"),
            (Path("services/task-worker/src/broker.py"), "send_default_pii=False"),
            (Path("services/task-worker/src/broker.py"), "max_request_body_size=\"never\""),
            (Path("services/task-worker/src/broker.py"), "include_local_variables=False"),
            (Path("services/task-worker/src/broker.py"), "before_send=before_send"),
            (Path("services/task-worker/src/observability.py"), "authorization"),
            (Path("services/task-worker/src/observability.py"), "payment"),
        ),
    ),
)


def read_text(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def env_key_present(env_text: str, key: str) -> bool:
    return any(
        line.startswith(f"{key}=") or line.startswith(f"# {key}=")
        for line in env_text.splitlines()
    )


def main() -> int:
    errors: list[str] = []
    lines = [
        "# S1-OBS-001 Sentry Critical Project Contract",
        "",
        "| Surface | Sentry project | Env example | Runtime/build contract |",
        "| --- | --- | --- | --- |",
    ]

    for surface in SURFACES:
        env_path = ROOT / surface.env_example
        if not env_path.exists():
            errors.append(f"{surface.name}: missing env example {surface.env_example}")
            env_text = ""
        else:
            env_text = env_path.read_text(encoding="utf-8")

        for key in surface.required_env_keys:
            if not env_key_present(env_text, key):
                errors.append(f"{surface.name}: {surface.env_example} missing {key}")

        if surface.sentry_project and surface.sentry_project not in env_text and surface.name in {"frontend", "admin"}:
            errors.append(
                f"{surface.name}: {surface.env_example} must document project {surface.sentry_project}"
            )

        for path in surface.required_files:
            if not (ROOT / path).exists():
                errors.append(f"{surface.name}: missing required file {path}")

        for path, snippet in surface.required_snippets:
            if not (ROOT / path).exists():
                continue
            text = read_text(path)
            if snippet not in text:
                errors.append(f"{surface.name}: {path} missing snippet `{snippet}`")

        for path, snippet in surface.forbidden_snippets:
            if not (ROOT / path).exists():
                continue
            text = read_text(path)
            if snippet in text:
                errors.append(f"{surface.name}: {path} contains forbidden snippet `{snippet}`")

        lines.append(
            f"| `{surface.name}` | `{surface.sentry_project}` | `{surface.env_example}` | checked |"
        )

    print("\n".join(lines))
    print("")

    if errors:
        print("Result: FAIL")
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Result: PASS")
    print("Live Sentry DSN/dashboard/alert evidence remains a separate go-live gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
