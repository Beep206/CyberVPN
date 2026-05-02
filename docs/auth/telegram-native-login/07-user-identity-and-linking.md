# User Identity and Linking

## Goal

Зафиксировать, как Telegram OIDC claims становятся внутренней mobile identity в CyberVPN.

## Telegram Claims

| Claim | Meaning | Internal usage |
|---|---|---|
| `sub` | Stable OIDC subject | Primary external identity key |
| `preferred_username` | Telegram username | Optional display metadata only |
| `name` | Display name | Optional profile field |
| `picture` | Avatar URL | Optional profile field |
| `phone_number` | Verified phone if user consented | Optional verified phone attribute |
| `iss` | Token issuer | Validation only |
| `aud` | Client ID audience | Validation only |
| `exp` | Expiration timestamp | Validation only |
| `iat` | Issued at | Validation only |

## Recommended Internal Identity Model

Phase 1 recommendation:

- keep the current Telegram-specific shape on `MobileUserModel`
- add a stable `telegram_subject` field as the primary OIDC identity key
- keep `telegram_id` as legacy compatibility field

Recommended fields on `mobile_users`:

- `telegram_subject` `unique nullable`
- `telegram_id` `unique nullable`
- `telegram_username` `nullable`
- `telegram_display_name` `nullable`
- `telegram_picture_url` `nullable`
- `telegram_phone_number_e164` `nullable`
- `telegram_phone_verified_at` `nullable`

Rationale:

- Phase 1 scope is Telegram-specific
- current mobile model already stores Telegram-specific fields
- this is smaller than introducing a full generic mobile social identity table immediately

Future option:

- migrate to a generic `mobile_oauth_accounts` or `external_identities` table later if more native providers need the same model

## Why `sub` Must Be Primary

Recommended primary lookup key:

```text
provider = "telegram"
provider_subject = id_token.sub
```

Do not use `phone_number` as the primary unique identity key.

Do not rely only on `telegram_id` going forward if the OIDC token gives a stronger stable subject model.

## Do Not Use `preferred_username` For Lookup

Do not use `preferred_username` for account lookup.

Telegram usernames can change.

If `preferred_username` changes, backend may update display metadata after successful login, but must not treat it as identity.

## Account Resolution Order

Recommended backend resolution order:

1. Find user by `telegram_subject`.
2. Fallback: find user by legacy `telegram_id`.
3. If explicitly allowed by product policy, optionally inspect verified `phone_number`.
4. Otherwise create a new mobile user.

## Linking Rules

### Authenticated Linking

When a logged-in user taps `Link Telegram`:

- backend validates `id_token`
- backend checks whether the Telegram identity is already linked elsewhere
- if free, backend binds Telegram identity to the current user

Endpoint contract is defined in [05-backend-oidc-contract.md](05-backend-oidc-contract.md).

### Auto-Linking

Recommended Phase 1 policy:

- allow lookup by `telegram_subject`
- allow fallback by legacy `telegram_id`
- do not auto-link solely by phone number

## Conflict Rules

- If `telegram_subject` is already linked to another user, reject the request.
- If legacy `telegram_id` points to another user during migration, reject and route for manual resolution or scripted migration.
- If `phone_number` is already attached to another user, do not silently merge accounts.

## Telegram-Only Accounts

Recommended product-policy behavior:

- Telegram-only mobile accounts are allowed
- email can remain absent at product level

Practical backend note:

- current `MobileUserModel` still requires non-null `email` and `password_hash`
- Phase 1 implementation must normalize how Telegram-only users are represented

## Storage Decision Required Before Implementation

### Option A

- allow nullable `email` and `password_hash` on `MobileUserModel`

### Option B

- keep non-null fields and use synthetic compatibility values:
  - `email = tg<telegram_id>@telegram.local`
  - `password_hash = non-login sentinel value`
  - add an explicit marker such as `auth_provider = telegram`

### Recommended Phase 1

- keep synthetic compatibility if DB migration risk is high
- add an explicit marker such as `auth_provider = telegram` or `is_synthetic_email = true`
- block password login for synthetic Telegram-only accounts until the user sets a real email and password

### Phase 0 Decision

Phase 1 is frozen on the synthetic compatibility path:

- keep non-null compatibility for `email` and `password_hash`
- use synthetic internal values only as storage compatibility
- add an explicit marker during implementation so these accounts are never treated as normal password accounts
- defer a full nullable-schema redesign to a later migration if needed

Recommended Phase 1 backend behavior:

- synthetic internal email allowed only as a storage compatibility detail
- synthetic password hash should not be treated as a real login credential
- product/UI should treat the account as Telegram-authenticated, not email-authenticated

## Unlink Policy

Recommended:

- allow unlinking Telegram only if another usable login method remains
- block unlink when it would orphan account access

## Migration From Legacy Telegram Identity

For users created from legacy Telegram flow:

- preserve existing `telegram_id`
- populate `telegram_subject` on next successful OIDC login
- once `telegram_subject` exists, use it as the primary lookup key

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
