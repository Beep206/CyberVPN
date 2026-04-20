# CyberVPN Partner And Admin Backend-Frontend Contract Freeze And DTO/OpenAPI Spec

**Date:** 2026-04-20  
**Status:** Integration closure specification  
**Purpose:** freeze the endpoint inventory, DTO families, error model, idempotency rules, permission expectations, and frontend query contracts for partner portal and admin partner operations integration.

---

## 1. Document Role

This document is the technical contract freeze layer.

It sits below product and workflow documents and above implementation.

It is the reference for:

- backend endpoint shape
- frontend query keys and mutations
- DTO naming
- permission requirements
- cache and invalidation behavior
- error semantics

---

## 2. Contract Principles

1. Backend is the source of truth for all durable partner lifecycle data.
2. DTO names must reflect business objects, not UI tabs.
3. Every mutation must define invalidation rules.
4. Sensitive writes must define idempotency strategy.
5. Permission checks happen server-side.
6. Frontend may use optimistic UI only where explicitly allowed.

---

## 3. Workspace Scoping Rules

Every partner-visible resource is resolved against exactly one of the following scopes:

1. explicit `workspace_id` path parameter
2. active workspace from canonical bootstrap or session context
3. current pre-workspace application shell for pre-activation flows only

## 3.1 General Rules

The following rules are mandatory:

- any mutation that creates durable workspace data must either include `workspace_id` or be valid only before workspace creation exists;
- if an operator belongs to multiple workspaces, endpoints must never silently choose the wrong workspace;
- payout accounts, codes, policy acceptance, notifications, cases, and finance records must never leak across workspaces;
- server-side authorization always checks `workspace_membership + permission_key`.

## 3.2 Specific Scoping Clarifications

### `/api/v1/partner-application-drafts/current`

This endpoint represents:

- the current applicant draft for the current principal before workspace activation;
- or the currently open draft for a specific workspace shell if application persistence already created one.

If a principal may hold multiple drafts in future, the API family must add an explicit selector and must not silently pick one.

### `/api/v1/policy-acceptance/me`

The response must expose enough context to disambiguate scope:

- `workspace_id` where applicable
- `legal_doc_set_id`
- `document_version_id`
- `accepted_by_principal_id`
- `acceptance_scope`

Accepted scope families may include:

- operator-level
- workspace-level
- document-set-level
- action-specific

### `/api/v1/partner-notifications`

If an operator belongs to multiple workspaces, notification feed must be deterministic by one of:

- explicit `workspace_id` filter
- response grouped by workspace
- active workspace context from bootstrap

The chosen behavior must be documented and tested before production.

---

## 4. Endpoint Inventory

## 4.1 Partner Portal Public / Auth

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/auth/partner/register` | `POST` | `PartnerRegistrationRequest`, `PartnerRegistrationResponse` |
| `/api/v1/auth/partner/login` | `POST` | `PartnerLoginRequest`, `PartnerSessionResponse` |
| `/api/v1/auth/partner/logout` | `POST` | `PartnerLogoutResponse` |
| `/api/v1/auth/partner/refresh` | `POST` | `PartnerSessionResponse` |
| `/api/v1/auth/partner/verify-email` | `POST` | `PartnerVerifyEmailRequest`, `PartnerVerifyEmailResponse` |
| `/api/v1/auth/partner/forgot-password` | `POST` | `PartnerForgotPasswordRequest`, `PartnerForgotPasswordResponse` |
| `/api/v1/auth/partner/reset-password` | `POST` | `PartnerResetPasswordRequest`, `PartnerResetPasswordResponse` |
| `/api/v1/auth/partner/mfa/*` | `POST` | `PartnerMfaChallenge*` DTOs |

## 4.2 Partner Session And Workspace Bootstrap

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-session/bootstrap` | `GET` | `PartnerPortalBootstrapResponse` |
| `/api/v1/partner-workspaces/me` | `GET` | `PartnerWorkspaceSummary[]` |
| `/api/v1/partner-workspaces/{workspace_id}` | `GET` | `PartnerWorkspaceDetail` |
| `/api/v1/partner-workspaces/{workspace_id}/programs` | `GET` | `PartnerWorkspaceProgramsResponse` |

## 4.3 Application / Onboarding

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-application-drafts/current` | `GET` | `PartnerApplicationDraft` |
| `/api/v1/partner-application-drafts` | `POST` | `CreatePartnerApplicationDraftRequest`, `PartnerApplicationDraft` |
| `/api/v1/partner-application-drafts/{draft_id}` | `PATCH` | `UpdatePartnerApplicationDraftRequest`, `PartnerApplicationDraft` |
| `/api/v1/partner-application-drafts/{draft_id}/attachments` | `POST` | `CreateApplicationAttachmentRequest`, `ApplicationAttachmentResponse` |
| `/api/v1/partner-application-drafts/{draft_id}/submit` | `POST` | `SubmitPartnerApplicationRequest`, `PartnerWorkspaceApplicationResponse` |
| `/api/v1/partner-application-drafts/{draft_id}/withdraw` | `POST` | `PartnerWorkspaceApplicationResponse` |
| `/api/v1/partner-application-drafts/{draft_id}/resubmit` | `POST` | `PartnerWorkspaceApplicationResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/lane-applications` | `GET`, `POST` | `PartnerLaneApplication*` DTOs |

## 4.4 Organization / Team / Legal / Settings

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-workspaces/{workspace_id}/organization-profile` | `GET`, `PATCH` | `WorkspaceOrganizationProfile` |
| `/api/v1/partner-workspaces/{workspace_id}/members` | `GET`, `POST` | `WorkspaceMember`, `CreateWorkspaceMemberRequest` |
| `/api/v1/partner-workspaces/{workspace_id}/members/{member_id}` | `PATCH` | `UpdateWorkspaceMemberRequest`, `WorkspaceMember` |
| `/api/v1/partner-workspaces/{workspace_id}/invitations` | `GET`, `POST` | `WorkspaceInvitation*` DTOs |
| `/api/v1/partner-workspaces/{workspace_id}/legal-documents` | `GET` | `LegalDocumentSetResponse` |
| `/api/v1/policy-acceptance/me` | `GET` | `PolicyAcceptanceRecord[]` |
| `/api/v1/policy-acceptance` | `POST` | `CreatePolicyAcceptanceRequest`, `PolicyAcceptanceRecord` |
| `/api/v1/partner-operators/me/settings` | `GET`, `PATCH` | `PartnerOperatorSettings` |
| `/api/v1/partner-workspaces/{workspace_id}/preferences` | `GET`, `PATCH` | `WorkspacePreferenceSet` |

## 4.5 Commercial

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-workspaces/{workspace_id}/codes` | `GET` | `PartnerWorkspaceCodeResponse[]` |
| `/api/v1/partner-codes` | `POST`, `PATCH` where enabled | `PartnerCodeWrite*` DTOs |
| `/api/v1/partner-workspaces/{workspace_id}/campaigns` | `GET` | `CampaignCatalogResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/conversion-records` | `GET` | `PartnerWorkspaceConversionRecordResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/conversion-records/{order_id}/explainability` | `GET` | `OrderExplainabilityResponse` |

## 4.6 Finance

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-workspaces/{workspace_id}/statements` | `GET` | `PartnerStatementResponse[]` |
| `/api/v1/partner-payout-accounts` | `GET`, `POST` | `PartnerPayoutAccountResponse`, `CreatePartnerPayoutAccountRequest` |
| `/api/v1/partner-payout-accounts/{id}` | `GET` | `PartnerPayoutAccountResponse` |
| `/api/v1/partner-payout-accounts/{id}/eligibility` | `GET` | `PartnerPayoutAccountEligibilityResponse` |
| `/api/v1/partner-payout-accounts/{id}/make-default` | `POST` | `PartnerPayoutAccountResponse` |
| `/api/v1/payouts/*` | `GET` partner-visible subset | `PayoutExecutionSummary*` DTOs |

## 4.7 Compliance / Risk

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-workspaces/{workspace_id}/traffic-declarations` | `GET`, `POST` | `TrafficDeclarationResponse`, `SubmitPartnerWorkspaceTrafficDeclarationRequest` |
| `/api/v1/partner-workspaces/{workspace_id}/creative-approvals` | `POST` | `CreativeApprovalResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/review-requests` | `GET` | `PartnerWorkspaceReviewRequestResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/review-requests/{id}/responses` | `POST` | `PartnerWorkspaceThreadEventResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/cases` | `GET` | `PartnerWorkspaceCaseResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/cases/{id}/responses` | `POST` | `PartnerWorkspaceThreadEventResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/cases/{id}/ready-for-ops` | `POST` | `PartnerWorkspaceThreadEventResponse` |

## 4.8 Reporting / Integrations

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-workspaces/{workspace_id}/analytics-metrics` | `GET` | `PartnerWorkspaceAnalyticsMetricResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/report-exports` | `GET` | `PartnerWorkspaceReportExportResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/report-exports/{export_id}/schedule` | `POST` | `PartnerWorkspaceReportExportResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/integration-credentials` | `GET` | `PartnerWorkspaceIntegrationCredentialResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/integration-credentials/{kind}/rotate` | `POST` | `RotatePartnerWorkspaceIntegrationCredentialResponse` |
| `/api/v1/partner-workspaces/{workspace_id}/integration-delivery-logs` | `GET` | `PartnerWorkspaceIntegrationDeliveryLogResponse[]` |
| `/api/v1/partner-workspaces/{workspace_id}/postback-readiness` | `GET` | `PartnerWorkspacePostbackReadinessResponse` |

## 4.9 Notifications

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/partner-notifications` | `GET` | `PartnerNotificationFeedResponse` |
| `/api/v1/partner-notifications/counters` | `GET` | `PartnerNotificationCountersResponse` |
| `/api/v1/partner-notifications/{id}/read` | `POST` | `PartnerNotificationReadStateResponse` |
| `/api/v1/partner-notifications/{id}/archive` | `POST` | `PartnerNotificationReadStateResponse` |
| `/api/v1/partner-notifications/preferences` | `GET`, `PATCH` | `PartnerNotificationPreferenceSet` |

## 4.10 Admin Partner Operations

| Endpoint Family | Method(s) | Primary DTOs |
|---|---|---|
| `/api/v1/admin/partner-applications` | `GET` | `AdminPartnerApplicationQueueItem[]` |
| `/api/v1/admin/partner-applications/{id}` | `GET` | `AdminPartnerApplicationDetail` |
| `/api/v1/admin/partner-applications/{id}/request-info` | `POST` | `AdminReviewRequestResponse` |
| `/api/v1/admin/partner-applications/{id}/approve-probation` | `POST` | `PartnerWorkspaceDetail` |
| `/api/v1/admin/partner-applications/{id}/waitlist` | `POST` | `PartnerWorkspaceDetail` |
| `/api/v1/admin/partner-applications/{id}/reject` | `POST` | `PartnerWorkspaceDetail` |
| `/api/v1/admin/partner-workspaces` | `GET` | `AdminPartnerWorkspaceSummary[]` |
| `/api/v1/admin/partner-workspaces/{id}` | `GET`, `PATCH` | `AdminPartnerWorkspaceDetail` |
| `/api/v1/admin/partner-workspaces/{id}/members` | `GET`, `POST`, `PATCH` | `AdminWorkspaceMember*` DTOs |
| `/api/v1/admin/partner-workspaces/{id}/lane-memberships` | `GET`, `POST`, `PATCH` | `AdminLaneMembership*` DTOs |
| `/api/v1/admin/partner-workspaces/{id}/codes` | `GET`, `PATCH` | `AdminPartnerCode*` DTOs |
| `/api/v1/admin/traffic-declarations` | `GET`, `PATCH` | `AdminTrafficDeclaration*` DTOs |
| `/api/v1/admin/creative-approvals` | `GET`, `PATCH` | `AdminCreativeApproval*` DTOs |
| `/api/v1/admin/partner-cases` | `GET`, `PATCH` | `AdminPartnerCase*` DTOs |
| `/api/v1/admin/partner-review-requests` | `GET`, `POST`, `PATCH` | `AdminPartnerReviewRequest*` DTOs |
| `/api/v1/admin/partner-payout-accounts` | `GET`, `PATCH` | `AdminPartnerPayoutAccount*` DTOs |
| `/api/v1/admin/partner-statements` | `GET`, `PATCH` | `AdminPartnerStatement*` DTOs |
| `/api/v1/admin/payouts/instructions` | `GET`, `POST`, `PATCH` | `PayoutInstruction*` DTOs |
| `/api/v1/admin/payouts/executions` | `GET`, `POST`, `PATCH` | `PayoutExecution*` DTOs |
| `/api/v1/admin/governance-actions` | `GET`, `POST` | `GovernanceAction*` DTOs |
| `/api/v1/admin/risk-reviews` | `GET`, `POST`, `PATCH` | `RiskReview*` DTOs |
| `/api/v1/admin/policy-acceptance` | `GET` | `PolicyAcceptanceRecord[]` |
| `/api/v1/admin/audit-log` | `GET` | `AuditLogRecord[]` |

---

## 5. Core DTO Families

## 5.1 Session And Bootstrap

### `PartnerPortalBootstrapResponse`

Must contain:

- principal summary
- realm summary
- active workspace summary
- workspace membership summary
- permission keys
- workspace status
- lane memberships
- readiness overlays
- release ring
- blocked reasons
- counters and pending tasks

### `PartnerWorkspaceSummary`

Must contain:

- `id`
- `display_name`
- `account_key`
- `workspace_status`
- primary lane label
- current membership summary

## 5.2 Application DTOs

### `PartnerApplicationDraft`

Must contain:

- draft id
- workspace shell reference if created
- staged fields
- lane modules
- declaration state
- autosave timestamp
- submission eligibility summary

### `PartnerWorkspaceApplicationResponse`

Must contain:

- workspace id
- current workspace status
- review summary
- pending requests count
- linked lane applications

## 5.3 Workspace Core DTOs

### `WorkspaceOrganizationProfile`

Must contain:

- legal or business identity fields
- public links and domains
- operating geos and languages
- support, finance, and technical contacts

### `WorkspaceMember`

Must contain:

- member id
- actor id
- display name
- email
- role key
- membership status
- invitation status if relevant

### `LegalDocumentSetResponse`

Must contain:

- required documents
- accepted documents
- superseded documents
- current required acceptance tasks

## 5.4 Operational DTOs

### `PartnerWorkspaceCodeResponse`

Must contain:

- code id
- code label
- status
- lane scope
- available actions
- reason for limitation if blocked

### `PartnerWorkspaceConversionRecordResponse`

Must contain:

- order id
- conversion kind
- status
- amount summary
- customer visibility scope
- explainability availability

### `PartnerWorkspaceAnalyticsMetricResponse`

Must contain:

- metric key
- value
- trend if present
- timestamp window

### `PartnerStatementResponse`

Must contain:

- statement id
- settlement period
- status
- totals
- hold/reserve indicators
- payout status summary

### `PartnerPayoutAccountResponse`

Must contain:

- payout account id
- masked destination
- payout rail
- verification status
- approval status
- account status
- default flag

### `TrafficDeclarationResponse`

Must contain:

- declaration id
- kind
- scope label
- approval status
- submitted timestamp
- reviewer decision summary when available

### `PartnerWorkspaceCaseResponse`

Must contain:

- case id
- kind
- status
- subject summary
- available actions
- latest thread event

### `PartnerNotificationFeedResponse`

Must contain:

- list of notifications
- unread count
- action-required count
- paging metadata

---

## 6. Error Model

| Error Code | HTTP | Meaning | Typical Consumer Handling |
|---|---|---|---|
| `FORBIDDEN_REALM` | `403` | wrong realm for this route | redirect to correct host or login |
| `INVALID_AUDIENCE` | `401` | token audience mismatch | logout and re-auth |
| `WORKSPACE_NOT_FOUND` | `404` | workspace missing or not visible | show not found |
| `WORKSPACE_MEMBERSHIP_REQUIRED` | `403` | authenticated but no membership | access denied screen |
| `PERMISSION_DENIED` | `403` | missing permission key | route read-only or block |
| `APPLICATION_LOCKED` | `409` | application cannot be edited in current state | show lock message |
| `POLICY_VERSION_EXPIRED` | `409` | action blocked until policy acceptance updated | route to `/legal` |
| `PAYOUT_BLOCKED` | `409` | finance action blocked by readiness or governance | show finance blocker |
| `RISK_REVIEW_REQUIRED` | `409` | action held pending risk review | show governance blocker |
| `LEGAL_ACCEPTANCE_REQUIRED` | `409` | legal acceptance required before action | route to `/legal` |
| `EVIDENCE_REQUIRED` | `409` | more evidence needed | route to `/application` or `/cases` |
| `RATE_LIMITED` | `429` | rate limit exceeded | retry with backoff |

---

## 7. Idempotency Rules

Idempotency keys are required for:

- application submit
- lane application submit
- payout account create
- credential rotation
- export scheduling
- review response creation if duplicate browser submits are plausible
- case reply creation if duplicate browser submits are plausible
- approve probation
- reject application
- waitlist application
- approve or decline lane
- suspend or revoke code
- payout maker-checker approval actions
- governance action application

Idempotency keys are recommended for:

- invite creation
- notification bulk actions

---

## 8. Audit Event Name Mapping

The following audit event names should be treated as canonical defaults for implementation and tests:

| Mutation Or Action | Audit Event Name |
|---|---|
| application submit | `partner_application.submitted` |
| request more info | `partner_application.info_requested` |
| approve probation | `partner_workspace.approved_probation` |
| waitlist application | `partner_workspace.waitlisted` |
| reject application | `partner_workspace.rejected` |
| lane approval | `partner_lane.approved` |
| lane decline | `partner_lane.declined` |
| code suspension | `partner_code.suspended` |
| payout account verification | `partner_payout_account.verified` |
| payout execution approval | `partner_payout.execution_approved` |
| governance action apply | `partner_governance.action_applied` |
| policy acceptance create | `partner_policy.accepted` |

---

## 9. Frontend Query Model

## 9.1 Required Query Keys

Suggested canonical query key families:

- `['partner-session', 'bootstrap']`
- `['partner-workspaces', 'me']`
- `['partner-workspace', workspaceId]`
- `['partner-workspace', workspaceId, 'programs']`
- `['partner-workspace', workspaceId, 'application']`
- `['partner-workspace', workspaceId, 'organization']`
- `['partner-workspace', workspaceId, 'members']`
- `['partner-workspace', workspaceId, 'legal']`
- `['partner-workspace', workspaceId, 'codes']`
- `['partner-workspace', workspaceId, 'campaigns']`
- `['partner-workspace', workspaceId, 'conversions']`
- `['partner-workspace', workspaceId, 'analytics']`
- `['partner-workspace', workspaceId, 'report-exports']`
- `['partner-workspace', workspaceId, 'statements']`
- `['partner-workspace', workspaceId, 'payout-accounts']`
- `['partner-workspace', workspaceId, 'traffic-declarations']`
- `['partner-workspace', workspaceId, 'cases']`
- `['partner-workspace', workspaceId, 'review-requests']`
- `['partner-workspace', workspaceId, 'integrations']`
- `['partner-workspace', workspaceId, 'integration-delivery-logs']`
- `['partner-notifications']`
- `['partner-notification-counters']`
- `['partner-settings']`

## 9.2 Mutation And Invalidation Rules

| Mutation | Invalidate |
|---|---|
| application draft update | application draft only |
| application submit | bootstrap, application, workspaces, review requests |
| organization update | organization, bootstrap |
| add member | members, workspace detail |
| policy acceptance | legal, bootstrap, blocked-action surfaces |
| code create/update | codes, dashboard bootstrap if counters affected |
| traffic declaration submit | traffic declarations, compliance tasks |
| creative approval submit | traffic declarations, campaigns |
| case reply | cases, review requests, notifications counters |
| report export schedule | report exports |
| payout account create | payout accounts, finance summary, bootstrap if readiness changes |
| mark notification read | notifications, notification counters |

## 9.3 Optimistic Update Policy

Allowed:

- mark notification read
- archive notification
- case reply text reset after success
- export schedule UI feedback

Not allowed:

- workspace status
- lane status
- permission keys
- payout eligibility
- legal acceptance requirement state

---

## 10. Closure Conditions

This document is complete only when:

1. partner portal and admin portal teams can implement against one contract inventory;
2. each mutation has invalidation and idempotency rules;
3. error semantics are frozen enough for UI handling;
4. DTO families are explicit enough to generate or validate OpenAPI types without guesswork.
