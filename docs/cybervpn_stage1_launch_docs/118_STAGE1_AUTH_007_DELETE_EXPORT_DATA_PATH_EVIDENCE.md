# 118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE

Backlog ID: `S1-AUTH-007`  
Status: completed locally; revalidated on 2026-05-09  
Date: 2026-05-08  
Revalidation date: 2026-05-09  
Scope: Stage 1 account deletion and data export request path for Controlled Public Beta

## Decision

For S1 Controlled Public Beta, account deletion and data export are handled through a conservative privacy-rights path:

- existing authenticated `DELETE /api/v1/auth/me` remains the direct soft-delete path;
- new authenticated `POST /api/v1/auth/me/privacy-requests` accepts `account_deletion` or `data_export` requests for manual privacy review;
- `data_export` is not generated automatically in S1;
- both privacy request types route to `s1_privacy_rights_review` and `privacy@cyber-vpn.net`;
- owner/support review, identity verification and audit are mandatory before fulfillment;
- password hashes, TOTP secrets, raw tokens, raw provider payloads, QR codes, subscription URLs and config files must not be exported or requested from users.

## Covered Behavior

| Area | Local proof |
|---|---|
| Account deletion path | Existing `DELETE /api/v1/auth/me` remains available for authenticated soft-delete |
| Manual privacy request path | `POST /api/v1/auth/me/privacy-requests` accepts `account_deletion` and `data_export` |
| Safe routing | Requests are classified as P1 and routed to `s1_privacy_rights_review` |
| Privacy contact | `privacy@cyber-vpn.net` is the target contact for delete/export requests |
| Escalation | Privacy requests route AI/support -> owner with audit required |
| Redaction | User-provided notes are sanitized before staff/API output; config URLs, URLs, emails, Telegram tokens and long secrets are redacted |
| Data export guardrails | Export is limited to portable account data and excludes internal security/provider fields |
| Deletion guardrails | Deletion requires identity verification and preserves required billing/security/legal records |
| Frontend API | `authApi.requestPrivacyAction()` and `authApi.requestDataExport()` call the S1 privacy request endpoint |
| MSW/tests | Frontend mocks return a 202 privacy review reference for local UI/API tests |

## Local Implementation

Changed files:

- `backend/src/presentation/api/shared/stage1_privacy_request_path.py`
- `backend/src/presentation/api/shared/stage1_support_ticket_path.py`
- `backend/src/presentation/api/shared/stage1_support_escalation.py`
- `backend/src/presentation/api/shared/stage1_support_templates.py`
- `backend/src/presentation/api/shared/__init__.py`
- `backend/src/presentation/api/v1/auth/schemas.py`
- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/docs/api/openapi.json`
- `backend/tests/security/test_stage1_privacy_request_path.py`
- `backend/tests/security/test_stage1_support_ticket_path.py`
- `backend/tests/security/test_stage1_support_escalation.py`
- `frontend/src/lib/api/auth.ts`
- `frontend/src/lib/api/generated/types.ts`
- `frontend/src/lib/api/__tests__/auth.test.ts`
- `frontend/src/test/mocks/handlers.ts`
- `frontend/src/test/infrastructure.test.tsx`
- `package-lock.json` - lockfile-only forward refresh from `npm audit fix --package-lock-only`; no package downgrade and no `package.json` version reduction

Implementation notes:

1. `Stage1SupportTicketCategory` now includes `account_deletion` and `data_export`.
2. `STAGE1_PRIVACY_EMAIL` is set to `privacy@cyber-vpn.net`.
3. Support tickets for delete/export become P1 privacy review tickets with 60-minute ack SLA and 12-hour customer response SLA.
4. Escalation rules add `account_deletion_request` and `data_export_request` triggers with owner review and audit required.
5. Support templates add `SUP-S1-006` and `SUP-S1-007` for account deletion and data export.
6. `build_stage1_privacy_request()` returns safe API/runbook metadata without raw user text.
7. `POST /api/v1/auth/me/privacy-requests` returns HTTP 202 and a safe ticket reference.
8. Frontend auth API has a typed S1 privacy request client path; local MSW supports it.

## Verification

Commands:

```bash
cd backend
PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_support_ticket_path.py src/presentation/api/shared/stage1_support_escalation.py src/presentation/api/shared/stage1_support_templates.py src/presentation/api/shared/stage1_privacy_request_path.py src/presentation/api/shared/__init__.py src/presentation/api/v1/auth/schemas.py src/presentation/api/v1/auth/routes.py tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_privacy_request_path.py
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_privacy_request_path.py -q --no-cov
PYENV_VERSION=3.13.11 uv run python - <<'PY'
from src.main import app
paths = set(app.openapi().get("paths", {}))
print("/api/v1/auth/me/privacy-requests" in paths)
PY
PYENV_VERSION=3.13.11 uv run pytest tests/contract/test_phase1_api_surface_contract.py tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_privacy_request_path.py -q --no-cov
PYENV_VERSION=3.13.11 pip-audit --skip-editable backend
PYENV_VERSION=3.13.11 uv run python scripts/export_openapi.py

cd ..
npm --prefix frontend run test:run -- src/lib/api/__tests__/auth.test.ts src/test/infrastructure.test.tsx
npm --prefix frontend run lint -- src/lib/api/auth.ts src/lib/api/__tests__/auth.test.ts src/test/mocks/handlers.ts src/test/infrastructure.test.tsx
npm --prefix frontend run generate:api-types
npm --prefix frontend run lint -- src/lib/api/auth.ts src/lib/api/generated/types.ts src/lib/api/__tests__/auth.test.ts src/test/mocks/handlers.ts src/test/infrastructure.test.tsx
npm audit --omit=dev --audit-level=high
npm --prefix frontend audit fix --package-lock-only
npm --prefix frontend audit --omit=dev --audit-level=high
npm --prefix frontend audit --audit-level=high

# Secret and dangerous-pattern scans were run against the explicit S1-AUTH-007
# touched-file list from this evidence document.
rg -n -e '(JWT_SECRET|SECRET_KEY|DATABASE_URL|REDIS_URL|SMTP_PASSWORD|OAUTH_CLIENT_SECRET|TOTP_ENCRYPTION_KEY|CRYPTOBOT_TOKEN)[[:space:]]*=[[:space:]]*["'\''][^"'\'']+["'\'']' -e 'Bearer[[:space:]]+[A-Za-z0-9._-]{20,}' -e 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}' backend/src/presentation/api/shared/stage1_privacy_request_path.py backend/src/presentation/api/v1/auth/schemas.py backend/src/presentation/api/v1/auth/routes.py backend/tests/security/test_stage1_privacy_request_path.py frontend/src/lib/api/auth.ts frontend/src/lib/api/generated/types.ts frontend/src/lib/api/__tests__/auth.test.ts frontend/src/test/mocks/handlers.ts frontend/src/test/infrastructure.test.tsx docs/cybervpn_stage1_launch_docs/118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md -S
rg -n -e '\beval\s*\(' -e '\bexec\s*\(' -e 'subprocess\.' -e 'shell=True' -e 'dangerouslySetInnerHTML' -e 'innerHTML' backend/src/presentation/api/shared/stage1_privacy_request_path.py backend/src/presentation/api/v1/auth/schemas.py backend/src/presentation/api/v1/auth/routes.py backend/tests/security/test_stage1_privacy_request_path.py frontend/src/lib/api/auth.ts frontend/src/lib/api/generated/types.ts frontend/src/lib/api/__tests__/auth.test.ts frontend/src/test/mocks/handlers.ts frontend/src/test/infrastructure.test.tsx -S
```

Results:

| Check | Result |
|---|---|
| Ruff touched backend files | PASS |
| Backend support/privacy security tests | PASS: 25 passed in 0.25s |
| FastAPI app import/OpenAPI path check | PASS: `/api/v1/auth/me/privacy-requests` present |
| Backend contract + privacy/support regression tests | PASS: 28 passed in 2.15s |
| Backend runtime dependency audit | PASS: no known vulnerabilities found |
| Frontend auth API/MSW tests | PASS: 102 passed |
| Frontend eslint on touched API/test files | PASS |
| OpenAPI export | PASS: `backend/docs/api/openapi.json` includes `/api/v1/auth/me/privacy-requests` |
| Frontend generated API types | PASS: `frontend/src/lib/api/generated/types.ts` includes `PrivacyRequestCreate` and `PrivacyRequestResponse` |
| Frontend eslint after API type generation | PASS with generated file ignored by configured eslint ignore pattern |
| Root npm production dependency audit | PASS for high/critical threshold; only moderate Next/PostCSS advisory reported |
| Frontend npm lockfile remediation | PASS with caveat: `npm --prefix frontend audit fix --package-lock-only` made forward-only lockfile updates and removed the high `fast-uri` finding; command still reports unresolved moderate Next/PostCSS because npm recommends a breaking `next@9.3.3` downgrade for that advisory |
| Frontend production dependency audit | PASS for `--omit=dev --audit-level=high`; only moderate Next/PostCSS advisory reported |
| Frontend full dev/tooling dependency audit | PASS for high/critical threshold after lockfile refresh; only moderate Next/PostCSS advisory reported |
| `git diff --check` on touched S1-AUTH-007 files/docs | PASS |
| High-confidence secret scan over touched S1-AUTH-007 files/docs | PASS: no matches |
| Dangerous-pattern scan over touched runtime/test/docs files except historical combined pack | PASS: no runtime matches |

## Residual Risk

The S1-AUTH-007 code and route/support contract are accepted locally. The 2026-05-09 revalidation removed the previous high frontend audit finding through a lockfile-only forward refresh:

- `npm --prefix frontend audit --omit=dev --audit-level=high` passes.
- `npm --prefix frontend audit --audit-level=high` passes for high/critical threshold.
- The remaining npm advisory is moderate Next/PostCSS, where `npm audit fix --force` proposes a breaking downgrade to `next@9.3.3`; this is intentionally not applied because the project must stay on the current Next.js 16 line and version downgrades are prohibited.
- Re-run the full dependency audit on the first `stage1-beta-rc.N` tag and after any Next.js lockfile refresh.

## Documentation References Used

Context7 MCP is not available in this local tool session, so official documentation was used as the required fallback.

| Reference | Use |
|---|---|
| <https://fastapi.tiangolo.com/tutorial/path-operation-configuration/> | Confirmed FastAPI path operations can declare explicit response status codes such as HTTP 202 |
| <https://docs.pydantic.dev/latest/concepts/fields/> | Confirmed Pydantic `Field` is the documented path for request-field constraints and descriptions |

## Remaining Go-Live Evidence

Local `S1-AUTH-007` is complete. Before beta go-live, still capture target-environment evidence:

1. `privacy@cyber-vpn.net` mailbox receives and can send privacy support messages.
2. Deployed frontend/user flow exposes or documents how to request data export before account deletion.
3. Deployed admin/support queue shows privacy requests without raw secrets or config payloads.
4. Human support SLA acknowledgement is captured for a test delete/export request.
5. Owner/support can verify identity and record fulfillment/denial without exposing passwords, TOTP codes, raw QR codes, subscription URLs or config files.
6. Any automated export implementation after S1 must pass a separate privacy/security review before it is exposed.

## Acceptance

`S1-AUTH-007` is accepted locally because users now have an authenticated S1 privacy request path for account deletion and data export, the existing authenticated soft-delete endpoint remains present, and the delete/export support workflow is covered by route, support-ticket, escalation, template, frontend API and regression tests.

Next ID superseded by `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Ordered Batch Revalidation

`S1-AUTH-007` was re-run as item 13 in the owner-requested ordered batch.

Backend verification:

```text
cd backend
PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_support_ticket_path.py src/presentation/api/shared/stage1_support_escalation.py src/presentation/api/shared/stage1_support_templates.py src/presentation/api/shared/stage1_privacy_request_path.py src/presentation/api/shared/__init__.py src/presentation/api/v1/auth/schemas.py src/presentation/api/v1/auth/routes.py tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_privacy_request_path.py
Result: All checks passed

PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_privacy_request_path.py -q --no-cov
Result: 25 passed in 0.26s

OpenAPI app-path check:
Result: /api/v1/auth/me/privacy-requests present = True

PYENV_VERSION=3.13.11 uv run pytest tests/contract/test_phase1_api_surface_contract.py tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_escalation.py tests/security/test_stage1_privacy_request_path.py -q --no-cov
Result: 28 passed in 2.15s

PYENV_VERSION=3.13.11 uv run python scripts/export_openapi.py
Result: OpenAPI spec written to backend/docs/api/openapi.json
```

Frontend/API verification:

```text
npm --prefix frontend run test:run -- src/lib/api/__tests__/auth.test.ts src/test/infrastructure.test.tsx
Result: 2 files passed, 102 tests passed

npm --prefix frontend run lint -- src/lib/api/auth.ts src/lib/api/__tests__/auth.test.ts src/test/mocks/handlers.ts src/test/infrastructure.test.tsx
Result: PASS

npm --prefix frontend run generate:api-types
Result: backend/docs/api/openapi.json -> frontend/src/lib/api/generated/types.ts

npm --prefix frontend run lint -- src/lib/api/auth.ts src/lib/api/generated/types.ts src/lib/api/__tests__/auth.test.ts src/test/mocks/handlers.ts src/test/infrastructure.test.tsx
Result: PASS with one expected warning that generated types are ignored by lint config
```

Local acceptance remains unchanged. Deployed `privacy@` mailbox, support queue, identity verification and human SLA evidence remain required before go-live.
