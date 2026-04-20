# CyberVPN Partner Platform Policy Version Lifecycle

**Date:** 2026-04-17  
**Status:** Canonical lifecycle baseline for `T0.3`

This document freezes the minimum lifecycle contract for policy-versioned objects.

## 1. Applies To

The lifecycle discipline applies to at least:

- partner-code economics;
- offers;
- pricebooks;
- program eligibility policies;
- attribution policies;
- markup policies;
- surface policy matrices;
- storefront legal document sets.

## 2. Required Fields

Every versioned object must support:

- `effective_from`
- `effective_to`
- `approval_state`
- `version_status`
- `created_by`
- `approved_by` when applicable
- immutable identifiers for downstream snapshot references

## 3. Approval State

Allowed `approval_state` values:

- `draft`
- `approved`
- `rejected`

## 4. Version Status

Allowed `version_status` values:

- `draft`
- `active`
- `superseded`
- `archived`

## 5. Canonical Rules

1. Finalized orders always retain references to the original version identifiers used for pricing, attribution, legal acceptance, and settlement explainability.
2. Policy supersession never rewrites finalized financial history retroactively.
3. Quote-time policy references must either remain valid through commit or fail with an explicit recomputation path.
4. Approval state and version status are related but not interchangeable.
5. Critical economics may not depend on mutable `system_config` keys as the only source of truth.

## 6. Effective Dating Rules

- `effective_from` marks the earliest valid timestamp for use.
- `effective_to` closes validity without deleting the version.
- overlapping active windows for the same scoped object must be blocked unless the owning policy explicitly allows overlap.
- `archived` versions remain referenceable for historical explainability.
