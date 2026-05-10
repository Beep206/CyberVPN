# CyberVPN H Public Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare the CyberVPN project infrastructure on the server `10.10.10.34` for public internet access through Caddy running directly on `10.10.10.34`, with Docker, GitLab, observability, Sentry, backups, security hardening, and hardware monitoring.

**Architecture:** `10.10.10.34` is both the public HTTP/HTTPS edge and the main app/ops host for CyberVPN. Caddy terminates HTTPS on `10.10.10.34` and proxies to local service ports on `127.0.0.1` for GitLab, GitLab Runner, Sentry, Grafana/Prometheus/Loki/Alertmanager, backup jobs, evidence archive, and security tooling. Cloudflare manages public DNS for `*.h.cyber-vpn.net`; router NAT should forward only public HTTP/HTTPS traffic to `10.10.10.34` unless a later task explicitly approves more exposure.

**Tech Stack:** Ubuntu 24.04 LTS, Docker Engine, Docker Compose plugin, Caddy systemd service on `10.10.10.34`, Cloudflare DNS, UFW, Fail2ban, GitLab, GitLab Runner, Grafana, Prometheus, Loki, Alertmanager, Sentry self-hosted, restic, rclone, smartmontools, nvme-cli, rasdaemon, sysstat.

---

## Current Verified State

### Main app/ops server

- Host: `10.10.10.34`
- Current hostname: `cybervpn-h-ops`
- User: `beep`
- SSH: key-only login works; password login has been disabled.
- OS: Ubuntu `24.04.4 LTS`
- Kernel: `6.8.0-111-generic`
- Hardware: bare metal `JGINYUE X99-D8 Server`
- CPU: `2 x Intel Xeon E5-2699 v3`, `36` physical cores, `72` threads.
- RAM: `64 GB` installed, Linux sees about `62 GiB`.
- NUMA: balanced, about `32 GB` on each node.
- NVMe: `/dev/nvme0n1`, about `953.9G`, ext4 root filesystem mounted at `/`.
- HDD: `/dev/sda1`, Seagate `ST2000VX017-3CV1`, ext4 label `srv-storage`, mounted at `/srv/storage`.
- HDD SMART: enabled, health `PASSED`, short self-test completed without error.
- Swap: current `/swap.img`, `32 GB`.
- Docker: installed and active; Docker data root is `/srv/docker`.
- UFW: active; default deny incoming, allow outgoing, deny routed.
- Caddy: installed as a systemd service on `10.10.10.34`, listening on public `80/tcp` and `443/tcp`.

### Storage policy

- NVMe `/`: hot data and active service volumes.
- HDD `/srv/storage`: backups, archives, GitLab artifacts/packages/LFS/uploads/registry/cache, Sentry attachments, cold observability data, evidence.
- Do not place PostgreSQL, Redis, ClickHouse, Kafka, or active Git repositories on the 5400 RPM HDD.

---

## Public Exposure Decision

The deployment is public internet facing. This changes the security baseline:

- No direct public exposure of service containers on `10.10.10.34`.
- Public router/NAT should forward TCP `80` and `443` to `10.10.10.34`.
- `10.10.10.34` should be the only public HTTP/HTTPS entry point.
- Application containers on `10.10.10.34` should bind service ports to `127.0.0.1` whenever possible, and Caddy should be the only public web listener.
- Public SSH should remain closed unless explicitly approved later.
- Git over HTTPS should be the default. Public Git over SSH is deferred.
- Every public web UI must have application-level 2FA where available.
- Cloudflare DNS and Cloudflare security controls become part of the launch checklist.

---

## Target Public Domains

Use `h` instead of `home`.

```text
gitlab.h.cyber-vpn.net
registry.h.cyber-vpn.net
grafana.h.cyber-vpn.net
sentry.h.cyber-vpn.net
prometheus.h.cyber-vpn.net
loki.h.cyber-vpn.net
alerts.h.cyber-vpn.net
uptime.h.cyber-vpn.net
```

Optional later:

```text
runner.h.cyber-vpn.net
evidence.h.cyber-vpn.net
partner-lab.h.cyber-vpn.net
```

---

## Cloudflare Actions Required From Owner

These actions require Cloudflare dashboard access.

1. Determine the public WAN IP of the home router.
2. In Cloudflare DNS for `cyber-vpn.net`, create records pointing to the home WAN IP:

```text
A gitlab.h       <HOME_WAN_IP>
A registry.h    <HOME_WAN_IP>
A grafana.h     <HOME_WAN_IP>
A sentry.h      <HOME_WAN_IP>
A prometheus.h  <HOME_WAN_IP>
A loki.h        <HOME_WAN_IP>
A alerts.h      <HOME_WAN_IP>
A uptime.h      <HOME_WAN_IP>
```

3. For first bring-up, use DNS-only mode for `gitlab.h` and `registry.h`.
   Cloudflare proxy can interfere with GitLab registry pushes, large uploads, WebSockets, and request limits depending on plan and configuration.
4. Grafana, Sentry, Alertmanager, and Uptime Kuma can be tested behind Cloudflare proxy later, but only after login, 2FA, and access controls are confirmed.
5. Enable Cloudflare security controls before public launch:

```text
WAF managed rules
Bot fight or equivalent bot controls
Rate limiting for login paths where available
Always Use HTTPS
TLS mode: Full strict, once valid certificates are in place
```

6. Optional later: replace public DNS-only exposure with Cloudflare Tunnel or Cloudflare Access for admin UIs.

Router/NAT required:

```text
TCP 80  -> 10.10.10.34:80
TCP 443 -> 10.10.10.34:443
```

Do not forward SSH, GitLab internal ports, PostgreSQL, Redis, Docker daemon, Prometheus, Loki, or Sentry component ports.

---

## Target Directory Layout

### Main orchestration root on NVMe

```text
/srv/cybervpn-h
/srv/cybervpn-h/compose
/srv/cybervpn-h/compose/gitlab
/srv/cybervpn-h/compose/gitlab-runner
/srv/cybervpn-h/compose/observability
/srv/cybervpn-h/compose/sentry
/srv/cybervpn-h/compose/reverse-proxy-upstreams
/srv/cybervpn-h/compose/backups
/srv/cybervpn-h/compose/security
/srv/cybervpn-h/compose/partner-lab
/srv/cybervpn-h/secrets
/srv/cybervpn-h/runbooks
/srv/cybervpn-h/evidence
/srv/cybervpn-h/scripts
/srv/cybervpn-h/configs
```

### Docker and hot data on NVMe

```text
/srv/docker

/srv/gitlab/config
/srv/gitlab/logs
/srv/gitlab/data

/srv/observability/grafana
/srv/observability/prometheus
/srv/observability/alertmanager
/srv/observability/loki-index
/srv/observability/loki-cache
/srv/observability/tempo

/srv/sentry/postgres
/srv/sentry/redis
/srv/sentry/clickhouse
/srv/sentry/kafka
/srv/sentry/zookeeper
/srv/sentry/symbolicator
```

### Cold and large data on HDD

```text
/srv/storage/backups/gitlab
/srv/storage/backups/sentry
/srv/storage/backups/observability
/srv/storage/backups/configs
/srv/storage/backups/postgres-dumps

/srv/storage/gitlab-artifacts
/srv/storage/gitlab-packages
/srv/storage/gitlab-lfs
/srv/storage/gitlab-uploads
/srv/storage/gitlab-registry
/srv/storage/gitlab-cache

/srv/storage/sentry-attachments
/srv/storage/observability-cold/loki-chunks
/srv/storage/observability-cold/prometheus-snapshots
/srv/storage/archives/logs
/srv/storage/evidence
```

Permissions:

```text
/srv/cybervpn-h/secrets: 0700
/srv/cybervpn-h/evidence: 0750
/srv/storage/evidence: 0750
secret files: 0600
```

Do not aggressively `chown` application data directories before containers are selected; GitLab, Sentry, Prometheus, and Loki use specific internal UIDs.

---

## Resource Budget

Initial resource limits:

| Block | RAM | CPU |
|---|---:|---:|
| GitLab | 12-16 GB | 6-10 threads |
| GitLab Runner | 8-16 GB | 8-16 threads, concurrency 1-2 |
| Sentry | 16-24 GB | 8-12 threads |
| Grafana/Prometheus/Loki/Alertmanager | 8-12 GB | 4-8 threads |
| OS/cache/buffer | 6-8 GB | reserve |
| Partner/reporting sandbox | on demand | on demand |

Hard rule: no major service should run with unlimited memory once it is public.

---

## Implementation Phases

### Phase 0: Safety And Baseline

**Goal:** Make all current state recoverable before changing host-level services.

**Files and paths:**

- Create: `/srv/cybervpn-h/evidence/baseline`
- Create: `/srv/storage/evidence/baseline`
- Create: `/srv/cybervpn-h/runbooks/host-access.md`
- Create: `/srv/cybervpn-h/runbooks/rollback-host-hardening.md`

**Steps:**

1. Confirm SSH key-only login to `10.10.10.34`.
2. Save baseline command outputs:

```bash
hostnamectl
cat /etc/os-release
uname -a
lscpu
free -h
numactl -H
lsblk -e7 -o NAME,PATH,MODEL,SERIAL,TYPE,SIZE,ROTA,FSTYPE,LABEL,UUID,MOUNTPOINTS
findmnt -D
df -hT
swapon --show
ip -br addr
ip route
ss -tulpen
systemctl --failed --no-pager
```

3. Back up critical configs:

```text
/etc/fstab
/etc/ssh
/etc/netplan
/etc/sysctl.conf
/etc/sysctl.d
/etc/ufw
/etc/fail2ban
```

4. Store baseline copies under:

```text
/srv/storage/evidence/baseline/YYYY-MM-DD/
```

5. Verify `/srv/storage` mount:

```bash
findmnt --verify --verbose
findmnt /srv/storage
```

**Acceptance criteria:**

- Baseline evidence exists on HDD.
- SSH key-only access still works.
- No failed systemd units.
- `/srv/storage` is mounted with `noatime`.

---

### Phase 1: Host Identity

**Goal:** Rename the main server to a project-specific hostname.

**Target hostname:**

```text
cybervpn-h-ops
```

**Files:**

- Modify: `/etc/hostname`
- Modify: `/etc/hosts`

**Steps:**

1. Set hostname:

```bash
sudo hostnamectl set-hostname cybervpn-h-ops
```

2. Update `/etc/hosts` so `127.0.1.1` maps to `cybervpn-h-ops`.
3. Reconnect via SSH.
4. Verify:

```bash
hostnamectl
hostname
```

**Acceptance criteria:**

- Static hostname is `cybervpn-h-ops`.
- SSH reconnect works.

---

### Phase 2: Directory Layout

**Goal:** Create the full NVMe/HDD directory structure before installing services.

**Files and paths:**

- Create all target directories listed in "Target Directory Layout".

**Steps:**

1. Create NVMe directories.
2. Create HDD directories.
3. Set permissions:

```bash
sudo chmod 700 /srv/cybervpn-h/secrets
sudo chmod 750 /srv/cybervpn-h/evidence /srv/storage/evidence
sudo chmod 1777 /srv/storage/tmp
```

4. Add README markers explaining hot vs cold storage:

```text
/srv/cybervpn-h/README.md
/srv/storage/README-cybervpn-h.md
```

**Acceptance criteria:**

- All directories exist.
- Secrets directory is not world-readable.
- HDD and NVMe roles are documented.

---

### Phase 3: Base Packages

**Goal:** Install operational packages used by the rest of the plan.

**Packages:**

```text
git
git-lfs
ufw
fail2ban
openssh-server
smartmontools
nvme-cli
lm-sensors
sysstat
htop
iotop
iftop
restic
rclone
jq
yq
make
curl
wget
ca-certificates
gnupg
lsb-release
unattended-upgrades
rasdaemon
acl
```

**Docker packages are installed in Phase 6 from the official Docker apt repository.**

**Steps:**

1. Run apt update.
2. Install packages.
3. Enable services:

```bash
sudo systemctl enable --now smartmontools.service
sudo systemctl enable --now rasdaemon.service
sudo systemctl enable --now sysstat.service
```

4. Keep `systemd-timesyncd` unless a later decision switches to `chrony`.

**Acceptance criteria:**

- `git lfs version` works.
- `smartctl -H /dev/sda` works.
- `nvme smart-log /dev/nvme0` works.
- `systemctl is-active rasdaemon` returns active.
- `sar -d 1 1` works.

---

### Phase 4: Swap And Kernel Tunables

**Goal:** Increase swap safety margin and tune basic host limits.

**Files:**

- Modify: `/swap.img`
- Modify: `/etc/fstab` only if needed.
- Create: `/etc/sysctl.d/99-cybervpn-h.conf`

**Target swap:**

```text
32 GB on NVMe at /swap.img
```

**Target sysctl:**

```text
vm.swappiness = 10
vm.max_map_count = 1048576
fs.inotify.max_user_watches = 1048576
fs.inotify.max_user_instances = 1024
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
```

**Steps:**

1. Disable current swap.
2. Recreate `/swap.img` as `32G`.
3. Set permissions `0600`.
4. Run `mkswap`.
5. Enable swap.
6. Apply sysctl.
7. Verify:

```bash
free -h
swapon --show
sysctl vm.swappiness vm.max_map_count fs.inotify.max_user_watches
```

**Acceptance criteria:**

- Swap shows `32G`.
- `vm.swappiness` is `10`.
- No `fstab` parse errors.

---

### Phase 5: CPU Performance Governor

**Goal:** Use predictable CPU performance for CI and service workloads.

**Files:**

- Create: `/etc/systemd/system/cpu-performance-governor.service`

**Steps:**

1. Set all available CPU governors to `performance`.
2. Create persistent systemd unit.
3. Enable the unit.
4. Verify:

```bash
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c
sensors
```

**Acceptance criteria:**

- All CPU governors report `performance`.
- CPU temperatures remain reasonable after light load.

**Risk note:** This increases power draw and heat. BIOS performance profile is a separate manual change.

---

### Phase 6: Docker Engine And Compose

**Goal:** Install Docker correctly before any service stack is deployed.

**Files:**

- Create: `/etc/docker/daemon.json`
- Use: `/srv/docker` as Docker data root.

**Target Docker daemon config:**

```json
{
  "data-root": "/srv/docker",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "live-restore": true,
  "userland-proxy": false,
  "default-address-pools": [
    {
      "base": "172.30.0.0/16",
      "size": 24
    }
  ]
}
```

**Steps:**

1. Add official Docker apt repository.
2. Install:

```text
docker-ce
docker-ce-cli
containerd.io
docker-buildx-plugin
docker-compose-plugin
```

3. Write `/etc/docker/daemon.json`.
4. Enable Docker.
5. Optionally add `beep` to `docker` group.
6. Verify:

```bash
docker version
docker compose version
docker info | grep -E 'Docker Root Dir|Logging Driver|Live Restore'
docker run --rm hello-world
```

**Acceptance criteria:**

- Docker root dir is `/srv/docker`.
- Log rotation is configured.
- Compose plugin works.

---

### Phase 7: Main Server Security Baseline

**Goal:** Harden `10.10.10.34` before exposing Caddy and dependent services to the public internet.

**SSH target settings:**

```text
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
X11Forwarding no
MaxAuthTries 3
AllowUsers beep
```

**UFW target policy on `10.10.10.34`:**

```text
default deny incoming
default allow outgoing
allow SSH from 10.10.10.0/24
allow public HTTP/HTTPS only to Caddy on 80/443
bind service upstream ports to 127.0.0.1 whenever possible
deny direct public access to service ports
```

**Initial allowed ports on `10.10.10.34`:**

```text
22/tcp from 10.10.10.0/24
80/tcp from anywhere for Caddy HTTP and ACME HTTP-01
443/tcp from anywhere for Caddy HTTPS and ACME TLS-ALPN
GitLab HTTP upstream bound to 127.0.0.1
Registry upstream bound to 127.0.0.1
Grafana upstream bound to 127.0.0.1
Sentry upstream bound to 127.0.0.1
Prometheus/Alertmanager/Uptime upstream bound to 127.0.0.1
```

Exact upstream ports will be assigned in service compose files.

**Fail2ban:**

- Enable `sshd` jail.
- Later add Caddy/GitLab auth filters if logs are available.

**Acceptance criteria:**

- SSH from LAN works.
- SSH password still fails.
- UFW is enabled.
- Only Caddy `80/443` is open to all sources.
- SSH remains restricted to `10.10.10.0/24`.
- No application service port is open to all sources.

---

### Phase 8: Public Edge Cutover Safety

**Goal:** Prepare router, DNS, and rollback evidence before making `10.10.10.34` the CyberVPN public HTTP/HTTPS edge.

**Scope:** CyberVPN domains under `*.h.cyber-vpn.net` only.

**Steps:**

1. Save RouterOS NAT, filter, DNS, and interface state before changes.
2. Confirm no CyberVPN application/database/internal service port is forwarded publicly.
3. Confirm only TCP `80` and `443` are intended for public NAT to `10.10.10.34`.
4. Keep a timestamped backup of router config before NAT edits.

**Acceptance criteria:**

- Router baseline evidence is saved.
- Public NAT plan only contains `80/tcp` and `443/tcp` to `10.10.10.34`.
- Rollback instructions are documented.
- Non-CyberVPN home services are outside this plan.

---

### Phase 9: Caddy Edge On `10.10.10.34`

**Goal:** Make `10.10.10.34` the central public HTTP/HTTPS edge before the router NAT cutover.

**Installed service:**

```text
Caddy package: official Caddy apt repository
Service: caddy.service
Config: /etc/caddy/Caddyfile
Access log: /var/log/caddy/access.log
Evidence: /srv/storage/evidence/edge-caddy/
```

**Current route map:**

| Domain | Upstream |
|---|---|
| `gitlab.h.cyber-vpn.net` | `127.0.0.1:8081` |
| `registry.h.cyber-vpn.net` | `127.0.0.1:5050` |
| `grafana.h.cyber-vpn.net` | `127.0.0.1:3000` |
| `sentry.h.cyber-vpn.net` | `127.0.0.1:9000` |
| `prometheus.h.cyber-vpn.net` | `127.0.0.1:9090` |
| `loki.h.cyber-vpn.net` | `127.0.0.1:3100` |
| `alerts.h.cyber-vpn.net` | `127.0.0.1:9093` |
| `uptime.h.cyber-vpn.net` | `127.0.0.1:3001` |

**TLS policy:**

- `*.h.cyber-vpn.net` uses Cloudflare DNS-01 and one wildcard certificate.
- Caddy routes h-domains with host matchers inside a single wildcard site block.
- The allowlist endpoint listens only on `127.0.0.1:9123`.
- Do not enable on-demand issuance for arbitrary hostnames.
- Keep Cloudflare records DNS-only for first certificate issuance.

**Acceptance criteria:**

- `caddy validate --config /etc/caddy/Caddyfile` passes.
- `caddy.service` is active and enabled.
- Caddy listens on public `80/443`.
- Caddy admin API listens only on `127.0.0.1:2019`.
- TLS ask endpoint listens only on `127.0.0.1:9123`.
- `*.h.cyber-vpn.net` has a valid Let's Encrypt certificate.
- HTTP host requests redirect to HTTPS for configured domains.

---

### Phase 10: Cloudflare And Router Public Entry

**Goal:** Route public HTTP/HTTPS to Caddy on `10.10.10.34` only.

**Owner actions:**

1. In router:

```text
Forward TCP 80  -> 10.10.10.34:80
Forward TCP 443 -> 10.10.10.34:443
Do not forward TCP 22.
Do not forward app service ports.
```

2. In Cloudflare DNS:

```text
A gitlab.h       95.82.233.131
A registry.h    95.82.233.131
A grafana.h      95.82.233.131
A sentry.h       95.82.233.131
A prometheus.h   95.82.233.131
A loki.h         95.82.233.131
A alerts.h       95.82.233.131
A uptime.h       95.82.233.131
```

3. Start with DNS-only for:

```text
gitlab.h
registry.h
```

4. Consider proxied mode later for:

```text
grafana.h
sentry.h
alerts.h
uptime.h
```

**Acceptance criteria:**

- External `dig` resolves records.
- External TCP `80/443` reaches `10.10.10.34`.
- Nothing public reaches SSH or app service ports directly.
- Caddy serves valid TLS for the h-domains; `502` is expected until local upstream services are deployed.

---

### Phase 11: Service Reverse Proxy Routes

**Goal:** Attach each service to the already-installed Caddy edge on `10.10.10.34`.

**Target route map:**

| Domain | Upstream |
|---|---|
| `gitlab.h.cyber-vpn.net` | `127.0.0.1:8081` |
| `registry.h.cyber-vpn.net` | `127.0.0.1:5050` |
| `grafana.h.cyber-vpn.net` | `127.0.0.1:3000` |
| `sentry.h.cyber-vpn.net` | `127.0.0.1:9000` |
| `prometheus.h.cyber-vpn.net` | `127.0.0.1:9090` |
| `loki.h.cyber-vpn.net` | `127.0.0.1:3100` |
| `alerts.h.cyber-vpn.net` | `127.0.0.1:9093` |
| `uptime.h.cyber-vpn.net` | `127.0.0.1:3001` |

**Security requirements:**

- No proxy route before upstream authentication is configured.
- Add response security headers where practical.
- Preserve `X-Forwarded-For`, `X-Forwarded-Proto`, and Host headers.
- Enable access logs with rotation.
- Docker compose files should publish web ports to `127.0.0.1` only.
- For Grafana, Prometheus, Alertmanager, and Uptime Kuma, prefer additional basic auth or Cloudflare Access if public.

**Acceptance criteria:**

- Proxy config validates.
- Existing edge services still work.
- Pending service routes return controlled `503` instead of leaking upstream connection errors.
- Observability routes require Caddy Basic Auth before reaching the pending/upstream handler.
- Public edge health endpoint returns `200`.
- TLS certificate issuance works.

---

### Phase 12: Backup Foundation

**Goal:** Create backup discipline before deploying GitLab and Sentry.

**Status 2026-05-10:** completed for host/config backups.

Evidence:

```text
docs/evidence/backups/phase12-backup-foundation-20260510T050950Z.md
```

**Tools:**

```text
restic
rclone
systemd timers
```

**Initial backup target:**

```text
/srv/storage/backups
```

Remote backup is deferred until external disk or remote storage is available.

**Files:**

```text
/srv/cybervpn-h/secrets/restic.env
/srv/cybervpn-h/secrets/rclone.conf
/srv/cybervpn-h/scripts/backup-configs.sh
/srv/cybervpn-h/scripts/backup-gitlab.sh
/srv/cybervpn-h/scripts/backup-sentry.sh
/srv/cybervpn-h/scripts/backup-observability.sh
/srv/cybervpn-h/scripts/restic-check.sh
/srv/cybervpn-h/runbooks/restore-from-restic.md
```

**Retention:**

```text
daily 14
weekly 4
monthly 3
```

**Acceptance criteria:**

- [x] Restic repository initializes on HDD.
- [x] Config backup creates a snapshot.
- [x] Restore of one test file succeeds.
- [x] Backup logs are stored in evidence.

Phase 12 intentionally does not back up GitLab, Sentry, Prometheus, Loki or Grafana data yet because those services are not deployed. Their scripts exist as explicit placeholders until service-specific backup and restore drills can be validated.

---

### Phase 13: Hardware And Host Monitoring

**Goal:** Monitor hardware before service load arrives.

**Status 2026-05-10:** completed.

Evidence:

```text
docs/evidence/monitoring/phase13-hardware-host-monitoring-20260510T051948Z.md
```

**Components:**

```text
smartmontools
nvme-cli
lm-sensors
sysstat
rasdaemon
node-exporter
cadvisor
```

**Metrics to track:**

```text
NVMe temperature/wear
HDD SMART health
ECC/MCE errors
iowait
RAM available
swap usage
disk free/inodes
network errors
Docker container CPU/RAM/restarts/log size
```

**Acceptance criteria:**

- [x] `smartd` active.
- [x] `rasdaemon` active.
- [x] Node exporter reachable from Prometheus network only.
- [x] cAdvisor reachable from Prometheus network only.

Phase 13 also added node-exporter textfile metrics for SMART/NVMe/RAS status and a daily host health evidence snapshot timer.

---

### Phase 13.1: Grafana Hardware Dashboard

**Goal:** Add a first Grafana dashboard for the host/hardware metrics created in Phase 13.

**Files:**

```text
/srv/cybervpn-h/configs/grafana/provisioning/dashboards/cybervpn-h-hardware.json
/srv/cybervpn-h/configs/grafana/provisioning/dashboards/dashboard-provider.yml
```

**Dashboard panels:**

```text
SMART health
NVMe temperature/wear/spare
RAS/MCE status
RAM available
Swap usage
Disk free/inodes
iowait
network errors
Docker container CPU/RAM
Docker JSON log size
```

**Acceptance criteria:**

- [x] Dashboard is provisioned automatically by Grafana.
- [x] Dashboard queries use Phase 13 metrics.
- [x] Dashboard is visible after Grafana starts in Phase 14.

Evidence:

```text
docs/evidence/observability/phase14-observability-stack-20260510T055100Z.md
```

---

### Phase 14: Observability Stack

**Goal:** Deploy Grafana, Prometheus, Loki, Alertmanager, exporters, and Uptime Kuma.

**Files:**

```text
/srv/cybervpn-h/compose/observability/compose.yml
/srv/cybervpn-h/configs/prometheus/prometheus.yml
/srv/cybervpn-h/configs/alertmanager/alertmanager.yml
/srv/cybervpn-h/configs/loki/loki.yml
/srv/cybervpn-h/configs/grafana/provisioning
```

**Components:**

```text
grafana
prometheus
alertmanager
loki
promtail or grafana-alloy
node-exporter
cadvisor
blackbox-exporter
uptime-kuma
```

**Retention:**

```text
Prometheus: 15-30 days plus retention size
Loki: 14-30 days
Scrape interval: 30-60 seconds
```

**Data placement:**

- Hot data on NVMe.
- Loki chunks and snapshots may use HDD.

**Public exposure requirement:**

- Grafana requires strong admin password and 2FA/SSO plan before public exposure.
- Prometheus should not be publicly exposed unless protected by strong auth or Cloudflare Access.
- Alertmanager should not be publicly exposed without auth.

**Acceptance criteria:**

- [x] Grafana login/API works locally with the provisioned admin account.
- [x] Prometheus scrapes host and Docker exporters.
- [x] Loki receives host/container logs.
- [x] Uptime Kuma is deployed behind Caddy Basic Auth.
- [x] Alertmanager accepts a test alert.
- [x] Telegram notification delivery works.
- [x] Resend SMTP backup email delivery works through `smtp.resend.com:2587`.

Evidence:

```text
docs/evidence/observability/phase14-observability-stack-20260510T055100Z.md
```

---

### Phase 15: GitLab

**Goal:** Deploy GitLab for internal DevOps, registry, CI, artifacts, issues, evidence, and release workflows.

**Files:**

```text
/srv/cybervpn-h/compose/gitlab/compose.yml
/srv/cybervpn-h/secrets/gitlab.env
/srv/cybervpn-h/runbooks/gitlab-ops.md
/srv/cybervpn-h/runbooks/gitlab-restore.md
```

**Placement:**

NVMe:

```text
/srv/gitlab/config
/srv/gitlab/logs
/srv/gitlab/data
```

HDD:

```text
/srv/storage/gitlab-artifacts
/srv/storage/gitlab-packages
/srv/storage/gitlab-lfs
/srv/storage/gitlab-uploads
/srv/storage/gitlab-registry
/srv/storage/gitlab-cache
/srv/storage/backups/gitlab
```

**Initial security settings:**

```text
Disable public signup
Require 2FA for admin accounts
Disable open registration
Set external URL to https://gitlab.h.cyber-vpn.net
Set registry external URL to https://registry.h.cyber-vpn.net
Use HTTPS git clone by default
Do not expose GitLab SSH publicly in first iteration
```

**Resource target:**

```text
RAM 12-16 GB
CPU 6-10 threads
```

**Acceptance criteria:**

- [x] GitLab starts.
- [x] Admin/root password is valid.
- [x] Public signup disabled.
- [x] Test repo push/pull over HTTPS works.
- [x] Registry login/push/pull works.
- [x] GitLab backup writes to HDD.

Evidence:

```text
docs/evidence/gitlab/phase15-gitlab-20260510T062216Z.md
```

---

### Phase 16: GitHub Mirror

**Goal:** Ensure the project does not depend only on the server at home.

**Project path:**

```text
/home/beep/projects/VPNBussiness
```

**Decisions:**

- Mirror direction: `GitHub -> GitLab`.
- GitHub remains the external source of truth and emergency fallback.
- Home GitLab is an internal DevOps mirror; do not create unique project work only in home GitLab.

- Production image registry must not be only the home GitLab registry.
- Keep GHCR or another external registry as emergency source.

**Acceptance criteria:**

- [x] Mirror sync works.
- [x] Emergency deploy can use GitHub/GHCR without home GitLab.
- [x] Mirror credentials are stored as secrets, not committed.

Evidence:

```text
docs/evidence/gitlab/phase16-github-mirror-20260510T063910Z.md
```

---

### Phase 16.1: GitLab Runner

**Goal:** Provide CI capacity without letting CI consume the whole server.

**Files:**

```text
/srv/cybervpn-h/compose/gitlab-runner/compose.yml
/srv/cybervpn-h/secrets/gitlab-runner/config.toml
/srv/cybervpn-h/configs/gitlab-runner/config.toml.example
/srv/cybervpn-h/runbooks/gitlab-runner.md
```

**Initial policy:**

```text
executor: docker
concurrency: 1-2
cache: /srv/storage/gitlab-cache
memory limit: 8-16 GB
cpu limit: 8-16 threads
protected runner for protected branches
no arbitrary untrusted branch execution
```

**Security decision:**

- Avoid mounting Docker socket into arbitrary jobs.
- Phase 17 normal runner mounts Docker socket only in the runner service container, not in job containers.
- Normal runner is restricted to protected refs and required tags.
- Docker-in-Docker and privileged jobs are deferred to a separate future protected/manual runner.

**Acceptance criteria:**

- [x] Runner registers.
- [x] Test pipeline runs.
- [x] Runner resource limits are configured.
- [x] Cache lands on HDD.

Evidence:

```text
docs/evidence/gitlab/phase16-1-gitlab-runner-20260510T100341Z.md
```

---

### Phase 17: Sentry Self-Hosted

**Goal:** Deploy Sentry for CyberVPN error tracking with strict retention and resource limits.

**Files:**

```text
/srv/cybervpn-h/compose/sentry
/srv/cybervpn-h/secrets/sentry.env
/srv/cybervpn-h/runbooks/sentry-ops.md
/srv/cybervpn-h/runbooks/sentry-restore.md
```

**Placement:**

NVMe:

```text
/srv/sentry/postgres
/srv/sentry/redis
/srv/sentry/clickhouse
/srv/sentry/kafka
/srv/sentry/zookeeper
/srv/sentry/symbolicator
```

HDD:

```text
/srv/storage/sentry-attachments
/srv/storage/backups/sentry
```

**Initial limits:**

```text
RAM 16-24 GB
CPU 8-12 threads
event retention 14-30 days
traces off or low sample
attachments on HDD
source maps later after release flow stabilizes
```

**Acceptance criteria:**

- [x] Sentry receives test event.
- [x] Admin login secured.
- [x] Retention configured.
- [x] Attachments path is HDD-backed.
- [x] Backups/config exports documented.

Evidence:

```text
docs/evidence/sentry/phase17-sentry-self-hosted-20260510T111500Z.md
```

---

### Phase 18: S1 Dashboards And Alerts

**Goal:** Build the first operational dashboards for CyberVPN S1.

**Dashboards:**

```text
API health
Auth success/failure
Payment success/failure
Webhook duplicate/retry
Paid-but-no-access/orphan payments
Provisioning latency
Remnawave API health
Worker queue/retry/dead-letter
Telegram bot health
Admin/support actions
VPN node health
Error rate by service
```

**Alerts:**

```text
host down
disk above 80/90 percent
swap usage above 1 GB sustained
iowait high
Docker container restarting
GitLab unavailable
Sentry ingestion failing
payment errors elevated
webhook retries elevated
VPN node unavailable
TLS certificate near expiry
```

**Notification channels:**

```text
Telegram primary
Email fallback if SMTP is available
```

**Acceptance criteria:**

- [x] Dashboards imported or provisioned.
- [x] Test alert reaches Telegram.
- [x] Backup email SMTP smoke succeeds through Resend.
- [x] Alert evidence saved for local Alertmanager delivery path.

Evidence:

```text
docs/evidence/observability/phase18-s1-dashboards-alerts-20260510T120537Z.md
```

---

### Phase 19: Evidence Archive

**Goal:** Preserve proof of releases, backups, restores, incidents, and security checks.

**Paths:**

```text
/srv/storage/evidence/releases
/srv/storage/evidence/backups
/srv/storage/evidence/restores
/srv/storage/evidence/security-scans
/srv/storage/evidence/incidents
```

**Artifacts:**

```text
release manifests
image digests
SBOM
Trivy/Grype reports
npm audit/pip audit reports
secret scan reports
backup logs
restore test logs
rollback dry-run artifacts
```

**Acceptance criteria:**

- [x] Evidence tree exists.
- [x] First baseline evidence pack is stored.
- [x] Retention and cleanup policy is documented.

Evidence:

```text
docs/evidence/evidence-archive/phase19-evidence-archive-20260510T122832Z.md
```

---

### Phase 20: Security Pipeline

**Goal:** Add security checks to CI and release evidence.

**Tools:**

```text
Trivy
Grype
npm audit
pip audit
gitleaks or trufflehog
SBOM generation
```

**Rules:**

- Do not store production secrets in repositories.
- Do not store production secrets in home GitLab without encryption.
- `.env` files must be `0600`.
- Docker socket must not be mounted into untrusted jobs.
- Security scan results are release evidence.

**Acceptance criteria:**

- [x] Secret scan job runs.
- [x] Dependency scan job runs.
- [x] Container scan job runs.
- [x] SBOM artifact is generated for release candidates.

**Evidence:**

```text
docs/evidence/security/phase20-security-pipeline-20260510T130144Z.md
/srv/storage/evidence/security-scans/cybervpn-h-phase20-security-pipeline-20260510T130144Z
```

---

### Phase 21: Restore Drill

**Goal:** Prove that backups can restore useful state.

**Runbooks:**

```text
/srv/cybervpn-h/runbooks/restore-gitlab.md
/srv/cybervpn-h/runbooks/restore-sentry.md
/srv/cybervpn-h/runbooks/restore-grafana.md
/srv/cybervpn-h/runbooks/restore-from-restic.md
```

**Drills:**

1. Restore one config file from restic.
2. Restore Grafana dashboards from backup.
3. Restore a GitLab backup in a non-production test directory or container.
4. Document timings, errors, and missing pieces.

**Acceptance criteria:**

- [x] Restore evidence exists.
- [x] Runbooks are accurate enough to follow under pressure.
- [x] Backup success is not accepted without restore proof.

**Evidence:**

```text
docs/evidence/restores/phase21-restore-drill-20260510T134712Z.md
/srv/storage/evidence/restores/cybervpn-h-restore-drill-20260510T134712Z
```

---

### Phase 22: Stage 2 Additions

**Goal:** Add broader reporting and quality gates after S1 is stable.

**Detailed plan:**

```text
docs/plans/2026-05-10-cybervpn-stage2-analytics-quality-gates-plan.md
docs/runbooks/STAGE2_ANALYTICS_AND_REPORTING.md
```

**Dashboards:**

```text
infra/grafana/dashboards/stage2-payment-reconciliation-dashboard.json
infra/grafana/dashboards/stage2-refund-renewal-dashboard.json
infra/grafana/dashboards/stage2-subscription-expiry-dashboard.json
infra/grafana/dashboards/stage2-support-sla-dashboard.json
infra/grafana/dashboards/stage2-status-page-dashboard.json
infra/grafana/dashboards/stage2-product-analytics-dashboard.json
infra/grafana/dashboards/stage2-release-quality-dashboard.json
```

**Prometheus and synthetic checks:**

```text
infra/prometheus/rules/stage2_analytics_alerts.yml
infra/prometheus/targets/stage2-public-endpoints.json
infra/blackbox/blackbox.yml
```

**Scripts:**

```text
scripts/grafana/generate-stage2-dashboards.py
scripts/status/export-status-page-data.sh
scripts/release/generate-release-comparison-report.sh
scripts/sentry/upload-frontend-sourcemaps.sh
scripts/restore/run-scheduled-restore-drill.sh
scripts/validate-stage2-analytics-artifacts.py
```

**CI jobs:**

```text
observability:stage2-artifacts
quality:release-comparison-report
sentry:frontend-sourcemaps
```

**Acceptance criteria:**

- [x] Stage 2 dashboards are generated and provisioned.
- [x] Stage 2 Prometheus rules are validated and loaded.
- [x] CyberVPN-only synthetic public endpoint checks exist.
- [x] Status-page data can be exported from Prometheus.
- [x] Monthly restore drill scheduling is installed.
- [x] Release comparison reports are generated as evidence.
- [x] Sentry source map upload is available through explicit CI opt-in.
- [x] CI quality gates include Stage 2 artifact validation.
- [x] Phase 20 security gates continue to cover Trivy, Grype, npm audit, pip audit, secret scan, and SBOM.
- [x] Stage 2 does not block S1 unless an active P0 customer-impacting issue is detected.

**Evidence:**

```text
docs/evidence/observability/phase22-stage2-analytics-quality-gates-20260510T140915Z.md
/srv/storage/evidence/releases/phase22-stage2-analytics-20260510T140915Z
```

---

### Phase 23: Stage 3 Partner / Reseller Platform

**Goal:** Prepare partner/reseller infrastructure without overloading S1.

**Detailed plan:**

```text
docs/plans/2026-05-10-cybervpn-stage3-partner-reseller-platform-plan.md
docs/runbooks/PARTNER_RESELLER_STAGE3_RUNBOOK.md
```

**Files:**

```text
infra/partner-lab/compose.yml
infra/partner-lab/README.md
infra/grafana/dashboards/stage3-partner-staging-readiness-dashboard.json
infra/grafana/dashboards/stage3-partner-attribution-storefront-dashboard.json
infra/grafana/dashboards/stage3-partner-settlement-payout-dashboard.json
infra/grafana/dashboards/stage3-partner-support-audit-risk-dashboard.json
infra/prometheus/rules/stage3_partner_reseller_alerts.yml
infra/prometheus/targets/stage3-storefront-endpoints.json
scripts/partner/run-webhook-test-receiver.py
scripts/partner/redact-stage3-import.py
scripts/partner/generate-stage3-sandbox-reports.sh
scripts/partner/check-storefront-synthetic-targets.sh
scripts/validate-stage3-partner-artifacts.py
```

**Acceptance criteria:**

- [x] Partner platform has a separated compose/config area.
- [x] Partner sandbox is resource-limited and off by default.
- [x] Partner portal CI pipeline has Stage 3 artifact and sandbox-pack jobs.
- [x] Partner dashboards are provisioned in Grafana.
- [x] Partner reporting sandbox templates exist.
- [x] Referral attribution test report template exists.
- [x] Commission ledger test report template exists.
- [x] Payout simulation and settlement dry-run templates exist.
- [x] Anti-fraud experiment template exists.
- [x] Partner support/audit/risk dashboard exists.
- [x] Storefront synthetic target file exists.
- [x] Storefront live scrape is not enabled until DNS exists.
- [x] Partner webhook test receiver exists and is local-only by default.
- [x] Redacted/anonymized data import tool exists and was tested.
- [x] Settlement evidence archive tree exists.
- [x] Partner incident runbook exists.

**Evidence:**

```text
docs/evidence/partner-platform/phase23-stage3-partner-reseller-20260510T143500Z.md
/srv/storage/evidence/settlements/phase23-sandbox-20260510T143000Z
```

---

## Execution Order

1. Phase 0: Safety and baseline.
2. Phase 1: Host identity.
3. Phase 2: Directory layout.
4. Phase 3: Base packages.
5. Phase 4: Swap and kernel tunables.
6. Phase 5: CPU performance governor.
7. Phase 6: Docker Engine and Compose.
8. Phase 7: Main server security baseline.
9. Phase 8: Public edge cutover safety.
10. Phase 9: Caddy edge on `10.10.10.34`.
11. Phase 10: Cloudflare and router public entry.
12. Phase 11: Service reverse proxy routes.
13. Phase 12: Backup foundation.
14. Phase 13: Hardware and host monitoring.
15. Phase 13.1: Grafana hardware dashboard.
16. Phase 14: Observability stack.
17. Phase 15: GitLab.
18. Phase 16: GitHub mirror.
19. Phase 16.1: GitLab Runner.
20. Phase 17: Sentry self-hosted.
21. Phase 18: S1 dashboards and alerts.
22. Phase 19: Evidence archive.
23. Phase 20: Security pipeline.
24. Phase 21: Restore drill.
25. Phase 22: Stage 2 additions.
26. Phase 23: Stage 3 partner/reseller platform.

---

## Current Implementation Status

Completed on `2026-05-09`:

1. `/srv/cybervpn-h` and `/srv/storage` directory structure created.
2. Baseline evidence saved under `/srv/storage/evidence`.
3. Base packages installed.
4. Swap increased to `32 GB`; swappiness reduced.
5. CPU performance governor enabled.
6. Docker Engine and Docker Compose plugin installed; Docker data root set to `/srv/docker`.
7. SSH hardening, UFW, and fail2ban enabled.
8. Caddy installed on `10.10.10.34` as the new central edge.
9. RouterOS NAT moved public `80/443` to `10.10.10.34`.
10. RouterOS split DNS maps public service names to LAN targets for internal clients.
11. Caddy Cloudflare DNS module installed for DNS-01 fallback.
12. Cloudflare token installed as `/srv/cybervpn-h/secrets/caddy/cloudflare.env`.
13. Caddy systemd override added so `--environ` does not log environment secrets.
14. `*.h.cyber-vpn.net` issued through Cloudflare DNS-01.
15. Public `80/443` verified reachable on `95.82.233.131`.
16. Phase 11 service routes hardened: undeployed h-services return controlled `503`, observability h-domains require Caddy Basic Auth, and `/.well-known/cybervpn-edge-health` returns `200`.
17. MikroTik static DHCP lease created for CyberVPN host MAC `00:E0:4C:7D:40:65` at `10.10.10.34`.
18. Pre-Phase 12 connectivity restored after physical reboot: SSH works, RouterOS ARP is reachable, h-domain health check returns `200`, observability route returns `401`, and pending GitLab route returns `503`.

Completed on `2026-05-10`:

1. Phase 12 backup foundation completed with local restic repository on HDD.
2. Phase 13 hardware and host monitoring completed: `smartd`, `rasdaemon`, node-exporter textfile metrics, node-exporter, and cAdvisor.
3. Phase 13.1 Grafana dashboard added: `CyberVPN h Hardware & Host`.
4. Phase 14 observability stack deployed: Grafana, Prometheus, Alertmanager, Loki, Promtail, Blackbox Exporter, and Uptime Kuma.
5. Observability routes are public through Caddy but protected by Caddy Basic Auth.
6. Prometheus targets are up for host, Docker, Grafana, Loki, Alertmanager, Blackbox, and Prometheus itself.
7. Loki receives Caddy access logs and Docker JSON logs.
8. Docker log collection was corrected for Docker data root `/srv/docker`.
9. Post-Phase 14 config backup completed as restic snapshot `a4c07acb`.
10. Phase 15 GitLab CE deployed at `gitlab.h.cyber-vpn.net`, with registry at `registry.h.cyber-vpn.net`.
11. GitLab public signup disabled, private defaults applied, and 2FA requirement enabled with 48h grace period.
12. HTTPS repository push/clone smoke test passed.
13. GitLab registry login/push/pull smoke test passed.
14. GitLab application backup written to HDD under `/srv/storage/backups/gitlab`.
15. Post-Phase 15 config backup completed as restic snapshot `6fd8ab8a`.
16. Phase 16 GitHub-to-GitLab mirror configured for `Beep206/CyberVPN` -> `root/CyberVPN`.
17. Home GitLab project `root/CyberVPN` created as private mirror project.
18. Mirror systemd timer `cybervpn-github-to-gitlab-mirror.timer` enabled and active.
19. Mirror verification passed: GitHub refs `41`, GitLab refs `41`, and `main` matched at `dd7ac0473c6ea827dfec7bf68f398f93735b4d4a`.
20. GitHub Actions `Control Plane Images` workflow verified active for GHCR publishing.
21. Post-Phase 16 GitLab application backup completed: `/srv/storage/backups/gitlab/1778395234_2026_05_10_18.11.2_gitlab_backup.tar`.
22. Post-Phase 16 config backup completed as restic snapshot `0e54a2c2`.
23. Phase 16.1 GitLab Runner deployed as `cybervpn-h-docker-protected`.
24. Runner policy applied: Docker executor, protected refs only, required tags `h-docker,protected`, untagged jobs disabled, privileged jobs disabled.
25. Phase 16.1 runner smoke pipeline passed in `root/phase17-runner-smoke`, pipeline `5`, job `25`.
26. Runner cache verified on HDD under `/srv/storage/gitlab-cache`.
27. Local `.gitlab-ci.yml` aligned to default tag `h-docker`; manual Docker package jobs remain on future `dind` runner.
28. Post-Phase 16.1 GitLab application backup completed: `/srv/storage/backups/gitlab/1778408068_2026_05_10_18.11.2_gitlab_backup.tar`.
29. Post-Phase 16.1 config backup completed as restic snapshot `ac127b0a`.
30. Phase 17 Sentry Self-Hosted deployed from official `getsentry/self-hosted` release `26.4.2`.
31. Sentry public route enabled: `sentry.h.cyber-vpn.net` -> Caddy -> `127.0.0.1:9000`.
32. Sentry configured with `COMPOSE_PROFILES=errors-only`, `SENTRY_EVENT_RETENTION_DAYS=30`, and explicit Docker CPU/RAM limits.
33. Sentry admin user created, public registration disabled, secure proxy headers enabled, and beacon disabled.
34. Attachments/data volume verified on HDD-backed `/srv/storage/sentry-attachments`.
35. Smoke project `cybervpn-phase17-smoke` received test events; Sentry issue query returned `group_count=2`.
36. Sentry backup script implemented and run; latest local backup is `/srv/storage/backups/sentry/sentry-20260510T111907Z`.
37. Sentry restic backup completed as snapshot `0dc4f761`.
38. Sentry GeoIP database updates configured with `geoipupdate`; GeoLite2 ASN, City, and Country databases are mounted into Sentry.
39. Post-GeoIP Sentry backup completed as restic snapshot `ae03fe70`.
40. Phase 18 S1 dashboards imported into Grafana folder `CyberVPN h`; `22` dashboards are currently provisioned.
41. Phase 18 Prometheus rules installed for host, disk, swap, iowait, Docker restarts, GitLab, Sentry ingestion, payment/webhook errors, VPN node availability, and TLS expiry.
42. Sentry ingestion smoke metric is published through node-exporter textfile collector as `cybervpn_h_sentry_ingestion_smoke_success`.
43. Phase 18 Prometheus target verification passed for Grafana, Prometheus, Alertmanager, Loki, cAdvisor, node-exporter, GitLab, Sentry, and h-domain edge health endpoints.
44. Alertmanager Phase 18 local smoke alert was accepted and stored as evidence.
45. Telegram live delivery was enabled and verified through the Telegram Bot API.
46. Resend SMTP backup email was configured through `smtp.resend.com:2587` and verified with a live SMTP smoke.
47. Post-Phase 18 config backup completed as restic snapshot `7e6ecd48`.
46. Phase 19 evidence archive tree created under `/srv/storage/evidence/{releases,backups,restores,security-scans,incidents}`.
47. Phase 19 baseline evidence pack stored at `/srv/storage/evidence/releases/cybervpn-h-baseline-20260510T122832Z`.
48. Phase 19 baseline security scan pack stored at `/srv/storage/evidence/security-scans/cybervpn-h-baseline-20260510T122832Z`.
49. Evidence retention policy and dry-run cleanup script installed; no automatic destructive cleanup is enabled.
50. Post-Phase 19 config backup completed as restic snapshot `10c54d40`.
51. Phase 20 GitLab CI security jobs added for Gitleaks, npm audit, pip-audit, Trivy/Grype, and Syft SBOM generation.
52. Phase 20 local CI-equivalent security scans completed; Gitleaks, npm high/critical, and pip-audit reports are clean for the configured S1 scopes.
53. Phase 20 container/filesystem scans completed with Trivy and Grype; remaining high/critical findings are preserved as release-triage evidence.
54. Phase 20 SBOM artifacts generated in CycloneDX and SPDX formats.
55. Phase 20 evidence pack stored at `/srv/storage/evidence/security-scans/cybervpn-h-phase20-security-pipeline-20260510T130144Z`.
56. Post-Phase 20 config backup completed as restic snapshot `2aa92491`.
57. Phase 20 security scripts renamed from phase-numbered names to stable action names: `scan-secrets.sh`, `audit-dependencies.sh`, `scan-filesystem-vulnerabilities.sh`, `generate-sbom.sh`.
58. Post-security-script-rename config backup completed as restic snapshot `01811b41`.
59. Phase 21 restore runbooks installed for restic, Grafana, GitLab, and Sentry.
60. Phase 21 restore drill completed: restic config file restore, Grafana dashboard restore from backup, and GitLab backup archive restore in a non-production directory.
61. Phase 21 restore evidence stored at `/srv/storage/evidence/restores/cybervpn-h-restore-drill-20260510T134712Z`.
62. Post-Phase 21 config backup completed as restic snapshot `359f7c44`.

---

## Blockers And Decisions Before Public Launch

1. Rotate the Cloudflare API token because it was exposed during setup; the replacement token needs `Zone / Zone / Read` and `Zone / DNS / Edit` for `cyber-vpn.net`.
2. Router/NAT already forwards `80/443` to `10.10.10.34`.
3. Decide whether GitLab over SSH is needed publicly. Default answer: no, use HTTPS first.
4. Decide whether Cloudflare proxy is acceptable per subdomain. Default:
   - `gitlab.h` and `registry.h`: DNS-only initially.
   - admin/observability UIs: proxied only with additional access controls.
5. Decide where remote backups go when external disk or object storage becomes available.
6. MikroTik UPnP is enabled and currently creates many dynamic forwards for unrelated home devices. This was not changed in Phase 11, but should be reviewed before treating the home WAN as a hardened public edge.
7. RAM should still be physically checked and balanced later, but it is not a blocker for continuing the current phases. After the latest checks Linux reports about `48 GB` online, with NUMA memory about `16 GB / 32 GB`. DMI shows six populated `8 GB` DIMMs (`DIMM_C1` through `DIMM_H1`), not the earlier expected `64 GB`.
8. Rotate the MaxMind license key because it was exposed during GeoIP setup.
9. Rotate the Telegram bot token and Resend API key because they were exposed during live receiver setup.
10. Phase 20 security reports contain high/critical Trivy and Grype findings in auxiliary SDK, desktop/Rust, and app lockfiles. These must be triaged before a release candidate is treated as shippable.
11. Phase 21 did not perform a full GitLab application restore into a separate container; the backup archive was validated by extraction, database gzip check, and repository bundle verification. Do a containerized GitLab restore before relying on home GitLab for disaster recovery under pressure.
12. GitLab registry data is not included in the current GitLab backup because `SKIP=registry` is used. Add a registry backup path if registry images become production-critical.

Evidence:

```text
docs/evidence/routeros/pre-phase12-connectivity-20260509T171124Z.txt
docs/evidence/routeros/pre-phase12-connectivity-restored-20260509T175505Z.txt
```

---

## Rollback Principles

- Every host config change must have a timestamped backup.
- Do not enable UFW without an active SSH session and an automatic rollback timer.
- Do not publish DNS before upstream authentication is configured.
- Do not expose GitLab/Sentry/Grafana directly from `10.10.10.34`.
- If a public route breaks, disable new public exposure and debug Caddy on `10.10.10.34` offline.
