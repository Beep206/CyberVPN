# Stage 1 Rented Production 15 - Cohort-2 Invite Execution And Support Watch

Date: 2026-05-21 11:57:22 UTC

Status: `STARTED_WAITING_FOR_COHORT2_USER_ACTION`

## Purpose

Start `STAGE1-RENT-15` by issuing a small owner-controlled beta invite pack and confirming that the runtime is safe enough to invite the next tiny cohort.

This is not a public referral/growth launch.

## Scope

Included:

- issue 3 owner-held controlled beta invite codes;
- keep codes short-lived;
- keep `referral`, `promo`, `gift`, `partner`, `payout` and public growth expansion disabled;
- verify production app health;
- verify public endpoint and VPN-node probes;
- open support-watch for the first invited users.

Excluded:

- public referral program;
- partner/reseller flow;
- paid checkout expansion;
- gift/promo code launch;
- automatic cohort widening;
- raw invite code storage in documentation.

## Invite Pack

Owner mobile account:

```text
email=tg157383237@telegram.local
telegram_id=157383237
status=active
```

Created invite pack:

```text
count=3
free_days=7
source=admin_grant
expires_at=2026-05-24 11:54:13 UTC
audit_id=75b5f4cb-47d1-43e9-8fca-e715840b49c5
raw_codes_redacted_in_evidence=true
```

Redacted code fingerprints:

```text
409F****
A21E****
C46C****
```

The full codes were delivered to the owner outside this evidence file and must not be committed to docs or logs.

## Production Verification

Production DB state after issue:

```text
total_invites=3
active_invites=3
first_expiry=2026-05-24 11:54:13 UTC
last_expiry=2026-05-24 11:54:13 UTC
```

Rented production containers:

```text
cybervpn-admin: healthy
cybervpn-backend: healthy
cybervpn-frontend: healthy
cybervpn-postgres: healthy
cybervpn-valkey: healthy
cybervpn-remnawave: healthy
cybervpn-telegram-bot: healthy
cybervpn-worker: healthy
cybervpn-scheduler: healthy
```

Public endpoint probes:

```text
https://cyber-vpn.net/ru-RU: 200
https://cyber-vpn.net/ru-RU/miniapp/home: 200
https://cyber-vpn.net/health: 200
https://cyber-vpn.net/api/v1/status: 200
```

VPN node proof:

```text
de-1.cyber-vpn.org:443: ok
de-1.cyber-vpn.org:8443: ok
```

Home Prometheus watch:

```text
firing_alerts=0
blackbox-stage1-public-web successful targets=8
stage1-vpn-node-tcp successful targets=2
stage1/blackbox up targets=21
```

Recent production backend/bot/worker/scheduler logs:

```text
No recent error/exception/traceback/failed/critical lines matched in the sampled window.
```

## Operational Notes

For S1, invite-code redemption and trial activation are not the same thing:

- trial activation is already proven to provision Remnawave and deliver a VPN config;
- invite-code redemption creates a controlled access entitlement;
- invite-code redemption to Remnawave provisioning must be treated as pending evidence until a real invited user flow proves config delivery.

Recommended support instruction for cohort-2:

```text
1. Invite only 1-3 users.
2. Prefer Telegram Bot/Mini App onboarding.
3. Have each user activate trial first if the goal is immediate VPN access.
4. If a user redeems an invite code and does not receive config, escalate immediately and pause additional invites.
5. Record every activation, no-config state, failed connection and support contact.
```

## Decision

```text
GO to share the 3 owner-held controlled beta invite codes with selected cohort-2 users.
NO-GO for public referral/growth launch.
NO-GO for paid users.
NO-GO for expanding beyond 1-3 users until first invited user evidence is recorded.
```

## Next Required Evidence

Create a follow-up evidence entry after the first invited user attempts onboarding:

```text
STAGE1-RENT-15A: First Invited User Trial/Invite Flow Evidence
```

Required observations:

1. user entry surface: Telegram Bot or Mini App;
2. auth/linking status;
3. trial or invite-code action;
4. Remnawave provisioning status;
5. config delivery status;
6. real client connection status;
7. support contact if any;
8. alerts/logs during the attempt.
