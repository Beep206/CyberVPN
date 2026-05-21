# Stage 1 Rented Production OS Baseline And Firewall Evidence

Date: `2026-05-19T16:47:52Z`

Stage: `STAGE1-RENT-02`

Scope: `prod-app-1` OS baseline, SSH hardening, firewall, basic runtime packages and Docker foundation.

## Result

```text
PASS
```

`prod-app-1` is ready for the next deployment step:

```text
STAGE1-RENT-03: DNS/TLS temporary health routes
```

## Host

| Field | Value |
|---|---|
| Role | `prod-app-1` |
| IPv4 | `45.87.41.146` |
| IPv6 | `2a0d:2787:1b:12f5::a/64` |
| Hostname | `prod-app-1` |
| OS | `Ubuntu 24.04` |
| Kernel | `6.8.0-106-generic` |
| CPU | `6` |
| RAM | `15Gi` visible |
| Swap | `4.0Gi` |
| Root filesystem | `232G`, `225G` available after setup |

## SSH Access

The original `MainKey2_private` file could not be loaded by local OpenSSH. It was locally re-encoded into:

```text
~/.ssh/MainKey2_private_fixed.pem
```

The fixed key derives the same public fingerprint:

```text
2048 SHA256:c7qFl4d3KfF3Y8m9ZRzbCnbyK0GAB0Jc6u4L4wUTiko no comment (RSA)
```

Verified access:

| User | Status |
|---|---|
| `root` | key-only access works |
| `deploy` | key-only access works |
| `deploy` sudo | `sudo -n true` works |

`deploy` user:

```text
uid=1000(deploy) gid=1000(deploy) groups=1000(deploy),27(sudo),100(users)
```

Sudoers file:

```text
/etc/sudoers.d/90-cybervpn-deploy
```

Validation:

```text
visudo -cf /etc/sudoers.d/90-cybervpn-deploy -> parsed OK
```

## SSH Hardening

Configuration file:

```text
/etc/ssh/sshd_config.d/90-cybervpn-hardening.conf
```

Effective SSH policy:

```text
logingracetime 30
maxauthtries 3
clientaliveinterval 30
clientalivecountmax 3
permitrootlogin without-password
pubkeyauthentication yes
passwordauthentication no
kbdinteractiveauthentication no
x11forwarding no
allowtcpforwarding no
allowagentforwarding no
permittunnel no
```

Note:

```text
Root login remains enabled for key-only bootstrap access. It can be restricted further after deployment automation and emergency access are confirmed through deploy.
```

## Firewall

UFW is active:

```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
```

Allowed inbound:

| Port | Purpose |
|---:|---|
| `22/tcp` | SSH |
| `80/tcp` | HTTP edge |
| `443/tcp` | HTTPS edge |

Allowed for both IPv4 and IPv6:

```text
22/tcp
80/tcp
443/tcp
```

Current listening TCP ports:

```text
127.0.0.53:53     systemd-resolved local DNS
127.0.0.54:53     systemd-resolved local DNS
0.0.0.0:22        sshd
[::]:22           sshd
```

No application service is listening yet.

Docker/UFW caveat:

```text
Docker can publish ports through its own iptables rules. Stage 1 compose must publish only the intended edge service ports and keep PostgreSQL, Valkey, Remnawave API, worker, bot runtime and metrics private.
```

## Fail2ban

Installed and enabled:

```text
fail2ban: active / enabled
```

Jail:

```text
[sshd]
enabled = true
backend = systemd
port = ssh
maxretry = 4
findtime = 10m
bantime = 1h
```

Status at evidence time:

```text
Currently banned: 0
Total banned: 0
```

## Unattended Upgrades

APT timers:

```text
apt-daily.timer: enabled
apt-daily-upgrade.timer: enabled
```

Configuration:

```text
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
```

Automatic reboot is disabled. Reboots remain manual during Stage 1.

## Journald

Configuration file:

```text
/etc/systemd/journald.conf.d/90-cybervpn.conf
```

Policy:

```text
SystemMaxUse=1G
RuntimeMaxUse=256M
MaxRetentionSec=14day
Compress=yes
```

## Docker

Installed from official Docker apt repository for Ubuntu `noble`.

Installed versions:

```text
Docker Engine client=29.5.1 server=29.5.1
Docker Compose version v5.1.3
```

Docker daemon configuration:

```text
/etc/docker/daemon.json
```

Runtime policy:

```text
root=/var/lib/docker
logging=json-file
live_restore=true
cgroup=systemd
```

Log rotation:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "live-restore": true,
  "default-address-pools": [
    {
      "base": "172.30.0.0/16",
      "size": 24
    }
  ]
}
```

No containers were deployed during this stage.

## Swap

Created:

```text
/swapfile 4G
```

Configured:

```text
vm.swappiness=10
```

Reason:

```text
prod-app-1 will initially host the app/control-plane stack. A small swap buffer reduces the chance of abrupt OOM kills during setup or burst conditions while still keeping memory pressure visible.
```

## Runtime Directories

Created:

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
drwx------ root:root /srv/cybervpn/env
drwx------ root:root /srv/cybervpn/secrets
drwxr-xr-x root:root /srv/cybervpn
drwxr-xr-x root:root /srv/cybervpn/backups
drwxr-xr-x root:root /srv/cybervpn/compose
drwxr-xr-x root:root /srv/cybervpn/evidence
drwxr-xr-x root:root /srv/cybervpn/logs
drwxr-xr-x root:root /srv/cybervpn/releases
drwxr-xr-x root:root /srv/cybervpn/runbooks
```

Baseline runbook:

```text
/srv/cybervpn/runbooks/STAGE1_RENT_02_BASELINE.md
```

## Active Services

```text
ssh: active
fail2ban: active
docker: active
containerd: active
systemd-journald: active
```

## Not Done In This Stage

- No application containers deployed.
- No production secrets written.
- No DNS changed.
- No Caddy/Nginx edge configured.
- No PostgreSQL/Valkey/Remnawave runtime started.
- No public registration/payment/provisioning enabled.

## Residual Notes

1. `root` key-only SSH remains allowed for bootstrap; later hardening can move to `deploy`-only after emergency access is proven.
2. UFW allows `80/443`, but no service listens on those ports yet.
3. Docker published ports must be reviewed carefully during compose deployment because Docker can bypass UFW expectations.
4. Provider-side firewall should mirror the same minimal inbound model: `22`, `80`, `443` only for `prod-app-1`.

## Verification

Server-side verification passed:

```text
deploy key-only SSH works
root key-only SSH works
deploy sudo works
sshd -T shows password/kbd auth disabled
ufw status active
fail2ban sshd jail active
apt timers enabled
Docker Engine and Compose installed
Docker live-restore enabled
swap active
/srv/cybervpn directories created
```

Post-setup reboot verification:

```text
checked_at=2026-05-19T16:53:23Z
reboot_required=no
deploy SSH works
deploy sudo works
ssh=active
fail2ban=active
docker=active
containerd=active
systemd-timesyncd=active
unattended-upgrades=active
systemd-journald=active
UFW remains active after reboot
Docker live_restore=true after reboot
/swapfile 4G active after reboot
only SSH and loopback DNS listeners are active before app deployment
```

Local documentation hygiene after writing this evidence:

```text
git diff --check
targeted secret-pattern scan
targeted dangerous static-pattern scan
```
