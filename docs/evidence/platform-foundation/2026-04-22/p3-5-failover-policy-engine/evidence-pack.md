# CyberVPN Platform Foundation P3.5 Failover Policy Engine Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P3.5`  
**Phase:** `P3`  
**Primary owners:** `fleet-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `security`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p3-5-failover-policy-engine-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-5-failover-policy-engine-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.5` carries `EX-034` as the formal reason later work may continue while live guarded
  failover proof is still absent.

---

## 2. Result Snapshot

Current `P3.5` result:

- the controller now persists:
  - `BudgetPolicy`
  - `RateLimitPolicy`
  - `ApprovalPolicy`
  - `FailoverGuardrailPolicy`
- the controller can upsert and read a durable failover-policy bundle for one scope
- typed `node-failover` evaluation now returns:
  - `accepted`
  - `awaiting_approval`
  - `blocked_policy`
- failover evaluation now enforces:
  - confidence threshold
  - minimum independent signal sources
  - monthly and burst budget checks
  - rate-limit window checks
  - cooldown checks
  - max parallel failovers
  - risk and budget approval thresholds
- request handling now persists blocked or approval-gated requests without publishing a
  command preview to NATS

This packet is **not yet claimed complete** because:

- no live health, DPI, or provider-impairment signals are driving this policy engine;
- no live approval workflow exists;
- no live guarded failover request is being reconciled against a real fleet node or pool;
- no live canary, traffic shift, drain, or quarantine proof exists for failover outcomes.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 3.1 Python Syntax Check

```bash
cd services/node-fleet-controller
.venv/bin/python -m py_compile $(find src -name '*.py' -print)
```

Result:

- compilation completed successfully

### 3.2 Service Unit And API Tests

```bash
cd services/node-fleet-controller
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Result:

- `Ran 16 tests`
- `OK`

### 3.3 Local Foundation Coverage

Observed validated baseline:

- policy bundles can be persisted and read back by scope
- low-confidence or low-signal failover requests become `blocked_policy`
- high-risk failover requests become `awaiting_approval`
- accepted failover requests remain typed `failover` requests with guardrail evaluation
  attached to the API response
- typed policy routes and typed `node-failover` route work through the controller API

---

## 4. Remaining Live Closure Requirements

`P3.5` can only move from "repo slice complete" to "packet complete" when:

1. live DPI, provider, or health impairment evidence is ingested into the controller;
2. at least one live failover request is evaluated through real policy records;
3. at least one live guarded failover enters:
   - `awaiting_approval` or
   - `blocked_policy`
   with durable audit proof;
4. at least one live accepted failover request reconciles into replacement capacity or
   controlled traffic shift evidence;
5. `EX-034` is removed from the exceptions register.
