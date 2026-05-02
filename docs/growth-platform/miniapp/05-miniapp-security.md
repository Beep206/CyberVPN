# Mini App Security

## Core Rules

1. Validate raw Telegram init data on the backend.
2. Never trust `initDataUnsafe` for protected actions.
3. Sign and expire all share and attribution payloads.
4. Activate service only after authoritative payment success.
5. Keep tenant context explicit in partner-branded flows.

## Telegram Session Validation

- raw init data enters backend on bootstrap;
- backend verifies origin and validity;
- session is bound to canonical user and Telegram identity;
- suspicious mismatches are logged and rate-limited;
- client telemetry around runtime events is informative only and not trusted as proof.

## `initDataUnsafe` Restrictions

Allowed uses:

- display-only hints in non-sensitive UI before bootstrap completes

Forbidden uses:

- price calculation
- partner attribution trust
- entitlement access
- trial eligibility
- payment authorization

## Signed `startapp` Payloads

Signed payloads should include:

- referral code if present;
- partner and campaign metadata if present;
- issuance time and expiry;
- signature or MAC.

## Referral and Attribution Signing

- never expose plain, unbounded referral tokens as the only signal;
- include expiry and integrity protection;
- validate surface and tenant where relevant.

## Payment Payload Security

- quote and invoice actions require server-issued references;
- client must not be able to change price or attribution silently;
- payment records must capture tenant and commercial context before invoice open;
- pre-checkout validation must reject quote tampering or stale tenant context.

## Trial Abuse Protection

Trial checks should incorporate:

- Telegram identity history;
- user linkage history;
- device and IP risk signals;
- referral loop patterns;
- partner risk policies.

## Config Delivery Protection

- require active entitlement;
- enforce device limits and access rules;
- audit config delivery;
- protect sensitive config URLs from uncontrolled reuse where possible.

## Rate Limits

Recommended strict controls for:

- trial activation
- quote creation
- invoice creation
- referral share events
- device mutation actions

## Suspicious Behavior Detection

Examples:

- many quote attempts with low follow-through;
- repeated invalid payloads;
- referral self-attribution loops;
- partner-branded flows hitting unexpected geographies or abuse patterns.

## Security Readiness Criteria

- bootstrap validation audited;
- payment activation server-authoritative;
- signed payloads implemented;
- abuse thresholds observable;
- partner-aware isolation tested.
