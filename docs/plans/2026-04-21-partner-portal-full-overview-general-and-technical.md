# CyberVPN Partner Portal Full Overview: General And Technical

**Date:** 2026-04-21  
**Status:** Canonical overview  
**Purpose:** explain in one document how the CyberVPN partner portal works in plain product language and how it is implemented technically.  
**Audience:** product, frontend, backend, admin-ops, support, QA, rollout owners.

---

## 1. Executive Summary

CyberVPN partner portal is not a small affiliate cabinet and not a customer referral screen. It is a separate external operating portal for partner organizations.

Its job is to let a partner organization:

- apply to join the partner program;
- pass review and compliance checks;
- operate one or more approved partner lanes;
- work with codes, campaigns, traffic, conversions and analytics;
- handle finance readiness, statements and payout setup;
- receive restrictions, reviews, requests and notifications;
- communicate with admin/support through cases and review loops;
- do all of this inside a separate partner workspace and separate partner realm.

In practical terms, the portal covers the full partner lifecycle:

`application -> review -> probation -> activation -> tracking -> reporting -> settlement -> governance`

This is why the portal is modeled as a separate `partner` surface, not as an extension of the consumer dashboard and not as an internal admin tool.

---

## 2. What The Portal Is

At the product level, the partner portal is:

- a separate partner-facing workspace surface;
- a governed operating environment for external partners;
- lane-aware, role-aware and status-aware;
- backed by canonical backend state, not by frontend-only simulation;
- connected to admin review and operations workflows;
- connected to finance, compliance, risk, notification and support flows.

The portal is designed for several partner models:

- `Creator / Affiliate`
- `Performance / Media Buyer`
- `Reseller / API / Distribution`

The portal is not the same thing for all of them. Some areas are shared, but capabilities, restrictions and review depth depend on lane, role and readiness.

---

## 3. What The Portal Is Not

The partner portal is explicitly not:

- the customer dashboard;
- the storefront;
- the admin portal;
- a consumer referral screen;
- an internal finance console;
- a raw fraud-search or global moderation surface.

Things intentionally excluded from the partner portal:

- invite / gift / consumer referral mechanics;
- internal maker-checker approval screens;
- global admin moderation queues;
- global fraud search across all partners;
- raw reserve controls and internal settlement overrides;
- unrestricted operational tools that belong only to internal staff.

This separation is important because it keeps product semantics clean:

- customer actions stay in customer surfaces;
- partner operations stay in the partner portal;
- internal control and approvals stay in admin.

---

## 4. Core Product Model

The portal is built around several different units of state.

### 4.1 Workspace

The primary unit of access is a `partner workspace`.

A workspace represents the partner organization or operating unit. It has:

- identity;
- status;
- members;
- permissions;
- organization profile;
- legal acceptance state;
- finance and compliance readiness;
- partner programs and assets.

The portal does not treat a consumer account as the main operating object. Even if a current user becomes a partner, the partner experience is modeled through a separate partner workspace.

### 4.2 Lane

A workspace can participate in one or more partner lanes:

- creator / affiliate lane;
- performance / media buying lane;
- reseller / API lane.

Each lane has:

- its own application requirements;
- its own approval state;
- its own restrictions;
- its own capabilities;
- its own compliance posture.

### 4.3 Code

Codes and tracking objects have their own lifecycle and do not automatically inherit full authority from workspace approval.

In other words:

- workspace approval is not the same as lane approval;
- lane approval is not the same as code activation.

### 4.4 Readiness Overlays

Even with an approved workspace, partner capability can still be limited by operational overlays:

- finance readiness;
- compliance readiness;
- technical readiness;
- governance state;
- release ring.

This is why the portal is not controlled by one status field. It is controlled by a composed runtime view.

---

## 5. Status Model

The portal exposes several status layers.

### 5.1 Workspace Lifecycle

The visible workspace lifecycle includes:

- `draft`
- `email_verified`
- `submitted`
- `needs_info`
- `under_review`
- `waitlisted`
- `approved_probation`
- `active`
- `restricted`
- `suspended`
- `rejected`
- `terminated`

These are the statuses the portal user can reason about. Internally, implementation may split some of this into application and operational states, but the portal works from a unified lifecycle view.

### 5.2 Lane Lifecycle

Lane lifecycle includes:

- `not_applied`
- `pending`
- `approved_probation`
- `approved_active`
- `declined`
- `paused`
- `suspended`
- `terminated`

### 5.3 Code Lifecycle

Code lifecycle includes:

- `draft`
- `pending_approval`
- `active`
- `paused`
- `revoked`
- `expired`

### 5.4 Readiness And Restriction State

On top of statuses, the portal evaluates:

- `finance_readiness`
- `compliance_readiness`
- `technical_readiness`
- `governance_state`
- `blocked_reasons`
- `pending_tasks`

This is what makes the portal state-aware instead of just menu-driven.

---

## 6. Roles And Access Model

The partner portal supports external workspace roles. The main role set includes:

- `workspace_owner`
- `workspace_admin`
- `finance_manager`
- `analyst`
- `traffic_manager`
- `support_manager`
- `technical_manager`
- `legal_compliance_manager`

Access is not decided only by role. Final visibility and mutability depend on:

- partner realm;
- session audience;
- principal class;
- workspace membership;
- permission keys;
- workspace status;
- lane state;
- readiness overlays;
- release ring.

This means:

- role answers "what kind of person is this?";
- workspace and lane state answer "what stage is this workspace in?";
- readiness and governance answer "what is currently allowed or blocked?".

Frontend route guards exist for UX, but the real security boundary is backend authorization.

---

## 7. Main Portal Sections

The canonical partner information architecture is:

1. `Dashboard`
2. `Application`
3. `Organization`
4. `Team`
5. `Programs`
6. `Legal`
7. `Codes`
8. `Campaigns`
9. `Conversions`
10. `Analytics`
11. `Finance`
12. `Compliance`
13. `Integrations`
14. `Cases`
15. `Notifications`
16. `Settings`
17. `Reseller`

### 7.1 Dashboard

The dashboard is the operating summary of the current workspace. It shows:

- current workspace state;
- pending tasks;
- blocked reasons;
- readiness posture;
- counters and operational signals;
- visible modules for the current status and role.

### 7.2 Application

This is the entry point for self-serve onboarding. It handles:

- application draft;
- staged onboarding data;
- evidence upload;
- submit / withdraw / resubmit;
- review-loop feedback.

### 7.3 Organization

This section stores partner organization truth:

- business identity;
- contacts;
- regions and languages;
- operating profile;
- business description;
- channel footprint.

### 7.4 Team

This section handles workspace membership:

- members;
- roles;
- permissions;
- invitations and acceptance state.

### 7.5 Programs

This is where the workspace sees partner programs and lane participation:

- active or available programs;
- lane applications;
- lane approval state;
- probation vs active program posture.

### 7.6 Legal

This section handles partner-facing legal and policy documents:

- document sets;
- acceptance requirements;
- accepted versions;
- legal tasks that block operations.

### 7.7 Codes

This is the codes and tracking area:

- partner codes;
- activation or pause state;
- tracking posture;
- code restrictions and explainability.

### 7.8 Campaigns

This is the enablement and asset surface:

- campaign assets;
- creative material;
- approval requests where needed;
- lane-specific enablement.

### 7.9 Conversions

This is the operational conversion view:

- attributed conversions;
- order-level context;
- customer or storefront scope where allowed;
- explainability around why a conversion is or is not attributed.

### 7.10 Analytics

This is the reporting surface:

- operational metrics;
- conversion and performance views;
- exports;
- status-aware reporting availability.

### 7.11 Finance

This section handles partner-visible settlement posture:

- statements;
- payout accounts;
- payout eligibility;
- payout history;
- settlement restrictions;
- finance readiness.

The partner portal shows the partner-facing finance state, not the internal payout execution console.

### 7.12 Compliance

This section handles partner-visible compliance and risk tasks:

- traffic declarations;
- creative approvals;
- review requests;
- restrictions;
- governance posture relevant to the workspace.

### 7.13 Integrations

This is the technical integration surface:

- API access;
- tokens or credentials where allowed;
- postback posture;
- delivery logs;
- integration health signals.

### 7.14 Cases

This is the partner support and dispute surface:

- partner-created cases;
- review-related cases;
- payout or attribution disputes;
- request/response threads with admin or support.

### 7.15 Notifications

This is the event-driven inbox:

- application events;
- legal tasks;
- payout and statement events;
- review actions;
- compliance events;
- case updates.

### 7.16 Settings

This is workspace and operator settings:

- profile-level settings;
- preferences;
- security baseline;
- session and identity context.

### 7.17 Reseller

This section is only for reseller/API lane behavior. It shows reseller-specific operating state:

- storefront or distribution scope;
- commercial posture;
- customer and support ownership view;
- reseller-specific technical context.

---

## 8. Main Business Workflows

### 8.1 Registration And Entry

The portal supports three entry patterns:

1. public self-serve apply;
2. invite-only onboarding;
3. upgrade request from an existing CyberVPN user.

In every case, self-serve applies only to entering the funnel. It does not imply instant activation.

### 8.2 Application Workflow

The partner application flow is:

1. create account in partner realm;
2. verify email and security baseline;
3. create or open partner workspace draft;
4. fill staged onboarding information;
5. upload evidence if needed;
6. submit application;
7. move into review.

If review needs more information:

1. admin requests additional information;
2. applicant sees `needs_info`;
3. applicant updates the draft and uploads new evidence;
4. applicant resubmits.

### 8.3 Review Workflow

The review workflow is governed, not automatic.

Possible outcomes include:

- approve to probation;
- approve to active where policy allows;
- request more information;
- waitlist;
- reject.

The partner sees this as a managed lifecycle, not as a black-box admin decision.

### 8.4 Probation And Activation

Probation is a controlled operating state. It means:

- the partner is allowed into real operations;
- not all capabilities are open yet;
- finance, compliance, code and traffic posture may still be limited;
- the workspace can accumulate evidence of normal behavior before full activation.

Activation does not simply mean "portal unlocked". It means:

- workspace status is upgraded;
- lane status may change;
- finance readiness may change;
- code and campaign operations may expand;
- reporting and payout posture may broaden.

### 8.5 Daily Partner Operations

Once active or approved to probation, the partner uses the portal for:

- program participation;
- code operations;
- campaigns and asset usage;
- conversion and analytics review;
- finance readiness and payout setup;
- compliance interactions;
- notifications and cases.

### 8.6 Admin-To-Partner Operational Loop

The portal is designed to stay in sync with admin actions.

Examples:

- admin requests info -> partner sees review task;
- admin approves lane -> program visibility changes;
- admin pauses code -> codes section shows blocked state;
- admin freezes finance action -> finance section shows blocked reason;
- admin updates case -> partner gets notification and case change;
- admin applies governance action -> compliance and dashboard posture change.

This is not a static dashboard. It is a runtime-controlled operational surface.

---

## 9. Visibility Logic

The portal is intentionally progressive.

### 9.1 Before Approval

Pending applicants typically see:

- dashboard lite;
- application and onboarding;
- messages, cases or notifications as applicable;
- legal read/accept where relevant;
- settings and security;
- organization basics.

They do not get full operational tools yet.

### 9.2 Probation

Approved probation users gain controlled operating surfaces such as:

- programs;
- codes or tracking basics;
- campaigns or assets where allowed;
- analytics lite;
- finance onboarding;
- compliance tasks.

### 9.3 Active

Active users can access:

- full reporting;
- broader code and campaign capabilities;
- payout setup and history;
- integrations;
- advanced lane-specific operations.

### 9.4 Restricted Or Suspended

Restricted or suspended users keep read and remediation surfaces:

- statements and history;
- compliance tasks;
- cases and notifications;
- remediation checklists;
- read-only operational visibility where policy allows.

But new action surfaces are gated or removed.

---

## 10. Technical Architecture Overview

### 10.1 Monorepo Placement

The partner portal is a dedicated application in the monorepo:

- `partner/` = external partner portal
- `admin/` = internal admin portal
- `backend/` = FastAPI backend and domain services
- `frontend/` = public/customer-facing web surface

This is important because the partner portal is not implemented as a sub-area of `frontend/`.

### 10.2 Separate Partner App

The `partner` app is a dedicated Next.js application with its own:

- route tree;
- auth flow;
- shell;
- runtime state;
- observability hooks;
- i18n messages;
- API client layer.

The canonical section registry lives in:

- `partner/src/features/partner-shell/config/section-registry.ts`

This registry defines:

- route slugs;
- navigation groups;
- access stages;
- release-ring gating;
- section metadata.

### 10.3 Partner Realm, Session And Security

The partner portal runs in a separate auth realm.

The core runtime identity contract is:

- `realm_key = partner`
- `audience = cybervpn:partner`
- `principal_type = partner_operator`

This is enforced in the frontend access layer and in backend authorization.

The frontend does not rely on "any logged-in role". It checks the correct partner realm tuple before allowing portal access.

The browser client injects:

- `X-Auth-Realm`
- `X-Request-ID`

and works with same-origin cookie-based auth.

Backend auth and realm resolution ensure that:

- partner sessions are separate from admin sessions;
- customer sessions are separate from partner sessions;
- wrong-host or wrong-realm usage is denied;
- workspace membership and permission keys remain the final authorization truth.

### 10.4 Backend Source Of Truth: Session Bootstrap

The most important runtime endpoint in the portal is:

- `GET /api/v1/partner-session/bootstrap`

This is the main source of truth for shell behavior.

The bootstrap payload returns:

- principal identity;
- workspace inventory;
- active workspace;
- workspace resolution;
- programs;
- current permission keys;
- release ring;
- finance readiness;
- compliance readiness;
- technical readiness;
- governance state;
- counters;
- pending tasks;
- blocked reasons;
- update timestamp.

This payload drives:

- dashboard;
- sidebar visibility;
- route guards;
- status banners;
- blocked-state explanations.

### 10.5 Frontend Runtime State

The frontend runtime state is layered in two steps:

1. bootstrap state;
2. live domain data.

Bootstrap gives the shell and access posture.

Then the portal loads live domain slices such as:

- notifications;
- cases;
- codes;
- campaign assets;
- statements;
- payout accounts;
- conversions;
- analytics;
- integrations;
- traffic declarations;
- review requests.

This mapping happens through a dedicated runtime state layer in the partner app, so the UI does not talk to raw backend DTOs directly.

### 10.6 API Structure

The partner portal backend contract is organized around partner-facing APIs for:

- auth and session;
- bootstrap;
- application drafts and attachments;
- organization profile;
- members and roles;
- legal documents and acceptance;
- lane applications;
- codes and tracking;
- campaigns and approval requests;
- conversions and explainability;
- analytics and exports;
- finance, payout accounts and statements;
- compliance and review requests;
- cases;
- notifications and notification preferences;
- integrations and delivery logs.

The admin portal uses a separate admin surface for:

- application review;
- lane approval;
- code governance;
- payout-account review;
- maker-checker actions;
- risk and governance actions;
- audit and ops workflows.

### 10.7 Notification And Case Layer

Notifications are backend-owned immutable events with partner read/archive state.

Cases are workflow objects, not just notifications. This distinction matters:

- notifications tell the partner that something happened;
- cases let the partner and admin work through an operational issue.

### 10.8 Observability

The portal is instrumented end-to-end.

The observability stack includes:

- Prometheus;
- Alertmanager;
- Grafana;
- OpenTelemetry Collector;
- Tempo;
- Loki and Promtail;
- infrastructure exporters.

Partner-specific observability covers:

- auth and realm flows;
- bootstrap;
- onboarding and application review;
- finance and payout readiness;
- notifications, cases and compliance loops;
- frontend route load and browser errors;
- frontend runtime events and Web Vitals;
- trace and log correlation between partner actions, backend mutations and admin workflows.

This means the portal is not only implemented functionally, but also observable operationally.

---

## 11. Current Implementation State

At the current stage, the partner portal is already implemented as a real product surface, not just as wireframes or a menu mock.

The current state can be summarized like this:

- separate `partner` application exists;
- canonical IA and runtime shell exist;
- partner realm auth runtime exists;
- backend bootstrap source of truth exists;
- application workflow exists on backend and frontend;
- workspace core sections are backend-backed;
- commercial surfaces are backend-backed;
- finance, compliance, notifications and cases are backend-backed;
- admin integration exists for partner operations;
- observability package is implemented in code and infrastructure;
- conformance and CI gates exist for partner/admin and observability packs.

The main remaining operational gap is not product design or core implementation. It is live environment rollout verification:

- staging observability rollout checks;
- live synthetic signal confirmation;
- evidence collection in staging;
- final rollout-readiness decision.

So the portal is architecturally and functionally built. The remaining uncertainty is operational validation, not conceptual design.

---

## 12. Mental Model For The Team

If the team needs one short sentence to remember what this portal is:

**CyberVPN partner portal is a separate partner operating workspace that manages the full external partner lifecycle, not a lightweight affiliate cabinet and not an admin clone.**

If the team needs one short sentence to remember how it works technically:

**The portal is a separate Next.js application in the `partner` workspace, authenticated in the `partner` realm, driven by backend bootstrap truth and live domain APIs, and synchronized with admin workflows through governed runtime state.**

---

## 13. Key Technical References

Main implementation references:

- [partner section registry](../../partner/src/features/partner-shell/config/section-registry.ts)
- [partner portal API client](../../partner/src/lib/api/partner-portal.ts)
- [partner bootstrap runtime hook](../../partner/src/features/partner-portal-state/lib/use-partner-portal-bootstrap-state.ts)
- [partner runtime state hook](../../partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts)
- [partner runtime mapping layer](../../partner/src/features/partner-portal-state/lib/runtime-state.ts)
- [partner access gate](../../partner/src/features/auth/lib/partner-access.ts)
- [partner browser API client](../../partner/src/lib/api/client.ts)
- [backend partner routes](../../backend/src/presentation/api/v1/partners/routes.py)
- [backend realm context](../../backend/src/presentation/api/v1/auth/realm_context.py)
- [backend monitoring routes](../../backend/src/presentation/api/v1/monitoring/routes.py)

Related product documents:

- [partner portal operating model and workflows](2026-04-20-partner-portal-operating-model-and-workflows.md)
- [partner frontend implementation and pre-backend integration assessment](2026-04-19-partner-frontend-implementation-and-pre-backend-integration-assessment.md)
- [partner portal PRD](2026-04-18-partner-portal-prd.md)
- [partner portal IA and menu map](2026-04-18-partner-portal-ia-and-menu-map.md)

