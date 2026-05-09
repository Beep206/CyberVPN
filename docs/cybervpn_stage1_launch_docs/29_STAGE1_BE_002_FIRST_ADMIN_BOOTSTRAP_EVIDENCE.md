> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Backlog ID: `S1-BE-002`
> Статус: local first-admin bootstrap evidence passed; staging/production bootstrap evidence remains required before go-live.

# S1-BE-002 First Admin Bootstrap Evidence

## Purpose

Этот документ фиксирует `S1-BE-002`: безопасный one-time bootstrap первого администратора CyberVPN после clean DB migrations.

S1 policy:

- owner/bootstrap handle: `@Sasha_Beep`;
- первый admin создаётся только через protected operator CLI;
- публичного bootstrap endpoint нет;
- default credentials запрещены;
- роль первого admin: `owner/super_admin`;
- 2FA/TOTP включена до первого доступа;
- bootstrap создаёт audit event;
- повторный bootstrap блокируется.

Local evidence не заменяет staging/production evidence. Перед go-live этот же runbook должен быть выполнен на staging/prod с redacted transcript.

## Implementation Result

| Check | Result |
|---|---|
| Bootstrap entrypoint | `backend/scripts/bootstrap_first_admin.py` |
| Public endpoint | Not created |
| Explicit confirmation | Required: `CYBERVPN_BOOTSTRAP_CONFIRM=CREATE_FIRST_ADMIN` |
| Default password | Not used; password must be supplied through environment |
| Secret output | Password, TOTP secret/code and hashes are not printed |
| Admin role | `owner/super_admin` |
| 2FA | `totp_enabled=true` at creation time |
| Audit event | `admin.bootstrap.first_admin_created` |
| Second run behavior | Rejected with `bootstrap_locked` |
| Invite path | `owner/super_admin` cannot be created through invite endpoint |

## Code Changes

| File | Change |
|---|---|
| `backend/scripts/bootstrap_first_admin.py` | Added protected one-time CLI bootstrap |
| `backend/scripts/bootstrap_first_admin.py` | Revalidated direct CLI execution on 2026-05-09; bootstrap script now prioritizes `backend/` on `sys.path` so `uv run python scripts/bootstrap_first_admin.py` works without `PYTHONPATH` |
| `backend/src/domain/enums/enums.py` | Added `AdminRole.OWNER_SUPER_ADMIN = "owner/super_admin"` |
| `backend/src/application/use_cases/auth/permissions.py` | Gave owner role full permissions and highest hierarchy |
| `backend/src/application/services/ws_topic_authorization.py` | Allowed owner role on super-admin WebSocket topics and fail-secure unknown topics |
| `backend/src/presentation/dependencies/partner_workspace.py` | Treated owner role as internal admin override |
| `backend/src/presentation/api/v1/admin/invites.py` | Blocked invite creation for `owner/super_admin` |
| `backend/tests/unit/test_first_admin_bootstrap.py` | Added config/redaction tests |
| `backend/tests/unit/test_use_cases.py` | Added owner role permission/hierarchy checks |
| `backend/tests/security/test_ws_topic_auth.py` | Added owner role topic authorization checks |
| `backend/tests/unit/test_domain_entities.py` | Added owner role enum value check |

## Operator Runbook

Run only after clean migrations on the target database.

Required environment variables:

```bash
CYBERVPN_BOOTSTRAP_CONFIRM=CREATE_FIRST_ADMIN
CYBERVPN_BOOTSTRAP_OWNER_HANDLE=@Sasha_Beep
CYBERVPN_BOOTSTRAP_LOGIN='<owner-login>'
CYBERVPN_BOOTSTRAP_EMAIL='<owner-email>'
CYBERVPN_BOOTSTRAP_PASSWORD='<redacted-strong-password>'
CYBERVPN_BOOTSTRAP_TOTP_SECRET='<redacted-base32-secret>'
CYBERVPN_BOOTSTRAP_TOTP_CODE='<redacted-current-6-digit-code>'
CYBERVPN_BOOTSTRAP_SOURCE_IP='<operator-source-label-or-ip>'
```

Production/staging must also provide normal backend secrets through the approved process:

```bash
DATABASE_URL='<redacted>'
REMNAWAVE_TOKEN='<redacted>'
JWT_SECRET='<redacted>'
CRYPTOBOT_TOKEN='<redacted>'
TOTP_ENCRYPTION_KEY='<redacted>'
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-or-approved-fallback>'
```

Bootstrap command:

```bash
cd backend
uv run python scripts/bootstrap_first_admin.py
```

Expected first-run output:

```json
{
  "admin_user_id": "<redacted-uuid>",
  "audit_action": "admin.bootstrap.first_admin_created",
  "auth_realm": "admin",
  "email": "owner@cyber-vpn.net",
  "login": "sasha.beep",
  "role": "owner/super_admin",
  "status": "created",
  "totp_enabled": true
}
```

Expected second-run output:

```json
{
  "message": "first admin bootstrap is locked because admin or bootstrap audit state already exists",
  "reason": "bootstrap_locked",
  "status": "failed"
}
```

## Local Evidence

Disposable DB from the 2026-05-09 `S1-BE-001` revalidation was reset and reused after applying the direct-CLI bootstrap hardening:

| Item | Value |
|---|---|
| Container | `cybervpn-s1-be001-postgres-rerun` |
| Image | `postgres:17.7` |
| Local port | `55433` |
| Database | `cybervpn_s1_be001` |
| Scope | Local disposable implementation evidence only |

Clean schema replay:

```text
alembic current: 20260423_p27_partner_events (head) (mergepoint)
```

Pre-check:

```text
admin_users: 0
bootstrap_audit_events: 0
auth_realms: admin/customer/partner active
```

Bootstrap smoke:

```text
first_cli_exit=0
first_cli_stdout={"admin_user_id": "<redacted-uuid>", "audit_action": "admin.bootstrap.first_admin_created", "auth_realm": "admin", "email": "owner@cyber-vpn.net", "login": "sasha.beep", "role": "owner/super_admin", "status": "created", "totp_enabled": true}
second_cli_exit=1
second_cli_stderr={"message": "first admin bootstrap is locked because admin or bootstrap audit state already exists", "reason": "bootstrap_locked", "status": "failed"}
```

Post-check:

```text
login: sasha.beep
email: owner@cyber-vpn.net
role: owner/super_admin
totp_enabled: true
is_active: true
is_email_verified: true
status: active
auth_realm: admin
password_hash_argon2id: true
totp_secret_stored: true
```

Audit event:

```text
action: admin.bootstrap.first_admin_created
entity_type: admin_user
role: owner/super_admin
bootstrap_owner_handle: @Sasha_Beep
default_credentials: false
permanent_public_endpoint: false
secrets_redacted: true
ip_address: operator-shell
user_agent: S1-BE-002 first-admin bootstrap CLI
```

Local artifacts:

| Artifact | Contents |
|---|---|
| `.tmp/stage1-db/s1-be002-rerun-alembic-upgrade-redacted.log` | Clean schema replay through Alembic `upgrade head` |
| `.tmp/stage1-db/s1-be002-rerun-alembic-current-redacted.log` | Current Alembic head after replay |
| Agent transcript for 2026-05-09 run | Direct CLI first-run/second-run output and DB post-check, with UUIDs redacted |

No local bootstrap secret values were printed in the transcript. Secrets were generated in-process for the disposable smoke and were not committed.

After the evidence run, the disposable PostgreSQL container was stopped and removed to save local resources. It contained only disposable local smoke data and is not a durable evidence source.

## Verification

Component checks:

```bash
cd backend
uv run ruff check \
  scripts/bootstrap_first_admin.py \
  tests/unit/test_first_admin_bootstrap.py \
  tests/security/test_stage1_admin_audit_log.py \
  tests/security/test_stage1_growth_policy.py
```

Result:

```text
All checks passed.
```

Targeted tests:

```bash
cd backend
uv run pytest \
  tests/unit/test_first_admin_bootstrap.py \
  tests/security/test_stage1_admin_audit_log.py \
  tests/security/test_stage1_growth_policy.py \
  -q --no-cov
```

Result:

```text
19 passed in 0.30s
```

Security/static checks were run at task completion and are recorded in the agent completion note. Remaining go-live security work is tracked in `19_STAGE1_TECH_DEBT_REGISTER.md`.

## Remaining Before Go-Live

| Gap | Required action |
|---|---|
| Staging/prod bootstrap | Repeat on real target DBs with redacted transcript |
| Admin login with real browser/API session | Prove owner can log in only with valid 2FA |
| Production secret store | Supply all bootstrap and backend secrets through approved process |
| Admin access protection | Prove admin domain protection, CORS/cookie settings and alerting |
| Backup/restore | Run restore drill after bootstrap and verify admin/audit state is recoverable |

## 2026-05-09 Ordered Batch Revalidation

`S1-BE-002` was re-run as item 6 in the owner-requested ordered batch:

6. `S1-BE-002`
7. `S1-BE-003`
8. `S1-AUTH-001`
9. `S1-AUTH-002`
10. `S1-AUTH-003`

Local disposable evidence:

| Check | Result |
|---|---|
| Disposable PostgreSQL | `postgres:17.7` started on `127.0.0.1:55433`, then removed after the check |
| Clean schema replay | Alembic `upgrade head` reached `20260423_p27_partner_events` |
| Pre-bootstrap state | `admin_users=0`, bootstrap audit events `0`, active admin realm `1` |
| First bootstrap | Created one `sasha.beep / owner@cyber-vpn.net` admin with role `owner/super_admin` |
| Required 2FA | `totp_enabled=true`, `is_email_verified=true` |
| Audit event | `admin.bootstrap.first_admin_created` written with `ip_address=operator-shell` |
| Repeat bootstrap | Rejected with `bootstrap_locked` |
| Post-bootstrap state | `admin_users=1`, bootstrap audit events `1` |
| Secret handling | Generated local password/TOTP values were not printed and were not committed |

Verification:

```text
cd backend
uv run pytest tests/unit/test_first_admin_bootstrap.py tests/security/test_stage1_admin_audit_log.py tests/security/test_stage1_growth_policy.py -q --no-cov
Result: 19 passed in 0.30s

uv run ruff check scripts/bootstrap_first_admin.py tests/unit/test_first_admin_bootstrap.py tests/security/test_stage1_admin_audit_log.py tests/security/test_stage1_growth_policy.py
Result: All checks passed
```

Acceptance remains local-only. Staging/prod bootstrap must still be repeated on the real target database with redacted evidence before go-live.
