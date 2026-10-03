# Beep test bench (stage 4)

Tooling to compare three kinds of traffic — Beep, a control HTTPS download,
and a baseline protocol — on the same addresses, across a matrix of
"network x entry point x profile" cells. The client side is scripted here; the
server side (cover site + node, and any baseline) is brought up per entry point
with `deploy-entry.sh`.

## Pieces

- `deploy-entry.sh` — bring one entry point up or down with a single command:
  Caddy (cover site) on 443 plus `beep-node --behind-proxy` on loopback, and an
  optional baseline via `BASELINE_DEPLOY_CMD`. Run on each server.
- `matrix-runner.sh` — on the client host, run a series for every cell: a
  control download, a Beep session, and (optionally) a baseline attempt,
  interleaved, with the clean-measurement pauses, client-side `tcpdump` capture
  when available, and per-attempt JSON event logs.
- `aggregate.py` — fold all attempts' event logs into one `results.jsonl`,
  tagged by cell, kind and attempt, for analysis.
- `cells.example.tsv` — the matrix format; copy and edit.

## The control download

`beep-client --control-download <path> --server <ip:port> --profile <p>` fetches
a file from the cover site over the **same TLS stack and profile** a Beep
session uses, with no tunnel. It is the baseline the plan's success criterion
compares Beep against: where an ordinary HTTPS load from the same server gets
through, Beep should too. With `--event-log` it records a `control_download`
event (status, bytes, duration) into the same log as Beep sessions.

## Event log

Both the control download and Beep sessions write JSON lines (via
`--event-log`): `handshake_start`/`handshake_end`, periodic `bytes`, `stall`
(a gap over 10 s), `session_closed` (totals and reason), and `control_download`.
Each line carries the profile id and role, so `aggregate.py` can line the three
traffic kinds up per cell.

## Running

Server, per entry point:

```
BEEP_COVER_DOMAIN=updates-a.example.net \
BEEP_COVER_SITE_ROOT=/srv/site \
BEEP_COVER_HEADER_VALUE=<long-random> \
BEEP_NODE_PROFILE=profiles/ru-chrome141.toml \
BEEP_NODE_TOKENS=tokens.txt \
BEEP_NODE_KEY=node.key \
BEEP_LEAF_CERT=/var/lib/caddy/.../updates-a.example.net.crt \
stand/deploy-entry.sh start
```

Client:

```
cargo build --release -p beep-client
cp stand/cells.example.tsv stand/cells.tsv   # then edit for your entries
BEEP_CLIENT=target/release/beep-client \
stand/matrix-runner.sh stand/cells.tsv runs/$(date +%F) 100
```

`aggregate.py` runs automatically at the end, producing `runs/.../results.jsonl`.

## What the owner provides for a real run

- Entry-point servers (plan: a foreign VPS A, a VPS B on a clean network, and
  optionally a VPS C in Russia) with DNS for one domain per profile pointed at
  them, so Caddy can issue real certificates.
- The baseline protocol (Xray VLESS+Reality / VLESS+XHTTP) config, wired in via
  `BASELINE_DEPLOY_CMD` (deploy) and `BASELINE_CMD` (client attempt).
- `tcpdump` on the client (and ideally on the server) for the captures;
  `CAP_NET_RAW`/root is needed to capture.
- A real cover-site content directory (not the lab placeholder).

The node-side leaf certificate path (`BEEP_LEAF_CERT`) is the cert Caddy serves
for the domain; with automatic HTTPS it lives under Caddy's data directory
(e.g. `.../certificates/acme-.../<domain>/<domain>.crt`).
