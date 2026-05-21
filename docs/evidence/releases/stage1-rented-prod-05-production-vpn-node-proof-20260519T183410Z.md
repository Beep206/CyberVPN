# STAGE1-RENT-05 Production VPN Node Proof

Date: `2026-05-19T18:34:10Z`

Stage: `S1 - Controlled Public Beta`

Scope: rented production VPN node proof for CyberVPN Stage 1.

Owner: `@Sasha_Beep`

## Summary

`prod-vpn-node-1` was provisioned on a rented HostBrr VPS and configured as the first production VPN transport node.

This step proves:

- rented datacenter VPN node exists outside the home server;
- node DNS lives only in `cyber-vpn.org`;
- node OS/Docker/firewall baseline is in place;
- Xray runtime is healthy;
- `VLESS Reality/Vision` on `443/tcp` is reachable and works from `prod-app-1`;
- `VLESS XHTTP Reality` on `8443/tcp` is reachable and works from `prod-app-1`;
- Remnawave control-plane on `prod-app-1` is now healthy.

Follow-up status: the Remnawave API token/node-registration blocker found in this file was closed in `stage1-rented-prod-06-remnawave-node-registration-provisioning-20260519T191146Z.md`.

## Server

| Field | Value |
|---|---|
| Role | `prod-vpn-node-1` |
| Provider | `hostbrr.com` |
| Product | AMD Ryzen 9 5950X VPS |
| Size | `2 core / 4 GB` |
| IPv4 | `77.90.13.29` |
| IPv6 | `2a0a:51c1:9:c3::a` |
| OS | `Ubuntu 24.04.4 LTS` |
| Hostname | `de-1.cyber-vpn.org` |
| Docker | `29.5.1` |

## DNS Rule

Owner decision during this step:

```text
VPN node DNS records must live only in cyber-vpn.org, not in cyber-vpn.net.
```

Applied DNS state:

```text
de-1.cyber-vpn.org A=77.90.13.29
de-1.cyber-vpn.org AAAA=2a0a:51c1:9:c3::a
de-1.node.cyber-vpn.org A=77.90.13.29
de-1.node.cyber-vpn.org AAAA=2a0a:51c1:9:c3::a
de-1.cyber-vpn.net A=
de-1.node.cyber-vpn.net A=
```

The temporary `.net` node records created earlier in this step were deleted.

## OS Baseline

Actions completed:

- created `deploy` user with key-based SSH access;
- installed Docker Engine and Docker Compose plugin;
- enabled `chrony`, `fail2ban`, unattended upgrades and journald caps;
- configured Docker json-file log caps;
- enabled UFW;
- allowed only `22/tcp`, `443/tcp` and `8443/tcp` publicly.

Firewall evidence:

```text
Status: active

[ 1] 22/tcp    ALLOW IN    Anywhere                   # SSH
[ 2] 443/tcp   ALLOW IN    Anywhere                   # CyberVPN VLESS Reality
[ 3] 8443/tcp  ALLOW IN    Anywhere                   # CyberVPN VLESS XHTTP
[ 4] 22/tcp    ALLOW IN    Anywhere (v6)              # SSH
[ 5] 443/tcp   ALLOW IN    Anywhere (v6)              # CyberVPN VLESS Reality
[ 6] 8443/tcp  ALLOW IN    Anywhere (v6)              # CyberVPN VLESS XHTTP
```

## Xray Runtime

Runtime:

```text
image: ghcr.io/xtls/xray-core:26.3.27
container: cybervpn-xray-node
compose path: /srv/cybervpn-vpn-node/compose/docker-compose.yml
config path: /srv/cybervpn-vpn-node/xray/config.json
secret inventory: /srv/cybervpn-vpn-node/secrets/xray-proof.env
```

Security handling:

- Xray UUIDs, Reality private keys, public keys, short IDs and XHTTP path were generated on the node;
- runtime secrets were not written to repository docs;
- client smoke configs were temporary and deleted after the proof;
- no subscription URLs or client configs are stored in this evidence.

File permissions:

```text
600 root:root /srv/cybervpn-vpn-node/secrets/xray-proof.env
600 root:root /srv/cybervpn-vpn-node/xray/config.json
644 root:root /srv/cybervpn-vpn-node/compose/docker-compose.yml
```

Container evidence:

```text
NAME                 IMAGE                            SERVICE              STATUS
cybervpn-xray-node   ghcr.io/xtls/xray-core:26.3.27   cybervpn-xray-node   Up (healthy)
```

Listening ports:

```text
tcp LISTEN *:443
tcp LISTEN *:8443
```

## Protocol Proof

Port reachability from local operator environment:

```text
de-1.cyber-vpn.org:443 reachable
de-1.cyber-vpn.org:8443 reachable
de-1.node.cyber-vpn.org:443 reachable
de-1.node.cyber-vpn.org:8443 reachable
```

Port reachability from `prod-app-1`:

```text
de-1.cyber-vpn.org:443 reachable_from_prod_app_1
de-1.cyber-vpn.org:8443 reachable_from_prod_app_1
de-1.node.cyber-vpn.org:443 reachable_from_prod_app_1
de-1.node.cyber-vpn.org:8443 reachable_from_prod_app_1
```

Xray client proof from `prod-app-1`:

```text
CLIENT_CONFIGS_OK
VLESS_REALITY_CLIENT_EGRESS=PASS
VLESS_XHTTP_REALITY_CLIENT_EGRESS=PASS
```

Meaning:

- `VLESS Reality/Vision` client egress returned `77.90.13.29`;
- `VLESS XHTTP Reality` client egress returned `77.90.13.29`;
- both checks used temporary client configs and cleaned them up after the proof.

## Remnawave Control-Plane

During this step, Remnawave control-plane was also started on `prod-app-1`.

Fixes applied on `prod-app-1`:

- added explicit `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` derived from the existing Remnawave `DATABASE_URL`;
- added required Remnawave `JWT_API_TOKENS_SECRET`;
- added required `FRONT_END_DOMAIN`;
- added required `SUB_PUBLIC_DOMAIN`;
- added required `METRICS_USER` and `METRICS_PASS`;
- added explicit `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`;
- replaced the too-short notification stub with the repository Remnawave 2.7.x notification event matrix.

File permissions:

```text
600 root:root /srv/cybervpn/secrets/remnawave-panel.env
644 root:root /srv/cybervpn/configs/app/remnawave-notifications.yml
```

Current Remnawave service evidence:

```text
cybervpn-stage1-cybervpn-remnawave-1            remnawave/backend:2.7.4    Up (healthy)
cybervpn-stage1-cybervpn-remnawave-postgres-1   postgres:17.7-alpine       Up (healthy)
cybervpn-stage1-cybervpn-remnawave-valkey-1     valkey/valkey:8.1-alpine   Up (healthy)
```

Health endpoint:

```json
{"status":"ok","info":{"database":{"status":"up"}},"error":{},"details":{"database":{"status":"up"}}}
```

Metrics proof:

```text
remnawave_process_uptime_seconds{instance_name="processor",app="remnawave"} present
remnawave_process_uptime_seconds{instance_name="api",app="remnawave"} present
remnawave_process_uptime_seconds{instance_name="scheduler",app="remnawave"} present
```

## Follow-Up Closure

The original blocker from this proof was:

```text
GET /api/nodes with current stored REMNAWAVE_API_TOKEN -> HTTP 401
```

It is now closed by `STAGE1-RENT-06` evidence:

- valid Remnawave API token inserted and stored in runtime secrets;
- stale token aliases removed;
- `GET /api/nodes` returns HTTP `200`;
- `s1-de-1` is registered as a Remnawave node inventory item;
- Remnawave-managed `remnawave/node:2.7.0` replaced the standalone Xray proof container;
- S1 VLESS Reality and VLESS XHTTP Reality inbounds are active on the registered node;
- disposable provisioning smoke proved user creation, subscription URL presence and accessible node mapping.

## Result

`STAGE1-RENT-05` is accepted as production VPN node runtime proof:

```text
PASS for rented node OS/runtime/DNS/VLESS/XHTTP proof.
PASS for Remnawave control-plane health.
PASS for Remnawave API token/node registration after STAGE1-RENT-06 closure.
```
