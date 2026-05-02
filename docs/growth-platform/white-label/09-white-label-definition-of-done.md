# White-Label Definition of Done

## Product DoD

- partner can self-service from approved application to active branded bot and branded Mini App path;
- partner has storefront preview, launch checklist, analytics, and payout visibility.

## Technical DoD

- partner branding is DB-driven;
- storefront runtime is DB-driven;
- branded Mini App uses shared canonical runtime;
- provisioning follows a state machine with retries and failure visibility.

## Security and Compliance DoD

- tenant isolation is enforced and tested;
- moderation and KYB controls are active;
- emergency suspend exists;
- audit logs exist for sensitive actions.

## Commercial DoD

- `PartnerCommercialPolicy` governs pricing and settlement;
- partner revenue attribution is preserved end-to-end;
- payout lifecycle is defined and observable;
- immutable settlement ledger and reversal behavior are in place.

## Provisioning DoD

- Managed Bots primary path is available or validated for the target release;
- manual token fallback exists;
- token rotation and suspension exist;
- admin/operator suspend and recovery paths exist.

## Analytics DoD

- partner applications, provisioning, sales, and payout events are captured;
- partner dashboards reflect actual attributed performance.

## Testing DoD

- E2E path exists for application -> bot -> payment -> entitlement -> partner attribution;
- negative tests exist for tenant leakage and provisioning failures.
