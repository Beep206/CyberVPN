# Caddy DNS-01 With Cloudflare

## Why

HTTP-01 and TLS-ALPN-01 validation reached Caddy from one Let's Encrypt validator, but secondary validation timed out against `95.82.233.131`. DNS-01 avoids inbound validation entirely by proving control of the DNS zone through Cloudflare TXT records.

## Current Server Preparation

Completed on `10.10.10.34`:

```text
Caddy module installed: dns.providers.cloudflare
Caddy binary backup: /usr/bin/caddy.tmp
Secret env template: /srv/cybervpn-h/secrets/caddy/cloudflare.env.example
Systemd drop-in: /etc/systemd/system/caddy.service.d/10-cloudflare-dns-env.conf
Optional EnvironmentFile: /srv/cybervpn-h/secrets/caddy/cloudflare.env
Caddy systemd ExecStart override removes --environ to avoid logging secrets
Issued certificate: *.h.cyber-vpn.net
```

## Cloudflare Token Required

Create a scoped Cloudflare API token.

Required permissions:

```text
Zone / Zone / Read
Zone / DNS / Edit
```

Zone resources:

```text
Include / Specific zone / cyber-vpn.net
```

## Install Token On Server

On `10.10.10.34`:

```bash
sudo install -d -m 0700 -o root -g root /srv/cybervpn-h/secrets/caddy
sudo nano /srv/cybervpn-h/secrets/caddy/cloudflare.env
sudo chmod 0600 /srv/cybervpn-h/secrets/caddy/cloudflare.env
```

File content:

```text
CLOUDFLARE_API_TOKEN=token_value_here
```

Do not commit this file to git.

## Caddyfile Change

The `h.cyber-vpn.net` routes use one wildcard certificate instead of separate certificates per hostname.

TLS snippet:

```caddyfile
(cybervpn_tls) {
	tls {
		dns cloudflare {env.CLOUDFLARE_API_TOKEN}
		propagation_timeout 5m
	}
}
```

Site routing pattern:

```caddyfile
*.h.cyber-vpn.net {
	import cybervpn_tls
	import standard_proxy

	@gitlab host gitlab.h.cyber-vpn.net
	handle @gitlab {
		reverse_proxy http://127.0.0.1:8081
	}

	handle {
		respond "not found" 404
	}
}
```

Then validate and reload:

```bash
sudo sh -c 'set -a; . /srv/cybervpn-h/secrets/caddy/cloudflare.env; set +a; caddy validate --config /etc/caddy/Caddyfile'
sudo systemctl restart caddy
sudo systemctl status caddy --no-pager
```

## Verification

Verify the wildcard certificate:

```bash
for h in gitlab.h.cyber-vpn.net registry.h.cyber-vpn.net grafana.h.cyber-vpn.net sentry.h.cyber-vpn.net prometheus.h.cyber-vpn.net loki.h.cyber-vpn.net alerts.h.cyber-vpn.net uptime.h.cyber-vpn.net; do
  curl -sS --connect-to "$h:443:127.0.0.1:443" -o /dev/null -w "$h http=%{http_code} verify=%{ssl_verify_result}\n" "https://$h/"
done
journalctl -u caddy --since '2026-05-09 16:30 UTC' --no-pager | grep -E 'wildcard|certificate obtained successfully|challenge failed'
```

Expected for undeployed local upstreams:

```text
certificate obtained successfully for *.h.cyber-vpn.net
http=502 verify=0
```

`502` is expected until the service behind the reserved local port is deployed.

## Operational Notes

- The current token should stay scoped only to `cyber-vpn.net`.
- Rotate the Cloudflare token if it was exposed in chat, shell history, screenshots, or logs.
- After token rotation, update `/srv/cybervpn-h/secrets/caddy/cloudflare.env` and restart Caddy.
