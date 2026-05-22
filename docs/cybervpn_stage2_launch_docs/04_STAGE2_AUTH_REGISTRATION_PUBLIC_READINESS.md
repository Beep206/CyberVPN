# Stage 2 Auth And Registration Public Readiness

**Stage:** `S2-STAGE-05`
**Status:** Approved local readiness baseline
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 public auth and registration contract before moving deeper into payment and subscription lifecycle work.

The goal is to move from S1 controlled beta access to wider public B2C signup without creating an abuse, support, or account-recovery problem.

---

## 2. S2 Public Registration Decision

S2 public registration should open gradually, not as an uncontrolled wide-open switch.

Recommended runtime progression:

| Step | `REGISTRATION_ENABLED` | `REGISTRATION_INVITE_REQUIRED` | Meaning |
|---|---:|---:|---|
| S2 auth smoke | `false` | `true` | Existing users only; prove login, delete, privacy, Telegram and OAuth readiness |
| S2 public canary | `true` | `true` | New users can register only with invite; safe for first wider cohort |
| S2 public release | `true` | `false` | Open signup after auth abuse controls, support diagnostics and payment gates pass |
| Emergency pause | `false` | `true` | Stop new account creation while keeping existing-user login available |

Do not open `REGISTRATION_INVITE_REQUIRED=false` until:

1. registration/login rate limits are active;
2. support can identify a user without seeing secrets;
3. email/Telegram/OAuth flows have staging or production-like smoke evidence;
4. payment and provisioning flows are ready for users who immediately convert after signup.

---

## 3. Approved Auth Methods For S2

| Method | S2 state | Runtime rule |
|---|---|---|
| Email + password | Approved | May be public after canary registration gate |
| Telegram Mini App / Bot / Web identity | Approved | May create/link customer accounts only under registration policy |
| Magic link / OTP | Approved | Must stay rate-limited and observable |
| Google OAuth | Conditional | Enable only when production credentials and callback evidence exist |
| GitHub OAuth | Conditional | Enable only when production credentials and callback evidence exist |
| Facebook / Discord / Apple / Microsoft / Twitter OAuth login | Not approved for S2 public login | Must remain inactive even if provider code exists |

Production OAuth rule:

```text
OAUTH_ENABLED_LOGIN_PROVIDERS=
```

is the safe default until credentials are ready.

If `google` or `github` is present in `OAUTH_ENABLED_LOGIN_PROVIDERS` in production, backend startup must fail unless the matching client ID/secret and `OAUTH_WEB_BASE_URL` are configured. This prevents a broken public login button or half-enabled OAuth callback from reaching users.

---

## 4. Rate Limit Coverage

S2 reuses the existing launch-sensitive rate-limit buckets. The internal bucket names still contain `s1_` because they were created during Stage 1 and remain the production control surface.

| Surface | Endpoint examples | Required bucket |
|---|---|---|
| Login | `POST /api/v1/auth/login` | `s1_auth_sensitive` |
| Registration | `POST /api/v1/auth/register` | `s1_auth_sensitive` |
| Magic link request | `POST /api/v1/auth/magic-link` | `s1_auth_sensitive` plus service-level email limit |
| Magic link verify | `POST /api/v1/auth/magic-link/verify` | `s1_auth_sensitive` |
| Magic link OTP verify | `POST /api/v1/auth/magic-link/verify-otp` | `s1_auth_sensitive` |
| Telegram Mini App auth | `POST /api/v1/auth/telegram/miniapp` | `s1_auth_sensitive` plus Telegram dependency limiter |
| Telegram Web auth | `POST /api/v1/auth/telegram/web` | `s1_auth_sensitive` plus Telegram dependency limiter |
| Telegram Bot link | `POST /api/v1/auth/telegram/bot-link` | `s1_auth_sensitive` plus Telegram dependency limiter |
| OAuth callbacks | `POST /api/v1/oauth/*` | `s1_auth_sensitive` |
| Invite redemption | `POST /api/v1/invites/redeem` | `s1_growth_sensitive` |

Production rate-limit failure mode remains fail-closed unless explicitly overridden for a controlled incident.

---

## 5. Account Deletion And Privacy Requests

The S2 readiness baseline keeps these user rights paths available:

| Capability | Path | S2 handling |
|---|---|---|
| Web/account delete | `DELETE /api/v1/auth/me` | Soft-delete user account, revoke sessions/tokens |
| Mobile/Mini App delete | `DELETE /api/v1/mobile/auth/me` | Delete customer account and revoke VPN access through backend flow |
| Privacy request | `POST /api/v1/auth/me/privacy-requests` | Manual support/escalation ticket for `account_deletion` or `data_export` |

S2 does not require fully automated raw data export before public release. The required S2 behavior is that the user has a documented privacy request path and support can process it manually without exposing secrets in chat/logs.

---

## 6. Admin And Bootstrap Guardrails

These S1 hard rules stay active for S2:

1. production admin 2FA is mandatory;
2. admin host protection is mandatory;
3. no default admin credentials are allowed;
4. first admin bootstrap is one-time, protected, audited and disabled after use;
5. no permanent public bootstrap endpoint may exist;
6. support/admin diagnostics must not expose raw passwords, OTP codes, OAuth secrets, Telegram bot tokens or refresh tokens.

---

## 7. Support Diagnostics Contract

Support may use these safe identifiers:

```text
user id
email
Telegram id / Telegram username
payment attempt id
subscription id
request id / trace id
ticket reference
```

Support must not ask users for:

```text
password
OTP code
magic-link token
OAuth authorization code
refresh token
Telegram initData
VPN private credential beyond the public subscription URL/config already shown to the user
```

---

## 8. Runtime Recommendation Before S2-STAGE-06

For the next stage, keep this posture:

```text
REGISTRATION_ENABLED=false
REGISTRATION_INVITE_REQUIRED=true
OAUTH_ENABLED_LOGIN_PROVIDERS=
```

Then switch to the S2 public canary only after payment production hardening is ready:

```text
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=true
```

Open fully only near S2 Go/No-Go:

```text
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=false
```

---

## 9. Acceptance Evidence

Completed checks for this stage:

| Check | Result |
|---|---|
| Missing auth-sensitive route coverage fixed | `magic-link/verify-otp` added to `s1_auth_sensitive` |
| Missing invite redemption coverage fixed | `invites/redeem` added to `s1_growth_sensitive` |
| Production OAuth credential guard added | Startup rejects enabled Google/GitHub without required production credentials |
| Unsupported public OAuth providers rejected | `OAUTH_ENABLED_LOGIN_PROVIDERS` accepts only Google/GitHub |
| Production safety tests | Passed targeted backend suite |
| Account deletion path reviewed | Web and mobile/customer delete paths exist |
| Privacy request path reviewed | Manual `account_deletion` / `data_export` support path exists |

Commands and outputs are recorded in:

```text
docs/evidence/releases/s2-stage-05-auth-registration-20260522.md
```

---

## 10. No-Go Conditions

Do not proceed to wider public registration if any of these become true:

1. public registration is opened without rate limits;
2. OAuth provider is enabled without production credentials and callback evidence;
3. Telegram account creation bypasses the registration policy;
4. support cannot identify failed auth cases without asking for secrets;
5. admin 2FA is disabled;
6. a default or public bootstrap admin path exists;
7. delete/privacy request paths are broken.
