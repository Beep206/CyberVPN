#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_dir="${repo_root}/infra/partner-lab"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_dir="${STAGE3_OUTBOX_EVIDENCE_DIR:-${repo_root}/docs/evidence/partner-platform/stage3-outbox-${timestamp}}"

export NATS_LAB_USER="${NATS_LAB_USER:-stage3_lab}"
export NATS_LAB_PASSWORD="${NATS_LAB_PASSWORD:-$(openssl rand -hex 24)}"
export PARTNER_LAB_POSTGRES_USER="${PARTNER_LAB_POSTGRES_USER:-cybervpn_stage3}"
export PARTNER_LAB_POSTGRES_PASSWORD="${PARTNER_LAB_POSTGRES_PASSWORD:-$(openssl rand -hex 24)}"
export PARTNER_LAB_POSTGRES_DB="${PARTNER_LAB_POSTGRES_DB:-cybervpn_stage3}"

mkdir -p "${evidence_dir}"
evidence_dir="$(cd "$(dirname "${evidence_dir}")" && pwd)/$(basename "${evidence_dir}")"
chmod 0700 "${evidence_dir}"

cleanup() {
  if [[ "${KEEP_STAGE3_OUTBOX_LAB:-0}" != "1" ]]; then
    (
      cd "${compose_dir}"
      docker compose --profile manual down --volumes >/dev/null 2>&1 || true
    )
  fi
}
trap cleanup EXIT

python_bin="${BACKEND_PYTHON:-${repo_root}/backend/.venv/bin/python}"
if [[ ! -x "${python_bin}" ]]; then
  python_bin="python3"
fi

database_url="postgresql+asyncpg://${PARTNER_LAB_POSTGRES_USER}:${PARTNER_LAB_POSTGRES_PASSWORD}@127.0.0.1:6788/${PARTNER_LAB_POSTGRES_DB}"
nats_url="nats://${NATS_LAB_USER}:${NATS_LAB_PASSWORD}@127.0.0.1:4222"

{
  echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "evidence_dir=${evidence_dir}"
  echo "python_bin=${python_bin}"
  echo "keep_lab=${KEEP_STAGE3_OUTBOX_LAB:-0}"
  echo "stream_name=${NATS_PARTNER_STREAM_NAME:-PARTNER_EVENTS}"
  echo "subject_prefix=${NATS_PARTNER_SUBJECT_PREFIX:-partner}"
} | tee "${evidence_dir}/run-summary.txt"

(
  cd "${compose_dir}"
  docker compose --profile manual config \
    | python3 -c 'import os, sys; data=sys.stdin.read();
for key in ("NATS_LAB_PASSWORD", "PARTNER_LAB_POSTGRES_PASSWORD"):
    data=data.replace(os.environ[key], "<redacted>")
sys.stdout.write(data)' \
    > "${evidence_dir}/compose.config.yml"
  docker compose --profile manual up -d partner-postgres partner-nats
)

for _ in {1..60}; do
  if (
    cd "${compose_dir}"
    docker compose --profile manual exec -T partner-postgres \
      pg_isready -U "${PARTNER_LAB_POSTGRES_USER}" -d "${PARTNER_LAB_POSTGRES_DB}"
  ) > "${evidence_dir}/postgres-ready.txt" 2>"${evidence_dir}/postgres-ready.err"; then
    break
  fi
  sleep 1
done

for _ in {1..30}; do
  if curl -fsS "http://127.0.0.1:8222/healthz?js-enabled-only=true" > "${evidence_dir}/nats-healthz.json" 2>"${evidence_dir}/nats-healthz.err"; then
    break
  fi
  sleep 1
done

(
  cd "${repo_root}/backend"
  ENVIRONMENT=stage3-lab \
    DATABASE_URL="${database_url}" \
    PYTHONPATH="${repo_root}/backend" \
    REDIS_URL="redis://127.0.0.1:6379/15" \
    REMNAWAVE_TOKEN="stage3_dummy_remnawave_token" \
    JWT_SECRET="stage3_dummy_jwt_secret_minimum_32_chars" \
    CRYPTOBOT_TOKEN="stage3_dummy_cryptobot_token" \
    PARTNER_EVENT_BACKBONE_ENABLED=true \
    NATS_URL="${nats_url}" \
    NATS_PARTNER_STREAM_NAME="${NATS_PARTNER_STREAM_NAME:-PARTNER_EVENTS}" \
    NATS_PARTNER_SUBJECT_PREFIX="${NATS_PARTNER_SUBJECT_PREFIX:-partner}" \
    OUTBOX_DISPATCH_BATCH_SIZE=20 \
    OUTBOX_DISPATCH_RETRY_AFTER_SECONDS=5 \
    OUTBOX_DISPATCH_DEAD_LETTER_AFTER_ATTEMPTS=5 \
    POSTHOG_ENABLED=false \
    OTEL_ENABLED=false \
    STAGE3_OUTBOX_EVIDENCE_DIR="${evidence_dir}" \
    "${python_bin}" "${repo_root}/scripts/partner/stage3_outbox_dispatcher_proof.py"
) > "${evidence_dir}/python-proof.stdout" 2>"${evidence_dir}/python-proof.stderr"

curl -fsS "http://127.0.0.1:8222/jsz?streams=true&consumers=true" > "${evidence_dir}/nats-jsz-final.json"

(
  cd "${compose_dir}"
  docker compose --profile manual ps > "${evidence_dir}/docker-ps.txt"
  docker compose --profile manual logs --no-color partner-nats > "${evidence_dir}/nats.log"
  docker compose --profile manual logs --no-color partner-postgres > "${evidence_dir}/postgres.log"
)

sha256sum "${evidence_dir}"/* > "${evidence_dir}/checksums.sha256"

{
  echo "finished_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "status=ok"
  echo "summary_json=${evidence_dir}/summary.json"
  echo "db_after_dispatch=${evidence_dir}/db-after-dispatch.json"
  echo "consumer_receipts=${evidence_dir}/consumer-receipts.json"
  echo "dead_letter_proof=${evidence_dir}/dead-letter-proof.json"
  echo "backlog_alert_input=${evidence_dir}/backlog-alert-input.json"
} | tee -a "${evidence_dir}/run-summary.txt"
