# CyberVPN Partner Lab

This directory contains off-by-default Stage 3 partner/reseller lab infrastructure for the home server.

The lab must not run as part of the default S1/S2 stack. Start it only for controlled staging, sandbox, or evidence work.

## Services

| Service | Purpose | Public by default |
|---|---|---|
| `partner-webhook-test-receiver` | receives partner webhook test payloads and writes redacted evidence | no, bound to `127.0.0.1:9088` |

## Start

```bash
cd /srv/cybervpn-h/compose/partner-lab
sudo docker compose --profile manual up -d partner-webhook-test-receiver
```

## Stop

```bash
cd /srv/cybervpn-h/compose/partner-lab
sudo docker compose --profile manual down
```

## Evidence

Webhook receiver evidence is stored under:

```text
/srv/storage/evidence/settlements/webhook-receiver
```

Do not publish this service through Caddy until DNS, HMAC signing, rate-limits, and evidence retention have been reviewed.
