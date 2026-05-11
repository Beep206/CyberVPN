# STAGE1-PUB-15C Production VPN Node And Trial Provisioning Proof Evidence

Date: 2026-05-11T07:27:05Z

Stage: `STAGE1-PUB-15C`

Result:

```text
BLOCKED for production VPN node and user-facing trial provisioning proof.
PASS for no-cost Remnawave control-plane, lab-node and safety preflight.
```

## Purpose

This gate is intended to prove that Stage 1 has a real, always-on production VPN exit node and that a beta user can receive working trial access through the CyberVPN flow.

For Stage 1 this gate must not be treated as complete until it proves the full path:

```text
registration / controlled beta identity
-> trial activation
-> CyberVPN provisioning
-> Remnawave user/profile update
-> QR / subscription URL / config delivery
-> real client connection
-> support/admin visibility
```

## What Was Checked

No-cost checks were performed against the current `cybervpn-h` runtime without creating users, enabling provisioning or starting paid/trial access for external users.

Runtime containers:

```text
cybervpn-frontend              Up About an hour (healthy)
cybervpn-admin                 Up 8 hours (healthy)
cybervpn-backend               Up 8 hours (healthy)
cybervpn-scheduler             Up 8 hours (healthy)
cybervpn-worker                Up 8 hours (healthy)
cybervpn-telegram-bot          Up 8 hours (healthy)
cybervpn-postgres              Up 8 hours (healthy)
cybervpn-valkey                Up 8 hours (healthy)
cybervpn-remnawave-node-local  Up 10 hours (healthy)
cybervpn-remnawave             Up 10 hours (healthy)
cybervpn-remnawave-postgres    Up 10 hours (healthy)
cybervpn-remnawave-valkey      Up 10 hours (healthy)
```

Remnawave health:

```text
GET http://127.0.0.1:13006/health -> 200
{"status":"ok","info":{"database":{"status":"up"}},"error":{},"details":{"database":{"status":"up"}}}
```

Prometheus:

```text
up{job="remnawave"} = 1
stage1:remnawave_healthy_nodes:current = 1
```

Remnawave node inventory was queried from the backend container with the token kept inside the container environment and not printed:

```text
remnawave_nodes_status=200
remnawave_nodes_count=1
node name=stage1-lab-home-node address_class=internal-hostname port=22230 connected=True connecting=False disabled=False
```

Public route smoke:

```text
GET https://api.cyber-vpn.net/healthz -> 200
GET https://api.cyber-vpn.net/api/sub -> 404 from Remnawave route
GET https://cyber-vpn.net/en-EN/status -> 200
GET https://admin.cyber-vpn.net/ru-RU/login -> 200
```

Safety flags:

```text
REGISTRATION_ENABLED=false
PAYMENTS_ENABLED=false
STAGE1_TRIAL_PROVISIONING_ENABLED=false
STAGE1_PAID_PROVISIONING_ENABLED=false
REFERRAL_ENABLED=false
PROMO_CODES_ENABLED=false
GIFT_CODES_ENABLED=false
```

Telegram bot flags:

```text
BOT_MODE=webhook
CRYPTOBOT_ENABLED=false
REFERRAL_ENABLED=false
TELEGRAM_STARS_ENABLED=false
TRIAL_ENABLED=true
WEBHOOK_PATH=/webhook/telegram
WEBHOOK_URL=https://api.cyber-vpn.net
```

Public registration safety probe:

```text
POST https://cyber-vpn.net/api/v1/auth/register
HTTP 403
code=REGISTRATION_DISABLED
message=Public registration is currently paused.
channel=web_password
```

Provisioning and paid-but-no-access recording rules:

```text
stage1:provisioning_success_ratio:current = no_data
stage1:paid_but_no_access_oldest_age_minutes:current = no_data
```

Interpretation: there is no live user provisioning data yet because provisioning and payments are intentionally disabled.

## Production Proof Status

| Requirement | Status | Evidence / Reason |
|---|---:|---|
| Remnawave control-plane healthy | PASS | `/health` returns 200 and Prometheus `up{job="remnawave"}=1` |
| At least one node connected | PASS for lab only | `stage1-lab-home-node` is connected |
| User-facing production VPN exit node | BLOCKED | only an internal lab/home node is proven |
| Production node inventory | BLOCKED | no rented/always-on external production node is present in evidence |
| Production node firewall/allowlist evidence | BLOCKED | requires real node IP/provider/network boundary |
| Trial provisioning enabled for controlled test account | BLOCKED | `STAGE1_TRIAL_PROVISIONING_ENABLED=false` |
| Trial creates/updates Remnawave user | BLOCKED | must not run against lab-only user-facing path |
| QR/subscription URL/config generated | BLOCKED | requires approved provisioning path |
| Real client connection evidence | BLOCKED | requires external production VPN node |
| Credential regeneration proof | BLOCKED | requires production node and disposable beta identity |
| Expiry/grace disable proof | BLOCKED | requires production node and disposable beta identity |
| Median/p95 `trial/pay -> VPN ready` latency sample | BLOCKED | requires live provisioning events |

## Decision

`STAGE1-PUB-15C` is not complete for controlled public beta users.

The current lab node is useful for control-plane smoke, metrics and route validation. It must not be used as the production proof for public beta access because it is tied to the home-server environment and is not a real customer VPN exit node.

Keep the following disabled until this gate is rerun with a real production node:

```text
REGISTRATION_ENABLED=false
PAYMENTS_ENABLED=false
STAGE1_TRIAL_PROVISIONING_ENABLED=false
STAGE1_PAID_PROVISIONING_ENABLED=false
```

`TRIAL_ENABLED=true` in the Telegram bot is acceptable only as UI/runtime smoke while backend provisioning remains disabled. It must not be presented as user-ready.

## Required Actions To Close This Gate Later

1. Provision at least one rented, always-on external VPN node.
2. Record safe node inventory: provider, region, OS, Docker version, Remnawave Node version, public IP redacted if needed, and owner.
3. Configure firewall so only the intended Remnawave control-plane path can reach the node control port.
4. Register the node in Remnawave with a production label/name that is not `lab`, `local`, `home` or `test`.
5. Prove the node is connected in Remnawave API and visible in Prometheus.
6. Enable `STAGE1_TRIAL_PROVISIONING_ENABLED=true` only for a disposable controlled beta identity or a temporary smoke window.
7. Run trial activation from the actual CyberVPN flow.
8. Prove Remnawave user/profile creation or update.
9. Prove QR/subscription URL/config delivery.
10. Import the config into a real client and capture redacted connection evidence.
11. Prove credential regeneration.
12. Prove expiry/grace disable behavior.
13. Capture median and p95 `trial/pay -> VPN ready` latency from the smoke events.
14. Re-disable trial provisioning if the production cohort is not starting immediately.

## Explicitly Not Performed

- No external server was purchased or provisioned.
- No production VPN node was deployed.
- No backend trial provisioning was enabled.
- No paid provisioning was enabled.
- No beta user access was created.
- No token, password, API key or private node secret was printed into evidence.

## Verification

```text
git diff --check
PASS
```

```text
targeted secret scan over this evidence file and the Stage 1 deployment plan
PASS: no matches
```

```text
targeted static scan over this evidence file and the Stage 1 deployment plan
PASS: no dangerous execution-pattern matches
```

```text
npm audit --omit=dev --audit-level=high
PASS: no high/critical production npm audit blocker
NOTE: audit reports 2 moderate Next/PostCSS advisories; the suggested forced fix would install an incompatible/breaking Next version and was not applied.
```

## Next Step

If the goal is to continue without infrastructure spend, do:

```text
STAGE1-PUB-15B: Approved Snapshot Commit And Immutable RC2 Tag
```

If the goal is to close the real-user VPN blocker, first provision a rented production VPN node and then rerun:

```text
STAGE1-PUB-15C: Production VPN Node And Trial Provisioning Proof
```
