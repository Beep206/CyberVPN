> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-03
> Backlog ID: `S1-VPN-012`
> Статус: PASS for local connected Remnawave node smoke. This is local/dev evidence only.

# S1-VPN-012 Local Remnawave Node Evidence

## Purpose

Этот документ дополняет `24_STAGE1_VPN_012_LOCAL_REMNAWAVE_SMOKE_EVIDENCE.md`: после control-plane smoke была поднята локальная Remnawave Node, зарегистрирована в Remnawave Panel and verified as connected through `/api/nodes`.

Это всё ещё не staging/prod evidence и не закрывает `S1-VPN-001` / `S1-VPN-002`. Для S1 go-live всё ещё нужны separate staging/prod Remnawave instances, external node/firewall proof, trial/paid provisioning evidence, outage retry evidence and backup/export/rebuild evidence.

## Official Documentation Baseline

Used sources:

- Remnawave Node install docs: <https://docs.rw/docs/install/remnawave-node/>
- Remnawave Node changelog: <https://docs.rw/docs/changelog/remnawave-node/>

Relevant baseline from docs:

- Remnawave Panel does not include Xray-core; Remnawave Node is separate and includes Xray-core.
- Remnawave Node uses `NODE_PORT` and `SECRET_KEY`.
- `NODE_PORT` is the internal API port used by Remnawave Panel to reach the node.
- Node firewall should restrict `NODE_PORT` to the panel IP/CIDR in real environments.
- Remnawave Node `2.7.0` requires Remnawave Panel `2.7.0` or higher and includes Xray Core `26.3.27`.

## Preconditions

- Local Remnawave control-plane, PostgreSQL, Valkey and Caddy proxy were running.
- Remnawave API token was read from local `services/task-worker/.env` without printing the value.
- Remnawave `GET /api/keygen` was used to obtain the local node `SECRET_KEY` without printing it.
- Existing default config profile was used:
  - profile: `Default-Profile`
  - inbound: `Shadowsocks`
  - inbound port: `1234`

## Commands Executed

Secrets were not printed. Commands below are redacted where secret values were passed through environment variables.

```bash
docker pull remnawave/node:2.7.4
docker pull remnawave/node:2.7.0
docker pull remnawave/node:latest
curl --max-time 8 -k -fsS -H "Authorization: Bearer <redacted>" https://panel.localhost/api/config-profiles
curl --max-time 8 -k -fsS -H "Authorization: Bearer <redacted>" https://panel.localhost/api/keygen
curl --max-time 10 -k -fsS \
  -H "Authorization: Bearer <redacted>" \
  -H "Content-Type: application/json" \
  -X POST https://panel.localhost/api/nodes \
  -d '<redacted-generated-local-node-json-without-secrets>'
docker run -d \
  --name remnanode-local \
  --hostname remnanode-local \
  --network cybervpn-backend \
  --cap-add NET_ADMIN \
  -e NODE_PORT=2222 \
  -e SECRET_KEY="<redacted>" \
  remnawave/node:2.7.0
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' remnanode-local
docker logs --tail=80 remnanode-local
docker exec remnanode-local sh -lc 'ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || true'
curl --max-time 8 -k -fsS -H "Authorization: Bearer <redacted>" https://panel.localhost/api/nodes
docker image inspect remnawave/node:2.7.0 --format '{{.Id}} {{index .RepoDigests 0}}'
```

## Image Result

`remnawave/node:2.7.4` was attempted first because the repository Ansible baseline references it. Docker Hub did not have that tag:

```text
Error response from daemon: failed to resolve reference "docker.io/remnawave/node:2.7.4": docker.io/remnawave/node:2.7.4: not found
```

Compatible node image pulled successfully:

```text
docker.io/remnawave/node:2.7.0
Digest: sha256:9d57375a8168d00252f4debe7a6ac29debd8449af60467ab26b4ee212b047525
```

`remnawave/node:latest` currently resolved to the same digest:

```text
sha256:9d57375a8168d00252f4debe7a6ac29debd8449af60467ab26b4ee212b047525 remnawave/node@sha256:9d57375a8168d00252f4debe7a6ac29debd8449af60467ab26b4ee212b047525
```

## Node Creation Result

Local node was created through `POST /api/nodes` using the existing default profile and inbound:

```json
{"uuid":"ec228317-3728-4a21-bbb1-b2fbbcdd714e","name":"Local Smoke Node","address":"remnanode-local","port":2222,"isConnected":false,"isConnecting":false,"isDisabled":false,"activeInbounds":1,"tags":["LOCAL_SMOKE"]}
```

The node address `remnanode-local` is intentionally Docker-network local. It is valid for local smoke because Remnawave Panel and Remnawave Node share `cybervpn-backend`.

## Node Container Result

Container state:

```text
/remnanode-local running no-healthcheck
```

Node startup logs, redacted:

```text
Supervisord started successfully
Xray version: Xray 26.3.27
API Port: 2222
XRay Core: v26.3.27
CAP_NET_ADMIN is available
Xray started
```

Listening ports inside node:

```text
tcp 127.0.0.1:61000 LISTEN rw-core
tcp :::1234 LISTEN rw-core
tcp :::2222 LISTEN node
```

## Remnawave API Verification

Final `/api/nodes` verification:

```json
{
  "count": 1,
  "connected_count": 1,
  "nodes": [
    {
      "name": "Local Smoke Node",
      "address": "remnanode-local",
      "port": 2222,
      "isConnected": true,
      "isConnecting": false,
      "isDisabled": false,
      "versions": {
        "xray": "26.3.27",
        "node": "2.7.0"
      },
      "xrayUptime": 29,
      "usersOnline": 0,
      "activeInbounds": 1
    }
  ]
}
```

## Result

`S1-VPN-012` local connected node result: **PASS**.

Accepted as local/dev evidence:

- Remnawave Node image can run locally.
- Local node can be registered through Remnawave API.
- Panel can connect to node through Docker network and `NODE_PORT=2222`.
- Xray starts inside node.
- `/api/nodes` reports `isConnected=true`.
- Node reports versions: Remnawave Node `2.7.0`, Xray `26.3.27`.

Not accepted as S1 go-live evidence:

- public/external VPN node readiness;
- production/staging node firewall restrictions;
- real domain/DNS route to node;
- user-facing host correctness;
- trial provisioning;
- paid provisioning;
- subscription URL/config delivery;
- outage retry behavior;
- Remnawave node backup/export/rebuild proof.

## Follow-Up

The repository's Ansible baseline currently references `remnawave/node:2.7.4`, but Docker Hub did not resolve that tag during local evidence capture. For S1, use an evidence-proven digest-pinned node image and update infra docs/playbooks once the production/staging node version is chosen.

## Container Cleanup

The next work item, `S1-INFRA-006`, does not require running containers. The local node container and compose stack were stopped after evidence capture without deleting volumes:

```bash
docker rm -f remnanode-local
docker compose -f infra/docker-compose.yml --profile proxy down
docker ps --format '{{.Names}}' | rg '^(remnawave|remnawave-db|remnawave-redis|caddy|remnanode-local)$' || true
```

Verification output for matching running containers was empty.

## Next Work Item

Next ID to execute: `S1-INFRA-006` — secrets inventory and interim secret storage/rotation policy.
