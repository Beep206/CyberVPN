> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-06
> Дата revalidation: 2026-05-09
> Backlog ID: `S1-QA-004`
> Статус: PASS for local/no-cost PostgreSQL restore drill; revalidated on 2026-05-09. Not a go-live clearance.

# S1-QA-004 Restore Drill Evidence

## Purpose

`S1-QA-004` proves that the local Stage 1 PostgreSQL backup artifact from `S1-QA-003` can be restored into a clean disposable database, queried, and removed without using paid hosting.

This is local/dev evidence only. It does not replace managed staging/prod backup evidence, encrypted off-host storage, production RPO/RTO proof, Remnawave backup/export/rebuild proof or alert delivery evidence.

## Acceptance Summary

| Requirement | Result |
|---|---|
| Source backup artifact exists | PASS |
| `pg_restore --list` can read the dump | PASS: `1817` lines |
| Clean restore database created | PASS: `s1_qa_004_restore_drill` |
| Dump restored into clean database | PASS |
| Restored database responds to smoke query | PASS: `SELECT 1` returned `1` |
| Restored schema/table smoke completed | PASS: `159` public tables, `2` expected schemas present |
| Key Stage 1 tables visible after restore | PASS: `helix.manifest_versions`, `public.payments`, `public.users`, `public.wallets` |
| Disposable restore database removed after drill | PASS |
| Local Docker resources stopped after task | PASS: no running Compose services after cleanup |

## Source Backup Artifact

The restore drill used the local custom-format PostgreSQL dump created in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md`.

```text
source_dump=.tmp/stage1-backups/s1-qa-003/20260505T183003Z/postgres/weekly/postgres-202619.dump
source_sha256=7f1db34353e147ca06fabe32e2725e4194e7d1331aff370a4c0ff43ec60dfdf9
source_size_bytes=1338849
```

2026-05-09 revalidation source backup:

```text
source_dump=.tmp/stage1-backups/s1-qa-003/20260509T063942Z/postgres/weekly/postgres-202619.dump
source_sha256=728e9df2eec4c70acc649a8ba96b4a913a020afb292721232b04d4752e7cb96a
source_size_bytes=1368488
pg_restore_list_lines=1817
```

The redacted restore transcript was written to an ignored local evidence directory:

```text
.tmp/stage1-restore/s1-qa-004/20260505T192350Z/
```

## Restore Manifest

Original 2026-05-05 manifest:

```text
S1-QA-004 local PostgreSQL restore drill
started_utc=2026-05-05T19:23:50Z
ended_utc=2026-05-05T19:24:01Z
elapsed_seconds=11
source_dump=.tmp/stage1-backups/s1-qa-003/20260505T183003Z/postgres/weekly/postgres-202619.dump
source_sha256=7f1db34353e147ca06fabe32e2725e4194e7d1331aff370a4c0ff43ec60dfdf9
source_size_bytes=1338849
pg_restore_list_lines=1817
restore_database=s1_qa_004_restore_drill
restore_database_removed=true
public_table_count=159
schema_presence_count=2
select1=1
```

2026-05-09 revalidation manifest:

```text
S1-QA-004 local PostgreSQL restore drill
started_utc=2026-05-09T06:48:42Z
restore_id=20260509T064842Z
ended_utc=2026-05-09T06:48:55Z
elapsed_seconds=13
source_dump=.tmp/stage1-backups/s1-qa-003/20260509T063942Z/postgres/weekly/postgres-202619.dump
source_sha256=728e9df2eec4c70acc649a8ba96b4a913a020afb292721232b04d4752e7cb96a
source_size_bytes=1368488
pg_restore_list_lines=1817
restore_database=s1_qa_004_restore_drill
restore_database_removed=true
public_table_count=159
schema_presence_count=2
select1=1
key_tables_visible=helix.manifest_versions, public.payments, public.users, public.wallets
```

## Commands Used

The drill intentionally restored through `pg_restore` inside the running `remnawave-db` container so no database password or secret value had to be printed or passed through the transcript.

```bash
cd infra
docker compose exec -T remnawave-db pg_restore --list < ../.tmp/stage1-backups/s1-qa-003/20260505T183003Z/postgres/weekly/postgres-202619.dump
docker compose exec -T remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE s1_qa_004_restore_drill;"
docker compose exec -T remnawave-db pg_restore -U postgres -d s1_qa_004_restore_drill < ../.tmp/stage1-backups/s1-qa-003/20260505T183003Z/postgres/weekly/postgres-202619.dump
docker compose exec -T remnawave-db psql -U postgres -d s1_qa_004_restore_drill -tAc "SELECT 1;"
docker compose exec -T remnawave-db psql -U postgres -d s1_qa_004_restore_drill -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
docker compose exec -T remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS s1_qa_004_restore_drill;"
docker compose stop remnawave-db
```

## RPO/RTO Interpretation

| Metric | Local result | Interpretation |
|---|---:|---|
| Local restore drill elapsed time | `13s` on 2026-05-09 revalidation; `11s` historical 2026-05-05 result | Useful implementation evidence only |
| S1 target RTO | `<=4h` | Still must be proven on staging/prod or the accepted managed DB target |
| S1 target RPO | `<=24h` | Requires managed encrypted off-host backup schedule and restore proof |

The local `13s` result does not prove production RTO. It proves the dump is restorable and the restore procedure is executable.

## Open Gaps

| Gap | Required later |
|---|---|
| Managed staging/prod restore evidence | Repeat restore drill on managed staging/prod PostgreSQL or the accepted production-like target |
| Encrypted off-host backup storage | Configure and prove storage outside the primary host |
| Production RPO/RTO | Measure with production-like data size, provider storage and network path |
| Remnawave backup/export/rebuild | Prove Remnawave control-plane export/rebuild separately |
| Alert delivery | Local restore-drill-evidence alert rules exist in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live delivery proof remains required |

## Resource State

After the 2026-05-09 drill, the disposable restore database was dropped and `remnawave-db` was stopped to avoid using local resources.

No `.tmp/stage1-restore/s1-qa-004` files are tracked by Git.

## Demo

| Component | Feature | Status |
|---|---|---|
| `pg_restore --list` | Fresh backup artifact readability | PASS: `1817` lines |
| `pg_restore -d s1_qa_004_restore_drill` | Restore into clean disposable local DB | PASS |
| Smoke queries | Restored DB queryability and schema/table visibility | PASS: `SELECT 1`, `159` public tables, `2` schemas, key S1 tables visible |
| Cleanup | Disposable restore DB and local container resource cleanup | PASS: restore DB dropped, `remnawave-db` stopped |
| Managed staging/production restore | Provider-backed restore/RPO/RTO proof | PARTIAL by design; blocked until external staging/production DB exists |

## Validation Commands

| Check | Result |
|---|---|
| `pg_restore --list` against S1-QA-003 dump | PASS: `1817` lines |
| 2026-05-09 restore drill against fresh backup `20260509T063942Z` | PASS: `13s` elapsed |
| Clean disposable restore DB smoke | PASS: `SELECT 1`, `159` public tables, `2` schemas |
| Key Stage 1 tables visible after 2026-05-09 restore | PASS: `helix.manifest_versions`, `public.payments`, `public.users`, `public.wallets` |
| Restore DB cleanup | PASS: `DROP DATABASE IF EXISTS s1_qa_004_restore_drill` completed |
| Stale next-step scan for `S1-QA-004` as current/next task | PASS: no stale source-doc matches |
| Evidence-pack relative link validation | PASS |
| `cd infra && docker compose config --quiet` | PASS |
| Running Compose services after cleanup | PASS: no running services reported |
| New evidence file trailing whitespace scan | PASS |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory via `next` remains tracked, and `audit fix --force` was not applied because it proposes a breaking/downgrade path |
| Backend `uv export` + `pip-audit` | PASS: no known vulnerabilities found |
| Secret-pattern scan over touched source docs | PASS: no matches |
| Dangerous-pattern scan over touched source docs | PASS: no matches |
| Combined pack secret/danger scan | FALSE POSITIVES: matched documented `rg` command examples and historical `/tmp` cleanup snippets, not secret values or new runtime code |
| Git status for `.tmp/stage1-restore/s1-qa-004` | PASS: no tracked/untracked restore artifacts reported |

## Acceptance Result

`S1-QA-004` is **completed locally and revalidated on 2026-05-09**.

It is acceptable for continuing local/no-cost S1 work. It is not sufficient for go-live until managed staging/prod backup/restore, encrypted off-host storage, production RPO/RTO, Remnawave backup/export/rebuild and alert delivery evidence are complete.

`S1-OBS-001`, `S1-OBS-002`, `S1-OBS-003` and `S1-OBS-004` were completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`, `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` and `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ID: `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Ordered Batch Revalidation

`S1-QA-004` was re-run as item 19 in the owner-requested ordered batch using the fresh `S1-QA-003` backup `20260509T112917Z`.

Fresh restore manifest:

```text
S1-QA-004 local PostgreSQL restore drill
started_utc=20260509T113011Z
restore_id=20260509T113011Z
elapsed_seconds=7
source_dump=.tmp/stage1-backups/s1-qa-003/20260509T112917Z/postgres/weekly/postgres-202619.dump
source_sha256=14ef02e7ab00f2ebee504f806cc36b5921c2df2fae1f9baf07a9ac5340802791
source_size_bytes=1376583
pg_restore_list_lines=1817
restore_database=s1_qa_004_restore_drill
restore_database_removed=t
public_table_count=159
schema_presence_count=2
select1=1
key_tables_visible=helix.manifest_versions, public.payments, public.users, public.wallets
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

Resource note: the disposable restore DB was dropped and `remnawave-db` was stopped after the drill.

Local acceptance remains unchanged. Managed staging/prod restore, encrypted off-host storage, production RPO/RTO, Remnawave backup/export/rebuild and live alert delivery remain required before go-live.
