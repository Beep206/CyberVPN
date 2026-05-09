> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Risk Register

## Risk scale

| Level | Meaning |
|---|---|
| Critical | Blocks Stage 1 go-live |
| High | Must be mitigated or explicitly accepted |
| Medium | Can be known issue if documented |
| Low | Track only |

## Current risk register

| ID | Risk | Level | Evidence from questionnaire | Mitigation | Stage 1 status |
|---|---|---|---|---|---|
| R-S1-001 | Payment providers selected but no accounts/credentials/evidence | Critical | Owner selected PayRam, NOWPayments, CryptoBot, Telegram Stars, Digiseller, YooKassa; local CryptoBot provider selection, sandbox runtime and production credential inventory are documented in `125`, `126`, `127`; real account/secret-store/callback evidence not proven | Create accounts, store credentials through approved process, attach provider status mapping, webhook/idempotency/refund/reconciliation evidence | Partially closed: provider set and local CryptoBot credential inventory approved; real provider evidence open |
| R-S1-002 | Remnawave staging/prod not deployed | Critical | Owner selected separate staging/prod Remnawave; instances/evidence not proven. Local control-plane smoke exists in `24_STAGE1_VPN_012_LOCAL_REMNAWAVE_SMOKE_EVIDENCE.md`; local connected node smoke exists in `25_STAGE1_VPN_012_LOCAL_REMNAWAVE_NODE_EVIDENCE.md`; local protocol allowlist exists in `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md`; local trial provisioning contract exists in `40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md`; local paid provisioning contract exists in `41_STAGE1_VPN_005_PAID_PROVISIONING_EVIDENCE.md`; local provisioning retry contract exists in `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md` | Use local/dev Remnawave for implementation confidence; deploy separate staging/prod Remnawave and prove the approved profiles/inbounds before go-live and before claiming real provisioning readiness | Partially closed: placement, local Remnawave/node smoke, local protocol list, local trial provisioning contract, local paid provisioning contract and local retry contract approved; staging/prod profile/provisioning/outage evidence open |
| R-S1-003 | Production topology not evidenced | Critical | Owner selected Simple Controlled Hybrid Container Topology; redacted secrets inventory/policy exists in `26_STAGE1_INFRA_006_SECRETS_INVENTORY_AND_POLICY.md`; local S1 dependency/container audit exists in `89_STAGE1_QA_002_DEPENDENCY_AUDIT_EVIDENCE.md` | Produce deploy diagram, ingress list, rollback/backup evidence; replace local/interim secret policy with production secret-store evidence before go-live; rebuild/scan final RC images from approved Dockerfiles | Partially closed: topology approved, secrets model documented and local S1 Python image high-critical audit passed; deploy/rollback/backup/production secret/final RC image evidence open |
| R-S1-004 | Domains selected but DNS/TLS not evidenced | High | `cyber-vpn.net` primary, `cyber-vpn.org` mirror/redirect, `admin.cyber-vpn.net` primary, `admin.cyber-vpn.org` redirect approved | Configure DNS/TLS/CORS/cookies/OAuth/webhooks and redirect evidence | Partially closed: domains approved; evidence open |
| R-S1-005 | Legal seller selected and legal/text pack owner-approved | Critical | Owner selected individual founder/owner; local Terms/Privacy/AUP/Refund/Cookie candidates exist; owner-approved legal/text closure exists in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Keep sensitive identity/tax/banking data outside repo; attach only redacted operational/provider evidence where required | Closed for legal/text approval; operational evidence still required |
| R-S1-006 | Privacy Policy final approval complete for S1 text | Critical | Local Privacy Policy candidate in `73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`; owner-approved legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Prove mailbox delivery, provider/processor deployment evidence and PII scrubbing under ops/security gates | Closed for legal/text approval; operational evidence still required |
| R-S1-007 | AUP/Cookie/Refund final approval complete for S1 text | High | Local AUP, Refund and Cookie candidates exist in `74`, `75`, `76`; owner-approved closure exists in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Prove abuse/refund mailbox delivery, provider refund behavior, deployed cookie inventory/`Set-Cookie`, consent and observability PII evidence under ops/security/provider gates | Closed for legal/text approval; operational evidence still required |
| R-S1-008 | Payment status mapping placeholders not proven | Critical | Documentation-derived provider mappings recorded in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`; real provider evidence absent | Replace placeholder mappings with real provider callback/API samples and tests before enablement | Partially closed: placeholder mapping exists; evidence open |
| R-S1-009 | Orphan payment policy not proven end-to-end | Critical | Owner approved no unresolved paid-but-no-access/orphan older than 24h; local policy/SLA/dashboard proof completed in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md` | Wire real admin/support queue, audit trail, alerts and provider reconciliation workflow | Partially mitigated; blocking before paid beta |
| R-S1-010 | Webhook idempotency not proven end-to-end | Critical | Local contract and duplicate-webhook ASGI proof completed in `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`; durable Redis/DB and live provider callback proof absent | Back keys with Redis/DB uniqueness and attach duplicate callback transcripts per enabled provider | Partially mitigated; blocking before paid beta |
| R-S1-011 | Migrations not proven on clean DB | Critical | Local clean PostgreSQL migration gate completed in `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md`; managed staging/prod DB evidence not run | Use local evidence for implementation; repeat on staging/managed PostgreSQL and preserve evidence before go-live | Partially closed: local evidence exists; staging/prod evidence open |
| R-S1-012 | First admin bootstrap staging/prod evidence missing | Critical | Bootstrap owner `@Sasha_Beep`; policy approved; local protected CLI/bootstrap/audit evidence completed in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md` | Repeat bootstrap on staging/prod through approved secret process, prove admin login requires 2FA, audit and backup/restore evidence | Partially closed: local evidence exists; staging/prod evidence open |
| R-S1-013 | Admin risky functions too broad | High | Manual grants/refunds/disable/regenerate dangerous | RBAC/2FA/audit/feature gates | Open |
| R-S1-014 | Account linking conflicts | High | Telegram/email/OAuth conflict needs careful design | Approve account linking policy and tests | Open |
| R-S1-015 | Open registration + trial abuse | High | Trial for everyone; 3 days/1 device | Rate limits, trial abuse checks, kill switch | Open |
| R-S1-016 | Referral/promo/gift abuse | Medium/High | Owner approved disabled-by-default for S1 | Keep hidden/gated, `REFERRAL_ENABLED=false`, manual audited support grants only | Mitigated for S1; monitor runtime gates |
| R-S1-017 | 38 languages create QA burden | Medium | All 38 desired | Critical-path locale audit; allow secondary locale known issues | Open |
| R-S1-018 | On-call/support single-person coverage and alert evidence | High | Primary/backup/finance/bootstrap all assigned to `@Sasha_Beep`; Telegram channel `-5173727789`, backup email `backup@cyber-vpn.net`, support/refund mailboxes recorded; local escalation runbook exists in `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md` | Test alert/support escalation and either accept single-person S1 risk or assign separate backup | Operational values and local runbook recorded; alert delivery/human SLA/risk acceptance open |
| R-S1-019 | Backup production retention/RPO/RTO not evidenced | High | Owner approved daily encrypted backups retained 14 days, RPO <=24h, RTO <=4h; local PostgreSQL backup proof completed in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md`; local restore drill completed in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md` | Configure managed staging/prod encrypted off-host backups, repeat restore drill on accepted managed target, prove production RPO/RTO and backup alerts | Partially closed locally; staging/prod/off-host/RPO/RTO/alert evidence open |
| R-S1-020 | Secrets management not production-proven | Critical | OpenBao target, env surfaces many; `26_STAGE1_INFRA_006_SECRETS_INVENTORY_AND_POLICY.md` records inventory/policy; `27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md` records Gitleaks scans, current-index remediation and local Git-history purge for `infra/APIToken.txt` / `frontend/localhost.har` | Force-replace remote history when owner is ready, rotate any affected token if applicable, add durable allowlist/baseline, attach production/staging secret-store evidence | Partially closed: inventory/policy, scan and local history purge done; remote replacement/rotation, allowlist/baseline and production proof open |
| R-S1-021 | Frontend bundle may leak env | High | Scan needed | Bundle/env scan | Open |
| R-S1-022 | No-logs claim may overpromise if expanded beyond S1 wording | Critical | Owner approved bounded S1 no-absolute-overpromise stance in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; deployed logging proof remains operational evidence | Keep public copy within approved wording until backend/Remnawave/node/Sentry evidence is attached | Mitigated for legal/text; operational proof still required |
| R-S1-023 | Observability not live-proven | High | Expanded observability coverage defined; Sentry local config contract completed in `94`; local PII scrubbing proof completed in `95`; local metrics/dashboard contract completed in `96`; local alert routing contract completed in `97`; live projects/dashboards/alerts unknown | Complete live Sentry scrub-rule/test-event proof, deployed Grafana screenshots/live target proof and live alert delivery to Telegram/email | Partially mitigated locally; open for go-live |
| R-S1-024 | Rollback not proven on staging/prod | Critical | Local rollback dry-run/proof exists in `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md`: release-pointer rollback, rollback target compose validation, Mini App/admin runtime rollback controls and registration/payment/provisioning safety tests pass locally | Repeat rollback dry-run on staging/prod final RC artifacts; prove frontend/admin hosting rollback, provider pause, Remnawave rollback, DB backup/restore interaction and alert/status comms | Partially closed locally; blocking before go-live |
| R-S1-025 | Dirty worktree very broad | Critical | Current snapshot audited in `22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md`; S1 docs untracked and frontend build/config changes need validation | Re-run scope map before first RC; freeze branch and exclude experimental code | Partially closed for current snapshot; open before RC |
| R-S1-026 | Partner/native/Helix scope creep | High | Many systems exist | Feature flags/default-off and runtime audit | Open |
| R-S1-027 | Autoprolongation provider mismatch | Medium/High | Owner approved no autoprolongation promise in S1 | Keep copy/manual renewal aligned; only reminders/invoice links if tested | Mitigated for S1 |
| R-S1-028 | Refund/dispute process not operational | High | Domain exists, final process unknown | Legal + finance + admin workflow | Open |
| R-S1-029 | Torrent/P2P/TOR node traffic policy partial | Medium | Plugin desired on certain nodes; TOR control requested if supported by Remnawave addon/plugin | Use local policy in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`: Torrent/P2P restricted by default, Remnawave Torrent Blocker only after plugin evidence, no native TOR addon found in official docs, TOR control disabled until egress/shared-list/custom-routing evidence exists | Partially closed locally; staging/prod plugin/provider/webhook/alert evidence open |
| R-S1-030 | Support AI may give wrong operational status | Medium/High | AI first line desired | Ground AI in backend status; escalation | Open |

## Highest priority blockers to close first

1. Payment provider accounts, credentials, real callback samples and evidence for the approved provider set.
2. Remnawave staging/prod deployment and provisioning evidence.
3. Production topology/domain DNS/TLS/ingress evidence.
4. Legal/text pack is closed by owner; remaining related work is operational evidence such as mailboxes, provider behavior, cookie/PII proof and support/admin workflow.
5. Remote history replacement/owner push decision, affected-token rotation and durable scan allowlist/baseline after `27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md`.
6. First admin bootstrap staging/prod/browser evidence; local clean DB migration and local bootstrap evidence exist, but staging/managed PostgreSQL evidence remains required before go-live.
7. Durable payment idempotency and deployed orphan-payment admin/support/alert evidence.
8. Provisioning failure/retry evidence.
9. Managed encrypted off-host backups and production RPO/RTO evidence. Local PostgreSQL backup and restore proof exists in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md` and `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`.
10. Staging/prod rollback on final RC artifacts and kill switches. Local rollback proof exists in `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md`.

## Risk handling rules

- Critical risks cannot be accepted silently.
- A Critical risk can only be downgraded if mitigation is implemented and evidence exists.
- High risks can be accepted only with written owner decision and rollback/kill switch where relevant.
- Medium risks can become known issues if they do not affect auth/payment/provisioning/security/legal/support.
- Low risks are tracked for Stage 2.

## Stage 1 risk posture

Current risk posture is **ready for S0 decision-freeze review with owner answers recorded**, but **not ready for production go-live**. It is ready for Stage 1 blocker closure and implementation planning only after `16_STAGE1_IMPLEMENTATION_ENTRY_CRITERIA.md` is satisfied.

Primary reason: key business decisions and operational handles/contacts are now approved, and local clean migration/bootstrap/webhook idempotency/orphan-payment policy plus local critical E2E, dependency audit, rollback dry-run, PostgreSQL backup proof, local restore drill proof and local alert routing proof exists, but production evidence, credentials, real provider callback samples, durable idempotency persistence, real admin/support queue, live alert delivery, staging/prod bootstrap and admin 2FA login proof, managed encrypted off-host backup/RPO/RTO evidence, staging/prod rollback on final RC artifacts, live observability evidence, final RC artifact/image scans and pre-RC dirty worktree scope map are not yet closed.
