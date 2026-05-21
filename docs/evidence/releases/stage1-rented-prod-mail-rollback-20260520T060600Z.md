# Stage 1 Rented Production Mail Rollback

Date: 2026-05-20T06:06:00Z

## Decision

The temporary Stalwart mail side-track was rolled back. CyberVPN will not run a self-hosted mail server during the immediate Stage 1 deployment path.

Future transactional/support email will be revisited after the core Stage 1 runtime is stable, with Resend as the preferred next candidate.

## Rolled Back

- Removed the active Stalwart Docker container and compose runtime from `prod-app-1`.
- Removed Stalwart local state, secrets and CLI files from `prod-app-1`.
- Removed mail protocol firewall openings:
  - `25/tcp`
  - `465/tcp`
  - `587/tcp`
  - `993/tcp`
  - `995/tcp`
- Restored the pre-mail Caddyfile.
- Restored the pre-mail edge compose network model.
- Removed Cloudflare mail DNS records that were created for the side-track:
  - `mail.cyber-vpn.net`
  - `mta-sts.cyber-vpn.net`
  - `autoconfig.cyber-vpn.net`
  - `autodiscover.cyber-vpn.net`
  - DKIM selectors
  - DMARC
  - MTA-STS
  - SMTP TLS reporting
  - DANE TLSA
  - mail SRV records
  - Stalwart-created CAA records
  - temporary apex MX/SPF
- Returned Cloudflare DNSSEC to `disabled`.

## Current Runtime State

Stage 1 app runtime was started again after rollback:

- `cybervpn-edge-caddy`
- CyberVPN backend
- CyberVPN frontend
- CyberVPN admin
- Telegram bot
- worker
- scheduler
- PostgreSQL
- Valkey
- Remnawave
- exporters

The production VPN node was also started again:

- `cybervpn-remnawave-node`

## Verification

- `prod-app-1` firewall allows only SSH, HTTP and HTTPS after rollback.
- No active Stalwart container remains.
- `/srv/stalwart-mail` is absent.
- Edge health check returns `{"status":"ok","stage":"stage1-rent04","surface":"edge"}`.
- Backend health check returns `{"status":"ok"}`.
- Stage 1 app containers are healthy.
- `mail.cyber-vpn.net`, `_dmarc.cyber-vpn.net`, `_mta-sts.cyber-vpn.net`, `_smtp._tls.cyber-vpn.net` and mail TLSA records return empty DNS responses after rollback.

## Follow-Up

When email becomes launch-critical again, implement it as a separate mail-provider task. Recommended direction:

1. Choose Resend for S1 transactional email.
2. Add only the DNS records required by Resend.
3. Keep support inbox routing separate from application deployment.
4. Do not reintroduce self-hosted mail until the product runtime, payments, VPN provisioning and support operations are stable.
