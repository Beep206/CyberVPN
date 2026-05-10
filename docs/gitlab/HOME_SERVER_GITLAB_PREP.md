# Home Server GitLab Preparation

Status: initial preparation note  
Date: 2026-05-09  
Host target: Ubuntu 24.04.4 LTS bare metal home server

## Server Role

The home server can run:

- GitLab;
- GitLab Runner;
- GitLab artifacts/cache/packages/registry;
- CI evidence jobs;
- security scans;
- local Docker image build checks;
- observability and Sentry in later steps.

The home server must not be required for:

- customer frontend availability;
- backend API availability;
- payment webhook delivery;
- Telegram production webhook delivery;
- production Remnawave control-plane;
- VPN node availability;
- production database availability;
- production rollback capability.

## Recommended Hostname And Access

Change the generic hostname `server` to a stable ops name:

```bash
sudo hostnamectl set-hostname cybervpn-home-ops
```

Recommended internal names:

```text
gitlab.home.cyber-vpn.net
registry.home.cyber-vpn.net
runner.home.cyber-vpn.net
grafana.home.cyber-vpn.net
sentry.home.cyber-vpn.net
```

Prefer VPN-only access through WireGuard or Tailscale. Do not expose GitLab directly to the public internet unless that is a deliberate operational decision.

## Base Packages

Install the base host tooling:

```bash
sudo apt update
sudo apt install -y \
  ca-certificates \
  curl \
  git \
  git-lfs \
  jq \
  yq \
  ufw \
  fail2ban \
  smartmontools \
  nvme-cli \
  lm-sensors \
  sysstat \
  htop \
  iotop \
  iftop \
  chrony \
  restic \
  rclone
```

Install Docker Engine and the Compose plugin from Docker's official repository before installing GitLab containers.

## Firewall Baseline

Initial VPN/LAN-only baseline:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.10.10.0/24 to any port 22 proto tcp
sudo ufw allow from 10.10.10.0/24 to any port 80 proto tcp
sudo ufw allow from 10.10.10.0/24 to any port 443 proto tcp
sudo ufw enable
```

If WireGuard is used, allow only the WireGuard UDP port from the internet and keep GitLab HTTP(S) private.

## Directory Layout

Create a stable directory layout:

```bash
sudo mkdir -p /srv/cybervpn-home/{compose,secrets,runbooks,evidence,scripts,configs}
sudo mkdir -p /srv/cybervpn-home/compose/{gitlab,gitlab-runner,observability,sentry,reverse-proxy,backups,security,partner-lab}
sudo mkdir -p /srv/gitlab/{config,logs,data}
sudo mkdir -p /srv/gitlab-runner/{config,cache}
sudo mkdir -p /srv/storage/{backups,archives,gitlab-artifacts,gitlab-packages,gitlab-lfs,gitlab-uploads,gitlab-registry,gitlab-cache,evidence}
```

Recommended placement:

| Path | Disk | Purpose |
|---|---|---|
| `/srv/gitlab/config` | NVMe | GitLab config |
| `/srv/gitlab/logs` | NVMe | GitLab logs |
| `/srv/gitlab/data` | NVMe | Git repositories, PostgreSQL, Redis, Gitaly |
| `/srv/gitlab-runner/config` | NVMe | Runner config |
| `/srv/gitlab-runner/cache` | HDD or NVMe | Runner cache |
| `/srv/storage/gitlab-artifacts` | HDD | CI artifacts |
| `/srv/storage/gitlab-packages` | HDD | Packages |
| `/srv/storage/gitlab-lfs` | HDD | LFS objects |
| `/srv/storage/gitlab-registry` | HDD | Container registry |
| `/srv/storage/backups` | HDD | Backups |
| `/srv/storage/evidence` | HDD | Evidence archive |

## GitLab Runner Plan

Use two Docker runners.

### Normal Runner

Purpose:

- lint;
- tests;
- frontend/admin/partner builds;
- Python smoke jobs;
- security scans.

Settings:

```text
executor = docker
privileged = false
concurrent = 1-2
run untagged jobs = true
```

### Docker Build Runner

Purpose:

- manual Docker image build jobs from `.gitlab-ci.yml`.

Settings:

```text
executor = docker
privileged = true
concurrent = 1
tag = dind
run untagged jobs = false
```

The `dind` runner is intentionally separated because privileged Docker-in-Docker is a larger security surface.

## GitLab Resource Guardrails

Start conservatively:

| Component | Initial limit |
|---|---:|
| GitLab | 12-16 GB RAM |
| Normal runner concurrency | 1-2 |
| DIND runner concurrency | 1 |
| GitLab registry | HDD-backed, manual use only |
| CI artifacts retention | 7-14 days initially |
| Package/registry cleanup | Scheduled cleanup required |

Do not run GitLab, Sentry, full observability and high-concurrency CI without limits at the same time.

## Backup Policy

Minimum before relying on GitLab:

1. Daily GitLab backup to `/srv/storage/backups/gitlab`.
2. Daily backup of `/srv/gitlab/config`.
3. Weekly offline backup to external disk.
4. Monthly restore drill.
5. Restore evidence stored under `/srv/storage/evidence/gitlab`.

GitHub remains the external repository fallback, but GitLab issues, CI variables, packages and registry data still need backups.

## First Import Checklist

1. Install GitLab.
2. Create private `cybervpn/cybervpn` project.
3. Disable public sign-up.
4. Require 2FA for maintainers.
5. Protect `main`.
6. Add GitLab remote locally.
7. Push `main`.
8. Push tags.
9. Register normal Docker runner.
10. Register `dind` runner.
11. Run `gitlab:ci-contract`.
12. Run one frontend path pipeline.
13. Run one backend path pipeline.
14. Run one manual Docker build job on the `dind` runner.
15. Configure GitHub mirror/fallback strategy.

## Immediate Repo Commands

From the monorepo:

```bash
git remote add gitlab ssh://git@gitlab.home.cyber-vpn.net:2222/cybervpn/cybervpn.git
git push gitlab main
git push gitlab --tags
python scripts/validate_gitlab_ci_contract.py
```

Only enable GitLab -> GitHub push mirroring after the first CI run and branch protection are proven.
