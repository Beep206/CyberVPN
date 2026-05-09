# Stage 1 DNS / TLS Contract

This directory contains the no-secret local contract for `S1-INFRA-004`.

The contract records approved Stage 1 domains, canonical redirect behavior, TLS requirements, admin protection requirements and the live evidence commands that must be captured before controlled public beta traffic.

It does not contain Cloudflare zone IDs, API tokens, origin IP addresses, tunnel tokens or certificate private keys.

## Files

| File | Purpose |
|---|---|
| `stage1-dns-tls-contract.json` | Canonical Stage 1 DNS/TLS contract |
| `../../scripts/validate_s1_dns_tls_contract.py` | Static validator for the contract |
| `../tests/test_stage1_dns_tls_contract.py` | Pytest coverage for required DNS/TLS invariants |

## S1 Canonical Hosts

| Host | S1 behavior |
|---|---|
| `cyber-vpn.net` | Primary public site and customer cabinet |
| `www.cyber-vpn.net` | Redirect to `https://cyber-vpn.net` |
| `api.cyber-vpn.net` | Backend API, payment webhooks, Telegram webhook and OAuth callbacks |
| `admin.cyber-vpn.net` | Protected admin canonical host |
| `cyber-vpn.org` | Mirror/redirect to `https://cyber-vpn.net` |
| `www.cyber-vpn.org` | Mirror/redirect to `https://cyber-vpn.net` |
| `admin.cyber-vpn.org` | Redirect to `https://admin.cyber-vpn.net`; no independent admin session |

For S1, status is a route on the primary domain: `https://cyber-vpn.net/status`. A separate `status.cyber-vpn.net` hostname is not required for S1 and should be treated as a later optional change.

## Go-Live Evidence Still Required

Before `stage1-beta-live.N`, attach redacted live evidence for:

- DNS resolution for every required host;
- valid TLS certificate coverage for every required host;
- HTTP to HTTPS redirect behavior;
- `.org` public mirror redirects;
- admin mirror redirect to primary admin;
- public `/status` route;
- admin access protection before login;
- payment/Telegram webhook and OAuth callback paths without interactive browser challenges.

Until that live evidence exists, `S1-INFRA-004` is complete only as a local contract and remains a go-live evidence gap.
