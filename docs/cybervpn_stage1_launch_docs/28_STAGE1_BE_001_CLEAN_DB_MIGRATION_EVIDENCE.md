> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Follow-up: 2026-05-09
> Backlog ID: `S1-BE-001`
> Статус: local clean PostgreSQL migration gate revalidated on PostgreSQL 17.7; S1 referral DB default corrected to disabled; staging/managed PostgreSQL evidence remains required before go-live.

# S1-BE-001 Clean DB Migration Evidence

## Purpose

Этот документ фиксирует `S1-BE-001`: чистый прогон backend Alembic migrations на пустой PostgreSQL 17 database без ручной подготовки таблиц.

Правило evidence: secret values не печатаются. Локальная disposable database использовалась только для проверки миграционной цепочки; это не production/staging credential evidence.

## Result

| Check | Result |
|---|---|
| Disposable PostgreSQL container | Started and ready |
| Alembic heads before final run | Single head: `20260423_p27_partner_events` |
| Clean `alembic upgrade head` | Passed |
| Alembic current after upgrade | `20260423_p27_partner_events (head) (mergepoint)` |
| `alembic_version` rows | 1 |
| Public table count | 120 |
| Key S1 tables present | `admin_users`, `mobile_users`, `oauth_accounts`, `subscription_plans`, `payments`, `notification_queue`, `audit_logs`, `system_config` |
| S1 DB default-off check | `referral.enabled=false`, `wallet.withdrawal_enabled=false` |
| Non-S1 scaffolding inventory | 39 partner/growth/payout/settlement/attribution tables present; operational rows are zero except 6 static partner role seed rows |

## Local Evidence Artifacts

Generated local evidence lives under `.tmp/stage1-db/`. This directory is ignored and must not be committed because it contains local-only command transcripts and a disposable Alembic config.

| Artifact | Contents |
|---|---|
| `.tmp/stage1-db/s1-be001-alembic-upgrade-redacted.log` | First failed run, missing `oauth_accounts` |
| `.tmp/stage1-db/s1-be001-alembic-upgrade-after-fix-redacted.log` | Second failed run, missing billing foundation tables |
| `.tmp/stage1-db/s1-be001-alembic-upgrade-final-redacted.log` | Final successful `upgrade head` transcript |
| `.tmp/stage1-db/s1-be001-alembic-current-redacted.log` | Final Alembic current output |
| `.tmp/stage1-db/s1-be001-version-query-redacted.log` | `alembic_version` query |
| `.tmp/stage1-db/s1-be001-table-count-redacted.log` | Public table count query |
| `.tmp/stage1-db/s1-be001-key-tables-redacted.log` | Key table existence query |
| `.tmp/stage1-db/s1-be001-rerun-heads-redacted.log` | 2026-05-09 Alembic heads output |
| `.tmp/stage1-db/s1-be001-rerun-upgrade-redacted.log` | 2026-05-09 successful clean `upgrade head` transcript |
| `.tmp/stage1-db/s1-be001-rerun-current-redacted.log` | 2026-05-09 Alembic current output |
| `.tmp/stage1-db/s1-be001-rerun-version-query-redacted.log` | 2026-05-09 `alembic_version` query |
| `.tmp/stage1-db/s1-be001-rerun-table-count-redacted.log` | 2026-05-09 public table count query |
| `.tmp/stage1-db/s1-be001-rerun-key-tables-redacted.log` | 2026-05-09 key S1 table existence query |
| `.tmp/stage1-db/s1-be001-rerun-stage1-default-off-redacted.log` | 2026-05-09 S1 DB default-off check |
| `.tmp/stage1-db/s1-be001-rerun-non-s1-scaffolding-inventory-redacted.log` | 2026-05-09 non-S1 scaffolding table inventory |
| `.tmp/stage1-db/s1-be001-rerun-non-s1-operational-counts-redacted.log` | 2026-05-09 operational partner/growth/payout row counts |

## Commands

The disposable database was created from `postgres:17-alpine` and exposed only on local port `55432`.

```bash
docker run -d --name cybervpn-s1-be001-postgres \
  -e POSTGRES_USER=cybervpn_s1 \
  -e POSTGRES_PASSWORD='<redacted-local-disposable-password>' \
  -e POSTGRES_DB=cybervpn_s1_be001 \
  -p 55432:5432 \
  postgres:17-alpine

docker exec cybervpn-s1-be001-postgres pg_isready \
  -U cybervpn_s1 \
  -d cybervpn_s1_be001

cd backend
PYENV_VERSION=3.13.11 alembic \
  -c ../.tmp/stage1-db/alembic-s1-be001.ini \
  upgrade head

PYENV_VERSION=3.13.11 alembic \
  -c ../.tmp/stage1-db/alembic-s1-be001.ini \
  current
```

Smoke queries:

```sql
SELECT version_num FROM alembic_version;

SELECT count(*) AS public_table_count
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE';

SELECT
  to_regclass('public.admin_users') AS admin_users,
  to_regclass('public.mobile_users') AS mobile_users,
  to_regclass('public.oauth_accounts') AS oauth_accounts,
  to_regclass('public.subscription_plans') AS subscription_plans,
  to_regclass('public.payments') AS payments,
  to_regclass('public.notification_queue') AS notification_queue,
  to_regclass('public.audit_logs') AS audit_logs,
  to_regclass('public.system_config') AS system_config;
```

## Failure Inventory and Fixes

| Finding | Root cause | Fix |
|---|---|---|
| `oauth_accounts` missing | Later OAuth retention/auth migrations assumed the table existed, but no earlier migration created it | Added `20260330_create_oauth_accounts.py`; linked `20260331_minimize_oauth_token_retention.py` after it |
| `subscription_plans` and `payments` missing | Later pricing/payment migrations assumed billing tables existed; older wallet migration skipped payment columns if `payments` was absent | Added `20260210_billing_core.py`; linked `20260210_add_codes_wallet_foundation.py` after it |
| Alembic `version_num` overflow | Several revision identifiers exceeded Alembic's default `VARCHAR(32)` version field | Shortened affected `revision` / `down_revision` strings to <=32 chars |
| PostgreSQL boolean default mismatch | One migration used integer defaults `0/1` for boolean columns | Changed defaults to `sa.false()` / `sa.true()` |
| PostgreSQL identifier length failures | Several explicit index names exceeded PostgreSQL's 63-character identifier limit | Shortened affected index names and matching downgrade references |
| `notification_queue` missing | Backend and worker models reference `notification_queue`, but no migration created it before customer notification delivery FKs | Added `20260422_notification_queue.py`; linked customer notification delivery policy after it |
| `referral.enabled` seeded as enabled | Clean DB review found `system_config.referral.enabled={"enabled": true}` despite S1 decision `REFERRAL_ENABLED=false` and public referral flows disabled | Changed `20260210_add_codes_wallet_foundation.py` seed to `{"enabled": false}` and reran the full clean migration from an empty PostgreSQL 17.7 database |

## Migration Chain Changes

New migrations:

| File | Purpose |
|---|---|
| `backend/alembic/versions/20260210_billing_core.py` | Creates foundational `subscription_plans` and `payments` tables |
| `backend/alembic/versions/20260330_create_oauth_accounts.py` | Creates OAuth account linking table |
| `backend/alembic/versions/20260422_notification_queue.py` | Creates `notification_queue` table used by backend and task-worker |

Adjusted migrations:

| Area | Change |
|---|---|
| Revision IDs | Long IDs shortened before public/staging launch so clean Alembic can record every revision |
| Index names | Long PostgreSQL identifiers shortened |
| Boolean defaults | Integer-like boolean defaults replaced with PostgreSQL-compatible boolean defaults |
| Chain order | Billing, OAuth and notification queue foundation migrations inserted before first dependent migration |
| S1 default-off seed | `referral.enabled` seed changed to disabled so DB config and global settings both fail closed for S1 |

Important compatibility note: this is pre-S1 launch migration-chain repair. If any shared/staging database has already applied the old long revision IDs, it must be rebuilt or handled with a deliberate Alembic stamp/remediation plan. Do not apply this blindly to an existing non-disposable database without checking `alembic_version`.

## Final Evidence Snapshot

Alembic current:

```text
20260423_p27_partner_events (head) (mergepoint)
```

Database revision:

```text
version_num: 20260423_p27_partner_events
```

Table count:

```text
public_table_count: 120
```

Key tables:

```text
admin_users
mobile_users
oauth_accounts
subscription_plans
payments
notification_queue
audit_logs
system_config
```

S1 DB default-off values:

```text
referral.enabled: {"enabled": false}
wallet.withdrawal_enabled: {"enabled": false}
```

Non-S1 scaffolding review:

```text
partner/growth/payout/settlement/attribution scaffolding tables: 39
operational partner/growth/payout rows: 0
static partner_account_roles seed rows: 6
```

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-001` local clean DB migration gate | Closed locally |
| `R-S1-011` clean DB migration risk | Partially closed: local PostgreSQL evidence exists |
| `TD-S1-QA-001` clean DB migration evidence | Partially closed: local evidence exists |

## What Remains Open

| Item | Why still open |
|---|---|
| Managed PostgreSQL staging/prod evidence | This task used a disposable local PostgreSQL container only |
| Backup/restore evidence | Local backup proof is completed in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md`; local restore drill is completed in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`; managed staging/prod evidence remains required |
| First admin bootstrap | Local evidence completed in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md`; staging/prod bootstrap and browser/API admin 2FA evidence still required |
| Seed/config readiness | S1 default-off DB config for referral and wallet withdrawals is verified locally; plan seed/bootstrap data still needs S1-specific verification |
| Existing non-disposable DB remediation | Any DB that already applied old revision IDs needs explicit inspection/rebuild/stamp plan |

## Container State

The original disposable container `cybervpn-s1-be001-postgres` was reused by `S1-BE-002` for local bootstrap evidence and is stopped.

The 2026-05-09 revalidation used `cybervpn-s1-be001-postgres-rerun`. It must be removed after evidence capture unless the next task explicitly needs the same clean DB.

## Completion Statement

`S1-BE-001` is revalidated locally for the updated S1 worktree. A clean PostgreSQL 17.7 database reaches the single Alembic head `20260423_p27_partner_events`, creates 120 public tables, contains the expected S1-critical tables and now seeds S1-sensitive runtime config in the disabled/default-off state. It is acceptable to continue no-cost implementation work, but staging/managed PostgreSQL clean migration evidence remains required before first rollout/go-live.

Follow-up completed: `S1-BE-002` was revalidated in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md`; current next ID is `S1-BE-003`.

## 2026-05-09 Batch Revalidation

`S1-BE-001` was re-run as item 5 in the owner-requested batch:

1. `S1-BE-003`
2. `S1-REL-002`
3. `S1-INFRA-002`
4. `S1-INFRA-004`
5. `S1-BE-001`

Disposable PostgreSQL:

| Item | Value |
|---|---|
| Container | `cybervpn-s1-batch-postgres-20260509` |
| Image | `postgres:17.7` |
| Local bind | `127.0.0.1:55433` |
| Database | `cybervpn_s1_be001` |
| State after run | Removed |

Verification:

```text
PostgreSQL: 17.7
alembic heads: 20260423_p27_partner_events (head)
alembic current: 20260423_p27_partner_events (head) (mergepoint)
alembic_version: 20260423_p27_partner_events
public_table_count: 120
```

Key S1 tables:

```text
admin_users
mobile_users
oauth_accounts
subscription_plans
payments
notification_queue
audit_logs
system_config
```

S1 default-off values:

```text
referral.enabled: {"enabled": false}
wallet.withdrawal_enabled: {"enabled": false}
```

Non-S1 scaffolding row counts:

```text
partner_accounts: 0
partner_codes: 0
growth_codes: 0
payout_instructions: 0
settlement_periods: 0
partner_account_roles: 6 static seed rows
```

Targeted test/lint:

```text
cd backend
uv run pytest tests/security/test_stage1_growth_policy.py -q --no-cov
Result: 8 passed in 0.04s

uv run ruff check alembic/versions/20260210_add_codes_wallet_foundation.py tests/security/test_stage1_growth_policy.py
Result: All checks passed
```

Status remains unchanged: clean local PostgreSQL migration evidence is current and valid, but staging/managed PostgreSQL evidence remains required before rollout.

The next execution item after this five-task batch is `S1-BE-002`.
