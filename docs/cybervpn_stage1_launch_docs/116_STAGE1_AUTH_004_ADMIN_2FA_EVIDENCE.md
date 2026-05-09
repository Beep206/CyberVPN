# 116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE

Backlog ID: `S1-AUTH-004`  
Status: completed locally; revalidated on 2026-05-09  
Date: 2026-05-08  
Scope: Stage 1 admin 2FA enforcement from the auth backlog perspective

## Decision

For S1 Controlled Public Beta, protected admin access is accepted locally only if admin role/permission surfaces fail closed when `ADMIN_2FA_REQUIRED=true` and the actor has not enabled TOTP.

The 2FA setup/login-completion path must remain usable so a legitimate admin can enroll or complete a pending 2FA login. The enforcement boundary is therefore:

```text
generic active-user dependency -> allows enrollment/status-style 2FA routes
admin role/permission dependency -> requires TOTP before privileged admin access
```

Revalidated on 2026-05-09 as the active execution step after `S1-AUTH-003`. The local contract remains valid: privileged admin role/permission surfaces fail closed without TOTP, valid TOTP-enabled admins pass, setup/completion paths remain usable and sensitive finance/support gates share the same 2FA posture. This local proof does not imply deployed admin browser/API persona evidence or target-environment first-admin/TOTP evidence.

## Covered Behavior

| Area | Local proof |
|---|---|
| Production config | Production settings reject `ADMIN_2FA_REQUIRED=false` |
| Admin permission gate | `require_permission()` returns `403 Admin 2FA required` when TOTP is disabled |
| Admin role gate | `require_role()` shares the same 2FA fail-closed helper |
| Valid admin with TOTP | Protected admin permission path succeeds when `totp_enabled=true` |
| Invalid admin role | Invalid role still fails closed before permission grant |
| Enrollment boundary | Setup/status-style routes using only active-user auth remain reachable without TOTP |
| 2FA completion route | Pending 2FA login completion issues tokens/cookies and rejects invalid code |
| Finance/support sensitive gates | Refund/dispute reviewer and payment-attempt admin view gates enforce admin 2FA where configured |
| Existing 2FA lifecycle | Setup, verification, rate limiting, disable and status tests still pass |

## Local Implementation

No production runtime code change was required for `S1-AUTH-004`. The runtime admin 2FA gate was already implemented and locally evidenced by:

- `backend/src/presentation/dependencies/roles.py`
- `docs/cybervpn_stage1_launch_docs/64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`

During the S1-AUTH-004 regression pass, one stale unit test was updated so direct calls to `/2fa/complete` pass the current admin `RealmResolution` dependency explicitly:

- `backend/tests/unit/api/v1/test_2fa_complete.py`

This is a test-harness correction only. It does not loosen the runtime 2FA route.

During the 2026-05-09 revalidation, the production settings test fixture was updated so successful production-config cases use a non-placeholder provider token:

- `backend/tests/unit/config/test_settings.py`

This keeps the admin 2FA settings regression aligned with the current CryptoBot production credential guardrail from the payment workstream. It does not add or expose a real provider token.

## Verification

Commands:

```bash
cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/unit/config/test_settings.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_rbac_matrix.py tests/security/test_stage1_admin_access_protection.py -q --no-cov
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_2fa_security.py tests/unit/api/v1/test_2fa_complete.py tests/integration/api/v1/two_factor/test_2fa_cycle.py -q --no-cov
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_refund_dispute_process.py tests/security/test_stage1_admin_payment_attempts_view.py -q --no-cov
PYENV_VERSION=3.13.11 uv run ruff check src/presentation/dependencies/roles.py src/presentation/api/shared/stage1_refund_dispute_process.py src/presentation/api/v1/admin/payment_attempts.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_payment_attempts_view.py tests/security/test_stage1_refund_dispute_process.py tests/unit/api/v1/test_2fa_complete.py tests/unit/config/test_settings.py

PYENV_VERSION=3.13.11 pip-audit --skip-editable backend
npm audit --omit=dev --audit-level=high
```

Results:

| Check | Result |
|---|---|
| Production setting + admin 2FA/RBAC/access protection | PASS: 48 passed in 4.71s after stale production provider-token fixture remediation |
| Generic 2FA security + 2FA complete + lifecycle regression | PASS: 22 passed in 1.72s |
| Sensitive finance/support admin gates | PASS: 15 passed in 0.34s |
| Ruff touched admin/2FA/settings files | PASS: all checks passed |
| Backend runtime dependency audit | PASS: no known vulnerabilities found |
| Root npm production dependency audit at high threshold | PASS for high/critical: exit 0; residual moderate `postcss <8.5.10` via `next`, fix currently suggests breaking `npm audit fix --force` |
| High-confidence secret scan over touched S1-AUTH-004 files | PASS: no matches |
| Dangerous-pattern scan over touched S1-AUTH-004 files | PASS: no matches |
| Docker/container usage | Existing local `remnawave-db` and `remnawave-redis` containers were reused, then stopped after this task to release resources; no new containers were started |

## Documentation / Library References Used

Context7 MCP is not available in this local tool session, so official documentation was used as the required fallback.

| Reference | Use |
|---|---|
| <https://fastapi.tiangolo.com/tutorial/dependencies/> | Confirmed FastAPI dependency injection is the correct place for shared role/permission auth checks |
| <https://fastapi.tiangolo.com/tutorial/security/first-steps/> | Confirmed auth/security dependencies belong in protected endpoint paths |
| <https://pyauth.github.io/pyotp/> | Confirmed PyOTP TOTP lifecycle concepts used by the existing 2FA implementation |
| <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | Confirmed isolated `monkeypatch` usage for runtime setting gates in tests |

## Remaining Go-Live Evidence

Local S1-AUTH-004 is complete. Before beta go-live, still capture deployed evidence:

1. Staging/prod admin login proof with the first admin and TOTP enabled.
2. Deployed proof that an admin without TOTP cannot access protected admin API/UI surfaces.
3. Deployed proof that 2FA setup/completion remains available to a legitimate pending admin session.
4. Browser/API transcripts for owner/support/operator/finance personas.
5. First-admin bootstrap target-environment evidence proving TOTP was enabled before admin access.
6. Audit-log proof for privileged actions remains covered by admin/audit tasks and target-environment evidence.

## Acceptance

`S1-AUTH-004` is accepted locally because protected admin role/permission surfaces fail closed without TOTP, valid TOTP-enabled admins pass, 2FA lifecycle tests pass, and sensitive finance/support admin gates share the required 2FA posture.

Next ID to execute after this task was `S1-AUTH-006` - verify S1 OAuth providers. `S1-AUTH-005` is already completed locally through `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`.

## 2026-05-09 Ordered Batch Revalidation

`S1-AUTH-004` was re-run as item 11 in the owner-requested ordered batch:

11. `S1-AUTH-004`
12. `S1-AUTH-006`
13. `S1-AUTH-007`
14. `S1-VPN-001`
15. `S1-VPN-003`

Verification:

```text
cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/unit/config/test_settings.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_rbac_matrix.py tests/security/test_stage1_admin_access_protection.py -q --no-cov
Result: 48 passed in 4.40s

PYENV_VERSION=3.13.11 uv run pytest tests/security/test_2fa_security.py tests/unit/api/v1/test_2fa_complete.py tests/integration/api/v1/two_factor/test_2fa_cycle.py -q --no-cov
Initial result: 10 passed, 12 skipped because local Docker-backed DB was not yet running

docker compose -f infra/docker-compose.yml up -d remnawave-db remnawave-redis
PYENV_VERSION=3.13.11 uv run pytest tests/integration/api/v1/two_factor/test_2fa_cycle.py -q --no-cov
Result after DB/Redis startup: 12 passed in 1.62s

PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_refund_dispute_process.py tests/security/test_stage1_admin_payment_attempts_view.py -q --no-cov
Result: 15 passed in 0.30s

PYENV_VERSION=3.13.11 uv run ruff check src/presentation/dependencies/roles.py src/presentation/api/shared/stage1_refund_dispute_process.py src/presentation/api/v1/admin/payment_attempts.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_admin_payment_attempts_view.py tests/security/test_stage1_refund_dispute_process.py tests/unit/api/v1/test_2fa_complete.py tests/unit/config/test_settings.py
Result: All checks passed
```

The ordered-batch result uses the post-startup integration run as the accepted feature proof. The earlier skipped run is retained as context only and is not treated as acceptance evidence.
