#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://127.0.0.1:9090}"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUTPUT="${STATUS_PAGE_OUTPUT:-${ROOT_DIR}/docs/evidence/status-page/status-page-data.json}"

mkdir -p "$(dirname "${OUTPUT}")"

query_prometheus() {
  local query="$1"
  curl -fsS --get "${PROMETHEUS_URL}/api/v1/query" --data-urlencode "query=${query}"
}

if ! command -v jq >/dev/null 2>&1; then
  printf 'ERROR: jq is required to export status page data\n' >&2
  exit 1
fi

success_json="$(query_prometheus 'stage2:status_public_endpoint_success_ratio:5m')"
tls_json="$(query_prometheus 'stage2:tls_cert_min_days')"
failures_json="$(query_prometheus 'stage2:synthetic_failures:15m')"
slow_json="$(query_prometheus 'stage2:synthetic_slow_probes:15m')"
customer_edge_json="$(query_prometheus 'stage2:customer_edge_success_ratio:5m')"
home_ops_json="$(query_prometheus 'stage2:home_ops_edge_success_ratio:5m')"
subscription_route_json="$(query_prometheus 'stage2:subscription_route_success_ratio:5m')"
vpn_node_json="$(query_prometheus 'stage2:vpn_node_tcp_success_ratio:5m')"

jq -n \
  --arg generated_at "${STAMP}" \
  --arg prometheus_url "${PROMETHEUS_URL}" \
  --argjson success "${success_json}" \
  --argjson tls "${tls_json}" \
  --argjson failures "${failures_json}" \
  --argjson slow "${slow_json}" \
  --argjson customer_edge "${customer_edge_json}" \
  --argjson home_ops "${home_ops_json}" \
  --argjson subscription_route "${subscription_route_json}" \
  --argjson vpn_node "${vpn_node_json}" \
  '{
    generated_at: $generated_at,
    source: "prometheus",
    prometheus_url: $prometheus_url,
    project: "cybervpn",
    public_scope: "cyber-vpn.net customer edge, cyber-vpn.org subscription/VPN delivery, and *.h.cyber-vpn.net home ops",
    status: {
      public_endpoint_success_ratio_5m: ($success.data.result[0].value[1] // "0"),
      customer_edge_success_ratio_5m: ($customer_edge.data.result[0].value[1] // "0"),
      subscription_route_success_ratio_5m: ($subscription_route.data.result[0].value[1] // "0"),
      vpn_node_tcp_success_ratio_5m: ($vpn_node.data.result[0].value[1] // "0"),
      home_ops_edge_success_ratio_5m: ($home_ops.data.result[0].value[1] // "0"),
      tls_cert_min_days: ($tls.data.result[0].value[1] // "0"),
      synthetic_failures_15m: ($failures.data.result[0].value[1] // "0"),
      synthetic_slow_probes_15m: ($slow.data.result[0].value[1] // "0")
    },
    notes: [
      "This file is a data source for a status page, not a public incident report.",
      "Do not include non-CyberVPN domains or internal-only service details here.",
      "The .org zone is used for subscription delivery and VPN node records, not as a general website mirror."
    ]
  }' > "${OUTPUT}"

printf '%s\n' "${OUTPUT}"
