# Stage 3 External Pilot List Intake And Finance/Postback Classification

**Stage:** `S3-STAGE-18A`
**Parent stage:** `S3-STAGE-18`
**Status:** Passed as intake/classification gate; external list still required
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`

---

## 1. Purpose

`S3-STAGE-18A` is a working step inside `S3-STAGE-18`. It does not create `S3-STAGE-19`.

The purpose is to prepare controlled external partner expansion without opening payouts, uncontrolled postbacks, or broad partner acquisition.

This step defines:

1. what owner must provide for the first external pilot list;
2. how each candidate is classified before onboarding;
3. which finance class is allowed for S3;
4. which postback class is allowed for S3;
5. which states still block expansion;
6. what evidence must be collected during the next daily S3 watch.

---

## 2. Current Production State

Observed production state on 2026-05-25:

```text
partner_accounts=1
partner_codes=1
profiles=0
review_requests=0
payout_accounts=0
payout_instructions=0
payout_executions=0
postback_credentials=0
traffic_declarations=0
outbox_pending_failed=0
```

Existing pilot:

```text
partner_account=cybervpn-internal-pilot
display_name=CyberVPN Internal Partner Pilot
status=active
partner_code=S3PILOT1
markup_pct=0.00
```

Interpretation:

1. S3 internal pilot runtime is still clean.
2. No real external partner has been onboarded yet.
3. No payout route is active.
4. No postback credential exists.
5. There is no outbox backlog that blocks intake.

---

## 3. External Pilot Intake Contract

For every external pilot candidate, owner must provide the fields below.

Actual names, personal contacts, private payout references and partner secrets must not be committed into public docs. Store sensitive details in `.private`, the admin system, or another approved private store. Public evidence may use redacted labels.

| Field | Required For S3 | Public Docs | Recommendation |
|---|---:|---:|---|
| Partner display label | Yes | Redacted/alias allowed | Use a stable short label. |
| Partner/operator Telegram or email | Yes | Redacted | Store real contact in private evidence/admin only. |
| Allowed partner code | Yes | Yes | Use a unique code, not reused from internal proof. |
| Allowed storefront label | Optional | Yes | Only if storefront is part of the pilot. |
| Pilot cohort size | Yes | Yes | Start with 1-3 external users per partner. |
| Pilot window | Yes | Yes | Define start/end date and daily watch owner. |
| Traffic/source description | Yes | Redacted summary | Required for abuse/risk context. |
| Support escalation path | Yes | Redacted/role | Must identify who receives partner/user issues. |
| Finance class | Yes | Yes | Use one of `F0`-`F3`. |
| Postback class | Yes | Yes | Use one of `P0`-`P3`. |
| Payout expectation | Yes | Yes | Must be `none`, `sandbox_only`, or `manual_review_later` for S3. |
| Synthetic fixture acknowledgement | Yes | Yes | Must confirm S3 fixture is not real revenue. |

---

## 4. Finance Classification

S3 must not require payout details just to run the first external pilot. Finance strictness increases only when money movement is promised.

| Class | Meaning | Allowed In S3 External Pilot | Requirements |
|---|---|---:|---|
| `F0_NO_PAYOUT` | No partner earnings promise and no payout expectation. | Yes | No payout account required. Reporting may show zero/sandbox state only. |
| `F1_SANDBOX_ONLY` | Partner can see sandbox/reporting values, but no live payout. | Yes, recommended default | `PARTNER_PAYOUTS_ENABLED=false`; clear copy that values are not payable yet. |
| `F2_MANUAL_REVIEW_LATER` | Partner may later request payout review after finance profile. | Conditional | Finance profile required before any payout account approval; no live payout during current watch. |
| `F3_LIVE_PAYOUT` | Real payout execution allowed. | No | Deferred until separate owner/finance/legal/evidence approval after S3 stabilization. |

Default for the next external pilot:

```text
finance_class=F1_SANDBOX_ONLY
live_payout_allowed=false
payout_account_required_before_external_pilot=false
payout_account_required_before_real_payout=true
```

This keeps S3 pragmatic: partners can test attribution/reporting before CyberVPN collects payout реквизиты or promises payouts.

---

## 5. Postback Classification

Postback should not block the first external pilot unless that partner specifically needs performance-media automation.

| Class | Meaning | Allowed In S3 External Pilot | Requirements |
|---|---|---:|---|
| `P0_NO_POSTBACK` | No postback. Code/storefront attribution only. | Yes, recommended default | Partner uses dashboard/manual reporting. |
| `P1_REPORTING_ONLY` | Reporting/export only; no server-to-server delivery. | Yes | Reporting must remain workspace-scoped. |
| `P2_DRY_RUN_PAUSED` | Endpoint or credential may be collected, but delivery remains paused. | Conditional | Credential storage, masking, audit and dry-run evidence required before use. |
| `P3_LIVE_POSTBACK` | Live server-to-server partner postback delivery. | No | Deferred until staging replay, alerting, dead-letter and rollback evidence. |

Default for the next external pilot:

```text
postback_class=P0_NO_POSTBACK or P1_REPORTING_ONLY
postback_delivery_status=paused
postback_secret_required_before_external_pilot=false
postback_secret_required_before_live_delivery=true
```

---

## 6. Allowed S3-18A Outcomes

| Outcome | Allowed | Meaning |
|---|---:|---|
| Continue internal pilot only | Yes | No owner-provided external list yet. |
| Prepare first external candidate as `F0/P0` | Yes | No payout, no postback, smallest risk. |
| Prepare first external candidate as `F1/P1` | Yes | Sandbox/reporting only, no payout/postback delivery. |
| Accept `F2/P2` candidate | Conditional | Only with explicit owner approval and private finance/postback evidence. |
| Enable live payouts | No | Not part of `S3-STAGE-18A`. |
| Enable live postbacks | No | Not part of `S3-STAGE-18A`. |
| Expand broad partner acquisition | No | S3 remains controlled pilot. |

---

## 7. Minimal External Pilot List Template

Use this template for the next owner-provided list. Keep real contacts private if the repository may be shared.

| Candidate ID | Partner label | Operator contact | Code/storefront | Cohort size | Traffic/source | Support path | Finance class | Postback class | Decision |
|---|---|---|---|---:|---|---|---|---|---|
| `EXT-PILOT-001` | `<redacted>` | `<private>` | `<code>` | `1-3` | `<summary>` | `<role/contact>` | `F1_SANDBOX_ONLY` | `P0_NO_POSTBACK` | `pending_owner_input` |

Required decision before onboarding:

```text
owner_approved_candidate=true|false
partner_code_reserved=true|false
support_watch_ready=true|false
finance_class_confirmed=true|false
postback_class_confirmed=true|false
live_payout_allowed=false
live_postback_allowed=false
```

---

## 8. Operational Rules

1. Keep `PARTNER_PAYOUTS_ENABLED=false` for S3 external pilot unless a later explicit owner/finance gate says otherwise.
2. Keep postback delivery paused for S3 external pilot unless a later explicit postback evidence gate says otherwise.
3. Do not count `S3-17B-PAID-FIXTURE-20260525` as real revenue.
4. Do not create payout instructions for pilot partners without a closed positive statement and approved finance path.
5. Do not create partner payout accounts unless the owner intentionally moves a candidate to `F2_MANUAL_REVIEW_LATER`.
6. Do not store private partner contacts or payout references in public documentation.
7. Every external candidate must be covered by daily `S3-STAGE-18` watch until the expansion decision is changed.

---

## 9. S3-18A Decision

```text
S3-STAGE-18A_INTAKE_CONTRACT_READY
S3-STAGE-18A_FINANCE_CLASSIFICATION_READY
S3-STAGE-18A_POSTBACK_CLASSIFICATION_READY
S3-STAGE-18A_EXTERNAL_LIST_NOT_YET_PROVIDED
S3-STAGE-18A_KEEP_LIVE_PAYOUTS_BLOCKED
S3-STAGE-18A_KEEP_LIVE_POSTBACKS_BLOCKED
S3-STAGE-18A_NO_NEW_TOP_LEVEL_STAGE_CREATED
```

This means CyberVPN can accept the first external pilot list from owner, but must not automatically onboard or expand it until the list is classified and approved under this document.

---

## 10. Next Work Inside S3-STAGE-18

Do not create `S3-STAGE-19`.

Next work remains inside `S3-STAGE-18`:

```text
daily S3-STAGE-18 stabilization snapshot
or
owner-provided EXT-PILOT-001 list classification using this S3-STAGE-18A contract
```

