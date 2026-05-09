# Observability Evidence

## Local Evidence Indexed

Dedicated `S1-OBS-*` local implementation evidence now exists:

| Area | Evidence |
|---|---|
| Sentry critical projects/config contract | `../../../94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md` |
| PII scrubbing local proof | `../../../95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md` |
| Metrics and dashboards local proof | `../../../96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` |
| Alerts local routing proof | `../../../97_STAGE1_OBS_004_ALERTS_EVIDENCE.md` |

Related local evidence exists:

| Area | Evidence |
|---|---|
| Orphan / paid-but-no-access SLA policy | `../../../38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md` |
| Reconciliation job report contract | `../../../83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md` |
| Telegram notifications contract | `../../../58_STAGE1_TG_006_TELEGRAM_NOTIFICATIONS_EVIDENCE.md` |
| Support escalation process | `../../../71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md` |
| Rollback dry-run | `../../../90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md` |

## Required Before Go-Live

- `S1-OBS-001`: completed locally as Sentry project/config contract for frontend, admin, backend, bot and worker; live Sentry proof remains required.
- `S1-OBS-002`: completed locally as Sentry/log PII scrubbing proof; live org/replay/deployed log proof remains required.
- `S1-OBS-003`: completed locally as metrics/dashboard config for API/auth/payments/provisioning/worker/DB/Redis/Remnawave; deployed Grafana screenshot/live target proof remains required.
- `S1-OBS-004`: completed locally as alert rule/routing contract; live delivery proof to Telegram `-5173727789` and `backup@cyber-vpn.net` remains required.
- Sample incident trace that does not expose secrets, payment secrets or VPN config URLs.

Current status: Sentry local config contract, local PII scrubbing proof, local metrics/dashboard contract and local alert routing contract are complete; observability remains a hard go-live blocker until live Sentry proof, deployed dashboards/live targets and Telegram/email alert delivery are attached.
