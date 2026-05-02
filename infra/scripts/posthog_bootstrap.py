#!/usr/bin/env python3
"""Render bootstrap bundles for the non-prod PostHog foundation."""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

PUBLIC_CAPTURE_PATHS = [
    "/batch",
    "/batch/",
    "/batch/*",
    "/flags",
    "/flags/",
    "/flags/*",
    "/decide",
    "/decide/",
    "/decide/*",
    "/i/v0/e",
    "/i/v0/e/",
    "/i/v0/e/*",
    "/capture",
    "/capture/",
    "/capture/*",
    "/engage",
    "/engage/",
    "/engage/*",
    "/s",
    "/s/",
    "/s/*",
    "/track",
    "/track/",
    "/track/*",
    "/static/array.js",
    "/static/recorder-v2.js",
    "/static/recorder.js",
    "/static/surveys.js",
]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def quoted_yaml(value: str) -> str:
    return json.dumps(value)


def render_env(
    *,
    domain: str,
    project_name: str,
    posthog_app_tag: str,
    posthog_node_tag: str,
    posthog_repo_ref: str,
    registry_url: str,
    opt_out_capture: bool,
    trusted_proxies: str,
    disable_secure_ssl_redirect: bool,
    posthog_secret: str,
    encryption_salt_keys: str,
) -> str:
    allowed_hosts = f"{domain},127.0.0.1,localhost"
    lines = [
        f"DOMAIN={domain}",
        f"POSTHOG_PROJECT_NAME={project_name}",
        f"POSTHOG_APP_TAG={posthog_app_tag}",
        f"POSTHOG_NODE_TAG={posthog_node_tag}",
        f"POSTHOG_REPO_REF={posthog_repo_ref}",
        f"REGISTRY_URL={registry_url}",
        f"POSTHOG_SECRET={posthog_secret}",
        f"ENCRYPTION_SALT_KEYS={encryption_salt_keys}",
        f"OPT_OUT_CAPTURE={'true' if opt_out_capture else 'false'}",
        "IS_BEHIND_PROXY=True",
        f"TRUSTED_PROXIES={trusted_proxies}",
        f"ALLOWED_HOSTS={allowed_hosts}",
        f"DISABLE_SECURE_SSL_REDIRECT={'True' if disable_secure_ssl_redirect else 'False'}",
        "",
    ]
    return "\n".join(lines)


def render_compose_override() -> str:
    return """services:
  web:
    ports:
      - "127.0.0.1:8000:8000"
  capture:
    ports:
      - "127.0.0.1:3000:3000"
  feature-flags:
    ports:
      - "127.0.0.1:3001:3001"
  replay-capture:
    ports:
      - "127.0.0.1:3002:3000"
"""


def render_proxy_headers(forwarded_proto: str) -> str:
    return f"""proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto {forwarded_proto};
proxy_set_header Host $http_host;
proxy_redirect off;
"""


def render_public_locations(forwarded_proto: str) -> str:
    header_block = render_proxy_headers(forwarded_proto)
    rendered: list[str] = []
    for path in PUBLIC_CAPTURE_PATHS:
        upstream = "http://127.0.0.1:8000"
        if path.startswith("/flags") or path.startswith("/decide"):
            upstream = "http://127.0.0.1:3001"
        elif path.startswith("/s"):
            upstream = "http://127.0.0.1:3002"
        elif path.startswith("/batch") or path.startswith("/i/v0/e") or path.startswith("/capture") or path.startswith("/engage") or path.startswith("/track"):
            upstream = "http://127.0.0.1:3000"
        rendered.append(
            f"    location {'^~ ' if path.endswith('/*') else '= '}{path[:-1] if path.endswith('*') else path} {{\n"
            f"{''.join(f'        {line}\\n' for line in header_block.splitlines())}"
            f"        proxy_pass {upstream};\n"
            "    }\n"
        )
    return "".join(rendered)


def render_nginx_http_conf(domain: str, admin_cidrs: list[str], auth_realm: str) -> str:
    header_block = render_proxy_headers("http")
    allow_lines = "".join(f"        allow {cidr};\n" for cidr in admin_cidrs)
    return (
        "server {\n"
        "    listen 80;\n"
        f"    server_name {domain};\n"
        "\n"
        "    location /.well-known/acme-challenge/ {\n"
        "        root /var/www/certbot;\n"
        "    }\n"
        "\n"
        f"{render_public_locations('http')}"
        "    location / {\n"
        "        satisfy any;\n"
        f"{allow_lines}"
        "        deny all;\n"
        f"        auth_basic {quoted_yaml(auth_realm)};\n"
        "        auth_basic_user_file /etc/nginx/posthog.htpasswd;\n"
        f"{''.join(f'        {line}\\n' for line in header_block.splitlines())}"
        "        proxy_pass http://127.0.0.1:8000;\n"
        "    }\n"
        "}\n"
    )


def render_nginx_https_conf(domain: str, admin_cidrs: list[str], auth_realm: str) -> str:
    allow_lines = "".join(f"        allow {cidr};\n" for cidr in admin_cidrs)
    header_block = render_proxy_headers("https")
    return (
        "server {\n"
        "    listen 80;\n"
        f"    server_name {domain};\n"
        "\n"
        "    location /.well-known/acme-challenge/ {\n"
        "        root /var/www/certbot;\n"
        "    }\n"
        "\n"
        "    location / {\n"
        "        return 301 https://$host$request_uri;\n"
        "    }\n"
        "}\n"
        "\n"
        "server {\n"
        "    listen 443 ssl http2;\n"
        f"    server_name {domain};\n"
        f"    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;\n"
        f"    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;\n"
        "\n"
        f"{render_public_locations('https')}"
        "    location / {\n"
        "        satisfy any;\n"
        f"{allow_lines}"
        "        deny all;\n"
        f"        auth_basic {quoted_yaml(auth_realm)};\n"
        "        auth_basic_user_file /etc/nginx/posthog.htpasswd;\n"
        f"{''.join(f'        {line}\\n' for line in header_block.splitlines())}"
        "        proxy_pass http://127.0.0.1:8000;\n"
        "    }\n"
        "}\n"
    )


def render_backup_script(backup_retention_days: int) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

deploy_dir="/opt/posthog/self-host"
backup_root="/var/backups/posthog"
timestamp="$$(date -u +%Y%m%dT%H%M%SZ)"
target_dir="$$backup_root/$$timestamp"

mkdir -p "$$target_dir"

if [ -f "$$deploy_dir/.env" ]; then
  tar -czf "$$target_dir/config.tar.gz" \
    "$$deploy_dir/.env" \
    "$$deploy_dir/docker-compose.yml" \
    "$$deploy_dir/docker-compose.override.yml" \
    /etc/nginx/sites-available/posthog.conf \
    /etc/systemd/system/posthog-local-backup.service \
    /etc/systemd/system/posthog-local-backup.timer
fi

if docker compose -f "$$deploy_dir/docker-compose.yml" -f "$$deploy_dir/docker-compose.override.yml" ps db >/dev/null 2>&1; then
  docker compose -f "$$deploy_dir/docker-compose.yml" -f "$$deploy_dir/docker-compose.override.yml" exec -T db \
    pg_dump -U posthog posthog | gzip -c > "$$target_dir/postgres.sql.gz"
fi

find "$$backup_root" -mindepth 1 -maxdepth 1 -type d -mtime +{backup_retention_days} -exec rm -rf {{}} +
"""


def render_compose_start_script() -> str:
    return """#!/bin/bash
./compose/wait
./bin/migrate
./bin/docker-server
"""


def render_compose_wait_script() -> str:
    return """#!/usr/bin/env python3

import socket
import time


def wait_for(host: str, port: int) -> None:
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(5)


wait_for("clickhouse", 9000)
wait_for("db", 5432)
"""


def render_temporal_worker_script() -> str:
    return """#!/bin/bash
./bin/temporal-django-worker
"""


def render_install_script(
    *,
    domain: str,
    posthog_repo_ref: str,
    basic_auth_username: str,
    basic_auth_password: str,
    tls_email: str | None,
) -> str:
    tls_section = ""
    if tls_email:
        tls_section = f"""
if [ ! -f "/etc/letsencrypt/live/{domain}/fullchain.pem" ]; then
  certbot --nginx --non-interactive --agree-tos -m {json.dumps(tls_email)} -d {json.dumps(domain)} --keep-until-expiring
fi

install -m 0644 "$$bundle_dir/nginx/posthog-https.conf" /etc/nginx/sites-available/posthog.conf
nginx -t
systemctl reload nginx
"""

    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$$(cd "$$(dirname "$0")" && pwd)"
deploy_dir="/opt/posthog/self-host"
repo_dir="$$deploy_dir/posthog"

install -d -m 0750 "$$deploy_dir" /opt/posthog/bootstrap /var/backups/posthog /var/www/certbot

if [ ! -d "$$repo_dir/.git" ]; then
  git clone --filter=blob:none https://github.com/PostHog/posthog.git "$$repo_dir"
fi

cd "$$repo_dir"
git fetch --tags origin

if [ {json.dumps(posthog_repo_ref)} = "HEAD" ]; then
  default_branch="$$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')"
  git checkout "$$default_branch"
  git reset --hard "origin/$$default_branch"
else
  git checkout {json.dumps(posthog_repo_ref)}
fi

cd "$$deploy_dir"
cp "$$repo_dir/docker-compose.base.yml" "$$deploy_dir/docker-compose.base.yml"
cp "$$repo_dir/docker-compose.hobby.yml" "$$deploy_dir/docker-compose.yml"
cp "$$repo_dir/dev-services.env" "$$deploy_dir/dev-services.env"
install -d -m 0750 "$$deploy_dir/compose" "$$deploy_dir/share"

install -m 0600 "$$bundle_dir/.env" "$$deploy_dir/.env"
install -m 0640 "$$bundle_dir/docker-compose.override.yml" "$$deploy_dir/docker-compose.override.yml"
install -m 0750 "$$bundle_dir/posthog-local-backup.sh" /usr/local/sbin/posthog-local-backup.sh
install -m 0750 "$$bundle_dir/compose/start" "$$deploy_dir/compose/start"
install -m 0750 "$$bundle_dir/compose/wait" "$$deploy_dir/compose/wait"
install -m 0750 "$$bundle_dir/compose/temporal-django-worker" "$$deploy_dir/compose/temporal-django-worker"

printf '%s:%s\\n' {json.dumps(basic_auth_username)} "$$(openssl passwd -apr1 {json.dumps(basic_auth_password)})" > /etc/nginx/posthog.htpasswd
chmod 0640 /etc/nginx/posthog.htpasswd

install -m 0644 "$$bundle_dir/nginx/posthog-http.conf" /etc/nginx/sites-available/posthog.conf
ln -sfn /etc/nginx/sites-available/posthog.conf /etc/nginx/sites-enabled/posthog.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if [ ! -f "$$deploy_dir/share/GeoLite2-City.mmdb" ]; then
  curl -L 'https://mmdbcdn.posthog.net/' --http1.1 | brotli --decompress > "$$deploy_dir/share/GeoLite2-City.mmdb"
  printf '{{"date":"%s"}}\n' "$$(date +%Y-%m-%d)" > "$$deploy_dir/share/GeoLite2-City.json"
  chmod 0644 "$$deploy_dir/share/GeoLite2-City.mmdb" "$$deploy_dir/share/GeoLite2-City.json"
fi

services="$$(docker compose -f "$$deploy_dir/docker-compose.yml" -f "$$deploy_dir/docker-compose.override.yml" config --services | grep -vx proxy | tr '\n' ' ')"
docker compose -f "$$deploy_dir/docker-compose.yml" -f "$$deploy_dir/docker-compose.override.yml" up -d --no-build --pull always $$services
{tls_section}
systemctl status --no-pager nginx
docker compose -f "$$deploy_dir/docker-compose.yml" -f "$$deploy_dir/docker-compose.override.yml" ps
"""


def command_render_bundle(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    basic_auth_password = secrets.token_urlsafe(18)
    posthog_secret = secrets.token_hex(28)
    encryption_salt_keys = secrets.token_hex(16)

    write_text(
        output_dir / ".env",
        render_env(
            domain=args.domain,
            project_name=args.project_name,
            posthog_app_tag=args.posthog_app_tag,
            posthog_node_tag=args.posthog_node_tag,
            posthog_repo_ref=args.posthog_repo_ref,
            registry_url=args.registry_url,
            opt_out_capture=args.opt_out_capture,
            trusted_proxies=args.trusted_proxies,
            disable_secure_ssl_redirect=args.disable_secure_ssl_redirect,
            posthog_secret=posthog_secret,
            encryption_salt_keys=encryption_salt_keys,
        ),
        mode=0o600,
    )
    write_text(output_dir / "docker-compose.override.yml", render_compose_override())
    write_text(
        output_dir / "nginx" / "posthog-http.conf",
        render_nginx_http_conf(args.domain, args.admin_cidrs, args.auth_realm),
        mode=0o644,
    )
    write_text(
        output_dir / "nginx" / "posthog-https.conf",
        render_nginx_https_conf(args.domain, args.admin_cidrs, args.auth_realm),
        mode=0o644,
    )
    write_text(
        output_dir / "posthog-local-backup.sh",
        render_backup_script(args.backup_retention_days),
        mode=0o750,
    )
    write_text(output_dir / "compose" / "start", render_compose_start_script(), mode=0o750)
    write_text(output_dir / "compose" / "wait", render_compose_wait_script(), mode=0o750)
    write_text(output_dir / "compose" / "temporal-django-worker", render_temporal_worker_script(), mode=0o750)
    write_text(
        output_dir / "install-node.sh",
        render_install_script(
            domain=args.domain,
            posthog_repo_ref=args.posthog_repo_ref,
            basic_auth_username=args.basic_auth_username,
            basic_auth_password=basic_auth_password,
            tls_email=args.tls_email,
        ),
        mode=0o750,
    )

    credentials = {
        "domain": args.domain,
        "project_name": args.project_name,
        "basic_auth": {
            "username": args.basic_auth_username,
            "password": basic_auth_password,
        },
        "posthog_secret": posthog_secret,
        "encryption_salt_keys": encryption_salt_keys,
        "posthog_app_tag": args.posthog_app_tag,
        "posthog_node_tag": args.posthog_node_tag,
        "posthog_repo_ref": args.posthog_repo_ref,
        "registry_url": args.registry_url,
        "trusted_proxies": args.trusted_proxies,
        "disable_secure_ssl_redirect": args.disable_secure_ssl_redirect,
    }
    if args.tls_email:
        credentials["tls_email"] = args.tls_email
    write_text(output_dir / "credentials.json", json.dumps(credentials, indent=2) + "\n", mode=0o600)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render bootstrap bundles for the non-prod PostHog foundation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_bundle = subparsers.add_parser("render-bundle", help="Render env, proxy, backup, and install artifacts for a PostHog host")
    render_bundle.add_argument("--domain", required=True)
    render_bundle.add_argument("--output-dir", required=True)
    render_bundle.add_argument("--project-name", default="cybervpn-posthog-nonprod")
    render_bundle.add_argument("--posthog-app-tag", default="latest")
    render_bundle.add_argument("--posthog-node-tag", default="latest")
    render_bundle.add_argument("--posthog-repo-ref", default="HEAD")
    render_bundle.add_argument("--registry-url", default="posthog/posthog")
    render_bundle.add_argument("--basic-auth-username", default="cyberops")
    render_bundle.add_argument("--tls-email")
    render_bundle.add_argument("--auth-realm", default="CyberVPN PostHog nonprod")
    render_bundle.add_argument("--trusted-proxies", default="127.0.0.1")
    render_bundle.add_argument("--backup-retention-days", type=int, default=7)
    render_bundle.add_argument("--opt-out-capture", action=argparse.BooleanOptionalAction, default=True)
    render_bundle.add_argument("--disable-secure-ssl-redirect", action=argparse.BooleanOptionalAction, default=True)
    render_bundle.add_argument("--admin-cidr", dest="admin_cidrs", action="append", default=[])
    render_bundle.set_defaults(func=command_render_bundle)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
