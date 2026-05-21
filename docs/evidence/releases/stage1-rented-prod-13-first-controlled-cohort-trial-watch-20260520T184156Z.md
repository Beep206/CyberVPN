# STAGE1-RENT-13 First Controlled Beta Cohort Trial Run And Support Watch

Date: `2026-05-20T18:41:56Z`

Stage: `S1 - Controlled Public Beta`

Scope: first owner/internal controlled beta trial run with live Telegram-linked user, Remnawave provisioning, config delivery, real VPN client connect and support/observability watch.

Owner: `@Sasha_Beep`

## Result

```text
PASS_WITH_HOTFIXED_TRIAL_CONFIG_DELIVERY
```

Stage 1 remains approved for owner/internal and very small manually controlled trial-only cohort expansion.

Stage 1 is still not approved for public global registration, paid beta users, generic payments/CryptoBot public checkout, referrals, promo codes, gift codes, checkout discounts or add-ons.

## Cohort Boundary

The first RENT-13 cohort used one Telegram-linked owner/internal mobile user.

No public registration expansion was performed. No paid checkout was enabled.

No raw Telegram ID, JWT, VLESS link, subscription URL, Remnawave token or payment secret is stored in this document.

## Runtime Safety Gates

Production runtime image tag after the RENT-13 hotfix:

```text
CYBERVPN_IMAGE_TAG=stage1-rent13b-config-delivery-20260520t183430
```

Observed safety state:

| Gate | State |
|---|---|
| Generic payments | `PAYMENTS_ENABLED=false` |
| CryptoBot generic checkout | `CRYPTOBOT_ENABLED=false` |
| Telegram Stars surface gate | `TELEGRAM_STARS_ENABLED=true` |
| Trial provisioning | `STAGE1_TRIAL_PROVISIONING_ENABLED=true` |
| Public registration | `REGISTRATION_ENABLED=false` |
| Referral / promo / gift flows | disabled by Stage 1 policy |

HTTP/3/QUIC remains enabled on the edge. UDP `443` is still published by Caddy and was not disabled during this step.

## Production Health

All Stage 1 app/control-plane containers on `prod-app-1` were running and healthy after the hotfix deploy:

- frontend;
- admin;
- backend;
- Telegram bot;
- worker;
- scheduler;
- PostgreSQL;
- Valkey;
- Remnawave;
- Remnawave PostgreSQL/Valkey;
- PostgreSQL and Redis exporters.

Public probes from `prod-app-1` returned:

| Target | Result |
|---|---:|
| `https://api.cyber-vpn.net/health` | `200` |
| `https://api.cyber-vpn.net/api/v1/plans/?channel=miniapp` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/plans` | `200` |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200` |

## Blockers Found And Fixed

### Blocker 1: Telegram/Mini App Trial Activation Did Not Pass Provisioning Gateway

The general backend trial endpoint already used the Stage 1 Remnawave provisioning gateway, but these Telegram surfaces did not:

- `POST /api/v1/miniapp/trial/activate`;
- `POST /api/v1/telegram/bot/user/{telegram_id}/trial/activate`.

Risk:

```text
Telegram or Mini App trial could become active in CyberVPN DB without creating VPN access in Remnawave.
```

Fix:

- added Stage 1 trial provisioning gateway dependency to Mini App trial activation;
- added Stage 1 trial provisioning gateway dependency to Telegram Bot trial activation;
- passed the gateway into `ActivateTrialUseCase`.

Intermediate deployed backend tag:

```text
stage1-rent13-trial-provisioning-surfaces-20260520t182838
```

### Blocker 2: Telegram Bot Config Delivery Ignored Local Remnawave UUID

After trial provisioning, CyberVPN stored the Remnawave user UUID and subscription URL on `mobile_users`, but the Telegram Bot config endpoint tried to find the user by Telegram ID through Remnawave first.

Risk:

```text
Trial user could have real Remnawave access but Telegram Bot would still return 404 / no config.
```

Fix:

- Mini App config now prefers `mobile_user.remnawave_uuid` before Telegram-ID lookup;
- Telegram Bot config now prefers `mobile_user.remnawave_uuid`;
- Telegram Bot config now falls back to stored `mobile_user.subscription_url` if Remnawave Telegram-ID lookup returns no user.

Final deployed backend tag:

```text
stage1-rent13b-config-delivery-20260520t183430
```

Files changed:

- `backend/src/presentation/api/v1/miniapp/routes.py`;
- `backend/src/presentation/api/v1/telegram/routes.py`;
- `backend/tests/security/test_stage1_trial_provisioning.py`;
- `backend/tests/unit/presentation/api/v1/miniapp/test_routes.py`.

## Tests

Targeted local tests:

```text
cd backend
.venv/bin/pytest tests/security/test_stage1_trial_provisioning.py tests/unit/presentation/api/v1/miniapp/test_routes.py -q --no-cov
```

Result:

```text
28 passed in 0.35s
```

`--no-cov` was used for the targeted suite because the full repository coverage threshold is unrelated to this runtime hotfix.

Targeted lint:

```text
cd backend
.venv/bin/ruff check src/presentation/api/v1/miniapp/routes.py src/presentation/api/v1/telegram/routes.py tests/security/test_stage1_trial_provisioning.py tests/unit/presentation/api/v1/miniapp/test_routes.py
```

Result:

```text
All checks passed.
```

## Trial Activation Proof

Protected Telegram Bot trial activation/recheck for the owner/internal Telegram-linked user returned a safe active state:

```json
{
  "eligible": false,
  "reason": "already_used",
  "is_trial_active": true,
  "days_remaining": 2,
  "duration_days": 3,
  "trial_start_present": true,
  "trial_end_present": true
}
```

Interpretation:

```text
The owner/internal user has an active trial and duplicate activation is safely rejected as already_used.
```

## Database State After Trial Run

Redacted production counts:

```text
mobile_users_total=1
trial_active_users=1
trial_used_users=1
remnawave_linked_users=1
subscription_url_present=1
service_identities_total=0
entitlement_grants_total=0
device_credentials_total=0
payments_total=0
payment_attempts_total=0
customer_staff_notes_total=0
notification_queue_total=0
```

Operational note:

```text
For this Telegram trial path, S1 currently relies on mobile_users.remnawave_uuid and mobile_users.subscription_url as the delivery bridge.
Canonical service identity / entitlement / device credential rows are still not populated by this path and should be tracked as S1 hardening, not as a trial-only launch blocker.
```

## Config Delivery Proof

Protected Telegram Bot config endpoint after the hotfix:

```json
{
  "http_code": 200,
  "client_type": "vless",
  "config_present": true,
  "config_length": 267
}
```

No raw config was printed or stored in repository evidence.

## Client Connect Proof

An ephemeral Xray client container was started on `prod-app-1` using the current owner/internal trial config.

The raw client config was stored only in a temporary `.secret` file on `prod-app-1` and was deleted after the proof.

Server evidence directory:

```text
/srv/cybervpn/evidence/rent13-owner-client-connect-20260520T184250Z
```

Redacted result:

```json
{
  "xray_client_container_running": true,
  "direct_ip_present": true,
  "proxy_ip_present": true,
  "proxy_egress_matches_node": true,
  "direct_and_proxy_differ": true,
  "node_ip_expected": "77.90.13.29",
  "result": "success"
}
```

Cleanup:

```text
secret_cleanup=passed
```

No ephemeral Xray client container remained running after the proof.

## Observability Watch

Home Prometheus Stage 1 user-path probes:

| Job | Result |
|---|---|
| `blackbox-stage1-public-web` | all configured public web/API/admin/status/Mini App probes green |
| `stage1-vpn-node-tcp` | `de-1.cyber-vpn.org:443` and `:8443` green |

Active Stage 1-specific firing alerts:

```text
0
```

General home ops firing alerts:

| Alert | Severity | Impact |
|---|---|---|
| `CyberVPNSwapInUse` | warning | home observability host warning only |
| `CyberVPNSwapUsageAbove1GiB` | warning | home observability host warning only |

Home server resource snapshot:

```text
RAM available: 17 GiB
Swap used: 15 GiB of 31 GiB
Root disk: 10% used
/srv/storage: 1% used
```

Decision:

```text
Do not block trial-only cohort on home swap warning, because customer runtime is on rented infrastructure.
Track and tune home observability memory/swap before widening observability retention, GitLab load or larger beta support watch.
```

## Support Watch

No payment support events were expected because paid runtime remains disabled.

No orphan payment queue items exist.

No customer staff notes or notification queue items were created during this first owner/internal trial proof.

Backend logs from the final post-hotfix window showed no new error/exception/traceback entries matching the watched patterns.

## Acceptance Result

RENT-13 acceptance is met for a trial-only owner/internal cohort:

- Telegram-linked user exists;
- trial is active;
- Remnawave UUID and subscription URL are present;
- Telegram Bot config delivery returns usable config;
- real Xray client connect through the production VPN node works;
- public web/API/admin/Mini App probes are green;
- VPN node TCP probes are green;
- Stage 1-specific firing alerts are zero;
- paid/growth/public-registration gates remain closed.

## Remaining Restrictions

Do not open paid beta yet.

Do not open global public registration yet.

Do not enable generic CryptoBot checkout until real invoice -> provider callback -> idempotency -> provisioning -> reconciliation evidence is captured.

Do not run non-node workloads on `prod-vpn-node-1`.

Do not disable HTTP/3/QUIC on the rented edge.

## Recommended Next Stage

```text
STAGE1-RENT-14: Owner Device Validation And Cohort-2 Trial Expansion
```
