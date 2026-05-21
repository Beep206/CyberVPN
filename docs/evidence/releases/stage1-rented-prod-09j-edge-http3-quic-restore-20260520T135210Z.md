# Stage 1 RENT-09J Edge HTTP/3/QUIC Restore Evidence

Date: `2026-05-20`

Stage: `S1 - Controlled Public Beta`

Scope: `STAGE1-RENT-09J`

Target: `prod-app-1`

## Reason

Owner confirmed the previously reported browser/WebView `ERR_CONNECTION_RESET` cleared, then required HTTP/3/QUIC to be restored and treated as mandatory for the CyberVPN edge.

Decision:

```text
HTTP/3/QUIC must not be disabled as a normal fix path.
If H3 causes a client symptom, repair UDP 443 publication, firewall, kernel buffer tuning, edge config and client evidence.
```

## Live Changes

Updated live Caddy configuration:

```caddy
servers {
  protocols h1 h2 h3
}
```

Removed stale Alt-Svc clearing:

```text
Alt-Svc "clear" removed from common headers.
```

Updated live edge compose:

```yaml
ports:
  - "80:80"
  - "443:443"
  - "443:443/udp"
```

Updated firewall:

```text
443/udp allowed for IPv4 and IPv6.
```

Added persistent QUIC UDP buffer tuning:

```text
/etc/sysctl.d/99-cybervpn-quic.conf
net.core.rmem_max = 7500000
net.core.wmem_max = 7500000
```

Recreated/restarted only the edge Caddy container:

```text
cybervpn-edge-caddy
```

Application containers were not restarted for this change.

## Validation

Caddy config validation:

```text
Valid configuration
```

Caddy startup evidence:

```text
enabling HTTP/3 listener addr=:443
server running protocols=["h1","h2","h3"]
```

Docker port evidence:

```text
0.0.0.0:443->443/tcp
0.0.0.0:443->443/udp
[::]:443->443/tcp
[::]:443->443/udp
```

Socket evidence:

```text
0.0.0.0:443 UDP docker-proxy
[::]:443 UDP docker-proxy
```

Firewall evidence:

```text
443/udp ALLOW IN Anywhere
443/udp ALLOW IN Anywhere (v6)
```

HTTP response evidence:

```text
HTTP/2 200
alt-svc: h3=":443"; ma=2592000
```

Mini App route probes:

```text
https://cyber-vpn.net/ru-RU/miniapp/home     200
https://cyber-vpn.net/ru-RU/miniapp/plans    200
https://cyber-vpn.net/ru-RU/miniapp/wallet   200
https://cyber-vpn.net/ru-RU/miniapp/profile  200
```

## Result

HTTP/3/QUIC is restored on the Stage 1 edge with both Caddy protocol support and real UDP `443` host publication.

The current local shell `curl` does not include HTTP/3 support, so this evidence proves the server-side H3 advertisement, UDP publication, firewall state and route health. Browser/Telegram owner retest remains the client-side confirmation.

Owner retest update:

```text
Owner confirmed the Telegram/client page opens and works after HTTP/3/QUIC restore.
```

## Policy

For future Stage 1 edge work:

```text
Do not disable HTTP/3/QUIC.
Keep TCP 443 and UDP 443 published together.
Keep firewall rules for 443/tcp and 443/udp together.
Keep Caddy protocols as h1 h2 h3.
Keep QUIC buffer sysctl present.
If a browser reset appears, validate client cache/state and UDP path before changing protocols.
```
