#!/usr/bin/env bash
# -------------------------------------------------------------------
# check-api-contract.sh
#
# ARCH-01.3 -- CI contract validation to block breaking API changes.
#
# This script regenerates the OpenAPI spec from the FastAPI application
# and compares it against the committed version at
#   backend/docs/api/openapi.json
#
# Breaking changes detected:
#   - Removed endpoints (paths that existed before but are now gone)
#   - Removed required request/response fields
#   - Changed response content types
#   - Removed HTTP methods from existing paths
#
# Non-breaking changes allowed:
#   - New endpoints (paths)
#   - New optional fields in request/response schemas
#   - New HTTP methods on existing paths
#   - New response codes
#
# Exit codes:
#   0 -- no breaking changes (or spec unchanged)
#   1 -- breaking changes found or script error
#
# Usage:
#   scripts/check-api-contract.sh           # from project root
#   scripts/check-api-contract.sh --verbose # show diff details
# -------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
COMMITTED_SPEC="${BACKEND_DIR}/docs/api/openapi.json"
GENERATED_SPEC=""
VERBOSE=0
BREAKING=0

for arg in "$@"; do
    case "$arg" in
        --verbose|-v) VERBOSE=1 ;;
    esac
done

cleanup() {
    if [[ -n "${GENERATED_SPEC}" && -f "${GENERATED_SPEC}" ]]; then
        rm -f "${GENERATED_SPEC}"
    fi
    if [[ -n "${TMPDIR_CREATED:-}" && -d "${TMPDIR_CREATED}" ]]; then
        rm -rf "${TMPDIR_CREATED}"
    fi
}
trap cleanup EXIT

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
info()  { printf "\033[0;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[0;32m[OK]\033[0m    %s\n" "$*"; }
warn()  { printf "\033[0;33m[WARN]\033[0m  %s\n" "$*"; }
fail()  { printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*"; }

# -------------------------------------------------------------------
# Step 0: Validate prerequisites
# -------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    fail "python3 is not available on PATH"
    exit 1
fi

if [[ ! -f "${COMMITTED_SPEC}" ]]; then
    fail "Committed OpenAPI spec not found at ${COMMITTED_SPEC}"
    fail "Run 'cd backend && python scripts/export_openapi.py' to generate it first."
    exit 1
fi

# -------------------------------------------------------------------
# Step 1: Regenerate the OpenAPI spec into a temp file
# -------------------------------------------------------------------
info "Regenerating OpenAPI spec from the FastAPI application..."

TMPDIR_CREATED="$(mktemp -d)"
GENERATED_SPEC="${TMPDIR_CREATED}/openapi-generated.json"

# The export script requires certain env vars to be set for Settings
# validation. We provide safe dummy values so the FastAPI app object
# can be constructed without a real database or services.
export REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_spec_generation_only}"
export JWT_SECRET="${JWT_SECRET:-contract_check_dummy_secret_that_is_at_least_32_chars_long}"
export CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}"
export SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

if ! python3 "${BACKEND_DIR}/scripts/export_openapi.py" \
        --output "${GENERATED_SPEC}" 2>/dev/null; then
    fail "Failed to regenerate OpenAPI spec. Check backend/scripts/export_openapi.py."
    exit 1
fi

if [[ ! -f "${GENERATED_SPEC}" ]]; then
    fail "Generated spec file not created at ${GENERATED_SPEC}"
    exit 1
fi

ok "OpenAPI spec regenerated successfully."

# -------------------------------------------------------------------
# Step 2: Compare specs using a Python structural diff
# -------------------------------------------------------------------
# We use an inline Python script to do a semantic comparison that
# understands OpenAPI structure rather than a naive text diff.
# -------------------------------------------------------------------
info "Comparing committed spec with regenerated spec..."

python3 - "${COMMITTED_SPEC}" "${GENERATED_SPEC}" "${VERBOSE}" <<'PYTHON_SCRIPT'
import json
import sys
from pathlib import Path


def load_spec(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_breaking_changes(old: dict, new: dict) -> list[str]:
    """Return a list of human-readable breaking change descriptions."""
    issues: list[str] = []

    old_paths = old.get("paths", {})
    new_paths = new.get("paths", {})

    # 1. Removed endpoints (path + method combinations)
    for path, methods in old_paths.items():
        if path not in new_paths:
            issues.append(f"REMOVED PATH: {path}")
            continue
        for method in methods:
            if method.startswith("x-"):
                continue  # skip OpenAPI extensions
            if method not in new_paths.get(path, {}):
                issues.append(f"REMOVED METHOD: {method.upper()} {path}")

    # 2. Check for removed/changed parameters on existing endpoints
    for path, methods in old_paths.items():
        if path not in new_paths:
            continue
        for method, old_op in methods.items():
            if method.startswith("x-"):
                continue
            new_op = new_paths.get(path, {}).get(method)
            if new_op is None:
                continue  # already caught above

            # 2a. Check required parameters
            old_params = {
                (p.get("name"), p.get("in")): p
                for p in old_op.get("parameters", [])
            }
            new_params = {
                (p.get("name"), p.get("in")): p
                for p in new_op.get("parameters", [])
            }
            for key, old_param in old_params.items():
                if key not in new_params:
                    if old_param.get("required", False):
                        issues.append(
                            f"REMOVED REQUIRED PARAM: {key[0]} (in {key[1]}) "
                            f"on {method.upper()} {path}"
                        )

            # 2b. Check response codes -- removing a documented success
            # response is breaking (clients may depend on it)
            old_responses = old_op.get("responses", {})
            new_responses = new_op.get("responses", {})
            for code in old_responses:
                if code.startswith("2") and code not in new_responses:
                    issues.append(
                        f"REMOVED SUCCESS RESPONSE: {code} "
                        f"on {method.upper()} {path}"
                    )

            # 2c. Check response content types removed
            for code, old_resp in old_responses.items():
                new_resp = new_responses.get(code, {})
                old_content = old_resp.get("content", {})
                new_content = new_resp.get("content", {})
                for media_type in old_content:
                    if media_type not in new_content:
                        issues.append(
                            f"REMOVED RESPONSE CONTENT TYPE: {media_type} "
                            f"from {code} on {method.upper()} {path}"
                        )

    # 3. Check schemas for removed required fields
    old_schemas = old.get("components", {}).get("schemas", {})
    new_schemas = new.get("components", {}).get("schemas", {})

    for schema_name, old_schema in old_schemas.items():
        new_schema = new_schemas.get(schema_name)
        if new_schema is None:
            # Schema removed -- only breaking if referenced in responses
            issues.append(f"REMOVED SCHEMA: {schema_name}")
            continue

        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        old_props = set(old_schema.get("properties", {}).keys())
        new_props = set(new_schema.get("properties", {}).keys())

        # Required field removed from schema properties
        for field in old_required:
            if field in old_props and field not in new_props:
                issues.append(
                    f"REMOVED REQUIRED FIELD: {schema_name}.{field}"
                )

        # New required field added (breaking for request schemas --
        # existing clients won't send it). We flag it as a warning.
        added_required = new_required - old_required
        for field in added_required:
            if field in new_props and field not in old_props:
                issues.append(
                    f"NEW REQUIRED FIELD: {schema_name}.{field} "
                    f"(breaks existing clients that do not send it)"
                )

        # Property type changed
        old_properties = old_schema.get("properties", {})
        new_properties = new_schema.get("properties", {})
        for prop_name in old_properties:
            if prop_name not in new_properties:
                if prop_name in old_required:
                    pass  # already flagged above
                continue
            old_type = old_properties[prop_name].get("type")
            new_type = new_properties[prop_name].get("type")
            if old_type and new_type and old_type != new_type:
                issues.append(
                    f"CHANGED FIELD TYPE: {schema_name}.{prop_name} "
                    f"({old_type} -> {new_type})"
                )

    return issues


def main() -> None:
    committed_path = sys.argv[1]
    generated_path = sys.argv[2]
    verbose = sys.argv[3] == "1"

    old_spec = load_spec(committed_path)
    new_spec = load_spec(generated_path)

    # Quick check: identical specs
    if old_spec == new_spec:
        print("RESULT:IDENTICAL")
        sys.exit(0)

    issues = find_breaking_changes(old_spec, new_spec)

    if not issues:
        # Non-breaking changes only (new endpoints, new optional fields, etc.)
        print("RESULT:NON_BREAKING")
        if verbose:
            # Show what was added
            old_paths = set(old_spec.get("paths", {}).keys())
            new_paths = set(new_spec.get("paths", {}).keys())
            added = new_paths - old_paths
            if added:
                print(f"  New endpoints: {', '.join(sorted(added))}")

            old_schemas = set(
                old_spec.get("components", {}).get("schemas", {}).keys()
            )
            new_schemas = set(
                new_spec.get("components", {}).get("schemas", {}).keys()
            )
            added_schemas = new_schemas - old_schemas
            if added_schemas:
                print(f"  New schemas: {', '.join(sorted(added_schemas))}")
        sys.exit(0)

    # Breaking changes found
    print(f"RESULT:BREAKING:{len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    sys.exit(1)


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

DIFF_EXIT=$?

if [[ ${DIFF_EXIT} -eq 0 ]]; then
    ok "No breaking API changes detected."
    exit 0
else
    BREAKING=1
fi

# -------------------------------------------------------------------
# Step 3: Report
# -------------------------------------------------------------------
if [[ ${BREAKING} -eq 1 ]]; then
    echo ""
    fail "Breaking API changes detected!"
    echo ""
    echo "To resolve this, either:"
    echo "  1. Revert the breaking change in your backend code, OR"
    echo "  2. If the break is intentional, regenerate and commit the spec:"
    echo "       cd backend && python scripts/export_openapi.py"
    echo "       git add docs/api/openapi.json"
    echo ""
    exit 1
fi
