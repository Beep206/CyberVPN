# STAGE1-PUB-01 UPnP And Firewall Review

Date: 2026-05-10 16:18 UTC  
Server: `10.10.10.34`  
Host: `cybervpn-h-ops`

## Result

Status: **PASS for CyberVPN host firewall and Caddy edge posture; WARN for unrelated home-router exposure.**

The CyberVPN home operations server itself is constrained correctly for the current preparation stage:

- public listener: Caddy on `80/tcp` and `443/tcp`;
- SSH is permitted by UFW only from `10.10.10.0/24`;
- management services are bound to loopback or Docker-internal ports;
- Caddy routes `*.h.cyber-vpn.net` through the public edge and internal upstreams.

Router-level exposure still needs owner review before public beta hardening because prior RouterOS evidence shows UPnP was enabled and unrelated home services had WAN forwards.

## Evidence Sources

Reviewed current server state:

```bash
sudo ufw status verbose
sudo ss -ltnp
docker ps --format '{{.Names}}\t{{.Ports}}'
```

Reviewed existing RouterOS evidence:

```text
docs/evidence/routeros/mikrotik-after-caddy-edge-20260509T155200Z.txt
docs/evidence/routeros/phase10-cloudflare-public-entry-20260509T161028Z.txt
docs/evidence/routeros/pre-phase12-connectivity-restored-20260509T175505Z.txt
```

No live RouterOS mutation was performed in this step.

## CyberVPN Host Firewall

Current UFW posture:

```text
Default incoming: deny
Default outgoing: allow
Default routed: deny
22/tcp: allow from 10.10.10.0/24
80/tcp: allow from anywhere
443/tcp: allow from anywhere
```

This is acceptable for the home operations edge.

## Host Listener Boundary

Expected public listeners:

```text
*:80
*:443
```

Expected LAN-only/admin listeners:

```text
0.0.0.0:22, gated by UFW to 10.10.10.0/24
```

Expected loopback/internal services include:

```text
127.0.0.1:2222    GitLab SSH proxy
127.0.0.1:3000    Grafana
127.0.0.1:3001    Uptime Kuma
127.0.0.1:5050    GitLab registry
127.0.0.1:8929    GitLab web
127.0.0.1:9000    Sentry nginx
127.0.0.1:9090    Prometheus
127.0.0.1:9093    Alertmanager
127.0.0.1:3100    Loki
```

## RouterOS Findings From Existing Evidence

Expected CyberVPN router forwards:

```text
HTTP  -> 10.10.10.34:80
HTTPS -> 10.10.10.34:443
Hairpin HTTP/HTTPS for LAN clients
```

Unrelated home-router exposure observed in prior evidence:

```text
Mumble TCP/UDP -> 10.10.10.32:64738
UPnP dynamic entries existed before the Caddy edge cleanup
```

These are not CyberVPN app surfaces, but they reduce the hardness of the home WAN edge.

## Recommendation Before Public Beta

Preferred:

1. Disable MikroTik UPnP on WAN-facing interfaces.
2. Remove unrelated dynamic UPnP NAT entries.
3. Keep only intentional static public forwards:
   - `80/tcp` to `10.10.10.34`;
   - `443/tcp` to `10.10.10.34`;
   - any non-CyberVPN home service only if explicitly accepted by owner.
4. Save fresh RouterOS export/evidence after the change.

Accepted tiny-beta alternative:

1. Keep unrelated forwards temporarily.
2. Document them as owner-accepted home-network risk.
3. Do not claim the home edge is hardened.
4. Keep customer-facing CyberVPN runtime isolated behind Caddy and Cloudflare.

## Decision

This is not a blocker for continuing repository/server deployment preparation.

It is a blocker for saying the home edge is fully hardened unless UPnP/unrelated forwards are removed or owner-accepted in writing.
