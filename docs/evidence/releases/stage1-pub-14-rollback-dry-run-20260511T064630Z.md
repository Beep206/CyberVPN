# STAGE1-PUB-14 Rollback Dry-Run And Kill Switch Evidence

Date: 2026-05-11T06:46:30Z

Stage: `STAGE1-PUB-14`

Result: PASS.

Server: `10.10.10.34` / `cybervpn-h-ops`

Current runtime tag: `stage1-beta-rc.2`

Rollback target: previous immutable Stage 1 images available on the deployment host.

## Rollback Dry-Run

The rollback drill was intentionally non-disruptive. It did not recreate live containers.

Mechanism:

1. Create a temporary Docker Compose override.
2. Point runtime services to known rollback image tags.
3. Validate merged Compose config.
4. Verify rollback images exist locally.
5. Remove the temporary override.

Compose validation:

```text
rollback_override_config=valid
```

Rollback image availability:

```text
local/cybervpn-backend:stage1-beta-rc.1 sha256:a42197ab5163aea18eba2c97f03899626fc574322749aacaa5d6ac445afc524a
local/cybervpn-frontend:stage1-beta-rc.1 sha256:eadf9769f1c70c9ba73527afadda34101a181f48feb6d8acf202a0a1387d1142
local/cybervpn-admin:stage1-beta-rc.1 sha256:cfd1c27e4d3ab1cde057ca1b28c847bc504fc1c89111f4e74d50048a6a5b66b1
local/cybervpn-telegram-bot:stage1-beta-rc.1 sha256:28c2669018d45fefb5083a2ed399972a52297980b29d631ff71e6af0122c848a
local/cybervpn-task-worker:stage1-beta-rc.2 sha256:9a7007ff31daa6a675d4a4a65cb81c8632aca05f28761128a23653f80d247368
```

Note:

- `cybervpn-task-worker` currently has no separate `stage1-beta-rc.1` image on the deployment host.
- The rollback target for `worker` and `scheduler` is therefore the current known-good `stage1-beta-rc.2` image.
- Before a larger cohort, keep at least two immutable worker images on the deployment host or in GitLab Registry.

## Rollback Commands

Emergency rollback command pattern:

```bash
cd /srv/cybervpn-h/compose/app
sudo docker compose -f docker-compose.yml -f /path/to/rollback.override.yml config --quiet
sudo docker compose -f docker-compose.yml -f /path/to/rollback.override.yml up -d --no-deps --force-recreate \
  cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-telegram-bot cybervpn-worker cybervpn-scheduler
sudo docker compose ps
curl -k -I https://cyber-vpn.net/en-EN/status
curl -k -I https://admin.cyber-vpn.net/ru-RU/login
curl -k -I https://api.cyber-vpn.net/healthz
```

For this gate, only the config validation and image availability parts were executed. Runtime recreation was not executed because the live stack was healthy and this was a dry-run gate.

## Kill Switch Dry-Run

A temporary no-code Docker Compose override was validated for emergency pause controls:

```text
kill_switch_override_config=valid
```

The override can set these values without code changes:

| Service | Kill switch |
|---|---|
| backend | `REGISTRATION_ENABLED=false` |
| backend | `PAYMENTS_ENABLED=false` |
| backend | `PAYMENT_AUTORENEWAL_ENABLED=false` |
| backend | `STAGE1_TRIAL_PROVISIONING_ENABLED=false` |
| backend | `STAGE1_PAID_PROVISIONING_ENABLED=false` |
| worker/scheduler | `STAGE1_TRIAL_PROVISIONING_ENABLED=false` |
| worker/scheduler | `STAGE1_PAID_PROVISIONING_ENABLED=false` |
| Telegram bot | `TRIAL_ENABLED=false` |
| Telegram bot | `CRYPTOBOT_ENABLED=false` |
| Telegram bot | `TELEGRAM_STARS_ENABLED=false` |
| Telegram bot | `REFERRAL_ENABLED=false` |

## Current Runtime Switch State

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
```

Telegram bot:

```text
TRIAL_ENABLED=true
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=false
REFERRAL_ENABLED=false
```

Interpretation:

- New public registration is currently paused.
- New paid flows are currently paused.
- Paid autoprolongation is currently paused.
- Backend trial and paid provisioning are currently paused.
- Telegram bot trial UI is currently enabled, but backend trial provisioning is still paused.
- A hard bot-level trial pause can be applied with `TRIAL_ENABLED=false` plus bot recreate, without code changes.

## Public Registration Kill Switch Proof

Public registration probe:

```text
POST https://cyber-vpn.net/api/v1/auth/register
HTTP 403
code=REGISTRATION_DISABLED
message=Public registration is currently paused.
channel=web_password
```

## Local Kill Switch Tests

Command:

```bash
cd backend
uv run pytest tests/security/test_registration_security.py tests/security/test_stage1_payment_runtime_kill_switch.py -q --no-cov
```

Result:

```text
11 passed in 0.29s
```

## Runtime Health After Rollback/Kill Switch Drill

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

## Final Hygiene

Repository/documentation checks after writing this evidence:

```text
git diff --check: pass
targeted secret scan over STAGE1-PUB-14 evidence: no matches
targeted static-dangerous-pattern scan over STAGE1-PUB-14 evidence: no matches
remote temporary script removed: yes
npm audit --omit=dev --audit-level=high: exit 0, no high/critical findings
```

Residual dependency note:

```text
2 moderate postcss/Next.js audit findings remain.
npm audit fix --force proposes a breaking downgrade path and was not applied.
```

## Residual Risk

Non-blocking for a small controlled beta:

- rollback was a dry-run, not a live traffic switch;
- worker/scheduler rollback currently points to the current known-good image because no older worker image is present;
- Telegram bot trial hard-pause requires setting `TRIAL_ENABLED=false` and recreating the bot container.

Must be improved before a larger cohort:

- retain previous immutable images for every runtime service, including worker/scheduler;
- keep rollback override files in the release evidence pack or GitLab protected release artifacts;
- repeat a full staging rollback that recreates containers and validates health checks end-to-end.
