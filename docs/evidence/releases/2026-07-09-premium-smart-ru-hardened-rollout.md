# CyberVPN Premium Smart RU Hardened Rollout Evidence

Date: 2026-07-09
Production host: `45.87.41.146`
Source commit: `b35e7df64ea24cb11832a6e4644b1f70b6334b1f`
Backend release tag: `main-b35e7df-premium-smart-ru-xhttp-gate-20260709T122827Z`
Backend image digest: `sha256:fb938c134b2e2b87b64aa67df6ffb4da073928ead63662696c8e573a1a758b95`

## Scope

Executed the repository-controlled and production-accessible parts of
`docs/plans/CyberVPN_Premium_Smart_RU_Hardened_Rollout_TZ_2026_07_09.md`.

The user explicitly owns these manual checks:

- XHTTP real-client connectivity.
- HAPP/INCY response headers on real clients and real user agents.
- DE/RU route smoke on real clients.

Home Grafana/Prometheus infrastructure is down for maintenance by user context
and was not started locally.

## Repository Changes

- Added `scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml`.
- Replaced canonical `scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml` with hardened content.
- Updated `scripts/remnawave/seed-cybervpn-premium-smart-ru.sql` with hardened YAML, subscription settings, response headers, SMTP blocked ports, plugin non-overwrite guard, and fail-fast validation.
- Updated backend XHTTP gate so `REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=premium_smart_ru` requires the selected subscription plan code to be allowed.
- Added focused backend and seed contract tests.
- Updated production compose defaults in `infra/deploy/stage1/docker-compose.stage1.yml` for future deployments.

## Production Backend

Runtime after deploy:

```text
CYBERVPN_IMAGE_TAG=main-b35e7df-premium-smart-ru-xhttp-gate-20260709T122827Z
cybervpn-stage1-cybervpn-backend-1|cybervpn/cybervpn-backend:main-b35e7df-premium-smart-ru-xhttp-gate-20260709T122827Z|healthy
```

Runtime XHTTP/Smart RU env:

```text
REMNAWAVE_FEATURE_XHTTP_ALLOWED_PLAN_CODES=premium_smart_ru
REMNAWAVE_FEATURE_XHTTP_ALLOWED_USER_SEGMENTS=internal,beta,premium_smart_ru_canary
REMNAWAVE_FEATURE_XHTTP_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=false
REMNAWAVE_FEATURE_XHTTP_MIHOMO_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=premium_smart_ru
REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID=50e565d7-4980-4f0e-b469-71bf024d1799
REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID=fe11f814-cbe8-44bf-aeef-4e7aa1f16b53
REMNAWAVE_SMART_RU_PLAN_CODES=premium_smart_ru
REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME=CyberVPN Premium Smart RU
```

Runtime code fingerprint:

```text
/app/src/application/use_cases/subscriptions/generate_config.py
plan_code=True
user_segments=True
premium_smart_ru=True
_csv_values=True
```

Smoke:

```text
GET http://127.0.0.1:18080/health -> {"status":"ok"}
GET http://127.0.0.1:18080/api/v1/client/capabilities -> 200 JSON
```

## Remnawave Version

Running container:

```text
cybervpn-stage1-cybervpn-remnawave-1|remnawave/backend:2.8.0|healthy
container_image=remnawave/backend:2.8.0
package /opt/app/package.json -> {"name":"@remnawave/backend","version":"2.8.0"}
```

## Remnawave Seed Result

Seed command:

```text
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/seed-cybervpn-premium-smart-ru.sql
re-run with Mihomo v1.19.28-compatible template: /tmp/seed-cybervpn-premium-smart-ru-20260709T125601Z.sql
```

Result:

```text
external_squad_uuid=50e565d7-4980-4f0e-b469-71bf024d1799
external_squad_name=CYBERVPN_PREMIUM_SMART_RU
template_uuid=b48a1fc9-9e30-4272-94ff-ce0cdee790d1
template_name=CyberVPN Premium Smart RU
template_type=MIHOMO
internal_squad_uuid=fe11f814-cbe8-44bf-aeef-4e7aa1f16b53
internal_squad_name=CYBERVPN_PREMIUM_SMART_RU_NODES
node_plugin_uuid=babff9ce-ff43-4cba-9890-5b7f15281710
node_plugin_name=CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION
internal_squad_inbound_count=2
linked_node_inbounds=8
plugin_assigned_node_count=4
```

External squad settings:

```json
{
  "supportLink": "https://cyber-vpn.org/support",
  "happAnnounce": "CyberVPN Premium Smart RU: DE 25G + RU 25G smart routing. RU-сервисы работают без отключения VPN. Torrent запрещён.",
  "profileTitle": "CyberVPN Premium Smart RU",
  "profileUpdateInterval": 24,
  "isProfileWebpageUrlEnabled": true
}
```

Response headers:

```json
{
  "x-cybervpn-plan": "premium_smart_ru",
  "x-cybervpn-routing": "de-primary-ru-smart",
  "x-cybervpn-unlimited": "true"
}
```

## Nodes

Direct node evidence:

```text
s1-ru-spb-3 193.233.91.99:
  remnanode|remnawave/node:2.8.0
  network=host
  cap=["CAP_NET_ADMIN"]
  ports=443,8443,22230
  nft tables include remnanode/remnanode6
  backup=/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T120558Z-pre-2.8.0

s1-de-3 138.124.115.206:
  remnanode|remnawave/node:2.8.0
  network=host
  cap=["CAP_NET_ADMIN"]
  ports=443,8443,22230
  nft tables include remnanode/remnanode6
  backup=/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T120616Z-pre-2.8.0

s1-nl-4 138.16.140.44:
  remnanode|remnawave/node:2.8.0
  network=host
  cap=["CAP_NET_ADMIN"]
  ports=443,8443,22230
  nft tables include remnanode/remnanode6
  backup=/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T120648Z-pre-2.8.0

s1-ru-msk-3 178.159.94.225:
  accessed through prod-app-1 IPv6 path to 2a12:5940:e38b::2 because public IPv4 SSH timed out
  OS=Ubuntu 24.04.4 LTS
  kernel=6.8.0-124-generic
  remnanode|remnawave/node:2.8.0
  network=host
  cap=["CAP_NET_ADMIN"]
  ports=443,8443,22230
  nft tables include remnanode/remnanode6
  backup=/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T131210Z-pre-2.8.0
```

Moscow direct SSH evidence:

```text
s1-ru-msk-3 178.159.94.225:
  public IPv4 SSH attempts to ports 22/2222/22022/22222 timed out before banner exchange.
  prod-app-1 has IPv6 route to 2a12:5940:e38b::2 and SSH port 22 is reachable there.
  Temporary key forwarding through prod-app-1 allowed direct OS/Docker/image verification.
```

Remnawave Panel/DB node evidence:

```text
DE Frankfurt: address=138.124.115.206 port=22230 connected=true disabled=false plugin_assigned=true
NL Amsterdam: address=138.16.140.44 port=22230 connected=true disabled=false plugin_assigned=true
RU Moscow: address=172.30.3.1 port=32230 connected=true disabled=false plugin_assigned=true
RU SPB: address=193.233.91.99 port=22230 connected=true disabled=false plugin_assigned=true
all_smart_connected=4
moscow_node_inbound_links=2
```

## Inbounds

Internal squad:

```text
CYBERVPN_PREMIUM_SMART_RU_NODES
  VLESS_REALITY_443 tcp reality 443
  VLESS_XHTTP_REALITY_8443 xhttp reality 8443
```

Node inbound links:

```text
node_inbound_count=8
```

## Abuse Protection

Plugin:

```text
CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION
blocked_ports=[25,465,587]
torrent_enabled=true
plugin_assigned_count=4
```

TOR shared lists are present but intentionally empty:

```json
[
  {"name":"ext:tor-exit-nodes","type":"ipList","items":[]},
  {"name":"ext:tor-relays","type":"ipList","items":[]}
]
```

This is P0 placeholder behavior; TOR updater/list population remains P1.

## Invite

Production app DB:

```text
invite_code|LU7QQTQZHG|active|premium_smart_ru_lifetime_multi_root_2026_06_30|premium_smart_ru|lifetime||5|multi_use|100000|3
```

No new public tariff or root invite code was created by this rollout.

The user owns the final real registration/onboarding activation smoke with
`LU7QQTQZHG`. Codex did not create or delete `veephtc@gmail.com` during this
final pass after the user clarified they will register and verify the flow.

## Local Validation

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/unit/application/use_cases/subscriptions/test_generate_config.py backend/tests/integration/remnawave/test_remnawave_xhttp_subscription.py backend/tests/unit/application/use_cases/customer_subscriptions/test_service_access.py backend/tests/contract/remnawave/test_premium_smart_ru_hardened_rollout_seed.py -q --no-cov
exit=0
20 passed
```

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/security/test_stage1_paid_provisioning.py backend/tests/security/test_stage1_admin_manual_subscription_ops.py backend/tests/unit/application/use_cases/customer_subscriptions/test_service_access.py backend/tests/integration/test_growth_code_registry.py -q --no-cov
exit=0
35 passed
```

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/integration/remnawave/test_remnawave_2_8_contracts.py backend/tests/integration/remnawave/test_remnawave_xhttp_subscription.py backend/tests/contract/remnawave/test_premium_smart_ru_hardened_rollout_seed.py -q --no-cov
exit=0
7 passed
```

```text
backend/.venv/Scripts/python.exe -m ruff check <changed backend rollout files>
exit=0
All checks passed
```

```text
YAML count check
exit=0
groups=20
rule_providers=39
rules=59
```

```text
Downloaded official MetaCubeX Mihomo release asset:
https://github.com/MetaCubeX/mihomo/releases/download/v1.19.28/mihomo-linux-amd64-compatible-v1.19.28.gz

Mihomo Meta v1.19.28 linux amd64 with go1.26.5 Wed Jul  8 00:22:48 UTC 2026
mihomo -t -f scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml
exit=0
configuration file ...cybervpn-premium-smart-ru-de-primary-hardened.yaml test is successful
warnings: Classical inline providers only match contained domain rules
```

## Release Warnings

- Build logs selected yanked package versions from the existing backend lockfile: `charset-normalizer==3.4.8` and `grpcio==1.82.0`. This rollout did not change dependencies; backend image build and production smoke passed.
- `docker compose up -d cybervpn-backend` also recreated dependency `nats`; it returned healthy before backend start. No backend errors or tracebacks were observed in fresh logs after deploy.
- Remnawave API metadata probes returned no usable JSON through the attempted internal URLs; version evidence is from running image and `/opt/app/package.json`.
- Mihomo v1.19.28 rejected the previous `global-client-fingerprint` key and a proxy-group loop during review; both were removed before the final production seed re-run.

## Rollback Anchors

Backend/env rollback files:

```text
/srv/cybervpn/compose/app/.env.pre-main-b35e7df-premium-smart-ru-xhttp-gate-20260709T122827Z-20260709T122939Z
/srv/cybervpn/compose/app/.env.pre-premium-smart-ru-xhttp-20260709T122413Z
```

Node compose rollback backups:

```text
s1-ru-spb-3:/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T120558Z-pre-2.8.0
s1-de-3:/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T120616Z-pre-2.8.0
s1-nl-4:/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T120648Z-pre-2.8.0
s1-ru-msk-3:/opt/cybervpn/remnanode/current/docker-compose.yml.bak-20260709T131210Z-pre-2.8.0
```

XHTTP rollback:

```text
REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=canary
# or
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true
```

Template/plugin rollback:

```text
Re-run seed-cybervpn-premium-smart-ru.sql from the previous commit/template, or restore the previous Remnawave template/plugin config from DB backup/runbook.
```

## Unresolved

- User-owned: real XHTTP client connectivity.
- User-owned: HAPP/INCY response headers on real clients and real user agents.
- User-owned: DE/RU route smoke on real clients.
- User-owned: real registration/onboarding activation smoke with `LU7QQTQZHG`.
- TOR shared lists require P1 updater/list population before claiming full TOR egress blocking.
