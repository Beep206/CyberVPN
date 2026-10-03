# Stage-2 cover site

The node no longer terminates TLS or owns the public port. A front proxy
(Caddy) does both: it holds the real certificate, serves ordinary site
content for every request, and reverse-proxies to the node only the one
request shape that carries the secret path, the secret header, and a real
WebSocket upgrade. Everything else — a plain page load, a scanner hitting
common paths, a probe that knows the path or the header but not both, or in
the right shape — gets exactly what the site would give with no node behind
it at all. That last property is this checkpoint: see
`crates/beep-cover-wss/tests/cover_site_probes.rs`, which runs both a
Caddy-with-node and a reference Caddy-without-node instance side by side and
asserts their responses match for a battery of such probes.

## Why gate on the upgrade shape, not just path and header

A request with the right path and the right header but no `Upgrade:
websocket` still has to produce the ordinary 404, not whatever the node
would do with it. The node's WS layer (tungstenite) closes a non-upgrade
request without writing a response at all, which is a different, distinctly
unusual-looking failure from a normal 404 — not something to let a prober
that has guessed the header ever see. `Caddyfile.lab` and
`Caddyfile.production.template` both add `header_regexp ws_upgrade Upgrade
(?i)^websocket$` to the matcher for this reason, so a non-upgrade request
never reaches the node in the first place; the ordinary file server answers
it, same as any other path.

## Transport binding without the node seeing TLS

The Beep session binds itself to the TLS leaf certificate the client
actually saw (`beep_transport::binding_from_leaf`), so a middlebox that
terminates TLS with a different certificate produces a different binding
and the session handshake fails. With Caddy terminating TLS instead of the
node, the node needs that same certificate's DER bytes from somewhere other
than a live TLS connection it no longer has.

`beep-node --behind-proxy <leaf-cert.pem>` reads them from a file: the exact
PEM Caddy is configured to present publicly, readable by the node because
both run on the same machine. This preserves the binding's guarantee
unchanged — a different front proxy certificate still produces a different
binding — at the cost of the operator keeping that path in sync with
whatever Caddy is actually serving (for `tls internal`, Caddy's own locally
managed certs live under its data directory; for a real domain, it's the
leaf Caddy fetched from its ACME issuer).

## Running the lab setup

```
cargo test -p beep-cover-wss --test cover_site_probes
```

This spawns a real `caddy` (must be on `PATH`) with `Caddyfile.lab` twice —
once reverse-proxying to an in-process stand-in for the node (the same
`WsGate`/`accept_ws` beep-node itself uses, without the TUN device or
session handshake, since the probes only exercise the HTTP layer) — and
diffs every probe's response. It does not need root or a TUN interface.

To poke at it by hand instead:

```
caddy run --config cover-site/Caddyfile.lab --adapter caddyfile &
beep-node --behind-proxy <some-leaf-cert.pem> --profile <profile.toml> \
  --port 4443 --iface beep_lab0 --address 10.9.0.1
curl http://127.0.0.1:18443/                              # ordinary site
curl http://127.0.0.1:18443/static/chunk-7f3a91c2.js       # 404, no header
```

## Deploying for real

`Caddyfile.production.template` is the same gating logic pointed at a real
domain, which still needs, from whoever is doing the deployment:

- a server and a domain name with DNS pointed at it, so Caddy's automatic
  HTTPS can issue a real certificate — this is the one piece nothing in
  this repository can stand in for;
- real content for `BEEP_COVER_SITE_ROOT` — what the domain is supposed to
  look like to anyone who just browses to it, not the lab's placeholder
  page;
- a long random value for `BEEP_COVER_HEADER_VALUE`, not the template's
  default.

`beep-node` then runs alongside Caddy on the same machine with
`--behind-proxy` pointed at Caddy's leaf certificate for that domain, and
`--port` matching `BEEP_NODE_PORT`.
