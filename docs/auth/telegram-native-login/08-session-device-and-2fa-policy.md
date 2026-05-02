# Session, Device and 2FA Policy

## Goal

Встроить Telegram Native Login в существующую mobile session model без побочного обхода device binding или TOTP.

## Session Model

Successful Telegram Native Login issues first-party mobile tokens:

- `access_token`
- `refresh_token`
- `token_type = Bearer`
- `expires_in`

Tokens are stored in mobile secure storage exactly like current mobile auth.

Telegram `id_token` is never stored as the primary app session token.

## Device Registration

On successful Telegram OIDC login backend must:

- create or update mobile device record
- bind refresh session to `device_id`
- persist `platform`, `platform_id`, `os_version`, `app_version`, `device_model`
- update `push_token` if provided

This preserves the same device-aware behavior already used in mobile password auth.

## Refresh Policy

After Telegram login:

- refresh uses normal mobile refresh flow
- refresh must validate that `device_id` belongs to the same user
- backend reissues first-party tokens, not Telegram tokens

## Logout Policy

After Telegram login:

- logout revokes CyberVPN refresh session
- logout does not attempt to “log out Telegram”
- local secure storage is always cleared on logout

## 2FA Policy

Recommended decision:

- use Option A
- if user has TOTP enabled, Telegram login returns `requires_2fa=true`
- mobile app shows TOTP screen
- backend issues tokens only after successful TOTP completion

Rationale:

- matches web password and OAuth behavior
- prevents Telegram login from becoming a 2FA bypass
- easier to explain to users and support

## Proposed Pending 2FA Flow

1. Telegram `id_token` is validated.
2. Backend resolves the user.
3. Backend sees TOTP enabled.
4. Backend returns:
   - `requires_2fa=true`
   - `method=totp`
   - `tfa_token`
5. Mobile app routes to TOTP screen.
6. Mobile app calls `POST /api/v1/mobile/auth/2fa/complete`.
7. Backend issues normal mobile tokens.

## `tfa_token` Requirements

The pending token should be:

- short-lived
- signed by backend
- bound to the user
- bound to the login method
- bound to `device_id`

Suggested embedded claims:

- `sub` = internal user id
- `amr` = `telegram_oidc_pending`
- `device_id`
- `exp`
- `iat`

Recommended `tfa_token` policy:

- TTL `5 minutes`
- single purpose only
- not refreshable
- invalid after successful completion
- must not contain the raw Telegram `id_token`

## Biometric Login Interaction

Telegram login does not replace biometric re-auth.

Recommended policy:

- biometric login continues to operate on existing CyberVPN device/session credentials
- Telegram Native Login is an account sign-in path, not a biometric substitute

## Session Invariants

- one successful Telegram login always results in first-party CyberVPN tokens
- refresh remains device-bound
- logout remains first-party
- TOTP policy is enforced consistently

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
