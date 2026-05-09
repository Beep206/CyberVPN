> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-05
> Backlog ID: `S1-VPN-009`
> Статус: local API/UI usage display contract completed; staging/prod Remnawave usage evidence remains required.

# S1-VPN-009 Usage Display Evidence

## Purpose

`S1-VPN-009` closes the local S1 contract for customer-facing VPN traffic/usage display.

The S1 rule is strict: CyberVPN must either show authoritative aggregate usage from Remnawave, or clearly mark usage as unavailable. The product must not display fallback `0 B / unlimited` or `0 GB / 0 GB` as if it were accurate customer usage.

## Scope Completed

| Area | Result |
|---|---|
| Backend usage API | `GET /api/v1/users/me/usage` now returns explicit availability metadata |
| Backend fallback | Remnawave/user lookup failures return `usage_available=false`, `usage_source=unavailable`, and a reason |
| Mini App bootstrap | Usage snapshot now carries `usageAvailable`, `usageSource`, and `usageUnavailableReason` |
| Mini App fallback | Missing/unreachable Remnawave usage no longer breaks bootstrap and no longer renders zero usage as authoritative |
| Web customer cabinet | Traffic and connection cards show unavailable when backend usage is unavailable |
| Dashboard usage card | VPN usage card marks unavailable instead of rendering zero/unlimited |
| OpenAPI/client types | Backend OpenAPI and frontend generated types were regenerated |
| Tests | Backend unit/integration and frontend UI/API tests cover available and unavailable usage states |

## Files Added Or Updated

```text
backend/src/presentation/api/v1/usage/routes.py
backend/src/presentation/api/v1/usage/schemas.py
backend/src/presentation/api/v1/miniapp/routes.py
backend/src/presentation/api/v1/miniapp/schemas.py
backend/tests/unit/api/v1/test_usage.py
backend/tests/integration/api/v1/usage/test_usage_flows.py
backend/tests/unit/presentation/api/v1/miniapp/test_routes.py
backend/docs/api/openapi.json
frontend/src/lib/api/generated/types.ts
frontend/src/lib/api/miniapp.ts
frontend/src/lib/api/__tests__/vpn.test.ts
frontend/src/widgets/customer-cabinet/customer-cabinet-model.ts
frontend/src/widgets/customer-cabinet/customer-cabinet-dashboard.tsx
frontend/src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts
frontend/src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx
frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardStats.tsx
frontend/src/app/[locale]/(dashboard)/dashboard/components/__tests__/DashboardStats.test.tsx
frontend/src/app/[locale]/miniapp/home/page.tsx
frontend/src/app/[locale]/miniapp/home/__tests__/page.test.tsx
frontend/src/app/[locale]/miniapp/home/components/__tests__/HomeClient.test.tsx
docs/cybervpn_stage1_launch_docs/85_STAGE1_VPN_009_USAGE_DISPLAY_EVIDENCE.md
```

## API Contract

`UsageResponse` now includes:

| Field | Meaning |
|---|---|
| `usage_available` | `true` only when aggregate usage was fetched from authoritative Remnawave data |
| `usage_source` | `remnawave` or `unavailable` |
| `usage_unavailable_reason` | `upstream_user_not_found`, `upstream_unavailable`, or `null` |
| `generated_at` | Timestamp when the snapshot was generated |

Existing numeric fields remain present for compatibility, but UI must treat them as displayable only when `usage_available=true`.

Mini App bootstrap mirrors the same contract in camelCase:

```text
usageAvailable
usageSource
usageUnavailableReason
```

## Privacy Boundary

This task only exposes aggregate operational usage fields already present in the Remnawave user model:

- total bandwidth used;
- bandwidth limit;
- active connection count;
- connection limit;
- period start/end;
- last connection timestamp.

It does not add browsing content, visited websites, destination telemetry, raw VPN traffic content, packet metadata, DNS query logs or per-site logs to the CyberVPN app/backend UI.

## Local Test Evidence

Backend unit command:

```bash
cd backend && uv run pytest tests/unit/api/v1/test_usage.py tests/unit/presentation/api/v1/miniapp/test_routes.py -q --no-cov
```

Observed result:

```text
20 passed
```

Backend integration command:

```bash
cd infra && docker compose up -d remnawave-db remnawave-redis
cd backend && uv run pytest tests/integration/api/v1/usage/test_usage_flows.py -q --no-cov
```

Observed result:

```text
3 passed
```

The local `remnawave-db` and `remnawave-redis` containers were stopped after the integration test run.

Frontend lint command:

```bash
cd frontend && npm run lint -- src/widgets/customer-cabinet/customer-cabinet-model.ts src/widgets/customer-cabinet/customer-cabinet-dashboard.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx 'src/app/[locale]/(dashboard)/dashboard/components/DashboardStats.tsx' 'src/app/[locale]/(dashboard)/dashboard/components/__tests__/DashboardStats.test.tsx' src/app/[locale]/miniapp/home/page.tsx src/app/[locale]/miniapp/home/__tests__/page.test.tsx src/app/[locale]/miniapp/home/components/__tests__/HomeClient.test.tsx src/lib/api/miniapp.ts src/lib/api/__tests__/vpn.test.ts
```

Observed result:

```text
eslint passed
```

Frontend test command:

```bash
cd frontend && npm run test:run -- src/lib/api/__tests__/vpn.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx 'src/app/[locale]/(dashboard)/dashboard/components/__tests__/DashboardStats.test.tsx' src/app/[locale]/miniapp/home/__tests__/page.test.tsx src/app/[locale]/miniapp/home/components/__tests__/HomeClient.test.tsx
```

Observed result:

```text
6 passed
41 passed
```

OpenAPI/client generation:

```bash
cd backend && uv run python scripts/export_openapi.py
cd frontend && npm run generate:api-types
```

Observed result:

```text
backend/docs/api/openapi.json regenerated
frontend/src/lib/api/generated/types.ts regenerated
```

## Security Evidence

Dependency checks:

```bash
cd backend && uvx pip-audit --progress-spinner off
cd frontend && npm audit --omit=dev --audit-level=high
```

Observed result:

```text
pip-audit: No known vulnerabilities found
npm audit: no high/critical findings; existing moderate PostCSS advisory remains through Next.js dependency path
```

Source scans on changed runtime files:

```bash
rg -n "(api[_-]?key|secret|token|password|BEGIN RSA|PRIVATE KEY|sk-[A-Za-z0-9]|xox[baprs]-|ghp_|github_pat_)" <changed-runtime-files>
rg -n "\b(eval|Function\(|dangerouslySetInnerHTML|innerHTML|document\.write|subprocess\.|os\.system|shell=True|raw\(|text\()" <changed-runtime-files>
git diff --check -- <changed-files>
```

Observed result:

```text
No runtime source secret markers found
No dangerous runtime patterns found
git diff --check passed
```

Test files contain expected synthetic test password/token strings only.

## What This Closes

| Item | Status |
|---|---|
| `S1-VPN-009` API contract | Closed locally |
| `S1-VPN-009` web usage display fallback | Closed locally |
| `S1-VPN-009` Mini App usage display fallback | Closed locally |
| `S1-VPN-009` generated client contract | Closed locally |
| `S1-VPN-009` local API/UI tests | Passed |

## What Remains Open

| Item | Why still open |
|---|---|
| Staging Remnawave usage evidence | Requires real staging Remnawave instance and real/test upstream user |
| Production Remnawave usage evidence | Requires production Remnawave instance and approved go-live environment |
| Deployed UI screenshots | Requires deployed staging/RC frontend and Telegram Mini App context |
| Real usage correctness sample | Requires comparing CyberVPN UI/API snapshot against Remnawave authoritative user record |
| Alerting for usage sync outage | Should be covered under observability/production readiness gates |

## Acceptance Result

`S1-VPN-009` is **completed locally** for implementation readiness.

It does not replace staging/prod Remnawave evidence. Before S1 go-live, a real staging/production evidence pack must prove that:

1. available Remnawave usage appears accurately in web and Mini App surfaces;
2. missing/unreachable Remnawave usage is marked unavailable;
3. support/admin can distinguish unavailable usage from zero usage;
4. no raw VPN traffic/content logs are exposed in customer or support UI.

Next task after this evidence was `S1-VPN-010`, which is now closed locally in `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`.
