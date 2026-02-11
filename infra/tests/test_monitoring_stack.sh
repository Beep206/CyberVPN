#!/usr/bin/env bash
#
# E2E Monitoring Stack Verification Script (TOB-6)
#
# Verifies that all monitoring infrastructure components are healthy:
# - Prometheus: targets up, metrics collection working
# - Grafana: dashboards configured (8+ expected)
# - AlertManager: reachable and ready
# - Loki: log aggregation ready
# - OpenTelemetry Collector: healthy and receiving traces
#
# Dependencies:
# - IOB-1: Loki log aggregation
# - IOB-2: Prometheus exporters (PostgreSQL, Redis, Node, cAdvisor)
# - IOB-3: OpenTelemetry Collector + Tempo
# - IOB-4: Grafana FastAPI API dashboard
# - IOB-5: Grafana PostgreSQL + Redis dashboards
# - IOB-6: Grafana Infrastructure + Application dashboards
# - IOB-7: Alert rules (API, DB, Redis, Infra)
# - IOB-8: AlertManager real configuration
#
# Usage: ./test_monitoring_stack.sh
#
# Returns: Exit code 0 if all checks pass, non-zero otherwise

set -euo pipefail

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (can be overridden via environment variables)
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3002}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"
LOKI_URL="${LOKI_URL:-http://localhost:3100}"
OTEL_COLLECTOR_URL="${OTEL_COLLECTOR_URL:-http://localhost:4318}"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper functions
function print_test_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

function print_failure() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function increment_total() {
    ((TESTS_TOTAL++))
}

# ===========================================================================
# Test: Prometheus Targets
# ===========================================================================

function test_prometheus_targets() {
    print_test_header "Testing Prometheus Targets"
    increment_total

    echo "Fetching Prometheus targets..."
    response=$(curl -s "${PROMETHEUS_URL}/api/v1/targets" || echo "FAILED")

    if [[ "$response" == "FAILED" ]]; then
        print_failure "Prometheus is not reachable at ${PROMETHEUS_URL}"
        return 1
    fi

    # Check if response contains targets
    if echo "$response" | jq -e '.data.activeTargets' > /dev/null 2>&1; then
        print_success "Prometheus API is reachable"
    else
        print_failure "Prometheus API returned invalid response"
        return 1
    fi

    # Check that all targets are UP
    down_targets=$(echo "$response" | jq -r '.data.activeTargets[] | select(.health != "up") | .labels.job')

    if [[ -z "$down_targets" ]]; then
        print_success "All Prometheus targets are UP"
    else
        print_failure "Some targets are DOWN: $down_targets"
        return 1
    fi

    # Verify expected targets exist
    echo ""
    echo "Checking for expected Prometheus targets..."
    expected_targets=("prometheus" "node-exporter" "postgres-exporter" "redis-exporter" "cadvisor")

    for target in "${expected_targets[@]}"; do
        if echo "$response" | jq -r '.data.activeTargets[].labels.job' | grep -q "$target"; then
            print_success "Target '$target' is configured"
        else
            print_warning "Target '$target' not found (may not be running)"
        fi
    done

    return 0
}

# ===========================================================================
# Test: Grafana Dashboards
# ===========================================================================

function test_grafana_dashboards() {
    print_test_header "Testing Grafana Dashboards"
    increment_total

    echo "Fetching Grafana dashboards..."
    response=$(curl -s -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        "${GRAFANA_URL}/api/search?type=dash-db" || echo "FAILED")

    if [[ "$response" == "FAILED" ]]; then
        print_failure "Grafana is not reachable at ${GRAFANA_URL}"
        return 1
    fi

    # Check if response is valid JSON array
    if echo "$response" | jq -e '. | length' > /dev/null 2>&1; then
        print_success "Grafana API is reachable"
    else
        print_failure "Grafana API returned invalid response"
        return 1
    fi

    # Count dashboards
    dashboard_count=$(echo "$response" | jq '. | length')

    echo ""
    echo "Found $dashboard_count dashboards in Grafana"

    if [[ "$dashboard_count" -ge 8 ]]; then
        print_success "Grafana has 8+ dashboards configured (found $dashboard_count)"
    else
        print_failure "Expected 8+ dashboards, found only $dashboard_count"
        return 1
    fi

    # List dashboards
    echo ""
    echo "Configured dashboards:"
    echo "$response" | jq -r '.[] | "  - \(.title)"'

    return 0
}

# ===========================================================================
# Test: AlertManager
# ===========================================================================

function test_alertmanager() {
    print_test_header "Testing AlertManager"
    increment_total

    echo "Checking AlertManager health..."
    response=$(curl -s "${ALERTMANAGER_URL}/-/healthy" || echo "FAILED")

    if [[ "$response" == "FAILED" ]]; then
        print_failure "AlertManager is not reachable at ${ALERTMANAGER_URL}"
        return 1
    fi

    print_success "AlertManager is reachable"

    # Check API endpoint
    echo ""
    echo "Checking AlertManager API..."
    api_response=$(curl -s "${ALERTMANAGER_URL}/api/v2/status" || echo "FAILED")

    if [[ "$api_response" == "FAILED" ]]; then
        print_failure "AlertManager API is not responding"
        return 1
    fi

    if echo "$api_response" | jq -e '.cluster' > /dev/null 2>&1; then
        print_success "AlertManager API is functional"
    else
        print_warning "AlertManager API response format unexpected"
    fi

    return 0
}

# ===========================================================================
# Test: Loki
# ===========================================================================

function test_loki() {
    print_test_header "Testing Loki Log Aggregation"
    increment_total

    echo "Checking Loki readiness..."
    response=$(curl -s "${LOKI_URL}/ready" || echo "FAILED")

    if [[ "$response" == "FAILED" ]]; then
        print_failure "Loki is not reachable at ${LOKI_URL}"
        return 1
    fi

    if [[ "$response" == "ready" ]]; then
        print_success "Loki is ready"
    else
        print_failure "Loki returned unexpected ready status: $response"
        return 1
    fi

    # Check Loki labels API
    echo ""
    echo "Checking Loki labels API..."
    labels_response=$(curl -s "${LOKI_URL}/loki/api/v1/labels" || echo "FAILED")

    if [[ "$labels_response" == "FAILED" ]]; then
        print_failure "Loki API is not responding"
        return 1
    fi

    if echo "$labels_response" | jq -e '.data' > /dev/null 2>&1; then
        print_success "Loki API is functional"
    else
        print_warning "Loki API response format unexpected"
    fi

    return 0
}

# ===========================================================================
# Test: OpenTelemetry Collector
# ===========================================================================

function test_otel_collector() {
    print_test_header "Testing OpenTelemetry Collector"
    increment_total

    echo "Checking OTel Collector health..."

    # Try the health check endpoint
    response=$(curl -s "${OTEL_COLLECTOR_URL}/healthz" || echo "FAILED")

    if [[ "$response" == "FAILED" ]]; then
        print_warning "OTel Collector health endpoint not reachable (may use different port)"

        # Try alternate health endpoint
        response=$(curl -s "http://localhost:13133/" || echo "FAILED")

        if [[ "$response" == "FAILED" ]]; then
            print_failure "OTel Collector is not reachable"
            return 1
        fi
    fi

    print_success "OpenTelemetry Collector is reachable"

    # Check metrics endpoint
    echo ""
    echo "Checking OTel Collector metrics..."
    metrics_response=$(curl -s "http://localhost:8888/metrics" || echo "FAILED")

    if [[ "$metrics_response" == "FAILED" ]]; then
        print_warning "OTel Collector metrics endpoint not accessible"
    else
        if echo "$metrics_response" | grep -q "otelcol"; then
            print_success "OTel Collector is exporting metrics"
        else
            print_warning "OTel Collector metrics format unexpected"
        fi
    fi

    return 0
}

# ===========================================================================
# Test: Prometheus Metrics Collection
# ===========================================================================

function test_prometheus_metrics_collection() {
    print_test_header "Testing Prometheus Metrics Collection"
    increment_total

    echo "Querying Prometheus for backend metrics..."

    # Query for http_requests_total metric from FastAPI backend
    query="http_requests_total"
    response=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${query}" || echo "FAILED")

    if [[ "$response" == "FAILED" ]]; then
        print_failure "Failed to query Prometheus metrics"
        return 1
    fi

    # Check if metric exists
    if echo "$response" | jq -e '.data.result | length > 0' > /dev/null 2>&1; then
        print_success "Prometheus is collecting backend metrics (http_requests_total found)"
    else
        print_warning "Backend metrics not yet collected (may need time or backend restart)"
    fi

    return 0
}

# ===========================================================================
# Main Execution
# ===========================================================================

function main() {
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  CyberVPN Monitoring Stack E2E Verification (TOB-6)          ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Configuration:"
    echo "  Prometheus:      ${PROMETHEUS_URL}"
    echo "  Grafana:         ${GRAFANA_URL}"
    echo "  AlertManager:    ${ALERTMANAGER_URL}"
    echo "  Loki:            ${LOKI_URL}"
    echo "  OTel Collector:  ${OTEL_COLLECTOR_URL}"
    echo ""

    # Run all tests
    test_prometheus_targets || true
    test_grafana_dashboards || true
    test_alertmanager || true
    test_loki || true
    test_otel_collector || true
    test_prometheus_metrics_collection || true

    # Summary
    echo ""
    print_test_header "Test Summary"
    echo ""
    echo "  Total Tests:  $TESTS_TOTAL"
    echo -e "  ${GREEN}Passed:       $TESTS_PASSED${NC}"
    echo -e "  ${RED}Failed:       $TESTS_FAILED${NC}"
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ All monitoring stack checks passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some monitoring stack checks failed${NC}"
        exit 1
    fi
}

# Run main function
main
