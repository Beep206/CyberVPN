> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-03
> Backlog ID: `S1-VPN-012`
> Статус: PASS-PARTIAL for local Remnawave control-plane smoke. This is local/dev evidence only.

# S1-VPN-012 Local Remnawave Smoke Evidence

## Purpose

Этот документ закрывает локальную часть `S1-VPN-012`: проверить, что Remnawave control-plane из `infra/docker-compose.yml` доступен в Docker, проходит healthcheck, работает через reverse proxy/TLS и принимает локальный API token для безопасного API smoke.

Это не staging/prod evidence и не закрывает `S1-VPN-001` / `S1-VPN-002`. В S1 go-live всё ещё нужны separate staging/prod Remnawave instances, trial/paid provisioning evidence, node evidence, outage retry evidence and backup/export/rebuild evidence.

## Preconditions

- `S1-INFRA-009` completed in `23_STAGE1_INFRA_009_LOCAL_DOCKER_COMPOSE_EVIDENCE.md`.
- Docker Desktop was running.
- Default local core stack was already up: `remnawave`, `remnawave-db`, `remnawave-redis`, `db-backup`.
- `proxy` profile was started only for this smoke because Remnawave blocks direct HTTP access to the app port.

## Commands Executed

Secrets were not printed. Token checks used local files only as shell variables.

```bash
docker compose -f infra/docker-compose.yml ps --services --status running
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' remnawave-db remnawave-redis remnawave db-backup
curl --max-time 10 -fsS http://127.0.0.1:3001/health
test -f infra/APIToken.txt
wc -c < infra/APIToken.txt
curl --max-time 10 -fsS -H "Authorization: Bearer <redacted>" http://127.0.0.1:3005/api/nodes
docker logs --tail=120 remnawave
docker compose -f infra/docker-compose.yml --profile proxy up -d caddy
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}} {{range $p, $conf := .NetworkSettings.Ports}}{{$p}}={{(index $conf 0).HostIp}}:{{(index $conf 0).HostPort}} {{end}}' caddy
curl --max-time 10 -k -sS -o /tmp/remnawave-panel-root.html -w 'panel_root http=%{http_code} bytes=%{size_download}\n' https://panel.localhost/
curl --max-time 10 -k -sS -o /tmp/remnawave-noauth.json -w 'nodes_no_auth http=%{http_code} bytes=%{size_download}\n' https://panel.localhost/api/nodes
curl --max-time 10 -k -sS -o /tmp/remnawave-badtoken.json -w 'nodes_infra_apitoken http=%{http_code} bytes=%{size_download}\n' -H "Authorization: Bearer <redacted>" https://panel.localhost/api/nodes
curl --max-time 10 -k -sS -o /tmp/remnawave-goodtoken.json -w 'nodes_task_worker_env_token http=%{http_code} bytes=%{size_download}\n' -H "Authorization: Bearer <redacted>" https://panel.localhost/api/nodes
jq -c '{response_count: ((.response // []) | length), response_type: (.response | type)}' /tmp/remnawave-goodtoken.json
```

## Running Stack

Running services before the smoke:

```text
db-backup
remnawave
remnawave-db
remnawave-redis
```

Docker health:

```text
/remnawave-db running healthy
/remnawave-redis running healthy
/remnawave running healthy
/db-backup running healthy
```

Remnawave metrics health:

```json
{"status":"ok","database":"up","redis":null}
```

`infra/APIToken.txt` exists, but its value was not printed. The file is 369 bytes and contains 3 lines.

## Direct HTTP Result

Direct app-port access failed:

```text
curl: (52) Empty reply from server
```

Remnawave logs showed the reason:

```text
Reverse proxy and HTTPS are required.
```

Conclusion: direct `http://127.0.0.1:3005` is not a valid local API smoke path for this Remnawave configuration. Local smoke must go through reverse proxy/TLS.

## Reverse Proxy Result

The local Caddy profile was started for the smoke:

```bash
docker compose -f infra/docker-compose.yml --profile proxy up -d caddy
```

Caddy result:

```text
/caddy running healthy 443/tcp=0.0.0.0:443 80/tcp=0.0.0.0:80
```

Panel root via local TLS:

```text
panel_root http=200 bytes=119683
```

Nodes API without auth:

```text
nodes_no_auth http=401 bytes=43
```

Nodes API with `infra/APIToken.txt` first-line token:

```text
nodes_infra_apitoken http=401 bytes=43
```

Nodes API with local `services/task-worker/.env` `REMNAWAVE_API_TOKEN`, value not printed:

```text
nodes_task_worker_env_token http=200 bytes=15
{"response_count":0,"response_type":"array"}
```

## Smoke Scope Result

| Check | Result |
|---|---|
| Remnawave container health | PASS |
| PostgreSQL dependency health | PASS |
| Valkey dependency health | PASS |
| Reverse proxy/TLS path | PASS |
| Unauthenticated API rejected | PASS: `401` |
| Authenticated nodes API | PASS: `200`, response array |
| Local node inventory | PASS with limitation: `0` nodes |
| Trial/paid provisioning | Not executed: no local VPN node and full staging smoke prerequisites are missing |

## Staging Smoke Script Assessment

The repository has a stronger script:

```bash
infra/scripts/remnawave-staging-smoke.sh
```

That script requires:

- `REMNAWAVE_BASE_URL`
- `REMNAWAVE_API_TOKEN`
- `API_BASE_URL`
- `EXPECTED_NODE_NAME`
- `ADMIN_LOGIN`
- `ADMIN_PASSWORD`
- `SMOKE_USER_LOGIN`
- `SMOKE_USER_PASSWORD`

It checks Remnawave nodes, backend auth, backend monitoring, node plugin facade, active subscription and optional cancel flow. This is the correct future staging/prod smoke shape, but it cannot be fully executed against the current local core-only stack because backend/admin/smoke-user credentials and an expected connected node are not available in this local setup.

## Security Notes

- Secret values were not intentionally printed into this evidence file.
- `infra/APIToken.txt` appears stale or invalid for the current local Remnawave instance.
- `services/task-worker/.env` contains a local Remnawave API token that works for local smoke. This file and any local `.env` token files must be handled in `S1-INFRA-006` / `S1-INFRA-007` as secrets-sensitive local inputs.
- Caddy binds local host ports `80` and `443` during the smoke. This is acceptable for local testing but should not be confused with production ingress evidence.

## Container Cleanup

The next work item, `S1-INFRA-006`, does not require running containers. The local compose stack was stopped after evidence capture without deleting volumes:

```bash
docker compose -f infra/docker-compose.yml --profile proxy down
docker compose -f infra/docker-compose.yml --profile proxy ps --services --status running
```

Verification output for running services was empty.

## Result

`S1-VPN-012` result: **PASS-PARTIAL**.

Accepted as local/dev evidence:

- Remnawave control-plane starts and reports healthy.
- Reverse proxy/TLS path is required and works locally.
- Remnawave API auth rejects unauthenticated requests.
- Authenticated `/api/nodes` returns a valid empty array.

Not accepted as S1 go-live evidence:

- staging/prod Remnawave deployment;
- connected VPN node evidence;
- trial provisioning evidence;
- paid provisioning evidence;
- provisioning retry evidence;
- Remnawave backup/export/rebuild evidence.

## Next Work Item

Next ID to execute: `S1-INFRA-006` — secrets inventory and interim secret storage/rotation policy.
