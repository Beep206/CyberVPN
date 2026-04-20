# Partner Platform Event Taxonomy Baseline

This file is the application-layer placeholder for the frozen `Phase 0` event taxonomy.

Canonical event families currently reserved:

- storefront
- realm
- order
- attribution
- growth_reward
- settlement
- risk
- entitlement
- service_access
- reporting

The frozen baseline is defined in:

- `docs/api/partner-platform-event-taxonomy.md`
- `src/application/events/partner_platform_events.py`
- `src/application/events/outbox.py`

Rules:

1. Event family names are canonical and must not be renamed in later phases.
2. Payloads may expand later, but frozen family names must remain stable.
3. Provider-specific terminology must not replace platform event families.
4. The reliable outbox layer must publish canonical event names, not derived aliases.
5. Canonical publication state lives in `outbox_events` and `outbox_publications`.
