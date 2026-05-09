> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-04
> Backlog ID: `S1-BE-004`
> Статус: local production-mode Swagger/OpenAPI public-off proof completed; deployed staging/prod curl evidence remains required before go-live.

# S1-BE-004 Swagger Public-Off Evidence

## Purpose

Этот документ фиксирует `S1-BE-004`: публичные Swagger/OpenAPI endpoints не должны быть доступны в production mode.

Проверяемые public docs paths:

- `/docs`
- `/docs/`
- `/openapi.json`
- `/redoc`
- `/redoc/`

## Implementation

До задачи backend выключал docs через `SWAGGER_ENABLED=false`, но production мог случайно поднять Swagger/OpenAPI, если `SWAGGER_ENABLED=true` был задан в environment.

Изменение:

- добавлен production guard `_swagger_enabled_for_environment()`;
- в `ENVIRONMENT=production` public docs routes принудительно отключены независимо от `SWAGGER_ENABLED`;
- для non-production окружений `SWAGGER_ENABLED=true` остаётся разрешённым для локальной/staging разработки;
- metrics ASGI app остаётся без docs routes.

FastAPI reference used: official FastAPI `Metadata and Docs URLs` docs state that `openapi_url=None` disables the OpenAPI schema and documentation UIs that use it, and that `docs_url=None` / `redoc_url=None` disable Swagger UI / ReDoc.

Source: https://fastapi.tiangolo.com/tutorial/metadata/

## Evidence Summary

| Check | Result |
|---|---|
| Production guard matrix | Passed |
| Current app public docs paths | All return `404` |
| `/health` remains available | `200` |
| Fresh production import with `SWAGGER_ENABLED=true` | Docs still not mounted |
| Metrics app docs routes | Not mounted |
| Regression test | `9 passed` |

## Local HTTP Status Evidence

Command shape:

```bash
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python '<ASGI status probe>'
```

Observed result:

```json
{
  "app_docs_url": null,
  "app_openapi_url": null,
  "app_redoc_url": null,
  "statuses": {
    "/docs": 404,
    "/docs/": 404,
    "/health": 200,
    "/openapi.json": 404,
    "/redoc": 404,
    "/redoc/": 404
  },
  "swagger_enabled_for_environment": false
}
```

Note: local probe logged Redis rate-limiter errors because Redis was not running. This did not affect the docs-route result; `/health` stayed `200`.

## Production Misconfiguration Evidence

Command shape:

```bash
ENVIRONMENT=production \
SWAGGER_ENABLED=true \
REMNAWAVE_TOKEN='<redacted-production-shaped-value>' \
JWT_SECRET='<redacted-production-shaped-value>' \
CRYPTOBOT_TOKEN='<redacted-production-shaped-value>' \
TOTP_ENCRYPTION_KEY='<redacted-production-shaped-value>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-production-shaped-value>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python '<fresh import probe>'
```

Observed result:

```json
{
  "app_docs_url": null,
  "app_openapi_url": null,
  "app_redoc_url": null,
  "configured_SWAGGER_ENABLED": true,
  "environment": "production",
  "public_doc_paths_present": [],
  "swagger_enabled_for_environment": false
}
```

The app also logged:

```text
Swagger/OpenAPI forced off in production despite SWAGGER_ENABLED=true
Swagger/OpenAPI public routes disabled
```

## Regression Test

Added:

```text
backend/tests/security/test_stage1_swagger_public_off.py
```

The test asserts:

- production always disables public docs routes;
- `development` and `staging` may enable docs when `SWAGGER_ENABLED=true`;
- current app returns `404` for docs paths and `200` for `/health`;
- a fresh production import with `SWAGGER_ENABLED=true` still does not mount `/docs`, `/openapi.json` or `/redoc`;
- metrics app never mounts public docs routes.

Targeted result:

```text
9 passed in 3.87s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-004` local Swagger/OpenAPI public-off proof | Closed locally |
| Accidental production `SWAGGER_ENABLED=true` exposure | Mitigated in code and tests |
| Metrics app docs exposure | Closed locally |

## What Remains Open

| Item | Why still open |
|---|---|
| Staging/prod deployed curl evidence | No deployed staging/prod environment is available yet |
| Edge/ingress screenshots | Requires real domain/TLS/ingress |
| OpenAPI export workflow | Programmatic `app.openapi()` remains available for internal contract/export tests; only public HTTP routes are disabled |

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
python -m pytest backend/tests/security/test_stage1_swagger_public_off.py -q --no-cov
```
