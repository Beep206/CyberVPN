# CyberVPN Partner Portal Role Matrix

**Date:** 2026-04-18  
**Status:** Role and permission matrix  
**Purpose:** define the external partner workspace roles, their responsibilities, and the portal capabilities granted to each role.

---

## 1. Document Role

This document defines partner-side roles for the external portal.

It does not define:

- internal admin roles
- service credentials
- raw backend scopes

It exists so product, backend, frontend, and partner ops can align on what each workspace role is allowed to see and do.

---

## 2. Permission Model Principles

1. Roles apply within one partner workspace.
2. Role grants do not bypass workspace status or lane status gates.
3. Role grants do not bypass finance, compliance, or governance restrictions.
4. Sensitive finance and legal actions require narrower roles than general reporting.
5. No external role can execute internal ops-only actions such as payout approval, reserve changes, or global risk review.

---

## 3. Canonical External Roles

| Role | Purpose |
|---|---|
| `workspace_owner` | ultimate accountable owner, legal acceptor, team and workspace authority |
| `workspace_admin` | delegated workspace administrator for non-ownership administration |
| `finance_manager` | statements, payout accounts, finance readiness, invoice and tax context |
| `analyst` | reporting, exports, explainability, read-only commercial insight |
| `traffic_manager` | codes, links, campaigns, traffic declarations, performance operations |
| `support_manager` | support, disputes, customer/order issue handling within row-level scope |
| `technical_manager` | integrations, tokens, webhooks, postbacks, reseller technical setup |
| `legal_compliance_manager` | contracts, policy acceptance, declarations, remediation tasks |

Recommended minimum launch set:

- `workspace_owner`
- `finance_manager`
- `analyst`
- `traffic_manager`
- `support_manager`

Recommended extended set:

- `workspace_admin`
- `technical_manager`
- `legal_compliance_manager`

### 3.1 Launch Role Set

For the first delivery slice, product, frontend, and backend should treat the following as must-have external roles:

- `workspace_owner`
- `finance_manager`
- `analyst`
- `traffic_manager`
- `support_manager`

These roles are enough to validate onboarding, reporting, finance readiness, codes, and support flows without prematurely widening external administration complexity.

### 3.2 Deferred But Modeled Roles

The following roles should remain modeled from day one, even if some permissions ship later:

- `workspace_admin`
- `technical_manager`
- `legal_compliance_manager`

This keeps the RBAC model stable while allowing the first delivery slice to ship with a narrower launch set.

---

## 4. Role Definitions

### 4.1 `workspace_owner`

Owns:

- workspace lifecycle decisions
- team invites and removals
- role assignment
- contract acceptance
- sensitive workspace-level confirmations

Cannot:

- approve own lane internally
- release payout holds
- execute payouts
- override attribution or governance decisions

### 4.2 `workspace_admin`

Owns:

- workspace administration
- most member management
- operational setup tasks

Cannot:

- transfer ownership
- accept certain legal documents if policy requires owner-only acceptance
- perform internal-only finance or governance actions

### 4.3 `finance_manager`

Owns:

- statement visibility
- payout account setup
- finance readiness tasks
- payout and adjustment visibility

Cannot:

- manage campaigns or codes by default
- see data outside workspace row-level scope
- approve internal finance decisions

### 4.4 `analyst`

Owns:

- dashboards
- exports
- explainability views
- performance investigation

Cannot:

- create codes
- change finance setup
- manage team members

### 4.5 `traffic_manager`

Owns:

- codes and links
- campaign setup
- traffic declarations
- creative submission
- tracking diagnostics

Cannot:

- accept contracts
- manage payout setup
- execute internal governance actions

### 4.6 `support_manager`

Owns:

- cases and messages
- order and attribution issue review
- dispute communication
- remediation follow-up

Cannot:

- manage tokens
- alter finance configuration
- accept legal documents by default

### 4.7 `technical_manager`

Owns:

- API tokens
- reporting tokens
- webhook secrets
- postback configuration
- technical diagnostics

Cannot:

- manage payouts
- accept contracts by default
- manage workspace ownership

### 4.8 `legal_compliance_manager`

Owns:

- contract review
- declarations
- policy history
- remediation tasks
- compliance evidence uploads

Cannot:

- manage payouts
- create campaign traffic by default
- change ownership

---

## 5. Capability Matrix

Legend:

- `N` = no access
- `R` = read
- `W` = write / manage
- `A` = admin / owner authority

| Capability Area | Owner | Admin | Finance | Analyst | Traffic | Support | Technical | Legal |
|---|---|---|---|---|---|---|---|---|
| Home and status cards | R | R | R | R | R | R | R | R |
| Application draft editing | A | W | R | R | W | R | R | W |
| Submit application | A | W | N | N | W | N | N | W |
| Respond to requested info | A | W | W | N | W | W | W | W |
| Organization profile | A | W | W | R | W | R | W | W |
| Team invites and removals | A | W | N | N | N | N | N | N |
| Role assignment | A | W | N | N | N | N | N | N |
| Programs and lane requests | A | W | R | R | W | R | R | R |
| Contracts and legal docs | A | R | R | R | R | R | N | W |
| Policy acceptance history | A | R | R | R | R | R | R | W |
| Codes and deep links | A | W | R | R | W | R | R | N |
| Campaigns and creative submission | A | W | N | R | W | R | R | R |
| Conversions and orders | R | R | R | R | R | W | R | R |
| Analytics dashboards | R | R | R | R | R | R | R | R |
| Export jobs | A | W | W | W | W | R | R | R |
| Statements | R | R | W | R | R | R | N | R |
| Payout accounts | A | R | W | R | N | N | N | R |
| Payout history | R | R | W | R | N | R | N | R |
| Traffic declarations | A | W | R | R | W | R | R | W |
| Governance action visibility | R | R | R | R | R | R | R | R |
| Appeals and evidence uploads | A | W | W | N | W | W | R | W |
| Integrations and tokens | A | W | N | R | W | N | W | N |
| Settings and security | A | W | R | R | R | R | R | R |

---

## 6. Sensitive Action Rules

The following actions should require `workspace_owner` or a narrow approved role:

- ownership transfer
- final contract acceptance where policy requires owner-level authority
- payout account default selection if it changes settlement destination
- destructive team-role changes
- workspace termination request

The following actions must remain internal-only:

- lane approval or decline
- payout execution approval
- reserve extension
- payout freeze application
- statement close and reopen
- code suspension as internal governance decision

---

## 7. Role And Lane Interaction Rules

Roles do not unlock capabilities that the lane does not support.

Examples:

- `traffic_manager` in a Creator lane does not gain performance postback controls unless that lane is enabled
- `technical_manager` in a non-Reseller workspace does not gain reseller storefront controls
- `finance_manager` in `approved_probation` may see payout onboarding but not full payout execution history if none exists

---

## 8. Acceptance Conditions

This role matrix is acceptable only when:

- each role has a clear business owner
- no external role can perform internal ops actions
- role grants remain subordinate to workspace, lane, and governance state
- finance, legal, technical, and traffic responsibilities are separated enough to support real partner teams
