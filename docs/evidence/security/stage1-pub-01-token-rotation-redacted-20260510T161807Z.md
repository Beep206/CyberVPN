# STAGE1-PUB-01 Runtime Access And Edge Safety Evidence

Date: 2026-05-10 16:18 UTC  
Server: `10.10.10.34`  
Host: `cybervpn-h-ops`  
Scope: secret-file posture, Caddy DNS-01 readiness, Caddy reload, public listener review and operations edge safety.

## Result

Status: **GO to continue deployment prep.**

Owner decision update: setup-key rotation is **not required** for the current controlled/tiny beta. This decision assumes values remain server-side only, file permissions stay locked down, and any future suspected exposure triggers immediate rotation.

The server-side posture is usable for the next preparation step:

- Caddy service is active.
- Caddy validates when its Cloudflare environment file is loaded.
- Caddy reload completed successfully.
- Server firewall allows public `80/tcp` and `443/tcp`; SSH is allowed only from LAN.
- Docker-published management services bind to `127.0.0.1` where they are meant to be routed through Caddy.
- Sensitive env files checked in this step are `0600 root root`.

External provider token rotation was **not** performed in this step because the owner decided it is not required for the current stage. Existing values were not printed or copied into this evidence.

## Commands Run

```bash
ssh beep@10.10.10.34 hostname
sudo systemctl cat caddy
sudo systemctl status caddy --no-pager -l
sudo ufw status verbose
sudo ss -ltnp
docker ps --format '{{.Names}}\t{{.Ports}}'
sudo stat -c '%a %U %G %n' /srv/cybervpn-h/secrets/caddy/cloudflare.env /srv/cybervpn-h/secrets/alertmanager.env /srv/cybervpn-h/secrets/sentry-geoip.env /srv/cybervpn-h/secrets/restic.env /srv/cybervpn-h/secrets/rclone.conf
sudo sh -c 'set -a; . /srv/cybervpn-h/secrets/caddy/cloudflare.env; set +a; caddy validate --config /etc/caddy/Caddyfile'
sudo systemctl reload caddy
curl -k -sS -o /dev/null -w '%{http_code}' https://gitlab.h.cyber-vpn.net/users/sign_in
curl -k -sS -o /dev/null -w '%{http_code}' https://grafana.h.cyber-vpn.net/.well-known/cybervpn-edge-health
curl -k -sS -o /dev/null -w '%{http_code}' https://sentry.h.cyber-vpn.net/_health/
curl -k -sS -o /dev/null -w '%{http_code}' https://prometheus.h.cyber-vpn.net/.well-known/cybervpn-edge-health
```

## Caddy

Systemd Caddy unit includes:

```text
EnvironmentFile=-/srv/cybervpn-h/secrets/caddy/cloudflare.env
ExecStart=/usr/bin/caddy run --config /etc/caddy/Caddyfile
```

Direct `sudo caddy validate --config /etc/caddy/Caddyfile` without loading the environment file reports an empty Cloudflare token. This is expected for a raw shell command and is not the service runtime path.

Validation with the Caddy Cloudflare env file loaded:

```text
Valid configuration
```

Caddy reload:

```text
Reloaded caddy.service - Caddy.
```

Caddy remained active after reload.

## Secret File Posture

Checked files:

```text
600 root root /srv/cybervpn-h/secrets/caddy/cloudflare.env
600 root root /srv/cybervpn-h/secrets/alertmanager.env
600 root root /srv/cybervpn-h/secrets/sentry-geoip.env
600 root root /srv/cybervpn-h/secrets/restic.env
600 root root /srv/cybervpn-h/secrets/rclone.conf
```

Redacted key inventory only:

```text
CLOUDFLARE_API_TOKEN=<redacted>
ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=<redacted>
ALERTMANAGER_TELEGRAM_BOT_TOKEN=<redacted>
ALERTMANAGER_TELEGRAM_CHAT_ID=<redacted>
ALERTMANAGER_BACKUP_EMAIL=<redacted>
ALERTMANAGER_SMTP_FROM=<redacted>
ALERTMANAGER_SMTP_SMARTHOST=<redacted>
ALERTMANAGER_SMTP_HELLO=<redacted>
ALERTMANAGER_SMTP_AUTH_USERNAME=<redacted>
ALERTMANAGER_SMTP_PASSWORD=<redacted>
ALERTMANAGER_SMTP_REQUIRE_TLS=<redacted>
MAXMIND_ACCOUNT_ID=<redacted>
MAXMIND_LICENSE_KEY=<redacted>
MAXMIND_EDITION_IDS=<redacted>
```

## Firewall And Listener Review

UFW:

```text
Default: deny incoming, allow outgoing, deny routed
22/tcp allowed from 10.10.10.0/24 only
80/tcp allowed from anywhere
443/tcp allowed from anywhere
```

Host listeners:

```text
0.0.0.0:22    SSH, gated by UFW to LAN
*:80          Caddy public edge
*:443         Caddy public edge
127.0.0.1:*   GitLab/Grafana/Sentry/Prometheus/Loki/Alertmanager/Uptime/Caddy admin and other local services
```

Docker published ports are either internal container ports or `127.0.0.1` host bindings for services routed through Caddy.

## Public Smoke

Current public/edge smoke:

```text
gitlab.h.cyber-vpn.net/users/sign_in                 200
grafana.h.cyber-vpn.net/.well-known/cybervpn-edge-health 200
sentry.h.cyber-vpn.net/_health/                      200
prometheus.h.cyber-vpn.net/.well-known/cybervpn-edge-health 200
```

## Current Alerts

Prometheus active alerts at review time:

```text
CyberVPNSwapInUse                  warning firing
CyberVPNSwapUsageAbove1GiB         warning firing
Stage1NoHealthyRemnawaveNodes      critical firing
```

Interpretation:

- Swap warning should be reviewed before beta expansion.
- `Stage1NoHealthyRemnawaveNodes` is expected until Stage 1 Remnawave/VPN node deployment.

## External Rotation Decision

| Item | Status | Notes |
|---|---|---|
| Cloudflare DNS token | Rotation not required by owner for current controlled beta | Server env exists and Caddy validates with it loaded. |
| MaxMind license key | Rotation not required by owner for current controlled beta | Server env exists. |
| Telegram alert bot token | Rotation not required by owner for current controlled beta | Alertmanager env exists. |
| Resend API key | Rotation not required by owner for current controlled beta | Alertmanager SMTP env exists. |

## Decision

Proceed to the next deployment-prep step.

Rotation becomes required later if a value is suspected to have leaked, if provider permissions are broadened, if a team member with access leaves, or before moving from controlled beta to a stricter production posture.
