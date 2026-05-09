# DB / Bootstrap / Backup Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Clean local PostgreSQL migration gate | `../../../28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md` |
| Protected first-admin bootstrap | `../../../29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md` |
| Trial/plan policy seed expectations | `../../../47_STAGE1_PROD_001_TRIAL_POLICY_EVIDENCE.md`, `../../../48_STAGE1_PROD_002_PAID_PLAN_MATRIX_EVIDENCE.md` |
| Local PostgreSQL backup proof | `../../../92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md` |
| Local PostgreSQL restore drill | `../../../93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md` |

## Required Before Go-Live

- Managed staging PostgreSQL clean migration evidence.
- Managed production PostgreSQL migration/upgrade evidence.
- Staging/prod first-admin bootstrap with no default credentials and 2FA proof.
- Backup configuration without secret values.
- Managed staging/prod restore drill transcript to a clean environment.
- RPO/RTO result: S1 target is RPO <=24h, RTO <=4h.
- Remnawave backup/export/rebuild proof.

Current status: local clean migration was revalidated on PostgreSQL 17.7 with S1-sensitive DB defaults off. Local first-admin bootstrap was revalidated on 2026-05-09 after a clean schema replay: the protected direct CLI created exactly one `owner/super_admin`, TOTP was enabled, the bootstrap audit event was written and repeat bootstrap was rejected with `bootstrap_locked`. Local backup proof and restore drill proof exist. Managed staging/prod migration/bootstrap/backup/restore, production RPO/RTO, encrypted off-host storage and Remnawave backup/export/rebuild proof remain required before go-live.
