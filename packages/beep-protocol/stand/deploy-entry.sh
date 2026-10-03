#!/usr/bin/env bash
# Bring up (or tear down) one Beep entry point (stage 4, task 4).
#
# Starts the cover site (Caddy) and the Beep node behind it with a single
# command, so a burned address can be replaced in minutes. Caddy owns the
# public port and certificate and forwards only gated requests to the node on
# loopback; the node runs with --behind-proxy. A baseline protocol (Xray) is
# deployed separately via BASELINE_DEPLOY_CMD if provided.
#
# Usage:
#   stand/deploy-entry.sh start
#   stand/deploy-entry.sh stop
#
# Required env for `start`:
#   BEEP_COVER_DOMAIN        real domain pointed at this host (Caddy gets a cert)
#   BEEP_COVER_SITE_ROOT     directory of real cover-site content
#   BEEP_COVER_HEADER_VALUE  the secret header value (a long random string)
#   BEEP_NODE_PROFILE        wire profile .toml the node loads
#   BEEP_NODE_TOKENS         file of accepted client tokens
#   BEEP_NODE_KEY            file with the node Ed25519 secret (hex)
#   BEEP_LEAF_CERT           PEM of the leaf cert Caddy serves (for the node's
#                            transport binding); see README for where Caddy
#                            stores it.
# Optional:
#   BEEP_COVER_PATH          secret path (default /static/chunk-7f3a91c2.js)
#   BEEP_COVER_HEADER_NAME   secret header name (default x-edge-token)
#   BEEP_NODE_PORT           node loopback port (default 4443)
#   CADDY_BIN / NODE_BIN     binary paths (defaults: caddy, target/release/beep-node)
#   BASELINE_DEPLOY_CMD      command to bring up the baseline protocol
set -euo pipefail

die() { echo "deploy-entry: $*" >&2; exit 1; }

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_PKG=$(cd "$SCRIPT_DIR/.." && pwd)          # packages/beep-protocol
CADDYFILE="$REPO_PKG/cover-site/Caddyfile.production.template"
RUN_DIR=${RUN_DIR:-"$SCRIPT_DIR/.run"}
mkdir -p "$RUN_DIR"

CADDY_BIN=${CADDY_BIN:-caddy}
NODE_BIN=${NODE_BIN:-"$REPO_PKG/target/release/beep-node"}

start() {
  : "${BEEP_COVER_DOMAIN:?set BEEP_COVER_DOMAIN}"
  : "${BEEP_COVER_SITE_ROOT:?set BEEP_COVER_SITE_ROOT}"
  : "${BEEP_COVER_HEADER_VALUE:?set BEEP_COVER_HEADER_VALUE}"
  : "${BEEP_NODE_PROFILE:?set BEEP_NODE_PROFILE}"
  : "${BEEP_NODE_TOKENS:?set BEEP_NODE_TOKENS}"
  : "${BEEP_NODE_KEY:?set BEEP_NODE_KEY}"
  : "${BEEP_LEAF_CERT:?set BEEP_LEAF_CERT}"

  export BEEP_COVER_DOMAIN BEEP_COVER_SITE_ROOT BEEP_COVER_HEADER_VALUE
  export BEEP_COVER_PATH=${BEEP_COVER_PATH:-/static/chunk-7f3a91c2.js}
  export BEEP_COVER_HEADER_NAME=${BEEP_COVER_HEADER_NAME:-x-edge-token}
  export BEEP_NODE_PORT=${BEEP_NODE_PORT:-4443}

  command -v "$CADDY_BIN" >/dev/null 2>&1 || die "caddy not found ($CADDY_BIN)"
  [ -x "$NODE_BIN" ] || die "beep-node not built at $NODE_BIN"
  [ -f "$CADDYFILE" ] || die "missing $CADDYFILE"
  [ -f "$BEEP_LEAF_CERT" ] || die "leaf cert not found: $BEEP_LEAF_CERT"

  echo "validating Caddyfile..."
  "$CADDY_BIN" validate --config "$CADDYFILE" --adapter caddyfile >/dev/null \
    || die "Caddyfile did not validate"

  echo "starting Caddy for $BEEP_COVER_DOMAIN (node loopback :$BEEP_NODE_PORT)..."
  nohup "$CADDY_BIN" run --config "$CADDYFILE" --adapter caddyfile \
    >"$RUN_DIR/caddy.log" 2>&1 &
  echo $! > "$RUN_DIR/caddy.pid"

  echo "starting beep-node behind the proxy..."
  nohup "$NODE_BIN" --behind-proxy "$BEEP_LEAF_CERT" \
    --profile "$BEEP_NODE_PROFILE" --tokens "$BEEP_NODE_TOKENS" \
    --node-key "$BEEP_NODE_KEY" --port "$BEEP_NODE_PORT" \
    >"$RUN_DIR/node.log" 2>&1 &
  echo $! > "$RUN_DIR/node.pid"

  if [ -n "${BASELINE_DEPLOY_CMD:-}" ]; then
    echo "starting baseline protocol..."
    nohup bash -c "$BASELINE_DEPLOY_CMD" >"$RUN_DIR/baseline.log" 2>&1 &
    echo $! > "$RUN_DIR/baseline.pid"
  fi

  echo "entry point up. logs in $RUN_DIR; stop with: $0 stop"
}

stop() {
  for svc in node caddy baseline; do
    pidfile="$RUN_DIR/$svc.pid"
    if [ -f "$pidfile" ]; then
      pid=$(cat "$pidfile")
      if kill "$pid" 2>/dev/null; then echo "stopped $svc ($pid)"; fi
      rm -f "$pidfile"
    fi
  done
}

case "${1:-}" in
  start) start ;;
  stop)  stop ;;
  *) die "usage: $0 start|stop" ;;
esac
