# Platform Foundation Production Drills And Conformance Spec

**Date:** 2026-04-23  
**Status:** canonical `P3.9` production drill and conformance spec  
**Purpose:** freeze the final production drill order, evidence domains, and Gate `D`
assembly rules for CyberVPN target-state validation.

---

## 1. Role

This document freezes the final production drill and conformance package for CyberVPN.

It exists to make four boundaries explicit:

1. which drill domains must exist before `Gate D` can pass;
2. how those drills map to the production conformance criteria;
3. how evidence must be assembled into a final gate package;
4. which shortcuts are explicitly forbidden.

This document does not declare any drill already complete. It freezes the conformance
contract that later live evidence must satisfy.

---

## 2. Frozen Drill Domains

The mandatory production drill domains are:

- `OpenBao`
- `NATS`
- `CloudNativePG`
- `GitOps / Flux recovery`
- `PostHog`
- `Node Fleet Controller / fleet reprovisioning`

These domains are mandatory because together they cover the canonical target-state
production conformance criteria in Section `16` of the architecture document.

---

## 3. Frozen Drill Order

The production drill order is:

1. `OpenBao`
2. `NATS`
3. `CloudNativePG`
4. `GitOps / Flux recovery`
5. `PostHog`
6. `Node Fleet Controller / fleet reprovisioning`
7. final scorecard snapshot and gate assembly

Rationale:

- secrets-plane and event-backbone recovery must be proven before application and fleet
  recovery claims are trusted;
- production data recovery must be proven before production cutover is considered safe;
- GitOps recovery must be proven before final production rollout authority is treated as
  production-conformant;
- product intelligence and fleet-control drills must prove that the final operational
  surfaces are both real and bounded.

---

## 4. Drill To Criteria Mapping

| Domain | Primary criteria |
|---|---|
| `OpenBao` | `C15` |
| `NATS` | `C02`, `C03`, `C05`, `C06`, `C15` |
| `CloudNativePG` | `C15` |
| `GitOps / Flux recovery` | `C14`, `C15` |
| `PostHog` | `C11`, `C12`, `C13`, `C14`, `C15` |
| `Node Fleet Controller / fleet reprovisioning` | `C07`, `C08`, `C09`, `C10`, `C15` |

Every final `Gate D` scorecard must show how each in-scope criterion is backed by at
least one linked evidence artifact.

---

## 5. Mandatory Proof By Domain

### 5.1 OpenBao

Required proof:

- `raft snapshot save`
- snapshot restore or equivalent restore rehearsal
- peer-set or cluster-health validation after restore

### 5.2 NATS

Required proof:

- declared stream and consumer governance evidence
- outage or node-loss drill showing backlog or recovery, not silent event loss
- replay or restore evidence

### 5.3 CloudNativePG

Required proof:

- backup evidence
- recovery bootstrap or PITR-style evidence
- monitoring and alert validation

### 5.4 GitOps / Flux recovery

Required proof:

- desired-state source-of-truth evidence
- controlled suspend, rollback, or reconciliation recovery evidence
- no manual host mutation acting as production truth

### 5.5 PostHog

Required proof:

- authoritative commercial event capture
- privacy validation showing prohibited VPN telemetry is absent
- deterministic flag fallback behavior
- recovery or restore validation for the product-intelligence surface

### 5.6 Node Fleet Controller / fleet reprovisioning

Required proof:

- `node-add`
- `node-replace` or equivalent reprovisioning
- `node-quarantine`
- guarded failover evaluation and outcome

---

## 6. Forbidden Shortcuts

The following are not valid substitutes for production drill evidence:

- screenshots without transcripts or artifacts
- verbal confirmation without linked evidence
- manual operator notes that bypass the canonical source-of-truth boundary
- partial drill success presented as full conformance
- untracked legacy fallback paths used to “pass” a drill

---

## 7. Gate D Assembly Rules

`Gate D` may only be claimed when all of the following are true:

1. every mandatory drill domain has linked evidence;
2. every in-scope scorecard row meets the `Gate D` minimum;
3. any remaining `EX-*` entries are non-blocking, explicitly allowed, and do not waive a
   production-conformance criterion;
4. the final evidence pack contains:
   - drill bundle
   - scorecard snapshot
   - sign-off block
   - explicit `passed` or `blocked` statement

---

## 8. Live Closure Requirements

`P3.9` can move from repo-slice complete to packet complete only when:

1. real production drill transcripts exist for all mandatory domains;
2. the final scorecard snapshot is filled with evidence-backed production scores;
3. `Gate D` evidence pack is assembled from the canonical template;
4. `EX-038` is removed from the temporary exceptions register.
