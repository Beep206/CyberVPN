# Stage 1 RENT-09I Edge HTTP/3 Reset Fix Evidence

Date: `2026-05-20`

Stage: `S1 - Controlled Public Beta`

Scope: `STAGE1-RENT-09I`

Target: `prod-app-1`

Status: `superseded by STAGE1-RENT-09J`

Supersession note:

```text
This was an emergency isolation step only.
Owner later confirmed the page worked and required HTTP/3/QUIC to be restored and never disabled.
The current authoritative edge state is documented in:
docs/evidence/releases/stage1-rented-prod-09j-edge-http3-quic-restore-20260520T135210Z.md
```

## Reason

Owner reported browser/Telegram WebView failure:

```text
ERR_CONNECTION_RESET
```

The public HTTPS endpoint was reachable through `curl` over HTTP/2, while Caddy was advertising HTTP/3 through `Alt-Svc: h3=":443"`.

Runtime inspection showed that the edge published TCP `80/443`, but did not publish UDP `443`. This made HTTP/3/QUIC unsafe for Stage 1 client traffic and could cause browser/WebView connection reset behavior after the client cached the H3 advertisement.

## Change

Applied live edge-only Caddy change:

```caddy
servers {
  protocols h1 h2
}
```

Added stale Alt-Svc clearing header:

```caddy
Alt-Svc "clear"
```

Restarted only the Caddy edge container:

```text
cybervpn-edge-caddy
```

Application containers were not restarted for this fix.

## Validation

Caddy config validation result:

```text
Valid configuration
```

Caddy startup protocol evidence:

```text
server running
protocols=["h1","h2"]
```

External route probes after the restart:

```text
https://cyber-vpn.net/ru-RU/miniapp/home     200
https://cyber-vpn.net/ru-RU/miniapp/plans    200
https://cyber-vpn.net/ru-RU/miniapp/wallet   200
https://cyber-vpn.net/ru-RU/miniapp/profile  200
```

Response header evidence:

```text
HTTP/2 200
alt-svc: clear
```

## Result

The Stage 1 edge no longer advertises HTTP/3/QUIC and explicitly tells clients to clear stale Alt-Svc state.

Owner/client retest is still required because some browsers and WebViews can keep previous connection state until the tab, browser or Telegram Mini App is fully closed and reopened.

## Follow-Up

Superseded by `STAGE1-RENT-09J`.

For Stage 1, HTTP/3/QUIC must remain enabled. If connection reset issues appear again, fix UDP `443` publish/firewall/sysctl/client evidence instead of disabling HTTP/3.
