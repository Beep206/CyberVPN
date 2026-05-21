# CyberVPN Stage 1 Rented Client Production Deployment Playbook

Date: `2026-05-18`

Target: `S1 - Controlled Public Beta`

Status: deployment preparation document

Owner: `@Sasha_Beep`

## Purpose

Этот документ фиксирует, что нужно сделать для публикации клиентской части CyberVPN на арендованных серверах, при этом домашний сервер остаётся для GitLab, CI evidence, observability, Sentry, Grafana, Loki, Alertmanager, Uptime, restore drills и архива.

Главная цель:

```text
Если домашний сервер выключился на 5 часов, пользовательский B2C-контур CyberVPN всё равно должен работать.
```

Под пользовательским B2C-контуром в Stage 1 понимается:

```text
public site / cabinet
-> registration/login
-> trial or payment
-> backend API
-> Telegram Bot / Mini App webhooks
-> Remnawave provisioning
-> QR/subscription URL/config delivery
-> VPN node connection
-> admin/support recovery
```

## Source Documents

Перед деплоем держать рядом:

- `docs/plans/2026-05-10-cybervpn-stage1-public-internet-deployment-plan.md`
- `docs/plans/2026-05-10-cybervpn-h-public-launch-readiness.md`
- `docs/cybervpn_stage1_launch_docs/20_HOME_LAB_NON_CRITICAL_OPTION.md`
- `docs/cybervpn_stage1_launch_docs/120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md`
- `docs/evidence/releases/stage1-stabilization-20260511.md`
- `docs/evidence/releases/stage1-pub-15c-production-vpn-node-trial-provisioning-20260511T072705Z.md`
- `docs/gitlab/README.md`
- `.private/cybervpn-h-10.10.10.34-access.md`

Security rule:

```text
Ничего из .private/ нельзя копировать в этот документ, GitLab logs, screenshots, issue comments, release notes или публичные evidence.
```

## Current Strategic Decision

CyberVPN Stage 1 больше не должен публиковаться как production-critical runtime с домашнего сервера.

Домашний сервер остаётся важным, но не является customer-critical path:

- GitLab first for repository CI/CD and release evidence;
- GitHub remains external fallback;
- Grafana/Prometheus/Loki/Alertmanager/Sentry/Uptime live at home;
- security scans and evidence archive live at home;
- restore drills can run at home;
- customer-facing runtime must run on rented infrastructure.

## Non-Negotiable Rule

Нельзя размещать на домашнем сервере как единственную production-точку:

- `cyber-vpn.net`;
- `admin.cyber-vpn.net`;
- `api.cyber-vpn.net`;
- Telegram production webhook;
- payment webhooks;
- production PostgreSQL;
- production Valkey/Redis if used for runtime coordination;
- production Remnawave control-plane;
- production VPN node;
- only copy of production backups.

Если дом выключился, допускается потерять:

- GitLab CI;
- Grafana dashboards;
- Loki/Sentry ingest;
- Uptime Kuma;
- release evidence archive;
- local restore lab;
- non-critical analytics.

Недопустимо потерять:

- вход пользователя;
- оплату или обработку webhook;
- provisioning;
- VPN доступ;
- админский emergency-доступ;
- rollback на арендованном runtime;
- свежий backup production DB.

---

# 1. Target Architecture

## 1.1 Recommended S1 Split

```text
Internet
  |
  v
Cloudflare DNS / TLS / WAF / redirects
  |
  +--> rented app/control-plane server
  |      - Caddy/Nginx
  |      - frontend
  |      - admin
  |      - backend API
  |      - Telegram Bot webhook runtime
  |      - worker/scheduler
  |      - Valkey/Redis
  |      - PostgreSQL if budget mode
  |      - Remnawave control-plane if budget mode
  |
  +--> rented VPN node 1
         - Remnawave node
         - Xray/VPN transport
         - DNS-only VPN hostname
         - no app/API/admin monitoring relay
         - no unrelated exporter/support/payment/backend workload

Home server 10.10.10.34
  - GitLab
  - GitLab Runner
  - Grafana
  - Prometheus
  - Loki
  - Alertmanager
  - Sentry
  - Uptime Kuma
  - restore lab
  - evidence archive
  - secondary backup copy
```

## 1.2 Production-Correct S1 Variant

Этот вариант лучше для реального запуска, но дороже.

| Component | Placement | Why |
|---|---|---|
| Public frontend/cabinet | Rented app server | Always available to users |
| Admin | Rented app server, protected | Support must work during incidents |
| Backend API | Rented app server | Auth, payments, provisioning |
| Telegram Bot webhook runtime | Rented app server | Telegram webhook must be reachable |
| Worker/scheduler | Rented app server | Payment/provisioning/reconciliation jobs |
| PostgreSQL 17 | Managed DB or separate DB VPS | Source of truth |
| Valkey/Redis | Managed/private or same app VPS for beta | Cache/rate limit/queue acceleration |
| Remnawave control-plane | App server or separate private VPS | VPN access authority |
| VPN node 1 | Separate rented VPS | User traffic endpoint |
| Object/offsite backup | Provider object storage or backup storage | DB restore if app server dies |
| GitLab/CI | Home | Non-critical for runtime |
| Observability | Home | Accepted Stage 1 cost tradeoff |

## 1.3 Minimum Budget S1 Variant

Этот вариант дешевле и допустим только как small controlled beta, если owner явно принимает риск.

| Server | Size | Runs |
|---|---:|---|
| `prod-app-1` | `4 vCPU / 8 GB RAM / 120-160 GB NVMe` minimum | frontend, admin, backend, bot, worker, scheduler, PostgreSQL, Valkey, Remnawave control-plane |
| `prod-vpn-node-1` | `2 vCPU / 2-4 GB RAM / 40-80 GB NVMe`, high traffic | Remnawave node / VPN transport |
| Offsite backup storage | `50-100 GB` start | encrypted DB dumps, Remnawave export, deploy bundle |

This is not as clean as the approved `managed PostgreSQL/private Valkey` decision, but it is a practical bridge if the first goal is to publish safely with minimal monthly cost.

Required risk acceptance for budget mode:

```text
PostgreSQL and Remnawave control-plane are temporarily colocated on prod-app-1 for S1 small beta.
RPO/RTO risk is accepted only if encrypted off-host backups and restore drill evidence exist before inviting users.
```

## 1.4 Recommended S1 Starting Point

For the first real public beta I recommend:

```text
Rent 2 servers now:
1. prod-app-1
2. prod-vpn-node-1

Add the smallest off-host backup storage immediately.

Do not rent Kubernetes, load balancer, extra app nodes, managed Grafana/Sentry, or partner/mobile/desktop infrastructure yet.
```

Reasoning:

- one app/control-plane server is enough for controlled beta;
- one VPN node is the missing P0 blocker;
- off-host backup is cheap compared to losing production DB;
- home observability can remain non-critical;
- Kubernetes/Talos/GitOps are Stage 7, not Stage 1 blockers;
- partner/mobile/desktop/Helix are outside Stage 1.

---

# 2. What To Rent

## 2.0 Current Owner Selection

Owner selection, updated `2026-05-19`:

```text
prod-app-1 selected: VPS X16
prod-vpn-node-1 selected: HostBrr AMD Ryzen 9 5950X Powered VPS, 2 core / 4 GB
```

`prod-app-1` selected characteristics:

| Field | Value |
|---|---|
| Product | `VPS X16` |
| CPU | `6 CPU cores` |
| RAM | `16 GB DDR4 RAM` |
| Disk | `240 GB SSD` |
| Bandwidth | `25 TB` |
| IPv4 | `45.87.41.146` |
| IPv6 allocation | `2a0d:2787:1b:12f5::/64` |

Decision:

```text
Accept VPS X16 as prod-app-1 for Stage 1 controlled beta.
```

This is a materially better app/control-plane choice than the previous netcup VPS 1000 G12 candidate because it doubles RAM to `16 GB`, provides `6 CPU cores`, and stays inside the recommended colocated DB/control-plane sizing band for Stage 1.

Recommended configuration for the order:

| Option | Recommendation |
|---|---|
| SSH | install the CyberVPN public deploy key and confirm key-only access |
| Networking | use IPv4 for first deployment; configure IPv6 only after firewall baseline is complete |
| Backups | provider snapshot is useful, but not enough; still configure encrypted off-host DB backup |
| Extra storage | not needed initially; add only if DB/backups/logs grow |

Important sizing caveat:

```text
VPS X16 is acceptable for the first Stage 1 app/control-plane deployment with frontend, admin, backend, bot, worker, scheduler, PostgreSQL, Valkey and Remnawave control-plane colocated on one host.
```

Memory gate:

| Condition | Action |
|---|---|
| sustained RAM usage above `75%` | review container limits and DB memory |
| sustained swap usage above `512 MB` | treat as warning before user expansion |
| OOM kill or repeated container restart | stop cohort expansion |
| PostgreSQL/Remnawave latency visible under beta load | upgrade to VPS 2000 G12 or move DB/Remnawave to separate server |
| more than `10-25` active beta users or paid users | review upgrade before expansion |

Upgrade path:

```text
If prod-app-1 becomes constrained, move PostgreSQL/Remnawave to managed/separate infrastructure or upgrade before expanding beyond the first controlled cohort.
```

## 2.1 Server `prod-app-1`

Purpose:

- public website;
- customer cabinet;
- backend API;
- admin UI;
- Telegram Bot webhook runtime;
- worker/scheduler;
- production DB/Valkey if budget mode;
- Remnawave control-plane if budget mode.

Minimum:

| Resource | Minimum |
|---|---:|
| CPU | 4 vCPU |
| RAM | 8 GB |
| Disk | 120 GB NVMe |
| Network | 1 Gbit/s |
| Traffic | 2-5 TB/month minimum |
| OS | Ubuntu 24.04 LTS |
| IPv4 | 1 public IPv4 |
| IPv6 | enabled if available |
| Firewall | provider firewall + UFW |
| Backups | provider snapshot optional, app-level backup mandatory |

Recommended if DB is colocated:

| Resource | Recommended |
|---|---:|
| CPU | 4-8 vCPU |
| RAM | 16 GB |
| Disk | 160-240 GB NVMe |
| Traffic | 5 TB/month or more |

Do not undersize this below `4 vCPU / 8 GB` if PostgreSQL and Remnawave are on the same host.

For the selected VPS X16:

```text
This satisfies the recommended colocated DB/control-plane baseline for Stage 1.
Treat it as acceptable for controlled beta, not as the final S2/S3 scale topology.
```

## 2.2 Server `prod-vpn-node-1`

Purpose:

- user VPN traffic;
- Remnawave node;
- Xray/VPN transport;
- no app database;
- no GitLab;
- no Grafana;
- no Sentry.

Minimum:

| Resource | Minimum |
|---|---:|
| CPU | 2 vCPU |
| RAM | 2 GB |
| Disk | 40 GB NVMe/SSD |
| Network | 1 Gbit/s |
| Traffic | as high as possible; ideally 10-20 TB/month |
| OS | Ubuntu 24.04 LTS |
| IPv4 | 1 public IPv4 |
| IPv6 | enabled if available |

Recommended:

| Resource | Recommended |
|---|---:|
| CPU | 2-4 vCPU |
| RAM | 4 GB |
| Disk | 80 GB |
| Traffic | 20 TB/month or unmetered fair-use |

Provider checks before paying:

- VPN/proxy use is not forbidden by provider AUP;
- high outbound traffic is allowed;
- abuse handling is clear;
- PTR/rDNS can be configured if needed;
- provider firewall exists;
- Docker is allowed;
- TUN/TAP/kernel modules are not blocked;
- ports required by Remnawave node can be opened.

### Previous Candidate: JustHost

Owner previously considered JustHost for `prod-vpn-node-1`.

Source pages checked on `2026-05-18`:

- <https://justhost.ru/en/services/vps/tariffs-all>
- <https://justhost.ru/ru/services/vps/tariffs>
- <https://support.justhost.ru/ru-RU/support/solutions/articles/151000171922-%D0%B5%D1%81%D1%82%D1%8C-%D0%BB%D0%B8-%D0%BE%D0%B3%D1%80%D0%B0%D0%BD%D0%B8%D1%87%D0%B5%D0%BD%D0%B8%D0%B5-%D0%BD%D0%B0-%D1%83%D1%81%D0%BB%D1%83%D0%B3%D0%B0%D1%85->

Observed relevant JustHost tariff options:

| Tariff | CPU | RAM | NVMe | Port / fair-share | Monthly traffic equivalent shown by provider | Use for S1 |
|---|---:|---:|---:|---:|---:|---|
| `Alpha Centauri` | 2 core | 2 GB | 40 GB | 400 Mbit | 124+ TB | Minimum budget node |
| `Vega` | 2 core | 4 GB | 80 GB | 500 Mbit | 155+ TB | Recommended first node |
| `Capella` | 4 core | 4 GB | 120 GB | 750 Mbit | 232+ TB | Better if budget allows |
| `Rigel` | 4 core | 8 GB | 200 GB | 750 Mbit | 232+ TB | Not needed for first tiny beta |

JustHost support article states that they do not impose service-side restrictions on VPS in general, but resources depend on the tariff, PROMO plans may have open-port restrictions, and service may be limited after complaints or violations.

Recommendation:

```text
Use JustHost Vega as prod-vpn-node-1 for the first Stage 1 production VPN node.
```

Why `Vega`:

- `2 core / 4 GB RAM` is safer than `2 GB` for a node that will run Remnawave node/Xray and metrics;
- `80 GB NVMe` is enough for OS, Docker, logs and operational headroom;
- `500 Mbit fair-share` is enough for the first controlled beta;
- it is still much cheaper than overbuying a 4-8 core plan before real usage data exists.

Acceptable lower-cost fallback:

```text
Alpha Centauri is acceptable only if the first cohort is tiny and trial-only.
```

Recommended higher-headroom option:

```text
Capella is the better choice if the price difference is acceptable or if the first node should support more concurrent users without an early migration.
```

Avoid for production node:

- `VPS Promo`, because it is promotional/month-limited and has port restrictions;
- `Sirius` / `Arcturus`, because `1 core` is too tight for a real customer VPN exit node;
- IPv6-only plans for the first node, because many users/networks still require IPv4 reachability.

### Final S1 Selection: HostBrr

Owner selection, updated `2026-05-19`:

| Field | Value |
|---|---|
| Provider | `hostbrr.com` |
| Product | AMD Ryzen 9 5950X Powered Virtual Private Server |
| CPU | `2 core` |
| RAM | `4 GB` |
| IPv4 | `77.90.13.29` |
| IPv6 allocation | `2a0a:51c1:9:c3::/64` |
| Runtime hostname | `de-1.cyber-vpn.org` |
| Node alias | `de-1.node.cyber-vpn.org` |

Decision:

```text
Use HostBrr AMD Ryzen 9 5950X VPS as prod-vpn-node-1 for Stage 1.
```

Owner DNS decision:

```text
VPN node DNS records must live only in cyber-vpn.org.
Do not create or keep VPN node records under cyber-vpn.net.
```

Applied S1 DNS:

```text
de-1.cyber-vpn.org A/AAAA -> prod-vpn-node-1
de-1.node.cyber-vpn.org A/AAAA -> prod-vpn-node-1
```

Rejected/removed S1 DNS:

```text
de-1.cyber-vpn.net
de-1.node.cyber-vpn.net
```

If JustHost is revisited later, open a support ticket and get written confirmation:

```text
We plan to use the VPS as a commercial VPN exit node for CyberVPN Stage 1 beta using Remnawave/Xray.
Is this allowed under JustHost rules?
Are there restrictions on VPN/proxy traffic, UDP/TCP ports, high outbound traffic, or abuse complaint handling?
Can the selected location and tariff be used for this purpose?
```

Do not invite users until this answer is saved as evidence.

## 2.3 Off-Host Backup Storage

Minimum:

| Resource | Minimum |
|---|---:|
| Capacity | 50 GB |
| Encryption | client-side |
| Retention | 14 days |
| Access | restricted backup key |

Recommended:

```text
100 GB object storage or backup storage for encrypted PostgreSQL/Remnawave dumps.
Home server pulls a second copy when it is online.
```

Do not rely only on:

- provider snapshots;
- home HDD;
- Git repository;
- Docker volumes without dumps.

## 2.4 Optional For Later

Do not rent these at first unless there is a clear reason:

| Optional item | Stage |
|---|---|
| Load balancer | S2 |
| Second app server | S2 |
| Second VPN node | S1 expansion or S2 |
| Managed PostgreSQL HA | S2 |
| Managed Redis/Valkey | S2 |
| Kubernetes/Talos | S7 |
| Managed Grafana/Sentry | Later, if home observability becomes insufficient |
| Partner portal production server | S3 |
| Mobile/desktop update infrastructure | S4/S5 |

---

# 3. Provider Selection

## 3.1 Practical Candidates

No provider is approved by this document. Choose after checking account, payment method, region, VPN/proxy policy and abuse process.

| Provider type | Pros | Risks |
|---|---|---|
| Low-cost EU VPS provider | Good price/performance, enough for S1 | Support/account/abuse policy must be checked |
| DigitalOcean-style cloud | Good docs, predictable products, managed DB option | More expensive for same raw resources |
| Dedicated server provider | Better traffic/cpu for VPN later | Overkill for first beta app runtime |
| Local/regional VPS | Useful for target market latency | Often weaker automation/backups/private networking |

## 3.2 Current External References

These were checked for planning context on `2026-05-18`:

- Netcup VPS 1000 G12 product page: current listed resources are `4 vCore`, `8 GB DDR5 ECC RAM`, `256 GB NVMe`, `2.5 GBit/s` interface, traffic flatrate and temporary throttling to `200 Mbps` if average traffic over the last 24 hours exceeds `2 TB`. Reference: <https://www.netcup.com/en/server/vps/vps-1000-g12-iv-12m>
- Netcup VPS overview: VPS 1000 G12 is listed as `4 vCore`, `8 GB DDR5 ECC RAM`, `256 GB NVMe`, traffic included and snapshots available. Reference: <https://www.netcup.com/en/server/vps>
- JustHost VPS tariffs: relevant VPN-node candidates are `Alpha Centauri`, `Vega`, `Capella` and `Rigel`; JustHost lists fair-share unmetered ports and large monthly traffic equivalents. Reference: <https://justhost.ru/en/services/vps/tariffs-all>
- JustHost service limitations article: VPS services are generally not limited by JustHost side, resources depend on tariff, PROMO plans may have open-port restrictions, and services may be limited after complaints or violations. Reference: <https://support.justhost.ru/ru-RU/support/solutions/articles/151000171922-%D0%B5%D1%81%D1%82%D1%8C-%D0%BB%D0%B8-%D0%BE%D0%B3%D1%80%D0%B0%D0%BD%D0%B8%D1%87%D0%B5%D0%BD%D0%B8%D0%B5-%D0%BD%D0%B0-%D1%83%D1%81%D0%BB%D1%83%D0%B3%D0%B0%D1%85->
- Hetzner Cloud docs: cloud servers can be shared or dedicated resources, with Firewalls, Volumes, Networks, Backups and Snapshots available. Public IPs are separate Primary IP resources, and IPv4 has a monthly cost in the documented model. Reference: <https://docs.hetzner.com/cloud/servers/overview/>
- Hetzner price adjustment docs: new cloud prices took effect on `2026-04-01`; check current prices before ordering. Reference: <https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/>
- DigitalOcean Droplet docs/pricing: Droplets are VMs, billed per-second with a monthly cap; powered-off droplets are still billed because resources remain reserved. Reference: <https://docs.digitalocean.com/products/droplets/details/pricing/>
- DigitalOcean public pricing page: basic Droplets start from low monthly tiers and include outbound transfer by plan; exact price depends on CPU/RAM/SSD/bandwidth. Reference: <https://www.digitalocean.com/pricing/droplets>
- Cloudflare DNS proxy docs: proxied A/AAAA/CNAME web records route HTTP/HTTPS through Cloudflare; DNS-only records expose the origin IP and do not get Cloudflare HTTP protection. Reference: <https://developers.cloudflare.com/dns/proxy-status/>

## 3.3 Recommendation

For first Stage 1 publication:

```text
Use one low-cost provider for prod-app-1 and prod-vpn-node-1 if private networking/firewall is available.
Prefer the same datacenter/region for app/control-plane and first VPN node only if that region matches the first beta users.
```

If first users are mostly RU/CIS:

- do not host everything inside Russia unless legal/payment/support is explicitly ready;
- start with a stable EU region with good route quality;
- add region-specific VPN nodes later.

If first users are global:

- app server in EU is acceptable;
- first VPN node in EU;
- second node later in another region based on observed demand.

---

# 4. What Stays On The Home Server

Home server `10.10.10.34` remains useful and should not be thrown away.

## 4.1 Keep At Home

| Service | Stage 1 role |
|---|---|
| GitLab | first CI/CD and release evidence |
| GitLab Runner | builds, tests, security scans |
| GitLab Registry | useful, but production must not require it at runtime |
| GitHub remote | external fallback |
| Grafana | main dashboard UI for owner |
| Prometheus | scrape rented runtime if home is online |
| Alertmanager | alert routing when home is online |
| Loki/Promtail | log aggregation when home is online |
| Sentry | app error collection when home is online |
| Uptime Kuma | synthetic checks when home is online |
| Restore lab | restore drills from production backups |
| Evidence archive | release/runbook/evidence copy |
| Security scans | secrets/dependency/SBOM/bundle scans |

## 4.2 Home Server Outage Impact

If home server goes down:

| Area | Expected impact |
|---|---|
| Website/cabinet | No impact |
| API | No impact |
| Telegram Bot webhook | No impact |
| Payment webhook | No impact |
| VPN node | No impact |
| Production DB | No impact |
| Admin | No impact |
| GitLab CI | Down |
| Grafana/Sentry/Loki | Down or degraded |
| Alertmanager | Down |
| Evidence archive | Temporarily inaccessible |
| Home backup copy | Delayed |

This is acceptable for S1 only if:

- production runtime logs remain locally available on rented servers;
- production DB backups continue off-host;
- emergency SSH/admin access to rented servers is documented;
- rollback does not require home GitLab.

## 4.3 Production Must Not Depend On Home GitLab

GitLab first is fine for CI/CD, but rented runtime must not need home GitLab to continue serving users.

Allowed:

- build/test in home GitLab;
- store release evidence in GitLab;
- push source to GitLab first;
- mirror/push same commit to GitHub;
- archive release bundle at home.

Required:

- production server has local immutable images or can rebuild from GitHub fallback;
- production rollback uses local image tags or stored tarballs;
- production secrets are on rented server, not in GitLab;
- production startup does not call home GitLab/Sentry/Grafana as a hard dependency.

---

# 5. DNS And Domain Plan

## 5.1 Public Domains

| Host | Target |
|---|---|
| `cyber-vpn.net` | rented app server edge |
| `www.cyber-vpn.net` | rented app server edge |
| `api.cyber-vpn.net` | rented app server edge |
| `admin.cyber-vpn.net` | rented app server edge, protected |
| `status.cyber-vpn.net` | frontend/status page or static status route |
| `cyber-vpn.org` | reserved for VPN nodes and future subscription delivery only; not a `.net` mirror |
| `www.cyber-vpn.org` | not used for S1 customer web |
| `admin.cyber-vpn.org` | not used for S1 admin; must not serve admin |

## 5.2 VPN Node DNS

VPN node records should normally be DNS-only unless you use a Cloudflare product that supports non-HTTP proxying for the required transport.

Candidate:

```text
de-1.cyber-vpn.org -> prod-vpn-node-1 public IP, DNS-only
de-1.node.cyber-vpn.org -> prod-vpn-node-1 public IP, DNS-only
```

Do not proxy VPN transport through normal Cloudflare HTTP proxy unless the protocol and product explicitly support it.

Future subscription delivery may use a dedicated `.org` hostname, for example `sub.cyber-vpn.org`, but only after DNS/TLS/route evidence exists. Until then, do not silently move live subscription URLs.

## 5.3 Cloudflare Proxy Rules

Recommended:

| Record | Proxy |
|---|---|
| `cyber-vpn.net` | Proxied |
| `www.cyber-vpn.net` | Proxied |
| `api.cyber-vpn.net` | Proxied only if webhook paths are not challenged |
| `admin.cyber-vpn.net` | Proxied, with Access/IP allowlist if configured |
| `status.cyber-vpn.net` | Proxied |
| VPN node hostnames | DNS-only |

Payment and Telegram webhook paths must not receive browser challenges:

```text
/webhook/telegram
/api/v1/payments/*/webhook
/api/payments/*/webhook
```

---

# 6. Network And Firewall Model

## 6.1 `prod-app-1` Open Ports

Public:

| Port | Purpose |
|---:|---|
| 80/tcp | HTTP challenge/redirect |
| 443/tcp | HTTPS public site/API/admin/webhooks |

Restricted:

| Port | Purpose |
|---:|---|
| 22/tcp | SSH from owner/admin IP only |
| metrics ports | only from home server or WireGuard |
| PostgreSQL | no public access |
| Valkey/Redis | no public access |
| Remnawave internal API | no public access |

## 6.2 `prod-vpn-node-1` Open Ports

Public:

| Port | Purpose |
|---:|---|
| VPN transport port | Xray/Remnawave node traffic |

Restricted:

| Port | Purpose |
|---:|---|
| 22/tcp | SSH from owner/admin IP only |
| node control/management | only from Remnawave control-plane |
| metrics | only from home server or WireGuard |

## 6.3 Private Connectivity

Preferred order:

1. Provider private network if both servers are in the same provider/region.
2. WireGuard overlay between `prod-app-1`, `prod-vpn-node-1` and home server.
3. Public IP with strict firewall allowlist only if private network/overlay is not available.

Recommended WireGuard peers:

```text
prod-app-1
prod-vpn-node-1
home-observability
owner-laptop optional
```

WireGuard use:

- Remnawave control-plane to node management path;
- Prometheus scrape from home to rented servers;
- SSH/admin emergency path if public SSH is disabled later;
- backup pull from home.

---

# 7. Runtime Layout On `prod-app-1`

## 7.1 Directory Layout

Create:

```text
/srv/cybervpn
/srv/cybervpn/compose
/srv/cybervpn/releases
/srv/cybervpn/env
/srv/cybervpn/secrets
/srv/cybervpn/backups
/srv/cybervpn/logs
/srv/cybervpn/runbooks
/srv/cybervpn/evidence
```

Permissions:

```text
/srv/cybervpn/secrets  -> root:root 0700
/srv/cybervpn/env      -> root:root 0700
env files              -> root:root 0600
```

## 7.2 Containers

Budget mode on one app server:

| Container | Public? | Notes |
|---|---:|---|
| `cybervpn-caddy` | Yes | HTTPS edge |
| `cybervpn-frontend` | Behind edge | website/cabinet |
| `cybervpn-admin` | Behind protected edge | admin |
| `cybervpn-backend` | Behind edge/internal | API/webhooks |
| `cybervpn-telegram-bot` | No direct public port | webhook runtime |
| `cybervpn-worker` | No | jobs |
| `cybervpn-scheduler` | No | periodic jobs |
| `cybervpn-postgres` | No | source of truth in budget mode |
| `cybervpn-valkey` | No | cache/queues |
| `cybervpn-remnawave` | No direct public API | control-plane |
| `cybervpn-remnawave-postgres` | No | Remnawave DB |
| `cybervpn-remnawave-valkey` | No | Remnawave cache |
| `node-exporter` | No public | metrics |
| `postgres-exporter` | No public | metrics |
| `redis-exporter` | No public | metrics |

## 7.3 Image Policy

Production should deploy immutable images:

```text
local/cybervpn-frontend:stage1-beta-rc.N
local/cybervpn-admin:stage1-beta-rc.N
local/cybervpn-backend:stage1-beta-rc.N
local/cybervpn-telegram-bot:stage1-beta-rc.N
local/cybervpn-task-worker:stage1-beta-rc.N
```

Acceptable S1 image paths:

1. Build images in home GitLab, export image tarballs, copy to `prod-app-1`, load with `docker load`.
2. Build images directly on `prod-app-1` from immutable GitHub fallback SHA/tag.
3. Push images to an external registry later.

Avoid:

- `latest`;
- floating `main`;
- runtime pull from home GitLab as the only source.

---

# 8. Secrets And Env Files

## 8.1 Required Secret Groups

Create separate env/secret files:

```text
/srv/cybervpn/env/backend.env
/srv/cybervpn/env/frontend.env
/srv/cybervpn/env/admin.env
/srv/cybervpn/env/telegram-bot.env
/srv/cybervpn/env/worker.env
/srv/cybervpn/env/remnawave.env
/srv/cybervpn/env/postgres.env
/srv/cybervpn/env/valkey.env
/srv/cybervpn/env/caddy.env
```

Do not use one giant `.env` for everything.

## 8.2 Required Runtime Decisions

Before public enablement:

| Setting | First state |
|---|---|
| `REGISTRATION_ENABLED` | `false` until smoke passes |
| `REGISTRATION_INVITE_REQUIRED` | `true` |
| `PAYMENTS_ENABLED` | `false` until provider proof |
| `STAGE1_TRIAL_PROVISIONING_ENABLED` | `false` until production VPN node proof |
| `STAGE1_PAID_PROVISIONING_ENABLED` | `false` until paid proof |
| `REFERRAL_ENABLED` | `false` |
| `PROMO_CODES_ENABLED` | `false` |
| `GIFT_CODES_ENABLED` | `false` |
| `ADMIN_2FA_REQUIRED` | `true` |
| `PAYMENT_AUTORENEWAL_ENABLED` | `false` |

Only after smoke:

```text
Enable one thing at a time:
1. admin login
2. public frontend
3. Telegram webhook
4. production VPN node
5. trial provisioning for disposable identity
6. invite-only registration
7. payment path if paid beta is included
```

## 8.3 Secret Rotation

New rented deployment should use new production secrets:

- JWT secret;
- cookie/session secret;
- admin bootstrap secret;
- TOTP encryption secret if used;
- Remnawave token;
- Telegram bot token if previous token was exposed in chat/history;
- payment provider tokens;
- backup encryption password/key;
- database passwords;
- Valkey password;
- Caddy/Cloudflare token if server manages DNS challenge.

If a token was ever shared in chat or evidence, rotate it before production use.

---

# 9. Deployment Phases

## PHASE 0 - Owner Budget And Scope Freeze

Goal: decide exactly what to pay for.

Steps:

1. Choose provider.
2. Choose region.
3. Decide budget mode vs production-correct mode.
4. Confirm whether first public beta is trial-only or includes paid path.
5. Confirm support channel for first users.
6. Confirm that observability home outage risk is accepted for S1.
7. Record decision in a new evidence file.

Exit criteria:

```text
Provider, region, server count, budget, first cohort type and risk acceptance are written down.
```

## PHASE 1 - Rent Servers

Create:

```text
prod-app-1
prod-vpn-node-1
```

Recommended labels/tags:

```text
project=cybervpn
stage=s1
env=production
role=app
role=vpn-node
owner=sasha-beep
```

Record:

- provider;
- region;
- server plan;
- public IPv4;
- IPv6 prefix if any;
- private IP;
- monthly cost;
- traffic allowance;
- backup/snapshot option;
- firewall ID;
- creation time.

Do not record:

- root password;
- SSH private key;
- API token;
- provider account password.

Exit criteria:

```text
Both servers exist, SSH works, provider firewall is attached, and no application is deployed yet.
```

## PHASE 2 - OS Baseline

On both servers:

1. Install Ubuntu 24.04 LTS.
2. Create deploy/admin user.
3. Disable password SSH if safe.
4. Restrict SSH to owner/admin IP or WireGuard.
5. Enable UFW.
6. Install `fail2ban`.
7. Install Docker Engine and Compose plugin.
8. Configure unattended security updates.
9. Configure timezone UTC.
10. Configure hostname:
    - `prod-app-1`
    - `prod-vpn-node-1`
11. Configure journald limits.
12. Configure Docker log rotation.

Evidence commands:

```bash
lsb_release -a
uname -a
docker version
docker compose version
ufw status verbose
ss -ltnp
systemctl status docker --no-pager
```

Exit criteria:

```text
OS hardened, Docker ready, only expected ports listening.
```

## PHASE 3 - Private Network / WireGuard

Goal: production servers and home observability can communicate without opening private ports publicly.

Steps:

1. Create provider private network if available.
2. Configure WireGuard if provider private network is not enough.
3. Add peers:
   - `prod-app-1`
   - `prod-vpn-node-1`
   - `home-observability`
4. Allow metrics and management only over private IP/WireGuard.
5. Confirm public access is not required for DB/Valkey/Remnawave API/metrics.

Exit criteria:

```text
prod-app-1 can reach prod-vpn-node-1 privately.
home server can scrape metrics privately when it is online.
Public internet cannot reach private service ports.
```

## PHASE 4 - DNS/TLS Edge

Goal: point public customer domains to rented app server.

Cloudflare records:

```text
cyber-vpn.net        A -> prod-app-1, DNS-only for temporary health/TLS evidence
www.cyber-vpn.net    A -> prod-app-1, DNS-only for temporary health/TLS evidence
api.cyber-vpn.net    A -> prod-app-1, DNS-only until webhook behavior is proven
admin.cyber-vpn.net  A -> prod-app-1, DNS-only until admin protection is proven
status.cyber-vpn.net A -> prod-app-1, DNS-only for temporary status evidence
cyber-vpn.org        reserved/no customer web mirror
www.cyber-vpn.org    reserved/no customer web mirror
admin.cyber-vpn.org  reserved/no admin mirror
de-1.cyber-vpn.org A/AAAA -> prod-vpn-node-1, DNS-only
de-1.node.cyber-vpn.org A/AAAA -> prod-vpn-node-1, DNS-only
```

For `STAGE1-RENT-03`, IPv4 DNS-only is acceptable. Cloudflare proxy/WAF can be enabled later after app routing, admin protection and webhook no-challenge behavior are proven.

On `prod-app-1`:

1. Install Caddy or Nginx.
2. Configure TLS.
3. Ensure `.org` customer/admin mirror routes are not enabled.
4. Configure security headers.
5. Configure no-challenge webhook paths.
6. Configure admin protection.

Exit criteria:

```text
Public web/API/admin domains resolve to rented app server and return expected temporary health pages.
VPN node domain resolves DNS-only to VPN node.
```

## PHASE 5 - Runtime Compose

Goal: install CyberVPN app stack on `prod-app-1`.

Create:

```text
/srv/cybervpn/compose/docker-compose.yml
/srv/cybervpn/env/*.env
/srv/cybervpn/secrets/*
```

Initial state:

```text
registration disabled
payments disabled
trial provisioning disabled
paid provisioning disabled
referral/promo/gift disabled
admin 2FA required
```

Deploy order:

1. PostgreSQL.
2. Valkey.
3. Remnawave DB/cache.
4. Remnawave control-plane.
5. Backend.
6. Worker/scheduler.
7. Frontend.
8. Admin.
9. Telegram Bot.
10. Caddy public routing.

Runtime edge note:

```text
For Next.js / next-intl locale redirects behind Caddy, pass X-Forwarded-Port=443 on HTTPS reverse_proxy routes.
Without it, root locale redirects can leak the upstream container port, for example https://cyber-vpn.net:3000/en-EN.
```

Exit criteria:

```text
All app containers are healthy locally on prod-app-1.
Public routes can show safe disabled-state UI.
No public registration/payment/provisioning is enabled.
```

## PHASE 6 - Database And Migrations

Goal: make DB state durable and reproducible.

Steps:

1. Create app DB and DB user.
2. Create Remnawave DB and DB user.
3. Apply clean migrations.
4. Run migration smoke.
5. Seed minimal Stage 1 data:
   - plan catalog;
   - support profile;
   - legal links;
   - feature flags;
   - Remnawave profile mapping.
6. Run first admin bootstrap.
7. Enforce admin 2FA.
8. Disable bootstrap endpoint/secret after use.
9. Capture redacted evidence.

Exit criteria:

```text
Clean DB migrations pass on production DB.
First owner/super_admin exists.
2FA is mandatory.
No default credentials exist.
Bootstrap is disabled after use.
```

## PHASE 7 - Remnawave Control-Plane And VPN Node

Goal: close current P0 blocker from `STAGE1-PUB-15C`.

On `prod-app-1`:

1. Run Remnawave control-plane.
2. Keep Remnawave API private/internal.
3. Configure backend Remnawave API token.
4. Configure Remnawave profiles/inbounds.

On `prod-vpn-node-1`:

1. Install Docker.
2. Deploy Remnawave node.
3. Connect node to control-plane.
4. Open only required VPN transport port.
5. Restrict management/control ports.
6. Set node name not containing `lab`, `local`, `home` or `test`.
7. Keep the host node-only: no public app/API/admin probes, no unrelated Prometheus exporter, no GitLab/Grafana/Loki/Sentry/Alertmanager, no backend/worker/payment/support runtime.

Suggested node naming:

```text
s1-eu-1
```

Evidence:

```text
Remnawave health = 200
node connected = true
node disabled = false
Prometheus healthy node count >= 1
node address is public/datacenter, not home/internal
```

Exit criteria:

```text
At least one real production VPN node is connected and healthy.
```

## PHASE 8 - Backend Provisioning Smoke

Goal: prove trial access without inviting real users yet.

Steps:

1. Keep public registration disabled.
2. Create disposable internal beta identity.
3. Temporarily enable trial provisioning only for smoke.
4. Activate trial through real CyberVPN backend path.
5. Confirm backend creates/updates Remnawave user.
6. Confirm QR/subscription URL/config delivery.
7. Import config into real client.
8. Connect through `prod-vpn-node-1`.
9. Confirm admin/support visibility.
10. Test credential regeneration.
11. Test expiry/grace disable behavior.
12. Re-disable trial provisioning unless immediately starting beta.

Exit criteria:

```text
trial -> VPN ready works end-to-end against rented production node.
Median/p95 timing sample is captured.
No secrets or config URLs are printed into public evidence.
```

## PHASE 9 - Telegram Bot And Mini App

Goal: move Telegram production webhook to rented app server.

Steps:

1. Confirm production bot token is stored only on `prod-app-1`.
2. Configure webhook:
   - `https://api.cyber-vpn.net/webhook/telegram`
3. Verify `getWebhookInfo`.
4. Confirm pending updates = `0`.
5. Confirm no last error.
6. Smoke bot commands.
7. Smoke Mini App open.
8. Keep paid methods disabled until payment evidence.
9. Keep trial UI aligned with backend provisioning flag.

Exit criteria:

```text
Telegram Bot and Mini App work from rented runtime and do not depend on home server.
```

## PHASE 10 - Payment Path

Goal: enable exactly one paid path if S1 includes paid users.

Recommended S1 order:

```text
1. trial-only first smoke cohort
2. one payment provider after trial provisioning is proven
3. more providers later
```

If paid beta is included:

1. Choose one provider first.
2. Store production credentials on `prod-app-1`.
3. Configure webhook on `api.cyber-vpn.net`.
4. Prove signature/authenticity.
5. Prove final statuses.
6. Prove duplicate webhook idempotency.
7. Prove payment -> provisioning.
8. Prove provider paid but Remnawave down recovery.
9. Prove orphan queue and support escalation.
10. Prove reconciliation job.

Keep disabled:

- Telegram Stars until Telegram flow evidence;
- PayRam/NOWPayments/YooKassa/Digiseller until real provider evidence;
- autoprolongation;
- refunds in UI unless provider/manual process is proven.

Exit criteria:

```text
One provider can complete payment -> VPN ready without duplicate provisioning or orphan state.
```

## PHASE 11 - Home Observability Integration

Goal: home observability sees rented runtime, but rented runtime does not depend on home observability.

On rented servers:

1. Run exporters:
   - node exporter;
   - cAdvisor optional;
   - postgres exporter;
   - redis exporter;
   - app metrics endpoints.
2. Expose metrics only over WireGuard/private allowlist.
3. Keep local Docker logs with rotation.
4. Configure promtail/log shipping to home Loki if desired.
5. Configure Sentry DSNs to home Sentry only if app does not block when Sentry is down.
6. Configure low timeout for Sentry/log shipping.
7. Keep local logs usable during home outage.

On home server:

1. Add Prometheus targets:
   - `prod-app-1`;
   - `prod-vpn-node-1`;
   - frontend blackbox;
   - admin blackbox;
   - API blackbox;
   - VPN node metrics.
2. Add dashboards/panels:
   - public endpoints;
   - API p95/p99;
   - auth;
   - trial provisioning;
   - payment;
   - paid-but-no-access;
   - Remnawave node;
   - worker queue;
   - PostgreSQL;
   - Valkey;
   - Telegram bot;
   - host CPU/RAM/disk/network.
3. Add Alertmanager routes to Telegram/email.

Accepted limitation:

```text
If home server is offline, dashboards and alerts may be unavailable.
Customer runtime must continue.
```

Exit criteria:

```text
Home Grafana shows real rented runtime metrics.
Home outage does not break production service.
```

## PHASE 12 - Backup, Restore And Rollback

Goal: production can be restored and rolled back without home server being online.

Minimum backup:

1. App PostgreSQL daily encrypted dump.
2. Remnawave DB daily encrypted dump.
3. Pre-deploy backup before migrations/releases.
4. Off-host copy to object/backup storage.
5. Home copy pulled when home is online.
6. 14-day retention.
7. Restore drill before user invite.

Rollback:

1. Keep previous immutable images on `prod-app-1`.
2. Keep rollback compose override locally.
3. Keep env rollback notes locally.
4. Verify `docker compose config`.
5. Verify previous images exist.
6. Run non-disruptive rollback dry-run.
7. Before larger cohort, perform staging/live maintenance rollback rehearsal.

Exit criteria:

```text
A production backup can be restored into disposable DB.
Rollback does not require home GitLab.
```

## PHASE 13 - Security Gate

Checks:

1. `git diff --check`.
2. Gitleaks/current-tree secret scan.
3. `npm audit --omit=dev --audit-level=high`.
4. Python dependency audit.
5. Frontend bundle/env scan.
6. Swagger/OpenAPI disabled publicly in production.
7. CORS/cookie settings correct.
8. Admin 2FA required.
9. Admin protected at edge.
10. Webhook paths not challenged.
11. Payment webhook signature verified.
12. No sensitive headers logged.
13. No tokens in Caddy/app logs.
14. SSH restricted.
15. DB/Valkey private.

Exit criteria:

```text
No high/critical blocker for the exact Stage 1 scope.
```

## PHASE 14 - Final Preflight

Run from outside:

```text
https://cyber-vpn.net/en-EN/status -> 200
https://cyber-vpn.net/ru-RU/privacy-policy -> 200
https://admin.cyber-vpn.net/ru-RU/login -> 200/protected expected
https://api.cyber-vpn.net/healthz -> 200
https://cyber-vpn.org/en-EN/status -> not a customer mirror
https://admin.cyber-vpn.org/ru-RU/login -> not an admin mirror
de-1.cyber-vpn.org:443 -> reachable
de-1.cyber-vpn.org:8443 -> reachable
```

Run product smoke:

1. owner admin login;
2. admin 2FA;
3. support profile visible;
4. plan catalog visible;
5. disposable internal user;
6. trial activation;
7. config delivery;
8. VPN connection;
9. credential regeneration;
10. expiry disable;
11. Telegram Bot command;
12. Mini App open;
13. payment provider if enabled;
14. backup pre-deploy;
15. rollback dry-run.

Exit criteria:

```text
Owner can sign controlled beta GO for first cohort.
```

## PHASE 15 - Controlled Beta Enablement

Recommended first cohort:

```text
3-5 trusted users maximum
trial-only first
invite-only registration
payments disabled until payment path is proven
```

Enablement order:

1. Keep `PAYMENTS_ENABLED=false`.
2. Enable `REGISTRATION_ENABLED=true` only with invite requirement.
3. Enable `STAGE1_TRIAL_PROVISIONING_ENABLED=true`.
4. Invite 1 internal test user.
5. Watch provisioning and VPN.
6. Invite 2-4 more trusted users.
7. Keep 24h stabilization window.
8. Only then consider one payment provider.

Immediate rollback/pause if:

- no healthy VPN node;
- provisioning success ratio below 95%;
- p95 `trial -> VPN ready` above 5 minutes for repeated events;
- any paid-but-no-access item older than 1 hour during paid test;
- payment webhook duplicate/idempotency issue;
- admin/support cannot recover user access;
- DB backup fails;
- logs show secrets.

---

# 10. Stage 1 Launch Guard Closure

The current stabilization evidence blocks external beta because:

- no rented production VPN node is proven;
- trial provisioning against production node is not proven;
- paid path is not proven;
- sensitive log redaction was previously noted;
- support mailbox DNS was unproven;
- app DB had no active plans/support profile;
- host observability at home had memory/swap pressure.

For client-facing publication on rented servers, close these in order:

| Blocker | Closure action |
|---|---|
| No production VPN node | Rent `prod-vpn-node-1`, connect to Remnawave, prove node health |
| Trial provisioning blocked | Enable only after node proof, run disposable user smoke |
| Paid path blocked | Keep payments disabled for first trial-only cohort or prove one provider |
| Sensitive logs | Ensure rented Caddy/app logs do not capture auth/payment/webhook secrets |
| Support mailbox | Either prove email DNS or explicitly use Telegram-only first cohort support |
| No active plans/support profile | Seed S1 plan/support data before enabling registration |
| Home observability outage | Accept as S1 risk; ensure runtime and backups do not depend on home |

Do not remove the `NO-GO` guard from evidence by wording only. It should be closed by a new evidence file proving the rented runtime.

---

# 11. Concrete Owner Checklist Before Renting

Fill this before paying:

| Question | Answer |
|---|---|
| Provider selected |  |
| Region selected |  |
| First beta users region |  |
| Monthly budget limit |  |
| `prod-app-1` plan | `VPS X16`, IPv4 `45.87.41.146`, IPv6 allocation `2a0d:2787:1b:12f5::/64` |
| `prod-vpn-node-1` plan | JustHost `Vega` recommended; `Capella` if budget allows |
| Backup storage selected |  |
| Use managed DB? | yes/no |
| First cohort trial-only? | recommended: yes |
| First payment provider | optional later |
| Support channel | Telegram / email / both |
| Is home observability outage risk accepted? | yes/no |
| Is colocated DB risk accepted for budget S1? | yes/no |
| Who can pause launch? | `@Sasha_Beep` |
| Who has emergency SSH? |  |

---

# 12. Files To Create During Deployment

In repo:

```text
docs/evidence/releases/stage1-rented-prod-00-budget-scope-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-01-server-rental-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-02-os-baseline-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-03-network-firewall-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-04-dns-tls-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-05-app-compose-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-06-db-migrations-bootstrap-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-07-remnawave-node-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-08-controlled-runtime-enablement-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-09-telegram-miniapp-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-10-payment-provider-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-11-observability-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-12-backup-restore-rollback-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-13-security-gate-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-14-final-preflight-YYYYMMDDTHHMMSSZ.md
docs/evidence/releases/stage1-rented-prod-15-owner-go-no-go-YYYYMMDDTHHMMSSZ.md
```

On rented server:

```text
/srv/cybervpn/runbooks/rollback-stage1.md
/srv/cybervpn/runbooks/pause-registration.md
/srv/cybervpn/runbooks/pause-payments.md
/srv/cybervpn/runbooks/pause-provisioning.md
/srv/cybervpn/runbooks/restore-db.md
/srv/cybervpn/evidence/
```

Do not store secrets in repo evidence.

---

# 13. Recommended Timeline

## Day 0 - Before Payment

1. Choose provider and region.
2. Choose budget mode vs production-correct mode.
3. Confirm trial-only first cohort.
4. Confirm support channel.
5. Confirm monthly spend cap.

## Day 1 - Infrastructure

1. Rent `prod-app-1`.
2. Rent `prod-vpn-node-1`.
3. Configure provider firewall.
4. Install OS baseline.
5. Configure DNS temporary health pages.
6. Configure WireGuard/private network.

## Day 2 - Runtime

1. Deploy app compose.
2. Run DB migrations.
3. Bootstrap first admin.
4. Deploy Remnawave control-plane.
5. Deploy VPN node.
6. Connect Remnawave node.

## Day 3 - Product Smoke

1. Public endpoint smoke.
2. Admin 2FA smoke.
3. Telegram webhook smoke.
4. Trial provisioning smoke.
5. Real client VPN connection.
6. Backup/restore drill.
7. Rollback dry-run.

## Day 4 - Controlled Beta

1. Owner go/no-go.
2. Enable invite-only registration.
3. Enable trial provisioning.
4. Invite 1 internal user.
5. Watch dashboards/logs.
6. Invite 2-4 trusted users if stable.

## Day 5-7 - Stabilization

1. Daily evidence.
2. Review errors.
3. Review provisioning.
4. Review VPN node.
5. Review support.
6. Review backups.
7. Decide whether to add payment path.

---

# 14. What Not To Do In Stage 1

Do not:

- run customer runtime from home;
- open public PostgreSQL;
- open public Valkey/Redis;
- expose Remnawave admin/API publicly;
- enable all payment providers at once;
- enable autoprolongation;
- enable referrals/promos/gifts;
- use VPN home node as production proof;
- use `latest` image tags;
- deploy from floating `main`;
- rely on home GitLab registry as the only runtime image source;
- invite users before production VPN node and trial provisioning proof;
- promise paid access before payment/provider/provisioning evidence;
- add Kubernetes/Talos just to launch S1;
- spend on mobile/desktop/partner infrastructure before S1 B2C is stable.

---

# 15. Minimum Go Criteria

CyberVPN can invite the first 3-5 controlled beta users only when:

| Gate | Required |
|---|---|
| Public site | `200` over HTTPS |
| API health | `200` over HTTPS |
| Admin | protected + 2FA |
| Registration | invite-only |
| Plans/support data | seeded |
| Production VPN node | connected and healthy |
| Trial provisioning | end-to-end proven |
| Config delivery | QR/subscription URL/config proven |
| Real client connection | proven |
| Telegram Bot/Mini App | webhook and basic flow proven |
| Payments | disabled or one provider proven |
| Paid-but-no-access queue | works if payments enabled |
| Backup | encrypted off-host backup exists |
| Restore | restore drill passed |
| Rollback | dry-run passed |
| Logs | no secrets/sensitive headers |
| Observability | home dashboards see runtime when home is online |
| Owner sign-off | recorded |

If payments are disabled, paid criteria can be deferred, but UI copy must not promise paid checkout.

---

# 16. Next Operational Step

Current rented deployment status, `2026-05-20`:

```text
STAGE1-RENT-01: completed for prod-app-1
STAGE1-RENT-02: completed for prod-app-1
STAGE1-RENT-03: completed for prod-app-1 with non-blocking www.cyber-vpn.org resolver propagation note
STAGE1-RENT-04: completed for prod-app-1 as disabled-state app/control-plane deploy
STAGE1-RENT-05: completed as rented node runtime proof with VLESS and XHTTP
STAGE1-RENT-06: completed; Remnawave node registration/provisioning evidence captured
STAGE1-RENT-07: completed; backend trial flow and real client connect proof captured
STAGE1-RENT-08: completed; trial-only controlled runtime enabled, public registration paused
STAGE1-RENT-09: infrastructure/API surface completed
STAGE1-RENT-09A: Telegram Mini App auth, route-guard, SDK, auth-gate/theme frontend hotfixes, backend Telegram token reload and temporary owner bootstrap allowlist completed
STAGE1-RENT-09G: Mini App customer-session and React error 31 hotfix deployed; internal redacted auth/bootstrap smoke passed; fresh owner/internal Telegram client retest pending
STAGE1-RENT-09H: Mini App RU localization hotfix deployed; reported mixed RU/EN phrases removed from customer-visible Home/Plans/Wallet/Profile surfaces; fresh owner/internal Telegram client retest pending
STAGE1-RENT-09I: emergency edge HTTP/3 isolation completed and superseded after owner confirmed page recovery
STAGE1-RENT-09J: HTTP/3/QUIC restored and required; TCP/UDP 443 published; UFW 443/udp allowed; QUIC sysctl tuning applied; Mini App route probes return 200; owner retest passed
STAGE1-RENT-10: payment path preflight completed; payments remain disabled; CryptoBot provider credential preflight returned HTTP 403, so paid beta is still blocked
STAGE1-RENT-10B: Crypto Pay key/webhook closure completed; provider auth now succeeds, USD fiat invoice smoke passes, webhook_logs schema blocker fixed, valid signed synthetic webhook returns 200; paid checkout remains disabled until real paid checkout -> provisioning evidence is captured
STAGE1-RENT-10C: Telegram Stars controlled enablement completed; Stars gate is open for Telegram-only flow, generic/CryptoBot checkout remains blocked, Telegram createInvoiceLink XTR smoke returns ok=true; real Stars purchase/provisioning proof remains blocked until production catalog and approved XTR plan prices exist
STAGE1-RENT-11: observability/stabilization loop completed with PASS_WITH_GAPS; VPN node TCP probes are live and green, Alertmanager Telegram/email delivery is proven, Sentry/Loki/Grafana/Prometheus are healthy, but home-to-prod-app public HTTP/TLS blackbox probes time out
STAGE1-RENT-11A: completed then superseded; external probe relay proved public endpoints from a rented network, but it was removed because prod-vpn-node-1 must stay node-only
STAGE1-RENT-11B: completed with NODE_ONLY_RESTORED_DIRECT_PROD_APP_HTTP_TLS_BLOCKED; VPN node relay removed, direct home-to-prod-app TCP handshake/ICMP works, TCP payload does not reach prod-app-1, direct-path closure remains open
STAGE1-RENT-11C: completed as upstream/provider-path blocker evidence; RouterOS SSH access works, MikroTik routes prod-app-1 directly through WAN, FastTrack/FastPath are inactive for the test, WAN sniffer shows post-handshake payload leaving MikroTik, but prod-app-1 tcpdump sees only SYN/SYN-ACK/ACK and no HTTP GET/TLS ClientHello payload on 80/443
STAGE1-RENT-11D: completed with PASS_CLOUDFLARE_USER_PATH_PROBES_GREEN; S1 .net public hostnames are Cloudflare-proxied, home Prometheus blackbox-stage1-public-web probes are all green with HTTP 200, direct home-origin failure remains a known upstream/provider issue
STAGE1-RENT-12: completed with PASS_WITH_TRIAL_ONLY_EXPANSION_APPROVED; production S1 plan catalog and support/storefront/merchant records are seeded, public plan API returns 16 entries per active channel, public probes and VPN-node probes remain green, paid beta remains blocked
STAGE1-RENT-13: completed with PASS_WITH_HOTFIXED_TRIAL_CONFIG_DELIVERY; owner/internal Telegram trial is active, Remnawave link and subscription URL are present, protected config delivery returns VLESS config, and ephemeral Xray client connect through the production VPN node succeeds
STAGE1-RENT-14: preflight completed with PASS_PREFLIGHT_PENDING_OWNER_DEVICE_CONFIRMATION; production runtime and observability are green, owner trial/config server-side proof remains valid, and cohort-2 is blocked until owner validates the real device flow
```

Evidence:

```text
docs/evidence/releases/stage1-rented-prod-01-server-rental-20260519T160411Z.md
docs/evidence/releases/stage1-rented-prod-02-os-baseline-20260519T164752Z.md
docs/evidence/releases/stage1-rented-prod-03-dns-tls-temporary-health-20260519T170939Z.md
docs/evidence/releases/stage1-rented-prod-04-app-compose-disabled-state-20260519T174532Z.md
docs/evidence/releases/stage1-rented-prod-05-production-vpn-node-proof-20260519T183410Z.md
docs/evidence/releases/stage1-rented-prod-06-remnawave-node-registration-provisioning-20260519T191146Z.md
docs/evidence/releases/stage1-rented-prod-07-backend-trial-client-connect-20260520T065023Z.md
docs/evidence/releases/stage1-rented-prod-08-controlled-runtime-enablement-20260520T070701Z.md
docs/evidence/releases/stage1-rented-prod-09-telegram-miniapp-live-smoke-20260520T072553Z.md
docs/evidence/releases/stage1-rented-prod-09a-owner-telegram-miniapp-auth-hotfix-20260520T074800Z.md
docs/evidence/releases/stage1-rented-prod-09b-miniapp-route-guard-hotfix-20260520T080000Z.md
docs/evidence/releases/stage1-rented-prod-09c-telegram-sdk-hotfix-20260520T081500Z.md
docs/evidence/releases/stage1-rented-prod-09d-miniapp-auth-gate-theme-20260520T083000Z.md
docs/evidence/releases/stage1-rented-prod-09e-backend-telegram-token-reload-20260520T085339Z.md
docs/evidence/releases/stage1-rented-prod-09f-telegram-miniapp-owner-bootstrap-20260520T090407Z.md
docs/evidence/releases/stage1-rented-prod-09g-miniapp-customer-session-react31-20260520T121643Z.md
docs/evidence/releases/stage1-rented-prod-09h-miniapp-ru-l10n-20260520T132348Z.md
docs/evidence/releases/stage1-rented-prod-09i-edge-http3-reset-fix-20260520T134851Z.md
docs/evidence/releases/stage1-rented-prod-09j-edge-http3-quic-restore-20260520T135210Z.md
docs/evidence/releases/stage1-rented-prod-10-payment-path-preflight-20260520T140517Z.md
docs/evidence/releases/stage1-rented-prod-10b-cryptopay-key-webhook-closure-20260520T144900Z.md
docs/evidence/releases/stage1-rented-prod-10c-telegram-stars-enable-20260520T150500Z.md
docs/evidence/releases/stage1-rented-prod-11-observability-stabilization-20260520T162926Z.md
docs/evidence/releases/stage1-rented-prod-11a-external-probe-relay-20260520T164632Z.md
docs/evidence/releases/stage1-rented-prod-11b-node-only-and-direct-home-prod-app-20260520T170051Z.md
docs/evidence/releases/stage1-rented-prod-11c-direct-home-prod-app-network-path-20260520T172432Z.md
docs/evidence/releases/stage1-rented-prod-11d-cloudflare-user-path-probes-20260520T175619Z.md
docs/evidence/releases/stage1-rented-prod-12-catalog-support-beta-gate-20260520T180458Z.md
docs/evidence/releases/stage1-rented-prod-13-first-controlled-cohort-trial-watch-20260520T184156Z.md
docs/evidence/releases/stage1-home-observability-swap-tuning-20260520T191045Z.md
docs/evidence/releases/stage1-rented-prod-14-owner-device-cohort2-preflight-20260520T191226Z.md
docs/evidence/releases/stage1-rented-prod-14a-owner-device-confirmation-cohort2-list-20260521T061114Z.md
docs/evidence/releases/stage1-rented-prod-14b-owner-real-device-retest-cohort2-invite-20260521T062040Z.md
docs/evidence/releases/stage1-stabilization-20260520.md
```

Recommended next step:

```text
STAGE1-RENT-15: Cohort-2 Trial Invite Execution And Support Watch
```

STAGE1-RENT-10 result:

```text
1. Generic payment runtime remains disabled: PAYMENTS_ENABLED=false and CRYPTOBOT_ENABLED=false.
2. Initial Crypto Pay mainnet auth preflight returned HTTP 403 and was blocked.
3. Owner recorded the real Crypto Pay app key.
4. Retest returned provider auth success: getMe status=200, ok=true.
5. USD invoice creation now uses Crypto Pay fiat contract: currency_type=fiat + fiat=USD.
6. Invoice URL preference follows current Crypto Pay invoice fields: mini_app_invoice_url, bot_invoice_url, web_app_invoice_url, pay_url.
7. webhook_logs production schema blocker was fixed through migration 20260520_stage1_webhook_logs.
8. Valid signed synthetic CryptoBot webhook returns HTTP 200 and stores a valid webhook log.
9. No paid checkout was enabled.
10. Stage 1 can continue as trial-only controlled beta, or move to a tightly controlled internal real payment proof.
11. Paid beta remains blocked until real checkout payment, provider callback, duplicate/idempotency, invoice lifecycle and payment-to-provisioning evidence exist.
```

STAGE1-RENT-10C result:

```text
1. Telegram Stars is enabled only for Telegram Bot/Mini App payment surfaces.
2. Generic/CryptoBot checkout remains blocked: PAYMENTS_ENABLED=false and CRYPTOBOT_ENABLED=false.
3. Backend gate check: generic_gate=blocked:503, stars_gate=open.
4. Telegram Bot runtime: TELEGRAM_STARS_ENABLED=true.
5. Telegram Bot API createInvoiceLink smoke with XTR returned ok=true; invoice URL was not stored.
6. Superseded by `STAGE1-RENT-12`: production subscription plan catalog is now seeded; real Stars purchase/provisioning proof still requires approved XTR purchase amount policy, real charge ID, `/paysupport`, refund/reconciliation and provisioning evidence.
```

STAGE1-RENT-11 result:

```text
1. prod-app-1 runtime containers are healthy with restart_count=0.
2. HTTP/3/QUIC remains enabled: Caddy publishes 443/tcp and 443/udp, and UFW allows 443/udp.
3. prod-vpn-node-1 runtime is healthy; de-1.cyber-vpn.org TCP probes for 443 and 8443 are live and green from home Prometheus.
4. Home Prometheus, Grafana, Loki, Alertmanager and Sentry are running.
5. Alertmanager accepted a synthetic alert and Telegram/email notification counters increased with zero failed notifications.
6. S1 observability source assets were updated with blackbox tcp_connect, VPN-node TCP targets and alerts.
7. Public web/API/admin external operator probes return 200.
8. Home Prometheus public-web blackbox probes to prod-app-1 still return probe_success=0 because the home server times out during HTTP/TLS exchange with 45.87.41.146.
9. False public-web P0 alerting for the current home-blocked live job was suppressed; this must not be mistaken for full public-web monitoring coverage.
10. Known issue S1-RENT11-001 must be closed by RENT-11A before widening the beta cohort.
```

STAGE1-RENT-11A superseded result:

```text
1. External relay proof existed temporarily, but it is no longer an approved Stage 1 runtime pattern.
2. The relay was removed by STAGE1-RENT-11B because prod-vpn-node-1 must stay node-only.
3. Do not use the VPN node as a public app/API/admin probe host.
```

STAGE1-RENT-11B result:

```text
1. prod-vpn-node-1 is restored to node-only policy.
2. cybervpn-stage1-external-probe-exporter.service, script, user and UFW port 19115 rule were removed.
3. Source-controlled relay job, relay alerts and relay service files were removed.
4. Grafana Stage 1 dashboard now uses direct stage1-public-web blackbox panels instead of relay metrics.
5. Direct home-to-prod-app DNS resolves to 45.87.41.146.
6. Direct ICMP and TCP handshake to prod-app-1 work.
7. Direct HTTP/TLS payload after handshake does not reach prod-app-1 from home; curl times out with 0 bytes.
8. Temporary payload listener on prod-app-1 received no payload from home even though TCP connect opened.
9. Home NIC offload test did not fix the path and was reverted.
10. Direct-path closure remains open; fix provider/ISP route or approve a non-node ops path.
```

STAGE1-RENT-11C result:

```text
1. RouterOS SSH access to MikroTik 10.10.10.1 works; no passwords are recorded in docs/evidence.
2. MikroTik route check sends 45.87.41.146 directly through sfp-sfpplus1 via 95.82.233.1.
3. FastTrack rule exists but is disabled; IPv4 FastPath/FastTrack counters are inactive for the test.
4. NAT uses standard WAN masquerade for home -> prod-app-1 traffic; no persistent MikroTik firewall/NAT/routing changes were made.
5. home -> example.com works and ICMP to 45.87.41.146 works, including 1200-byte DF payload.
6. home -> cyber-vpn.net/api.cyber-vpn.net still times out on HTTP/TLS.
7. prod-app-1 -> cyber-vpn.net edge health is 200 locally, and prod-vpn-node-1 -> cyber-vpn.net edge health is 200 from a non-home rented network.
8. home -> prod-app-1:22 receives SSH banner, while 80/443 connect but HTTP/TLS payload does not complete.
9. prod-app packet capture sees SYN/SYN-ACK/ACK for home-origin HTTP/TLS, but not the expected HTTP GET/ClientHello payload.
10. MikroTik WAN sniffer sees the matching TLS ClientHello/post-handshake payload transmitted out sfp-sfpplus1 from 95.82.233.131 to 45.87.41.146:443.
11. Current fault domain is upstream/provider path after MikroTik TX: home ISP path or JustHost/provider anti-DDoS/TCP validation for the home public IP on 80/443.
12. Direct home -> prod-app-1 monitoring is not closed; close with provider ticket/whitelist, Cloudflare-proxied user-path probes, separate external probe location, or explicit owner risk acceptance.
```

STAGE1-RENT-11D result:

```text
1. Cloudflare proxy was enabled for cyber-vpn.net, www.cyber-vpn.net, api.cyber-vpn.net, admin.cyber-vpn.net and status.cyber-vpn.net.
2. All proxied records keep origin 45.87.41.146 and now return Cloudflare edge IPs to clients.
3. No .org VPN-node DNS records were changed.
4. Home curl probes now reach Cloudflare edge and return user-facing responses for web, API, admin and status.
5. Cloudflare responses advertise HTTP/3 to clients with alt-svc h3=:443; origin Caddy HTTP/3/QUIC was not disabled.
6. Home Prometheus blackbox-stage1-public-web reports probe_success=1 and HTTP 200 for all configured public web/API/admin/status/Mini App targets.
7. No active Stage1PublicEndpointProbeFailed alert was returned after the Cloudflare user-path probes went green.
8. Public endpoint user-path monitoring authority is closed for Stage 1.
9. Direct home -> origin payload loss remains tracked as an upstream/provider known issue from STAGE1-RENT-11C.
10. prod-vpn-node-1 remains node-only and must not be used as an app/API/admin monitoring relay.
```

STAGE1-RENT-12 result:

```text
1. Production pricing seed created 28 subscription plan rows and 2 add-on rows.
2. Add-ons remain disabled by runtime flag: STAGE1_ADDONS_ENABLED=false.
3. Public active catalog contains 16 entries: Basic, Plus, Pro and Max for 30, 90, 180 and 365 days.
4. Public plan API returns count=16 for channel=web, channel=miniapp and channel=telegram_bot.
5. Minimum support/storefront/merchant records are seeded and active: support profile, communication profile, invoice profile, merchant profile, billing descriptor and cyber-vpn.net storefront.
6. Runtime safety gates remain closed for paid/growth expansion: PAYMENTS_ENABLED=false, CRYPTOBOT_ENABLED=false, STAGE1_PAID_PROVISIONING_ENABLED=false, REFERRAL_ENABLED=false, PROMO_CODES_ENABLED=false and GIFT_CODES_ENABLED=false.
7. Trial provisioning remains open: STAGE1_TRIAL_PROVISIONING_ENABLED=true.
8. Telegram Stars remains enabled only as a Telegram payment surface gate, but real Stars purchase/provisioning evidence is still missing.
9. Home Prometheus reports zero firing Stage 1 alerts, all Cloudflare user-path public probes green and both VPN-node TCP probes green.
10. Decision: GO for owner/internal and small manually controlled trial cohort; NO-GO for paid beta and global public registration.
```

STAGE1-RENT-13 result:

```text
1. First owner/internal Telegram-linked controlled beta trial proof is complete.
2. Mini App and Telegram Bot trial activation now pass the Stage 1 Remnawave provisioning gateway.
3. Telegram Bot and Mini App config delivery now prefer the locally stored Remnawave UUID before Telegram-ID lookup and can fall back to stored subscription URL.
4. Final deployed backend tag is stage1-rent13b-config-delivery-20260520t183430.
5. Targeted tests pass: 28 passed in 0.35s.
6. Production DB redacted proof: 1 mobile user, 1 active trial, 1 Remnawave-linked user and 1 stored subscription URL.
7. Protected Telegram Bot config returns HTTP 200 with VLESS config present.
8. Ephemeral Xray client proof from prod-app-1 succeeds; proxied egress matches the production VPN node IPv4.
9. Temporary Xray client and .secret files were removed after proof.
10. Public web/API/admin/Mini App probes remain green and VPN-node TCP probes remain green.
11. Stage 1-specific firing alerts are 0; home ops has two non-customer-runtime swap warning alerts to track.
12. Paid beta and global public registration remain blocked.
```

STAGE1-RENT-09/09A hard safety rules:

```text
payments remain disabled unless a provider path is proven;
growth mechanisms remain disabled;
no raw config URLs, VLESS links, invite tokens, JWTs or provider secrets in evidence;
registration is not opened globally unless every public B2C registration path is invite-controlled;
trial provisioning can be paused by setting STAGE1_TRIAL_PROVISIONING_ENABLED=false and recreating backend/worker/bot containers;
Telegram bot can be returned to safe no-network startup by setting TELEGRAM_BOT_SKIP_NETWORK_CALLS=true and recreating cybervpn-telegram-bot.
HTTP/3/QUIC must remain enabled on the rented edge. Do not remove h3 from Caddy protocols; fix UDP 443/firewall/sysctl/client-state issues instead.
```

Remaining ordered steps after RENT-13:

```text
STAGE1-RENT-15: Cohort-2 Trial Invite Execution And Support Watch
```

STAGE1-RENT-13 closed the first real controlled-cohort operating step:

```text
1. Select a very small owner-approved beta cohort.
2. Keep public registration paused; onboard users manually or through an explicitly controlled path.
3. Run the user flow: Telegram/web entry -> auth/linking -> trial activation -> Remnawave provisioning -> config delivery -> real client connect.
4. Watch support, backend, worker, Remnawave, VPN node, Telegram Bot/Mini App, public probes, Sentry and Loki during the cohort.
5. Record every failed activation, no-config state, support contact and remediation.
6. Do not enable paid checkout, generic payments, referrals, promo/gift codes or add-ons during this step.
```

STAGE1-RENT-14 should be the second controlled-cohort operating step:

```text
1. Owner validates on a real device that Mini App/Profile/Home shows active trial and usable config.
2. Add 1-3 manually selected beta users only after owner device validation.
3. Keep public registration paused and keep payments disabled.
4. Watch Telegram Bot, Mini App, backend, worker, Remnawave, VPN node, Sentry/Loki and Prometheus during the cohort.
5. Record every no-config, failed-connect, support contact, trial activation error and remediation.
6. If support load or provisioning errors appear, pause trial provisioning before adding more users.
```

STAGE1-RENT-14A server-side gate result:

```text
1. Found and fixed Mini App bootstrap usage lookup fallback: linked owner users now prefer mobile_users.remnawave_uuid over Telegram-ID Remnawave lookup.
2. Deployed backend image cybervpn/cybervpn-backend:stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z.
3. Production Mini App auth/bootstrap/config server-side smoke returned 200/200/200 and config_source=remnawave_generated.
4. Public endpoint and VPN-node probes remain green from home observability.
5. Cohort-2 invitations remain blocked until owner real-device validation and 1-3 user list approval.
```

STAGE1-RENT-14B owner-device gate result:

```text
1. Owner confirmed config delivery through Telegram Bot/Mini App.
2. Owner imported the config into a VPN client.
3. Owner connected successfully through the production VPN node.
4. whoer.net showed public exit IP 77.90.13.29 in Germany.
5. Runtime containers remained healthy and public/VPN probes remained green.
6. Cohort-2 invitations remain blocked only until the 1-3 user list is approved.
```

STAGE1-RENT-14C Mini App stale-session hotfix result:

```text
1. Owner reported that Mini App later showed no active subscription and could not activate trial again.
2. Backend state proved this was not lost subscription state: the owner Telegram-linked user remained active, trial remained active, Remnawave UUID was present and subscription URL was present.
3. Root cause: stale/missing Mini App cookie produced protected API 401 responses, while the frontend rendered a no-subscription fallback instead of restoring Telegram auth.
4. Frontend now dispatches a Mini App auth-restore event on unrecovered Mini App 401, re-authenticates through Telegram initData, invalidates miniapp-* queries and shows a session-restore state during recovery.
5. Auth layout now wraps TelegramMiniAppAuthProvider with QueryProvider so TanStack Query cache invalidation is available everywhere the provider is mounted.
6. Deployed image: cybervpn/cybervpn-frontend:stage1-rent14c-miniapp-session-restore-20260521t063728z.
7. Only cybervpn-frontend was recreated; backend, bot, worker, scheduler, Remnawave and VPN node were not changed.
8. Targeted tests passed: 4 files, 104 tests.
9. Targeted eslint passed.
10. Production frontend build passed and generated 2801 static pages.
11. Public Mini App route returned HTTP 200 after deploy.
12. Cohort-2 invitations remain blocked until owner confirms real-device Mini App retest after this hotfix.
```

STAGE1-RENT-15 cohort-2 invite execution result:

```text
1. Issued 3 owner-held controlled beta invite codes to the owner Telegram-linked mobile account.
2. Codes grant 7 free days each and expire on 2026-05-24 11:54:13 UTC.
3. Raw invite codes are not stored in docs/evidence.
4. Public referral, promo, gift, partner and payout mechanisms remain disabled.
5. Rented production containers remained healthy after issue.
6. Public web/Mini App/status probes returned HTTP 200.
7. VPN node TCP probes remained green for de-1.cyber-vpn.org:443 and :8443.
8. Home Prometheus firing alerts were 0.
9. Cohort expansion is limited to the issued 3-code pack.
10. Next evidence required: STAGE1-RENT-15A first invited user trial/invite flow and support watch.
```
