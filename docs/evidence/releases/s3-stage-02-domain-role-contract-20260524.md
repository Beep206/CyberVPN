# S3-STAGE-02 Partner Domain Model And Role Contract Evidence

**Stage:** `S3-STAGE-02: Partner Domain Model And Role Contract`
**Date:** 2026-05-24
**Decision:** `APPROVED_DOMAIN_ROLE_BASELINE`
**Prior gate:** `S3-STAGE-01: S3 Scope, Backlog, And Decision Freeze`

---

## 1. Summary

The Stage 3 partner domain and role contract is frozen.

This stage does not enable production partner runtime. It defines the model S3 implementation must follow:

- partner workspace root: `partner_accounts`;
- partner operator membership: `partner_account_users`;
- partner realm: `partner`;
- token audience: `cybervpn:partner`;
- role keys: `owner`, `manager`, `finance`, `analyst`, `traffic_manager`, `support_manager`, `technical_manager`;
- external pilot roles are separated from internal admin/finance approval;
- production partner runtime remains disabled until later gates.

---

## 2. Files Reviewed

Reviewed code:

- `backend/src/domain/entities/partner.py`
- `backend/src/domain/entities/partner_account_user.py`
- `backend/src/domain/entities/partner_role.py`
- `backend/src/domain/entities/partner_permission.py`
- `backend/src/domain/entities/auth_realm.py`
- `backend/src/infrastructure/database/models/partner_model.py`
- `backend/src/infrastructure/database/models/partner_account_user_model.py`
- `backend/src/infrastructure/database/models/partner_role_model.py`
- `backend/src/infrastructure/database/repositories/partner_account_repository.py`
- `backend/src/presentation/dependencies/partner_workspace.py`
- `backend/src/application/use_cases/partners/partner_applications.py`
- `backend/src/presentation/api/v1/partners/schemas.py`
- `backend/alembic/versions/20260417_phase1_partner_workspace.py`
- `backend/alembic/versions/20260420_phase10_partner_workspace_core.py`

Reviewed docs:

- `docs/cybervpn_stage3_launch_docs/01_STAGE3_SCOPE_BACKLOG_FREEZE.md`
- `docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md`
- `docs/plans/2026-04-17-partner-platform-rulebook.md`
- `docs/plans/2026-04-17-partner-platform-target-state-architecture.md`
- `docs/plans/2026-04-18-partner-portal-prd.md`
- `docs/plans/2026-04-18-partner-portal-role-matrix.md`

Created:

- `docs/cybervpn_stage3_launch_docs/02_STAGE3_PARTNER_DOMAIN_ROLE_CONTRACT.md`
- `docs/evidence/releases/s3-stage-02-domain-role-contract-20260524.md`

Updated:

- `docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md`

---

## 3. Production Snapshot

Observed on `prod-app-1`:

```text
partner_accounts=0
partner_account_users=0
auth_realms=admin:admin:cybervpn:admin,customer:customer:cybervpn:customer,partner:partner:cybervpn:partner,service:service:cybervpn:service
```

Production role seed snapshot before reconciliation:

```text
partner_roles=analyst:4,finance:4,manager:6,owner:8,support_manager:2,traffic_manager:4
```

Interpretation:

- production has no active partner workspaces or partner operators yet;
- partner realm exists;
- current production role rows were older seed rows before this stage's reconciliation;
- this is not a current customer runtime risk because production partner runtime is disabled and no partner users exist.

---

## 4. Contract Decisions

| Area | Decision |
|---|---|
| Workspace root | `partner_accounts` |
| Partner operator membership | `partner_account_users` |
| Operator principal storage | Current implementation uses `admin_users` under partner realm semantics |
| Customer compatibility link | `legacy_owner_user_id` and `mobile_users.partner_account_id` only transitional |
| Partner realm | `partner` |
| Partner audience | `cybervpn:partner` |
| Workspace statuses | frozen in `PartnerAccountStatus` |
| Membership statuses | `active`, `invited`, `suspended`, `revoked` |
| Application lane keys | `creator_affiliate`, `performance_media`, `reseller_api` |
| Finance boundary | payout readiness/write is not payout execution |
| Internal override | allowed only for internal admin/support paths with audit |

---

## 5. Exit Criteria Check

| Exit Criteria | Result |
|---|---|
| Partner workspace model frozen | Passed |
| Partner membership model frozen | Passed |
| Realm/audience boundary frozen | Passed |
| Workspace statuses frozen | Passed |
| Lane keys frozen | Passed |
| Role keys and required permissions frozen | Passed |
| Finance/payout authority separated from execution | Passed |
| Legal/profile requirements frozen | Passed |
| API/UI vocabulary frozen | Passed |
| Production role seed reconciliation completed for current role matrix | Passed |
| Production partner runtime remains disabled | Passed |

---

## 6. Production Role Seed Reconciliation

A fresh production backup was captured before the mutation:

```text
backup_dir=/srv/cybervpn/backups/s3-stage02-role-seed-20260524T155729Z
cybervpn_dump=/srv/cybervpn/backups/s3-stage02-role-seed-20260524T155729Z/cybervpn-20260524T155729Z.dump
cybervpn_table_count=121
status=ok
```

Reconciliation was executed through the backend code path:

```text
PartnerAccountRepository.ensure_builtin_roles()
```

Before:

```text
analyst:4
finance:4
manager:6
owner:8
support_manager:2
technical_manager=missing
traffic_manager:4
partner_accounts=0
partner_account_users=0
```

After:

```text
analyst:5
finance:6
manager:10
owner:13
support_manager:3
technical_manager:5
traffic_manager:8
partner_accounts=0
partner_account_users=0
mismatched_after=[]
```

Public/customer runtime check after reconciliation:

```text
https://api.cyber-vpn.net/health             http=200
https://cyber-vpn.net/ru-RU                  http=200
https://cyber-vpn.net/ru-RU/miniapp/home     http=200
https://admin.cyber-vpn.net/ru-RU/login      http=200
```

All app containers remained `running healthy`.

Decision:

```text
PRODUCTION_ROLE_SEED_RECONCILED
```

This closes the S3-STAGE-02 production role seed tail for the current role matrix. If the role matrix changes later, repeat this reconciliation with fresh backup/evidence before enabling production partner runtime.

---

## 7. Next Stage

Proceed to:

```text
S3-STAGE-03: Non-Prod Event Backbone Topology
```
