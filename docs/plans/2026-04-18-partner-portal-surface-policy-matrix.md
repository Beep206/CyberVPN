# CyberVPN Partner Portal Surface Policy Matrix

**Date:** 2026-04-18  
**Status:** Surface policy matrix  
**Purpose:** define which capabilities belong to which external or internal surfaces and prevent leakage between customer, partner, storefront, admin, and reporting contexts.

---

## 1. Document Role

This document defines the surface boundaries for:

- customer dashboard
- partner portal
- partner storefront
- admin and internal ops
- reporting and export APIs
- service and integration surfaces

It exists to keep partner portal scope clean and aligned with the canonical platform architecture.

---

## 2. Surface Definitions

| Surface | Primary principal | Purpose |
|---|---|---|
| Customer Dashboard | customer | consumer account and service management |
| Partner Portal | partner_operator | workspace operations for partner revenue lanes |
| Partner Storefront | customer in partner brand realm | partner-branded commerce and self-service |
| Admin / Internal Ops | admin | review, governance, finance, risk, and global operations |
| Reporting / Export APIs | partner token, admin token, service token | analytics, exports, and explainability feeds |
| Service / Integration APIs | service or scoped technical credentials | postbacks, webhooks, and partner technical integrations |

---

## 3. Surface Policy Principles

1. Customer and partner surfaces remain separate.
2. Partner portal exposes workspace operations, not internal moderation queues.
3. Partner storefront exposes customer-facing commerce, not partner-admin operations.
4. Admin surface owns review, override, freeze, and maker-checker actions.
5. Reporting and export APIs expose scoped data, not raw unrestricted operational access.

---

## 4. Capability Matrix

Legend:

- `Primary` = main owning surface
- `Secondary` = allowed supporting surface
- `Read-only` = visible but not writable
- `No` = not allowed on this surface

| Capability | Customer Dashboard | Partner Portal | Partner Storefront | Admin / Internal Ops | Reporting / Export APIs | Service / Integration APIs |
|---|---|---|---|---|---|---|
| Consumer referral and invite flows | Primary | No | No | Secondary | Read-only | No |
| Partner application submission | No | Primary | No | Secondary | No | No |
| Partner invite acceptance | No | Primary | No | Secondary | No | No |
| Workspace organization profile | No | Primary | No | Secondary | No | No |
| Team and access management | No | Primary | No | Secondary | No | No |
| Lane request and lane status view | No | Primary | No | Secondary | Read-only | No |
| Internal lane approval or decline | No | No | No | Primary | No | No |
| Contract acceptance by partner | No | Primary | No | Secondary | No | No |
| Code creation and link management | No | Primary | No | Secondary | Read-only | Secondary |
| Traffic declaration submission | No | Primary | No | Secondary | Read-only | Secondary |
| Creative approval review decision | No | No | No | Primary | No | No |
| Creative approval submission | No | Primary | No | Secondary | No | No |
| Attributed conversion and order views | No | Primary | No | Secondary | Secondary | No |
| Partner analytics dashboards | No | Primary | No | Secondary | Secondary | No |
| Statement visibility | No | Primary | No | Secondary | Secondary | No |
| Payout account setup | No | Primary | No | Secondary | No | No |
| Payout execution approval | No | No | No | Primary | No | No |
| Governance action execution | No | No | No | Primary | No | No |
| Governance action visibility and remediation | No | Primary | No | Secondary | Read-only | No |
| Reseller storefront config view | No | Primary | Secondary | Secondary | Read-only | Secondary |
| Customer commerce in partner brand | No | No | Primary | Secondary | Read-only | Secondary |
| Global fraud or cross-partner search | No | No | No | Primary | No | No |
| Reporting exports | No | Primary | No | Secondary | Primary | No |
| Postback delivery and webhook diagnostics | No | Primary | No | Secondary | Secondary | Primary |

---

## 5. Explicit Exclusions From Partner Portal

The partner portal must not include:

- Invite / Gift mechanics
- Consumer Referral Credits management
- global admin moderation queues
- cross-partner fraud search
- raw reserve controls
- maker-checker approval screens
- internal payout execution controls
- global policy publication tools

Those belong in customer or admin surfaces.

---

## 6. Partner Storefront Rules

The partner storefront is a customer-facing commerce surface, not a partner operations console.

It may expose:

- partner-branded commerce
- customer checkout and self-service
- partner-owned pricing where allowed by policy

It must not expose:

- workspace role management
- statement management
- internal compliance tasks
- partner-side reporting administration

---

## 7. Reporting API Rules

Reporting and export APIs may expose:

- partner-scoped reporting
- statement exports
- payout-status exports
- explainability reporting

They must enforce:

- server-side row-level visibility
- workspace scoping
- role-aware visibility where required

They must not expose:

- unrestricted admin datasets
- writable governance decisions
- raw internal-only reconciliation controls

---

## 8. Acceptance Conditions

This matrix is acceptable only when:

- partner portal remains a workspace operating surface
- customer and partner semantics do not leak into each other
- internal ops actions remain internal
- reporting and technical surfaces remain scoped and non-admin by default

