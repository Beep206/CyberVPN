#!/usr/bin/env python3
"""Run a local browser-to-backend partner attribution smoke with SQL evidence."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from re import IGNORECASE, sub
from typing import Any

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"

os.environ.setdefault("REMNAWAVE_TOKEN", "browser-e2e-local-remnawave-token")
os.environ.setdefault(
    "JWT_SECRET", "browser-e2e-local-jwt-secret-with-at-least-32-characters"
)
os.environ.setdefault("CRYPTOBOT_TOKEN", "browser-e2e-local-cryptobot-token")
os.environ.setdefault(
    "PAYMENT_SETTLEMENT_WORKER_SECRET", "browser-e2e-local-worker-secret"
)
os.environ.setdefault("PARTNER_ATTRIBUTION_ENABLED", "true")
os.environ.setdefault("PARTNER_CODES_ENABLED", "true")
os.environ.setdefault("SWAGGER_ENABLED", "false")

sys.path.insert(0, str(BACKEND_DIR))

from src.application.use_cases.partner_attribution.utils import (
    hash_partner_attribution_token,
)  # noqa: E402
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel  # noqa: E402
from src.infrastructure.database.models.brand_model import BrandModel  # noqa: E402
from src.infrastructure.database.models.mobile_user_model import MobileUserModel  # noqa: E402
from src.infrastructure.database.models.partner_model import (  # noqa: E402
    PartnerAccountModel,
    PartnerCodeLinkModel,
    PartnerCodeModel,
)
from src.infrastructure.database.models.storefront_model import StorefrontModel  # noqa: E402


def _free_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found from {start}")


def _asyncpg_url(admin_url: str, database: str | None = None) -> str:
    if admin_url.startswith("postgresql+asyncpg://"):
        url = admin_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    else:
        url = admin_url
    if database is None:
        return url
    prefix, _sep, _db = url.rpartition("/")
    return f"{prefix}/{database}"


def _sqlalchemy_url(admin_url: str, database: str) -> str:
    url = _asyncpg_url(admin_url, database)
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


async def _create_database(admin_url: str, database: str) -> None:
    conn = await asyncpg.connect(_asyncpg_url(admin_url))
    try:
        await conn.execute(f'CREATE DATABASE "{database}"')
    finally:
        await conn.close()


async def _drop_database(admin_url: str, database: str) -> None:
    conn = await asyncpg.connect(_asyncpg_url(admin_url))
    try:
        await conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1
              AND pid <> pg_backend_pid()
            """,
            database,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{database}"')
    finally:
        await conn.close()


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _run_alembic(database_url: str, redis_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "REDIS_URL": redis_url,
            "PAYMENT_SETTLEMENT_WORKER_SECRET": "codex-local-secret",
            "PARTNER_ATTRIBUTION_ENABLED": "true",
            "PARTNER_CODES_ENABLED": "true",
            "SWAGGER_ENABLED": "false",
        }
    )
    return _run(
        [str(BACKEND_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        timeout=180,
    )


async def _seed_capture_fixture(database_url: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:12]
    public_slug = f"browser-e2e-{suffix}"
    now = datetime.now(UTC)
    engine = create_async_engine(database_url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with maker() as session:
            realm = AuthRealmModel(
                id=uuid.uuid4(),
                realm_key=f"browser-customer-{suffix}",
                realm_type="customer",
                display_name="Browser E2E Customer Realm",
                audience=f"cybervpn:browser-e2e:{suffix}",
                cookie_namespace=f"be2e{suffix}",
                status="active",
                is_default=True,
            )
            brand = BrandModel(
                id=uuid.uuid4(),
                brand_key=f"browser-brand-{suffix}",
                display_name="Browser E2E Brand",
                status="active",
            )
            storefront = StorefrontModel(
                id=uuid.uuid4(),
                storefront_key=f"browser-storefront-{suffix}",
                brand_id=brand.id,
                display_name="Browser E2E Storefront",
                host="127.0.0.1",
                auth_realm_id=realm.id,
                status="active",
            )
            owner = MobileUserModel(
                id=uuid.uuid4(),
                auth_realm_id=realm.id,
                email=f"browser-owner-{suffix}@example.test",
                password_hash="browser-e2e-hash",
                is_active=True,
                status="active",
                is_partner=True,
                created_at=now,
            )
            account = PartnerAccountModel(
                id=uuid.uuid4(),
                account_key=f"browser-account-{suffix}",
                display_name="Browser E2E Partner",
                status="active",
                legacy_owner_user_id=owner.id,
            )
            code = PartnerCodeModel(
                id=uuid.uuid4(),
                code=f"BE2E{suffix[:8].upper()}",
                code_normalized=f"BE2E{suffix[:8].upper()}",
                public_slug=f"legacy-browser-{suffix}",
                public_token_hash=hash_partner_attribution_token(
                    f"legacy-browser-{suffix}"
                ),
                partner_account_id=account.id,
                partner_user_id=owner.id,
                markup_pct=Decimal("7.00"),
                is_active=True,
                lifecycle_status="active",
                approval_status="approved",
                owner_type="affiliate",
                lane_key="creator_affiliate",
                attribution_model="last_eligible_touch",
                attribution_window_seconds=30 * 24 * 60 * 60,
                default_storefront_id=storefront.id,
                destination_path="/pricing",
                allowed_channels=["content", "web"],
                allowed_storefront_ids=["*"],
                allowed_geographies=["*"],
                sub_id_schema={},
            )
            link = PartnerCodeLinkModel(
                id=uuid.uuid4(),
                public_slug=public_slug,
                partner_code_id=code.id,
                partner_account_id=account.id,
                link_kind="deep_link",
                destination_key="pricing",
                destination_path="/pricing",
                locale="ru-RU",
                sale_channel="content",
                campaign_params={"utm_source": "browser_seed"},
                sub_ids={"seed": "browser"},
                status="active",
            )
            session.add_all([realm, brand, storefront, owner, account])
            await session.flush()
            session.add(code)
            await session.flush()
            session.add(link)
            await session.commit()
    finally:
        await engine.dispose()

    return {
        "public_slug": public_slug,
        "realm_id": str(realm.id),
        "storefront_id": str(storefront.id),
        "partner_account_id": str(account.id),
        "partner_code_id": str(code.id),
        "partner_code_link_id": str(link.id),
    }


def _start_backend(
    database_url: str, redis_url: str, port: int
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "REDIS_URL": redis_url,
            "PAYMENT_SETTLEMENT_WORKER_SECRET": "codex-local-secret",
            "PARTNER_ATTRIBUTION_ENABLED": "true",
            "PARTNER_CODES_ENABLED": "true",
            "SWAGGER_ENABLED": "false",
            "ENVIRONMENT": "development",
        }
    )
    return subprocess.Popen(
        [
            str(BACKEND_PYTHON),
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--lifespan",
            "off",
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_frontend(backend_port: int, frontend_port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(
        {
            "API_URL": f"http://127.0.0.1:{backend_port}",
            "NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{backend_port}",
            "NEXT_PUBLIC_APP_ENV": "development",
            "NEXT_TELEMETRY_DISABLED": "1",
            "NODE_ENV": "development",
        }
    )
    return subprocess.Popen(
        [
            "node",
            str(REPO_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"),
            "dev",
            "--turbopack",
            "-p",
            str(frontend_port),
            "-H",
            "127.0.0.1",
        ],
        cwd=FRONTEND_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait_http(url: str, *, accepted_statuses: set[int], timeout: int) -> int:
    deadline = time.time() + timeout
    last_error: str | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status in accepted_statuses:
                    return response.status
        except urllib.error.HTTPError as exc:
            if exc.code in accepted_statuses:
                return exc.code
            last_error = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - diagnostic wait loop
            last_error = repr(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}; last error: {last_error}")


def _run_chrome(url: str, user_data_dir: Path) -> subprocess.CompletedProcess[str]:
    chrome = (
        shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if chrome is None:
        raise RuntimeError("google-chrome/chromium executable was not found")
    return _run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-background-networking",
            "--host-resolver-rules=MAP cyber-vpn.net 127.0.0.1,MAP www.cyber-vpn.net 127.0.0.1,MAP my.cyber-vpn.net 127.0.0.1",
            f"--user-data-dir={user_data_dir}",
            "--virtual-time-budget=5000",
            "--dump-dom",
            url,
        ],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        timeout=60,
    )


def _read_browser_cookie_metadata(user_data_dir: Path) -> dict[str, Any]:
    cookie_db = user_data_dir / "Default" / "Cookies"
    if not cookie_db.exists():
        return {"present": False, "reason": "cookie_db_missing"}
    conn = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """
            select host_key, name, is_httponly, is_secure, samesite
            from cookies
            where name = 'cv_partner_browser'
            order by creation_utc desc
            limit 1
            """
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"present": False, "reason": "cookie_not_found"}
    return {
        "present": True,
        "host_key": row[0],
        "name": row[1],
        "is_httponly": bool(row[2]),
        "is_secure": bool(row[3]),
        "samesite": row[4],
    }


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _redact_url_tokens(value: str) -> str:
    redacted = sub(
        r"([?&#](?:pat|token|transfer_token|access_token|refresh_token|authorization|cookie)=)[^&\"'\\s<>#]+",
        r"\1[REDACTED]",
        value,
        flags=IGNORECASE,
    )
    redacted = sub(
        r"(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}",
        r"\1[REDACTED]",
        redacted,
        flags=IGNORECASE,
    )
    return sub(
        r"\b(eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b",
        "[REDACTED_JWT]",
        redacted,
    )


def _process_output_summary(stdout: str | None, stderr: str | None) -> dict[str, Any]:
    safe_stdout = _redact_url_tokens(stdout or "")
    safe_stderr = _redact_url_tokens(stderr or "")
    return {
        "stdout_bytes": len(stdout or ""),
        "stderr_bytes": len(stderr or ""),
        "ready_marker_seen": "Ready" in safe_stdout or "Uvicorn running" in safe_stderr,
        "redaction_marker_seen": "[REDACTED]" in safe_stdout
        or "[REDACTED]" in safe_stderr,
    }


async def _collect_sql_evidence(
    database_url: str, fixture: dict[str, str]
) -> dict[str, Any]:
    conn = await asyncpg.connect(_asyncpg_url(database_url))
    try:
        link = await conn.fetchrow(
            """
            select id::text, public_slug, partner_code_id::text, partner_account_id::text, status
            from partner_code_links
            where id = $1::uuid
            """,
            fixture["partner_code_link_id"],
        )
        sessions = await conn.fetch(
            """
            select id::text,
                   status,
                   partner_code_id::text,
                   partner_code_link_id::text,
                   partner_account_id::text,
                   transfer_token_hash is not null as has_transfer_token_hash,
                   session_token_hash is null as session_token_not_set,
                   destination_path,
                   locale,
                   sale_channel,
                   sub_ids::jsonb as sub_ids,
                   campaign_params::jsonb as campaign_params,
                   evidence_payload::jsonb as evidence_payload,
                   source_path
            from partner_attribution_sessions
            where partner_code_link_id = $1::uuid
            order by created_at desc
            """,
            fixture["partner_code_link_id"],
        )
        touchpoints = await conn.fetch(
            """
            select id::text,
                   touchpoint_type,
                   partner_code_id::text,
                   partner_attribution_session_id::text,
                   idempotency_key,
                   source_event_id
            from attribution_touchpoints
            where partner_attribution_session_id = any($1::uuid[])
            order by created_at asc
            """,
            [row["id"] for row in sessions],
        )
        outbox = await conn.fetch(
            """
            select event_name, aggregate_id, event_key
            from outbox_events
            where aggregate_id = any($1::text[])
            order by created_at asc
            """,
            [row["id"] for row in sessions],
        )
        table_counts = {}
        for table in (
            "partner_code_links",
            "partner_attribution_sessions",
            "attribution_touchpoints",
            "customer_commercial_bindings",
            "order_attribution_results",
            "outbox_events",
            "earning_events",
            "earning_holds",
            "partner_statements",
            "statement_adjustments",
        ):
            table_counts[table] = await conn.fetchval(f"select count(*) from {table}")
    finally:
        await conn.close()

    session_rows = []
    for row in sessions:
        item = dict(row)
        item["sub_ids"] = _json_object(item.get("sub_ids"))
        item["campaign_params"] = _json_object(item.get("campaign_params"))
        item["evidence_payload"] = _json_object(item.get("evidence_payload"))
        session_rows.append(item)

    evidence: dict[str, Any] = {
        "link": dict(link) if link is not None else None,
        "sessions": session_rows,
        "touchpoints": [dict(row) for row in touchpoints],
        "outbox_events": [dict(row) for row in outbox],
        "table_counts": table_counts,
    }
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    check(link is not None, "partner_code_link row must exist")
    check(
        len(sessions) == 1,
        f"expected exactly one attribution session, got {len(sessions)}",
    )
    if session_rows:
        session = session_rows[0]
        check(
            session["status"] == "pending",
            f"session status must be pending, got {session['status']!r}",
        )
        check(
            session["partner_code_link_id"] == fixture["partner_code_link_id"],
            "session must reference seeded partner_code_link_id",
        )
        check(
            session["has_transfer_token_hash"] is True,
            "session must have transfer_token_hash",
        )
        check(
            session["session_token_not_set"] is True,
            "session_token_hash must not be persisted",
        )
        check(
            session["destination_path"] == "/pricing",
            f"destination_path mismatch: {session['destination_path']!r}",
        )
        check(session["locale"] == "ru-RU", f"locale mismatch: {session['locale']!r}")
        check(
            session["sale_channel"] == "content",
            f"sale_channel mismatch: {session['sale_channel']!r}",
        )
        check(
            (session["sub_ids"] or {}).get("seed") == "browser",
            "sub_ids.seed must be browser",
        )
        check(
            (session["campaign_params"] or {}).get("utm_source") == "browser_seed",
            "campaign_params.utm_source must be browser_seed",
        )
        check(
            (session["evidence_payload"] or {}).get("public_token_source")
            == "partner_code_link",
            "evidence_payload.public_token_source must be partner_code_link",
        )
        check(
            "pat=" not in (session["source_path"] or ""),
            "source_path must not persist attacker pat query",
        )
    check(
        len(touchpoints) == 1,
        f"expected exactly one attribution touchpoint, got {len(touchpoints)}",
    )
    if touchpoints:
        touchpoint = dict(touchpoints[0])
        session_id = session_rows[0]["id"] if session_rows else None
        check(
            touchpoint["touchpoint_type"] == "passive_click",
            f"touchpoint_type must be passive_click, got {touchpoint['touchpoint_type']!r}",
        )
        check(
            touchpoint["partner_attribution_session_id"] == session_id,
            "touchpoint must reference created attribution session",
        )
    check(len(outbox) == 1, f"expected exactly one outbox event, got {len(outbox)}")
    if outbox:
        check(
            outbox[0]["event_name"] == "partner.attribution.captured",
            f"outbox event_name mismatch: {outbox[0]['event_name']!r}",
        )
    check(
        table_counts["partner_code_links"] >= 1,
        "partner_code_links count must be at least 1",
    )
    check(
        table_counts["partner_attribution_sessions"] == 1,
        "partner_attribution_sessions count must be 1",
    )
    check(
        table_counts["attribution_touchpoints"] == 1,
        "attribution_touchpoints count must be 1",
    )
    check(table_counts["outbox_events"] == 1, "outbox_events count must be 1")
    evidence["validation_failures"] = failures
    return evidence


def _terminate(process: subprocess.Popen[str] | None) -> dict[str, Any]:
    if process is None:
        return {
            "returncode": None,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "ready_marker_seen": False,
            "redaction_marker_seen": False,
        }
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    try:
        stdout, stderr = process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return {
        "returncode": process.returncode,
        **_process_output_summary(stdout, stderr),
    }


async def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--postgres-admin-url",
        default=os.getenv(
            "CYBERVPN_E2E_POSTGRES_ADMIN_URL",
            "postgresql://postgres@127.0.0.1:6767/postgres",
        ),
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("CYBERVPN_E2E_REDIS_URL", "redis://127.0.0.1:6380/15"),
    )
    parser.add_argument("--backend-port", type=int, default=0)
    parser.add_argument("--frontend-port", type=int, default=0)
    parser.add_argument("--evidence", type=Path, default=None)
    parser.add_argument("--keep-database", action="store_true")
    args = parser.parse_args()

    if not BACKEND_PYTHON.exists():
        raise RuntimeError(f"Backend venv python not found at {BACKEND_PYTHON}")

    database = f"cvpn_browser_e2e_{uuid.uuid4().hex[:16]}"
    database_url = _sqlalchemy_url(args.postgres_admin_url, database)
    backend_port = args.backend_port or _free_port(9100)
    frontend_port = args.frontend_port or _free_port(9200)
    evidence_path = args.evidence or (
        REPO_ROOT
        / "docs"
        / "evidence"
        / "partner-attribution"
        / f"browser-sql-e2e-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    backend_process: subprocess.Popen[str] | None = None
    frontend_process: subprocess.Popen[str] | None = None
    tmp_dir = Path(tempfile.mkdtemp(prefix="cybervpn-browser-e2e-"))
    report: dict[str, Any] = {
        "status": "started",
        "database": database,
        "database_dropped": False,
        "backend_port": backend_port,
        "frontend_port": frontend_port,
        "started_at": datetime.now(UTC).isoformat(),
    }

    try:
        await _create_database(args.postgres_admin_url, database)
        alembic = _run_alembic(database_url, args.redis_url)
        report["alembic"] = {
            "returncode": alembic.returncode,
            **_process_output_summary(alembic.stdout, alembic.stderr),
        }
        if alembic.returncode != 0:
            raise RuntimeError("Alembic upgrade failed")

        fixture = await _seed_capture_fixture(database_url)
        report["fixture"] = fixture

        backend_process = _start_backend(database_url, args.redis_url, backend_port)
        _wait_http(
            f"http://127.0.0.1:{backend_port}/health",
            accepted_statuses={200},
            timeout=30,
        )
        report["backend_health"] = "ok"

        frontend_process = _start_frontend(backend_port, frontend_port)
        _wait_http(
            f"http://127.0.0.1:{frontend_port}/p/not-a-real-token-{uuid.uuid4().hex}",
            accepted_statuses={403, 404},
            timeout=60,
        )
        report["frontend_probe"] = "ok"

        attacker_param = "redacted-probe"
        browser_url = (
            f"http://cyber-vpn.net:{frontend_port}/p/{fixture['public_slug']}"
            "?destination=pricing&utm_source=browser_e2e&sub_creator=browser&click_id=browser-e2e-click"
            f"&locale=ru-RU&channel=content&pat={attacker_param}"
        )
        chrome = _run_chrome(browser_url, tmp_dir / "chrome")
        report["browser"] = {
            "url": _redact_url_tokens(browser_url),
            "returncode": chrome.returncode,
            **_process_output_summary(chrome.stdout, chrome.stderr),
            "cookie": _read_browser_cookie_metadata(tmp_dir / "chrome"),
        }
        if chrome.returncode != 0:
            raise RuntimeError("Chrome browser smoke failed")

        sql_evidence = await _collect_sql_evidence(database_url, fixture)
        report["sql_evidence"] = sql_evidence
        if sql_evidence["validation_failures"]:
            raise RuntimeError(
                "SQL evidence validation failed: "
                + "; ".join(sql_evidence["validation_failures"])
            )
        report["status"] = "passed"
        return 0
    except Exception as exc:  # noqa: BLE001 - report exact smoke failure
        report["status"] = "failed"
        report["error"] = repr(exc)
        return 1
    finally:
        report["frontend_process"] = _terminate(frontend_process)
        report["backend_process"] = _terminate(backend_process)
        if not args.keep_database:
            with suppress(Exception):
                await _drop_database(args.postgres_admin_url, database)
                report["database_dropped"] = True
        report["finished_at"] = datetime.now(UTC).isoformat()
        evidence_path.write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"wrote evidence: {evidence_path}")
        print(f"status: {report['status']}")
        if report["status"] != "passed":
            print(
                json.dumps(
                    {k: report.get(k) for k in ("error", "alembic", "browser")},
                    indent=2,
                    default=str,
                )
            )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
