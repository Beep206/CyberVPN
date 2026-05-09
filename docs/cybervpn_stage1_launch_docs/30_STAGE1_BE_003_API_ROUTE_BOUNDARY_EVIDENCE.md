> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Backlog ID: `S1-BE-003`
> Статус: local backend route-boundary audit completed; staging/prod ingress and live auth evidence remain required before go-live.

# S1-BE-003 API Route Boundary Evidence

## Purpose

Этот документ фиксирует `S1-BE-003`: фактический audit backend routes по коду, чтобы public/internal/admin/user surfaces были явно классифицированы перед дальнейшей реализацией S1.

Цель задачи: не доказать каждый бизнес-сценарий, а закрыть риск "в backend есть неизвестный публичный endpoint". Бизнес-authorization и live ingress evidence остаются отдельными задачами.

## Method

Маршруты были сняты из `src.main.app.routes` через FastAPI route introspection.

Проверялись:

- HTTP routes из `APIRoute`;
- WebSocket routes из `APIWebSocketRoute`;
- FastAPI dependencies: `require_role`, `require_permission`, `get_current_active_user`, mobile/current principal dependencies;
- internal header guards in endpoint source: `_require_telegram_bot_secret`, `_require_frontend_observability_secret`;
- webhook signature guards in endpoint source;
- partner reporting token dependency;
- explicit public allowlist for auth/catalog/status/public network/security.txt routes.

FastAPI reference used: official `APIRouter` docs describe router/path operation dependencies and OpenAPI inclusion behavior.

## Result Summary

| Category | Count | Meaning |
|---|---:|---|
| HTTP routes | 594 | FastAPI `APIRoute` endpoints |
| WebSocket routes | 2 | `APIWebSocketRoute`; both use `ws_authenticate` |
| `principal-protected` | 508 | Requires current user/mobile principal/admin role/permission |
| `public-allowlisted` | 49 | Login/register/OAuth/catalog/status/public network/security.txt |
| `header-secret-protected` | 34 | Internal bot/worker/frontend-observability routes with explicit shared-secret check |
| `webhook-signature-protected` | 2 | Remnawave/CryptoBot webhook receivers |
| `partner-reporting-token` | 1 | Partner reporting snapshot token dependency |
| `needs-review` | 0 | No HTTP route fell outside the approved boundary classifier |

## Boundary Categories

| Boundary | Examples | S1 rule |
|---|---|---|
| Public B2C/auth | `/api/v1/auth/*`, `/api/v1/mobile/auth/*`, `/api/v1/oauth/*` | Public by design, but rate limits and account-linking tests still required |
| Public catalog/legal | `/api/v1/plans/`, `/api/v1/offers/`, `/api/v1/legal-documents/sets/resolve`, `/api/v1/pricebooks/resolve` | Public by design, final legal/public copy still required |
| Public status/network | `/health`, `/readiness`, `/api/v1/status`, `/api/v1/public/network/*` | Public/edge by design, but `/readiness` should be edge/internal or reduced before go-live |
| Admin/user protected | `/api/v1/admin/*`, `/api/v1/users/*`, `/api/v1/wallet/*`, `/api/v1/subscriptions/*` | Protected by principal/role/permission dependencies |
| Internal shared-secret | `/api/v1/admin/growth-reporting/internal/*`, `/api/v1/partner-bots/internal/*`, `/api/v1/telegram/bot/*`, `/api/v1/monitoring/frontend-*` | Requires shared secret now; should also be edge/IP/network restricted where possible |
| Webhooks | `/api/v1/webhooks/remnawave`, `/api/v1/webhooks/cryptobot` | Signature validation required; provider-specific evidence remains open |
| WebSocket | `/api/v1/ws/monitoring`, `/api/v1/ws/notifications` | `ws_authenticate` required; monitoring topics have role-based authorization |

## Route Family Matrix

This is a family-level matrix. Full generated route inventory lives in local ignored artifact `.tmp/stage1-be-003-routes-clean.json` and can be regenerated before RC.

| Family | Total | Principal-protected | Internal-token/signature | Public/no-principal | Needs review |
|---|---:|---:|---:|---:|---:|
| `/.well-known/security.txt` | 1 | 0 | 0 | 1 | 0 |
| `/api/v1/2fa` | 8 | 8 | 0 | 0 | 0 |
| `/api/v1/access-delivery-channels` | 6 | 6 | 0 | 0 | 0 |
| `/api/v1/addons` | 4 | 3 | 0 | 1 | 0 |
| `/api/v1/admin` | 91 | 86 | 5 | 0 | 0 |
| `/api/v1/auth` | 27 | 11 | 0 | 16 | 0 |
| `/api/v1/mobile` | 13 | 7 | 0 | 6 | 0 |
| `/api/v1/monitoring` | 14 | 10 | 4 | 0 | 0 |
| `/api/v1/oauth` | 15 | 10 | 0 | 5 | 0 |
| `/api/v1/partner-bots` | 9 | 7 | 2 | 0 | 0 |
| `/api/v1/public/network` | 9 | 0 | 1 | 8 | 0 |
| `/api/v1/reporting` | 8 | 7 | 1 | 0 | 0 |
| `/api/v1/status` | 1 | 0 | 0 | 1 | 0 |
| `/api/v1/telegram` | 25 | 3 | 22 | 0 | 0 |
| `/api/v1/webhooks` | 2 | 0 | 2 | 0 | 0 |
| `/health` | 1 | 0 | 0 | 1 | 0 |
| `/health/detailed` | 1 | 1 | 0 | 0 | 0 |
| `/readiness` | 1 | 0 | 0 | 1 | 0 |
| `/security.txt` | 1 | 0 | 0 | 1 | 0 |
| All other API families | 357 | 349 | 0 | 8 | 0 |

The "All other API families" public count covers public catalog/resolve endpoints: billing descriptor resolve, legal document set resolve, merchant profile resolve, offers, plans, pricebook resolve, program eligibility and realm resolve.

## Regression Test

Added route-boundary regression test:

```text
backend/tests/security/test_stage1_route_boundary.py
```

The test asserts:

- every HTTP route is classified;
- no `/internal/` route is public-allowlisted;
- expected boundary categories exist;
- every WebSocket route depends on `ws_authenticate`.

Targeted result:

```text
4 passed in 0.23s
```

## Findings

| Finding | Severity | Decision |
|---|---|---|
| No unclassified HTTP route found | Good | `S1-BE-003` local route audit passes |
| Internal routes rely on shared headers | Medium | Accept for local implementation; before go-live add secret-store evidence and edge/IP/network restriction where feasible |
| `/readiness` is unauthenticated and reveals dependency status | Medium | Keep for local orchestration; before go-live expose only through private/edge path or reduce returned detail |
| `security.txt` uses `cybervpn.example` placeholder values | Medium | Replace before public go-live as part of legal/support public contact cleanup |
| Webhook routes are signature-classified, not provider-evidenced | High for paid beta | Provider webhook signature/idempotency evidence remains under `S1-PAY-*` |
| Swagger/OpenAPI currently disabled by default via `SWAGGER_ENABLED=false` | Good baseline | `S1-BE-004` local production-mode proof completed in `31_STAGE1_BE_004_SWAGGER_PUBLIC_OFF_EVIDENCE.md`; deployed evidence still required before go-live |

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-003` route boundary audit | Closed locally |
| Unknown backend route surface risk | Closed for current snapshot |
| Future silent route drift | Mitigated by `test_stage1_route_boundary.py` |

## What Remains Open

| Item | Why still open |
|---|---|
| Production/staging ingress evidence | This audit is local code introspection, not deployed ingress proof |
| Swagger public-off proof | Completed locally in `31_STAGE1_BE_004_SWAGGER_PUBLIC_OFF_EVIDENCE.md`; deployed staging/prod curl evidence still required |
| CORS/cookie domain proof | Completed locally in `32_STAGE1_BE_005_CORS_COOKIE_CONFIG_EVIDENCE.md`; deployed DNS/TLS/redirect/CORS/Set-Cookie evidence still required |
| CSRF assessment | Local proof completed in `33_STAGE1_BE_006_CSRF_ASSESSMENT_EVIDENCE.md`; deployed HTTPS/browser evidence remains open |
| Rate-limit proof | Local proof completed in `34_STAGE1_BE_007_RATE_LIMIT_POLICY_EVIDENCE.md`; deployed Redis/ingress/edge evidence remains open |
| Payment webhook idempotency | Covered by `S1-PAY-006` |
| Public legal/security contacts | Covered by legal/support tech debt before go-live |

## Regeneration Command

```bash
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/security/test_stage1_route_boundary.py -q --no-cov
```

## 2026-05-09 Batch Revalidation

This task was re-run as item 1 in the owner-requested batch:

1. `S1-BE-003`
2. `S1-REL-002`
3. `S1-INFRA-002`
4. `S1-INFRA-004`
5. `S1-BE-001`

Current route inventory:

| Category | Count |
|---|---:|
| HTTP routes | 603 |
| WebSocket routes | 2 |
| `principal-protected` | 515 |
| `public-allowlisted` | 49 |
| `header-secret-protected` | 36 |
| `webhook-signature-protected` | 2 |
| `partner-reporting-token` | 1 |
| `needs-review` | 0 |

Current family deltas worth noting:

| Family | Current total | Boundary note |
|---|---:|---|
| `/api/v1/admin` | 96 | 91 principal-protected, 5 header-secret-protected |
| `/api/v1/auth` | 29 | 16 public-allowlisted, 13 principal-protected |
| `/api/v1/telegram` | 26 | 23 header-secret-protected, 3 principal-protected |
| `/api/v1/payments` | 11 | 10 principal-protected, 1 header-secret-protected |
| `/api/v1/webhooks` | 2 | 2 webhook-signature-protected |
| `/readiness` | 1 | Public-allowlisted locally; still needs deployed edge/private handling before go-live |

Verification:

```text
cd backend
uv run pytest tests/security/test_stage1_route_boundary.py -q --no-cov
Result: 4 passed in 0.24s

uv run ruff check tests/security/test_stage1_route_boundary.py
Result: All checks passed
```

Feature evidence status remains partial by design: this is local FastAPI route introspection. The same route boundary must be proven again on real staging ingress after `S1-INFRA-002` and `S1-INFRA-004` have live infrastructure.

## 2026-05-09 Ordered Batch Revalidation

`S1-BE-003` was re-run again as item 7 in the owner-requested ordered batch after `S1-BE-002`.

Current route inventory:

| Category | Count |
|---|---:|
| HTTP routes | 603 |
| WebSocket routes | 2 |
| `principal-protected` | 515 |
| `public-allowlisted` | 49 |
| `header-secret-protected` | 36 |
| `webhook-signature-protected` | 2 |
| `partner-reporting-token` | 1 |
| `needs-review` | 0 |

Verification:

```text
cd backend
uv run pytest tests/security/test_stage1_route_boundary.py -q --no-cov
Result: 4 passed in 0.24s

uv run ruff check tests/security/test_stage1_route_boundary.py
Result: All checks passed
```

The local route boundary remains accepted. Deployed ingress behavior, admin host protection, Swagger public-off proof, CORS/cookie/CSRF/rate-limit evidence and webhook callback exposure still require staging/prod proof.
