# CyberVPN Partner Platform API Conventions

**Date:** 2026-04-17  
**Status:** Canonical API baseline for `T0.4`

This document freezes the minimum API conventions that Phase 1 resources must follow.

## 1. Base Path

- Canonical browser-facing API base path: `/api/v1`

## 2. Canonical Headers

- request correlation header: `X-Request-ID`
- idempotent write header: `Idempotency-Key`

`Idempotency-Key` is part of the contract baseline even if some write families adopt it later than others.

## 3. Resource Naming Rules

- Use kebab-case for multi-word resource groups.
- Use canonical domain object names from the enum registry and target-state documents.
- Do not introduce provider-native resource groups where a normalized platform object already exists.

Reserved resource groups:

- `/api/v1/brands`
- `/api/v1/storefronts`
- `/api/v1/storefront-profiles`
- `/api/v1/surface-policies`
- `/api/v1/legal-documents`
- `/api/v1/realms`
- `/api/v1/principals`
- `/api/v1/partner-workspaces`
- `/api/v1/roles`
- `/api/v1/tokens`
- `/api/v1/offers`
- `/api/v1/pricebooks`
- `/api/v1/program-eligibility`
- `/api/v1/catalog`
- `/api/v1/partner-payout-accounts`

`partner-payout-accounts` is a first-class resource family. It is not only a nested property of payout instructions.

## 4. Error Envelope Baseline

The canonical error response shape must include:

- `error.code`
- `error.message`
- `request_id`

Optional details may be added without changing the baseline shape.

## 5. Async Job Baseline

When an operation is asynchronous, the API contract must expose a stable job envelope that includes:

- job identifier
- current status
- requested resource family or operation type
- timestamps sufficient for audit and support investigation

## 6. Provider Normalization Rule

Canonical platform objects must remain stable even when provider terminology differs.

Example:

- disputes are exposed as canonical `payment_dispute` resources;
- provider-specific states like inquiry, chargeback, or reversal are mapped as subtype, status, provider snapshot, or outcome class.

## 7. Scope Of This Baseline

The resource groups listed here are representative and reserved, not exhaustive. Later phases may add more resource groups without violating this baseline, but they must not rename the canonical groups listed above.
