> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-05
> Дата revalidation: 2026-05-09
> Backlog ID: `S1-QA-003`
> Статус: PASS for local/no-cost PostgreSQL backup proof; revalidated on 2026-05-09. Local restore drill completed later in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`.

# S1-QA-003 Local Backup Evidence

## Purpose

`S1-QA-003` proves that the local Stage 1 PostgreSQL backup path can create a usable backup artifact without paid hosting.

This is local/dev evidence only. It does not replace managed staging/prod backup evidence, encrypted off-host storage, production RPO/RTO proof or Remnawave backup/export/rebuild evidence.

## Scope Covered

| Scope | Result |
|---|---|
| Local PostgreSQL container is available and healthy | PASS |
| Backup image can connect to `remnawave-db` over Docker network | PASS |
| On-demand PostgreSQL backup completes | PASS |
| Backup artifact uses PostgreSQL custom format and `.dump` suffix | PASS |
| Backup retention is configured for 14 days in S1 local/control-plane config | PASS |
| Backup artifact integrity can be listed with `pg_restore --list` | PASS |
| Backup file is stored under ignored `.tmp/` path, not committed docs/runtime config | PASS |

## Configuration Fix Applied

During `S1-QA-003`, a backup/restore contract mismatch was found and fixed:

- `prodrigestivill/postgres-backup-local:17` defaults to `BACKUP_SUFFIX=.sql.gz`;
- the existing Ansible `backup_restore` role expects `*.dump` files for backup/restore drill discovery;
- local backup service used 7-day retention, while S1 owner decision requires 14 days.

Fix:

| File | Change |
|---|---|
| `infra/docker-compose.yml` | `db-backup` now sets `BACKUP_SUFFIX=.dump` and `BACKUP_KEEP_DAYS=14`; backup healthcheck groups `*.sql.gz`/`*.dump` patterns correctly |
| `infra/ansible/roles/control_plane_stack/defaults/main.yml` | `control_plane_stack_db_backup_keep_days=14` |
| `infra/ansible/inventories/staging/group_vars/control_plane_staging/main.yml` | `control_plane_stack_db_backup_env` includes `BACKUP_SUFFIX: .dump` |
| `infra/ansible/inventories/production/group_vars/control_plane_production/main.yml` | `control_plane_stack_db_backup_env` includes `BACKUP_SUFFIX: .dump` |

## Local Backup Command

The local DB was started without starting the full Remnawave stack:

```bash
cd infra
docker compose up -d remnawave-db
```

The backup was written to an ignored local evidence directory:

```text
.tmp/stage1-backups/s1-qa-003/20260505T183003Z/
```

The on-demand backup used:

```bash
docker run --rm \
  --network cybervpn-data \
  --env-file infra/.env \
  -e POSTGRES_HOST=remnawave-db \
  -e POSTGRES_EXTRA_OPTS='--format=custom --compress=6' \
  -e BACKUP_SUFFIX='.dump' \
  -e SCHEDULE='@daily' \
  -e BACKUP_KEEP_DAYS=14 \
  -e TZ=UTC \
  -v "$PWD/.tmp/stage1-backups/s1-qa-003/20260505T183003Z/postgres:/backups" \
  prodrigestivill/postgres-backup-local:17 /backup.sh
```

No secret values were copied into this evidence document. The command used the local development `.env` only inside the container runtime.

## Observed Result

Original 2026-05-05 result:

```text
backup_result=passed
backup_dir=/home/beep/projects/VPNBussiness/infra/../.tmp/stage1-backups/s1-qa-003/20260505T183003Z
dump_file=postgres-202619.dump
dump_size_bytes=1338849
pg_restore_list_lines=1817
elapsed_seconds=1
```

Redacted local manifest:

```text
backup_id=20260505T183003Z
backup_dir=.tmp/stage1-backups/s1-qa-003/20260505T183003Z
backup_image=prodrigestivill/postgres-backup-local:17
docker_network=cybervpn-data
postgres_host=remnawave-db
postgres_format=custom
backup_suffix=.dump
retention_days=14
backup_keep_policy=BACKUP_KEEP_DAYS=14
dump_file=postgres-202619.dump
dump_size_bytes=1338849
dump_sha256=7f1db34353e147ca06fabe32e2725e4194e7d1331aff370a4c0ff43ec60dfdf9
pg_restore_list_lines=1817
elapsed_seconds=1
secret_values_recorded=false
```

## 2026-05-09 Revalidation Result

Fresh no-cost local backup proof was repeated without creating paid staging/production infrastructure.

```text
backup_result=passed
backup_id=20260509T063942Z
backup_dir=.tmp/stage1-backups/s1-qa-003/20260509T063942Z
backup_image=prodrigestivill/postgres-backup-local:17
docker_network=cybervpn-data
postgres_host=remnawave-db
postgres_format=custom
backup_suffix=.dump
retention_days=14
dump_file=weekly/postgres-202619.dump
dump_size_bytes=1368488
dump_sha256=728e9df2eec4c70acc649a8ba96b4a913a020afb292721232b04d4752e7cb96a
pg_restore_list_lines=1817
secret_values_recorded=false
```

Observed `pg_restore --list` header:

```text
; Archive created at 2026-05-09 06:39:43 UTC
;     dbname: postgres
;     TOC Entries: 1807
;     Compression: gzip
;     Dump Version: 1.16-0
;     Format: CUSTOM
;     Dumped from database version: 17.7 (Debian 17.7-3.pgdg13+1)
;     Dumped by pg_dump version: 17.6 (Debian 17.6-2.pgdg13+1)
```

Interpretation:

- fresh local PostgreSQL backup creation still works;
- backup suffix remains `.dump`;
- artifact is readable by `pg_restore`;
- 14-day retention remains configured in local/control-plane backup settings;
- no backup artifact was added to Git status;
- managed staging/production backup proof remains external and blocking before go-live.

## Integrity Check

Command:

```bash
docker run --rm \
  -v "$PWD/.tmp/stage1-backups/s1-qa-003/20260505T183003Z/postgres:/backups:ro" \
  prodrigestivill/postgres-backup-local:17 \
  pg_restore --list /backups/weekly/postgres-202619.dump
```

Observed header:

```text
; Archive created at 2026-05-05 18:30:03 UTC
;     dbname: postgres
;     TOC Entries: 1807
;     Compression: gzip
;     Dump Version: 1.16-0
;     Format: CUSTOM
;     Dumped from database version: 17.7
;     Dumped by pg_dump version: 17.6
```

Interpretation:

- the artifact is readable by `pg_restore`;
- the artifact is a PostgreSQL custom-format backup, despite using compression internally;
- the dump was suitable for the `S1-QA-004` restore drill later completed in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`.

## Validation Commands

| Check | Result |
|---|---|
| `cd infra && docker compose config --quiet` | PASS |
| `uvx --with pyyaml pytest infra/ansible/tests/test_control_plane_phase8.py -q` | PASS: `4 passed` |
| 2026-05-09 on-demand backup to `.tmp/stage1-backups/s1-qa-003/20260509T063942Z` | PASS |
| `pg_restore --list` against generated `.dump` | PASS: `1817` lines |
| Stale next-step scan for `S1-QA-003` as current/next task | PASS: no stale next-step references in source docs |
| `git diff --check` on touched config/docs | PASS |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory via `next` remains tracked, and `audit fix --force` was not applied because it proposes a breaking/downgrade path |
| Backend `uv export` + `pip-audit` | PASS: no known vulnerabilities found |
| Secret-pattern scan over touched config/docs | PASS: no matches |
| Dangerous-pattern scan over touched config/docs | PASS: no matches |
| Git status for `.tmp/stage1-backups/s1-qa-003` | PASS: no tracked/untracked backup artifacts reported |

## Open Gaps

| Gap | Required later |
|---|---|
| Restore drill | Local restore completed in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`; repeat on staging/prod or accepted managed target before go-live |
| Managed staging/prod backup evidence | Run on managed staging/prod PostgreSQL or accepted deployment target |
| Off-host encrypted storage | Configure encrypted storage outside the primary host before go-live |
| RPO/RTO proof | Measure during restore drill and production-like backup setup |
| Remnawave backup/export/rebuild | Separate Remnawave evidence remains required |
| Alert delivery | Local backup stale alert rules exist in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live alert delivery remains required |

## Resource State

`remnawave-db` was left running intentionally after the 2026-05-09 `S1-QA-003` revalidation because the next task is `S1-QA-004`.

No `db-backup` container was left running; the backup run used an ephemeral container.

## Acceptance Result

`S1-QA-003` is **completed locally and revalidated on 2026-05-09**.

It is acceptable historical backup evidence for the local restore drill. It is not sufficient for go-live until managed staging/prod backup/restore, encrypted off-host storage, production RPO/RTO and alert evidence are complete.

## Demo

| Component | Feature | Status |
|---|---|---|
| `docker compose up -d remnawave-db` | Local PostgreSQL availability for backup | PASS |
| `prodrigestivill/postgres-backup-local:17 /backup.sh` | On-demand custom-format `.dump` backup creation | PASS |
| `pg_restore --list` | Backup artifact readability/integrity listing | PASS |
| Managed staging/production backup | Encrypted off-host managed backup and provider restore path | PARTIAL by design; blocked until external staging/production DB exists |

`S1-OBS-001`, `S1-OBS-002`, `S1-OBS-003` and `S1-OBS-004` were completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`, `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` and `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ID: `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Ordered Batch Revalidation

`S1-QA-003` was re-run as item 18 in the owner-requested ordered batch. A fresh local custom-format PostgreSQL backup was created under ignored `.tmp/` storage.

Fresh manifest:

```text
backup_result=passed
backup_id=20260509T112917Z
backup_dir=.tmp/stage1-backups/s1-qa-003/20260509T112917Z
backup_image=prodrigestivill/postgres-backup-local:17
docker_network=cybervpn-data
postgres_host=remnawave-db
postgres_format=custom
backup_suffix=.dump
retention_days=14
dump_file=weekly/postgres-202619.dump
dump_size_bytes=1376583
dump_sha256=14ef02e7ab00f2ebee504f806cc36b5921c2df2fae1f9baf07a9ac5340802791
pg_restore_list_lines=1817
elapsed_seconds=1
secret_values_recorded=false
```

Observed `pg_restore --list` header:

```text
; Archive created at 2026-05-09 11:29:18 UTC
;     dbname: postgres
;     TOC Entries: 1807
;     Compression: gzip
;     Dump Version: 1.16-0
;     Format: CUSTOM
```

Additional validation:

```text
docker compose -f infra/docker-compose.yml config --quiet
Result: PASS

uvx --with pyyaml pytest infra/ansible/tests/test_control_plane_phase8.py -q
Result: 4 passed in 0.10s
```

Resource note: `remnawave-db` was left running only for the immediately following `S1-QA-004` restore drill.
