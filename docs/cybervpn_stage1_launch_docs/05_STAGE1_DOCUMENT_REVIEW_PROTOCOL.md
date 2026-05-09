> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Document Review and Change Control Protocol

## Purpose

Этот документ фиксирует процесс, при котором сначала утверждаются документы, затем выполняется реализация, затем реализация проверяется против документов, и только после этого Stage 1 вводится в эксплуатацию.

## Document states

| State | Meaning | Allowed next step |
|---|---|---|
| Draft | Документ подготовлен, но не утверждён | Review |
| Review | Владелец проекта и reviewer проверяют документ | Approve / Revise / Block |
| Approved | Документ является source of truth | Implementation may start |
| Blocked | Есть нерешённые blockers | No implementation for affected scope |
| Superseded | Документ заменён новой версией | Only newer approved version is valid |

## Stage 1 documents that must be approved

| ID | Document | Required before implementation? | Required before go-live? |
|---|---|---|---|
| DOC-S1-001 | Stage 1 Charter | Yes | Yes |
| DOC-S1-002 | PRD/User Flows | Yes | Yes |
| DOC-S1-003 | Technical Specification | Yes | Yes |
| DOC-S1-004 | Payment Provider Readiness Matrix | Yes for payment work | Yes |
| DOC-S1-005 | Remnawave Provisioning Runbook | Yes for provisioning work | Yes |
| DOC-S1-006 | Admin Permissions/RBAC Matrix | Yes for admin work | Yes |
| DOC-S1-007 | Legal Pack: ToS/Privacy/AUP/Refund/Cookie | No for internal dev; yes for public | Yes |
| DOC-S1-008 | Support Playbook | No for internal dev; yes for beta | Yes |
| DOC-S1-009 | Acceptance Gates | Yes | Yes |
| DOC-S1-010 | Go-live and Rollback Runbook | No for early dev; yes for staging/prod | Yes |
| DOC-S1-011 | Risk Register | Yes | Yes |
| DOC-S1-012 | Evidence Pack Template | Yes before staging gates | Yes |
| DOC-S1-013 | Approved Decision Log | Yes | Yes |
| DOC-S1-014 | Operational Inputs and Evidence Checklist | Yes | Yes |
| DOC-S1-015 | Technical Debt Register | Yes | Yes |

## Implementation rule

No implementation task should be accepted unless it references at least one approved requirement ID.

Required task metadata:

```text
Task ID:
Linked requirement ID(s):
Component:
Environment affected:
Expected behavior:
Acceptance criteria:
Evidence required:
Rollback impact:
Secrets impact:
Logs/PII impact:
```

## Requirement ID format

| Prefix | Area |
|---|---|
| S1-PROD | Product/user flow |
| S1-AUTH | Auth/account/security |
| S1-PAY | Payments/billing/wallet |
| S1-VPN | Remnawave/provisioning/devices |
| S1-FE | Frontend/customer cabinet/marketing |
| S1-TG | Telegram Bot/Mini App |
| S1-ADM | Admin/RBAC/audit |
| S1-INFRA | Infrastructure/deploy/secrets |
| S1-OBS | Observability/alerts/evidence |
| S1-LEGAL | Legal/privacy/abuse |
| S1-SUP | Support/operations |
| S1-QA | Tests/gates/conformance |
| S1-REL | Release/rollback/go-live |

## Change request process

A change request is required when:

- New feature is added to Stage 1 scope.
- Out-of-scope component is moved into Stage 1.
- Payment provider is added or removed.
- Auth method is added or removed.
- Legal/no-logs/privacy wording changes.
- Domain/topology/secrets strategy changes.
- Any gate is weakened.
- Any hard blocker is reclassified as known issue.

Change request format:

```text
CR ID:
Requested change:
Reason:
Affected documents:
Affected requirements:
Risk impact:
Security/privacy impact:
Operational impact:
Timeline impact:
Decision: Approved / Rejected / Deferred
Approver:
Date:
```

## Document review checklist

Every Stage 1 document must pass:

- Scope is clear.
- Out-of-scope is clear.
- Unknown decisions are listed.
- Hard blockers are not hidden.
- Requirements are testable.
- Acceptance criteria are measurable.
- Evidence requirements are defined.
- Security/privacy implications are stated.
- Rollback/kill switch impact is stated where relevant.
- No placeholders in public-facing legal/product text.

## Implementation review protocol

After implementation, each component must be reviewed against approved documents.

Review dimensions:

1. **Functional correctness** — does it match PRD and technical spec?
2. **Security** — secrets, auth, RBAC, logs, PII, rate limits.
3. **Reliability** — retry, idempotency, failure states, rollback.
4. **Observability** — metrics, logs, Sentry, alerts, evidence.
5. **Supportability** — support can diagnose and escalate.
6. **Legal/privacy alignment** — UI claims match actual data handling.
7. **No scope creep** — partner/native/Helix not accidentally enabled.

## Evidence pack requirements

Each gate must produce evidence:

- Commands executed.
- Test output.
- Screenshots where UI matters.
- Config snippets without secrets.
- Logs with redacted sensitive values.
- Migration results.
- Webhook test results.
- Provisioning test results.
- Rollback test result or documented dry-run.
- Backup restore evidence.

Evidence location should follow the repo convention, for example:

```text
docs/evidence/stage-1/<gate>/<date>/
```

## Go/No-Go decision format

```text
Stage:
Date:
Candidate version/tag:
Approved documents:
Open hard blockers: none / list
Known issues accepted:
Critical gates passed:
Rollback ready: yes/no
Backups verified: yes/no
Support ready: yes/no
Legal ready: yes/no
Decision: Go / No-Go
Decision maker:
Notes:
```

## Rule for disagreements

If business goal conflicts with launch safety, the conflict must be written explicitly as a decision:

- what business wants;
- what the technical/security risk is;
- what mitigation exists;
- whether the risk is accepted.

Do not hide such conflicts inside implementation tasks.
