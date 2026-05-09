> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-05
> Backlog ID: `S1-QA-002`
> Статус: PASS for local/no-cost S1 dependency audit gate. Repeat on final RC images/artifacts before go-live.

# S1-QA-002 Dependency Audit Evidence

## Purpose

`S1-QA-002` checks the S1 Controlled Public Beta dependency surface for known high/critical vulnerabilities before continuing release preparation.

This gate covers the launch-critical S1 B2C runtime surfaces:

- root npm workspace lock;
- customer frontend / Telegram Mini App frontend;
- admin frontend;
- backend API;
- Telegram Bot;
- task worker and scheduler;
- local S1 Python service container images.

Out-of-S1 surfaces are explicitly excluded from this gate and must be audited before their own stage enablement:

- partner portal/payouts: Stage 3;
- mobile apps: Stage 4;
- desktop, Android TV and browser extension: Stage 5;
- Helix/Verta/Beep private transport and node fleet experiments: Stage 6;
- SDKs and experimental packages not deployed in S1 runtime.

## Summary

| Area | Result | Notes |
|---|---|---|
| npm root workspace | PASS for high/critical | `npm audit` reports only moderate `postcss` via `next` |
| frontend npm | PASS for high/critical | Same moderate `postcss` via `next`; no high/critical |
| admin npm | PASS for high/critical | Same moderate `postcss` via `next`; no high/critical |
| backend Python lock export | PASS | runtime and dev exports clean in `pip-audit` |
| Telegram Bot Python lock export | PASS | runtime and dev exports clean in `pip-audit` |
| task-worker Python lock export | PASS | runtime and dev exports clean in `pip-audit` |
| S1 Python container images | PASS after remediation | Debian `slim-bookworm` high CVEs removed by switching S1 Python Dockerfiles to `python:3.13.13-alpine` |
| frontend/admin container images | Not present in repo | If S1 deploy containerizes these apps, image build/scan evidence must be added before first RC |

2026-05-09 repeat during `S1-AUTH-007`: `npm --prefix frontend audit fix --package-lock-only` was applied as a safe lockfile-only forward refresh. It removed the previous frontend high audit finding and both frontend production/full audits now pass the high/critical threshold. The remaining npm finding is still the moderate Next/PostCSS advisory where npm recommends a breaking `next@9.3.3` downgrade; that force fix remains prohibited.

## npm Audit Commands

```bash
npm audit --omit=dev --audit-level=high
npm audit --audit-level=high

cd frontend
npm audit --omit=dev --audit-level=high
npm audit --audit-level=high

cd ../admin
npm audit --omit=dev --audit-level=high
npm audit --audit-level=high
```

Observed result for root, frontend and admin:

```text
0 critical, 0 high
2 moderate vulnerabilities
Package: postcss <8.5.10
Path: node_modules/next/node_modules/postcss
Advisory: GHSA-qx2v-qp2m-jg93
Audit auto-fix would install next@9.3.3, which is a breaking downgrade.
```

Decision:

- No high/critical npm finding blocks S1 local work.
- The moderate `postcss` advisory remains tracked as accepted local risk until a forward Next.js dependency path is available.
- Do not run `npm audit fix --force` because it proposes a downgrade to `next@9.3.3`, which violates the project version-management rule and would break the Next.js 16 stack.
- Re-run npm audits on the first `stage1-beta-rc.N` tag and after any Next.js lockfile refresh.

## Python Lock Export and pip-audit Commands

The Python audit used exported dependency files from `uv.lock`, not a random active virtual environment.

Backend:

```bash
cd backend

tmp=$(mktemp)
uv export --frozen --format requirements.txt --no-dev --no-emit-project --no-hashes --output-file "$tmp"
uvx pip-audit --progress-spinner off -r "$tmp"
rm -f "$tmp"

tmp=$(mktemp)
uv export --frozen --format requirements.txt --all-extras --all-groups --no-emit-project --no-hashes --output-file "$tmp"
uvx pip-audit --progress-spinner off -r "$tmp"
rm -f "$tmp"
```

Observed result:

```text
backend runtime deps: 80
No known vulnerabilities found
backend dev deps: 92
No known vulnerabilities found
```

Telegram Bot:

```bash
cd services/telegram-bot

tmp=$(mktemp)
uv export --frozen --format requirements.txt --no-dev --no-emit-project --no-hashes --output-file "$tmp"
uvx pip-audit --progress-spinner off -r "$tmp"
rm -f "$tmp"

tmp=$(mktemp)
uv export --frozen --format requirements.txt --all-extras --all-groups --no-emit-project --no-hashes --output-file "$tmp"
uvx pip-audit --progress-spinner off -r "$tmp"
rm -f "$tmp"
```

Observed result:

```text
telegram-bot runtime deps: 39
No known vulnerabilities found
telegram-bot dev deps: 72
No known vulnerabilities found
```

Task Worker:

```bash
cd services/task-worker

tmp=$(mktemp)
uv export --frozen --format requirements.txt --no-dev --no-emit-project --no-hashes --output-file "$tmp"
uvx pip-audit --progress-spinner off -r "$tmp"
rm -f "$tmp"

tmp=$(mktemp)
uv export --frozen --format requirements.txt --all-extras --all-groups --no-emit-project --no-hashes --output-file "$tmp"
uvx pip-audit --progress-spinner off -r "$tmp"
rm -f "$tmp"
```

Observed result:

```text
task-worker runtime deps: 43
No known vulnerabilities found
task-worker dev deps: 66
No known vulnerabilities found
```

## Container Scan Finding and Remediation

Initial Docker Scout scan of the existing local `slim-bookworm` S1 service image found high base-image vulnerabilities:

```text
remnawave-local-cybervpn-scheduler:latest
0 critical, 3 high
gnutls28: CVE-2026-33846, CVE-2026-33845
glibc: CVE-2026-5435
Fixed version: not fixed
```

The Python base-image comparison showed:

```text
registry://python:3.13.13-alpine
0 critical, 0 high, 0 medium, 0 low
```

Remediation applied:

| File | Change |
|---|---|
| `backend/Dockerfile` | `python:3.13.13-slim-bookworm` -> `python:3.13.13-alpine`; `apt-get build-essential` -> `apk add build-base`; Debian user commands -> Alpine `addgroup/adduser` |
| `services/telegram-bot/Dockerfile` | Same base-image and build-dependency change; Alpine user creation |
| `services/task-worker/Dockerfile` | Same base-image and build-dependency change |
| `infra/scripts/Dockerfile.metrics-seed` | `python:3.13.13-slim-bookworm` -> `python:3.13.13-alpine` |

## Container Build and Docker Scout Commands

```bash
docker build -t cybervpn-backend-qa002:latest backend
docker build -t cybervpn-telegram-bot-qa002:latest services/telegram-bot
docker build -t cybervpn-task-worker-qa002:latest services/task-worker
docker build -t cybervpn-task-scheduler-qa002:latest services/task-worker
docker build -t cybervpn-metrics-seed-qa002:latest -f infra/scripts/Dockerfile.metrics-seed infra/scripts

for image in \
  cybervpn-backend-qa002:latest \
  cybervpn-telegram-bot-qa002:latest \
  cybervpn-task-worker-qa002:latest \
  cybervpn-task-scheduler-qa002:latest \
  cybervpn-metrics-seed-qa002:latest; do
  docker scout cves --only-severity critical,high "local://$image"
done
```

Observed Docker Scout result after remediation:

| Image | Packages indexed | Critical | High | Result |
|---|---:|---:|---:|---|
| `cybervpn-backend-qa002:latest` | 122 | 0 | 0 | PASS |
| `cybervpn-telegram-bot-qa002:latest` | 83 | 0 | 0 | PASS |
| `cybervpn-task-worker-qa002:latest` | 84 | 0 | 0 | PASS |
| `cybervpn-task-scheduler-qa002:latest` | 84 | 0 | 0 | PASS |
| `cybervpn-metrics-seed-qa002:latest` | 40 | 0 | 0 | PASS |

Container dependency integrity smoke:

```bash
docker run --rm cybervpn-backend-qa002:latest pip check
docker run --rm --entrypoint /opt/venv/bin/pip cybervpn-telegram-bot-qa002:latest check
docker run --rm cybervpn-task-worker-qa002:latest pip check
docker run --rm cybervpn-metrics-seed-qa002:latest pip check
```

Observed result:

```text
No broken requirements found.
```

Note: direct import of backend/bot/worker entry modules was not used as the image smoke assertion because those modules intentionally require runtime secrets/env values such as Remnawave, JWT, Telegram and payment tokens.

## Scanner Availability

| Scanner | Available | Used |
|---|---:|---:|
| `npm audit` | Yes | Yes |
| `uv export` + `pip-audit` | Yes | Yes |
| Docker Scout | Yes | Yes |
| Trivy | No | No |
| Grype | No | No |
| Syft | No | No |
| cargo-audit | No | No |
| osv-scanner | No | No |

Rust, Flutter, desktop, browser-extension and private-transport dependency audits are deliberately not closed here because those components are outside S1 runtime and belong to later launch stages.

## Remaining Requirements Before RC / Go-Live

| Requirement | Status |
|---|---|
| Re-run npm audits on immutable `stage1-beta-rc.N` tag | Required before RC |
| Rebuild production images from the updated Dockerfiles | Required before RC |
| Re-run Docker Scout on final RC images, not only `*-qa002` local images | Required before RC |
| Add frontend/admin container image scans if frontend/admin are deployed as containers in S1 | Required if containerized |
| Track moderate Next/PostCSS advisory until forward fix exists | Required |
| Audit excluded Stage 3-6 surfaces before enabling them | Required later |

## Acceptance Result

`S1-QA-002` is **completed locally** for S1 no-cost dependency audit.

No known high/critical vulnerability remains in the audited S1 npm, Python lock exports or rebuilt S1 Python service images.

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-QA-002` as item `28` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| Root `npm audit --omit=dev --audit-level=high` and `npm audit --audit-level=high` | PASS for high/critical; known moderate Next/PostCSS advisory remains |
| Frontend `npm audit --omit=dev --audit-level=high` and `npm audit --audit-level=high` | PASS for high/critical; known moderate Next/PostCSS advisory remains |
| Admin `npm audit --omit=dev --audit-level=high` and `npm audit --audit-level=high` | PASS for high/critical; known moderate Next/PostCSS advisory remains |
| Backend `uv export --no-dev` + `pip-audit` | PASS: `80` runtime deps, no known vulnerabilities |
| Backend `uv export --all-extras --all-groups` + `pip-audit` | PASS: `92` all-groups deps, no known vulnerabilities |
| Telegram Bot `uv export --no-dev` + `pip-audit` | PASS: `39` runtime deps, no known vulnerabilities |
| Telegram Bot `uv export --all-extras --all-groups` + `pip-audit` | PASS: `72` all-groups deps, no known vulnerabilities |
| Task Worker `uv export --no-dev` + `pip-audit` | PASS: `43` runtime deps, no known vulnerabilities |
| Task Worker `uv export --all-extras --all-groups` + `pip-audit` | PASS: `66` all-groups deps, no known vulnerabilities |
| Docker Scout high/critical scan for `cybervpn-backend-qa002`, `cybervpn-telegram-bot-qa002`, `cybervpn-task-worker-qa002`, `cybervpn-task-scheduler-qa002`, `cybervpn-metrics-seed-qa002` | PASS: all reported `0C / 0H` |
| Container `pip check` for backend, Telegram Bot, task-worker and metrics-seed images | PASS: no broken requirements |

The Python audits printed transient `cachecontrol.controller` cache deserialization warnings in some projects, but each audit completed successfully with `No known vulnerabilities found`.

`S1-OBS-001`, `S1-OBS-002`, `S1-OBS-003` and `S1-OBS-004` were completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`, `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` and `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
