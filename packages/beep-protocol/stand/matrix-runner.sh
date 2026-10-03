#!/usr/bin/env bash
# Matrix runner for the Beep test bench (stage 4, task 3).
#
# Runs a series for each cell "network x entry point x profile": a control
# download, a Beep session, and (optionally) a baseline protocol, interleaved
# inside one window so the three are compared under the same conditions. It
# honours the clean-measurement pauses, captures traffic on the client side
# when tcpdump is available, and writes every attempt's JSON events into one
# raw directory that aggregate.py folds into a single results file.
#
# This orchestrates the client side only. Entry points (Caddy + beep-node, and
# any baseline) are brought up with deploy-entry.sh on the servers. A full run
# needs real entry points; see README.md.
#
# Usage:
#   stand/matrix-runner.sh CELLS_FILE OUT_DIR [ATTEMPTS]
#
# Environment overrides:
#   BEEP_CLIENT       path to the beep-client binary (default: target/release/beep-client)
#   INSECURE=1        pass --insecure to the client (lab self-signed certs)
#   MIN_GAP_SECS      min pause between attempts to one domain (default 120)
#   FREEZE_PAUSE_SECS pause after a suspected freeze (default 600)
#   BEEP_HOLD_SECS    how long to hold a Beep session open (default 60)
#   BASELINE_CMD      command template for the baseline protocol attempt; the
#                     tokens {entry} {port} {domain} {out} are substituted.
#                     Unset means the baseline leg is skipped.
set -euo pipefail

die() { echo "matrix-runner: $*" >&2; exit 1; }

[ $# -ge 2 ] || die "usage: $0 CELLS_FILE OUT_DIR [ATTEMPTS]"
CELLS_FILE=$1
OUT_DIR=$2
ATTEMPTS=${3:-5}

BEEP_CLIENT=${BEEP_CLIENT:-target/release/beep-client}
MIN_GAP_SECS=${MIN_GAP_SECS:-120}
FREEZE_PAUSE_SECS=${FREEZE_PAUSE_SECS:-600}
BEEP_HOLD_SECS=${BEEP_HOLD_SECS:-60}
INSECURE_FLAG=""
[ "${INSECURE:-0}" = "1" ] && INSECURE_FLAG="--insecure"

[ -f "$CELLS_FILE" ] || die "cells file not found: $CELLS_FILE"
command -v "$BEEP_CLIENT" >/dev/null 2>&1 || [ -x "$BEEP_CLIENT" ] \
  || die "beep-client not found/executable at: $BEEP_CLIENT (build it, or set BEEP_CLIENT)"

RAW_DIR="$OUT_DIR/raw"
mkdir -p "$RAW_DIR"
INDEX="$OUT_DIR/index.tsv"
: > "$INDEX"
echo -e "# cell\tnetwork\tentry\tport\tdomain\tprofile\tkind\tattempt\tevent_log\tpcap" >> "$INDEX"

have_tcpdump() { command -v tcpdump >/dev/null 2>&1; }

start_capture() { # <pcap> <host>
  have_tcpdump || { echo ""; return; }
  tcpdump -i any -w "$1" "host $2" >/dev/null 2>&1 &
  echo $!
}
stop_capture() { [ -n "${1:-}" ] && kill "$1" 2>/dev/null || true; }

# Read cells: TAB-separated "network entry port domain profile token control_path".
# Lines starting with # and blank lines are ignored.
line_no=0
while IFS=$'\t' read -r network entry port domain profile token control_path _rest || [ -n "${network:-}" ]; do
  line_no=$((line_no + 1))
  case "${network:-}" in ''|'#'*) continue ;; esac
  [ -n "${entry:-}" ] && [ -n "${port:-}" ] && [ -n "${profile:-}" ] \
    || die "cell on line $line_no is missing fields (need network entry port domain profile token control_path)"

  cell="${network}__${domain:-nodomain}__$(basename "$profile" .toml)"
  echo "== cell: $cell ($entry:$port, profile $profile) =="

  for ((n = 1; n <= ATTEMPTS; n++)); do
    # Interleave the three traffic kinds inside one window.
    for kind in control beep baseline; do
      ev="$RAW_DIR/${cell}__${kind}__${n}.jsonl"
      pcap="$RAW_DIR/${cell}__${kind}__${n}.pcap"
      : > "$ev"
      cap_pid=$(start_capture "$pcap" "$entry")

      case "$kind" in
        control)
          "$BEEP_CLIENT" --control-download "${control_path:-/}" \
            --server "$entry:$port" --profile "$profile" \
            --event-log "$ev" $INSECURE_FLAG || true
          ;;
        beep)
          # Hold a session open; the event log records handshake timing,
          # byte totals, stalls and the close reason. Routing real traffic
          # through the tunnel is a deployment detail of the client host.
          timeout "$BEEP_HOLD_SECS" "$BEEP_CLIENT" \
            --server "$entry:$port" --profile "$profile" \
            --token "${token:-}" --event-log "$ev" $INSECURE_FLAG || true
          ;;
        baseline)
          if [ -n "${BASELINE_CMD:-}" ]; then
            cmd=${BASELINE_CMD//\{entry\}/$entry}
            cmd=${cmd//\{port\}/$port}
            cmd=${cmd//\{domain\}/${domain:-}}
            cmd=${cmd//\{out\}/$ev}
            bash -c "$cmd" || true
          else
            stop_capture "$cap_pid"
            continue
          fi
          ;;
      esac

      stop_capture "$cap_pid"
      echo -e "${cell}\t${network}\t${entry}\t${port}\t${domain:-}\t${profile}\t${kind}\t${n}\t${ev}\t$([ -f "$pcap" ] && echo "$pcap" || echo "-")" >> "$INDEX"

      # Clean-measurement pause before the next attempt to this domain.
      if grep -qi "stall" "$ev" 2>/dev/null; then
        echo "  (suspected freeze on $kind #$n; pausing ${FREEZE_PAUSE_SECS}s)"
        sleep "$FREEZE_PAUSE_SECS"
      else
        sleep "$MIN_GAP_SECS"
      fi
    done
  done
  # reset loop vars so the `|| [ -n ... ]` guard behaves on the last line
  network=""; entry=""; port=""; domain=""; profile=""; token=""; control_path=""
done < "$CELLS_FILE"

echo "== aggregating =="
if command -v python3 >/dev/null 2>&1; then
  python3 "$(dirname "$0")/aggregate.py" "$INDEX" "$OUT_DIR/results.jsonl"
  echo "results: $OUT_DIR/results.jsonl"
else
  echo "python3 not found; raw events are under $RAW_DIR and indexed in $INDEX"
fi
