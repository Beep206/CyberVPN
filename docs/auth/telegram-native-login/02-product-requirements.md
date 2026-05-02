# Product Requirements — Telegram Native Login

## Problem Statement

Мобильное приложение `cybervpn_mobile` уже имеет Telegram login entry point, но текущий flow опирается на legacy payload и не соответствует новому официальному Telegram Native Login/OIDC path.

Нужно внедрить mobile-first Telegram login так, чтобы:

- регистрация и логин происходили быстрее
- снизился friction для новых пользователей
- не ломалась текущая mobile token/session model
- не появлялся security gap относительно web auth и TOTP

## Goals

- Add `Continue with Telegram` to mobile login and register screens.
- Allow new users to create account without email/password.
- Allow existing Telegram-linked users to sign in with Telegram.
- Allow authenticated users to link Telegram to an existing account.
- Optionally request verified phone number when product policy requires it.
- Preserve current secure storage and device-aware session model.

## Non-Goals

- Rebuild the full web auth stack.
- Make Telegram mandatory for all mobile users.
- Request `phone` scope by default without product justification.
- Bypass TOTP for users who already enabled 2FA.

## Primary User Flows

### New User Via Telegram

1. User taps `Continue with Telegram`.
2. Telegram native login starts.
3. User grants consent.
4. App receives Telegram login result from the native SDK.
5. App sends `id_token` to backend.
6. Backend validates identity.
7. Backend creates mobile user if none exists.
8. Backend returns first-party mobile tokens.
9. App stores tokens securely and opens the authenticated area.

### Existing User With Telegram Already Linked

1. User taps `Continue with Telegram`.
2. App gets `id_token`.
3. Backend resolves the existing account by Telegram identity.
4. Backend registers or updates device.
5. Backend returns tokens.

### Existing Logged-In User Links Telegram

1. User opens profile or security settings.
2. User taps `Link Telegram`.
3. Native Telegram login starts.
4. Backend validates the `id_token`.
5. Backend links Telegram identity to the current user.
6. UI confirms that Telegram is linked.

### Existing User With TOTP Enabled

1. User completes Telegram login.
2. Backend validates Telegram identity.
3. Backend sees that the user has TOTP enabled.
4. Backend returns `requires_2fa=true`.
5. Mobile app shows TOTP challenge.
6. Backend issues tokens only after successful TOTP verification.

## Recommended Product Decisions

### Decision 1: Phone Scope

Recommended for Phase 1:

- default scopes: `openid profile`
- `phone` scope disabled by default
- enable `phone` only behind a feature flag and explicit UI copy

Rationale:

- lower friction at launch
- smaller consent surface
- faster rollout
- avoids premature identity and privacy complexity

### Decision 2: Telegram-Only Accounts

Recommended:

- Telegram-only accounts are allowed in Phase 1
- email is optional at product level
- if backend storage still requires email, use a system-generated internal placeholder and mark it as synthetic

### Decision 3: Email Verification

Recommended:

- Telegram login does not require separate email verification
- Telegram identity is treated as possession-based login
- this does not bypass TOTP if TOTP is enabled

### Decision 4: 2FA

Recommended:

- Telegram login must respect existing TOTP policy
- Telegram login does not become a 2FA bypass route

### Decision 5: `telegram:bot_access` Scope

Recommended for Phase 1:

- do not request `telegram:bot_access`
- request only if a clearly defined product need exists for post-login bot DM

## Product Rules

- If Telegram identity is already linked to another user, linking must be rejected.
- If the user is new, account creation must be seamless.
- If the user is existing and has TOTP enabled, tokens must not be issued before TOTP completion.
- If `phone` is requested and returned, it is treated as optional verified profile data, not as the sole identity key.

## Acceptance Criteria

- User can complete `Continue with Telegram` on iOS.
- User can complete `Continue with Telegram` on Android.
- Successful login results in secure storage of first-party mobile tokens.
- Existing linked users are resolved without duplicate account creation.
- New Telegram users can enter the app without email/password.
- A Telegram-only user cannot accidentally sign in via password unless they explicitly set a real email and password.
- If Telegram login is cancelled by the user, the app returns to the login screen without partial session state.
- TOTP-enabled users are gated behind pending 2FA.
- Legacy mobile Telegram flow remains available for rollback during migration.

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
