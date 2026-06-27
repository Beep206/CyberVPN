"""Safe Growth Codes v6 rule-builder AST validation, compilation, and simulation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

RULE_SCHEMA_VERSION = "growth-rule.v1"
RULE_CATALOG_VERSION = "growth-rule-catalog.v1"
MAX_RULE_NODES = 32
MAX_RULE_DEPTH = 6
MAX_RULE_ACTIONS = 8
MAX_RULE_BYTES = 20_000
MAX_REGEX_LENGTH = 120

RuleResult = Literal["allow", "deny", "challenge", "review", "noop"]

_FIELD_CATALOG: dict[str, dict[str, Any]] = {
    "customer.account_age_days": {"type": "integer", "operators": ["eq", "gte", "lte"]},
    "customer.email_verified": {"type": "boolean", "operators": ["eq"]},
    "checkout.gateway_amount": {"type": "decimal", "operators": ["eq", "gte", "lte"]},
    "checkout.currency": {"type": "string", "operators": ["eq", "in", "not_in"]},
    "checkout.sale_channel": {"type": "string", "operators": ["eq", "in", "not_in"]},
    "code.code_type": {"type": "string", "operators": ["eq", "in", "not_in"]},
    "code.normalized_code_hash": {"type": "string", "operators": ["eq"]},
    "risk.score": {"type": "decimal", "operators": ["eq", "gte", "lte"]},
    "risk.device_velocity_24h": {"type": "integer", "operators": ["eq", "gte", "lte"]},
    "risk.country_mismatch": {"type": "boolean", "operators": ["eq"]},
    "private_catalog.access_class": {"type": "string", "operators": ["eq", "in", "not_in"]},
    "partner.owner_type": {"type": "string", "operators": ["eq", "in", "not_in"]},
}

_ACTION_CATALOG: dict[str, dict[str, Any]] = {
    "allow": {"result": "allow", "params": []},
    "deny": {"result": "deny", "params": ["message_key"]},
    "challenge": {"result": "challenge", "params": ["challenge_type", "message_key"]},
    "review": {"result": "review", "params": ["queue", "message_key"]},
    "apply_discount": {"result": "allow", "params": ["discount_policy_key"]},
    "issue_invites": {"result": "allow", "params": ["benefit_key"]},
    "unlock_private_catalog": {"result": "allow", "params": ["private_policy_key"]},
}

_FORBIDDEN_EXECUTABLE_TERMS = frozenset(
    {
        "eval",
        "exec",
        "function",
        "import",
        "jinja",
        "subprocess",
    }
)
_FORBIDDEN_EXECUTABLE_SUBSTRINGS = ("javascript:", "python:", "__import__", "os.system")
_FORBIDDEN_SQL_TERM_SEQUENCES = (
    ("select", "from"),
    ("insert", "into"),
    ("update", "set"),
    ("delete", "from"),
)
_UNSAFE_REGEX_PATTERNS = (
    re.compile(r"\(\?"),  # lookarounds, flags, named groups and other advanced constructs
    re.compile(r"\\[1-9]"),  # backreferences
    re.compile(r"(\.\*){2,}"),
    re.compile(r"(\+|\*|\})\s*(\+|\*|\{)"),
)


class RuleValidationError(ValueError):
    """Raised when a rule AST is invalid or unsafe."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CompiledRule:
    schema_version: str
    catalog_version: str
    normalized_ast: dict[str, Any]
    compiled_plan: dict[str, Any]
    compiled_checksum: str
    node_count: int
    max_depth: int
    complexity_score: int


@dataclass(frozen=True)
class RuleSimulationResult:
    matched: bool
    result: RuleResult
    actions: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    compiled_checksum: str


def build_rule_catalog() -> dict[str, Any]:
    return {
        "catalog_version": RULE_CATALOG_VERSION,
        "schema_version": RULE_SCHEMA_VERSION,
        "limits": {
            "max_nodes": MAX_RULE_NODES,
            "max_depth": MAX_RULE_DEPTH,
            "max_actions": MAX_RULE_ACTIONS,
            "max_regex_length": MAX_REGEX_LENGTH,
        },
        "fields": _FIELD_CATALOG,
        "operators": {
            "eq": {"value_types": ["string", "integer", "decimal", "boolean"]},
            "gte": {"value_types": ["integer", "decimal"]},
            "lte": {"value_types": ["integer", "decimal"]},
            "in": {"value_types": ["list"]},
            "not_in": {"value_types": ["list"]},
            "regex_match": {"value_types": ["string"], "safe_regex": True},
        },
        "actions": _ACTION_CATALOG,
    }


def compile_rule_ast(ast: dict[str, Any]) -> CompiledRule:
    _validate_payload_size(ast)
    if ast.get("schema_version") != RULE_SCHEMA_VERSION:
        raise RuleValidationError("RULE_SCHEMA_UNSUPPORTED", "Unsupported growth rule schema version")
    when = ast.get("when")
    if not isinstance(when, dict):
        raise RuleValidationError("RULE_WHEN_REQUIRED", "Rule must contain a when tree")
    then = ast.get("then")
    if not isinstance(then, list) or not then:
        raise RuleValidationError("RULE_ACTION_REQUIRED", "Rule must contain at least one action")
    if len(then) > MAX_RULE_ACTIONS:
        raise RuleValidationError("RULE_TOO_MANY_ACTIONS", "Rule action count exceeds limit")

    condition_plan, condition_stats = _compile_condition_node(when, depth=1)
    action_plan = [_compile_action(action) for action in then]
    node_count = condition_stats["node_count"] + len(action_plan)
    max_depth = condition_stats["max_depth"]
    if node_count > MAX_RULE_NODES:
        raise RuleValidationError("RULE_TOO_COMPLEX", "Rule node count exceeds limit")
    if max_depth > MAX_RULE_DEPTH:
        raise RuleValidationError("RULE_TOO_DEEP", "Rule depth exceeds limit")

    normalized_ast = {
        "schema_version": RULE_SCHEMA_VERSION,
        "when": condition_plan,
        "then": action_plan,
    }
    compiled_plan = {
        "catalog_version": RULE_CATALOG_VERSION,
        "condition": condition_plan,
        "actions": action_plan,
    }
    checksum = _checksum(compiled_plan)
    return CompiledRule(
        schema_version=RULE_SCHEMA_VERSION,
        catalog_version=RULE_CATALOG_VERSION,
        normalized_ast=normalized_ast,
        compiled_plan=compiled_plan,
        compiled_checksum=checksum,
        node_count=node_count,
        max_depth=max_depth,
        complexity_score=node_count + max_depth + _regex_complexity(condition_plan),
    )


def simulate_rule_ast(ast: dict[str, Any], context: dict[str, Any]) -> RuleSimulationResult:
    compiled = compile_rule_ast(ast)
    trace: list[dict[str, Any]] = []
    matched = _evaluate_condition(compiled.compiled_plan["condition"], context=context, trace=trace)
    actions = compiled.compiled_plan["actions"] if matched else []
    result: RuleResult = "noop"
    if matched:
        result = _dominant_result(actions)
    return RuleSimulationResult(
        matched=matched,
        result=result,
        actions=actions,
        trace=trace,
        compiled_checksum=compiled.compiled_checksum,
    )


def _compile_condition_node(node: dict[str, Any], *, depth: int) -> tuple[dict[str, Any], dict[str, int]]:
    if depth > MAX_RULE_DEPTH:
        raise RuleValidationError("RULE_TOO_DEEP", "Rule depth exceeds limit")
    node_type = node.get("type")
    if node_type in {"all", "any"}:
        children = node.get("children")
        if not isinstance(children, list) or not children:
            raise RuleValidationError("RULE_EMPTY_GROUP", "Condition group must contain children")
        normalized_children: list[dict[str, Any]] = []
        node_count = 1
        max_depth = depth
        for child in children:
            if not isinstance(child, dict):
                raise RuleValidationError("RULE_NODE_INVALID", "Condition child must be an object")
            compiled_child, stats = _compile_condition_node(child, depth=depth + 1)
            normalized_children.append(compiled_child)
            node_count += stats["node_count"]
            max_depth = max(max_depth, stats["max_depth"])
        return {"type": node_type, "children": normalized_children}, {"node_count": node_count, "max_depth": max_depth}
    if node_type == "not":
        child = node.get("child")
        if not isinstance(child, dict):
            raise RuleValidationError("RULE_NODE_INVALID", "Not condition must contain child")
        compiled_child, stats = _compile_condition_node(child, depth=depth + 1)
        return {"type": "not", "child": compiled_child}, {
            "node_count": stats["node_count"] + 1,
            "max_depth": max(depth, stats["max_depth"]),
        }
    if node_type == "condition":
        return _compile_leaf_condition(node), {"node_count": 1, "max_depth": depth}
    raise RuleValidationError("RULE_NODE_TYPE_UNSUPPORTED", "Unsupported condition node type")


def _compile_leaf_condition(node: dict[str, Any]) -> dict[str, Any]:
    field = str(node.get("field") or "")
    operator = str(node.get("operator") or "")
    if field not in _FIELD_CATALOG:
        raise RuleValidationError("RULE_FIELD_UNSUPPORTED", "Unsupported rule field")
    field_spec = _FIELD_CATALOG[field]
    allowed_operators = set(field_spec["operators"]) | ({"regex_match"} if field_spec["type"] == "string" else set())
    if operator not in allowed_operators:
        raise RuleValidationError("RULE_OPERATOR_UNSUPPORTED", "Unsupported operator for rule field")
    value = node.get("value")
    _assert_no_executable_text(value)
    if operator == "regex_match":
        _assert_safe_regex(value)
    _assert_value_matches_field(field_type=str(field_spec["type"]), operator=operator, value=value)
    return {"type": "condition", "field": field, "operator": operator, "value": value}


def _compile_action(action: object) -> dict[str, Any]:
    if not isinstance(action, dict):
        raise RuleValidationError("RULE_ACTION_INVALID", "Rule action must be an object")
    action_type = str(action.get("action") or "")
    if action_type not in _ACTION_CATALOG:
        raise RuleValidationError("RULE_ACTION_UNSUPPORTED", "Unsupported rule action")
    params = action.get("params") or {}
    if not isinstance(params, dict):
        raise RuleValidationError("RULE_ACTION_PARAMS_INVALID", "Rule action params must be an object")
    _assert_no_executable_text(params)
    return {
        "action": action_type,
        "result": _ACTION_CATALOG[action_type]["result"],
        "params": params,
    }


def _evaluate_condition(node: dict[str, Any], *, context: dict[str, Any], trace: list[dict[str, Any]]) -> bool:
    node_type = node["type"]
    if node_type == "all":
        child_results = [_evaluate_condition(child, context=context, trace=trace) for child in node["children"]]
        result = all(child_results)
        trace.append({"type": "all", "result": result, "children": child_results})
        return result
    if node_type == "any":
        child_results = [_evaluate_condition(child, context=context, trace=trace) for child in node["children"]]
        result = any(child_results)
        trace.append({"type": "any", "result": result, "children": child_results})
        return result
    if node_type == "not":
        child_result = _evaluate_condition(node["child"], context=context, trace=trace)
        result = not child_result
        trace.append({"type": "not", "result": result, "child": child_result})
        return result
    actual = _lookup_context_value(context, node["field"])
    result = _compare(actual=actual, operator=node["operator"], expected=node["value"])
    trace.append(
        {
            "type": "condition",
            "field": node["field"],
            "operator": node["operator"],
            "actual_present": actual is not None,
            "result": result,
        }
    )
    return result


def _compare(*, actual: object, operator: str, expected: object) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "gte":
        return _decimal(actual) >= _decimal(expected)
    if operator == "lte":
        return _decimal(actual) <= _decimal(expected)
    if operator == "in":
        return actual in (expected if isinstance(expected, list) else [])
    if operator == "not_in":
        return actual not in (expected if isinstance(expected, list) else [])
    if operator == "regex_match":
        return bool(re.search(str(expected), str(actual or ""), flags=re.ASCII))
    raise RuleValidationError("RULE_OPERATOR_UNSUPPORTED", "Unsupported rule operator")


def _lookup_context_value(context: dict[str, Any], field: str) -> object:
    value: object = context
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _dominant_result(actions: list[dict[str, Any]]) -> RuleResult:
    for result in ("deny", "challenge", "review", "allow"):
        if any(action.get("result") == result for action in actions):
            return result  # type: ignore[return-value]
    return "noop"


def _assert_value_matches_field(*, field_type: str, operator: str, value: object) -> None:
    if operator in {"in", "not_in"}:
        if not isinstance(value, list):
            raise RuleValidationError("RULE_VALUE_TYPE_INVALID", "Membership operators require a list")
        for item in value:
            _assert_scalar_field_value(field_type=field_type, value=item)
        return
    _assert_scalar_field_value(field_type=field_type, value=value)


def _assert_scalar_field_value(*, field_type: str, value: object) -> None:
    if field_type == "boolean" and not isinstance(value, bool):
        raise RuleValidationError("RULE_VALUE_TYPE_INVALID", "Boolean field requires boolean value")
    if field_type == "integer" and not isinstance(value, int):
        raise RuleValidationError("RULE_VALUE_TYPE_INVALID", "Integer field requires integer value")
    if field_type == "decimal":
        _decimal(value)
    if field_type == "string" and not isinstance(value, str):
        raise RuleValidationError("RULE_VALUE_TYPE_INVALID", "String field requires string value")


def _assert_safe_regex(value: object) -> None:
    if not isinstance(value, str) or not value:
        raise RuleValidationError("RULE_REGEX_INVALID", "Regex value must be a non-empty string")
    if len(value) > MAX_REGEX_LENGTH:
        raise RuleValidationError("RULE_REGEX_TOO_LONG", "Regex exceeds maximum length")
    if any(pattern.search(value) for pattern in _UNSAFE_REGEX_PATTERNS):
        raise RuleValidationError("RULE_REGEX_UNSAFE", "Regex contains unsupported unsafe constructs")
    try:
        re.compile(value, flags=re.ASCII)
    except re.error as exc:
        raise RuleValidationError("RULE_REGEX_INVALID", "Regex could not be compiled") from exc


def _assert_no_executable_text(value: object) -> None:
    if isinstance(value, str):
        if _contains_forbidden_executable_text(value):
            raise RuleValidationError("RULE_EXECUTABLE_TEXT_FORBIDDEN", "Rule cannot contain executable code")
        return
    if isinstance(value, dict):
        for nested_value in value.values():
            _assert_no_executable_text(nested_value)
        return
    if isinstance(value, list):
        for nested_value in value:
            _assert_no_executable_text(nested_value)


def _contains_forbidden_executable_text(value: str) -> bool:
    normalized = value.casefold()
    if any(marker in normalized for marker in _FORBIDDEN_EXECUTABLE_SUBSTRINGS):
        return True
    tokens = _ascii_word_tokens(normalized)
    if any(term in tokens for term in _FORBIDDEN_EXECUTABLE_TERMS):
        return True
    return any(_contains_ordered_terms(tokens, sequence) for sequence in _FORBIDDEN_SQL_TERM_SEQUENCES)


def _ascii_word_tokens(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in value:
        if char.isascii() and (char.isalnum() or char == "_"):
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current.clear()
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def _contains_ordered_terms(tokens: tuple[str, ...], terms: tuple[str, ...]) -> bool:
    position = 0
    for token in tokens:
        if token == terms[position]:
            position += 1
            if position == len(terms):
                return True
    return False


def _validate_payload_size(ast: dict[str, Any]) -> None:
    encoded = json.dumps(ast, sort_keys=True, separators=(",", ":"), default=str)
    if len(encoded.encode("utf-8")) > MAX_RULE_BYTES:
        raise RuleValidationError("RULE_PAYLOAD_TOO_LARGE", "Rule payload exceeds maximum size")


def _regex_complexity(node: dict[str, Any]) -> int:
    if node.get("type") == "condition" and node.get("operator") == "regex_match":
        return len(str(node.get("value") or ""))
    if node.get("type") in {"all", "any"}:
        return sum(_regex_complexity(child) for child in node.get("children", []))
    if node.get("type") == "not":
        return _regex_complexity(node.get("child", {}))
    return 0


def _checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RuleValidationError("RULE_VALUE_TYPE_INVALID", "Decimal field requires numeric value") from exc
