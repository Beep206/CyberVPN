#!/usr/bin/env bash
#
# Dashboard Validation Script
#
# Validates Grafana dashboard configuration:
# - Counts dashboard JSON files (must be 11+)
# - Validates JSON syntax for each file
# - Verifies at least one dashboard uses Loki datasource
# - Verifies at least one dashboard uses Tempo datasource
#
# Exit codes:
#   0 - All validations passed
#   1 - Validation failed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DASHBOARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../grafana/dashboards" && pwd)"
ERRORS=0

echo "🔍 Validating Grafana dashboards in: ${DASHBOARD_DIR}"
echo ""

# Check 1: Count dashboard files
echo "📊 Checking dashboard count..."
DASHBOARD_COUNT=$(find "${DASHBOARD_DIR}" -name "*.json" -type f | wc -l)

if [ "${DASHBOARD_COUNT}" -lt 11 ]; then
    echo -e "${RED}✗ FAIL: Expected 11+ dashboards, found ${DASHBOARD_COUNT}${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ PASS: Found ${DASHBOARD_COUNT} dashboard files${NC}"
fi
echo ""

# Check 2: Validate JSON syntax
echo "✅ Validating JSON syntax..."
JSON_ERRORS=0

while IFS= read -r dashboard; do
    if ! jq empty "${dashboard}" 2>/dev/null; then
        echo -e "${RED}✗ FAIL: Invalid JSON in $(basename "${dashboard}")${NC}"
        JSON_ERRORS=$((JSON_ERRORS + 1))
    fi
done < <(find "${DASHBOARD_DIR}" -name "*.json" -type f)

if [ "${JSON_ERRORS}" -gt 0 ]; then
    echo -e "${RED}✗ FAIL: ${JSON_ERRORS} dashboard(s) have invalid JSON${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ PASS: All dashboards have valid JSON syntax${NC}"
fi
echo ""

# Check 3: Loki datasource presence
echo "🔍 Checking for Loki datasource..."
LOKI_COUNT=$(grep -l '"type": "loki"' "${DASHBOARD_DIR}"/*.json 2>/dev/null | wc -l)

if [ "${LOKI_COUNT}" -lt 1 ]; then
    echo -e "${RED}✗ FAIL: No dashboards found with Loki datasource${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ PASS: Found ${LOKI_COUNT} dashboard(s) with Loki datasource${NC}"
    grep -l '"type": "loki"' "${DASHBOARD_DIR}"/*.json 2>/dev/null | while read -r f; do
        echo "  - $(basename "${f}")"
    done
fi
echo ""

# Check 4: Tempo datasource presence
echo "🔍 Checking for Tempo datasource..."
TEMPO_COUNT=$(grep -l '"type": "tempo"' "${DASHBOARD_DIR}"/*.json 2>/dev/null | wc -l)

if [ "${TEMPO_COUNT}" -lt 1 ]; then
    echo -e "${RED}✗ FAIL: No dashboards found with Tempo datasource${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✓ PASS: Found ${TEMPO_COUNT} dashboard(s) with Tempo datasource${NC}"
    grep -l '"type": "tempo"' "${DASHBOARD_DIR}"/*.json 2>/dev/null | while read -r f; do
        echo "  - $(basename "${f}")"
    done
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "${ERRORS}" -eq 0 ]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo -e "${RED}✗ ${ERRORS} validation(s) failed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
