# Stage 1 Protected Ingress Contract

This directory contains the local, no-secret protected ingress contract for S1.

`S1-INFRA-005` is about the boundary between public users/providers and internal CyberVPN services. It does not claim that Cloudflare, another edge provider or a production reverse proxy is already deployed.

## Files

| File | Purpose |
|---|---|
| `stage1-protected-ingress-contract.json` | Machine-readable protected ingress contract |
| `../../scripts/validate_s1_protected_ingress.py` | Static validator for required ingress invariants |
| `../tests/test_stage1_protected_ingress.py` | Pytest coverage for protected ingress rules |

## S1 Public Entrypoints

| Host | S1 behavior |
|---|---|
| `cyber-vpn.net` | Primary public site and customer cabinet |
| `www.cyber-vpn.net` | Redirect to `cyber-vpn.net` |
| `cyber-vpn.org` | Reserved for VPN nodes and future subscription delivery; no customer web mirror |
| `www.cyber-vpn.org` | Not used for S1 customer web |
| `api.cyber-vpn.net` | Controlled backend API, webhooks and OAuth callbacks |
| `admin.cyber-vpn.net` | Protected admin entrypoint only |
| `admin.cyber-vpn.org` | Not used for S1 admin; no independent admin session |

## Required Boundary

- Backend and admin container ports must not be directly public.
- Admin must be gated before login by Cloudflare Access, IP allowlist, private VPN or equivalent.
- Admin still requires backend host guard, mandatory 2FA, RBAC and audit.
- Payment, Telegram and OAuth callbacks must not receive interactive browser challenges.
- Remnawave API, PostgreSQL, Valkey/Redis and observability ports stay private.
- Customer production traffic must not point to staging or home-lab origins.

## Still Required Before Go-Live

Attach redacted evidence for real edge routes, reverse proxy config, origin firewall/security group rules, admin access protection, disabled production docs, CORS/cookie/CSRF behavior, webhook no-challenge behavior, private Remnawave/PostgreSQL/Valkey reachability and ingress rollback controls.
