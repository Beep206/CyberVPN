#!/usr/bin/env bash

# CyberVPN Monitoring Stack Verification Script
# Verifies all monitoring services are healthy and properly configured

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  $1"
    echo "═══════════════════════════════════════════════════════════"
}

check_service() {
    local service_name=$1
    local url=$2
    local expected_pattern=$3

    if curl -sf "$url" | grep -q "$expected_pattern" 2>/dev/null; then
        print_success "$service_name is ready"
        return 0
    else
        print_error "$service_name is NOT ready (URL: $url)"
        return 1
    fi
}

# Main verification
print_header "CyberVPN Monitoring Stack Verification"

# 1. Check Prometheus
print_header "1. Prometheus"
if check_service "Prometheus" "http://localhost:9094/-/healthy" "Prometheus Server is Healthy"; then
    # Check Prometheus targets
    TARGETS_UP=$(curl -s http://localhost:9094/api/v1/targets | jq -r '.data.activeTargets | map(select(.health=="up")) | length')
    TARGETS_TOTAL=$(curl -s http://localhost:9094/api/v1/targets | jq -r '.data.activeTargets | length')

    if [ "$TARGETS_UP" -eq "$TARGETS_TOTAL" ] && [ "$TARGETS_TOTAL" -gt 0 ]; then
        print_success "All Prometheus targets are UP ($TARGETS_UP/$TARGETS_TOTAL)"
    else
        print_warning "Some Prometheus targets are DOWN ($TARGETS_UP/$TARGETS_TOTAL UP)"
    fi
fi

# 2. Check Grafana
print_header "2. Grafana"
if check_service "Grafana" "http://localhost:3002/api/health" "ok"; then
    # Check dashboard count
    DASHBOARD_COUNT=$(ls -1 /home/beep/projects/VPNBussiness/infra/grafana/dashboards/*.json 2>/dev/null | wc -l)

    if [ "$DASHBOARD_COUNT" -ge 11 ]; then
        print_success "Grafana has $DASHBOARD_COUNT dashboards (required: 11+)"
    else
        print_error "Grafana has only $DASHBOARD_COUNT dashboards (required: 11+)"
    fi
fi

# 3. Check Loki
print_header "3. Loki"
if check_service "Loki" "http://localhost:3100/ready" "ready"; then
    # Check if Loki rules are mounted
    if [ -d "/home/beep/projects/VPNBussiness/infra/loki/rules/cybervpn" ] && [ -f "/home/beep/projects/VPNBussiness/infra/loki/rules/cybervpn/alerts.yml" ]; then
        print_success "Loki alert rules are present"
    else
        print_warning "Loki alert rules directory not found"
    fi
fi

# 4. Check Tempo
print_header "4. Tempo"
check_service "Tempo" "http://localhost:3200/ready" "ready"

# 5. Check OTEL Collector
print_header "5. OpenTelemetry Collector"
if curl -sf http://localhost:8888/metrics >/dev/null 2>&1; then
    print_success "OTEL Collector is ready"
    ((PASSED++))
else
    print_error "OTEL Collector is NOT ready"
    ((FAILED++))
fi

# 6. Check AlertManager
print_header "6. AlertManager"
check_service "AlertManager" "http://localhost:9093/-/healthy" "Healthy"

# 7. Verify datasources configuration
print_header "7. Grafana Datasources"
DATASOURCES_FILE="/home/beep/projects/VPNBussiness/infra/grafana/provisioning/datasources/datasources.yml"
if [ -f "$DATASOURCES_FILE" ]; then
    DATASOURCE_COUNT=$(grep -c "^  - name:" "$DATASOURCES_FILE")
    if [ "$DATASOURCE_COUNT" -ge 3 ]; then
        print_success "Grafana has $DATASOURCE_COUNT datasources configured (Prometheus, Loki, Tempo)"
    else
        print_warning "Expected 3 datasources, found $DATASOURCE_COUNT"
    fi
else
    print_error "Datasources configuration file not found"
fi

# 8. Verify new dashboards exist
print_header "8. New Dashboards"
DASHBOARD_DIR="/home/beep/projects/VPNBussiness/infra/grafana/dashboards"

if [ -f "$DASHBOARD_DIR/logs-dashboard.json" ]; then
    print_success "Logs Overview dashboard exists"
else
    print_error "Logs Overview dashboard NOT found"
fi

if [ -f "$DASHBOARD_DIR/traces-dashboard.json" ]; then
    print_success "Traces Overview dashboard exists"
else
    print_error "Traces Overview dashboard NOT found"
fi

if [ -f "$DASHBOARD_DIR/slo-dashboard.json" ]; then
    print_success "SLO Tracking dashboard exists"
else
    print_error "SLO Tracking dashboard NOT found"
fi

# 9. Verify healthchecks in docker-compose
print_header "9. Service Healthchecks"
COMPOSE_FILE="/home/beep/projects/VPNBussiness/infra/docker-compose.yml"

if grep -A 5 "prometheus:" "$COMPOSE_FILE" | grep -q "healthcheck:"; then
    print_success "Prometheus healthcheck configured"
else
    print_error "Prometheus healthcheck NOT configured"
fi

if grep -A 5 "grafana:" "$COMPOSE_FILE" | grep -q "healthcheck:"; then
    print_success "Grafana healthcheck configured"
else
    print_error "Grafana healthcheck NOT configured"
fi

# Summary
print_header "Verification Summary"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All checks passed!${NC} Monitoring stack is healthy."
    exit 0
else
    echo -e "\n${RED}Some checks failed.${NC} Please review the errors above."
    exit 1
fi
