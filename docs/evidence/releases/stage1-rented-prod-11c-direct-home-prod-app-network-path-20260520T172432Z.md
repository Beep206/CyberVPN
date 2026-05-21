# STAGE1-RENT-11C - Direct Home-to-Prod-App Network Path Evidence

Date: `2026-05-20T17:37:55Z`
Scope: investigate whether MikroTik/home routing is the cause of direct `home -> prod-app-1` public probe failures.
Result: `BLOCKED_BY_UPSTREAM_OR_PROVIDER_PATH_AFTER_MIKROTIK_TX`

Follow-up: `STAGE1-RENT-11D` chose Cloudflare-proxied user-path probes as the Stage 1 public endpoint monitoring authority. The direct home-origin path issue in this file remains a known upstream/provider issue, not the active user-path monitoring authority.

## Summary

The direct home observability path to `prod-app-1` is still broken for HTTP/TLS probes.

This is not a CyberVPN application runtime issue:

- `prod-app-1` serves its own public edge locally with HTTP `200`;
- external non-home paths can reach the public app;
- `prod-vpn-node-1` can reach the public app with HTTP `200`;
- home can reach other public HTTPS destinations;
- VPN node TCP probes are green;
- the VPN node is not used as a relay and must remain node-only.

RouterOS access is now available and the MikroTik datapath was inspected. The important finding is:

```text
MikroTik sends the post-handshake HTTP/TLS payload out of the WAN interface,
but prod-app-1 does not receive that payload on ens3.
```

The current fault domain is therefore outside the CyberVPN app/runtime and outside the local home server. It is either:

- upstream ISP path after the MikroTik WAN interface;
- JustHost/provider anti-DDoS/TCP validation before packets reach `prod-app-1`;
- a provider-side source-specific block or broken TCP path for the home public IP to ports `80/443`.

## MikroTik Access Result

RouterOS access was established through SSH as `admin`. No passwords are recorded in this evidence file.

Observed router facts:

| Item | Result |
|---|---|
| RouterOS | `7.22.1` |
| Board | `RB4011iGS+5HacQ2HnD` |
| LAN gateway | `10.10.10.1/24` on `bridge` |
| WAN interface | `sfp-sfpplus1` |
| WAN IPv4 observed on router | `95.82.233.131/24` |
| Route to `45.87.41.146` | direct via `sfp-sfpplus1`, nexthop `95.82.233.1` |
| FastTrack | rule exists but disabled; counters inactive |
| IPv4 fast path | inactive |
| Routing rules | no separate routing rules observed |
| NAT for home traffic | standard WAN masquerade |
| Persistent config changes | none |

Only temporary packet sniffer configuration was used during diagnostics. Sniffer was stopped and reset after the test.

## Evidence

### Home Server Public Internet Works Generally

From `cybervpn-h-ops`:

| Target | Result |
|---|---|
| `https://example.com` | `200` |
| ICMP to `45.87.41.146`, 56 bytes | `0%` packet loss |
| ICMP to `45.87.41.146`, 1200 bytes with DF | `0%` packet loss |

So this is not a general home-server Internet outage or basic MTU failure.

### CyberVPN Public Edge Fails Only From Home Path

From `cybervpn-h-ops`:

| Target | Result |
|---|---|
| `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | SSL connection timeout |
| `https://api.cyber-vpn.net/health` | SSL connection timeout |
| `http://45.87.41.146/.well-known/cybervpn-edge-health` with `Host: cyber-vpn.net` | TCP connect succeeds, then timeout with `0` bytes received |

DNS resolution from home points directly to `45.87.41.146` for `cyber-vpn.net`, `api.cyber-vpn.net` and `admin.cyber-vpn.net`.

### prod-app-1 Is Healthy Locally And From Non-Home Paths

From `prod-app-1`:

| Target | Result |
|---|---|
| `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | `200`, about `45ms` |

From `prod-vpn-node-1`:

| Target | Result |
|---|---|
| `https://cyber-vpn.net/.well-known/cybervpn-edge-health` | `200`, about `62ms` |

The one-off `curl` from the VPN node was diagnostic only. The VPN node still must not run observability relay/exporter/support/backend/payment workloads.

### Port-Specific Behavior From Home

From `cybervpn-h-ops`:

| Target | Result |
|---|---|
| `45.87.41.146:22` | TCP connect succeeds, SSH banner received |
| `45.87.41.146:80` | TCP connect succeeds, HTTP request payload does not complete |
| `45.87.41.146:443` | TCP connect succeeds, TLS ClientHello does not complete |

This points away from a total route outage and toward TCP payload handling on web ports after the handshake.

### prod-app-1 Packet Capture

For a unique HTTPS test using local source port `57323`, `prod-app-1` captured only the TCP handshake:

```text
95.82.233.131:57323 -> 45.87.41.146:443  SYN
45.87.41.146:443 -> 95.82.233.131:57323  SYN,ACK
95.82.233.131:57323 -> 45.87.41.146:443  ACK
```

No TLS ClientHello payload reached `prod-app-1`.

For a unique HTTP test using local source port `57480`, `prod-app-1` captured only the TCP handshake:

```text
95.82.233.131:57480 -> 45.87.41.146:80  SYN
45.87.41.146:80 -> 95.82.233.131:57480  SYN,ACK
95.82.233.131:57480 -> 45.87.41.146:80  ACK
```

No HTTP request payload reached `prod-app-1`.

### MikroTik WAN Packet Capture

For the HTTPS diagnostic using local source port `57223`, MikroTik captured this on WAN `sfp-sfpplus1`:

```text
95.82.233.131:57223 -> 45.87.41.146:443  SYN
45.87.41.146:443 -> 95.82.233.131:57223  SYN,ACK
95.82.233.131:57223 -> 45.87.41.146:443  ACK
95.82.233.131:57223 -> 45.87.41.146:443  PSH,ACK 569-byte IP packet
95.82.233.131:57223 -> 45.87.41.146:443  repeated PSH,ACK retransmits
95.82.233.131:57223 -> 45.87.41.146:443  FIN,ACK
```

Interpretation:

```text
The home server emits TLS payload.
MikroTik forwards/NATs that payload and transmits it out WAN.
prod-app-1 does not receive that payload.
```

MikroTik connection tracking confirms the same pattern: original-direction bytes increase materially while reply-direction bytes stay near handshake-only volume, with no FastTrack counters.

### Router-Origin HTTP Fetch

RouterOS `/tool fetch` from MikroTik itself to the HTTP health endpoint reached `requesting` and did not produce a successful response during the diagnostic window.

This supports the conclusion that the failure is not specific to the home Linux host or Docker stack.

## Current Interpretation

The direct home-to-prod-app public HTTP/TLS path is broken after MikroTik transmits post-handshake payload to WAN.

Current most likely causes:

1. Upstream ISP path issue between the home WAN and JustHost.
2. JustHost/provider anti-DDoS or TCP validation dropping source-specific web-port payload before it reaches `prod-app-1`.
3. Source-specific provider block for home public IP `95.82.233.131` on ports `80/443`.

Current less likely causes:

1. CyberVPN application or Caddy issue: ruled down because non-home paths work and local edge health is green.
2. `prod-app-1` firewall issue: ruled down because host `tcpdump` does not receive the missing payload.
3. MikroTik FastTrack issue: ruled down by disabled/inactive FastTrack and WAN sniffer proof of transmitted payload.
4. Basic MTU issue: ruled down by successful 1200-byte DF ICMP and the small 569-byte TCP payload.

## Recommended Closure Options

### Option A - Provider Ticket / Whitelist

Open a ticket with JustHost and/or the home ISP using the packet evidence:

```text
Source: 95.82.233.131
Destination: 45.87.41.146
Ports: TCP 80 and 443
Symptom: TCP handshake completes, but post-handshake payload from source does not arrive at prod-app host.
Host tcpdump sees SYN/SYN-ACK/ACK only.
MikroTik WAN sniffer shows PSH,ACK payload transmitted to provider gateway.
```

Ask JustHost to check upstream anti-DDoS/TCP validation logs and whitelist or unblock the source for HTTP/TLS.

### Option B - Use Cloudflare-Proxied Public Probes

For beta operations, put public web/API/admin DNS behind Cloudflare proxy and let home Prometheus probe the same public hostnames users see.

This does not close the direct-origin path, but it gives useful user-facing monitoring and avoids using the VPN node as a relay.

### Option C - External Probe Location

Run blackbox probes from a low-cost external probe host or managed uptime provider. This also does not close direct home-origin probing, but it gives independent user-path evidence.

### Option D - Risk Accept For Internal Beta Only

Continue owner/internal beta with this known observability gap, as long as:

- direct home blackbox probes stay marked as `NO-GO_FOR_WIDER_COHORT`;
- VPN node is not used as a relay;
- external/non-home endpoint checks remain green;
- the blocker remains visible in stabilization docs.

## Current Status

```text
NO-GO for considering direct home -> prod-app-1 monitoring closed.
GO to continue owner/internal beta with the known observability limitation recorded.
NO relay on prod-vpn-node-1.
Need provider/upstream fix, Cloudflare-proxied monitoring decision, or explicit owner risk acceptance to close STAGE1-RENT-11C.
```

## Next Action

Recommended next step:

```text
STAGE1-RENT-11D: Public Endpoint Monitoring Authority Decision
```

Decision needed:

- fix direct path through provider support;
- switch public probes to Cloudflare-proxied user path;
- add a separate external probe host/provider;
- or explicitly risk-accept the direct home-path gap for the first internal cohort.
