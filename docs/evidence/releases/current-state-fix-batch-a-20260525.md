# Current-state FIX Batch A evidence

Date: 2026-05-25

Scope: `FIX-001` - `FIX-005` production test data reset.

## FIX-001 preflight

Production host: `prod-app-1`

Compose directory: `/srv/cybervpn/compose/app`

Observed services before reset:

- `cybervpn-admin`: healthy
- `cybervpn-backend`: healthy
- `cybervpn-frontend`: healthy
- `cybervpn-postgres`: healthy
- `cybervpn-remnawave`: healthy
- `cybervpn-remnawave-postgres`: healthy
- `cybervpn-telegram-bot`: healthy
- `cybervpn-worker`: healthy
- `cybervpn-scheduler`: healthy
- `cybervpn-valkey`: healthy
- `cybervpn-nats`: healthy

Safety backup created before writes:

- `/srv/cybervpn/backups/cybervpn-pre-fix-batch-a-20260525T173437Z.dump`
- Size: `750K`
- Format: PostgreSQL custom dump from `cybervpn` database

Pre-reset target snapshot:

| Target | Store | State before reset |
|---|---|---|
| `veephtc@gmail.com` | `admin_users` | Active verified viewer account, login `veephtc`, active principal session observed. |
| `@Sasha_Beep` | `mobile_users` | Trial expired on `2026-05-25T08:33:00Z`; Remnawave user `EXPIRED`, 2 GiB limit; has legacy subscription URL. |
| `@Sasha_Beep` | `invite_codes` | 3 invite codes existed; all expired on `2026-05-24`; 2 marked used. |
| `@Sasha_Beep_KZ` | `mobile_users` | Active mobile account with Remnawave UUID and subscription URL. |
| `@Sasha_Beep_KZ` | `entitlement_grants` | Active invite entitlement until `2026-05-29T08:52:47Z`. |
| `@Sasha_Beep_KZ` | `remnawave.users` | Active Remnawave user, 2 GiB limit, expiry `2026-05-29T08:52:47Z`. |

No unrelated users were selected for mutation.

## Planned writes

1. Free `veephtc@gmail.com` and login `veephtc` for repeat registration by tombstoning only that test account.
2. Extend `@Sasha_Beep` trial to a fresh 2 GiB test window and make invite codes reusable/unexpired.
3. Remove active access from `@Sasha_Beep_KZ` so invite redemption can be tested again.
4. Save after-reset snapshot.

## FIX-002 after-reset

`veephtc@gmail.com` registration blockers after reset:

- Rows with `email = veephtc@gmail.com` or `login = veephtc`: `0`
- Original test row tombstoned as `veephtc_deleted_20260525`
- Test row is inactive, email-unverified and has `deleted_at`
- Active principal session for this test row was revoked

Expected owner check: registering `veephtc@gmail.com` should no longer stop at `Username already exists`.

## FIX-003 after-reset

`@Sasha_Beep` after reset:

- `mobile_users.status`: `active`
- Trial active from `2026-05-25T17:37:57Z`
- Trial expires at `2026-05-28T17:37:57Z`
- Existing Remnawave UUID and subscription URL remain present
- Remnawave user status: `ACTIVE`
- Remnawave traffic limit: `2147483648` bytes (`2 GiB`)
- Remnawave strategy: `NO_RESET`
- Remnawave expiry: `2026-05-28T17:38:23Z`

Reusable invite codes now available:

| Code | Free days | Used | Expires |
|---|---:|---|---|
| `409F****` | 7 | false | `2026-06-01T17:37:57Z` |
| `A21E****` | 7 | false | `2026-06-01T17:37:57Z` |
| `C46C****` | 7 | false | `2026-06-01T17:37:57Z` |

Growth redemptions for these reset invite codes after cleanup: `0`.

## FIX-004 after-reset

`@Sasha_Beep_KZ` after reset:

- `mobile_users.status`: `active`
- Trial fields: empty
- Stored Remnawave UUID: absent
- Stored subscription URL: absent
- Active entitlement grants: `0`
- Service identities: `0`
- Remnawave user status: `EXPIRED`
- Remnawave expiry: `2026-05-25T17:37:23Z`
- Remnawave `sub_revoked_at`: `2026-05-25T17:38:23Z`

Expected owner check: `@Sasha_Beep_KZ` should be able to redeem one of `@Sasha_Beep` invite codes again and receive a fresh config after redemption.

## FIX-005 after-reset snapshot

After-reset verification passed for the requested test accounts only:

- `veephtc@gmail.com` is free for registration retest.
- `@Sasha_Beep` has fresh 2 GiB trial access and 3 reusable invite codes.
- `@Sasha_Beep_KZ` no longer has active CyberVPN entitlement or stored VPN config pointer.
- Remnawave state matches the intended test setup: owner active, invite tester expired.

No production containers were restarted for Batch A because only database state was changed.
