# Mini App Definition of Done

## Product DoD

- user can open Mini App, authenticate, purchase or start trial, and obtain config without leaving Telegram;
- primary user journeys are available in both platform and partner-branded mode;
- server picker and referral flows are available.

## Technical DoD

- `/miniapp` routing is canonical and stable;
- Mini App uses dedicated API contracts for bootstrap, offers, servers, config, and payment status;
- runtime hooks cover Telegram lifecycle needs.

## Security DoD

- backend validates raw Telegram init data;
- `initDataUnsafe` is not used for trust decisions;
- referral and start payloads are signed;
- payment and config access rules are audited.

## Payment DoD

- in-Telegram payment uses Telegram Stars;
- invoice lifecycle is supported in frontend and backend;
- entitlement activates only after authoritative success;
- refund and support handling is defined.

## Analytics DoD

- Mini App funnel events are emitted and visible in dashboards;
- partner and referral attribution survive purchase;
- payment and config delivery events reconcile.

## Testing DoD

- unit, contract, integration, and E2E coverage exist for critical paths;
- route persistence and payment replay behaviors are tested;
- partner-branded runtime path is covered.

## Rollout DoD

- feature flags exist for major Mini App modules;
- rollback path exists for checkout;
- support and incident routing are documented.
