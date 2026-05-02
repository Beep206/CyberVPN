#!/usr/bin/env bash
set -euo pipefail

umask 077

usage() {
  cat <<'EOF'
Usage:
  capture_opentofu_cutover_evidence.sh \
    --stack-dir <path> \
    --backend-config <path> \
    [--var-file <path>] \
    [--tofu-bin <path-or-name>] \
    [--evidence-dir <path>] \
    [--lock-timeout <duration>] \
    [--write-plan-json]

Purpose:
  Initialize a real OpenTofu backend for one stack, pull a state backup, run a
  reviewed plan, and archive the resulting evidence bundle.

Notes:
  - This script is for operator-approved live backend validation.
  - It does not run apply.
  - The generated state backup is sensitive.
  - The optional plan JSON is also sensitive because OpenTofu may include
    sensitive values in plain text.
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_DIR=""
BACKEND_CONFIG=""
VAR_FILE=""
TOFU_BIN="${TOFU_BIN:-tofu}"
EVIDENCE_DIR=""
LOCK_TIMEOUT="60s"
WRITE_PLAN_JSON=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack-dir)
      STACK_DIR="${2:-}"
      shift 2
      ;;
    --backend-config)
      BACKEND_CONFIG="${2:-}"
      shift 2
      ;;
    --var-file)
      VAR_FILE="${2:-}"
      shift 2
      ;;
    --tofu-bin)
      TOFU_BIN="${2:-}"
      shift 2
      ;;
    --evidence-dir)
      EVIDENCE_DIR="${2:-}"
      shift 2
      ;;
    --lock-timeout)
      LOCK_TIMEOUT="${2:-}"
      shift 2
      ;;
    --write-plan-json)
      WRITE_PLAN_JSON=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$STACK_DIR" || -z "$BACKEND_CONFIG" ]]; then
  echo "Both --stack-dir and --backend-config are required." >&2
  usage >&2
  exit 1
fi

if ! command -v "$TOFU_BIN" >/dev/null 2>&1; then
  echo "OpenTofu binary not found: $TOFU_BIN" >&2
  exit 1
fi

STACK_DIR="$(realpath "$STACK_DIR")"
BACKEND_CONFIG="$(realpath "$BACKEND_CONFIG")"

if [[ ! -d "$STACK_DIR" ]]; then
  echo "Stack directory does not exist: $STACK_DIR" >&2
  exit 1
fi

if [[ ! -f "$BACKEND_CONFIG" ]]; then
  echo "Backend config does not exist: $BACKEND_CONFIG" >&2
  exit 1
fi

if [[ -n "$VAR_FILE" ]]; then
  VAR_FILE="$(realpath "$VAR_FILE")"
  if [[ ! -f "$VAR_FILE" ]]; then
    echo "Var file does not exist: $VAR_FILE" >&2
    exit 1
  fi
fi

stack_slug="$(printf '%s' "$STACK_DIR" | sed 's#^.*/terraform/live/##; s#[/ ]#-#g')"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -z "$EVIDENCE_DIR" ]]; then
  EVIDENCE_DIR="$ROOT_DIR/artifacts/opentofu-cutover/$stack_slug/$timestamp"
else
  EVIDENCE_DIR="$(realpath -m "$EVIDENCE_DIR")"
fi

mkdir -p "$EVIDENCE_DIR"

plan_file="$EVIDENCE_DIR/tfplan"
state_backup="$EVIDENCE_DIR/remote-state-backup.tfstate"
state_backup_sha="$EVIDENCE_DIR/remote-state-backup.tfstate.sha256"
plan_status_file="$EVIDENCE_DIR/plan.status"
plan_exit_file="$EVIDENCE_DIR/plan.exitcode"

cat > "$EVIDENCE_DIR/metadata.env" <<EOF
timestamp_utc=$timestamp
stack_dir=$STACK_DIR
stack_slug=$stack_slug
backend_config=$BACKEND_CONFIG
var_file=${VAR_FILE:-}
tofu_bin=$TOFU_BIN
lock_timeout=$LOCK_TIMEOUT
write_plan_json=$WRITE_PLAN_JSON
EOF

printf '%s\n' "$TOFU_BIN version" > "$EVIDENCE_DIR/tofu-version.command.txt"
"$TOFU_BIN" version > "$EVIDENCE_DIR/tofu-version.txt"

printf '%s\n' "$TOFU_BIN -chdir=$STACK_DIR init -input=false -no-color -backend-config=$BACKEND_CONFIG" \
  > "$EVIDENCE_DIR/init.command.txt"
"$TOFU_BIN" -chdir="$STACK_DIR" init -input=false -no-color -backend-config="$BACKEND_CONFIG" \
  > "$EVIDENCE_DIR/init.log" 2>&1

printf '%s\n' "$TOFU_BIN -chdir=$STACK_DIR state pull" > "$EVIDENCE_DIR/state-pull.command.txt"
"$TOFU_BIN" -chdir="$STACK_DIR" state pull > "$state_backup"
sha256sum "$state_backup" > "$state_backup_sha"

plan_cmd=(
  "$TOFU_BIN"
  "-chdir=$STACK_DIR"
  plan
  -input=false
  -no-color
  "-lock-timeout=$LOCK_TIMEOUT"
  "-out=$plan_file"
)

if [[ -n "$VAR_FILE" ]]; then
  plan_cmd+=("-var-file=$VAR_FILE")
fi

printf '%q ' "${plan_cmd[@]}" > "$EVIDENCE_DIR/plan.command.txt"
printf '\n' >> "$EVIDENCE_DIR/plan.command.txt"

set +e
"${plan_cmd[@]}" > "$EVIDENCE_DIR/plan.log" 2>&1
plan_exit_code=$?
set -e

printf '%s\n' "$plan_exit_code" > "$plan_exit_file"

case "$plan_exit_code" in
  0)
    printf '%s\n' "no_changes" > "$plan_status_file"
    ;;
  2)
    printf '%s\n' "changes_present" > "$plan_status_file"
    ;;
  *)
    printf '%s\n' "failed" > "$plan_status_file"
    echo "OpenTofu plan failed; see $EVIDENCE_DIR/plan.log" >&2
    exit "$plan_exit_code"
    ;;
esac

printf '%s\n' "$TOFU_BIN show -no-color $plan_file" > "$EVIDENCE_DIR/plan-show.command.txt"
"$TOFU_BIN" show -no-color "$plan_file" > "$EVIDENCE_DIR/plan.txt"

if [[ "$WRITE_PLAN_JSON" -eq 1 ]]; then
  printf '%s\n' "$TOFU_BIN show -json $plan_file" > "$EVIDENCE_DIR/plan-json.command.txt"
  "$TOFU_BIN" show -json "$plan_file" > "$EVIDENCE_DIR/plan.json"
fi

cat > "$EVIDENCE_DIR/README.md" <<EOF
# OpenTofu Cutover Evidence Bundle

- timestamp (UTC): $timestamp
- stack: $stack_slug
- stack dir: $STACK_DIR
- backend config path: $BACKEND_CONFIG
- var file path: ${VAR_FILE:-not supplied}
- plan status: $(cat "$plan_status_file")
- plan exit code: $plan_exit_code

Sensitive artifacts in this directory:

- remote-state-backup.tfstate
- remote-state-backup.tfstate.sha256
$(if [[ "$WRITE_PLAN_JSON" -eq 1 ]]; then printf '%s\n' '- plan.json'; fi)

Generated files:

- metadata.env
- tofu-version.txt
- init.log
- plan.log
- plan.txt
- tfplan

This bundle is intended to be copied into the corresponding evidence archive or
referenced from the packet evidence pack.
EOF

echo "Wrote OpenTofu cutover evidence to: $EVIDENCE_DIR"
