# CyberVPN Partner Platform Environment Command Inventory Sheet

**Date:** 2026-04-19  
**Status:** Environment command inventory baseline for `RB-012`  
**Purpose:** convert the repository's already-existing local, staging, and production command sources into one explicit inventory sheet, so cutover windows no longer depend on generic production placeholders or chat-only operator knowledge.

---

## 1. Document Role

This document is the canonical command companion to:

- [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)
- [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)
- [../testing/partner-platform-phase8-production-readiness-bundle.md](../testing/partner-platform-phase8-production-readiness-bundle.md)
- [../testing/partner-platform-phase8-exit-evidence.md](../testing/partner-platform-phase8-exit-evidence.md)

It exists to make one thing explicit:

- the repository already contains concrete command families for staging and production rollout work;
- what still remains unresolved is not the existence of command families, but the exact runtime parameters, named human owners, and named rollout windows for a live production activation.

This sheet does not replace service-specific runbooks. It centralizes where the allowed commands already live and how they should be referenced in rehearsal and cutover records.

---

## 2. Canonical Command Sources

The command sources below are the only approved sources for environment command truth in the current repository baseline:

- [infra/Makefile](/home/beep/projects/VPNBussiness/infra/Makefile)
- [PRODUCTION_EDGE_CANARY_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md)
- [CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md)
- [STAGING_REMNAWAVE_SMOKE_CHECKLIST.md](/home/beep/projects/VPNBussiness/docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md)
- [EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md](/home/beep/projects/VPNBussiness/docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md)
- [infra/README.md](/home/beep/projects/VPNBussiness/infra/README.md)

Operational rule:

1. use the exact commands from these sources;
2. do not replace them with ad-hoc chat instructions;
3. if a live production window needs extra parameters, record those parameters in the window registration record instead of editing the command family itself.

---

## 3. Command Family Ownership

| Command family | Canonical source | Primary owner group | Notes |
|---|---|---|---|
| local bootstrap | repo root `npm`, `infra/docker compose`, `infra/README.md` | platform engineering, frontend platform | local integration only |
| staging terraform and inventory | `infra/Makefile` | platform engineering | foundation, edge, dns, control-plane |
| staging rollout and smoke | `infra/Makefile`, staging runbooks | platform engineering, QA | includes smoke and rollback |
| production terraform and inventory | `infra/Makefile`, production canary runbook | platform engineering | live environment precondition |
| control-plane release promotion | `infra/Makefile`, control-plane release runbook | platform engineering | requires immutable image digests |
| production edge canary rollout | `infra/Makefile`, production canary runbook | platform engineering, QA | live window must name canary hosts |
| production rollback | `infra/Makefile`, production canary runbook | platform engineering, incident commander | live window must name rollback owner |
| production smoke and reconciliation references | cutover runbooks plus evidence packs | QA, finance ops, risk ops | command references must be linked in the window record |

---

## 4. Local Environment Command Inventory

Local commands are intentionally simple and developer-owned.

| Use case | Canonical command |
|---|---|
| install dependencies | `npm install` |
| start core local services | `cd infra && docker compose up -d` |
| start frontend dev server | `NEXT_TELEMETRY_DISABLED=1 npm run dev` |
| optional local dev server in background | `nohup NEXT_TELEMETRY_DISABLED=1 npm run dev > /tmp/next.log 2>&1 &` |

Local validation still relies on target-specific engineering gate packs. This sheet only captures the shared bootstrap layer.

---

## 5. Staging Environment Command Inventory

## 5.1 Terraform And Inventory

| Use case | Canonical command |
|---|---|
| init staging foundation | `cd infra && make terraform-init-staging-foundation` |
| plan staging foundation | `cd infra && make terraform-plan-staging-foundation` |
| init staging edge | `cd infra && make terraform-init-staging-edge` |
| plan staging edge | `cd infra && make terraform-plan-staging-edge` |
| init staging dns | `cd infra && make terraform-init-staging-dns` |
| plan staging dns | `cd infra && make terraform-plan-staging-dns` |
| init staging control-plane | `cd infra && make terraform-init-staging-control-plane` |
| plan staging control-plane | `cd infra && make terraform-plan-staging-control-plane` |
| generate staging inventory | `cd infra && make inventory-staging` |

## 5.2 Edge And Service Rollouts

| Use case | Canonical command |
|---|---|
| bootstrap and verify edge baseline | `cd infra && make ansible-phase2-staging` |
| rollout and verify Remnawave | `cd infra && make ansible-phase3-staging` |
| verify Remnawave only | `cd infra && make ansible-remnawave-verify-staging` |
| rollback Remnawave | `cd infra && make ansible-remnawave-rollback-staging` |
| rollout and verify Helix | `cd infra && make ansible-phase4-staging` |
| verify Helix only | `cd infra && make ansible-helix-verify-staging` |
| rollback Helix | `cd infra && make ansible-helix-rollback-staging` |
| rollout and verify Alloy | `cd infra && make ansible-phase5-staging` |
| verify Alloy only | `cd infra && make ansible-alloy-verify-staging` |
| rollback Alloy | `cd infra && make ansible-alloy-rollback-staging` |

## 5.3 Control-Plane Release Flow

| Use case | Canonical command |
|---|---|
| promote staging release manifest | `cd infra && make control-plane-release-staging BACKEND_IMAGE=ghcr.io/<owner>/<repo>/backend@sha256:<digest> WORKER_IMAGE=ghcr.io/<owner>/<repo>/task-worker@sha256:<digest> HELIX_ADAPTER_IMAGE=ghcr.io/<owner>/<repo>/helix-adapter@sha256:<digest> SOURCE_COMMIT=<git-sha>` |
| bootstrap staging vault from source file | `cd infra && make control-plane-vault-bootstrap-staging SECRETS_SOURCE=/secure/path/control-plane-staging.yml` |
| bootstrap and encrypt staging vault | `cd infra && make control-plane-vault-bootstrap-staging SECRETS_SOURCE=/secure/path/control-plane-staging.yml ENCRYPT_VAULT=1 VAULT_PASSWORD_FILE=/secure/path/.vault-pass.txt` |
| rollout staging control-plane | `cd infra && make ansible-control-plane-rollout-staging` |
| verify staging control-plane | `cd infra && make ansible-control-plane-verify-staging` |
| backup staging control-plane | `cd infra && make ansible-control-plane-backup-staging` |
| restore-drill staging control-plane | `cd infra && make ansible-control-plane-restore-drill-staging` |
| rollback staging control-plane | `cd infra && make ansible-control-plane-rollback-staging` |

## 5.4 Staging Smoke

| Use case | Canonical command |
|---|---|
| operator shortcut smoke | `cd infra && make remnawave-staging-smoke` |
| staging smoke prerequisites | `cd infra && make ansible-phase3-staging && make ansible-remnawave-verify-staging` |

The detailed environment variables and API checks remain in [STAGING_REMNAWAVE_SMOKE_CHECKLIST.md](/home/beep/projects/VPNBussiness/docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md).

---

## 6. Production Environment Command Inventory

## 6.1 Terraform And Inventory

| Use case | Canonical command |
|---|---|
| init production foundation | `cd infra && make terraform-init-production-foundation` |
| plan production foundation | `cd infra && make terraform-plan-production-foundation` |
| init production edge | `cd infra && make terraform-init-production-edge` |
| plan production edge | `cd infra && make terraform-plan-production-edge` |
| init production dns | `cd infra && make terraform-init-production-dns` |
| plan production dns | `cd infra && make terraform-plan-production-dns` |
| init production control-plane | `cd infra && make terraform-init-production-control-plane` |
| plan production control-plane | `cd infra && make terraform-plan-production-control-plane` |
| generate production inventory | `cd infra && make inventory-production` |

## 6.2 Production Control-Plane Promotion

| Use case | Canonical command |
|---|---|
| promote production release manifest | `cd infra && make control-plane-release-production BACKEND_IMAGE=ghcr.io/<owner>/<repo>/backend@sha256:<digest> WORKER_IMAGE=ghcr.io/<owner>/<repo>/task-worker@sha256:<digest> HELIX_ADAPTER_IMAGE=ghcr.io/<owner>/<repo>/helix-adapter@sha256:<digest> SOURCE_COMMIT=<git-sha>` |
| bootstrap production vault from source file | `cd infra && make control-plane-vault-bootstrap-production SECRETS_SOURCE=/secure/path/control-plane-production.yml` |
| bootstrap and encrypt production vault | `cd infra && make control-plane-vault-bootstrap-production SECRETS_SOURCE=/secure/path/control-plane-production.yml ENCRYPT_VAULT=1 VAULT_PASSWORD_FILE=/secure/path/.vault-pass.txt` |
| rollout production control-plane | `cd infra && make ansible-control-plane-rollout-production` |
| verify production control-plane | `cd infra && make ansible-control-plane-verify-production` |
| backup production control-plane | `cd infra && make ansible-control-plane-backup-production` |
| rollback production control-plane | `cd infra && make ansible-control-plane-rollback-production` |
| restore-drill production control-plane | `cd infra && make ansible-control-plane-restore-drill-production` |

Control-plane promotion rules:

- immutable image digests are mandatory;
- mutable tags such as `latest`, `staging`, or branch tags are not allowed;
- production promotions require approved release governance outside this sheet.

## 6.3 Production Edge Rollouts

| Use case | Canonical command |
|---|---|
| rollout Remnawave across production target group | `cd infra && make ansible-remnawave-rollout-production` |
| verify Remnawave across production target group | `cd infra && make ansible-remnawave-verify-production` |
| rollback Remnawave across production target group | `cd infra && make ansible-remnawave-rollback-production` |
| rollout Helix across production target group | `cd infra && make ansible-helix-rollout-production` |
| verify Helix across production target group | `cd infra && make ansible-helix-verify-production` |
| rollback Helix across production target group | `cd infra && make ansible-helix-rollback-production` |
| rollout Alloy across production target group | `cd infra && make ansible-alloy-rollout-production` |
| verify Alloy across production target group | `cd infra && make ansible-alloy-verify-production` |
| rollback Alloy across production target group | `cd infra && make ansible-alloy-rollback-production` |

## 6.4 Production Canary Rollouts

| Use case | Canonical command |
|---|---|
| Remnawave canary rollout | `cd infra && PROD_REMNAWAVE_CANARY_HOST=<inventory-hostname> make ansible-phase6-remnawave-canary-production` |
| Helix canary rollout | `cd infra && PROD_HELIX_CANARY_HOST=<inventory-hostname> make ansible-phase6-helix-canary-production` |
| Remnawave targeted rollback | `cd infra/ansible && ansible-playbook -i inventories/production playbooks/rollback-remnawave.yml -e remnawave_edge_target_group=remnawave_edge_production --limit "<inventory-hostname>"` |
| Helix targeted rollback | `cd infra/ansible && ansible-playbook -i inventories/production playbooks/rollback-helix.yml -e helix_edge_target_group=helix_edge_production --limit "<inventory-hostname>"` |

These commands are defined by [PRODUCTION_EDGE_CANARY_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md) and remain the canonical production edge widening baseline.

---

## 7. Runtime Parameters That Must Be Resolved Per Window

The repository now stores the base command families. The unresolved items are the exact runtime parameters for the live window.

The fields below must be filled for every production rollout window:

| Parameter class | Examples |
|---|---|
| rollout window identity | `window_id`, approved start time, approved end time |
| named human owners | incident commander, command owner, rollback owner, finance approver, risk approver, support lead |
| immutable image refs | exact `BACKEND_IMAGE`, `WORKER_IMAGE`, `HELIX_ADAPTER_IMAGE` digests |
| secure source paths | exact `SECRETS_SOURCE`, `VAULT_PASSWORD_FILE`, vault id if used |
| canary targets | exact `PROD_REMNAWAVE_CANARY_HOST`, `PROD_HELIX_CANARY_HOST` |
| smoke and reconciliation references | exact evidence pack command links and expected archive paths |
| communication rails | incident channel, finance channel, support channel |

Operational rule:

- a production cutover is blocked if the command family exists but these runtime values are still blank for the named window.

---

## 8. Rollout Window Registration Template

Use the template below for every real production window.

```md
# Production Window Registration

**Window ID:** <window-id>
**Environment:** production
**Lane / Surface / Cutover Units:** <scope>
**Approved Start:** <timestamp>
**Approved End:** <timestamp>
**Command Owner:** <name>
**Incident Commander:** <name>
**Rollback Owner:** <name>
**Finance Approver:** <name or n/a>
**Risk Approver:** <name or n/a>
**Support Lead:** <name>

## Runtime Parameters

- `BACKEND_IMAGE`: <immutable digest or n/a>
- `WORKER_IMAGE`: <immutable digest or n/a>
- `HELIX_ADAPTER_IMAGE`: <immutable digest or n/a>
- `SECRETS_SOURCE`: <secure path or n/a>
- `VAULT_PASSWORD_FILE`: <secure path or n/a>
- `PROD_REMNAWAVE_CANARY_HOST`: <inventory hostname or n/a>
- `PROD_HELIX_CANARY_HOST`: <inventory hostname or n/a>

## Approved Command Set

- terraform and inventory: <link to section 6.1>
- control-plane promotion: <link to section 6.2 or n/a>
- edge rollout family: <link to section 6.3 or 6.4>
- smoke references: <link to rehearsal log or runbook>
- reconciliation references: <link to evidence pack>
- rollback references: <link to section 6.2, 6.3, or 6.4>

## Evidence Links

- rehearsal log: <path>
- archive manifest: <path>
- readiness bundle: <path>
- phase 8 exit evidence: <path>
- sign-off tracker: <path>
```

This registration record may live in the evidence archive for the exact window. It must exist before live command execution starts.

---

## 9. Closure Meaning

This sheet resolves the old ambiguity that production commands were only placeholders.

After this document:

- the base command inventory is explicit for `local`, `staging`, and `production`;
- the cutover runbook no longer needs generic placeholder command stubs;
- `RB-012` still remains open until at least one real production window registration record is filled with runtime values, named owners, and linked signed rehearsal evidence.

Therefore, `RB-012` is not closed by this sheet alone. It becomes signature-ready and execution-ready, but not broad-activation-ready, until the exact live window record is populated and approved.
