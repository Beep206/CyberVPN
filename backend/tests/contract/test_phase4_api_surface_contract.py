import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

PHASE4_REQUIRED_PATHS = (
    f"{API_V1_PREFIX}/earning-events/",
    f"{API_V1_PREFIX}/earning-events/{{event_id}}",
    f"{API_V1_PREFIX}/earning-holds/",
    f"{API_V1_PREFIX}/earning-holds/{{hold_id}}",
    f"{API_V1_PREFIX}/earning-holds/{{hold_id}}/release",
    f"{API_V1_PREFIX}/reserves/",
    f"{API_V1_PREFIX}/reserves/{{reserve_id}}",
    f"{API_V1_PREFIX}/reserves/{{reserve_id}}/release",
    f"{API_V1_PREFIX}/settlement-periods/",
    f"{API_V1_PREFIX}/settlement-periods/{{settlement_period_id}}",
    f"{API_V1_PREFIX}/settlement-periods/{{settlement_period_id}}/close",
    f"{API_V1_PREFIX}/settlement-periods/{{settlement_period_id}}/reopen",
    f"{API_V1_PREFIX}/partner-statements/generate",
    f"{API_V1_PREFIX}/partner-statements/",
    f"{API_V1_PREFIX}/partner-statements/{{statement_id}}",
    f"{API_V1_PREFIX}/partner-statements/{{statement_id}}/close",
    f"{API_V1_PREFIX}/partner-statements/{{statement_id}}/reopen",
    f"{API_V1_PREFIX}/partner-statements/{{statement_id}}/adjustments",
    f"{API_V1_PREFIX}/partner-payout-accounts/",
    f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}",
    f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/eligibility",
    f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/verify",
    f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/suspend",
    f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/archive",
    f"{API_V1_PREFIX}/partner-payout-accounts/{{payout_account_id}}/make-default",
    f"{API_V1_PREFIX}/payouts/instructions",
    f"{API_V1_PREFIX}/payouts/instructions/{{payout_instruction_id}}",
    f"{API_V1_PREFIX}/payouts/instructions/{{payout_instruction_id}}/approve",
    f"{API_V1_PREFIX}/payouts/instructions/{{payout_instruction_id}}/reject",
    f"{API_V1_PREFIX}/payouts/executions",
    f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}",
    f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/submit",
    f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/complete",
    f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/fail",
    f"{API_V1_PREFIX}/payouts/executions/{{payout_execution_id}}/reconcile",
)

PHASE4_REQUIRED_SCHEMAS = (
    "EarningEventResponse",
    "EarningHoldResponse",
    "ReserveResponse",
    "SettlementPeriodResponse",
    "PartnerStatementResponse",
    "StatementAdjustmentResponse",
    "PartnerPayoutAccountResponse",
    "PartnerPayoutAccountEligibilityResponse",
    "PayoutInstructionResponse",
    "PayoutExecutionResponse",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen Phase 4 contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def test_live_openapi_contains_phase4_finance_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    for required_path in PHASE4_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase4_finance_paths() -> None:
    schema = _exported_openapi_schema()
    paths = schema["paths"]

    for required_path in PHASE4_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase4_finance_schemas() -> None:
    schema = _exported_openapi_schema()
    components = schema["components"]["schemas"]

    for schema_name in PHASE4_REQUIRED_SCHEMAS:
        assert schema_name in components
