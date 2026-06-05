# Sanitizer Rules For Browser QA Evidence

Date: `2026-06-04`

Source issue: [CYBA-454](/CYBA/issues/CYBA-454)

## Default Rule

If an artifact might contain secrets, production PII, payment data, auth state, or raw provider payloads, do not commit it. Quarantine it outside the repo, create a sanitized note, and add a row to `rejected-artifacts.md`.

## Must-Redact Data

Never publish these values in screenshots, traces, videos, console logs, network notes, bug packets, comments, or final reports:

- `Authorization`, `Cookie`, `Set-Cookie`, `X-CSRF-Token`, `X-Api-Key`, `X-Fresh-Auth-Grant-Id`, bearer tokens, API keys, session IDs, CSRF tokens, refresh tokens, access tokens, JWT-like strings, OAuth codes;
- passwords, OTPs, recovery codes, passkey challenges, raw WebAuthn credential IDs, public keys, attestation/assertion payloads;
- Telegram bot tokens, raw Telegram `initData`, signed Mini App payloads, deep links with login payloads;
- payment secrets, provider webhook secrets, card/bank/payment identifiers, crypto invoice payloads, chargeback/dispute raw records;
- `.env` values, deployment secrets, database URLs, Redis/Valkey URLs, Remnawave tokens, VPN subscription/config URLs, QR payloads;
- real customer names, emails, phones, addresses, Telegram usernames/IDs, IP addresses tied to real customers, support messages, ticket transcripts, invoices;
- production tenant/workspace/customer IDs unless already public and approved for release.

## Allowed Synthetic Placeholders

Use stable placeholders instead of raw values:

```text
<redacted-token>
<redacted-cookie>
<redacted-jwt>
<redacted-refresh-token>
<redacted-payment-id>
<redacted-telegram-init-data>
<redacted-customer-email>
test-customer-001@example.test
test-partner-001
test-admin-001
```

## Screenshots And Videos

Accept only when:

- synthetic/test data is visible;
- no browser devtools panel exposes cookies, storage, headers, request bodies, `.env`, tokens, passwords, or payment/customer data;
- visible email/phone/name/payment fields are synthetic or redacted;
- QR codes and VPN config/subscription links are hidden or redacted;
- the screenshot/video has a matching `evidence-index.md` row.

Reject when:

- a real account or real payment/customer record is visible;
- a QR code, config URL, subscription URL, token, or credential is visible;
- a production admin/customer surface is captured without Board approval.

## Console Notes

Do not paste raw console dumps when they include request payloads or tokens.

Allowed format:

```text
[error] route=/en-EN/login code=AUTH_REQUIRED message=<sanitized>
[warning] route=/admin/users code=RBAC_DENIED role=viewer
```

Remove stack frames only when they disclose filesystem secrets, tokens, or private URLs. Keep file/function names when they are safe and useful.

## Network Notes

Prefer summarized markdown over HAR.

Allowed fields:

- HTTP method;
- sanitized path without sensitive query strings;
- status code;
- coarse request type;
- sanitized error code/message;
- timing bucket if relevant.

Do not include:

- headers;
- cookies;
- auth tokens;
- raw request/response bodies;
- payment payloads;
- Telegram `initData`;
- customer PII.

Example:

```text
POST /api/v1/auth/login -> 401 AUTH_INVALID_CREDENTIALS
GET /api/v1/admin/users?cursor=<redacted> -> 403 RBAC_DENIED
```

## Trace And HAR Handling

Raw traces and HAR files are high risk because they may embed request metadata, cookies, headers, URLs, snapshots, and response bodies.

Accept only when:

- the capture used local/staging/test data;
- content/body capture was disabled or removed where possible;
- the artifact was opened and manually inspected;
- all cookies, tokens, auth headers, customer/payment data, Telegram payloads, and raw provider payloads are absent or redacted;
- the index row names the reviewer and review result.

Reject when inspection is not possible in the heartbeat or when any sensitive material remains.

## Bug Packet Safety

Every bug packet must include a `Sensitive-data review` field with one of:

- `PASS - no sensitive data present`;
- `PASS - redacted before publish`;
- `REJECTED - unsafe artifact removed`;
- `BLOCKED - artifact not reviewed`.

`BLOCKED` packets cannot be used as release evidence until reviewed.

## Docs Evidence Line

Context7 docs checked: unavailable - Context7 quota exceeded. Fallback official docs checked: Playwright screenshots, trace viewer/tracing, videos, and network/HAR docs at `playwright.dev`.
