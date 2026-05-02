# Privacy, Consent and Phone Number Handling

## Goal

Зафиксировать политику запроса `phone` scope и обращения с номером телефона, если Telegram его возвращает.

## Scope Policy

Recommended Phase 1 scopes:

```text
openid profile
```

Optional extended scopes:

```text
openid profile phone
```

Not requested in Phase 1 by default:

```text
telegram:bot_access
```

## Recommended Phone Policy

Request `phone` only if at least one of the following becomes a confirmed product need:

- phone is required for billing
- phone is required for anti-abuse
- phone improves account recovery enough to justify added consent friction
- the product UI can clearly explain why the number is requested

## Consent Principle

If `phone` is requested:

- user must see why it is needed
- request must be explicit, not hidden
- backend must treat `phone_number` as optional returned data

## Storage Rules

If a phone number is returned:

- Telegram `phone_number` may arrive without `+`
- normalize to E.164 format if possible
- do not guess country incorrectly when normalization is uncertain
- store raw value and normalized value separately if normalization confidence is low
- store a marker such as `phone_verified_by = telegram`
- store `phone_verified_at`
- treat it as profile data, not as the only account identity key

## Analytics Rules

Do not send to analytics without explicit approval:

- raw phone number
- raw Telegram `sub`
- raw Telegram `id_token`

If telemetry needs identity correlation:

- use hashed or internal IDs

## Recommended UI Copy

Primary button:

```text
Continue with Telegram
```

Helper text when `phone` is not requested:

```text
We may receive your Telegram profile information to sign you in.
```

Helper text when `phone` is requested:

```text
We may receive your Telegram profile information. If you allow it, Telegram may also share your verified phone number.
```

## Account Recovery Policy

Recommended Phase 1:

- do not rely solely on Telegram phone number for account recovery
- recovery policy should stay aligned with first-party account and session rules

## Unlink And Deletion Policy

If the user unlinks Telegram:

- preserve any phone data only if product policy allows and privacy basis remains valid
- otherwise remove Telegram-sourced phone markers

If the user deletes account:

- delete or anonymize stored Telegram-linked personal data according to product data-retention policy

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
