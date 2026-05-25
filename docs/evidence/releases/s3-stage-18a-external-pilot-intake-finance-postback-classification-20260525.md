# S3-STAGE-18A Evidence: External Pilot List Intake And Finance/Postback Classification

**Date:** 2026-05-25
**Stage:** `S3-STAGE-18A`
**Parent stage:** `S3-STAGE-18`
**Status:** Passed as intake/classification gate; waiting for owner external pilot list
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`
**Stage document:** `docs/cybervpn_stage3_launch_docs/18A_STAGE3_EXTERNAL_PILOT_LIST_INTAKE_FINANCE_POSTBACK_CLASSIFICATION.md`

---

## 1. Summary

`S3-STAGE-18A` was completed as a guarded intake and classification step inside `S3-STAGE-18`.

Result:

```text
external_pilot_intake_contract=ready
finance_classification=ready
postback_classification=ready
external_pilot_list_provided=false
live_payout_allowed=false
live_postback_allowed=false
new_top_level_stage_created=false
```

This keeps S3 moving without forcing payout реквизиты or postback credentials before they are actually needed.

---

## 2. Production Snapshot

Production runtime remained healthy during the check:

```text
cybervpn-admin=healthy
cybervpn-backend=healthy
cybervpn-frontend=healthy
cybervpn-nats=healthy
cybervpn-postgres=healthy
cybervpn-remnawave=healthy
cybervpn-scheduler=healthy
cybervpn-telegram-bot=healthy
cybervpn-valkey=healthy
cybervpn-worker=healthy
```

Production partner state:

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

Internal pilot:

```text
partner_account=cybervpn-internal-pilot
display_name=CyberVPN Internal Partner Pilot
status=active
partner_code=S3PILOT1
markup_pct=0.00
```

---

## 3. Finance Classification Evidence

S3 external pilot can proceed without live payout obligations only under these allowed classes:

| Class | Status | S3 decision |
|---|---|---|
| `F0_NO_PAYOUT` | Allowed | No payout account required. |
| `F1_SANDBOX_ONLY` | Allowed and recommended default | Reporting/sandbox only; no payable promise. |
| `F2_MANUAL_REVIEW_LATER` | Conditional | Requires private finance profile before payout-account approval. |
| `F3_LIVE_PAYOUT` | Blocked | Not allowed in S3-18A. |

Current decision:

```text
default_finance_class=F1_SANDBOX_ONLY
partner_payout_accounts=0
payout_instructions=0
payout_executions=0
live_payout_allowed=false
```

---

## 4. Postback Classification Evidence

S3 external pilot can proceed without live postback delivery under these allowed classes:

| Class | Status | S3 decision |
|---|---|---|
| `P0_NO_POSTBACK` | Allowed and recommended default | Code/storefront attribution only. |
| `P1_REPORTING_ONLY` | Allowed | Dashboard/reporting only. |
| `P2_DRY_RUN_PAUSED` | Conditional | Endpoint/credential may be collected privately, delivery remains paused. |
| `P3_LIVE_POSTBACK` | Blocked | Not allowed in S3-18A. |

Current decision:

```text
default_postback_class=P0_NO_POSTBACK
postback_credentials=0
postback_delivery_status=paused
live_postback_allowed=false
```

---

## 5. Owner Intake Status

No external pilot list was provided during this step.

Required next input:

```text
candidate_id=EXT-PILOT-001
partner_label=<redacted-or-private>
operator_contact=<private>
partner_code=<unique-code>
cohort_size=1-3
traffic_source=<summary>
support_path=<owner/support route>
finance_class=F0_NO_PAYOUT or F1_SANDBOX_ONLY recommended
postback_class=P0_NO_POSTBACK or P1_REPORTING_ONLY recommended
owner_approval=true|false
```

---

## 6. Decision

```text
S3-STAGE-18A_INTAKE_CONTRACT_READY
S3-STAGE-18A_FINANCE_CLASSIFICATION_READY
S3-STAGE-18A_POSTBACK_CLASSIFICATION_READY
S3-STAGE-18A_EXTERNAL_LIST_NOT_YET_PROVIDED
S3-STAGE-18A_KEEP_LIVE_PAYOUTS_BLOCKED
S3-STAGE-18A_KEEP_LIVE_POSTBACKS_BLOCKED
S3-STAGE-18A_NO_NEW_TOP_LEVEL_STAGE_CREATED
```

---

## 7. DEMO

### Component

Command:

```bash
ssh -i /home/beep/.ssh/MainKey2_private_fixed.pem deploy@45.87.41.146 \
  'cd /srv/cybervpn/compose/app && sudo -n docker compose exec -T cybervpn-postgres psql -U cybervpn -d cybervpn -At -c "<partner finance/postback count queries>"'
```

Result:

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

### Feature

Steps:

1. Reviewed `S3-STAGE-18` residual requirement.
2. Verified production partner/finance/postback state.
3. Added S3-18A intake contract.
4. Added finance classification `F0`-`F3`.
5. Added postback classification `P0`-`P3`.
6. Kept live payout and live postback blocked.
7. Confirmed no `S3-STAGE-19` was created.

Result:

```text
S3-18A ready for owner-provided external pilot list.
External expansion remains pending list/classification approval.
```

