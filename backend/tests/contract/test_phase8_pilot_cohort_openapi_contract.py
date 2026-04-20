from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_phase8_pilot_cohort_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/pilot-cohorts/" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}/owner-acknowledgements" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}/rollback-drills" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}/go-no-go-decisions" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}/readiness" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}/activate" in paths
    assert f"{API_V1_PREFIX}/pilot-cohorts/{{cohort_id}}/pause" in paths


def test_phase8_pilot_cohort_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "CreatePilotCohortRequest" in component_schemas
    assert "PausePilotCohortRequest" in component_schemas
    assert "PilotOwnerAcknowledgementRequest" in component_schemas
    assert "PilotOwnerAcknowledgementResponse" in component_schemas
    assert "PilotRollbackDrillRequest" in component_schemas
    assert "PilotRollbackDrillResponse" in component_schemas
    assert "PilotGoNoGoDecisionRequest" in component_schemas
    assert "PilotGoNoGoDecisionResponse" in component_schemas
    assert "PilotCohortResponse" in component_schemas
    assert "PilotCohortReadinessResponse" in component_schemas
    assert "PilotRolloutWindowResponse" in component_schemas
