# CyberVPN Partner Platform Phase 0 And Phase 1 Validation Pack

**Date:** 2026-04-17  
**Status:** Validation and evidence baseline for `T0.6`

This document defines the minimum validation and evidence pack that must exist before `Phase 0` closes and before `Phase 1` exit evidence is assembled.

## 1. Validation Objectives

The validation pack must support:

- glossary and contract freeze verification;
- synthetic realm and storefront fixture reuse;
- same-email different-realm validation;
- partner workspace and operator-role validation;
- legal acceptance evidence capture validation;
- early risk-subject linkage validation.

## 2. Mandatory Synthetic Fixtures

The baseline synthetic fixture set must include:

- one official realm
- one partner realm
- one official storefront
- one partner storefront
- one partner workspace
- one legal acceptance record
- one risk subject

These fixtures are defined in reusable backend test factories and fixtures, not only in prose.

## 3. Required Evidence Categories

Every `Phase 0` and `Phase 1` evidence pack must be able to attach:

- contract test output
- unit test output where enums or lifecycle logic are frozen
- API contract or OpenAPI evidence where relevant
- sign-off block with named owners
- divergence notes if any gate is partially accepted

## 4. Sign-Off Cadence

Minimum sign-off functions:

- platform architecture
- backend platform
- data/BI
- QA
- risk
- finance ops when finance-facing terminology is involved

## 5. Canonical Rules

1. `Phase 1` may not start until `Phase 0` blocking contracts are signed off.
2. `Phase 1` exit evidence must reuse this pack instead of inventing a new evidence shape.
3. Synthetic fixtures must preserve realm isolation semantics while still allowing cross-realm risk linkage scenarios.
