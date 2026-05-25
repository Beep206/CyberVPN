# Stage 3 Controlled Partner Pilot

**Stage:** `S3-STAGE-17`
**Status:** Runtime enabled; first pilot workspace/code proof passed; conversion proof pending
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-16A: GitLab CI Runner And Tag Pipeline Closure`

---

## 1. Purpose

`S3-STAGE-17` turns the Stage 3 partner/reseller runtime on in production for a controlled pilot.

This is not yet broad partner scale. The goal is to prove the real production partner path with owner-approved pilot participants before expanding.

The runtime enablement includes:

1. partner portal backend surfaces;
2. partner application surfaces;
3. partner codes;
4. attribution;
5. storefront previews;
6. partner reporting;
7. settlement sandbox;
8. partner webhooks/runtime flags;
9. payout admin surfaces;
10. partner event backbone on internal-only NATS/JetStream;
11. frontend/Mini App partner UI flag.

---

## 2. Production Release

Final production runtime tag:

```text
s3-stage17-controlled-partner-pilot.3
```

Final release commit:

```text
ea0ccca2
```

Deployment evidence:

```text
docs/evidence/releases/s3-stage-17-controlled-partner-pilot-runtime-enable-20260525.md
docs/evidence/releases/s3-stage-17-deploy/stage1-gitlab-deploy-s3-stage17-controlled-partner-pilot.3.md
```

---

## 3. Runtime Flags

Production runtime flags for S3-STAGE-17:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_APPLICATIONS_ENABLED=true
PARTNER_CODES_ENABLED=true
PARTNER_ATTRIBUTION_ENABLED=true
PARTNER_STOREFRONTS_ENABLED=true
PARTNER_REPORTING_ENABLED=true
PARTNER_SETTLEMENT_SANDBOX_ENABLED=true
PARTNER_WEBHOOKS_ENABLED=true
PARTNER_PAYOUTS_ENABLED=true
PARTNER_EVENT_BACKBONE_ENABLED=true
PARTNER_EXPORTS_ENABLED=true
PAUSE_PARTNER_EXPANSION=false
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=true
NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED=true
NEXT_PUBLIC_PARTNER_PILOT_ENABLED=true
```

`PARTNER_PAYOUTS_ENABLED=true` exposes the admin/manual payout workflow surface. It does not create an automatic external payout integration by itself. Finance actions still require authenticated admin roles, maker-checker workflow, audit trail and manual control.

---

## 4. Internal NATS/JetStream

`PARTNER_EVENT_BACKBONE_ENABLED=true` requires a live NATS runtime. S3-STAGE-17 adds:

```text
Service: cybervpn-nats
Image: nats:2.12.7-alpine
Mode: internal-only Docker network
Public ports: none
JetStream storage: cybervpn_stage1_nats_jetstream
```

NATS is not placed on the VPN node. The VPN node remains node-only.

---

## 5. Enablement Notes

The first enablement attempt on tag `s3-stage17-controlled-partner-pilot.1` found a backend startup bug in the partner event backbone logging path:

```text
Logger._log() got an unexpected keyword argument 'consumers'
```

This was fixed by moving the structured field into `extra={...}` and redeploying backend on:

```text
s3-stage17-controlled-partner-pilot.2
```

The final production tag:

```text
s3-stage17-controlled-partner-pilot.3
```

also ensures `PARTNER_EXPORTS_ENABLED=true` is visible inside the backend container environment.

---

## 6. Current Pilot Data State

Production runtime was enabled first with no pilot partner data:

```text
partner_accounts=0
partner_account_users=0
partner_codes=0
partner_payout_accounts=0
storefronts=1
outbox_events_pending=0
```

This means `S3-STAGE-17` runtime enablement is complete, but the stage exit criterion is not complete until at least one approved pilot partner/workspace/code is created and tested end-to-end.

`S3-STAGE-17A` then created the first internal controlled pilot workspace/code:

```text
account_key=cybervpn-internal-pilot
operator_login=s2_admin_ops
operator_role=owner
operator_2fa=true
mobile_owner=Sasha_Beep
code=S3PILOT1
markup_pct=0
is_active=true
```

Evidence:

```text
docs/cybervpn_stage3_launch_docs/17A_STAGE3_FIRST_PILOT_PARTNER_WORKSPACE_CODE_PROOF.md
docs/evidence/releases/s3-stage-17a-first-pilot-partner-workspace-code-proof-20260525.md
```

---

## 7. Exit Criteria

`S3-STAGE-17` can be considered fully passed only when:

1. one approved pilot partner or internal partner workspace exists;
2. a partner operator can authenticate and load partner surfaces;
3. at least one partner code is created under manual control;
4. a test customer can use that code or storefront path;
5. attribution is recorded and explainable;
6. reporting reflects the conversion without inconsistency;
7. settlement sandbox shows expected manual finance posture;
8. no unresolved paid/access/support inconsistency appears;
9. no P0/P1 alert remains unresolved;
10. owner decides to continue, pause or expand.

---

## 8. Rollback

Primary rollback for the S3-STAGE-17 runtime:

```text
1. set partner flags back to false;
2. set PAUSE_PARTNER_EXPANSION=true;
3. redeploy backend/frontend or rollback to s3-stage16-disabled-state.3;
4. stop cybervpn-nats only if PARTNER_EVENT_BACKBONE_ENABLED=false and no pending pilot event evidence is needed;
5. run B2C smoke endpoints and partner disabled-boundary probes.
```

Known rollback artifacts:

```text
Pre-enable env backup: .env.pre-s3-stage17-controlled-partner-pilot-20260525T125101Z
Pre-final compose backup: docker-compose.yml.pre-s3-stage17-controlled-partner-pilot.3
Prior disabled-state tag: s3-stage16-disabled-state.3
```

---

## 9. Decision

```text
S3-STAGE-17_RUNTIME_ENABLEMENT_PASSED
S3-STAGE-17A_FIRST_PILOT_WORKSPACE_CODE_PROOF_PASSED
S3-STAGE-17_CONVERSION_ATTRIBUTION_REPORTING_PROOF_PENDING
```

Recommended next working step:

```text
S3-STAGE-17B: First Partner Code Redemption, Attribution, Reporting, And Settlement Sandbox Proof
```
