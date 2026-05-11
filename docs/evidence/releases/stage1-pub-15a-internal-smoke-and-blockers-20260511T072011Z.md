# STAGE1-PUB-15A Internal Smoke And Launch Blocker Closure Evidence

Date: 2026-05-11T07:20:11Z

Stage: `STAGE1-PUB-15A`

Result:

```text
PASS for internal smoke.
NO-GO for external beta users.
```

## Purpose

This gate follows `STAGE1-PUB-15`.

It proves that the public-domain runtime can be smoked internally while keeping user-facing launch blockers closed and visible.

This gate does not enable:

- public registration;
- trial provisioning for users;
- paid checkout;
- paid provisioning;
- external beta invitations;
- public launch announcement.

## Runtime Smoke Result

Stage 1 containers:

```text
cybervpn-admin                  running   healthy
cybervpn-backend                running   healthy
cybervpn-frontend               running   healthy
cybervpn-postgres               running   healthy
cybervpn-postgres-exporter      running   healthy
cybervpn-redis-exporter         running   healthy
cybervpn-remnawave              running   healthy
cybervpn-remnawave-node-local   running   healthy
cybervpn-remnawave-postgres     running   healthy
cybervpn-remnawave-valkey       running   healthy
cybervpn-scheduler              running   healthy
cybervpn-telegram-bot           running   healthy
cybervpn-valkey                 running   healthy
cybervpn-worker                 running   healthy
```

Internal container/host HTTP smoke:

```text
200 http://127.0.0.1:18080/health
404 http://127.0.0.1:18080/ready
200 http://127.0.0.1:18088/health
200 http://127.0.0.1:13006/health
200 http://127.0.0.1:13000/en-EN/status
200 http://127.0.0.1:13001/ru-RU/login
```

Interpretation:

- app health, bot health, Remnawave health, frontend and admin runtime are reachable;
- `/ready` is not currently exposed on the backend direct port and returns `404`; this is not treated as a blocker because public `api.cyber-vpn.net/healthz` and backend `/health` are healthy.

Public smoke inherited from `STAGE1-PUB-15`:

```text
200 https://cyber-vpn.net/en-EN/status
200 https://cyber-vpn.net/ru-RU/privacy-policy
200 https://admin.cyber-vpn.net/ru-RU/login
200 https://api.cyber-vpn.net/healthz
301 https://cyber-vpn.org/en-EN/status
301 https://admin.cyber-vpn.org/ru-RU/login
```

## Runtime Flags

Backend:

```text
REGISTRATION_ENABLED=false
REGISTRATION_INVITE_REQUIRED=true
PAYMENTS_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
STAGE1_TRIAL_PROVISIONING_ENABLED=false
STAGE1_PAID_PROVISIONING_ENABLED=false
REFERRAL_ENABLED=false
PROMO_CODES_ENABLED=false
GIFT_CODES_ENABLED=false
CHECKOUT_CODE_DISCOUNTS_ENABLED=false
ADMIN_2FA_REQUIRED=true
```

Telegram bot:

```text
TRIAL_ENABLED=true
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=false
REFERRAL_ENABLED=false
BOT_MODE=webhook
WEBHOOK_URL=https://api.cyber-vpn.net
WEBHOOK_PATH=/webhook/telegram
```

Interpretation:

- registration is closed;
- payments are closed;
- backend trial provisioning is closed;
- backend paid provisioning is closed;
- Telegram bot trial UI is not enough to issue access because backend provisioning is closed;
- referrals, promo/gift flows and checkout discounts are closed;
- admin 2FA is required.

## Safety Probes

Public registration probe:

```text
POST https://cyber-vpn.net/api/v1/auth/register
HTTP 403
code=REGISTRATION_DISABLED
message=Public registration is currently paused.
channel=web_password
```

CryptoBot provider auth probe:

```text
cryptobot_ok=false
cryptobot_error_code=401
cryptobot_error_name=UNAUTHORIZED
```

Decision:

- paid checkout must remain disabled;
- no paid beta may start until the provider account/token/callback path is proven.

Support mailbox DNS:

```text
cyber-vpn.net mx_records=0 dmarc_records=0
cyber-vpn.org mx_records=0 dmarc_records=0
```

Decision:

- email-only support is not proven;
- Telegram/on-call support remains the only proven support path for internal smoke;
- configure MX/SPF/DKIM/DMARC before relying on support/refund email for external users.

## Telegram Bot Smoke

Telegram webhook info was checked from the bot container without printing token values:

```text
telegram_get_webhook_info=true
telegram_webhook_url_set=true
telegram_pending_update_count=0
telegram_last_error_present=false
telegram_allowed_updates_count=3
```

Decision:

- Telegram webhook is configured and clean for internal smoke;
- bot payment flows remain disabled;
- bot trial flow must not be represented as user-ready until backend trial provisioning and production node evidence exist.

## Observability Smoke

Prometheus `up` showed expected Stage 1 and home observability targets as `1`, including:

```text
cybervpn-local-backend
cybervpn-telegram-bot
cybervpn-worker
postgres
redis
remnawave
blackbox-stage1-public-web
node-exporter
grafana
loki
alertmanager
```

Remnawave Stage 1 recording rule:

```text
stage1:remnawave_healthy_nodes:current=1
```

Payment/provisioning recording rules:

```text
stage1:payment_reconciliation_launch_blocked:current=no_data
stage1:paid_but_no_access_oldest_age_minutes:current=no_data
```

Interpretation:

- Remnawave control-plane and lab node are visible;
- payment/provisioning business metrics remain unpopulated because paid/provisioning flows are intentionally disabled;
- this is acceptable for internal smoke but not enough for user cohort success metrics.

Active Alertmanager alerts:

```text
CyberVPNSwapInUse warning active
CyberVPNSwapUsageAbove1GiB warning active
```

Decision:

- warnings do not block internal smoke;
- review memory/swap pressure before external beta users.

## Dirty Worktree / Release Control

Current repository state summary:

```text
dirty_entries=262
tracked_modified=170
untracked=92
```

Current release-control interpretation:

- runtime is using `stage1-beta-rc.2`;
- Git tag at current checked commit remains `stage1-beta-rc.1`;
- broad dirty worktree remains a launch-control risk;
- do not expand a cohort until the approved S1 snapshot is committed and tagged.

## Launch Blocker Closure Status

| Blocker | Current evidence | Status |
|---|---|---:|
| Internal public-domain smoke | Public/internal routes, containers, Telegram webhook and Prometheus checked | CLOSED for internal smoke |
| Public registration safe pause | `403 REGISTRATION_DISABLED` | CLOSED for safe pause |
| Payments safe pause | `PAYMENTS_ENABLED=false`; CryptoBot `401` | CLOSED for safe pause; BLOCKED for paid beta |
| Trial provisioning safe pause | `STAGE1_TRIAL_PROVISIONING_ENABLED=false` | CLOSED for safe pause; BLOCKED for user trial |
| Paid provisioning safe pause | `STAGE1_PAID_PROVISIONING_ENABLED=false` | CLOSED for safe pause; BLOCKED for paid users |
| User-facing production VPN node | only lab home-server node is proven | OPEN P0 |
| QR/subscription URL/config delivery | requires production node and provisioning flags | OPEN P0 |
| Real client connection evidence | requires production node | OPEN P0 |
| Payment provider proof | CryptoBot returns `401` | OPEN P0 for paid beta |
| Immutable `stage1-beta-rc.2` Git tag | not created from current dirty tree | OPEN P1 |
| Support/refund email DNS | no MX/DMARC records | OPEN P1 |
| Host swap warnings | 2 active warning alerts | OPEN P2 |

## Decision

Internal smoke may continue.

External beta users must not be invited yet.

The next recommended blocker to close without spending on hosting is release control:

```text
STAGE1-PUB-15B: Approved Snapshot Commit And Immutable RC2 Tag
```

The next blocker to close for real users is:

```text
STAGE1-PUB-15C: Production VPN Node And Trial Provisioning Proof
```

## Allowed Next Actions

Allowed now:

1. Commit and tag the approved S1 snapshot.
2. Keep current runtime online for owner-only smoke.
3. Review active swap warnings.
4. Prepare DNS/mail records for support/refund addresses.
5. Prepare first production VPN node.
6. Replace/fix CryptoBot token or keep paid beta explicitly out of scope.

Not allowed yet:

1. Enable public registration.
2. Enable payments.
3. Enable trial provisioning for outside users.
4. Invite real beta users.
5. Announce public beta.
6. Promise VPN access through the bot/site.

## Cleanup

Temporary remote scripts created for this gate were removed:

```text
temp_scripts_removed=yes
blocker_temp_script_removed=yes
```

## Final Hygiene

Post-write checks:

```text
git diff --check: pass
targeted secret scan over STAGE1-PUB-15A docs: no matches
targeted static-dangerous-pattern scan over STAGE1-PUB-15A docs: no matches
npm audit --omit=dev --audit-level=high: exit 0, no high/critical findings
```

Residual dependency note:

```text
2 moderate postcss/Next.js audit findings remain.
npm audit fix --force proposes a breaking Next.js downgrade and was not applied.
```
