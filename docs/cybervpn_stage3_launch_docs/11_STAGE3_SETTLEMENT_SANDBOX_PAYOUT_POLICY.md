# Stage 3 Settlement Sandbox And Payout Policy

**Stage:** `S3-STAGE-11`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-10: Partner Reporting And Analytics`

---

## 1. Назначение

S3-STAGE-11 готовит settlement и payout-контур без реальных выплат.

Цель этапа: дать finance/admin объяснимый read-only sandbox, где видно:

- какие statement amounts потенциально доступны к выплате;
- какие суммы удержаны через holds/reserves;
- какие refund/chargeback факторы должны быть учтены;
- готов ли payout account;
- есть ли pending/approved payout instructions;
- разрешён ли dry-run;
- почему live payout остаётся заблокированным.

Этот этап не включает реальные partner payouts и не открывает партнёрам self-serve withdrawal.

---

## 2. Decision

Production default остаётся закрытым:

```text
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
```

Settlement sandbox открывается только когда включены оба флага:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_SETTLEMENT_SANDBOX_ENABLED=true
```

Реальные payout routes остаются отдельно закрыты через:

```text
PARTNER_PAYOUTS_ENABLED=false
```

Важно: `PARTNER_SETTLEMENT_SANDBOX_ENABLED=true` не разрешает live payouts. Это только read-only симуляция.

---

## 3. Входит

| Area | S3-STAGE-11 result |
|---|---|
| Settlement sandbox | Added workspace-scoped read-only settlement simulation endpoint. |
| Payout policy | Response declares `sandbox_only`, `live_payouts_enabled=false`, export disabled. |
| Eligibility | Shows payout instruction eligibility, dry-run eligibility and live payout block. |
| Holds/reserves | Surfaces on-hold and reserve amounts from partner statements. |
| Refund/chargeback impact | Surfaces refund and chargeback counts from partner reporting mart. |
| Maker-checker | Declares finance approval and different maker/checker requirement. |
| Access control | Requires partner workspace `payouts_read` permission. |
| Disabled-state | Route returns S3 disabled-state 404 until portal and sandbox flags are enabled. |

---

## 4. Backend Changes

### 4.1 Kill switch

Added setting:

```text
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
```

Files:

```text
backend/src/config/settings.py
backend/.env.example
backend/src/presentation/middleware/partner_disabled_boundary.py
```

Protected surfaces:

```text
/api/v1/settlement-sandbox/*
/api/v1/partner-workspaces/{workspace_id}/settlement-sandbox
```

Disabled response:

```json
{
  "detail": {
    "code": "partner_settlement_sandbox_disabled",
    "message": "Partner settlement sandbox is not enabled for this release.",
    "stage": "S3-STAGE-11"
  }
}
```

### 4.2 Settlement sandbox endpoint

Added:

```http
GET /api/v1/partner-workspaces/{workspace_id}/settlement-sandbox
```

The endpoint returns:

```text
workspace_id
generated_at
currency_code
metrics
eligibility
policy
calculation_notes
```

It requires:

```text
payouts_read
```

The endpoint is read-only. It does not:

- create payout instructions;
- approve payout instructions;
- create payout executions;
- submit payout batches;
- export partner payout files;
- trigger provider payouts.

### 4.3 Metrics returned

| Metric | Source of truth |
|---|---|
| `available_statement_amount` | `partner_statements.available_amount` |
| `on_hold_amount` | `partner_statements.on_hold_amount` |
| `reserve_amount` | `partner_statements.reserve_amount` |
| `adjustment_net_amount` | `partner_statements.adjustment_net_amount` |
| `paid_conversion_count` | `partner_reporting_mart` |
| `refund_count` | `partner_reporting_mart` |
| `chargeback_count` | `partner_reporting_mart` |
| `payout_export_status` | `S3-STAGE-11 policy` |

### 4.4 Eligibility model

The sandbox reports:

```text
settlement_simulation_reproducible
payout_instruction_allowed
dry_run_execution_allowed
live_payout_allowed
manual_approval_required
maker_checker_required
blocked_reasons
eligible_statement_count
eligible_payout_account_count
pending_instruction_count
approved_instruction_count
dry_run_execution_count
live_execution_count
```

`live_payout_allowed` is always `false` in S3-STAGE-11.

Typical blocked reasons:

```text
stage_blocks_live_payout
no_closed_positive_statement
payout_account_not_approved
payout_instruction_awaiting_maker_checker
no_approved_instruction_for_dry_run
active_payout_execution_exists
```

---

## 5. Payout Policy For S3

S3-STAGE-11 policy:

```text
mode=sandbox_only
payout_export_status=disabled_by_default
live_payouts_enabled=false
requires_finance_approval=true
requires_maker_checker=true
same_admin_approval_allowed=false
```

Required later gates before live payout:

```text
S3-STAGE-12
S3-STAGE-14
S3-STAGE-15
S3-STAGE-17
```

Live payouts remain blocked until:

1. support/admin operations can process payout cases without shell access;
2. legal/privacy/payment/payout copy is approved;
3. full staging rehearsal proves payout dry-run and rollback;
4. controlled partner pilot is explicitly approved by owner/finance.

---

## 6. What Is Explicitly Not Enabled

S3-STAGE-11 does not enable:

- automatic payouts;
- mass payout;
- live provider payout API calls;
- partner self-serve withdrawal;
- payout file download for partners;
- payout account approval by partner;
- same-admin maker-checker bypass;
- payout execution without an approved instruction;
- payout execution while active execution exists.

---

## 7. Test Coverage

Covered locally:

| Proof | Result |
|---|---|
| Settlement sandbox hidden until flag is enabled | Passed |
| Settlement sandbox hidden when portal is disabled | Passed |
| Settlement sandbox passes when portal and sandbox flags are enabled | Passed |
| OpenAPI exposes settlement sandbox schemas | Passed |
| Workspace owner can read sandbox simulation | Passed |
| Outsider cannot read another workspace sandbox | Passed |
| Sandbox shows available statement amount | Passed |
| Sandbox shows on-hold/reserve amounts | Passed |
| Sandbox blocks live payout | Passed |
| Sandbox blocks payout instruction when payout account is not approved | Passed |
| Payout export remains disabled by policy | Passed |

---

## 8. Production Notes

Production must keep:

```text
PARTNER_SETTLEMENT_SANDBOX_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
```

until the later S3 finance, legal, staging and pilot gates are completed.

If sandbox is enabled for an internal finance review, keep:

```text
PARTNER_PAYOUTS_ENABLED=false
```

so live payout routes stay closed.

---

## 9. Next Stage

```text
S3-STAGE-12: Partner Support, Admin Ops, And Audit
```
