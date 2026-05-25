#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_dir="${repo_root}/infra/partner-lab"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_dir="${STAGE3_NATS_EVIDENCE_DIR:-${repo_root}/docs/evidence/partner-platform/stage3-nats-${timestamp}}"

stream_name="${NATS_PARTNER_STREAM_NAME:-PARTNER_EVENTS}"
subject_prefix="${NATS_PARTNER_SUBJECT_PREFIX:-partner}"
consumer_name="${NATS_PARTNER_CONSUMER_NAME:-stage3-proof}"

export NATS_LAB_USER="${NATS_LAB_USER:-stage3_lab}"
export NATS_LAB_PASSWORD="${NATS_LAB_PASSWORD:-$(openssl rand -hex 24)}"
export PARTNER_LAB_POSTGRES_USER="${PARTNER_LAB_POSTGRES_USER:-cybervpn_stage3}"
export PARTNER_LAB_POSTGRES_PASSWORD="${PARTNER_LAB_POSTGRES_PASSWORD:-$(openssl rand -hex 24)}"
export PARTNER_LAB_POSTGRES_DB="${PARTNER_LAB_POSTGRES_DB:-cybervpn_stage3}"

mkdir -p "${evidence_dir}"
evidence_dir="$(cd "$(dirname "${evidence_dir}")" && pwd)/$(basename "${evidence_dir}")"
chmod 0700 "${evidence_dir}"

cleanup() {
  if [[ "${KEEP_STAGE3_NATS_LAB:-0}" != "1" ]]; then
    (
      cd "${compose_dir}"
      docker compose --profile manual down --volumes >/dev/null 2>&1 || true
    )
  fi
}
trap cleanup EXIT

run_box() {
  (
    cd "${compose_dir}"
    docker compose --profile manual run --rm --entrypoint sh partner-nats-box -lc "$*"
  )
}

{
  echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "evidence_dir=${evidence_dir}"
  echo "stream_name=${stream_name}"
  echo "subject_prefix=${subject_prefix}"
  echo "consumer_name=${consumer_name}"
  echo "keep_lab=${KEEP_STAGE3_NATS_LAB:-0}"
} | tee "${evidence_dir}/summary.txt"

(
  cd "${compose_dir}"
  docker compose --profile manual config \
    | python3 -c 'import os, sys; data=sys.stdin.read();
for key in ("NATS_LAB_PASSWORD", "PARTNER_LAB_POSTGRES_PASSWORD"):
    data=data.replace(os.environ[key], "<redacted>")
sys.stdout.write(data)' \
    > "${evidence_dir}/compose.config.yml"
  docker compose --profile manual up -d partner-nats
)

for _ in {1..30}; do
  if curl -fsS "http://127.0.0.1:8222/healthz?js-enabled-only=true" > "${evidence_dir}/healthz.json" 2>"${evidence_dir}/healthz.err"; then
    break
  fi
  sleep 1
done

curl -fsS "http://127.0.0.1:8222/jsz" > "${evidence_dir}/jsz-before.json"

run_box "nats --server \"\$NATS_URL\" stream add \"${stream_name}\" --subjects \"${subject_prefix}.>\" --storage file --retention limits --discard old --max-age 7d --max-msgs 10000 --dupe-window 2m --defaults" \
  > "${evidence_dir}/stream-add.txt"

run_box "nats --server \"\$NATS_URL\" stream info \"${stream_name}\" --json" \
  > "${evidence_dir}/stream-info-after-add.json"

payload='{"event_id":"s3-stage03-proof-001","event_type":"entitlement.grant.activated","event_version":1,"consumer_key":"analytics_mart","aggregate_type":"partner_workspace","aggregate_id":"stage3-nonprod-proof","correlation_id":"s3-stage03-proof-001","idempotency_key":"analytics_mart:s3-stage03-proof-001","payload":{"result":"stage3_nonprod_jetstream_proof"}}'
printf '%s\n' "${payload}" > "${evidence_dir}/published-event.json"

run_box "printf '%s' '${payload}' | nats --server \"\$NATS_URL\" pub \"${subject_prefix}.analytics_mart.entitlement.grant.activated\" --jetstream --force-stdin" \
  > "${evidence_dir}/publish.txt" 2>&1

run_box "nats --server \"\$NATS_URL\" stream info \"${stream_name}\" --json" \
  > "${evidence_dir}/stream-info-after-publish.json"

run_box "nats --server \"\$NATS_URL\" consumer add \"${stream_name}\" \"${consumer_name}\" --filter \"${subject_prefix}.analytics_mart.>\" --ack explicit --pull --deliver all --replay instant --max-deliver 3 --defaults" \
  > "${evidence_dir}/consumer-add.txt"

run_box "nats --server \"\$NATS_URL\" consumer next \"${stream_name}\" \"${consumer_name}\" --count 1 --ack --raw" \
  > "${evidence_dir}/consumer-next.txt" 2>&1

run_box "nats --server \"\$NATS_URL\" consumer info \"${stream_name}\" \"${consumer_name}\" --json" \
  > "${evidence_dir}/consumer-info-after-ack.json"

run_box "nats --server \"\$NATS_URL\" consumer add \"${stream_name}\" \"${consumer_name}-replay\" --filter \"${subject_prefix}.analytics_mart.>\" --ack explicit --pull --deliver all --replay instant --max-deliver 3 --defaults" \
  > "${evidence_dir}/consumer-replay-add.txt"

run_box "nats --server \"\$NATS_URL\" consumer next \"${stream_name}\" \"${consumer_name}-replay\" --count 1 --ack --raw" \
  > "${evidence_dir}/consumer-replay-next.txt" 2>&1

curl -fsS "http://127.0.0.1:8222/jsz?streams=true&consumers=true" > "${evidence_dir}/jsz-after.json"

(
  cd "${compose_dir}"
  docker compose --profile manual ps > "${evidence_dir}/docker-ps.txt"
  docker compose --profile manual logs --no-color partner-nats > "${evidence_dir}/nats.log"
)

sha256sum "${evidence_dir}"/* > "${evidence_dir}/checksums.sha256"

{
  echo "finished_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "status=ok"
  echo "stream_proof=${evidence_dir}/stream-info-after-add.json"
  echo "publish_proof=${evidence_dir}/publish.txt"
  echo "consume_proof=${evidence_dir}/consumer-next.txt"
  echo "replay_proof=${evidence_dir}/consumer-replay-next.txt"
  echo "alert_input_proof=${evidence_dir}/jsz-after.json"
} | tee -a "${evidence_dir}/summary.txt"
