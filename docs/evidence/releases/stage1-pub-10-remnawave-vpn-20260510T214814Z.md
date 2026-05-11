# STAGE1-PUB-10 Remnawave And VPN Node Evidence

Date: 2026-05-10 21:48 UTC

Scope: Stage 1 public internet deployment, Remnawave control-plane and lab VPN node smoke on `cybervpn-h`.

## Result

STAGE1-PUB-10 is partially completed for runtime/control-plane readiness and lab node connectivity.

User-facing VPN access is not approved yet because the connected node is a lab-only home-server node, not a rented production VPN exit node. Trial/paid provisioning flags remain disabled until a real production node is available and client connection evidence is captured.

## Official References Used

- Remnawave Panel installation: <https://docs.rw/docs/install/remnawave-panel>
- Remnawave Node installation: <https://docs.rw/docs/install/remnawave-node/>
- Remnawave requirements: <https://docs.rw/docs/install/requirements>
- Remnawave environment variables and metrics: <https://docs.rw/docs/install/environment-variables/>
- Remnawave Rescue CLI: <https://docs.rw/docs/features/rescue-cli>

## Changes Applied

- Added Stage 1 Remnawave control-plane services to `infra/deploy/stage1/docker-compose.stage1.yml`:
  - `cybervpn-remnawave`
  - `cybervpn-remnawave-postgres`
  - `cybervpn-remnawave-valkey`
- Added guarded lab node profile:
  - service: `cybervpn-remnawave-node-local`
  - profile: `vpn-node-local`
  - image: `remnawave/node:2.7.0`
  - scope label: `lab-only-until-real-vpn-node`
- Added redacted env examples:
  - `infra/deploy/stage1/remnawave-panel.env.example`
  - `infra/deploy/stage1/remnawave-node.env.example`
- Added Remnawave subscription route:
  - container Caddy snippet: `/api/sub* -> remnawave:3000`
  - system-edge Caddy snippet: `/api/sub* -> http://127.0.0.1:13005`
- Installed server-only secret files on `cybervpn-h`:
  - `/srv/cybervpn-h/secrets/remnawave-panel.env`
  - `/srv/cybervpn-h/secrets/remnawave-admin.env`
  - `/srv/cybervpn-h/secrets/remnawave.env`
  - `/srv/cybervpn-h/secrets/remnawave-node.env`
- Created Remnawave API token and stored it only in server secrets.
- Connected Remnawave metrics to Prometheus using `basic_auth.password_file`, not inline password.

## Runtime Evidence

```text
containers
cybervpn-stage1-cybervpn-remnawave-node-local-1    Up 2 minutes (healthy)
cybervpn-stage1-cybervpn-remnawave-1               Up 23 minutes (healthy)    127.0.0.1:13005->3000/tcp, 127.0.0.1:13006->3001/tcp
cybervpn-stage1-cybervpn-remnawave-postgres-1      Up 23 minutes (healthy)    5432/tcp
cybervpn-stage1-cybervpn-remnawave-valkey-1        Up 23 minutes (healthy)    6379/tcp
```

```text
GET http://127.0.0.1:13006/health -> 200
{"status":"ok","info":{"database":{"status":"up"}},"error":{},"details":{"database":{"status":"up"}}}
```

```text
name                   address                 port    is_connected    is_connecting    is_disabled
stage1-lab-home-node   remnawave-node-local    22230   true            false            false
```

```text
up{job="remnawave"} = 1
stage1:remnawave_healthy_nodes:current = 1
```

Public edge route smoke:

```text
GET https://api.cyber-vpn.net/healthz -> 200 ok
GET https://api.cyber-vpn.net/api/sub -> 404 from Remnawave, proving route reaches Remnawave instead of system-edge fallback
```

## Verification

```text
docker compose -f infra/deploy/stage1/docker-compose.stage1.yml --profile vpn-node-local config -> PASS
git diff --check -> PASS
secret scan over changed Stage 1 Remnawave docs/configs -> PASS, only placeholder example values matched
npm audit --omit=dev --audit-level=high -> PASS exit status; report contains 2 moderate Next/PostCSS advisories, no high/critical production npm audit blocker
```

## Important Implementation Notes

- `remnawave/node:2.7.4` is not available in Docker Hub. The lab node uses `remnawave/node:2.7.0`, which matches the current Remnawave Node 2.7.x line documented by Remnawave.
- `NODE_PORT=2222` cannot be used on `cybervpn-h` because it is already reserved by GitLab SSH on `127.0.0.1:2222`.
- The lab node uses `NODE_PORT=22230`.
- The first attempt with host-network node was not usable from the Remnawave container because the container could not connect to the host-network port through the current bridge/firewall boundary.
- The lab node was therefore moved to the private Remnawave Docker network and registered as `remnawave-node-local:22230`.
- This is acceptable for control-plane smoke only. It is not acceptable as the final public VPN exit node for beta users.

## Exit Criteria Status

| Criterion | Status | Evidence / Reason |
|---|---:|---|
| Remnawave control-plane healthy | PASS | `cybervpn-remnawave` healthy, `/health` returns 200 |
| At least one node healthy | PASS for lab | `stage1-lab-home-node` connected and `stage1:remnawave_healthy_nodes:current = 1` |
| Remnawave metrics connected to Prometheus | PASS | `up{job="remnawave"} = 1` |
| `Stage1NoHealthyRemnawaveNodes` cleared | PASS for lab | recording rule reports `1` |
| Trial provisioning succeeds | BLOCKED | provisioning flags intentionally remain disabled until real production node exists |
| QR/subscription URL/config generated | BLOCKED | requires approved trial/paid provisioning path |
| Real user/client connection | BLOCKED | lab node is not a public production VPN node |
| Credential regeneration live test | BLOCKED | should be tested against the real production node |
| Expiry/grace disable live test | BLOCKED | should be tested against the real production node |
| Median/p95 `trial/pay -> VPN ready` latency | BLOCKED | requires live provisioning path |

## Current Blocker

Before controlled public beta can include real users, deploy at least one rented, always-on production Remnawave node outside the home server and capture:

- node inventory;
- firewall allowlist from panel to node `NODE_PORT`;
- node health in DB and Prometheus;
- trial provisioning from CyberVPN backend;
- QR/subscription URL/config generation;
- real client or documented equivalent connection;
- credential regeneration;
- expiry/grace disable;
- latency sample for `trial/pay -> VPN ready`.
