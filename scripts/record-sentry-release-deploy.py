#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a Sentry release deploy marker via the Releases API.")
    parser.add_argument("--release", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--deploy-name", default="")
    parser.add_argument("--deploy-url", default="")
    parser.add_argument("--release-url", default="")
    parser.add_argument("--ref", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--started-at", default="")
    parser.add_argument("--finished-at", default="")
    parser.add_argument("--summary-label", default="")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--noop-on-missing-config", action="store_true")
    return parser.parse_args()


def iso_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_base_url() -> str:
    return os.environ.get("SENTRY_URL", "https://sentry.io").rstrip("/")


def request_json(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict | list | None]:
    body = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=f"{get_base_url()}{path}",
        method=method,
        data=body,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        data = json.loads(raw) if raw else None
        return exc.code, data


def ensure_release(org: str, token: str, release: str, projects: list[str], ref: str, release_url: str) -> str:
    encoded_release = urllib.parse.quote(release, safe="")
    status, _ = request_json(
        "GET",
        f"/api/0/organizations/{org}/releases/{encoded_release}/",
        token,
    )
    if status == 200:
        return "existing"
    if status != 404:
        raise RuntimeError(f"release lookup failed with status {status}")

    payload: dict[str, object] = {"version": release, "projects": projects}
    if ref:
        payload["ref"] = ref
    if release_url:
        payload["url"] = release_url

    status, _ = request_json("POST", f"/api/0/organizations/{org}/releases/", token, payload)
    if status not in {200, 201, 208}:
        raise RuntimeError(f"release creation failed with status {status}")
    return "created"


def create_deploy(
    org: str,
    token: str,
    release: str,
    environment: str,
    projects: list[str],
    deploy_name: str,
    deploy_url: str,
    started_at: str,
    finished_at: str,
) -> None:
    payload: dict[str, object] = {"environment": environment}
    if deploy_name:
        payload["name"] = deploy_name
    if deploy_url:
        payload["url"] = deploy_url
    if started_at:
        payload["dateStarted"] = started_at
    if finished_at:
        payload["dateFinished"] = finished_at
    if projects:
        payload["projects"] = projects

    encoded_release = urllib.parse.quote(release, safe="")
    status, _ = request_json(
        "POST",
        f"/api/0/organizations/{org}/releases/{encoded_release}/deploys/",
        token,
        payload,
    )
    if status not in {200, 201}:
        raise RuntimeError(f"deploy creation failed with status {status}")


def finalize_release(org: str, token: str, release: str, finished_at: str) -> None:
    encoded_release = urllib.parse.quote(release, safe="")
    status, _ = request_json(
        "PUT",
        f"/api/0/organizations/{org}/releases/{encoded_release}/",
        token,
        {"dateReleased": finished_at},
    )
    if status not in {200, 201}:
        raise RuntimeError(f"release finalization failed with status {status}")


def write_summary(message: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write(message)


def main() -> None:
    args = parse_args()
    org = os.environ.get("SENTRY_ORG", "").strip()
    token = os.environ.get("SENTRY_AUTH_TOKEN", "").strip()
    projects = list(dict.fromkeys(project for project in args.project if project and project != "unconfigured"))

    label = args.summary_label or f"{args.release} deploy marker"
    if not org or not token or not projects:
        if args.noop_on_missing_config:
            write_summary(
                f"### {label}\n"
                f"- Release: `{args.release}`\n"
                f"- Environment: `{args.environment}`\n"
                f"- Status: `skipped`\n"
                f"- Reason: missing `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, or release project configuration\n"
            )
            print("[sentry-release-deploy] skipped: missing configuration")
            return
        print("[sentry-release-deploy] ERROR: missing SENTRY_AUTH_TOKEN, SENTRY_ORG, or project configuration", file=sys.stderr)
        raise SystemExit(1)

    started_at = args.started_at or iso_now()
    finished_at = args.finished_at or iso_now()

    try:
        release_state = ensure_release(org, token, args.release, projects, args.ref, args.release_url)
        create_deploy(
            org=org,
            token=token,
            release=args.release,
            environment=args.environment,
            projects=projects,
            deploy_name=args.deploy_name,
            deploy_url=args.deploy_url,
            started_at=started_at,
            finished_at=finished_at,
        )
        if args.finalize:
            finalize_release(org, token, args.release, finished_at)
    except RuntimeError as exc:
        print(f"[sentry-release-deploy] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    write_summary(
        f"### {label}\n"
        f"- Release: `{args.release}`\n"
        f"- Environment: `{args.environment}`\n"
        f"- Projects: `{', '.join(projects)}`\n"
        f"- Release state: `{release_state}`\n"
        f"- Deploy marker: `created`\n"
        f"- Finalized: `{'true' if args.finalize else 'false'}`\n"
    )
    print(
        f"[sentry-release-deploy] release={args.release} environment={args.environment} "
        f"projects={len(projects)} finalized={'yes' if args.finalize else 'no'}"
    )


if __name__ == "__main__":
    main()
