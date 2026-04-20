# CyberVPN Partner Portal Lane Capability Matrix

**Date:** 2026-04-18  
**Status:** Lane capability matrix  
**Purpose:** define which portal capabilities apply to each partner revenue lane and what additional controls are required for each lane.

---

## 1. Document Role

This document defines the lane-specific capability model for:

- Creator / Affiliate
- Performance / Media Buyer
- Reseller / API / Distribution

It does not cover consumer growth lanes.

---

## 2. Matrix Principles

1. One shared portal may serve all partner revenue lanes.
2. Shared modules do not imply shared capability depth.
3. Performance and Reseller lanes are more controlled than Creator by default.
4. Lane capability is further constrained by workspace status, role, and governance state.

---

## 3. Capability Matrix

Legend:

- `Yes` = capability is expected for the lane
- `Conditional` = capability exists but is gated by approval, readiness, or policy
- `Required` = capability or control is mandatory for the lane
- `No` = not a standard lane capability

| Capability | Creator / Affiliate | Performance / Media Buyer | Reseller / API / Distribution |
|---|---|---|---|
| Public self-serve application | Yes | Conditional | Conditional |
| Invite-only onboarding support | Conditional | Required | Required |
| Manual review | Conditional | Required | Required |
| Probation stage | Yes | Required | Required |
| Multiple lane applications | Conditional | Conditional | Conditional |
| Code creation | Yes | Yes | Yes |
| Starter code on probation | Yes | Conditional | Conditional |
| Deep-link builder | Yes | Yes | Conditional |
| QR generation | Yes | Conditional | Conditional |
| Vanity links | Yes | Yes | Conditional |
| Campaign and creative library | Yes | Yes | Conditional |
| Creative submission | Conditional | Required | Conditional |
| Traffic declarations | Conditional | Required | Conditional |
| Creative approvals | Conditional | Required | Conditional |
| Postback or webhook configuration | No | Required | Conditional |
| API token management | Conditional | Conditional | Required |
| Reporting dashboards | Yes | Yes | Yes |
| Exports | Yes | Yes | Yes |
| Attribution explainability | Yes | Yes | Yes |
| Statement visibility | Yes | Yes | Yes |
| Payout account management | Yes | Yes | Yes |
| Longer payout hold rules | Conditional | Required | Conditional |
| Reserve behavior visibility | Conditional | Required | Conditional |
| Storefront and domain config | No | No | Required |
| Customer and order scoped views | Limited | Limited | Yes |
| Support ownership visibility | No | No | Required |
| Technical integration diagnostics | Conditional | Yes | Required |
| Reseller Console | No | No | Required |

---

## 4. Lane Summaries

### 4.1 Creator / Affiliate

Primary operating model:

- content and community growth
- codes, links, assets, reporting, and statements as core modules

Default partner experience:

- public self-serve application allowed
- manual-lite review
- probation with limited finance and code operations
- full access after approval, finance readiness, and initial quality validation

### 4.2 Performance / Media Buyer

Primary operating model:

- paid traffic with elevated risk and operational controls

Default partner experience:

- application allowed but not instant activation
- mandatory manual review
- mandatory traffic declaration
- mandatory postback or click tracking readiness
- mandatory probation and longer hold controls

### 4.3 Reseller / API / Distribution

Primary operating model:

- distribution, markup, API resale, and storefront-linked operations

Default partner experience:

- manual review required
- legal, support, and technical readiness required
- storefront or API capabilities unlocked only after contract and finance alignment
- reseller console available only after lane activation

---

## 5. Capability Gating By Stage

### 5.1 `approved_probation`

Expected lane behavior:

- Creator: starter code, assets, reporting lite, finance onboarding
- Performance: limited launch setup, declaration tasks, no unrestricted scale-out
- Reseller: limited workspace access, no live storefront or unrestricted API mode

### 5.2 `approved_active`

Expected lane behavior:

- Creator: full standard code, reporting, and finance views
- Performance: active postback, reporting, compliance, and hold-aware finance views
- Reseller: storefront, domain, order, finance, and integration capabilities within scope

### 5.3 `paused` / `suspended`

Expected lane behavior:

- historical data remains visible
- new commercial expansion tools may be blocked
- compliance and support modules remain visible

---

## 6. Cross-Lane Rules

1. One workspace may apply to multiple lanes.
2. Lane approval does not automatically grant capability in another lane.
3. One partner may have multiple codes with different economics, but visibility must remain scoped to allowed lanes.
4. Performance lane must remain the most conservative lane for activation and finance release.
5. Reseller features must not leak admin-level global platform control.

---

## 7. Acceptance Conditions

This lane matrix is acceptable only when:

- each lane has clearly different operational expectations
- performance and reseller lanes remain more controlled than creator lanes
- shared portal modules can still present lane-specific capabilities and restrictions
- consumer growth programs remain outside this matrix

