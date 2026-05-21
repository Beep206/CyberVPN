# STAGE1-RENT-06 Remnawave Node Registration And Provisioning Proof

Date: `2026-05-19T19:11:46Z`

Stage: `S1 - Controlled Public Beta`

Scope: close the Remnawave API token, node registration and first provisioning-smoke blocker for the rented production VPN node.

Owner: `@Sasha_Beep`

## Summary

The previous blocker was:

```text
REMNAWAVE_API_TOKEN returned HTTP 401 on /api/nodes.
```

This blocker is closed for Stage 1 node registration.

Result:

- Remnawave API token was rotated/created in the running production control-plane;
- stale runtime token aliases were removed;
- Remnawave API now accepts `GET /api/nodes`;
- `s1-de-1` is registered in Remnawave with address `de-1.cyber-vpn.org`;
- the node runs the official `remnawave/node:2.7.0` runtime;
- Remnawave sees the node as connected and enabled;
- S1 VLESS Reality and VLESS XHTTP Reality inbounds are attached to the node;
- S1 internal squad `S1_DEFAULT_DE` maps beta users to the node;
- disposable provisioning smoke proved user creation, subscription URL presence and accessible node mapping;
- smoke user was deleted after evidence.

No token, node `SECRET_KEY`, Reality key, VLESS UUID, subscription URL, QR payload or client config is stored in this file.

## Domain Decision Update

Owner decision for Stage 1:

```text
cyber-vpn.org is no longer a public mirror or redirect surface for cyber-vpn.net.
```

Updated domain contract:

| Domain | Stage 1 role |
|---|---|
| `cyber-vpn.net` | primary customer app/cabinet domain |
| `www.cyber-vpn.net` | redirect/canonicalization to `cyber-vpn.net` |
| `api.cyber-vpn.net` | backend API, provider callbacks, Telegram callbacks and OAuth callbacks |
| `admin.cyber-vpn.net` | canonical protected admin host |
| `cyber-vpn.org` | reserved zone for VPN nodes and future subscription delivery only |
| `de-1.cyber-vpn.org` | production VPN node hostname |
| `de-1.node.cyber-vpn.org` | production VPN node alias |
| `admin.cyber-vpn.org` | not used for S1 admin; must not serve admin |
| `www.cyber-vpn.org` | not used for S1 customer web |

Current Remnawave subscription-public host remains a runtime setting and must be changed only after DNS/TLS/route evidence exists for the future `.org` subscription endpoint.

## Remnawave API Token

Observed before fix:

```text
api_tokens table empty
stored REMNAWAVE_API_TOKEN rejected on /api/nodes
```

Actions completed on `prod-app-1`:

- generated a Remnawave API JWT using the running control-plane secret contract;
- inserted one API token record into Remnawave PostgreSQL;
- updated `/srv/cybervpn/secrets/remnawave.env`;
- updated `/srv/cybervpn/secrets/app.env`;
- removed stale typo alias `nREMNAWAVE_API_TOKEN`;
- restarted CyberVPN backend, worker and scheduler.

Evidence:

```text
REMNAWAVE_API_TOKEN_ROTATED
REMNAWAVE_NODES_HTTP=200
API_TOKEN_ROWS=1
backend/worker/scheduler healthy
```

Security note: token values are intentionally excluded.

## Node Registration

Created Remnawave config profile:

```text
CONFIG_PROFILE_CREATE_HTTP=201
profile: S1 DE VLESS XHTTP
```

Profile inbounds:

| Inbound | Port | Protocol | Network | Security |
|---|---:|---|---|---|
| `VLESS_REALITY_443` | `443` | `vless` | `tcp` | `reality` |
| `VLESS_XHTTP_REALITY_8443` | `8443` | `vless` | `xhttp` | `reality` |

Existing partially-created node was repaired instead of duplicated:

```text
NODE_UPDATE_HTTP=200
activeInboundsCount=2
```

Final node state:

```json
{
  "name": "s1-de-1",
  "address": "de-1.cyber-vpn.org",
  "port": 22230,
  "isDisabled": false,
  "isConnected": true,
  "isConnecting": false,
  "activeInbounds": ["VLESS_REALITY_443", "VLESS_XHTTP_REALITY_8443"],
  "countryCode": "DE"
}
```

## VPN Node Runtime

The standalone Xray proof container from `STAGE1-RENT-05` was stopped and preserved as an exited fallback container.

Current runtime:

```text
container: cybervpn-remnawave-node
image: remnawave/node:2.7.0
hostname: s1-de-1
network_mode: host
compose path: /srv/cybervpn-remnawave-node/compose/docker-compose.yml
secret path: /srv/cybervpn-remnawave-node/secrets/remnawave-node.env
```

File/security rules:

```text
/srv/cybervpn-remnawave-node/secrets/remnawave-node.env mode 0600
SECRET_KEY not printed to evidence
```

Listening ports after Remnawave-managed start:

```text
*:22230 remnawave node internal API
*:443   Remnawave-managed Xray VLESS Reality
*:8443  Remnawave-managed Xray VLESS XHTTP Reality
```

Firewall:

```text
443/tcp public
8443/tcp public
22230/tcp allowed only from prod-app-1 IPv4 45.87.41.146
22230/tcp allowed only from prod-app-1 IPv6 2a0d:2787:1b:12f5::a
```

Reachability from `prod-app-1`:

```text
de-1.cyber-vpn.org:22230 reachable_from_prod_app_1
de-1.cyber-vpn.org:443 reachable_from_prod_app_1
de-1.cyber-vpn.org:8443 reachable_from_prod_app_1
```

Remnawave node logs show the panel pushed config and Xray started:

```text
Started node in 1s 96ms
Xray started
Xray Core: v26.3.27
```

## Provisioning Smoke

Created internal squad:

```text
SQUAD_CREATE_HTTP=201
name=S1_DEFAULT_DE
accessibleCount=1
node=s1-de-1
activeInbounds=VLESS_REALITY_443,VLESS_XHTTP_REALITY_8443
```

Created disposable Remnawave user with `S1_DEFAULT_DE`:

```text
USER_CREATE_WITH_SQUAD_HTTP=201
subscriptionUrlPresent=true
vlessUuidPresent=true
activeInternalSquads=["S1_DEFAULT_DE"]
```

Verified accessible node mapping:

```text
USER_ACCESSIBLE_NODES_WITH_SQUAD_HTTP=200
activeCount=1
nodeName=s1-de-1
activeInbounds=VLESS_REALITY_443,VLESS_XHTTP_REALITY_8443
```

Node remained connected:

```text
NODE_AFTER_SQUAD_USER_CREATE={"isConnected": true, "isDisabled": false}
```

Cleanup:

```text
USER_DELETE_WITH_SQUAD_HTTP=200
response.isDeleted=true
```

Persistent runtime object intentionally kept:

```text
S1_DEFAULT_DE internal squad
```

This squad is required for S1 beta users to receive access to `s1-de-1`.

## Remaining Work

This evidence closes:

- Remnawave API token 401 blocker;
- Remnawave node inventory registration;
- Remnawave-managed node runtime;
- basic Remnawave provisioning smoke through internal squad/access mapping.

Still required before expanding beta:

1. prove CyberVPN backend trial flow creates/updates the Remnawave user through the application path;
2. prove generated QR/subscription/config imports into an actual VPN client after the app trial flow;
3. decide and deploy the future `.org` subscription endpoint if we move subscription delivery off `api.cyber-vpn.net`;
4. keep `22230/tcp` restricted to the app server addresses only.

## Result

```text
PASS: Remnawave API token valid.
PASS: /api/nodes returns 200.
PASS: s1-de-1 registered and connected in Remnawave.
PASS: Remnawave-managed VLESS Reality and VLESS XHTTP inbounds active.
PASS: disposable user provisioning smoke with subscription URL presence and accessible node mapping.
```
