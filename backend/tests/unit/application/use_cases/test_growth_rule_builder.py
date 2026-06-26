from __future__ import annotations

from copy import deepcopy

import pytest

from src.application.use_cases.growth_code_sets.rule_builder import (
    RULE_CATALOG_VERSION,
    RuleValidationError,
    build_rule_catalog,
    compile_rule_ast,
    simulate_rule_ast,
)


def _rule_ast() -> dict:
    return {
        "schema_version": "growth-rule.v1",
        "when": {
            "type": "all",
            "children": [
                {
                    "type": "condition",
                    "field": "code.code_type",
                    "operator": "eq",
                    "value": "promo",
                },
                {
                    "type": "condition",
                    "field": "risk.score",
                    "operator": "gte",
                    "value": "0.85",
                },
            ],
        },
        "then": [
            {
                "action": "challenge",
                "params": {"challenge_type": "email_otp", "message_key": "growth.rules.challenge.high_risk"},
            }
        ],
    }


def test_rule_catalog_exposes_safe_fields_operators_actions_and_limits() -> None:
    catalog = build_rule_catalog()

    assert catalog["catalog_version"] == RULE_CATALOG_VERSION
    assert "code.code_type" in catalog["fields"]
    assert "regex_match" in catalog["operators"]
    assert "unlock_private_catalog" in catalog["actions"]
    assert catalog["limits"]["max_nodes"] > 0


def test_compile_rule_ast_returns_stable_checksum_and_complexity() -> None:
    first = compile_rule_ast(_rule_ast())
    second = compile_rule_ast(deepcopy(_rule_ast()))

    assert first.compiled_checksum == second.compiled_checksum
    assert first.node_count == 4
    assert first.max_depth == 2
    assert first.compiled_plan["catalog_version"] == RULE_CATALOG_VERSION


def test_simulate_rule_ast_returns_trace_without_mutating_context() -> None:
    context = {
        "code": {"code_type": "promo"},
        "risk": {"score": "0.91"},
    }
    original_context = deepcopy(context)

    result = simulate_rule_ast(_rule_ast(), context)

    assert context == original_context
    assert result.matched is True
    assert result.result == "challenge"
    assert result.actions[0]["action"] == "challenge"
    assert any(item["type"] == "condition" and item["field"] == "risk.score" for item in result.trace)


def test_rule_builder_rejects_executable_text() -> None:
    ast = _rule_ast()
    ast["then"][0]["params"]["message_key"] = "eval(alert(1))"

    with pytest.raises(RuleValidationError) as exc:
        compile_rule_ast(ast)

    assert exc.value.code == "RULE_EXECUTABLE_TEXT_FORBIDDEN"


def test_rule_builder_rejects_unsafe_regex() -> None:
    ast = {
        "schema_version": "growth-rule.v1",
        "when": {
            "type": "condition",
            "field": "checkout.currency",
            "operator": "regex_match",
            "value": "(.*.*)+",
        },
        "then": [{"action": "review", "params": {"queue": "risk"}}],
    }

    with pytest.raises(RuleValidationError) as exc:
        compile_rule_ast(ast)

    assert exc.value.code == "RULE_REGEX_UNSAFE"


def test_rule_builder_rejects_unknown_field_and_excessive_depth() -> None:
    ast = _rule_ast()
    ast["when"]["children"][0]["field"] = "unknown.field"

    with pytest.raises(RuleValidationError) as exc:
        compile_rule_ast(ast)

    assert exc.value.code == "RULE_FIELD_UNSUPPORTED"

    too_deep = {
        "schema_version": "growth-rule.v1",
        "when": {
            "type": "not",
            "child": {
                "type": "not",
                "child": {
                    "type": "not",
                    "child": {
                        "type": "not",
                        "child": {
                            "type": "not",
                            "child": {
                                "type": "not",
                                "child": {
                                    "type": "condition",
                                    "field": "code.code_type",
                                    "operator": "eq",
                                    "value": "promo",
                                },
                            },
                        },
                    },
                },
            },
        },
        "then": [{"action": "allow", "params": {}}],
    }

    with pytest.raises(RuleValidationError) as exc:
        compile_rule_ast(too_deep)

    assert exc.value.code == "RULE_TOO_DEEP"
