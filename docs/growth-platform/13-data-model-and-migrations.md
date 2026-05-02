# Data Model and Migrations

## Purpose

This document defines migration sequencing so implementation does not drift into feature-specific schema shortcuts.

## Migration Principles

1. Shared runtime entities come before feature-specific convenience tables.
2. Payment, entitlement, and attribution migrations preserve backward compatibility where possible.
3. Partner finance uses append-only ledger semantics from the start.
4. Public snapshot publishing supports atomic replacement and last-valid retention.

## Group 1 — Shared Runtime Context

Goal:

- establish tenant-aware and attribution-aware foundation.

Expected schema areas:

- identity links;
- Telegram identity linkage;
- runtime tenant context support;
- surface and attribution metadata expansion.

## Group 2 — Mini App Payments and Entitlements

Goal:

- support Telegram Stars purchase flow safely.

Expected schema areas:

- payment provider and surface metadata expansion;
- quote and invoice references;
- payment authoritative status fields;
- refund and reconciliation support;
- entitlement linkage hardening.

## Group 3 — Public Network Intelligence

Goal:

- support public snapshot generation and truthful serving.

Expected schema areas:

- public snapshot store;
- snapshot history;
- public incidents;
- methodology versioning;
- measurement window metadata.

## Group 4 — White-Label Foundation

Goal:

- create durable partner tenant objects before advanced UX.

Expected schema areas:

- partner bots;
- partner brand theme;
- partner commercial policy;
- partner settlement accounts;
- partner risk profile;
- provisioning jobs.

## Group 5 — Settlement and Operations

Goal:

- make finance and operations production-grade.

Expected schema areas:

- immutable partner settlement ledger;
- payout hold and release records;
- operator actions and audit records;
- incident publication records.

## Migration Sequencing Rules

- no partner payout automation before ledger tables exist;
- no public incident editing without audit support;
- no partner-branded rollout without tenant-aware runtime tables;
- no recurring subscription work inside Telegram until baseline Stars flow is stable.

## Backfill Strategy

- derive tenant context where safely inferable;
- backfill partner attribution conservatively;
- create explicit unknown states instead of silent assumptions;
- flag ambiguous history for manual review.

## Release Strategy

- ship migrations before dependent code paths;
- use temporary compatibility adapters where needed;
- remove transition logic only after live verification.

## Anti-Patterns to Avoid

- durable business state only in JSON blobs or env defaults;
- mutable partner balances without ledger history;
- public snapshot rows overwritten without last-valid fallback;
- feature rollout before lower migration groups are complete.
