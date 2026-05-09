> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Статус: implementation entry criteria после approval документов.

# Stage 1 Implementation Entry Criteria

## Purpose

Этот документ определяет, когда можно переходить от документов к реализации первого этапа запуска CyberVPN. Формат запуска: **Controlled Public Beta CyberVPN**, управляемая публичная beta, где запускается B2C-контур.

## Hard rule

Каждая реализационная задача Stage 1 должна ссылаться на ID из `06_STAGE1_IMPLEMENTATION_BACKLOG.md`. Если задача не имеет ID, она не входит в Stage 1 release scope, пока не добавлена через decision log.

## G0: document approval before implementation

Implementation starts only after:

1. `02_STAGE1_CHARTER.md` approved as Controlled Public Beta / B2C only.
2. `11_STAGE1_REVIEW_CHECKLIST.md` section 2 filled with owner answers.
3. `14_STAGE1_BLOCKER_RESOLUTION_PLAN.md` accepted or superseded.
4. `15_STAGE1_OWNER_DECISION_PACKET.md` converted into approved owner decisions and `17_STAGE1_APPROVED_DECISION_LOG.md` created.
5. `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` accepted as operational/evidence checklist.
6. `19_STAGE1_TECH_DEBT_REGISTER.md` accepted as the active placeholder/deferred-item register.
7. Launch branch/tag policy approved under `S1-REL-001`.
8. Dirty worktree inventory completed under `S1-REL-002`.

## Work that can start first after G0

These tasks reduce uncertainty and should happen before deeper feature work:

| Order | Backlog IDs | Why first |
|---|---|---|
| 1 | `S1-REL-001`, `S1-REL-002`, `S1-REL-003`, `S1-REL-004` | Establish release branch, dirty worktree boundary, decision log and go/no-go owner |
| 2 | `S1-INFRA-001`, `S1-INFRA-006`, `S1-INFRA-007` | Decide topology, secrets model and secrets scan before touching runtime configs |
| 3 | `S1-BE-001`, `S1-BE-002` | Clean DB migrations are locally proven in `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md`; first admin bootstrap path is locally proven in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md`; staging/prod evidence remains required |
| 4 | `S1-PAY-001`, `S1-PAY-004`, `S1-PAY-007`, `S1-PAY-013`...`S1-PAY-017` where applicable | Prove approved provider set, statuses and orphan policy before coding/enabling paid flow changes; replace documentation-derived mappings before provider enablement |
| 5 | `S1-VPN-001`, `S1-VPN-002`, `S1-VPN-003` | Confirm Remnawave environments and protocols before frontend guides and provisioning flows |
| 6 | `S1-LEGAL-001`...`S1-LEGAL-009` | Legal/support text is owner-approved in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; operational/provider evidence remains separate |

## Work blocked by external decisions

| Work | Blocked until | Backlog IDs |
|---|---|---|
| Paid checkout implementation/evidence | Approved provider set, account owner, sandbox/prod provider access setup, status mapping and provider callback samples | `S1-PAY-001`...`S1-PAY-017` |
| Telegram Stars public flow | Telegram Stars evidence for Telegram Bot/Mini App paid flow, bot token, pricing, refund behavior | `S1-PAY-011`, `S1-TG-001`...`S1-TG-005` |
| Public domain config | Local DNS/TLS contract exists in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; local protected ingress contract exists in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`; live DNS access, TLS proof, redirects, edge/firewall proof and admin protection remain external evidence | `S1-INFRA-004`, `S1-INFRA-005`, `S1-BE-005` |
| Production deployment | Production topology, secrets storage, ingress protection | `S1-INFRA-001`...`S1-INFRA-007` |
| Remnawave provisioning | Staging/prod Remnawave instances and protocol list | `S1-VPN-001`...`S1-VPN-008` |
| Public legal pages | Owner-approved S1 legal/text/public-copy closure; mailbox/provider/deployed workflow proof remains separate | `S1-LEGAL-001`...`S1-LEGAL-009`, `TD-S1-LEGAL-*` |
| First admin production use | Bootstrap owner `@Sasha_Beep`, admin domain, RBAC, 2FA | `S1-BE-002`, `S1-ADM-001`...`S1-ADM-004`; local CLI evidence exists, production use still requires target-environment proof |
| Observability go-live | Telegram alert channel `-5173727789`, backup email `backup@cyber-vpn.net`, support/refund mailboxes tested | `S1-OBS-*`, `S1-SUP-*` |
| Google/GitHub OAuth | Provider credentials, callback URLs, state protection, account-linking tests | `S1-AUTH-005`, `S1-AUTH-006` |

## Default-off implementation rule

Unless explicitly approved and evidenced, these features remain hidden or disabled in Stage 1:

1. Partner portal public access.
2. Partner payouts.
3. Native mobile/desktop/Android TV release as launch dependency.
4. Helix/Verta/Beep production exposure.
5. Browser extension.
6. Referral/promo/gift flows; S1 default is hidden/gated with `REFERRAL_ENABLED=false`.
7. Any approved payment provider without evidence.
8. OAuth providers other than Google, GitHub and Telegram identity/linking.
9. Autoprolongation promise.
10. Public analytics/monitoring pages for ordinary users.

## Definition of done for any Stage 1 task

A task can be marked done only when:

1. It references a backlog ID.
2. Acceptance criteria from `06_STAGE1_IMPLEMENTATION_BACKLOG.md` are met.
3. Evidence artifact exists or the task is explicitly non-evidence documentation work.
4. Security/privacy impact is checked.
5. Feature flags or kill switches are documented if the task affects public registration, trial, payments, referral, Telegram flow or provisioning.
6. No secret values are committed.
7. The task does not enable out-of-scope S1 features by accident.

## Required evidence before go-live

| Evidence area | Required before |
|---|---|
| Clean DB migration and first admin bootstrap | Local DB migration/bootstrap evidence exists; staging/managed DB, target bootstrap, admin login/2FA and restore evidence required before any staging release candidate |
| Payment sandbox and webhook idempotency | Any paid beta test |
| Provider-specific real callback/status samples replacing documentation placeholders | Any provider enablement |
| Production payment credentials inventory without values | Any production paid beta |
| Remnawave staging/prod provisioning | Any public beta access |
| Backup restore drill | Production go-live |
| Rollback dry-run | Production go-live |
| Observability alert test | Production go-live |
| Telegram alert channel, backup email, support and refund mailbox tests | Production go-live |
| Legal final pages and support templates | Closed for owner-approved legal/text work in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; live mailboxes/provider/support workflow still required before public beta with real users |
| Secrets scan and frontend bundle/env scan | Any release candidate; local frontend proof exists in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`, but final RC/deployed artifact scan remains required |

## Stop conditions

Implementation or rollout must stop if:

1. Owner decisions in `11_STAGE1_REVIEW_CHECKLIST.md` are incomplete.
2. A P0 task needs a secret, domain, provider or Remnawave instance that does not exist.
3. A paid flow cannot prove signature verification and idempotency.
4. A provisioning flow can lose a paid user without retry/support escalation.
5. Public pages still contain unresolved placeholders or claims outside the owner-approved S1 wording boundary.
6. Rollback, backup restore or observability evidence is missing before go-live.
7. Launch-critical and experimental code cannot be separated.
8. Provider documentation-derived mapping is still the only evidence for an enabled payment provider.
9. Orphan/paid-but-no-access handling can allow unresolved items older than 24h without P0 escalation.

## Approved implementation sequence

After G0, execute in this order:

1. Governance/release boundary: `S1-REL-*`.
2. Infrastructure and secrets: `S1-INFRA-*`.
3. Backend foundation: `S1-BE-*`, then `S1-AUTH-*`.
4. Payments policy and provider evidence: `S1-PAY-*`.
5. Product subscription/trial/wallet states: `S1-PROD-*`.
6. Remnawave provisioning: `S1-VPN-*`.
7. Frontend and Telegram critical flows: `S1-FE-*`, `S1-TG-*`.
8. Admin/support/legal/observability/security: `S1-ADM-*`, `S1-SUP-*`, `S1-LEGAL-*`, `S1-OBS-*`.
9. QA/evidence/go-live: `S1-QA-*`, `S1-REL-006`, `S1-REL-007`.
