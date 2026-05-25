# Stage 3 Partner Domain Model And Role Contract

**Stage:** `S3-STAGE-02`
**Status:** Approved domain and role baseline
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-01: S3 Scope, Backlog, And Decision Freeze`

---

## 1. Purpose

This document freezes the partner domain model and role contract before Stage 3 implementation continues into event backbone, partner portal, storefront, attribution, reporting or finance flows.

The goal is to make one thing unambiguous: a CyberVPN partner is a governed workspace with its own operators, roles, permissions, status lifecycle, legal acceptance, audit trail and finance boundary. A partner is not a normal customer account with an extra flag.

---

## 2. Authoritative Code Facts

The current monorepo already contains a partner foundation. S3 implementation must build on it instead of inventing a parallel model.

| Area | Current source |
|---|---|
| Partner account/workspace entity | `backend/src/domain/entities/partner.py` |
| Partner account ORM | `backend/src/infrastructure/database/models/partner_model.py` |
| Partner membership entity | `backend/src/domain/entities/partner_account_user.py` |
| Partner membership ORM | `backend/src/infrastructure/database/models/partner_account_user_model.py` |
| Partner roles and builtin role catalog | `backend/src/domain/entities/partner_role.py` |
| Partner permissions | `backend/src/domain/entities/partner_permission.py` |
| Partner workspace dependency/RBAC check | `backend/src/presentation/dependencies/partner_workspace.py` |
| Auth realms | `backend/src/domain/entities/auth_realm.py` |
| Partner application workflow | `backend/src/application/use_cases/partners/partner_applications.py` |
| Partner application/API schemas | `backend/src/presentation/api/v1/partners/schemas.py` |
| Partner payout accounts/statements | `backend/src/application/use_cases/settlement/` |
| Partner event contracts | `backend/src/application/events/README_partner_platform.md` |

Current production snapshot during this stage:

```text
partner_accounts=0
partner_account_users=0
auth_realms=admin, customer, partner, service
PARTNER_EVENT_BACKBONE_ENABLED=false
```

Interpretation:

- no production partner workspace is active yet;
- no production partner operator is active yet;
- the partner realm exists;
- production partner runtime stays disabled until later S3 gates.

---

## 3. Canonical Principal And Realm Model

CyberVPN must preserve these principal classes:

| Principal class | Meaning | S3 rule |
|---|---|---|
| `customer` | B2C buyer and VPN user | Cannot automatically become partner operator. |
| `partner_operator` | External partner workspace user | Operates only inside assigned partner workspace and role. |
| `admin` | Internal CyberVPN staff | May override only through internal-admin paths with audit. |
| `service` | Automation or machine actor | No human workspace authority. |

Canonical auth realms:

| Realm key | Realm type | Audience | Cookie namespace |
|---|---|---|---|
| `customer` | `customer` | `cybervpn:customer` | `customer` |
| `partner` | `partner` | `cybervpn:partner` | `partner` |
| `admin` | `admin` | `cybervpn:admin` | `admin` |
| `service` | `service` | `cybervpn:service` | `service` |

Rules:

1. Customer, partner, admin and service sessions must not be interchangeable.
2. Partner APIs must reject customer tokens even if the human email matches.
3. Admin APIs must not accept partner tokens.
4. Partner operators use partner realm/audience.
5. Internal admin override is allowed only for internal support/admin routes and must be audited.
6. `legacy_owner_user_id` and `mobile_users.partner_account_id` are transitional compatibility links only. They are not the S3 partner operator model.

---

## 4. Canonical Partner Workspace Model

The canonical S3 workspace root is `partner_accounts`.

| Field | Meaning | S3 contract |
|---|---|---|
| `id` | Stable workspace identifier | Primary workspace key for partner-scoped data. |
| `account_key` | Human/stable workspace slug | Unique, URL/API-safe, not a secret. |
| `display_name` | Partner-facing workspace name | Mutable with audit. |
| `status` | Workspace lifecycle state | Drives UI, access, finance and support gates. |
| `legacy_owner_user_id` | Transitional customer link | Do not rely on it for S3 partner operator access. |
| `created_by_admin_user_id` | Internal creator | Audit/provenance only. |

The canonical membership table is `partner_account_users`.

| Field | Meaning | S3 contract |
|---|---|---|
| `partner_account_id` | Workspace scope | Required for every external partner operator. |
| `admin_user_id` | Operator principal row | Current implementation uses `admin_users` for partner operators under partner realm semantics. |
| `role_id` | Partner role | Must resolve to `partner_account_roles`. |
| `membership_status` | Membership lifecycle | Only `active` membership grants access. |
| `invited_by_admin_user_id` | Inviter/provenance | Must be preserved for audit. |

Unique rule:

```text
one partner_account_id + one admin_user_id = at most one membership
```

This prevents duplicate role ambiguity inside one workspace.

---

## 5. Partner Workspace Status Lifecycle

Canonical workspace statuses:

| Status | Meaning | External access |
|---|---|---|
| `draft` | Application/workspace draft started | Limited application access only. |
| `email_verified` | Applicant email verified | Application can be completed/submitted. |
| `submitted` | Application submitted | Read/status access; no production commercial privileges. |
| `under_review` | Internal review in progress | Read/status access; requested-info handling if needed. |
| `needs_info` | More data required | Applicant can respond. |
| `waitlisted` | Valid but not accepted yet | No production commercial privileges. |
| `approved_probation` | Approved for probation | Limited partner pilot capabilities only. |
| `active` | Fully active workspace | Required for broad partner operations. |
| `restricted` | Active but constrained | Access and finance functions limited. |
| `suspended` | Temporarily blocked | No commercial operation. |
| `rejected` | Application declined | No commercial operation. |
| `terminated` | Relationship ended | No operation; historical reporting only if policy allows. |
| `disabled` | System or owner disabled | No operation. |

Rules:

1. `approved_probation` may be used for controlled pilot.
2. Real payout execution requires `active`, not only `approved_probation`.
3. `restricted`, `suspended`, `terminated`, `disabled` must block commercial operations.
4. Status transitions must write workflow/audit events.
5. Status changes must not silently change role permissions.

---

## 6. Partner Lane Contract

Stage 3 revenue lanes:

| Canonical lane | Application/API key | S3 meaning |
|---|---|---|
| Creator / Affiliate | `creator_affiliate` | Creator, content, SEO, communities, reviews. |
| Performance / Media Buyer | `performance_media` | Paid traffic partners with stricter approval and quality gates. |
| Reseller / API / Distribution | `reseller_api` | Partner-owned storefront/API/distribution flows. |

The codebase also contains broader pilot enum names:

| Broader enum | S3 mapping |
|---|---|
| `creator_affiliate` | `creator_affiliate` |
| `performance_media_buyer` | `performance_media` |
| `reseller_distribution` | `reseller_api` |

Rules:

1. Do not rename public application/API lane keys during S3 without migration and frontend/API evidence.
2. Lane membership does not bypass workspace status.
3. Role permission does not bypass lane status.
4. Reseller storefront capabilities require `reseller_api` lane approval plus S3 storefront gates.
5. Performance postback capabilities require `performance_media` lane approval plus traffic/compliance gates.

---

## 7. Canonical Role Contract

The implementation role keys are the source of truth for backend RBAC. Product/UI may display friendlier names.

| Product role | Backend role key | S3 status | Purpose |
|---|---|---|---|
| Workspace Owner | `owner` | Required | Ultimate partner-side authority, legal acceptance, team authority. |
| Workspace Admin / Manager | `manager` | Required | Delegated workspace operations and member/code management. |
| Finance Manager | `finance` | Required | Finance readiness, statements, payout account visibility/write where allowed. |
| Analyst | `analyst` | Required | Read-only performance, reporting and analytics. |
| Traffic Manager | `traffic_manager` | Required | Codes, links, campaigns, traffic declarations and integrations where allowed. |
| Support Manager | `support_manager` | Required | Workspace support visibility and support workflow actions. |
| Technical Manager | `technical_manager` | Required for integrations | API/reporting tokens, postbacks, webhooks and diagnostics. |
| Legal / Compliance Manager | not yet a backend role key | Modelled, not enabled for pilot | Legal/compliance can be represented by owner/manager until a dedicated role is implemented. |

Role rules:

1. `owner` is the only external role allowed to hold full workspace authority.
2. `manager` must not execute internal-only finance/governance actions.
3. `finance` may manage payout account readiness but cannot approve or execute internal payout release.
4. `analyst` is read-only.
5. `traffic_manager` must not gain payout write authority.
6. `support_manager` must not gain payout, token or ownership controls.
7. `technical_manager` must not gain payout or legal acceptance authority by default.
8. A future `legal_compliance_manager` role requires explicit S3 evidence before production enablement.

---

## 8. Permission Contract

Canonical backend permission keys:

| Permission | Meaning | Sensitive |
|---|---|---|
| `workspace_read` | Read workspace state | No |
| `operations_write` | Perform allowed workspace workflow actions | Yes |
| `membership_read` | Read team/membership | No |
| `membership_write` | Invite/change members and roles | Yes |
| `codes_read` | Read codes and link data | No |
| `codes_write` | Create/update/suspend codes where allowed | Yes |
| `earnings_read` | Read earnings/reporting data | Yes |
| `payouts_read` | Read payout/statement/account data | Yes |
| `payouts_write` | Manage payout account readiness | High |
| `traffic_read` | Read traffic/campaign declarations | No |
| `traffic_write` | Submit/update traffic declarations and related config | Yes |
| `integrations_read` | Read integration config/status | Yes |
| `integrations_write` | Manage webhooks, postbacks, tokens or integration settings | High |

Sensitive action rules:

1. `payouts_write` does not mean payout execution.
2. Payout execution remains internal-only until `S3-STAGE-11`, `S3-STAGE-14`, `S3-STAGE-15` and `S3-STAGE-17` gates pass.
3. `membership_write`, `payouts_write`, `integrations_write`, `codes_write` and `traffic_write` require audit events.
4. External roles cannot approve their own lane, release holds, approve payouts, change reserves, override attribution or suppress risk flags.
5. Internal admin override must be visible in audit/support evidence.

---

## 9. Required Role Permission Matrix

This is the S3 contract. Backend, admin UI, partner UI and tests must align to it before production partner runtime is enabled.

| Backend role key | Required permissions |
|---|---|
| `owner` | all canonical partner permissions |
| `manager` | `workspace_read`, `operations_write`, `membership_read`, `membership_write`, `codes_read`, `codes_write`, `earnings_read`, `traffic_read`, `traffic_write`, `integrations_read` |
| `finance` | `workspace_read`, `operations_write`, `membership_read`, `earnings_read`, `payouts_read`, `payouts_write` |
| `analyst` | `workspace_read`, `codes_read`, `earnings_read`, `traffic_read`, `integrations_read` |
| `traffic_manager` | `workspace_read`, `operations_write`, `codes_read`, `codes_write`, `traffic_read`, `traffic_write`, `integrations_read`, `integrations_write` |
| `support_manager` | `workspace_read`, `operations_write`, `membership_read` |
| `technical_manager` | `workspace_read`, `traffic_read`, `traffic_write`, `integrations_read`, `integrations_write` |

Production reconciliation:

- production role rows were reconciled on 2026-05-24 through the backend `ensure_builtin_roles()` code path;
- a fresh PostgreSQL backup was captured first at `/srv/cybervpn/backups/s3-stage02-role-seed-20260524T155729Z`;
- production still has zero partner accounts and zero partner account users;
- post-reconciliation production role rows match this matrix;
- if the builtin role contract changes later, role seed reconciliation must be repeated before the next production partner runtime gate.

---

## 10. Legal, Profile And Finance Boundaries

Partner workspace profile is required for S3 readiness:

| Profile field group | Examples | Required before pilot |
|---|---|---|
| Identity | workspace name, website, country | Yes |
| Contacts | primary, support, technical, finance contacts | Yes |
| Business | description, acquisition channels, operating regions, languages | Yes |
| Security | require MFA, active-session review, passkey preference | Yes for high-risk lanes |
| Finance | preferred currency, payout readiness | Yes before payout sandbox/pilot |

Partner legal acceptance is required before active commercial operation:

```text
partner_account_id + document_kind + document_version
```

Rules:

1. Legal acceptance belongs to a workspace, not to a vague user session.
2. Legal acceptance must record the accepting operator.
3. Payout account write/read must remain separate from payout execution.
4. Finance operations require support/admin visibility and audit trail.

---

## 11. API And UI Contract

Backend, partner frontend and admin/support UI must use the same domain language.

| Concept | Canonical term |
|---|---|
| Workspace root | `partner_account` / partner workspace |
| Workspace operator | partner operator |
| Workspace membership | `partner_account_user` |
| Role key | `owner`, `manager`, `finance`, `analyst`, `traffic_manager`, `support_manager`, `technical_manager` |
| Workspace status | `draft`, `email_verified`, `submitted`, `under_review`, `needs_info`, `waitlisted`, `approved_probation`, `active`, `restricted`, `suspended`, `rejected`, `terminated`, `disabled` |
| Lane keys | `creator_affiliate`, `performance_media`, `reseller_api` |
| Realm key | `partner` |
| Token audience | `cybervpn:partner` |

UI copy may translate names, but API contracts must stay stable.

---

## 12. Security Invariants

S3 must preserve these invariants:

1. Partner operator cannot access another workspace by guessing `workspace_id`.
2. Customer token cannot access partner workspace APIs.
3. Partner token cannot access admin-only APIs.
4. Internal admin override cannot be invisible.
5. Finance role cannot approve internal payout execution.
6. Traffic role cannot read or change payout destination.
7. Analyst role cannot mutate codes, traffic, members or payout data.
8. Support role cannot read integration secrets or payout destination secrets.
9. Integration credentials and tokens must not be rendered in logs or exports.
10. Role changes must be auditable and reversible.

---

## 13. Exit Criteria

`S3-STAGE-02` is complete when:

1. partner workspace is frozen as `partner_accounts`;
2. partner operator membership is frozen as `partner_account_users`;
3. auth realm boundary is frozen as `partner` realm and `cybervpn:partner` audience;
4. workspace statuses are frozen;
5. lane keys are frozen;
6. role keys and required permissions are frozen;
7. finance/payout authority is separated from payout execution;
8. legal/profile requirements are frozen;
9. API/UI vocabulary is frozen;
10. production role seed reconciliation is complete for the current role matrix;
11. no production partner runtime is enabled by this stage.

---

## 14. Next Stage

After this contract, proceed to:

```text
S3-STAGE-03: Non-Prod Event Backbone Topology
```

Do not start `S3-STAGE-04: Outbox Dispatcher And Consumer Proof` until the non-production event backbone topology is selected and proven.
