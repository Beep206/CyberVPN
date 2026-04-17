# CyberVPN Partner Operations, Risk, Finance, And Compliance Spec

**Date:** 2026-04-17  
**Status:** Domain specification  
**Purpose:** define the canonical operational model for partner workspace operations, financial settlement, risk review, compliance actions, and governance controls.

---

## 1. Document Role

This document defines the operating layer used by:

- partner managers;
- finance ops;
- support;
- fraud and risk teams;
- governance and compliance operators.

---

## 2. Partner Operations Objects

Required entities:

- `partner_accounts`
- `partner_account_users`
- `partner_program_memberships`
- `partner_codes`
- `partner_code_versions`
- `contracts`
- `tax_profiles`
- `settlement_profiles`
- `partner_payout_accounts`

Partner workspaces must expose:

- users and roles;
- codes and memberships;
- statements and payout accounts;
- reporting and exports;
- compliance actions and declarations.

---

## 3. Partner Finance

Partner finance requires:

- `earning_events`
- `earning_holds`
- `earning_adjustments`
- `partner_statements`
- `settlement_periods`
- `payout_instructions`
- `payout_executions`
- `reserves`

Canonical rules:

- wallet is not the accounting system for partner settlement;
- statements and payouts are separate from consumer wallet behavior;
- refunds, disputes, and chargebacks must create typed adjustment flows;
- no hard-delete of financial records;
- maker-checker approval applies to sensitive payout actions.

---

## 4. Risk Model

Required entities:

- `risk_subjects`
- `risk_identifiers`
- `risk_links`
- `risk_events`
- `risk_reviews`
- `risk_decisions`

Risk must detect:

- self-referral;
- same-human multi-account farming;
- duplicate trials;
- partner self-purchases;
- synthetic first-payment abuse;
- cross-realm payout abuse.

---

## 5. Governance And Compliance

Required entities:

- `accepted_legal_documents`
- `partner_traffic_declarations`
- `creative_approvals`
- `governance_actions`
- `dispute_cases`

Canonical governance actions:

- code suspension;
- payout freeze;
- reserve extension;
- manual override;
- traffic restriction;
- creative rejection.

---

## 6. Operational Review Queues

The platform should support dedicated queues for:

- payout review;
- dispute review;
- risk review;
- policy acceptance review where needed;
- partner onboarding review;
- traffic declaration review.

---

## 7. Acceptance Conditions

The operations, risk, finance, and compliance layer is acceptable only when:

- partner workspaces and internal teams can operate without raw SQL;
- risk decisions and compliance actions are auditable;
- statement and payout flows are explainable end to end;
- dispute, refund, and clawback events propagate through typed operational pathways.
